"""CRM Stufe 6: Angebot → Rechnungsentwurf → Pflichtangaben-Prüfung → Freigabe → Testexport.

Entwürfe liegen in invoice_drafts und erscheinen erst nach ausdrücklicher Freigabe in invoices
(dann mit fortlaufender RE-Nummer). So tauchen Entwürfe nicht in Umsatz, DATEV oder Mahnwesen auf.
Der Export ist ein Testexport ohne Buchung und ohne Kontenzuordnung.
Steuerliche Regeln (Steuerfall, Konten) vor produktiver Nutzung mit dem Steuerberater abstimmen.
"""
import csv
import hashlib
import io
from datetime import date, datetime, timedelta

from numbering import next_number_from

_ADDRESS = {"street": "Hauptstraße 19", "city": "38474 Tülau", "country": "Deutschland",
            "phone": "+49 176 42988324", "vat_id": "DE364648388"}
ISSUERS = {
    "Sicherheit": {"name": "Byblos Sicherheitsdienst & Service", "email": "info@byblos-sicherheit.de",
                   "website": "https://byblos-sicherheit.de", **_ADDRESS},
    "Facility": {"name": "Byblos Reinigung & Hausmeisterservice", "email": "info@byblos-reinigung.de",
                 "website": "https://byblos-reinigung.de", **_ADDRESS},
}

# Steuerfall -> (Steuersatz, Pflichthinweis auf der Rechnung, Begründung nötig)
TAX_CASES = {
    "Regelsteuersatz 19 %": (19.0, "", False),
    "Ermäßigt 7 %": (7.0, "", True),
    "Reverse Charge § 13b UStG": (0.0, "Steuerschuldnerschaft des Leistungsempfängers", True),
    "Steuerfrei": (0.0, "Steuerfreie Leistung", True),
}
FINANCE_ROLES = ("Inhaber/Admin", "Buchhaltung")
EDITABLE = ("description", "service_date", "due_days", "net_total", "tax_case", "tax_reason", "recipient_vat_id")


def ensure_tables(conn):
    conn.execute("""CREATE TABLE IF NOT EXISTS invoice_drafts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        offer_id INTEGER UNIQUE NOT NULL,
        lead_id INTEGER,
        customer_id INTEGER NOT NULL,
        sparte TEXT NOT NULL,
        description TEXT,
        service_date TEXT,
        due_days INTEGER NOT NULL DEFAULT 14,
        net_total REAL NOT NULL,
        tax_case TEXT NOT NULL DEFAULT 'Regelsteuersatz 19 %',
        vat_rate REAL NOT NULL DEFAULT 19,
        tax_reason TEXT,
        recipient_vat_id TEXT,
        status TEXT NOT NULL DEFAULT 'Entwurf',
        invoice_id INTEGER,
        approved_by TEXT,
        approved_at TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP)""")
    conn.execute("""CREATE TABLE IF NOT EXISTS invoice_exports (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ts TEXT NOT NULL,
        period TEXT NOT NULL,
        kind TEXT NOT NULL,
        rows INTEGER NOT NULL,
        sha256 TEXT NOT NULL,
        exported_by TEXT)""")
    conn.commit()


def get_draft(conn, draft_id):
    cur = conn.execute("SELECT * FROM invoice_drafts WHERE id=?", (draft_id,))
    row = cur.fetchone()
    if not row:
        raise ValueError("Rechnungsentwurf nicht gefunden")
    return dict(zip([d[0] for d in cur.description], row))


def amounts(net, vat_rate):
    vat = round(net * vat_rate / 100, 2)
    return round(net, 2), vat, round(net + vat, 2)


