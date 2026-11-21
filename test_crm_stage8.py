"""Tests für CRM Stufe 8 (Betrieb): 2FA, Sicherung, Probe-Migration mit Rückfall, Systemzustand.

Nur synthetische Testdatenbanken in tmp_path.
"""
import sqlite3
from datetime import datetime

import pytest

import crm_stage8 as s8

RFC_SECRET = "GEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQ"  # ASCII "12345678901234567890" (RFC 6238, Anhang B)
NOW = datetime(2026, 11, 21, 8, 0)


@pytest.fixture
def dbfile(tmp_path):
    path = tmp_path / "crm.db"
    c = sqlite3.connect(path)
    c.executescript("""
        CREATE TABLE users (id INTEGER PRIMARY KEY, username TEXT UNIQUE, password_hash TEXT, role TEXT, active INTEGER DEFAULT 1);
        CREATE TABLE customers (id INTEGER PRIMARY KEY, company TEXT);
        CREATE TABLE backups (id INTEGER PRIMARY KEY AUTOINCREMENT, created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                              file_path TEXT, file_size INTEGER, sha256 TEXT, note TEXT);
        CREATE TABLE automation_log (id INTEGER PRIMARY KEY AUTOINCREMENT, created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                                     job_name TEXT, status TEXT, details TEXT);
        INSERT INTO users(username, password_hash, role) VALUES('admin', 'HASH:admin123', 'Admin'), ('bh', 'HASH:x', 'Buchhaltung');
        INSERT INTO customers(company) VALUES('A'), ('B'), ('C');
    """)
    s8.ensure_tables(c)
    c.commit()
    c.close()
    return path


def fake_verify(password, stored):
    return stored == f"HASH:{password}"


def wrong_code(secret, at):
    valid = {s8.totp(secret, at + i * s8.TOTP_STEP) for i in (-1, 0, 1)}
    return next(c for c in ("000000", "111111", "222222", "333333") if c not in valid)


@pytest.mark.parametrize("t,code", [(59, "287082"), (1111111109, "081804"), (1234567890, "005924"), (2000000000, "279037")])
def test_totp_matches_rfc6238_vectors(t, code):
    assert s8.totp(RFC_SECRET, t) == code
    assert s8.verify_totp(RFC_SECRET, code, at=t)


def test_totp_rejects_wrong_old_and_malformed_codes():
    assert s8.verify_totp(RFC_SECRET, s8.totp(RFC_SECRET, 1000), at=1000 + 30)  # ein Schritt Toleranz
    assert not s8.verify_totp(RFC_SECRET, s8.totp(RFC_SECRET, 1000), at=1000 + 120)
    for bad in ("", "12345", "abcdef", None, "1234567"):
        assert not s8.verify_totp(RFC_SECRET, bad, at=1000)


def test_2fa_only_active_after_confirmed_code(dbfile):
    c = sqlite3.connect(dbfile)
    secret = s8.start_2fa(c, "admin")
    assert c.execute("SELECT enabled FROM two_factor_secrets WHERE username='admin'").fetchone()[0] == 0
    with pytest.raises(ValueError, match="Code falsch"):
        s8.confirm_2fa(c, "admin", wrong_code(secret, 5000), at=5000)
    s8.confirm_2fa(c, "admin", s8.totp(secret, 5000), at=5000)
    assert c.execute("SELECT enabled FROM two_factor_secrets WHERE username='admin'").fetchone()[0] == 1
    with pytest.raises(ValueError, match="bereits aktiv"):
        s8.start_2fa(c, "admin")
    with pytest.raises(ValueError, match="gültiger Code"):
        s8.disable_2fa(c, "admin", "", at=5000)
    s8.disable_2fa(c, "admin", s8.totp(secret, 6000), at=6000)
    assert c.execute("SELECT COUNT(*) FROM two_factor_secrets").fetchone()[0] == 0
    assert s8.provisioning_uri("admin", secret).startswith("otpauth://totp/Byblos%20CRM:admin?secret=")


def test_backup_and_restore_round_trip(dbfile, tmp_path):
    target, digest = s8.backup_db(dbfile, tmp_path / "bk")
    c = sqlite3.connect(dbfile)
    assert c.execute("SELECT sha256, note FROM backups").fetchone() == (digest, "manuell")
    c.execute("DELETE FROM customers")
    c.commit()
    c.close()
    s8.restore_db(target, dbfile)
    assert s8.table_counts(dbfile)["customers"] == 3
    assert list(tmp_path.glob("crm.db.vor-wiederherstellung-*")), "vorheriger Stand muss erhalten bleiben"


def add_column(path):
    c = sqlite3.connect(path)
    c.execute("ALTER TABLE customers ADD COLUMN sparte TEXT")
    c.commit()
    c.close()


def test_migration_without_change_needs_no_backup(dbfile, tmp_path):
    assert s8.migrate_safely(dbfile, tmp_path / "bk", lambda p: None) == {"status": "keine Änderung", "backup": None}
    assert not (tmp_path / "bk").exists()


