"""CRM Stufe 3: Posteingang → Zuordnung → Lead → Angebot → Auftrag, revisionssicher archiviert.

Liest Postfächer nur (IMAP readonly, BODY.PEEK); verschickt und löscht nichts.
"""
import email
import hashlib
import imaplib
from datetime import date, timedelta
from email import policy
from email.utils import getaddresses, parseaddr, parsedate_to_datetime
from pathlib import Path

import crm_stage1
import crm_stage2
from numbering import next_number_from

MAILBOXES = {addr: sparte for sparte, addr in crm_stage2.SENDERS.items()}
INBOX_STATUSES = ("neu", "zugeordnet", "Lead", "Angebot", "Auftrag", "ignoriert")
INBOX_ROLES = ("Admin", "Manager", "Inhaber/Admin", "Vertrieb")
EXCERPT_CHARS = 4000


def ensure_tables(conn):
    conn.execute("""CREATE TABLE IF NOT EXISTS inbox_messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        mailbox TEXT NOT NULL,
        sparte TEXT NOT NULL,
        message_id TEXT UNIQUE NOT NULL,
        from_addr TEXT,
        subject TEXT,
        received_at TEXT,
        body_excerpt TEXT,
        sha256 TEXT,
        customer_id INTEGER REFERENCES customers(id),
        lead_id INTEGER REFERENCES leads(id),
        offer_id INTEGER,
        status TEXT NOT NULL DEFAULT 'neu',
        created_at TEXT DEFAULT CURRENT_TIMESTAMP)""")
    if conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='offers'").fetchone():
        cols = {r[1] for r in conn.execute("PRAGMA table_info(offers)")}
        if "lead_id" not in cols:
            conn.execute("ALTER TABLE offers ADD COLUMN lead_id INTEGER")
    conn.commit()


def _body_text(msg):
    part = msg.get_body(preferencelist=("plain", "html"))
    if part is None:
        return ""
    try:
        return part.get_content()
    except (LookupError, ValueError):
        return part.get_payload(decode=True).decode("utf-8", "replace")


def parse_eml(raw):
    """Rohe E-Mail (bytes) in ein Dict mit den Feldern für inbox_messages umwandeln."""
    msg = email.message_from_bytes(raw, policy=policy.default)
    received = None
    if msg["Date"]:
        try:
            received = parsedate_to_datetime(str(msg["Date"])).strftime("%Y-%m-%d %H:%M:%S")
        except (TypeError, ValueError):
            received = None
    sha = hashlib.sha256(raw).hexdigest()
    return {
        "message_id": str(msg["Message-ID"] or "").strip() or f"<sha256-{sha}>",
        "from_addr": parseaddr(str(msg["From"] or ""))[1].lower(),
        "to_addrs": [a[1].lower() for a in getaddresses([str(msg["To"] or ""), str(msg["Cc"] or "")]) if a[1]],
        "subject": str(msg["Subject"] or ""),
        "received_at": received,
        "body_excerpt": _body_text(msg)[:EXCERPT_CHARS],
        "sha256": sha,
    }


def _archive(conn, raw, sha, archive_dir, ref):
    target = Path(archive_dir) / "inbox" / f"{sha}.eml"
    target.parent.mkdir(parents=True, exist_ok=True)
    if not target.exists():
        target.write_bytes(raw)
    if conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='archive_documents'").fetchone():
        conn.execute("INSERT INTO archive_documents(doc_type,ref_no,file_name,file_path,sha256,locked,note) VALUES(?,?,?,?,?,1,?)",
                     ("E-Mail-Eingang", ref, target.name, str(target), sha, "Original, unverändert"))


def _match_customer(conn, from_addr):
    cur = conn.execute("SELECT * FROM customers")
    cols = [d[0] for d in cur.description]
    rows = [dict(zip(cols, r)) for r in cur.fetchall()]
    hits = crm_stage1.find_duplicates_in(rows, "", from_addr)
    return hits[0][0] if hits else None


