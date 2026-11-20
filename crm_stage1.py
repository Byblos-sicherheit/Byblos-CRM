"""CRM Stufe 1: Sparten-Trennung, 80-km-Radius ab Tülau und Dublettenprüfung für Kunden."""
import json
import math
import re
import unicodedata
import urllib.parse
import urllib.request

SPARTEN = ("Unbekannt", "Sicherheit", "Facility", "Beide")

# shortcut: Ortsmitte Tülau (38474), ca. ±1 km genau; bei Grenzfällen Straßenentfernung manuell prüfen
BASE_LAT, BASE_LON = 52.574, 10.876
MAX_KM = 80.0
# Luftlinie unterschätzt die Straßenentfernung, daher ab 70 km manuelle Prüfung
GRENZ_KM = 70.0

NEW_COLUMNS = {
    "sparte": "TEXT DEFAULT 'Unbekannt'",
    "website": "TEXT",
    "source": "TEXT",
    "lat": "REAL",
    "lon": "REAL",
    "distance_km": "REAL",
}

FREEMAIL = {
    "gmail.com", "googlemail.com", "web.de", "gmx.de", "gmx.net", "outlook.de", "outlook.com",
    "hotmail.com", "hotmail.de", "live.de", "yahoo.de", "yahoo.com", "t-online.de", "icloud.com",
    "aol.com", "freenet.de", "mail.de", "posteo.de",
}

LEGAL_FORMS = (
    r"gmbh\s*&\s*co\.?\s*kg", r"gmbh\s*u\.?\s*co\.?\s*kg", r"se\s*&\s*co\.?\s*kg", r"ug\s*\(haftungsbeschränkt\)",
    r"gmbh", r"mbh", r"ag", r"kg", r"ohg", r"gbr", r"e\.?\s*k\.?", r"e\.?\s*v\.?", r"ug", r"se", r"ltd\.?", r"inc\.?",
)


def ensure_columns(conn):
    """Fehlende Stufe-1-Spalten an customers anhängen (idempotent)."""
    have = {r[1] for r in conn.execute("PRAGMA table_info(customers)")}
    for name, decl in NEW_COLUMNS.items():
        if name not in have:
            conn.execute(f"ALTER TABLE customers ADD COLUMN {name} {decl}")
    conn.commit()


def haversine_km(lat1, lon1, lat2, lon2):
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def distance_from_base(lat, lon):
    if lat is None or lon is None:
        return None
    return round(haversine_km(BASE_LAT, BASE_LON, float(lat), float(lon)), 1)


def radius_status(km):
    if km is None:
        return "unbekannt"
    if km > MAX_KM:
        return "außerhalb"
    if km > GRENZ_KM:
        return "Grenzfall – Straßenentfernung prüfen"
    return "im Radius"


def geocode(street, zip_city, country="Deutschland", timeout=10):
    """Adresse über OpenStreetMap Nominatim in (lat, lon) umwandeln; None bei Fehler oder ohne Netz."""
    query = ", ".join(x for x in (street, zip_city, country) if x)
    if not query.strip():
        return None
    url = "https://nominatim.openstreetmap.org/search?" + urllib.parse.urlencode({"q": query, "format": "json", "limit": 1})
    req = urllib.request.Request(url, headers={"User-Agent": "ByblosCRM/2 (Kundenverwaltung)"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            hits = json.loads(resp.read().decode("utf-8"))
    except (OSError, ValueError):
        return None
    if not hits:
        return None
    return float(hits[0]["lat"]), float(hits[0]["lon"])


def _fold(text):
    text = (text or "").lower().replace("ß", "ss").replace("ä", "ae").replace("ö", "oe").replace("ü", "ue")
    return unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()


def normalize_company(name):
    s = (name or "").lower()
    for form in LEGAL_FORMS:
        s = re.sub(rf"(?<![a-zäöüß]){form}(?![a-zäöüß])", " ", s)
    s = _fold(s)
    return re.sub(r"[^a-z0-9]+", "", s)


def normalize_address(street, zip_city):
    s = _fold(f"{street or ''} {zip_city or ''}")
    s = re.sub(r"strasse\b|\bstr\b\.?", "str", s)
    return re.sub(r"[^a-z0-9]+", "", s)


def company_domain(email="", website=""):
    """Firmendomain aus Website oder E-Mail; Freemail-Adressen zählen nicht."""
    if website:
        host = urllib.parse.urlparse(website if "://" in website else "http://" + website).hostname or ""
        host = host.lower().removeprefix("www.")
        if host:
            return host
    if email and "@" in email:
        dom = email.rsplit("@", 1)[1].strip().lower()
        if dom and dom not in FREEMAIL:
            return dom
    return ""


def find_duplicates(conn, company, email="", website="", street="", zip_city="", exclude_id=None):
    """Mögliche Dubletten als Liste von (id, company, gründe)."""
    cur = conn.execute("SELECT * FROM customers")
    cols = [d[0] for d in cur.description]
    rows = [dict(zip(cols, r)) for r in cur.fetchall()]
    return find_duplicates_in(rows, company, email, website, street, zip_city, exclude_id)


def find_duplicates_in(rows, company, email="", website="", street="", zip_city="", exclude_id=None):
    """Wie find_duplicates, aber auf einer Liste von Kunden-Dicts (z. B. DataFrame.to_dict('records'))."""
    n_company = normalize_company(company)
    n_email = (email or "").strip().lower()
    n_domain = company_domain(email, website)
    n_addr = normalize_address(street, zip_city) if street and zip_city else ""
    hits = []
    for row in rows:
        if exclude_id is not None and row["id"] == exclude_id:
            continue
        reasons = []
        if n_company and normalize_company(row.get("company")) == n_company:
            reasons.append("Firmenname")
        if n_email and (row.get("email") or "").strip().lower() == n_email:
            reasons.append("E-Mail")
        if n_domain and company_domain(row.get("email") or "", row.get("website") or "") == n_domain:
            reasons.append("Domain")
        if n_addr and row.get("street") and row.get("zip_city") and normalize_address(row["street"], row["zip_city"]) == n_addr:
            reasons.append("Adresse")
        if reasons:
            hits.append((row["id"], row.get("company"), reasons))
    return hits
