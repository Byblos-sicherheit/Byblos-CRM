"""Tests für CRM Stufe 4 (Einsatzprüfung). Nur synthetische Testdaten."""
import sqlite3

import pytest

import crm_stage1 as s1
import crm_stage4 as s4
from test_crm_stage1 import BASE_SCHEMA
from test_crm_stage3 import OFFERS

FIELD = [
    "CREATE TABLE field_employees (id INTEGER PRIMARY KEY AUTOINCREMENT, full_name TEXT NOT NULL, active INTEGER DEFAULT 1)",
    """CREATE TABLE employee_qualifications (id INTEGER PRIMARY KEY AUTOINCREMENT, employee_id INTEGER, qualification TEXT,
       valid_until TEXT, status TEXT DEFAULT 'gültig')""",
    """CREATE TABLE service_objects (id INTEGER PRIMARY KEY AUTOINCREMENT, customer_id INTEGER, object_name TEXT NOT NULL,
       service_type TEXT, address TEXT, access_notes TEXT, risk_notes TEXT, active INTEGER DEFAULT 1)""",
    """CREATE TABLE field_shifts (id INTEGER PRIMARY KEY AUTOINCREMENT, object_id INTEGER, employee_id INTEGER, service_type TEXT,
       shift_date TEXT, start_time TEXT, end_time TEXT, status TEXT DEFAULT 'geplant', instructions TEXT, problem_note TEXT)""",
]
DAY = "2026-12-01"


@pytest.fixture
def db():
    c = sqlite3.connect(":memory:")
    for sql in [BASE_SCHEMA, OFFERS] + FIELD:
        c.execute(sql)
    s1.ensure_columns(c)
    s4.ensure_columns(c)
    c.execute("INSERT INTO customers(company,distance_km) VALUES('Lager Synthetik',20)")          # id 1
    c.execute("INSERT INTO customers(company,distance_km) VALUES('Fern GmbH',120)")              # id 2
    c.execute("INSERT INTO service_objects(customer_id,object_name) VALUES(1,'Lagerhalle Nord')")  # id 1
    c.execute("INSERT INTO service_objects(customer_id,object_name) VALUES(2,'Halle Fern')")       # id 2
    c.execute("INSERT INTO field_employees(full_name) VALUES('Test Wache')")                       # id 1 mit §34a
    c.execute("INSERT INTO field_employees(full_name) VALUES('Test Reinigung')")                   # id 2 ohne
    c.execute("INSERT INTO employee_qualifications(employee_id,qualification,valid_until) VALUES(1,'Sachkunde §34a GewO',NULL)")
    yield c
    c.close()


def plan(c, emp=1, obj=1, service="Sicherheitsdienst", day=DAY, start="18:00", end="02:00", contact="Herr Test", **kw):
    return s4.plan_shift(c, emp, obj, service, day, start, end, contact, **kw)


def test_trial_assignment_documented_with_times_contact_and_permissions(db):
    db.execute("INSERT INTO offers(offer_no,customer_id,offer_date,status) VALUES('ANG-0001',1,'2026-11-20','angenommen')")
    sid = plan(db, contact_phone="0151 000000", access_permissions="Schlüssel Tor Süd, Alarmanlage Bereich A", offer_id=1)
    row = db.execute("""SELECT shift_date,start_time,end_time,contact_person,contact_phone,access_permissions,offer_id
                        FROM field_shifts WHERE id=?""", (sid,)).fetchone()
    assert row == (DAY, "18:00", "02:00", "Herr Test", "0151 000000", "Schlüssel Tor Süd, Alarmanlage Bereich A", 1)


def test_security_requires_34a(db):
    with pytest.raises(ValueError, match="34a"):
        plan(db, emp=2)


def test_cleaning_needs_no_34a(db):
    assert plan(db, emp=2, service="Reinigung", start="06:00", end="10:00") > 0


def test_expired_qualification_rejected(db):
    db.execute("UPDATE employee_qualifications SET valid_until='2026-01-01'")
    with pytest.raises(ValueError, match="34a"):
        plan(db)


def test_expiry_date_schema_variant_supported():
    c = sqlite3.connect(":memory:")
    c.execute("CREATE TABLE employee_qualifications (id INTEGER PRIMARY KEY, employee_id INTEGER, qualification TEXT, expiry_date TEXT)")
    c.execute("INSERT INTO employee_qualifications(employee_id,qualification,expiry_date) VALUES(1,'Unterrichtung §34a','2027-12-31')")
    assert s4._qualified(c, 1, DAY)


@pytest.mark.parametrize("start,end,expected", [
    ("08:00", "20:00", "höchstens 10 h"),
    ("08:00", "08:00", "gleich"),
    ("8 Uhr", "16:00", "Zeiten"),
])
def test_time_rules(db, start, end, expected):
    with pytest.raises(ValueError, match=expected):
        plan(db, start=start, end=end)


def test_missing_contact_rejected(db):
    with pytest.raises(ValueError, match="Ansprechpartner"):
        plan(db, contact=" ")


def test_overlap_rejected_including_overnight(db):
    plan(db)  # 18:00–02:00
    with pytest.raises(ValueError, match="Überschneidung"):
        plan(db, day="2026-12-02", start="01:00", end="05:00")


def test_rest_time_11h(db):
    plan(db)  # endet 02.12. 02:00
    with pytest.raises(ValueError, match="Ruhezeit"):
        plan(db, day="2026-12-02", start="10:00", end="14:00")
    assert plan(db, day="2026-12-02", start="13:00", end="17:00") > 0


def test_cancelled_shift_does_not_block(db):
    sid = plan(db)
    db.execute("UPDATE field_shifts SET status='abgesagt' WHERE id=?", (sid,))
    assert plan(db) > 0


def test_object_outside_radius_rejected(db):
    with pytest.raises(ValueError, match="außerhalb"):
        plan(db, obj=2)


def test_offer_must_be_accepted(db):
    db.execute("INSERT INTO offers(offer_no,customer_id,offer_date,status) VALUES('ANG-0002',1,'2026-11-20','entwurf')")
    with pytest.raises(ValueError, match="nicht angenommen"):
        plan(db, offer_id=1)


def test_other_employee_not_affected(db):
    plan(db)
    db.execute("INSERT INTO employee_qualifications(employee_id,qualification) VALUES(2,'Unterrichtung §34a')")
    assert plan(db, emp=2) > 0
