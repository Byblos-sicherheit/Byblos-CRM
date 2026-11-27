"""Mitarbeiterbereich: Benutzerkonto ↔ Mitarbeiter und nur die eigenen Einsätze und Leistungsnachweise.

Die Mitarbeiter-ID kommt ausschließlich aus users.employee_id des angemeldeten Kontos, nie aus einer Eingabe.
Keine Lohn-, Stundensatz- oder Personalaktendaten.
"""
from datetime import date, timedelta

SHIFT_KEYS = ("quelle", "id", "datum", "von", "bis", "objekt", "adresse", "hinweise", "aufgabe", "ansprechpartner", "status")


def _has(conn, table):
    return conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone() is not None


def _cols(conn, table):
    return {r[1] for r in conn.execute(f'PRAGMA table_info("{table}")')}  # Tabellenname fest im Code


def ensure_columns(conn):
    if _has(conn, "users") and "employee_id" not in _cols(conn, "users"):
        conn.execute("ALTER TABLE users ADD COLUMN employee_id INTEGER")
        conn.commit()


def link_user(conn, username, employee_id):
    """Konto einem aktiven Mitarbeiter zuordnen (None = Zuordnung lösen). Ein Mitarbeiter gehört höchstens einem Konto."""
    if not conn.execute("SELECT 1 FROM users WHERE username=?", (username,)).fetchone():
        raise ValueError("Benutzer nicht gefunden")
    if employee_id is not None:
        if not conn.execute("SELECT 1 FROM employees WHERE id=? AND active=1", (employee_id,)).fetchone():
            raise ValueError("Mitarbeiter nicht gefunden oder inaktiv")
        other = conn.execute("SELECT username FROM users WHERE employee_id=? AND username<>?", (employee_id, username)).fetchone()
        if other:
            raise ValueError(f"Mitarbeiter ist bereits dem Konto „{other[0]}“ zugeordnet")
    conn.execute("UPDATE users SET employee_id=? WHERE username=?", (employee_id, username))
    conn.commit()


def my_employee(conn, username):
    """(id, name) des dem Konto zugeordneten aktiven Mitarbeiters oder None."""
    if not username or "employee_id" not in _cols(conn, "users"):
        return None
    return conn.execute("""SELECT e.id, e.name FROM users u JOIN employees e ON e.id=u.employee_id
                           WHERE u.username=? AND u.active=1 AND e.active=1""", (username,)).fetchone()


def my_shifts(conn, username, start=None, end=None):
    """Eigene Einsätze aus Einsatzplanung (field_shifts) und Dienstplan (shifts), nach Datum sortiert."""
    emp = my_employee(conn, username)
    if not emp:
        return []
    start = start or (date.today() - timedelta(days=14)).isoformat()
    end = end or (date.today() + timedelta(days=60)).isoformat()
    rows = []
    if _has(conn, "field_shifts"):
        contact = "f.contact_person" if "contact_person" in _cols(conn, "field_shifts") else "NULL"
        objects = _has(conn, "service_objects")
        obj_cols = "o.object_name, o.address, o.access_notes" if objects else "NULL, NULL, NULL"
        obj_join = "LEFT JOIN service_objects o ON o.id=f.object_id" if objects else ""
        rows += [dict(zip(SHIFT_KEYS, r)) for r in conn.execute(
            f"""SELECT 'Einsatzplanung', f.id, f.shift_date, f.start_time, f.end_time, {obj_cols},
                       f.instructions, {contact}, f.status
                FROM field_shifts f {obj_join}
                WHERE f.employee_id=? AND f.shift_date BETWEEN ? AND ?""", (emp[0], start, end))]
    if _has(conn, "shifts"):
        rows += [dict(zip(SHIFT_KEYS, r)) for r in conn.execute(
            """SELECT 'Dienstplan', id, shift_date, start_time, end_time, location, NULL, NULL, notes, NULL, status
               FROM shifts WHERE employee_id=? AND shift_date BETWEEN ? AND ?""", (emp[0], start, end))]
    return sorted(rows, key=lambda r: (r["datum"] or "", r["von"] or ""))


def my_reports(conn, username):
    """Eigene Leistungsnachweise (über die Einsatzplanung)."""
    emp = my_employee(conn, username)
    if not emp or not (_has(conn, "service_reports") and _has(conn, "field_shifts")):
        return []
    return [dict(zip(("id", "datum", "einsatz", "taetigkeit", "vorkommnisse", "status"), r)) for r in conn.execute(
        """SELECT r.id, r.report_date, r.shift_id, r.work_done, r.incidents, r.status
           FROM service_reports r JOIN field_shifts f ON f.id=r.shift_id
           WHERE f.employee_id=? ORDER BY r.report_date DESC, r.id DESC""", (emp[0],))]
