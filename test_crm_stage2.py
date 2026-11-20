"""Tests für CRM Stufe 2 (Leads, Statuskette, Versandprüfung). Nur synthetische Testdaten."""
import sqlite3
from datetime import datetime, timedelta, timezone

import pytest

import crm_stage1 as s1
import crm_stage2 as s2
from test_crm_stage1 import BASE_SCHEMA

T0 = datetime(2026, 11, 20, 10, 0, 0, tzinfo=timezone.utc)


@pytest.fixture
def db():
    c = sqlite3.connect(":memory:")
    c.execute(BASE_SCHEMA)
    s1.ensure_columns(c)
    s2.ensure_tables(c)
    yield c
    c.close()


def customer(c, company, km, email="info@kunde.example"):
    cur = c.execute("INSERT INTO customers(company,email,distance_km,sparte) VALUES(?,?,?,'Sicherheit')", (company, email, km))
    return cur.lastrowid


def to_draft(c, lead_id):
    for status in ("geprüft", "geeignet", "Entwurf"):
        s2.transition(c, lead_id, status, now=T0)


def email_lead(c, cid, sparte="Sicherheit", legal="Öffentliche Ausschreibung / Portal", recipient="einkauf@kunde.example"):
    lid = s2.create_lead(c, cid, sparte, "Objektschutz Lager", "E-Mail", legal, recipient)
    to_draft(c, lid)
    return lid


def test_happy_path_records_sender_by_sparte(db):
    lid = email_lead(db, customer(db, "Kunde A", 20))
    assert s2.check_send(db, lid, T0) == []
    s2.transition(db, lid, "gesendet", now=T0)
    ev = db.execute("SELECT sender, legal_basis, recipient FROM lead_events WHERE to_status='gesendet'").fetchone()
    assert ev == ("info@byblos-sicherheit.de", "Öffentliche Ausschreibung / Portal", "einkauf@kunde.example")


def test_facility_uses_reinigung_sender(db):
    lid = email_lead(db, customer(db, "Kunde F", 20), sparte="Facility")
    s2.transition(db, lid, "gesendet", now=T0)
    assert db.execute("SELECT sender FROM lead_events WHERE to_status='gesendet'").fetchone()[0] == "info@byblos-reinigung.de"


def test_double_application_blocked(db):
    cid = customer(db, "Kunde B", 20)
    first = email_lead(db, cid)
    s2.transition(db, first, "gesendet", now=T0)
    second = email_lead(db, cid)
    later = T0 + timedelta(hours=1)
    with pytest.raises(ValueError, match="Doppelbewerbung"):
        s2.transition(db, second, "gesendet", now=later)


def test_other_sparte_is_not_a_double_application(db):
    cid = customer(db, "Kunde C", 20)
    s2.transition(db, email_lead(db, cid, "Sicherheit"), "gesendet", now=T0)
    other = email_lead(db, cid, "Facility")
    assert s2.check_send(db, other, T0 + timedelta(hours=1)) == []


@pytest.mark.parametrize("km,legal,recipient,expected", [
    (95, "Öffentliche Ausschreibung / Portal", "a@kunde.example", "außerhalb"),
    (None, "Öffentliche Ausschreibung / Portal", "a@kunde.example", "Entfernung des Kunden unbekannt"),
    (75, "Öffentliche Ausschreibung / Portal", "a@kunde.example", "Grenzfall"),
    (20, "Keine", "a@kunde.example", "ohne Rechtsgrundlage"),
    (20, "Öffentliche Ausschreibung / Portal", "", "Empfänger-E-Mail fehlt"),
])
def test_impermissible_send_blocked(db, km, legal, recipient, expected):
    lid = email_lead(db, customer(db, "Kunde D", km), legal=legal, recipient=recipient)
    with pytest.raises(ValueError, match=expected):
        s2.transition(db, lid, "gesendet", now=T0)
    assert db.execute("SELECT status FROM leads WHERE id=?", (lid,)).fetchone()[0] == "Entwurf"


def test_grenzfall_allowed_after_confirmation(db):
    lid = email_lead(db, customer(db, "Kunde G", 75))
    s2.confirm_radius(db, lid)
    assert s2.check_send(db, lid, T0) == []


def test_portal_channel_needs_no_email_legal_basis(db):
    lid = s2.create_lead(db, customer(db, "Kunde P", 20), "Sicherheit", "Ausschreibung Wachdienst", "Vergabeportal")
    to_draft(db, lid)
    assert s2.check_send(db, lid, T0) == []


def test_min_gap_between_sends(db):
    s2.transition(db, email_lead(db, customer(db, "K1", 20, "a@k1.example")), "gesendet", now=T0)
    lid = email_lead(db, customer(db, "K2", 20, "a@k2.example"), recipient="b@k2.example")
    with pytest.raises(ValueError, match="mindestens 60 s"):
        s2.transition(db, lid, "gesendet", now=T0 + timedelta(seconds=30))
    s2.transition(db, lid, "gesendet", now=T0 + timedelta(seconds=61))


def test_blocked_customer_cannot_be_contacted(db):
    cid = customer(db, "Kunde S", 20)
    s2.transition(db, s2.create_lead(db, cid, "Sicherheit", "alt", "Telefon"), "gesperrt", now=T0)
    lid = email_lead(db, cid)
    with pytest.raises(ValueError, match="gesperrt"):
        s2.transition(db, lid, "gesendet", now=T0)


def test_invalid_transition_rejected(db):
    lid = s2.create_lead(db, customer(db, "Kunde T", 20), "Sicherheit", "x", "Telefon")
    with pytest.raises(ValueError, match="nicht erlaubt"):
        s2.transition(db, lid, "gesendet", now=T0)


def test_create_lead_validates_input(db):
    cid = customer(db, "Kunde V", 20)
    with pytest.raises(ValueError, match="Sparte"):
        s2.create_lead(db, cid, "Beide", "x", "Telefon")
    with pytest.raises(ValueError, match="Kanal"):
        s2.create_lead(db, cid, "Sicherheit", "x", "Fax")
    with pytest.raises(ValueError, match="Kunde nicht gefunden"):
        s2.create_lead(db, 999, "Sicherheit", "x", "Telefon")


def test_contact_history_merges_leads_contacts_and_email_log(db):
    db.execute("CREATE TABLE contacts (id INTEGER PRIMARY KEY, customer_id INTEGER, contact_date TEXT, contact_type TEXT, subject TEXT)")
    db.execute("CREATE TABLE email_log (id INTEGER PRIMARY KEY, created_at TEXT, sent_at TEXT, recipient TEXT, subject TEXT, status TEXT)")
    cid = customer(db, "Kunde H", 20, "info@hist.example")
    db.execute("INSERT INTO contacts(customer_id,contact_date,contact_type,subject) VALUES(?,?,?,?)", (cid, "2026-01-05", "Telefon", "Erstgespräch"))
    db.execute("INSERT INTO email_log(created_at,sent_at,recipient,subject,status) VALUES('2026-02-01','2026-02-01','chef@hist.example','Angebot','gesendet')")
    s2.create_lead(db, cid, "Sicherheit", "Objektschutz", "Telefon")
    kinds = [h[0] for h in s2.contact_history(db, cid)]
    assert sorted(kinds) == ["E-Mail", "Kontakt", "Lead"]