def draft_from_offer(conn, offer_id):
    """Rechnungsentwurf aus angenommenem Angebot (Auftrag). Sparte und Absender kommen vom Kunden."""
    row = conn.execute("""SELECT o.status, o.customer_id, o.description, o.net_total, o.lead_id, c.sparte
                          FROM offers o JOIN customers c ON c.id=o.customer_id WHERE o.id=?""", (offer_id,)).fetchone()
    if not row:
        raise ValueError("Angebot nicht gefunden")
    status, customer_id, desc, net, lead_id, sparte = row
    if status != "angenommen":
        raise ValueError("Rechnung erst nach angenommenem Angebot (Auftrag)")
    if sparte not in ISSUERS:
        raise ValueError("Sparte des Kunden zuerst auf Sicherheit oder Facility setzen")
    if conn.execute("SELECT 1 FROM invoice_drafts WHERE offer_id=?", (offer_id,)).fetchone():
        raise ValueError("Zu diesem Angebot gibt es bereits einen Rechnungsentwurf")
    cur = conn.execute("""INSERT INTO invoice_drafts(offer_id, lead_id, customer_id, sparte, description, net_total)
                          VALUES(?,?,?,?,?,?)""", (offer_id, lead_id, customer_id, sparte, desc, net))
    conn.commit()
    return cur.lastrowid


def update_draft(conn, draft_id, **fields):
    """Felder eines Entwurfs ändern; der Steuersatz folgt immer aus dem Steuerfall."""
    if get_draft(conn, draft_id)["status"] != "Entwurf":
        raise ValueError("Freigegebene Rechnungen sind unveränderlich – Korrektur nur per Storno")
    unknown = set(fields) - set(EDITABLE)
    if unknown:
        raise ValueError(f"Unbekannte Felder: {', '.join(sorted(unknown))}")
    if "tax_case" in fields:
        if fields["tax_case"] not in TAX_CASES:
            raise ValueError("Unbekannter Steuerfall")
        fields["vat_rate"] = TAX_CASES[fields["tax_case"]][0]
    for key, value in fields.items():  # key ist durch EDITABLE/vat_rate begrenzt, kein Nutzereingabe-SQL
        conn.execute(f"UPDATE invoice_drafts SET {key}=? WHERE id=?", (value, draft_id))
    conn.commit()


def check(conn, draft_id, today=None):
    """Pflichtangaben nach § 14 Abs. 4 UStG (und § 14a bei § 13b). Liste von (Angabe, ok, Hinweis)."""
    d = get_draft(conn, draft_id)
    issuer = ISSUERS.get(d["sparte"], {})
    cust = conn.execute("SELECT company, street, zip_city FROM customers WHERE id=?", (d["customer_id"],)).fetchone() or ("", "", "")
    rate, note, needs_reason = TAX_CASES.get(d["tax_case"], (None, "", False))
    net, vat, gross = amounts(d["net_total"] or 0, d["vat_rate"])
    today = today or date.today()
    service_ok = bool(d["service_date"]) and d["service_date"] <= today.isoformat()
    results = [
        ("Name und Anschrift Leistender", bool(issuer.get("name") and issuer.get("street") and issuer.get("city")),
         issuer.get("name", "Sparte ohne Absender")),
        ("USt-IdNr. oder Steuernummer", bool(issuer.get("vat_id")), issuer.get("vat_id", "")),
        ("Name Leistungsempfänger", bool(cust[0]), cust[0] or "fehlt"),
        ("Anschrift Leistungsempfänger", bool(cust[1] and cust[2]), "Straße und PLZ/Ort im Kunden pflegen"),
        ("Leistungsbeschreibung", bool((d["description"] or "").strip()), "Art und Umfang der Leistung"),
        ("Leistungszeitpunkt/-zeitraum", service_ok, "Leistungsdatum angeben (nicht in der Zukunft)"),
        ("Nettoentgelt", net > 0, f"{net:.2f} €"),
        ("Steuersatz passend zum Steuerfall", rate is not None and rate == d["vat_rate"], d["tax_case"]),
        ("Steuerbetrag und Brutto", True, f"{d['vat_rate']:g} % = {vat:.2f} €, brutto {gross:.2f} €"),
    ]
    if needs_reason:
        results.append(("Begründung Steuerfall", bool((d["tax_reason"] or "").strip()),
                        "Rechtsgrundlage/Begründung angeben (mit Steuerberater klären)"))
    if d["tax_case"].startswith("Reverse Charge"):
        results.append(("USt-IdNr. Leistungsempfänger", bool((d["recipient_vat_id"] or "").strip()), "bei § 13b erforderlich"))
    if note:
        results.append(("Pflichthinweis", True, note))
    results.append(("Rechnungsdatum und fortlaufende Nummer", True, "werden bei Freigabe vergeben"))
    return results


