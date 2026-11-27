"""Tests für den Mitarbeiterbereich: Zuordnung Konto ↔ Mitarbeiter, nur eigene Daten sichtbar. Synthetische Daten."""
import sqlite3
from pathlib import Path

import pytest

import crm_portal as p
import crm_stage5
import crm_stage8


@pytest.fixture
def db():
    c = sqlite3.connect(":memory:")
    c.executescript("""
        CREATE TABLE users (id INTEGER PRIMARY KEY, username TEXT UNIQUE, password_hash TEXT, role TEXT, active INTEGER DEFAULT 1);
        CREATE TABLE employees (id INTEGER PRIMARY KEY, employee_no TEXT, name TEXT, hourly_rate REAL, active INTEGER DEFAULT 1);
        CREATE TABLE service_objects (id INTEGER PRIMARY KEY, object_name TEXT, address TEXT, access_notes TEXT);
        CREATE TABLE field_shifts (id INTEGER PRIMARY KEY, object_id INTEGER, employee_id INTEGER, shift_date TEXT,
            start_time TEXT, end_time TEXT, status TEXT, instructions TEXT, contact_person TEXT);
        CREATE TABLE shifts (id INTEGER PRIMARY KEY, shift_date TEXT, start_time TEXT, end_time TEXT, employee_id INTEGER,
            location TEXT, status TEXT, notes TEXT);
        CREATE TABLE service_reports (id INTEGER PRIMARY KEY, shift_id INTEGER, report_date TEXT, work_done TEXT,
            incidents TEXT, status TEXT);
        INSERT INTO users(username, role) VALUES('anna', 'Mitarbeiter'), ('ben', 'Mitarbeiter'), ('chef', 'Admin');
        INSERT INTO employees(id, name, hourly_rate, active) VALUES(1, 'Anna Test', 15, 1), (2, 'Ben Test', 15, 1), (3, 'Alt', 15, 0);
        INSERT INTO service_objects VALUES(1, 'Lager Nord', 'Teststr. 1', 'Schlüssel an Pforte');
        INSERT INTO field_shifts VALUES(1, 1, 1, '2026-12-01', '22:00', '06:00', 'geplant', 'Rundgang stündlich', 'Herr Muster');
        INSERT INTO field_shifts VALUES(2, 1, 2, '2026-12-01', '06:00', '14:00', 'geplant', 'Ben-Aufgabe', NULL);
        INSERT INTO shifts VALUES(1, '2026-11-30', '08:00', '16:00', 1, 'Büro', 'geplant', 'Altdienst');
        INSERT INTO service_reports VALUES(1, 1, '2026-12-02', 'Rundgänge erledigt', 'keine', 'Entwurf');
        INSERT INTO service_reports VALUES(2, 2, '2026-12-02', 'Ben-Bericht', '', 'Entwurf');
    """)
    p.ensure_columns(c)
    yield c
    c.close()


def test_unlinked_account_sees_nothing(db):
    assert p.my_employee(db, "anna") is None
    assert p.my_shifts(db, "anna", "2026-01-01", "2026-12-31") == []
    assert p.my_reports(db, "anna") == []


def test_linked_account_sees_only_own_shifts_and_reports(db):
    p.link_user(db, "anna", 1)
    shifts = p.my_shifts(db, "anna", "2026-11-01", "2026-12-31")
    assert [(s["quelle"], s["id"]) for s in shifts] == [("Dienstplan", 1), ("Einsatzplanung", 1)]
    assert shifts[1]["objekt"] == "Lager Nord" and shifts[1]["hinweise"] == "Schlüssel an Pforte"
    assert all("Ben" not in str(s) for s in shifts)
    assert [r["id"] for r in p.my_reports(db, "anna")] == [1]
    assert all(set(s) == set(p.SHIFT_KEYS) for s in shifts), "keine Lohn- oder Personaldaten"


def test_link_rules(db):
    with pytest.raises(ValueError, match="inaktiv"):
        p.link_user(db, "anna", 3)
    with pytest.raises(ValueError, match="Benutzer"):
        p.link_user(db, "niemand", 1)
    p.link_user(db, "anna", 1)
    with pytest.raises(ValueError, match="bereits dem Konto „anna“"):
        p.link_user(db, "ben", 1)
    p.link_user(db, "anna", None)
    assert p.my_employee(db, "anna") is None


def test_deactivated_account_or_employee_loses_access(db):
    p.link_user(db, "anna", 1)
    db.execute("UPDATE employees SET active=0 WHERE id=1")
    assert p.my_shifts(db, "anna", "2026-01-01", "2026-12-31") == []
    db.execute("UPDATE employees SET active=1 WHERE id=1")
    db.execute("UPDATE users SET active=0 WHERE username='anna'")
    assert p.my_employee(db, "anna") is None


def test_staff_role_sees_my_area_page():
    from test_crm_stage5 import SECTIONS
    crm_stage8.page_available.cache_clear()
    assert crm_stage8.page_available("Mein Bereich"), "Seite darf nicht mehr ausgeblendet sein"
    assert crm_stage5.can_access_page("Mitarbeiter", SECTIONS, "Mein Bereich")
    src = Path(__file__).with_name("app.py").read_text(encoding="utf-8")
    assert "from extensions_v2_portal import page_my_area" in src
