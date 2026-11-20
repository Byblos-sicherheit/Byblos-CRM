"""CRM Stufe 4: Einsatzprüfung für field_shifts (Arbeitszeit, Überschneidung, §34a, Radius, Ansprechpartner)."""
from datetime import date, datetime, timedelta

import crm_stage1

SECURITY_SERVICES = {"Sicherheitsdienst"}
MAX_SHIFT_HOURS = 10   # ArbZG § 3: höchstens 10 Stunden werktäglich
MIN_REST_HOURS = 11    # ArbZG § 5: mindestens 11 Stunden Ruhezeit
INACTIVE = {"abgesagt"}
QUALIFICATION_KEYWORD = "34a"
NEW_COLUMNS = {"offer_id": "INTEGER", "contact_person": "TEXT", "contact_phone": "TEXT", "access_permissions": "TEXT"}


def ensure_columns(conn):
    if not conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='field_shifts'").fetchone():
        return
    have = {r[1] for r in conn.execute("PRAGMA table_info(field_shifts)")}
    for name, decl in NEW_COLUMNS.items():
        if name not in have:
            conn.execute(f"ALTER TABLE field_shifts ADD COLUMN {name} {decl}")
    conn.commit()


def _span(day, start, end):
    """(Beginn, Ende) als datetime; Ende vor Beginn = Nachtschicht bis zum Folgetag. ValueError bei falschem Format."""
    d = date.fromisoformat(str(day))
    s = datetime.combine(d, datetime.strptime(start, "%H:%M").time())
    e = datetime.combine(d, datetime.strptime(end, "%H:%M").time())
    return s, e + timedelta(days=1) if e <= s else e


def _qualified(conn, employee_id, day):
    cols = {r[1] for r in conn.execute("PRAGMA table_info(employee_qualifications)")}
    if not cols:
        return False
    until = "valid_until" if "valid_until" in cols else "expiry_date"
    rows = conn.execute(f"SELECT qualification, {until} FROM employee_qualifications WHERE employee_id=?", (employee_id,)).fetchall()
    # Unterrichtung/Sachkunde nach §34a hat oft kein Ablaufdatum: leer = unbefristet
    return any(QUALIFICATION_KEYWORD in (q or "") and (not v or str(v) >= str(day)) for q, v in rows)


def validate_shift(conn, employee_id, object_id, service, day, start, end, contact_person, offer_id=None, exclude_id=None):
    """Gründe, warum der Einsatz NICHT geplant werden darf. Leere Liste = zulässig."""
    try:
        s, e = _span(day, start, end)
    except (TypeError, ValueError):
        return ["Datum (JJJJ-MM-TT) und Zeiten (HH:MM) prüfen"]
    reasons = []
    if s == e - timedelta(days=1):
        reasons.append("Beginn und Ende sind gleich")
    hours = (e - s).total_seconds() / 3600
    if hours > MAX_SHIFT_HOURS:
        reasons.append(f"Einsatz {hours:.1f} h – höchstens {MAX_SHIFT_HOURS} h (ArbZG § 3)")
    if not (contact_person or "").strip():
        reasons.append("Ansprechpartner vor Ort fehlt")
    obj = conn.execute("SELECT customer_id FROM service_objects WHERE id=?", (object_id,)).fetchone()
    if not obj:
        reasons.append("Objekt nicht gefunden")
    elif obj[0]:
        km = conn.execute("SELECT distance_km FROM customers WHERE id=?", (obj[0],)).fetchone()
        if km and crm_stage1.radius_status(km[0]) == "außerhalb":
            reasons.append(f"Kunde des Objekts liegt außerhalb von {crm_stage1.MAX_KM:.0f} km")
    if service in SECURITY_SERVICES and not _qualified(conn, employee_id, s.date().isoformat()):
        reasons.append("Sicherheitsdienst nur mit gültiger §-34a-Qualifikation des Mitarbeiters")
    if offer_id:
        status = conn.execute("SELECT status FROM offers WHERE id=?", (offer_id,)).fetchone()
        if not status or status[0] != "angenommen":
            reasons.append("Verknüpftes Angebot ist nicht angenommen (kein Auftrag)")
    rest = timedelta(hours=MIN_REST_HOURS)
    others = conn.execute(f"""SELECT id, shift_date, start_time, end_time FROM field_shifts
                             WHERE employee_id=? AND id<>? AND COALESCE(status,'') NOT IN ({','.join('?' * len(INACTIVE))})""",
                          (employee_id, exclude_id or -1, *INACTIVE)).fetchall()
    for oid, od, ostart, oend in others:
        try:
            os_, oe = _span(od, ostart, oend)
        except (TypeError, ValueError):
            continue
        if s < oe and os_ < e:
            reasons.append(f"Überschneidung mit Einsatz {oid} ({od} {ostart}–{oend})")
        elif (os_ >= e and os_ - e < rest) or (s >= oe and s - oe < rest):
            reasons.append(f"Weniger als {MIN_REST_HOURS} h Ruhezeit zu Einsatz {oid} ({od} {ostart}–{oend}, ArbZG § 5)")
    return reasons


def plan_shift(conn, employee_id, object_id, service, day, start, end, contact_person, contact_phone="",
               access_permissions="", instructions="", offer_id=None):
    """Einsatz prüfen und anlegen. ValueError mit allen Gründen, wenn unzulässig."""
    reasons = validate_shift(conn, employee_id, object_id, service, day, start, end, contact_person, offer_id)
    if reasons:
        raise ValueError("; ".join(reasons))
    cur = conn.execute("""INSERT INTO field_shifts(object_id,employee_id,service_type,shift_date,start_time,end_time,instructions,
                                                   offer_id,contact_person,contact_phone,access_permissions)
                          VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
                       (object_id, employee_id, service, str(day), start, end, instructions, offer_id,
                        contact_person.strip(), contact_phone, access_permissions))
    conn.commit()
    return cur.lastrowid
