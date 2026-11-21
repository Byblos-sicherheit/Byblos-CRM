"""CRM Stufe 7: Kennzahlen nur aus vorhandenen Daten, nachvollziehbar bis zum Datensatz, protokolliert.

Automationen gelten nur als aktiv, wenn ihre Läufe im Protokoll (automation_log / backups) nachgewiesen sind.
"""
import hashlib
import json
from datetime import date, datetime, timedelta

import crm_stage4

UNKNOWN = "UNBEKANNT / ZU BESTÄTIGEN"
OPEN_REPLY = ("gesendet", "nachfassen")
# Job -> (Bezeichnung, erwarteter Abstand in Stunden). Quelle: automation_log, beim Backup die Tabelle backups.
JOBS = {
    "mark_overdue": ("Überfällige Rechnungen markieren", 24),
    "overdue_reminders": ("Mahnungen vorbereiten", 24),
    "bank_auto_match": ("Bankabgleich", 24),
    "daily_kpis": ("Tageskennzahlen", 24),
    "backup": ("Datensicherung", 168),
}
MIN_PROVEN_RUNS = 3  # an verschiedenen Tagen; ein einzelner Knopfdruck ist kein Nachweis einer Automation


def ensure_tables(conn):
    conn.execute("""CREATE TABLE IF NOT EXISTS kpi_snapshots (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ts TEXT NOT NULL,
        period_start TEXT NOT NULL,
        period_end TEXT NOT NULL,
        created_by TEXT,
        data TEXT NOT NULL,
        sha256 TEXT NOT NULL)""")
    conn.commit()


def _has(conn, table):
    return conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone() is not None


def _kpi(name, value, unit, source, ids, note=""):
    return {"name": name, "value": value, "unit": unit, "source": source, "ids": list(ids), "note": note}


def _event_kpi(conn, name, to_status, start, end, extra=""):
    ids = [r[0] for r in conn.execute(
        f"""SELECT DISTINCT lead_id FROM lead_events WHERE to_status=? AND substr(ts,1,10) BETWEEN ? AND ? {extra}
            ORDER BY lead_id""", (to_status, start, end))]
    return _kpi(name, len(ids), "Leads", f"lead_events → '{to_status}' im Zeitraum", ids)


def _planned_hours(conn, start, end):
    if not _has(conn, "field_shifts"):
        return _kpi("Geplante Einsatzstunden", 0.0, "Std.", "field_shifts", [], "Einsatzplanung noch nicht genutzt")
    hours, ids = 0.0, []
    for sid, day, s, e in conn.execute(
            "SELECT id, shift_date, start_time, end_time FROM field_shifts WHERE shift_date BETWEEN ? AND ? AND status NOT IN ('abgesagt')",
            (start, end)):
        try:
            a, b = crm_stage4._span(day, s, e)
        except (TypeError, ValueError):
            continue  # unvollständige Schicht zählt nicht
        hours += (b - a).total_seconds() / 3600
        ids.append(sid)
    return _kpi("Geplante Einsatzstunden", round(hours, 2), "Std.", "field_shifts (ohne abgesagte)", ids,
                f"Auslastung in %: {UNKNOWN} – Soll-Stunden je Mitarbeiter sind nicht erfasst")


def kpis(conn, start, end):
    """Kennzahlen für [start, end] (ISO-Daten). Jede Kennzahl nennt Quelle und Datensatz-IDs."""
    start, end = date.fromisoformat(start).isoformat(), date.fromisoformat(end).isoformat()
    if start > end:
        raise ValueError("Beginn liegt nach dem Ende")
    result = []
    if _has(conn, "lead_events"):
        result.append(_event_kpi(conn, "Neu geprüfte Leads", "geprüft", start, end))
        result.append(_event_kpi(conn, "Zulässige Kontaktaufnahmen", "gesendet", start, end,
                                 "AND COALESCE(legal_basis,'Keine')<>'Keine'"))
        ids = [r[0] for r in conn.execute("SELECT id FROM leads WHERE status IN (?,?) ORDER BY id", OPEN_REPLY)]
        result.append(_kpi("Offene Antworten (aktuell)", len(ids), "Leads", "leads mit Status gesendet/nachfassen", ids))
    if _has(conn, "offers"):
        rows = conn.execute("SELECT id, net_total FROM offers WHERE offer_date BETWEEN ? AND ? ORDER BY id", (start, end)).fetchall()
        result.append(_kpi("Angebote", len(rows), "Stück", "offers.offer_date im Zeitraum", [r[0] for r in rows],
                           f"Summe netto {sum(r[1] or 0 for r in rows):.2f} €"))
        ids = [r[0] for r in conn.execute(
            """SELECT o.id FROM offers o WHERE o.status='angenommen' AND o.offer_date BETWEEN ? AND ?
               AND EXISTS (SELECT 1 FROM offers p WHERE p.customer_id=o.customer_id AND p.status='angenommen'
                           AND (p.offer_date < o.offer_date OR (p.offer_date = o.offer_date AND p.id < o.id)))
               ORDER BY o.id""", (start, end))]
        result.append(_kpi("Folgeaufträge", len(ids), "Aufträge",
                           "angenommene Angebote von Kunden mit früherem angenommenen Angebot", ids))
    result.append(_planned_hours(conn, start, end))
    return result


def snapshot(conn, start, end, created_by=""):
    """Kennzahlen berechnen und mit Prüfsumme protokollieren. Gibt (snapshot_id, kpis) zurück."""
    values = kpis(conn, start, end)
    data = json.dumps(values, ensure_ascii=False, sort_keys=True)
    cur = conn.execute("INSERT INTO kpi_snapshots(ts, period_start, period_end, created_by, data, sha256) VALUES(?,?,?,?,?,?)",
                       (datetime.now().isoformat(timespec="seconds"), start, end, created_by, data,
                        hashlib.sha256(data.encode("utf-8")).hexdigest()))
    conn.commit()
    return cur.lastrowid, values


def _runs(conn, job):
    """(Zeitpunkt, ok) aller Läufe eines Jobs, älteste zuerst."""
    if job == "backup":
        if not _has(conn, "backups"):
            return []
        return [(r[0], True) for r in conn.execute("SELECT created_at FROM backups WHERE created_at IS NOT NULL ORDER BY created_at")]
    if not _has(conn, "automation_log"):
        return []
    return [(r[0], r[1] == "ok") for r in conn.execute(
        "SELECT created_at, status FROM automation_log WHERE job_name=? AND created_at IS NOT NULL ORDER BY created_at, id", (job,))]


def job_status(conn, job, now=None):
    """Status einer Automation aus dem Protokoll: aktiv nur mit Nachweis regelmäßiger, aktueller, fehlerfreier Läufe."""
    label, interval = JOBS[job]
    now = now or datetime.now()
    runs = _runs(conn, job)
    if not runs:
        return {"job": job, "label": label, "status": "nicht eingerichtet", "last_run": None, "runs": 0}
    last_ts, last_ok = runs[-1]
    ok_days = {ts[:10] for ts, ok in runs if ok}
    last = datetime.fromisoformat(last_ts.replace("T", " ")[:19])
    if not last_ok:
        status = "Fehler beim letzten Lauf"
    elif now - last > timedelta(hours=2 * interval):
        status = "überfällig"
    elif len(ok_days) < MIN_PROVEN_RUNS:
        status = "nicht nachgewiesen (nur einzelne Läufe)"
    else:
        status = "aktiv (nachgewiesen)"
    return {"job": job, "label": label, "status": status, "last_run": last_ts, "runs": len(runs)}