def approve(conn, draft_id, approved_by, role, confirmed, today=None):
    """Freigabe: nur Inhaber/Buchhaltung, nur mit Bestätigung und vollständigen Pflichtangaben.

    Erst jetzt entsteht die Rechnung in invoices (Status 'offen') mit fortlaufender Nummer.
    """
    if role not in FINANCE_ROLES:
        raise PermissionError("Freigabe nur durch Inhaber/Admin oder Buchhaltung")
    if not confirmed:
        raise ValueError("Freigabe muss ausdrücklich bestätigt werden")
    d = get_draft(conn, draft_id)
    if d["status"] != "Entwurf":
        raise ValueError("Entwurf ist bereits freigegeben")
    missing = [name for name, ok, _ in check(conn, draft_id, today) if not ok]
    if missing:
        raise ValueError("Pflichtangaben fehlen: " + ", ".join(missing))
    today = today or date.today()
    net, vat, gross = amounts(d["net_total"], d["vat_rate"])
    note = TAX_CASES[d["tax_case"]][1]
    text = d["description"] + (f" – {note}" if note else "") + (f" ({d['tax_reason']})" if d["tax_reason"] else "")
    if d["recipient_vat_id"]:
        text += f" – USt-IdNr. Leistungsempfänger {d['recipient_vat_id']}"
    invoice_no = next_number_from([r[0] for r in conn.execute("SELECT invoice_no FROM invoices")], "RE-")
    cur = conn.execute("""INSERT INTO invoices(invoice_no, customer_id, invoice_date, service_date, due_date, description,
                          net_total, vat_rate, vat_total, gross_total, paid_amount, status)
                          VALUES(?,?,?,?,?,?,?,?,?,?,0,'offen')""",
                       (invoice_no, d["customer_id"], today.isoformat(), d["service_date"],
                        (today + timedelta(days=int(d["due_days"]))).isoformat(), text, net, d["vat_rate"], vat, gross))
    invoice_id = cur.lastrowid
    conn.execute("""INSERT INTO invoice_items(invoice_id, position, description, quantity, unit, unit_price, total)
                    VALUES(?,1,?,1,'pauschal',?,?)""", (invoice_id, d["description"], net, net))
    conn.execute("UPDATE invoice_drafts SET status='freigegeben', invoice_id=?, approved_by=?, approved_at=? WHERE id=?",
                 (invoice_id, approved_by, datetime.now().isoformat(timespec="seconds"), draft_id))
    conn.commit()
    return invoice_id, invoice_no


def export_test(conn, period, exported_by=""):
    """Testexport (CSV) der freigegebenen Stufe-6-Rechnungen eines Monats (YYYY-MM).

    Bucht nichts, ändert keine Rechnung; Konten bleiben leer (Steuerberater). Protokolliert nur den Export.
    """
    datetime.strptime(period, "%Y-%m")
    rows = conn.execute("""SELECT i.invoice_date, i.invoice_no, c.company, d.sparte, d.tax_case, i.net_total, i.vat_rate,
                                  i.vat_total, i.gross_total
                           FROM invoice_drafts d JOIN invoices i ON i.id=d.invoice_id JOIN customers c ON c.id=i.customer_id
                           WHERE d.status='freigegeben' AND substr(i.invoice_date,1,7)=? ORDER BY i.invoice_no""",
                        (period,)).fetchall()
    buf = io.StringIO()
    buf.write("# TESTEXPORT - keine Buchung. Konten und Format vor Nutzung mit dem Steuerberater abstimmen.\n")
    w = csv.writer(buf, delimiter=";")
    w.writerow(["Belegdatum", "Belegnummer", "Kunde", "Sparte", "Steuerfall", "Netto", "Steuersatz", "Steuer", "Brutto",
                "Erloeskonto", "Debitorenkonto"])
    for r in rows:
        w.writerow([*r[:5], f"{r[5]:.2f}", f"{r[6]:g}", f"{r[7]:.2f}", f"{r[8]:.2f}", "", ""])
    data = buf.getvalue()
    conn.execute("INSERT INTO invoice_exports(ts, period, kind, rows, sha256, exported_by) VALUES(?,?,?,?,?,?)",
                 (datetime.now().isoformat(timespec="seconds"), period, "Testexport", len(rows),
                  hashlib.sha256(data.encode("utf-8")).hexdigest(), exported_by))
    conn.commit()
    return data, len(rows)
