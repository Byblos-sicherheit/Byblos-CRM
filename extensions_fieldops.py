from __future__ import annotations

from datetime import date, timedelta
import pandas as pd
import streamlit as st

SERVICES = ["Sicherheitsdienst", "Reinigung", "Hausmeister", "Umzug", "Entrümpelung"]
SHIFT_STATUS = ["geplant", "aktiv", "erledigt", "Problem", "abgesagt"]


def register_fieldops(run, df):
    run('''CREATE TABLE IF NOT EXISTS field_employees (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        full_name TEXT NOT NULL,
        phone TEXT,
        email TEXT,
        role TEXT,
        service_area TEXT,
        active INTEGER DEFAULT 1,
        notes TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )''')
    run('''CREATE TABLE IF NOT EXISTS employee_qualifications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        employee_id INTEGER,
        qualification TEXT,
        valid_until TEXT,
        document_path TEXT,
        status TEXT DEFAULT 'gültig',
        notes TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )''')
    run('''CREATE TABLE IF NOT EXISTS service_objects (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        customer_id INTEGER,
        object_name TEXT NOT NULL,
        service_type TEXT,
        address TEXT,
        access_notes TEXT,
        risk_notes TEXT,
        active INTEGER DEFAULT 1,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )''')
    run('''CREATE TABLE IF NOT EXISTS field_shifts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        object_id INTEGER,
        employee_id INTEGER,
        service_type TEXT,
        shift_date TEXT,
        start_time TEXT,
        end_time TEXT,
        status TEXT DEFAULT 'geplant',
        instructions TEXT,
        problem_note TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )''')
    run('''CREATE TABLE IF NOT EXISTS service_reports (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        shift_id INTEGER,
        report_date TEXT DEFAULT CURRENT_DATE,
        work_done TEXT,
        incidents TEXT,
        customer_signature TEXT,
        employee_signature TEXT,
        status TEXT DEFAULT 'Entwurf',
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )''')
    run('''CREATE TABLE IF NOT EXISTS object_check_results (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        object_id INTEGER,
        shift_id INTEGER,
        checklist_item TEXT,
        result TEXT DEFAULT 'offen',
        note TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )''')
    seed_fieldops(run, df)


def seed_fieldops(run, df):
    if df("SELECT COUNT(*) AS c FROM field_employees").iloc[0]['c'] == 0:
        run("INSERT INTO field_employees(full_name, role, service_area, notes) VALUES(?,?,?,?)", ("Beispiel Mitarbeiter", "Einsatzkraft", "Sicherheitsdienst", "Demo-Datensatz"))
    if df("SELECT COUNT(*) AS c FROM service_objects").iloc[0]['c'] == 0:
        run("INSERT INTO service_objects(object_name, service_type, address, access_notes, risk_notes) VALUES(?,?,?,?,?)", ("Beispiel Objekt", "Sicherheitsdienst", "Berlin", "Zugang nach Absprache", "Objektprüfung vor Einsatz"))


def page_fieldops_cockpit(run, df):
    st.title("Außendienst & Einsatz Cockpit")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Aktive Mitarbeiter", int(df("SELECT COUNT(*) AS c FROM field_employees WHERE active=1").iloc[0]['c']))
    col2.metric("Aktive Objekte", int(df("SELECT COUNT(*) AS c FROM service_objects WHERE active=1").iloc[0]['c']))
    col3.metric("Geplante Einsätze", int(df("SELECT COUNT(*) AS c FROM field_shifts WHERE status='geplant'").iloc[0]['c']))
    col4.metric("Probleme", int(df("SELECT COUNT(*) AS c FROM field_shifts WHERE status='Problem'").iloc[0]['c']))

    st.subheader("Heute / nächste Einsätze")
    q = df('''SELECT fs.id, fs.shift_date, fs.start_time, fs.end_time, fs.service_type, fs.status,
                    so.object_name, fe.full_name
             FROM field_shifts fs
             LEFT JOIN service_objects so ON so.id=fs.object_id
             LEFT JOIN field_employees fe ON fe.id=fs.employee_id
             ORDER BY fs.shift_date DESC, fs.start_time DESC LIMIT 100''')
    st.dataframe(q, use_container_width=True)

    st.subheader("Operative Warnungen")
    warnings = []
    soon = (date.today() + timedelta(days=30)).isoformat()
    exp = df("SELECT * FROM employee_qualifications WHERE valid_until IS NOT NULL AND valid_until <= ? ORDER BY valid_until", (soon,))
    if not exp.empty:
        warnings.append(f"{len(exp)} Mitarbeiter-Qualifikation(en) laufen innerhalb von 30 Tagen ab.")
    probs = df("SELECT * FROM field_shifts WHERE status='Problem' ORDER BY shift_date DESC")
    if not probs.empty:
        warnings.append(f"{len(probs)} Einsatz/Einsätze mit Problemstatus vorhanden.")
    if warnings:
        for w in warnings: st.warning(w)
    else:
        st.success("Keine kritischen Field-Ops-Warnungen gefunden.")