def import_message(conn, raw, mailbox, archive_dir):
    """E-Mail übernehmen. Gibt (id, neu_angelegt) zurück; dieselbe Message-ID wird nicht doppelt angelegt."""
    mailbox = (mailbox or "").strip().lower()
    if mailbox not in MAILBOXES:
        raise ValueError(f"Nur Firmenpostfächer erlaubt: {', '.join(MAILBOXES)}")
    data = parse_eml(raw)
    existing = conn.execute("SELECT id FROM inbox_messages WHERE message_id=?", (data["message_id"],)).fetchone()
    if existing:
        return existing[0], False
    customer_id = _match_customer(conn, data["from_addr"])
    cur = conn.execute(
        """INSERT INTO inbox_messages(mailbox,sparte,message_id,from_addr,subject,received_at,body_excerpt,sha256,customer_id,status)
           VALUES(?,?,?,?,?,?,?,?,?,?)""",
        (mailbox, MAILBOXES[mailbox], data["message_id"], data["from_addr"], data["subject"], data["received_at"],
         data["body_excerpt"], data["sha256"], customer_id, "zugeordnet" if customer_id else "neu"))
    _archive(conn, raw, data["sha256"], archive_dir, f"Eingang #{cur.lastrowid}")
    conn.commit()
    return cur.lastrowid, True


def fetch_imap(conn, host, user, password, mailbox, archive_dir, port=993, folder="INBOX", limit=50,
               imap_cls=imaplib.IMAP4_SSL):
    """Neueste E-Mails nur lesend abrufen (Mails bleiben ungelesen). Gibt (neu, bereits_vorhanden) zurück."""
    new = known = 0
    with imap_cls(host, port) as imap:
        imap.login(user, password)
        imap.select(folder, readonly=True)
        _, data = imap.search(None, "ALL")
        for num in data[0].split()[-limit:]:
            _, parts = imap.fetch(num, "(BODY.PEEK[])")
            raw = next((p[1] for p in parts if isinstance(p, tuple)), None)
            if raw:
                _, created = import_message(conn, raw, mailbox, archive_dir)
                new, known = (new + 1, known) if created else (new, known + 1)
    return new, known


def _message(conn, msg_id):
    cur = conn.execute("SELECT * FROM inbox_messages WHERE id=?", (msg_id,))
    row = cur.fetchone()
    if not row:
        raise ValueError("Eingang nicht gefunden")
    return dict(zip([d[0] for d in cur.description], row))


def assign_customer(conn, msg_id, customer_id):
    if not conn.execute("SELECT id FROM customers WHERE id=?", (customer_id,)).fetchone():
        raise ValueError("Kunde nicht gefunden")
    conn.execute("UPDATE inbox_messages SET customer_id=?, status=CASE WHEN status='neu' THEN 'zugeordnet' ELSE status END WHERE id=?",
                 (customer_id, msg_id))
    conn.commit()


def lead_from_message(conn, msg_id, title):
    """Aus einer Kundenanfrage einen Lead machen (Rechtsgrundlage: Anfrage des Kunden)."""
    msg = _message(conn, msg_id)
    if not msg["customer_id"]:
        raise ValueError("Eingang zuerst einem Kunden zuordnen")
    if msg["lead_id"]:
        raise ValueError(f"Aus diesem Eingang wurde bereits Lead {msg['lead_id']} erstellt")
    lead_id = crm_stage2.create_lead(conn, msg["customer_id"], msg["sparte"], title or msg["subject"] or "Anfrage",
                                     "E-Mail", "Anfrage des Kunden", msg["from_addr"], f"Posteingang #{msg_id}")
    conn.execute("UPDATE inbox_messages SET lead_id=?, status='Lead' WHERE id=?", (lead_id, msg_id))
    conn.commit()
    return lead_id


