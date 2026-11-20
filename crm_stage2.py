"""CRM Stufe 2: Leads/Bewerbungen mit Statuskette, Kontaktnachweis und Versandprüfung.

"gesendet" protokolliert nur einen außerhalb erfolgten Versand; dieses Modul verschickt nichts.
"""
from datetime import datetime, timedelta, timezone

import crm_stage1

STATUSES = ("neu", "geprüft", "geeignet", "Entwurf", "gesendet", "Antwort", "nachfassen", "gewonnen", "verloren", "gesperrt")
TRANSITIONS = {
    "neu": {"geprüft", "gesperrt"},
    "geprüft": {"geeignet", "gesperrt"},
    "geeignet": {"Entwurf", "gesperrt"},
    "Entwurf": {"gesendet", "geeignet", "gesperrt"},
    "gesendet": {"Antwort", "nachfassen", "verloren"},
    "Antwort": {"nachfassen", "gewonnen", "verloren"},
    "nachfassen": {"Antwort", "gewonnen", "verloren"},
    "gewonnen": set(),
    "verloren": set(),
    "gesperrt": set(),
}
# Status, die bedeuten: dieser Kunde wurde in dieser Sparte bereits angeschrieben
CONTACTED = {"gesendet", "Antwort", "nachfassen", "gewonnen", "verloren"}

CHANNELS = ("E-Mail", "Vergabeportal", "Lieferantenportal", "Telefon", "Post", "Persönlich")
LEGAL_BASES = (
    "Keine",
    "Ausdrückliche Einwilligung",
    "Anfrage des Kunden",
    "Öffentliche Ausschreibung / Portal",
    "Bestandskunde (§ 7 Abs. 3 UWG geprüft)",
)
# Kanäle, für die eine Rechtsgrundlage Pflicht ist (Werbung per E-Mail, § 7 UWG)
NEEDS_LEGAL_BASIS = {"E-Mail"}

SENDERS = {"Sicherheit": "info@byblos-sicherheit.de", "Facility": "info@byblos-reinigung.de"}
MIN_SEND_GAP_SECONDS = 60


def ensure_tables(conn):
    conn.execute("""CREATE TABLE IF NOT EXISTS leads (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        customer_id INTEGER NOT NULL REFERENCES customers(id),
        sparte TEXT NOT NULL,
        title TEXT NOT NULL,
        source TEXT,
        channel TEXT NOT NULL,
        legal_basis TEXT NOT NULL DEFAULT 'Keine',
        recipient TEXT,
        status TEXT NOT NULL DEFAULT 'neu',
        radius_confirmed INTEGER NOT NULL DEFAULT 0,
        notes TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP)""")
    conn.execute("""CREATE TABLE IF NOT EXISTS lead_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        lead_id INTEGER NOT NULL REFERENCES leads(id),
        ts TEXT NOT NULL,
        from_status TEXT,
        to_status TEXT NOT NULL,
        channel TEXT,
        legal_basis TEXT,
        recipient TEXT,
        sender TEXT,
        note TEXT)""")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_leads_customer ON leads(customer_id, sparte)")
    conn.commit()


def _now():
    return datetime.now(timezone.utc).replace(microsecond=0)


def _fmt(ts):
    return ts.strftime("%Y-%m-%d %H:%M:%S")


def _one(conn, sql, params=()):
    cur = conn.execute(sql, params)
    row = cur.fetchone()
    return dict(zip([d[0] for d in cur.description], row)) if row else None


def create_lead(conn, customer_id, sparte, title, channel, legal_basis="Keine", recipient="", source="", notes=""):
    """Lead anlegen (Status neu) und das erste Ereignis protokollieren. Gibt die id zurück."""
    if sparte not in SENDERS:
        raise ValueError("Lead braucht die Sparte Sicherheit oder Facility")
    if channel not in CHANNELS:
        raise ValueError(f"Unbekannter Kanal: {channel}")
    if legal_basis not in LEGAL_BASES:
        raise ValueError(f"Unbekannte Rechtsgrundlage: {legal_basis}")
    if not (title or "").strip():
        raise ValueError("Titel/Leistung ist Pflicht")
    if not _one(conn, "SELECT id FROM customers WHERE id=?", (customer_id,)):
        raise ValueError("Kunde nicht gefunden")
    cur = conn.execute(
        "INSERT INTO leads(customer_id,sparte,title,source,channel,legal_basis,recipient,notes) VALUES(?,?,?,?,?,?,?,?)",
        (customer_id, sparte, title.strip(), source, channel, legal_basis, recipient, notes))
    lead_id = cur.lastrowid
    conn.execute("INSERT INTO lead_events(lead_id,ts,from_status,to_status,channel,legal_basis,recipient,note) VALUES(?,?,?,?,?,?,?,?)",
                 (lead_id, _fmt(_now()), None, "neu", channel, legal_basis, recipient, "angelegt"))
    conn.commit()
    return lead_id