def page_employees_field(run, df):
    st.title("Mitarbeiter & Qualifikationen")
    with st.form("new_field_employee"):
        c1, c2 = st.columns(2)
        name = c1.text_input("Name")
        role = c2.text_input("Rolle", "Einsatzkraft")
        phone = c1.text_input("Telefon")
        email = c2.text_input("E-Mail")
        area = st.selectbox("Leistungsbereich", SERVICES)
        notes = st.text_area("Notizen")
        if st.form_submit_button("Mitarbeiter speichern") and name:
            run("INSERT INTO field_employees(full_name, phone, email, role, service_area, notes) VALUES(?,?,?,?,?,?)", (name, phone, email, role, area, notes))
            st.success("Mitarbeiter gespeichert."); st.rerun()
    data = df("SELECT * FROM field_employees ORDER BY active DESC, full_name")
    st.dataframe(data, use_container_width=True)

    st.subheader("Qualifikation / Dokument eintragen")
    emps = df("SELECT id, full_name FROM field_employees ORDER BY full_name")
    if not emps.empty:
        emp_label = st.selectbox("Mitarbeiter", [f"{r.id} - {r.full_name}" for r in emps.itertuples()])
        emp_id = int(emp_label.split(" - ")[0])
        with st.form("qual_form"):
            qual = st.text_input("Qualifikation/Dokument", "Unterweisung / Nachweis")
            valid_until = st.date_input("Gültig bis", value=date.today() + timedelta(days=365))
            doc_path = st.text_input("Dokumentpfad / Ablagehinweis")
            notes = st.text_area("Hinweis")
            if st.form_submit_button("Qualifikation speichern"):
                run("INSERT INTO employee_qualifications(employee_id, qualification, valid_until, document_path, notes) VALUES(?,?,?,?,?)", (emp_id, qual, valid_until.isoformat(), doc_path, notes))
                st.success("Qualifikation gespeichert."); st.rerun()
    st.dataframe(df("SELECT * FROM employee_qualifications ORDER BY valid_until"), use_container_width=True)


def page_objects_field(run, df):
    st.title("Objekte & Einsatzorte")
    customers = df("SELECT id, name FROM customers ORDER BY name")
    customer_options = ["0 - ohne Kunde"] + [f"{r.id} - {r.name}" for r in customers.itertuples()]
    with st.form("new_object"):
        cust = st.selectbox("Kunde", customer_options)
        name = st.text_input("Objektname")
        service = st.selectbox("Leistung", SERVICES)
        address = st.text_area("Adresse")
        access = st.text_area("Zugang / Schlüssel / Ansprechpartner")
        risk = st.text_area("Risiken / Besonderheiten")
        if st.form_submit_button("Objekt speichern") and name:
            cid = int(cust.split(" - ")[0]) or None
            run("INSERT INTO service_objects(customer_id, object_name, service_type, address, access_notes, risk_notes) VALUES(?,?,?,?,?,?)", (cid, name, service, address, access, risk))
            st.success("Objekt gespeichert."); st.rerun()
    st.dataframe(df("SELECT * FROM service_objects ORDER BY active DESC, object_name"), use_container_width=True)


