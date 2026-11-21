"""Tests für CRM Stufe 6. Abnahme: Rechnungsentwurf und Testexport, keine echte Buchung ohne Freigabe.

Nur synthetische Testdaten.
"""
import sqlite3
from datetime import date

import pytest

import crm_stage1 as s1
import crm_stage2 as s2
import crm_stage3 as s3
import crm_stage6 as s6
from test_crm_stage1 import BASE_SCHEMA
from test_crm_stage3 import OFFERS

INVOICES = """CREATE TABLE invoices (id INTEGER PRIMARY KEY AUTOINCREMENT, invoice_no TEXT UNIQUE, customer_id INTEGER NOT NULL,
    invoice_date TEXT NOT NULL, service_date TEXT, due_date TEXT, description TEXT, net_total REAL DEFAULT 0,
    vat_rate REAL DEFAULT 19, vat_total REAL DEFAULT 0, gross_total REAL DEFAULT 0, paid_amount REAL DEFAULT 0,
    paid_date TEXT, status TEXT DEFAULT 'offen', pdf_path TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP)"""
ITEMS = """CREATE TABLE invoice_items (id INTEGER PRIMARY KEY AUTOINCREMENT, invoice_id INTEGER NOT NULL, position INTEGER,
    description TEXT NOT NULL, quantity REAL DEFAULT 1, unit TEXT DEFAULT 'Stunden', unit_price REAL DEFAULT 0, total REAL DEFAULT 0)"""
TODAY = date(2026, 11, 21)


@pytest.fixture
def db():
    c = sqlite3.connect(":memory:")
    for sql in (BASE_SCHEMA, OFFERS, INVOICES, ITEMS):
        c.execute(sql)
    s1.ensure_columns(c)
    s2.ensure_tables(c)
    s3.ensure_tables(c)
    s6.ensure_tables(c)
    c.execute("INSERT INTO invoices(invoice_no, customer_id, invoice_date) VALUES('RE-0025', 99, '2026-10-01')")
    yield c
    c.close()


def accepted_offer(c, sparte="Sicherheit", street="Industriestr. 1", status="angenommen"):
    cid = c.execute("INSERT INTO customers(company, street, zip_city, sparte) VALUES('Lager Synthetik', ?, '38440 Wolfsburg', ?)",
                    (street, sparte)).lastrowid
    return c.execute("""INSERT INTO offers(offer_no, customer_id, offer_date, description, net_total, status)
                        VALUES('ANG-0001', ?, '2026-11-01', 'Objektschutz Lager, Oktober 2026', 1000.0, ?)""",
                     (cid, status)).lastrowid


def invoice_count(c):
    return c.execute("SELECT COUNT(*) FROM invoices").fetchone()[0]


def test_draft_is_not_a_booking_until_approved(db):
    draft = s6.draft_from_offer(db, accepted_offer(db))
    s6.update_draft(db, draft, service_date="2026-10-31")
    assert all(ok for _, ok, _ in s6.check(db, draft, TODAY))
    assert invoice_count(db) == 1, "Entwurf darf nicht in invoices (Umsatz, DATEV, Mahnwesen) auftauchen"
    with pytest.raises(ValueError, match="bestätigt"):
        s6.approve(db, draft, "buchhaltung", "Buchhaltung", confirmed=False, today=TODAY)
    with pytest.raises(PermissionError):
        s6.approve(db, draft, "vertrieb", "Vertrieb", confirmed=True, today=TODAY)
    assert invoice_count(db) == 1

    invoice_id, invoice_no = s6.approve(db, draft, "inhaber", "Inhaber/Admin", confirmed=True, today=TODAY)
    assert invoice_no == "RE-0026"
    row = db.execute("SELECT net_total, vat_total, gross_total, status, due_date FROM invoices WHERE id=?", (invoice_id,)).fetchone()
    assert row == (1000.0, 190.0, 1190.0, "offen", "2026-12-05")
    assert db.execute("SELECT total FROM invoice_items WHERE invoice_id=?", (invoice_id,)).fetchone()[0] == 1000.0
    with pytest.raises(ValueError, match="unveränderlich"):
        s6.update_draft(db, draft, net_total=1.0)
    with pytest.raises(ValueError, match="bereits freigegeben"):
        s6.approve(db, draft, "inhaber", "Inhaber/Admin", confirmed=True, today=TODAY)