def contact_history(conn, customer_id):
    """Bisherige Kontakte zu einem Kunden: Lead-Ereignisse, Kontakthistorie und E-Mail-Log (gleiche Domain)."""
    hist = [("Lead", r[0], f"{r[1]}: {r[2]} → {r[3]}") for r in conn.execute(
        """SELECT e.ts, l.title, e.from_status, e.to_status FROM lead_events e JOIN leads l ON l.id=e.lead_id
           WHERE l.customer_id=? ORDER BY e.ts""", (customer_id,))]
    if _one(conn, "SELECT name FROM sqlite_master WHERE type='table' AND name='contacts'"):
        hist += [("Kontakt", r[0], f"{r[1]}: {r[2] or ''}") for r in conn.execute(
            "SELECT contact_date, contact_type, subject FROM contacts WHERE customer_id=?", (customer_id,))]
    cust = _one(conn, "SELECT * FROM customers WHERE id=?", (customer_id,)) or {}
    domain = crm_stage1.company_domain(cust.get("email") or "", cust.get("website") or "")
    if domain and _one(conn, "SELECT name FROM sqlite_master WHERE type='table' AND name='email_log'"):
        hist += [("E-Mail", r[0] or r[1], f"{r[2]} ({r[3]})") for r in conn.execute(
            "SELECT sent_at, created_at, subject, status FROM email_log WHERE lower(recipient) LIKE ?", (f"%@{domain}",))]
    return sorted(hist, key=lambda h: str(h[1] or ""))


def check_send(conn, lead_id, now=None):
    """Gründe, warum dieser Lead NICHT als gesendet markiert werden darf. Leere Liste = zulässig."""
    now = now or _now()
    lead = _one(conn, "SELECT * FROM leads WHERE id=?", (lead_id,))
    if not lead:
        return ["Lead nicht gefunden"]
    cust = _one(conn, "SELECT * FROM customers WHERE id=?", (lead["customer_id"],)) or {}
    reasons = []
    if lead["status"] != "Entwurf":
        reasons.append(f"Nur ein Entwurf kann gesendet werden (Status: {lead['status']})")
    if lead["sparte"] not in SENDERS:
        reasons.append("Sparte des Leads muss Sicherheit oder Facility sein")
    status = crm_stage1.radius_status(cust.get("distance_km"))
    if status == "außerhalb":
        reasons.append(f"Kunde liegt außerhalb von {crm_stage1.MAX_KM:.0f} km ({cust.get('distance_km')} km)")
    elif status == "unbekannt":
        reasons.append("Entfernung des Kunden unbekannt – Koordinaten in der Kundenverwaltung eintragen")
    elif status.startswith("Grenzfall") and not lead["radius_confirmed"]:
        reasons.append("Grenzfall: Straßenentfernung prüfen und im Lead bestätigen")
    if lead["channel"] in NEEDS_LEGAL_BASIS and lead["legal_basis"] == "Keine":
        reasons.append("E-Mail ohne Rechtsgrundlage (§ 7 UWG) – Portal oder Entwurf nutzen")
    if lead["channel"] == "E-Mail" and "@" not in (lead["recipient"] or ""):
        reasons.append("Empfänger-E-Mail fehlt")
    prior = _one(conn, f"""SELECT id, title, status FROM leads WHERE customer_id=? AND sparte=? AND id<>?
                           AND status IN ({','.join('?' * len(CONTACTED))})""",
                 (lead["customer_id"], lead["sparte"], lead_id, *sorted(CONTACTED)))
    if prior:
        reasons.append(f"Doppelbewerbung: Kunde in Sparte {lead['sparte']} bereits angeschrieben (Lead {prior['id']}: {prior['title']}, {prior['status']})")
    blocked = _one(conn, "SELECT id FROM leads WHERE customer_id=? AND status='gesperrt' AND id<>?", (lead["customer_id"], lead_id))
    if blocked:
        reasons.append(f"Kunde ist gesperrt (Lead {blocked['id']})")
    last = _one(conn, "SELECT MAX(ts) AS ts FROM lead_events WHERE to_status='gesendet'")
    if last and last["ts"]:
        gap = now - datetime.strptime(last["ts"], "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
        if gap < timedelta(seconds=MIN_SEND_GAP_SECONDS):
            reasons.append(f"Letzter Versand vor {int(gap.total_seconds())} s – mindestens {MIN_SEND_GAP_SECONDS} s Abstand")
    return reasons


def transition(conn, lead_id, to_status, note="", now=None):
    """Status ändern und als Nachweis protokollieren. ValueError, wenn nicht zulässig."""
    now = now or _now()
    lead = _one(conn, "SELECT * FROM leads WHERE id=?", (lead_id,))
    if not lead:
        raise ValueError("Lead nicht gefunden")
    if to_status not in TRANSITIONS.get(lead["status"], set()):
        raise ValueError(f"Übergang {lead['status']} → {to_status} nicht erlaubt")
    sender = None
    if to_status == "gesendet":
        reasons = check_send(conn, lead_id, now)
        if reasons:
            raise ValueError("; ".join(reasons))
        sender = SENDERS[lead["sparte"]]
    conn.execute("UPDATE leads SET status=?, updated_at=? WHERE id=?", (to_status, _fmt(now), lead_id))
    conn.execute("INSERT INTO lead_events(lead_id,ts,from_status,to_status,channel,legal_basis,recipient,sender,note) VALUES(?,?,?,?,?,?,?,?,?)",
                 (lead_id, _fmt(now), lead["status"], to_status, lead["channel"], lead["legal_basis"], lead["recipient"], sender, note))
    conn.commit()


def confirm_radius(conn, lead_id):
    conn.execute("UPDATE leads SET radius_confirmed=1 WHERE id=?", (lead_id,))
    conn.commit()
