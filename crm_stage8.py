"""CRM Stufe 8: Betrieb – 2FA (TOTP), Sicherung vor Migration mit Probelauf und Rückfall, Systemzustand, Wartung.

Kommandozeile (für Aufgabenplanung/Cron auf dem Zielrechner):
    python crm_stage8.py health    # Systemzustand, Exit-Code 1 bei Fehler (für Monitoring)
    python crm_stage8.py backup    # konsistente Sicherung + Prüfung, protokolliert in backups/automation_log
    python crm_stage8.py migrate   # Probe-Migration auf Kopie, dann Sicherung + echte Migration, Rückfall bei Fehler
Eine produktive Umstellung braucht weiterhin eine gesonderte technische Freigabe.
"""
import base64
import hashlib
import hmac
import importlib.util
import secrets
import shutil
import sqlite3
import struct
import sys
import tempfile
import time
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import quote

import crm_stage7

TOTP_STEP = 30
TOTP_DIGITS = 6
BACKUP_MAX_AGE_DAYS = 7
DEFAULT_ADMIN_PASSWORD = "admin123"  # nur zum Erkennen des unsicheren Auslieferungszustands
ADMIN_ROLES = ("admin", "inhaber/admin", "inhaber", "administrator")
# Module, die app.py importiert, die im Repository aber fehlen (Stand Stufe 8)
OPTIONAL_MODULES = ("extensions_v2_polish", "extensions_v2_prod1", "extensions_v2_prod2", "extensions_v2_remote_access",
                    "extensions_v2_security", "extensions_v2_systemplus", "extensions_v2_sysutils",
                    "extensions_v2_ultra", "extensions_v2_xtra")


# ── 2FA (TOTP nach RFC 6238, SHA-1, 6 Stellen, 30 s – kompatibel mit gängigen Authenticator-Apps) ──

def ensure_tables(conn):
    conn.execute("""CREATE TABLE IF NOT EXISTS two_factor_secrets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        totp_secret TEXT NOT NULL,
        enabled INTEGER DEFAULT 0,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP)""")
    conn.commit()


def new_secret():
    return base64.b32encode(secrets.token_bytes(20)).decode("ascii")