def offer_from_lead(conn, lead_id, net_total, description="", vat_rate=19.0, valid_days=30, today=None):
    """Angebotsentwurf zum Lead anlegen (verknüpft über offers.lead_id)."""
    cur = conn.execute("SELECT customer_id, title FROM leads WHERE id=?", (lead_id,))
    lead = cur.fetchone()
    if not lead:
        raise ValueError("Lead nicht gefunden")
    if net_total is None or net_total <= 0:
        raise ValueError("Nettobetrag muss größer als 0 sein")
    today = today or date.today()
    offer_no = next_number_from([r[0] for r in conn.execute("SELECT offer_no FROM offers")], "ANG-")
    vat = round(net_total * vat_rate / 100, 2)
    cur = conn.execute(
        """INSERT INTO offers(offer_no,customer_id,offer_date,valid_until,description,net_total,vat_rate,vat_total,gross_total,status,lead_id)
           VALUES(?,?,?,?,?,?,?,?,?,'entwurf',?)""",
        (offer_no, lead[0], today.isoformat(), (today + timedelta(days=valid_days)).isoformat(), description or lead[1],
         round(net_total, 2), vat_rate, vat, round(net_total + vat, 2), lead_id))
    offer_id = cur.lastrowid
    conn.execute("UPDATE inbox_messages SET offer_id=?, status='Angebot' WHERE lead_id=?", (offer_id, lead_id))
    conn.commit()
    return offer_id


def accept_offer(conn, offer_id, note=""):
    """Angebot angenommen = Auftrag: Angebot 'angenommen', Lead 'gewonnen', Eingang 'Auftrag'."""
    cur = conn.execute("SELECT lead_id, status FROM offers WHERE id=?", (offer_id,))
    row = cur.fetchone()
    if not row:
        raise ValueError("Angebot nicht gefunden")
    lead_id = row[0]
    status = conn.execute("SELECT status FROM leads WHERE id=?", (lead_id,)).fetchone()
    if not status or status[0] not in {"gesendet", "Antwort", "nachfassen"}:
        raise ValueError("Angebot zuerst im Lead als gesendet protokollieren")
    if status[0] == "gesendet":
        crm_stage2.transition(conn, lead_id, "Antwort", "Kunde hat geantwortet")
    crm_stage2.transition(conn, lead_id, "gewonnen", note or f"Angebot {offer_id} angenommen")
    conn.execute("UPDATE offers SET status='angenommen' WHERE id=?", (offer_id,))
    conn.execute("UPDATE inbox_messages SET status='Auftrag' WHERE offer_id=?", (offer_id,))
    conn.commit()


def trace(conn, msg_id):
    """Nachvollziehbarer Weg eines Eingangs: Liste von (Schritt, Detail)."""
    msg = _message(conn, msg_id)
    steps = [("Eingang", f"{msg['received_at'] or msg['created_at']} an {msg['mailbox']} von {msg['from_addr']}: {msg['subject']}"),
             ("Archiv", f"SHA-256 {msg['sha256']}")]
    if msg["customer_id"]:
        name = conn.execute("SELECT company FROM customers WHERE id=?", (msg["customer_id"],)).fetchone()
        steps.append(("Kunde", name[0] if name else f"#{msg['customer_id']}"))
    if msg["lead_id"]:
        steps += [("Lead", f"{r[0]}: {r[1] or '–'} → {r[2]}" + (f" (Absender {r[3]})" if r[3] else ""))
                  for r in conn.execute("SELECT ts, from_status, to_status, sender FROM lead_events WHERE lead_id=? ORDER BY id",
                                        (msg["lead_id"],))]
    if msg["offer_id"]:
        o = conn.execute("SELECT offer_no, gross_total, status FROM offers WHERE id=?", (msg["offer_id"],)).fetchone()
        if o:
            steps.append(("Angebot", f"{o[0]} über {o[1]:.2f} € brutto – {o[2]}"))
    steps.append(("Status", msg["status"]))
    return steps