def page_shift_planner(run, df):
    st.title("Einsatz- & Schichtplanung")
    objects = df("SELECT id, object_name, service_type FROM service_objects WHERE active=1 ORDER BY object_name")
    emps = df("SELECT id, full_name FROM field_employees WHERE active=1 ORDER BY full_name")
    if objects.empty or emps.empty:
        st.warning("Lege zuerst mindestens ein Objekt und einen Mitarbeiter an.")
        return
    with st.form("new_shift"):
        obj_label = st.selectbox("Objekt", [f"{r.id} - {r.object_name} ({r.service_type})" for r in objects.itertuples()])
        emp_label = st.selectbox("Mitarbeiter", [f"{r.id} - {r.full_name}" for r in emps.itertuples()])
        service = st.selectbox("Leistung", SERVICES)
        d = st.date_input("Datum", value=date.today())
        c1, c2 = st.columns(2)
        start = c1.text_input("Start", "08:00")
        end = c2.text_input("Ende", "16:00")
        instr = st.text_area("Anweisung")
        if st.form_submit_button("Einsatz planen"):
            run("INSERT INTO field_shifts(object_id, employee_id, service_type, shift_date, start_time, end_time, instructions) VALUES(?,?,?,?,?,?,?)", (int(obj_label.split(' - ')[0]), int(emp_label.split(' - ')[0]), service, d.isoformat(), start, end, instr))
            st.success("Einsatz geplant."); st.rerun()
    q = df('''SELECT fs.id, fs.shift_date, fs.start_time, fs.end_time, fs.service_type, fs.status, so.object_name, fe.full_name, fs.instructions, fs.problem_note
              FROM field_shifts fs LEFT JOIN service_objects so ON so.id=fs.object_id LEFT JOIN field_employees fe ON fe.id=fs.employee_id
              ORDER BY fs.shift_date DESC, fs.start_time DESC''')
    st.dataframe(q, use_container_width=True)
    ids = df("SELECT id FROM field_shifts ORDER BY id DESC")
    if not ids.empty:
        sid = st.selectbox("Einsatz bearbeiten", ids['id'].tolist())
        new_status = st.selectbox("Status", SHIFT_STATUS)
        note = st.text_area("Problem / Hinweis")
        if st.button("Status aktualisieren"):
            run("UPDATE field_shifts SET status=?, problem_note=? WHERE id=?", (new_status, note, int(sid)))
            st.success("Status aktualisiert."); st.rerun()


def page_service_reports(run, df):
    st.title("Leistungsnachweise & Einsatzberichte")
    shifts = df('''SELECT fs.id, fs.shift_date, so.object_name, fe.full_name, fs.service_type
                   FROM field_shifts fs LEFT JOIN service_objects so ON so.id=fs.object_id LEFT JOIN field_employees fe ON fe.id=fs.employee_id
                   ORDER BY fs.shift_date DESC, fs.id DESC''')
    if shifts.empty:
        st.warning("Noch keine Einsätze vorhanden.")
    else:
        label = st.selectbox("Einsatz", [f"{r.id} - {r.shift_date} - {r.object_name} - {r.full_name} - {r.service_type}" for r in shifts.itertuples()])
        shift_id = int(label.split(" - ")[0])
        with st.form("new_report"):
            done = st.text_area("Erbrachte Leistung")
            incidents = st.text_area("Vorkommnisse / Schäden / Hinweise")
            emp_sig = st.text_input("Mitarbeiter Unterschrift / Name")
            cust_sig = st.text_input("Kunden Unterschrift / Name")
            status = st.selectbox("Status", ["Entwurf", "geprüft", "unterschrieben", "archiviert"])
            if st.form_submit_button("Leistungsnachweis speichern"):
                run("INSERT INTO service_reports(shift_id, work_done, incidents, employee_signature, customer_signature, status) VALUES(?,?,?,?,?,?)", (shift_id, done, incidents, emp_sig, cust_sig, status))
                st.success("Leistungsnachweis gespeichert."); st.rerun()
    st.dataframe(df("SELECT * FROM service_reports ORDER BY id DESC"), use_container_width=True)


def page_fieldops_exports(run, df):
    st.title("Field-Ops Export")
    tables = {
        "Mitarbeiter": "field_employees",
        "Qualifikationen": "employee_qualifications",
        "Objekte": "service_objects",
        "Einsätze": "field_shifts",
        "Leistungsnachweise": "service_reports",
    }
    choice = st.selectbox("Export", list(tables.keys()))
    data = df(f"SELECT * FROM {tables[choice]} ORDER BY id DESC")
    st.dataframe(data, use_container_width=True)
    st.download_button("CSV herunterladen", data.to_csv(index=False).encode('utf-8-sig'), file_name=f"{tables[choice]}_export.csv", mime="text/csv")