def totp(secret, at=None):
    key = base64.b32decode(secret.upper() + "=" * (-len(secret) % 8))
    counter = int((time.time() if at is None else at) // TOTP_STEP)
    digest = hmac.new(key, struct.pack(">Q", counter), hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    code = (struct.unpack(">I", digest[offset:offset + 4])[0] & 0x7FFFFFFF) % 10 ** TOTP_DIGITS
    return str(code).zfill(TOTP_DIGITS)


def verify_totp(secret, code, at=None, window=1):
    """Code prüfen; ±window Zeitschritte Toleranz für Uhrabweichung."""
    code = str(code or "").strip()
    if not secret or len(code) != TOTP_DIGITS or not code.isdigit():
        return False
    now = time.time() if at is None else at
    return any(hmac.compare_digest(totp(secret, now + i * TOTP_STEP), code) for i in range(-window, window + 1))


def provisioning_uri(username, secret, issuer="Byblos CRM"):
    return (f"otpauth://totp/{quote(issuer)}:{quote(username)}?secret={secret}&issuer={quote(issuer)}"
            f"&digits={TOTP_DIGITS}&period={TOTP_STEP}")


def start_2fa(conn, username):
    """Neues Geheimnis anlegen (noch nicht aktiv). Ersetzt ein nicht aktiviertes, nie ein aktives."""
    row = conn.execute("SELECT enabled FROM two_factor_secrets WHERE username=?", (username,)).fetchone()
    if row and row[0] == 1:
        raise ValueError("2FA ist bereits aktiv – zuerst deaktivieren")
    secret = new_secret()
    conn.execute("""INSERT INTO two_factor_secrets(username, totp_secret, enabled) VALUES(?,?,0)
                    ON CONFLICT(username) DO UPDATE SET totp_secret=excluded.totp_secret, enabled=0""", (username, secret))
    conn.commit()
    return secret


def _secret(conn, username):
    row = conn.execute("SELECT totp_secret, enabled FROM two_factor_secrets WHERE username=?", (username,)).fetchone()
    if not row:
        raise ValueError("2FA wurde nicht eingerichtet")
    return row


def confirm_2fa(conn, username, code, at=None):
    """Aktivieren erst nach korrektem Code aus der App – so wird niemand ausgesperrt."""
    secret, _ = _secret(conn, username)
    if not verify_totp(secret, code, at):
        raise ValueError("Code falsch – Uhrzeit des Telefons prüfen und erneut versuchen")
    conn.execute("UPDATE two_factor_secrets SET enabled=1 WHERE username=?", (username,))
    conn.commit()


def disable_2fa(conn, username, code, at=None):
    secret, enabled = _secret(conn, username)
    if enabled and not verify_totp(secret, code, at):
        raise ValueError("Zum Deaktivieren ist ein gültiger Code nötig")
    conn.execute("DELETE FROM two_factor_secrets WHERE username=?", (username,))
    conn.commit()


# ── Sicherung, Probe-Migration, Rückfall ──

def _sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _copy_db(src, dst):
    """Konsistente Kopie über die SQLite-Backup-API (auch bei laufender Anwendung)."""
    s, d = sqlite3.connect(src), sqlite3.connect(dst)
    try:
        s.backup(d)
    finally:
        s.close()
        d.close()


def _connect(db_path):
    return sqlite3.connect(db_path)


def _has(c, table):
    return c.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone() is not None


def table_counts(db_path):
    c = _connect(db_path)
    try:
        tables = [r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")]
        return {t: c.execute(f'SELECT COUNT(*) FROM "{t}"').fetchone()[0] for t in tables}  # Namen aus sqlite_master
    finally:
        c.close()


def schema_signature(db_path):
    c = _connect(db_path)
    try:
        return sorted(r[0] or "" for r in c.execute("SELECT sql FROM sqlite_master WHERE name NOT LIKE 'sqlite_%'"))
    finally:
        c.close()


def integrity_ok(db_path):
    c = _connect(db_path)
    try:
        return c.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
    except sqlite3.DatabaseError:
        return False
    finally:
        c.close()


def backup_db(db_path, backup_dir, note="manuell"):
    """Sicherung anlegen, prüfen und in backups protokollieren (Grundlage für den Nachweis in Stufe 7)."""
    backup_dir = Path(backup_dir)
    backup_dir.mkdir(parents=True, exist_ok=True)
    target = backup_dir / f"byblos_crm_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}.db"
    _copy_db(db_path, target)
    if not integrity_ok(target):
        raise RuntimeError(f"Sicherung beschädigt: {target}")
    digest = _sha256(target)
    c = _connect(db_path)
    try:
        if _has(c, "backups"):
            c.execute("INSERT INTO backups(file_path, file_size, sha256, note) VALUES(?,?,?,?)",
                      (str(target), target.stat().st_size, digest, note))
            c.commit()
    finally:
        c.close()
    return target, digest


def restore_db(backup_path, db_path):
    """Sicherung zurückspielen; der bisherige Stand bleibt als *.vor-wiederherstellung-* erhalten."""
    if not integrity_ok(backup_path):
        raise RuntimeError("Sicherung ist beschädigt – Wiederherstellung abgebrochen")
    db_path = Path(db_path)
    if db_path.exists():
        shutil.copy2(db_path, db_path.with_name(db_path.name + f".vor-wiederherstellung-{datetime.now():%Y%m%d%H%M%S%f}"))
    _copy_db(backup_path, db_path)


def _check_no_loss(before, after):
    lost = {t: (n, after.get(t)) for t, n in before.items() if after.get(t, -1) < n}
    if lost:
        raise RuntimeError(f"Migration würde Daten verlieren: {lost}")


def migrate_safely(db_path, backup_dir, migrate_fn):
    """migrate_fn(pfad) zuerst auf einer Kopie testen; nur bei Erfolg sichern und echt ausführen, sonst Rückfall.

    Die echte Datenbank bleibt unverändert, wenn der Probelauf scheitert.
    """
    before, schema_before = table_counts(db_path), schema_signature(db_path)
    with tempfile.TemporaryDirectory() as tmp:
        trial = Path(tmp) / "probe.db"
        _copy_db(db_path, trial)
        migrate_fn(trial)
        if not integrity_ok(trial):
            raise RuntimeError("Probelauf: Datenbank nach Migration beschädigt")
        _check_no_loss(before, table_counts(trial))
        if schema_signature(trial) == schema_before:
            return {"status": "keine Änderung", "backup": None}
    backup, digest = backup_db(db_path, backup_dir, note="vor Migration")
    try:
        migrate_fn(Path(db_path))
        if not integrity_ok(db_path):
            raise RuntimeError("Datenbank nach Migration beschädigt")
        _check_no_loss(before, table_counts(db_path))
    except Exception:
        restore_db(backup, db_path)
        raise
    return {"status": "migriert", "backup": str(backup), "sha256": digest}


# ── Systemzustand (Monitoring) ──

def _backup_check(last, now):
    if not last:
        return ("Letzte Sicherung", "fehler", "keine Sicherung protokolliert")
    ts, path, digest = last
    age = now - datetime.fromisoformat(str(ts).replace("T", " ")[:19])
    if not path or not Path(path).exists():
        return ("Letzte Sicherung", "fehler", f"Datei fehlt: {path}")
    if digest and _sha256(path) != digest:
        return ("Letzte Sicherung", "fehler", "Prüfsumme stimmt nicht")
    return ("Letzte Sicherung", "warnung" if age > timedelta(days=BACKUP_MAX_AGE_DAYS) else "ok", f"{ts} ({age.days} Tage alt)")


def health_report(db_path, verify_password=None, now=None):
    """Liste von (Prüfung, Status 'ok'|'warnung'|'fehler', Detail)."""
    now = now or datetime.now()
    if not integrity_ok(db_path):
        return [("Datenbank-Integrität", "fehler", "PRAGMA integrity_check meldet Fehler")]
    out = [("Datenbank-Integrität", "ok", f"{Path(db_path).stat().st_size / 1e6:.1f} MB")]
    c = _connect(db_path)
    try:
        if _has(c, "users"):
            row = c.execute("SELECT password_hash FROM users WHERE username='admin' AND active=1").fetchone()
            if verify_password:
                default = bool(row) and verify_password(DEFAULT_ADMIN_PASSWORD, row[0])
                out.append(("Standardpasswort admin", "fehler" if default else "ok",
                            "admin123 ist noch aktiv – sofort ändern" if default else "nicht aktiv"))
            admins = [u for u, r in c.execute("SELECT username, role FROM users WHERE active=1")
                      if (r or "").strip().lower() in ADMIN_ROLES]
            with_2fa = ({r[0] for r in c.execute("SELECT username FROM two_factor_secrets WHERE enabled=1")}
                        if _has(c, "two_factor_secrets") else set())
            missing = [a for a in admins if a not in with_2fa]
            out.append(("2FA für Admins", "warnung" if missing else "ok",
                        f"ohne 2FA: {', '.join(missing)}" if missing else "alle Admins mit 2FA"))
        last = (c.execute("SELECT created_at, file_path, sha256 FROM backups ORDER BY created_at DESC, id DESC LIMIT 1").fetchone()
                if _has(c, "backups") else None)
        out.append(_backup_check(last, now))
        for job in crm_stage7.JOBS:
            s = crm_stage7.job_status(c, job, now)
            out.append((f"Automation: {s['label']}", "ok" if s["status"].startswith("aktiv") else "warnung", s["status"]))
    finally:
        c.close()
    missing_mods = [m for m in OPTIONAL_MODULES if importlib.util.find_spec(m) is None]
    out.append(("Erweiterungsmodule", "warnung" if missing_mods else "ok",
                f"fehlen: {', '.join(missing_mods)}" if missing_mods else "vollständig"))
    return out


def log_run(db_path, job, status, details=""):
    c = _connect(db_path)
    try:
        if _has(c, "automation_log"):
            c.execute("INSERT INTO automation_log(job_name, status, details) VALUES(?,?,?)", (job, status, details))
            c.commit()
    finally:
        c.close()


def main(argv):
    base = Path(__file__).resolve().parent
    db_path, backup_dir = base / "byblos_crm.db", base / "backups"
    cmd = argv[1] if len(argv) > 1 else "health"
    if cmd == "health":
        from app import verify_password  # noqa: PLC0415 – nur für die Kommandozeile
        report = health_report(db_path, verify_password)
        for name, status, detail in report:
            print(f"[{status.upper():7}] {name}: {detail}")
        return 1 if any(s == "fehler" for _, s, _ in report) else 0
    if cmd == "backup":
        try:
            target, digest = backup_db(db_path, backup_dir, note="Wartung")
        except Exception as exc:  # Fehler protokollieren, damit Stufe 7 ihn anzeigt
            log_run(db_path, "backup_job", "error", str(exc))
            print(f"Sicherung fehlgeschlagen: {exc}")
            return 1
        log_run(db_path, "backup_job", "ok", f"{target.name} {digest[:12]}")
        print(f"Sicherung: {target} (SHA-256 {digest})")
        return 0
    if cmd == "migrate":
        import app  # noqa: PLC0415

        def run_init(path):
            original = app.DB_PATH
            app.DB_PATH = Path(path)
            try:
                app.init_db()
            finally:
                app.DB_PATH = original
        print(migrate_safely(db_path, backup_dir, run_init))
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
