"""Tests für CRM Stufe 3 (Posteingang → Lead → Angebot → Auftrag). Nur synthetische Testdaten."""
import hashlib
import sqlite3
from datetime import date, datetime, timedelta, timezone

import pytest

import crm_stage1 as s1
import crm_stage2 as s2
import crm_stage3 as s3
from test_crm_stage1 import BASE_SCHEMA

OFFERS = """CREATE TABLE offers (id INTEGER PRIMARY KEY AUTOINCREMENT, offer_no TEXT UNIQUE, customer_id INTEGER,
    offer_date TEXT NOT NULL, valid_until TEXT, description TEXT, net_total REAL DEFAULT 0, vat_rate REAL DEFAULT 19,
    vat_total REAL DEFAULT 0, gross_total REAL DEFAULT 0, status TEXT DEFAULT 'entwurf', notes TEXT, pdf_path TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP)"""
ARCHIVE = """CREATE TABLE archive_documents (id INTEGER PRIMARY KEY AUTOINCREMENT, doc_type TEXT, ref_no TEXT, file_name TEXT,
    file_path TEXT, sha256 TEXT, archived_at TEXT DEFAULT CURRENT_TIMESTAMP, locked INTEGER DEFAULT 1, note TEXT)"""


def eml(sender="einkauf@lager.example", to="info@byblos-sicherheit.de", subject="Anfrage Objektschutz", msgid="<1@lager.example>"):
    return (f"From: Einkauf <{sender}>\r\nTo: {to}\r\nSubject: {subject}\r\nMessage-ID: {msgid}\r\n"
            "Date: Fri, 20 Nov 2026 09:15:00 +0100\r\nContent-Type: text/plain; charset=utf-8\r\n\r\n"
            "Wir benötigen ein Angebot für die Bewachung unseres Lagers.\r\n").encode("utf-8")


@pytest.fixture
def db():
    c = sqlite3.connect(":memory:")
    c.execute(BASE_SCHEMA)
    c.execute(OFFERS)
    c.execute(ARCHIVE)
    s1.ensure_columns(c)
    s2.ensure_tables(c)
    s3.ensure_tables(c)
    yield c
    c.close()


def customer(c, email="info@lager.example", km=20):
    return c.execute("INSERT INTO customers(company,email,distance_km,sparte) VALUES('Lager Synthetik',?,?,'Sicherheit')",
                     (email, km)).lastrowid


def test_full_pipeline_from_inbox_to_order(db, tmp_path):
    cid = customer(db)
    msg_id, created = s3.import_message(db, eml(), "info@byblos-sicherheit.de", tmp_path)
    assert created
    msg = db.execute("SELECT sparte, customer_id, status FROM inbox_messages WHERE id=?", (msg_id,)).fetchone()
    assert msg == ("Sicherheit", cid, "zugeordnet")

    lead_id = s3.lead_from_message(db, msg_id, "Objektschutz Lager")
    offer_id = s3.offer_from_lead(db, lead_id, 1000.0, today=date(2026, 11, 20))
    for status in ("geprüft", "geeignet", "Entwurf", "gesendet"):
        s2.transition(db, lead_id, status)
    s3.accept_offer(db, offer_id)

    assert db.execute("SELECT status FROM leads WHERE id=?", (lead_id,)).fetchone()[0] == "gewonnen"
    assert db.execute("SELECT offer_no, gross_total, status, lead_id FROM offers WHERE id=?", (offer_id,)).fetchone() == \
        ("ANG-0001", 1190.0, "angenommen", lead_id)
    assert db.execute("SELECT status FROM inbox_messages WHERE id=?", (msg_id,)).fetchone()[0] == "Auftrag"
    steps = [s[0] for s in s3.trace(db, msg_id)]
    assert steps[:3] == ["Eingang", "Archiv", "Kunde"] and "Angebot" in steps and steps[-1] == "Status"
    sent = db.execute("SELECT sender FROM lead_events WHERE lead_id=? AND to_status='gesendet'", (lead_id,)).fetchone()[0]
    assert sent == "info@byblos-sicherheit.de"