def test_only_accepted_offers_and_once(db):
    with pytest.raises(ValueError, match="angenommen"):
        s6.draft_from_offer(db, accepted_offer(db, status="entwurf"))
    db.execute("DELETE FROM offers")
    offer = accepted_offer(db)
    s6.draft_from_offer(db, offer)
    with pytest.raises(ValueError, match="bereits"):
        s6.draft_from_offer(db, offer)


def test_issuer_follows_sparte(db):
    with pytest.raises(ValueError, match="Sparte"):
        s6.draft_from_offer(db, accepted_offer(db, sparte="Unbekannt"))
    assert s6.ISSUERS["Facility"]["name"] == "Byblos Reinigung & Hausmeisterservice"
    assert s6.ISSUERS["Facility"]["email"] == "info@byblos-reinigung.de"
    assert s6.ISSUERS["Sicherheit"]["email"] == "info@byblos-sicherheit.de"


def test_missing_mandatory_fields_block_approval(db):
    draft = s6.draft_from_offer(db, accepted_offer(db, street=""))
    s6.update_draft(db, draft, service_date="2026-12-31")  # in der Zukunft
    failed = {name for name, ok, _ in s6.check(db, draft, TODAY) if not ok}
    assert failed == {"Anschrift Leistungsempfänger", "Leistungszeitpunkt/-zeitraum"}
    with pytest.raises(ValueError, match="Pflichtangaben fehlen"):
        s6.approve(db, draft, "inhaber", "Inhaber/Admin", confirmed=True, today=TODAY)
    assert invoice_count(db) == 1


def test_reverse_charge_needs_reason_and_recipient_vat_id(db):
    draft = s6.draft_from_offer(db, accepted_offer(db, sparte="Facility"))
    s6.update_draft(db, draft, service_date="2026-10-31", tax_case="Reverse Charge § 13b UStG")
    assert s6.get_draft(db, draft)["vat_rate"] == 0.0
    failed = {name for name, ok, _ in s6.check(db, draft, TODAY) if not ok}
    assert failed == {"Begründung Steuerfall", "USt-IdNr. Leistungsempfänger"}
    s6.update_draft(db, draft, tax_reason="§ 13b Abs. 2 Nr. 8 UStG", recipient_vat_id="DE000000000")
    invoice_id, _ = s6.approve(db, draft, "bh", "Buchhaltung", confirmed=True, today=TODAY)
    desc, vat, gross = db.execute("SELECT description, vat_total, gross_total FROM invoices WHERE id=?", (invoice_id,)).fetchone()
    assert "Steuerschuldnerschaft des Leistungsempfängers" in desc and "DE000000000" in desc
    assert (vat, gross) == (0.0, 1000.0)


def test_tax_rate_cannot_be_set_freely(db):
    draft = s6.draft_from_offer(db, accepted_offer(db))
    with pytest.raises(ValueError, match="Unbekannte Felder"):
        s6.update_draft(db, draft, vat_rate=5)
    with pytest.raises(ValueError, match="Steuerfall"):
        s6.update_draft(db, draft, tax_case="16 %")


def test_export_is_test_only_and_logged(db):
    draft = s6.draft_from_offer(db, accepted_offer(db))
    s6.update_draft(db, draft, service_date="2026-10-31")
    data, n = s6.export_test(db, "2026-11")
    assert n == 0, "unfreigegebene Entwürfe werden nicht exportiert"
    s6.approve(db, draft, "inhaber", "Inhaber/Admin", confirmed=True, today=TODAY)
    before = db.execute("SELECT * FROM invoices").fetchall()
    data, n = s6.export_test(db, "2026-11", "inhaber")
    assert n == 1 and data.startswith("# TESTEXPORT")
    assert "RE-0026;Lager Synthetik;Sicherheit;Regelsteuersatz 19 %;1000.00;19;190.00;1190.00;;" in data
    assert "RE-0025" not in data, "Altbestand gehört nicht in den Stufe-6-Testexport"
    assert db.execute("SELECT * FROM invoices").fetchall() == before, "Export darf nichts buchen oder ändern"
    assert db.execute("SELECT kind, rows, exported_by FROM invoice_exports ORDER BY id DESC").fetchone() == ("Testexport", 1, "inhaber")
    with pytest.raises(ValueError):
        s6.export_test(db, "November")