def test_migration_backs_up_then_applies(dbfile, tmp_path):
    result = s8.migrate_safely(dbfile, tmp_path / "bk", add_column)
    assert result["status"] == "migriert"
    c = sqlite3.connect(dbfile)
    assert "sparte" in {r[1] for r in c.execute("PRAGMA table_info(customers)")}
    assert c.execute("SELECT note FROM backups ORDER BY id DESC").fetchone()[0] == "vor Migration"


def test_data_loss_is_caught_in_trial_and_real_db_untouched(dbfile, tmp_path):
    def lossy(path):
        c = sqlite3.connect(path)
        c.execute("ALTER TABLE customers ADD COLUMN x TEXT")
        c.execute("DELETE FROM customers WHERE id=1")
        c.commit()
        c.close()
    before = s8.schema_signature(dbfile)
    with pytest.raises(RuntimeError, match="Daten verlieren"):
        s8.migrate_safely(dbfile, tmp_path / "bk", lossy)
    assert s8.schema_signature(dbfile) == before and s8.table_counts(dbfile)["customers"] == 3


def test_failure_on_real_db_rolls_back(dbfile, tmp_path):
    calls = []

    def flaky(path):
        calls.append(path)
        add_column(path)
        if len(calls) == 2:  # Probelauf ok, echter Lauf scheitert danach
            raise RuntimeError("Abbruch mitten in der Migration")
    with pytest.raises(RuntimeError, match="Abbruch"):
        s8.migrate_safely(dbfile, tmp_path / "bk", flaky)
    assert "sparte" not in {r[1] for r in sqlite3.connect(dbfile).execute("PRAGMA table_info(customers)")}


def status(report, name):
    return next(s for n, s, _ in report if n == name)


def test_health_report_flags_real_risks(dbfile, tmp_path):
    report = s8.health_report(dbfile, fake_verify, NOW)
    assert status(report, "Datenbank-Integrität") == "ok"
    assert status(report, "Standardpasswort admin") == "fehler"
    assert status(report, "2FA für Admins") == "warnung"
    assert status(report, "Letzte Sicherung") == "fehler"
    assert status(report, "Automation: Datensicherung") == "warnung"

    s8.backup_db(dbfile, tmp_path / "bk")
    c = sqlite3.connect(dbfile)
    c.execute("UPDATE users SET password_hash='HASH:neu' WHERE username='admin'")
    c.commit()
    secret = s8.start_2fa(c, "admin")
    s8.confirm_2fa(c, "admin", s8.totp(secret, 7000), at=7000)
    c.close()
    report = s8.health_report(dbfile, fake_verify)
    assert status(report, "Standardpasswort admin") == "ok"
    assert status(report, "2FA für Admins") == "ok"
    assert status(report, "Letzte Sicherung") == "ok"


def test_tampered_backup_is_detected(dbfile, tmp_path):
    target, _ = s8.backup_db(dbfile, tmp_path / "bk")
    with open(target, "ab") as f:
        f.write(b"x")
    assert status(s8.health_report(dbfile), "Letzte Sicherung") == "fehler"


def test_page_sources_match_app_dispatch():
    """Jede Seite, die aus einem der unvollständigen Module lädt, steht in PAGE_SOURCES (erster Treffer gewinnt)."""
    import re
    from pathlib import Path
    src = Path(__file__).with_name("app.py").read_text(encoding="utf-8")
    found = {}
    for block in src.split("\n    elif page ")[1:]:
        body = block.split("\n    elif ")[0]
        names = re.findall(r'"([^"]+)"', block.split(":", 1)[0])
        imp = re.search(r"from (%s) import (\w+)" % "|".join(s8.OPTIONAL_MODULES), body)
        for name in names if imp else []:
            found.setdefault(name, (imp.group(1), imp.group(2)))
    assert found == s8.PAGE_SOURCES


def test_missing_pages_are_hidden_and_empty_sections_dropped():
    s8.page_available.cache_clear()
    sections = {"A": ["Kunden", "Mein Bereich"], "B": ["GPS-Stempeluhr"], "C": ["Intelligenter Import"]}
    assert s8.available_sections(sections) == {"A": ["Kunden"]}, "prod1 existiert, aber ohne Seitenfunktion"


def test_cli_backup_command_logs_run(dbfile, tmp_path, monkeypatch):
    monkeypatch.setattr(s8, "__file__", str(tmp_path / "crm_stage8.py"))
    dbfile.rename(tmp_path / "byblos_crm.db")
    assert s8.main(["crm_stage8.py", "backup"]) == 0
    c = sqlite3.connect(tmp_path / "byblos_crm.db")
    assert c.execute("SELECT job_name, status FROM automation_log").fetchone() == ("backup_job", "ok")
    assert c.execute("SELECT note FROM backups").fetchone()[0] == "Wartung"