def test_facility_mailbox_maps_to_facility(db, tmp_path):
    msg_id, _ = s3.import_message(db, eml(to="info@byblos-reinigung.de"), "info@byblos-reinigung.de", tmp_path)
    assert db.execute("SELECT sparte, status FROM inbox_messages WHERE id=?", (msg_id,)).fetchone() == ("Facility", "neu")


def test_foreign_mailbox_rejected(db, tmp_path):
    with pytest.raises(ValueError, match="Firmenpostfächer"):
        s3.import_message(db, eml(), "byblossicherheit@gmail.com", tmp_path)


def test_same_message_not_imported_twice(db, tmp_path):
    first, created1 = s3.import_message(db, eml(), "info@byblos-sicherheit.de", tmp_path)
    second, created2 = s3.import_message(db, eml(), "info@byblos-sicherheit.de", tmp_path)
    assert (first, created1, created2) == (second, True, False)
    assert db.execute("SELECT COUNT(*) FROM inbox_messages").fetchone()[0] == 1


def test_original_archived_with_hash(db, tmp_path):
    raw = eml()
    s3.import_message(db, raw, "info@byblos-sicherheit.de", tmp_path)
    sha = hashlib.sha256(raw).hexdigest()
    assert (tmp_path / "inbox" / f"{sha}.eml").read_bytes() == raw
    assert db.execute("SELECT sha256, locked FROM archive_documents").fetchone() == (sha, 1)


def test_unknown_sender_needs_assignment_before_lead(db, tmp_path):
    msg_id, _ = s3.import_message(db, eml(sender="neu@unbekannt.example"), "info@byblos-sicherheit.de", tmp_path)
    with pytest.raises(ValueError, match="zuordnen"):
        s3.lead_from_message(db, msg_id, "x")
    s3.assign_customer(db, msg_id, customer(db, "kontakt@unbekannt.example"))
    assert s3.lead_from_message(db, msg_id, "x") > 0
    with pytest.raises(ValueError, match="bereits Lead"):
        s3.lead_from_message(db, msg_id, "x")


def test_accept_requires_offer_sent(db, tmp_path):
    customer(db)
    msg_id, _ = s3.import_message(db, eml(), "info@byblos-sicherheit.de", tmp_path)
    offer_id = s3.offer_from_lead(db, s3.lead_from_message(db, msg_id, "x"), 500.0)
    with pytest.raises(ValueError, match="gesendet"):
        s3.accept_offer(db, offer_id)


def test_offer_requires_positive_amount(db, tmp_path):
    customer(db)
    msg_id, _ = s3.import_message(db, eml(), "info@byblos-sicherheit.de", tmp_path)
    with pytest.raises(ValueError, match="größer als 0"):
        s3.offer_from_lead(db, s3.lead_from_message(db, msg_id, "x"), 0)


class FakeImap:
    """Ersatz für imaplib.IMAP4_SSL; prüft, dass nur lesend zugegriffen wird."""
    calls = []

    def __init__(self, host, port):
        self.messages = [eml(msgid="<a@x>"), eml(msgid="<b@x>")]

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def login(self, user, password):
        FakeImap.calls.append(("login", user))

    def select(self, folder, readonly=False):
        FakeImap.calls.append(("select", folder, readonly))

    def search(self, charset, criterion):
        return "OK", [b"1 2"]

    def fetch(self, num, spec):
        FakeImap.calls.append(("fetch", spec))
        return "OK", [(b"1 (BODY[] {10}", self.messages[int(num) - 1]), b")"]


def test_fetch_imap_is_readonly_and_idempotent(db, tmp_path):
    FakeImap.calls = []
    assert s3.fetch_imap(db, "imap.example", "u", "p", "info@byblos-sicherheit.de", tmp_path, imap_cls=FakeImap) == (2, 0)
    assert s3.fetch_imap(db, "imap.example", "u", "p", "info@byblos-sicherheit.de", tmp_path, imap_cls=FakeImap) == (0, 2)
    assert ("select", "INBOX", True) in FakeImap.calls
    assert all(c[1] == "(BODY.PEEK[])" for c in FakeImap.calls if c[0] == "fetch")


def test_parse_eml_without_message_id_uses_hash(db):
    raw = eml(msgid="")
    data = s3.parse_eml(raw.replace(b"Message-ID: \r\n", b""))
    assert data["message_id"].startswith("<sha256-") and data["from_addr"] == "einkauf@lager.example"
