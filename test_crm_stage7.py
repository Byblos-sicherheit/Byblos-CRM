"""Tests für CRM Stufe 7. Abnahme: Dashboard mit nachvollziehbaren Testwerten und Protokollierung.

Nur synthetische Testdaten mit bekannten Sollwerten.
"""
import hashlib
import json
import sqlite3
from datetime import datetime

import pytest

import crm_stage1 as s1
import crm_stage2 as s2
import crm_stage7 as s7
from test_crm_stage1 import BASE_SCHEMA
from test_crm_stage3 import OFFERS

SHIFTS = """CREATE TABLE field_shifts (id INTEGER PRIMARY KEY AUTOINCREMENT, object_id INTEGER, employee_id INTEGER,
    service_type TEXT, shift_date TEXT, start_time TEXT, end_time TEXT, status TEXT DEFAULT 'geplant')"""
LOG = """CREATE TABLE automation_log (id INTEGER PRIMARY KEY AUTOINCREMENT, created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    job_name TEXT, status TEXT, details TEXT)"""
BACKUPS = "CREATE TABLE backups (id INTEGER PRIMARY KEY AUTOINCREMENT, created_at TEXT, file_path TEXT, sha256 TEXT)"
NOW = datetime(2026, 11, 21, 8, 0)


@pytest.fixture
def db():
    c = sqlite3.connect(":memory:")
    for sql in (BASE_SCHEMA, OFFERS, SHIFTS, LOG, BACKUPS):
        c.execute(sql)
    s1.ensure_columns(c)
    s2.ensure_tables(c)
    s7.ensure_tables(c)
    a = c.execute("INSERT INTO customers(company, sparte) VALUES('Kunde A','Sicherheit')").lastrowid
    b = c.execute("INSERT INTO customers(company, sparte) VALUES('Kunde B','Facility')").lastrowid
    leads = [c.execute("INSERT INTO leads(customer_id, sparte, title, channel, status) VALUES(?,?,?,?,?)",
                       (cid, sp, "Test", "E-Mail", st)).lastrowid
             for cid, sp, st in ((a, "Sicherheit", "gesendet"), (b, "Facility", "nachfassen"), (a, "Sicherheit", "verloren"))]
    events = [  # (lead, ts, to_status, legal_basis)
        (leads[0], "2026-11-03T09:00:00+00:00", "geprüft", None),
        (leads[1], "2026-11-04T09:00:00+00:00", "geprüft", None),
        (leads[2], "2026-10-30T09:00:00+00:00", "geprüft", None),  # außerhalb
        (leads[0], "2026-11-05T09:00:00+00:00", "gesendet", "Bestandskunde"),
        (leads[1], "2026-11-06T09:00:00+00:00", "gesendet", "Keine"),  # unzulässig – zählt nicht
    ]
    c.executemany("INSERT INTO lead_events(lead_id, ts, to_status, legal_basis) VALUES(?,?,?,?)", events)
    offers = [  # (no, customer, date, net, status)
        ("ANG-1", a, "2026-10-10", 500, "angenommen"),
        ("ANG-2", a, "2026-11-10", 800, "angenommen"),  # Folgeauftrag
        ("ANG-3", b, "2026-11-12", 300, "angenommen"),  # Erstauftrag
        ("ANG-4", b, "2026-11-15", 100, "entwurf"),
    ]
    c.executemany("INSERT INTO offers(offer_no, customer_id, offer_date, net_total, status) VALUES(?,?,?,?,?)", offers)
    c.executemany("INSERT INTO field_shifts(shift_date, start_time, end_time, status) VALUES(?,?,?,?)", [
        ("2026-11-02", "08:00", "16:00", "geplant"),
        ("2026-11-03", "22:00", "06:00", "geplant"),  # Nachtschicht 8 Std.
        ("2026-11-04", "08:00", "12:00", "abgesagt"),
        ("2026-11-05", "", "", "geplant"),  # unvollständig
    ])
    c.commit()
    yield c
    c.close()


def by_name(values):
    return {k["name"]: k for k in values}


def test_kpis_match_known_test_values_and_point_to_records(db):
    k = by_name(s7.kpis(db, "2026-11-01", "2026-11-30"))
    assert k["Neu geprüfte Leads"]["value"] == 2 and k["Neu geprüfte Leads"]["ids"] == [1, 2]
    assert k["Zulässige Kontaktaufnahmen"]["value"] == 1 and k["Zulässige Kontaktaufnahmen"]["ids"] == [1]
    assert k["Offene Antworten (aktuell)"]["ids"] == [1, 2]
    assert k["Angebote"]["value"] == 3 and "1200.00" in k["Angebote"]["note"]
    assert k["Folgeaufträge"]["ids"] == [2]
    hours = k["Geplante Einsatzstunden"]
    assert hours["value"] == 16.0 and hours["ids"] == [1, 2]
    assert s7.UNKNOWN in hours["note"], "Auslastung ohne Soll-Stunden darf nicht erfunden werden"
    assert all(v["source"] for v in k.values())


def test_snapshot_is_logged_with_checksum(db):
    snap_id, values = s7.snapshot(db, "2026-11-01", "2026-11-30", "inhaber")
    data, sha, by = db.execute("SELECT data, sha256, created_by FROM kpi_snapshots WHERE id=?", (snap_id,)).fetchone()
    assert json.loads(data) == json.loads(json.dumps(values, ensure_ascii=False, sort_keys=True))
    assert sha == hashlib.sha256(data.encode("utf-8")).hexdigest() and by == "inhaber"


def test_invalid_period_rejected(db):
    with pytest.raises(ValueError):
        s7.kpis(db, "2026-11-30", "2026-11-01")
    with pytest.raises(ValueError):
        s7.kpis(db, "gestern", "2026-11-01")


def test_missing_tables_do_not_invent_values():
    c = sqlite3.connect(":memory:")
    k = by_name(s7.kpis(c, "2026-11-01", "2026-11-30"))
    assert list(k) == ["Geplante Einsatzstunden"] and k["Geplante Einsatzstunden"]["value"] == 0.0


def log(db, job, ts, status="ok"):
    db.execute("INSERT INTO automation_log(created_at, job_name, status) VALUES(?,?,?)", (ts, job, status))


def test_automation_only_active_with_proof(db):
    assert s7.job_status(db, "mark_overdue", NOW)["status"] == "nicht eingerichtet"
    log(db, "mark_overdue", "2026-11-21 06:00:00")
    assert s7.job_status(db, "mark_overdue", NOW)["status"].startswith("nicht nachgewiesen"), "ein Knopfdruck ist keine Automation"
    log(db, "mark_overdue", "2026-11-19 06:00:00")
    log(db, "mark_overdue", "2026-11-20 06:00:00")
    assert s7.job_status(db, "mark_overdue", NOW)["status"] == "aktiv (nachgewiesen)"
    assert s7.job_status(db, "mark_overdue", datetime(2026, 11, 24, 8))["status"] == "überfällig"
    log(db, "mark_overdue", "2026-11-21 07:00:00", "error")
    assert s7.job_status(db, "mark_overdue", NOW)["status"] == "Fehler beim letzten Lauf"


def test_backup_status_from_backups_table(db):
    for d in ("2026-11-07", "2026-11-14", "2026-11-20"):
        db.execute("INSERT INTO backups(created_at) VALUES(?)", (f"{d} 03:00:00",))
    assert s7.job_status(db, "backup", NOW)["status"] == "aktiv (nachgewiesen)"
