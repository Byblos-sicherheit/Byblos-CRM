"""
extensions_v2_einvoice_time.py – Byblos-spezifische Sicherheitsdienst-Module
=============================================================================
1.  Wachbuch digital (stündliche Einträge)
2.  Objekt-Stammdaten (Gebäude / Liegenschaften)
3.  Unfallmelde-Protokoll (BG-konform)
4.  Schlüssel-Verwaltung (Ausgabe / Rückgabe)
5.  Dienstanweisung-Generator (Objekt-spezifisch)
6.  §34a GewO Registrierungs-Nachweis-Center
7.  Einsatzplanung Großveranstaltungen
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
import secrets

import pandas as pd
import streamlit as st


def fmt_eur(v: float) -> str:
    return f"{v:,.2f} €".replace(",","X").replace(".",",").replace("X",".")


# ─────────────────────────────────────────────────────────────
# DB-Registrierung
# ─────────────────────────────────────────────────────────────

def register_einvoice_time(run_fn, df_fn) -> None:
    run_fn("""CREATE TABLE IF NOT EXISTS objects (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        object_no TEXT UNIQUE NOT NULL,
        name TEXT NOT NULL,
        customer_id INTEGER,
        address TEXT,
        object_type TEXT DEFAULT 'Gebäude',
        access_info TEXT,
        emergency_contacts TEXT,
        special_instructions TEXT,
        sla_response_minutes INTEGER DEFAULT 15,
        security_level TEXT DEFAULT 'Standard',
        active INTEGER DEFAULT 1,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(customer_id) REFERENCES customers(id)
    )""")
    run_fn("""CREATE TABLE IF NOT EXISTS watch_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        object_id INTEGER,
        employee_id INTEGER,
        log_date TEXT NOT NULL,
        log_time TEXT NOT NULL,
        entry_type TEXT DEFAULT 'Rundgang',
        status TEXT DEFAULT 'normal',
        notes TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(object_id) REFERENCES objects(id),
        FOREIGN KEY(employee_id) REFERENCES employees(id)
    )""")
    run_fn("""CREATE TABLE IF NOT EXISTS incident_reports (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        report_no TEXT UNIQUE NOT NULL,
        object_id INTEGER,
        employee_id INTEGER,
        incident_date TEXT NOT NULL,
        incident_time TEXT NOT NULL,
        incident_type TEXT NOT NULL,
        description TEXT NOT NULL,
        persons_involved TEXT,
        witnesses TEXT,
        police_called INTEGER DEFAULT 0,
        police_report_no TEXT,
        ambulance_called INTEGER DEFAULT 0,
        first_aid_provided INTEGER DEFAULT 0,
        corrective_action TEXT,
        status TEXT DEFAULT 'offen',
        bg_reported INTEGER DEFAULT 0,
        bg_report_date TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(object_id) REFERENCES objects(id),
        FOREIGN KEY(employee_id) REFERENCES employees(id)
    )""")
    run_fn("""CREATE TABLE IF NOT EXISTS key_management (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        key_no TEXT UNIQUE NOT NULL,
        object_id INTEGER,
        description TEXT NOT NULL,
        copies INTEGER DEFAULT 1,
        issued_to INTEGER,
        issued_date TEXT,
        return_date TEXT,
        status TEXT DEFAULT 'verfügbar',
        notes TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(object_id) REFERENCES objects(id),
        FOREIGN KEY(issued_to) REFERENCES employees(id)
    )""")
    run_fn("""CREATE TABLE IF NOT EXISTS duty_instructions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        instruction_no TEXT UNIQUE NOT NULL,
        object_id INTEGER,
        title TEXT NOT NULL,
        version TEXT DEFAULT '1.0',
        content TEXT NOT NULL,
        valid_from TEXT NOT NULL,
        valid_until TEXT,
        acknowledged_by TEXT DEFAULT '[]',
        created_by TEXT,
        active INTEGER DEFAULT 1,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(object_id) REFERENCES objects(id)
    )""")
    run_fn("""CREATE TABLE IF NOT EXISTS events_security (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        event_no TEXT UNIQUE NOT NULL,
        customer_id INTEGER,
        event_name TEXT NOT NULL,
        event_date TEXT NOT NULL,
        event_time_start TEXT,
        event_time_end TEXT,
        venue TEXT NOT NULL,
        expected_visitors INTEGER DEFAULT 0,
        security_concept TEXT,
        staff_required INTEGER DEFAULT 0,
        staff_assigned INTEGER DEFAULT 0,
        equipment_needed TEXT,
        briefing_time TEXT,
        status TEXT DEFAULT 'geplant',
        notes TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(customer_id) REFERENCES customers(id)
    )""")


# ─────────────────────────────────────────────────────────────
# 1. Objekt-Stammdaten
# ─────────────────────────────────────────────────────────────

def page_objects(run_fn, df_fn, next_number_fn, log_fn) -> None:
    st.title("🏢 Objekt-Stammdaten")
    st.caption("Gebäude, Liegenschaften und Einsatzobjekte verwalten.")

    OBJECT_TYPES  = ["Gebäude","Industrieanlage","Einkaufszentrum","Parkhaus",
                     "Veranstaltungsort","Baustelle","Außengelände","Sonstiges"]
    SEC_LEVELS    = ["Basis","Standard","Erhöht","Kritisch"]

    tabs = st.tabs(["📋 Objekte", "➕ Neu anlegen", "✏️ Bearbeiten"])

    with tabs[0]:
        q = st.text_input("🔍 Suche")
        objects = df_fn("""
            SELECT o.id, o.object_no AS Nr, o.name AS Objekt,
                   COALESCE(c.company,'–') AS Kunde, o.object_type AS Typ,
                   o.address AS Adresse, o.security_level AS Sicherheitslevel,
                   o.sla_response_minutes AS SLA_Min, o.active AS Aktiv
            FROM objects o LEFT JOIN customers c ON c.id=o.customer_id
        """ + (f" WHERE o.name LIKE '%{q}%' OR o.address LIKE '%{q}%'" if q else "") +
            " ORDER BY o.name")
        if not objects.empty:
            c1, c2 = st.columns(2)
            c1.metric("Objekte gesamt", len(objects))
            c2.metric("Aktive Objekte", len(objects[objects["Aktiv"]==1]))
            st.dataframe(objects.drop(columns=["id"]), use_container_width=True, height=400)
            csv = objects.drop(columns=["id"]).to_csv(index=False, sep=";").encode("utf-8-sig")
            st.download_button("📥 Objektliste CSV", csv, "objekte.csv", "text/csv")
        else:
            st.info("Keine Objekte vorhanden.")

    with tabs[1]:
        customers = df_fn("SELECT id, customer_no || ' – ' || company AS label FROM customers ORDER BY company")
        with st.form("obj_form", clear_on_submit=True):
            a, b = st.columns(2)
            obj_no   = a.text_input("Objekt-Nr.", next_number_fn("objects","object_no","OBJ-"))
            name     = b.text_input("Objektbezeichnung *")
            cust_lbl = a.selectbox("Auftraggeber", ["—"] + (customers["label"].tolist() if not customers.empty else []))
            obj_type = b.selectbox("Objekttyp", OBJECT_TYPES)
            address  = st.text_input("Adresse / Standort")
            col3, col4 = st.columns(2)
            sec_lvl  = col3.selectbox("Sicherheitslevel", SEC_LEVELS)
            sla_min  = col4.number_input("SLA Reaktionszeit (Min)", min_value=5, value=15, step=5)
            access   = st.text_area("Zugangsinformationen (Codes, Schlüssel, Gates)")
            emerg    = st.text_area("Notfallkontakte (Hausmeister, Techniker, Polizei)")
            instr    = st.text_area("Besondere Anweisungen")
            submitted = st.form_submit_button("💾 Speichern", type="primary")

        if submitted and name:
            cid = None
            if cust_lbl != "—" and not customers.empty:
                match = customers[customers["label"] == cust_lbl]
                if not match.empty: cid = int(match.iloc[0]["id"])
            run_fn("""INSERT INTO objects(object_no,name,customer_id,address,object_type,
                      access_info,emergency_contacts,special_instructions,
                      sla_response_minutes,security_level)
                      VALUES(?,?,?,?,?,?,?,?,?,?)""",
                   (obj_no, name, cid, address, obj_type, access, emerg, instr, sla_min, sec_lvl))
            log_fn("object_created", name)
            st.success(f"✅ Objekt '{name}' angelegt!"); st.rerun()

    with tabs[2]:
        obj_list = df_fn("SELECT id, object_no || ' – ' || name AS label, active FROM objects ORDER BY name")
        if obj_list.empty:
            st.info("Keine Objekte.")
            return
        sel = st.selectbox("Objekt auswählen", obj_list["label"].tolist())
        oid = int(obj_list[obj_list["label"] == sel].iloc[0]["id"])
        cur_active = bool(obj_list[obj_list["label"] == sel].iloc[0]["active"])
        col1, col2 = st.columns(2)
        if col1.button("⛔ Deaktivieren" if cur_active else "✅ Aktivieren"):
            run_fn("UPDATE objects SET active=? WHERE id=?", (0 if cur_active else 1, oid))
            st.rerun()
        if col2.button("🗑️ Löschen"):
            run_fn("DELETE FROM objects WHERE id=?", (oid,))
            st.rerun()


# ─────────────────────────────────────────────────────────────
# 2. Wachbuch digital
# ─────────────────────────────────────────────────────────────

def page_watch_log(run_fn, df_fn, current_user_fn) -> None:
    st.title("📔 Wachbuch")
    st.caption("Digitales Wachbuch – stündliche Einträge und Ereignismeldungen.")

    ENTRY_TYPES = ["Rundgang absolviert","Dienstbeginn","Dienstende","Schichtwechsel",
                   "Besuchermeldung","Störung festgestellt","Alarmauslösung","Sonstiger Eintrag"]
    STATUS_TYPES = ["normal","auffällig","Alarm","Notfall"]

    user = current_user_fn() or {}

    tabs = st.tabs(["📋 Tagbuch heute", "➕ Eintrag", "📅 Archiv"])

    with tabs[0]:
        today = date.today().isoformat()
        objects = df_fn("SELECT id, name FROM objects WHERE active=1 ORDER BY name")
        obj_label = st.selectbox("Objekt", objects["name"].tolist() if not objects.empty else ["–"])

        if not objects.empty:
            oid = int(objects[objects["name"] == obj_label].iloc[0]["id"])
            today_entries = df_fn(f"""
                SELECT wl.log_time AS Zeit, wl.entry_type AS Typ,
                       COALESCE(e.name,'–') AS Mitarbeiter,
                       wl.status AS Status, wl.notes AS Notiz
                FROM watch_log wl LEFT JOIN employees e ON e.id=wl.employee_id
                WHERE wl.object_id={oid} AND wl.log_date='{today}'
                ORDER BY wl.log_time
            """)
            if not today_entries.empty:
                # Farbkodierung Status
                for _, r in today_entries.iterrows():
                    color = {"normal":"#27ae60","auffällig":"#e67e22",
                              "Alarm":"#c0392b","Notfall":"#8e44ad"}.get(str(r["Status"]),"#888")
                    st.markdown(
                        f'<div style="border-left:3px solid {color};padding:4px 10px;margin:2px 0;">'
                        f'<b>{r["Zeit"]}</b> — {r["Typ"]} '
                        f'<span style="color:#888;">({r["Mitarbeiter"]})</span>'
                        f'<br/><span style="font-size:.85em;">{r.get("Notiz","") or ""}</span></div>',
                        unsafe_allow_html=True
                    )
                if st.button("📥 Tagesbuch als CSV"):
                    csv = today_entries.to_csv(index=False, sep=";").encode("utf-8-sig")
                    st.download_button("⬇", csv, f"wachbuch_{obj_label}_{today}.csv", "text/csv")
            else:
                st.info("Heute noch keine Einträge für dieses Objekt.")

    with tabs[1]:
        objects2 = df_fn("SELECT id, name FROM objects WHERE active=1 ORDER BY name")
        employees = df_fn("SELECT id, name FROM employees WHERE active=1 ORDER BY name")
        with st.form("watch_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            obj_sel  = col1.selectbox("Objekt *", objects2["name"].tolist() if not objects2.empty else ["–"])
            emp_sel  = col2.selectbox("Mitarbeiter", employees["name"].tolist() if not employees.empty else ["–"])
            col3, col4 = st.columns(2)
            log_date = col3.date_input("Datum", date.today())
            log_time = col4.time_input("Uhrzeit", datetime.now().time())
            entry_t  = col1.selectbox("Eintragstyp", ENTRY_TYPES)
            status   = col2.selectbox("Status", STATUS_TYPES)
            notes    = st.text_area("Notiz / Meldung")
            submitted = st.form_submit_button("📝 Eintragen", type="primary")

        if submitted and not objects2.empty:
            oid2 = int(objects2[objects2["name"] == obj_sel].iloc[0]["id"])
            eid2 = int(employees[employees["name"] == emp_sel].iloc[0]["id"]) if not employees.empty else None
            run_fn("""INSERT INTO watch_log(object_id,employee_id,log_date,log_time,
                      entry_type,status,notes)
                      VALUES(?,?,?,?,?,?,?)""",
                   (oid2, eid2, log_date.isoformat(), log_time.strftime("%H:%M"),
                    entry_t, status, notes))
            if status in ("Alarm","Notfall"):
                st.error(f"⚠️ {status}-Eintrag gespeichert! Bitte Vorgesetzten informieren.")
            else:
                st.success("✅ Wachbuch-Eintrag gespeichert!")
            st.rerun()

    with tabs[2]:
        objects3 = df_fn("SELECT id, name FROM objects WHERE active=1 ORDER BY name")
        if objects3.empty:
            st.info("Keine Objekte.")
            return
        col1, col2 = st.columns(2)
        obj_a   = col1.selectbox("Objekt", objects3["name"].tolist(), key="arch_obj")
        date_a  = col2.date_input("Datum", date.today() - timedelta(days=1), key="arch_date")
        oid_a = int(objects3[objects3["name"] == obj_a].iloc[0]["id"])
        arch = df_fn(f"""
            SELECT wl.log_time AS Zeit, wl.entry_type AS Typ,
                   COALESCE(e.name,'–') AS Mitarbeiter,
                   wl.status AS Status, wl.notes AS Notiz
            FROM watch_log wl LEFT JOIN employees e ON e.id=wl.employee_id
            WHERE wl.object_id={oid_a} AND wl.log_date='{date_a.isoformat()}'
            ORDER BY wl.log_time
        """)
        if not arch.empty:
            st.dataframe(arch, use_container_width=True)
        else:
            st.info(f"Keine Einträge für {date_a.isoformat()}.")


# ─────────────────────────────────────────────────────────────
# 3. Unfallmelde-Protokoll (BG-konform)
# ─────────────────────────────────────────────────────────────

def page_incident_reports(run_fn, df_fn, next_number_fn, log_fn) -> None:
    st.title("🚨 Unfallmelde-Protokoll")
    st.caption("BG-konforme Dokumentation von Unfällen und Vorfällen.")

    INCIDENT_TYPES = ["Einbruchversuch","Diebstahl","Vandalismus","Körperverletzung",
                      "Arbeitsunfall","Brandvorfall","Wasserschaden","Technische Störung",
                      "Unerlaubtes Betreten","Verdächtiger Gegenstand","Sonstiger Vorfall"]

    tabs = st.tabs(["📋 Protokolle", "➕ Neues Protokoll", "📊 Statistik", "⚙️ BG-Meldung"])

    with tabs[0]:
        reports = df_fn("""
            SELECT r.report_no AS Nr, r.incident_date AS Datum,
                   r.incident_time AS Zeit, o.name AS Objekt,
                   r.incident_type AS Typ, r.status AS Status,
                   CASE WHEN r.bg_reported=1 THEN '✅' ELSE '–' END AS BG_gemeldet
            FROM incident_reports r LEFT JOIN objects o ON o.id=r.object_id
            ORDER BY r.incident_date DESC, r.incident_time DESC
        """)
        if not reports.empty:
            c1, c2, c3 = st.columns(3)
            c1.metric("Protokolle gesamt", len(reports))
            c2.metric("Offen", len(reports[reports["Status"]=="offen"]))
            c3.metric("BG-gemeldet", len(reports[reports["BG_gemeldet"]=="✅"]))
            st.dataframe(reports, use_container_width=True, height=350)
        else:
            st.info("Noch keine Protokolle.")

    with tabs[1]:
        objects = df_fn("SELECT id, name FROM objects WHERE active=1 ORDER BY name")
        employees = df_fn("SELECT id, name FROM employees WHERE active=1 ORDER BY name")
        with st.form("incident_form", clear_on_submit=True):
            rep_no = st.text_input("Protokoll-Nr.", next_number_fn("incident_reports","report_no","UNF-"))
            col1, col2, col3 = st.columns(3)
            inc_date = col1.date_input("Datum", date.today())
            inc_time = col2.time_input("Uhrzeit", datetime.now().time())
            inc_type = col3.selectbox("Vorfalltyp *", INCIDENT_TYPES)
            obj_sel  = col1.selectbox("Objekt", objects["name"].tolist() if not objects.empty else ["–"])
            emp_sel  = col2.selectbox("Meldender MA", employees["name"].tolist() if not employees.empty else ["–"])

            description = st.text_area("Genaue Beschreibung des Vorfalls *", height=120)
            persons  = st.text_area("Beteiligte Personen (Name, Alter, Kennzeichen)")
            witnesses = st.text_area("Zeugen")

            col4, col5, col6 = st.columns(3)
            police = col4.checkbox("Polizei verständigt")
            ambu   = col5.checkbox("Rettungsdienst")
            fa     = col6.checkbox("Erste Hilfe geleistet")
            police_no = st.text_input("Polizei Tagebuch-Nr.") if police else ""
            corrective = st.text_area("Sofortmaßnahmen / Korrekturmaßnahmen")
            submitted = st.form_submit_button("💾 Protokoll speichern", type="primary")

        if submitted and description:
            oid = int(objects[objects["name"] == obj_sel].iloc[0]["id"]) if not objects.empty else None
            eid = int(employees[employees["name"] == emp_sel].iloc[0]["id"]) if not employees.empty else None
            run_fn("""INSERT INTO incident_reports(report_no,object_id,employee_id,
                      incident_date,incident_time,incident_type,description,
                      persons_involved,witnesses,police_called,police_report_no,
                      ambulance_called,first_aid_provided,corrective_action,status)
                      VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                   (rep_no, oid, eid, inc_date.isoformat(), inc_time.strftime("%H:%M"),
                    inc_type, description, persons, witnesses,
                    1 if police else 0, police_no, 1 if ambu else 0,
                    1 if fa else 0, corrective, "offen"))
            log_fn("incident_reported", f"{rep_no} {inc_type}")
            st.success(f"✅ Protokoll {rep_no} gespeichert!")
            if inc_type in ("Körperverletzung","Arbeitsunfall"):
                st.warning("⚠️ Bitte Berufsgenossenschaft innerhalb von 3 Tagen informieren (Unfälle mit >3 Ausfalltagen)!")
            st.rerun()

    with tabs[2]:
        stats = df_fn("""
            SELECT incident_type AS Vorfalltyp, COUNT(*) AS Anzahl,
                   SUM(police_called) AS Polizei_gerufen,
                   SUM(ambulance_called) AS Rettung_gerufen
            FROM incident_reports GROUP BY incident_type ORDER BY Anzahl DESC
        """)
        if not stats.empty:
            st.dataframe(stats, use_container_width=True)
            st.bar_chart(stats.set_index("Vorfalltyp")["Anzahl"])
        else:
            st.info("Noch keine Protokolle für Statistik.")

    with tabs[3]:
        st.subheader("BG-Meldepflicht Checkliste")
        st.markdown("""
**Meldepflichtige Arbeitsunfälle (BG Sicherheitswirtschaft):**

| Kriterium | Frist | Empfänger |
|---|---|---|
| Unfall mit >3 Tagen Arbeitsausfall | 3 Werktage | BG Sicherheitswirtschaft |
| Wegeunfall (auf dem Weg zur Arbeit) | 3 Werktage | Unfallkasse/BG |
| Tödlicher Unfall | Sofort | BG + Behörde |
| Berufskrankheit (Verdacht) | Unverzüglich | BG |

**Kontakt BG Sicherheitswirtschaft:**
- Internet: www.bgsg.de
- Tel.: 06221 5108-0
- Online-Meldung: BGConnect Portal

**Dokumentation im System:**
        """)
        open_incidents = df_fn("SELECT id, report_no, incident_type, bg_reported FROM incident_reports WHERE status='offen' AND incident_type IN ('Körperverletzung','Arbeitsunfall')")
        if not open_incidents.empty:
            for _, r in open_incidents.iterrows():
                rid = int(r["id"])
                col1, col2 = st.columns([3,1])
                col1.write(f"📋 {r['report_no']} – {r['incident_type']}")
                if not r["bg_reported"]:
                    if col2.button("BG gemeldet ✅", key=f"bg_{rid}"):
                        run_fn("UPDATE incident_reports SET bg_reported=1, bg_report_date=? WHERE id=?",
                               (date.today().isoformat(), rid))
                        st.rerun()
                else:
                    col2.success("Gemeldet ✅")


# ─────────────────────────────────────────────────────────────
# 4. Schlüssel-Verwaltung
# ─────────────────────────────────────────────────────────────

def page_key_management(run_fn, df_fn, next_number_fn, log_fn) -> None:
    st.title("🔑 Schlüssel-Verwaltung")
    st.caption("Ausgabe und Rückgabe von Schlüsseln und Zugangsmitteln.")

    tabs = st.tabs(["📋 Schlüsselübersicht", "➕ Schlüssel anlegen",
                    "📤 Ausgabe", "📥 Rückgabe", "⚠️ Verluste"])

    with tabs[0]:
        keys = df_fn("""
            SELECT k.key_no AS Nr, k.description AS Beschreibung,
                   COALESCE(o.name,'–') AS Objekt,
                   k.copies AS Exemplare, k.status AS Status,
                   COALESCE(e.name,'–') AS Ausgegeben_an,
                   k.issued_date AS Ausgabedatum
            FROM key_management k
            LEFT JOIN objects o ON o.id=k.object_id
            LEFT JOIN employees e ON e.id=k.issued_to
            ORDER BY k.key_no
        """)
        if not keys.empty:
            c1, c2 = st.columns(2)
            c1.metric("Schlüssel gesamt", len(keys))
            c2.metric("Aktuell ausgegeben", len(keys[keys["Status"]=="ausgegeben"]))
            st.dataframe(keys, use_container_width=True, height=350)
        else:
            st.info("Noch keine Schlüssel erfasst.")

    with tabs[1]:
        objects = df_fn("SELECT id, name FROM objects WHERE active=1 ORDER BY name")
        with st.form("key_form", clear_on_submit=True):
            key_no = st.text_input("Schlüssel-Nr.", next_number_fn("key_management","key_no","KEY-"))
            desc   = st.text_input("Beschreibung (z.B. 'Haupteingang Tor 1') *")
            obj_sel = st.selectbox("Objekt", ["—"] + (objects["name"].tolist() if not objects.empty else []))
            copies = st.number_input("Anzahl Exemplare", min_value=1, value=1, step=1)
            notes  = st.text_area("Notizen")
            if st.form_submit_button("💾 Schlüssel anlegen", type="primary") and desc:
                oid = None
                if obj_sel != "—" and not objects.empty:
                    match = objects[objects["name"] == obj_sel]
                    if not match.empty: oid = int(match.iloc[0]["id"])
                run_fn("INSERT INTO key_management(key_no,description,object_id,copies,status,notes) VALUES(?,?,?,?,'verfügbar',?)",
                       (key_no, desc, oid, copies, notes))
                log_fn("key_added", key_no)
                st.success(f"✅ Schlüssel {key_no} angelegt!")
                st.rerun()

    with tabs[2]:
        avail = df_fn("SELECT id, key_no || ' – ' || description AS label FROM key_management WHERE status='verfügbar'")
        employees = df_fn("SELECT id, name FROM employees WHERE active=1 ORDER BY name")
        if avail.empty:
            st.info("Alle Schlüssel sind ausgegeben oder nicht erfasst.")
        elif employees.empty:
            st.info("Keine Mitarbeiter.")
        else:
            key_sel = st.selectbox("Schlüssel ausgeben", avail["label"].tolist())
            emp_sel = st.selectbox("An Mitarbeiter", employees["name"].tolist())
            if st.button("📤 Ausgeben", type="primary"):
                kid = int(avail[avail["label"] == key_sel].iloc[0]["id"])
                eid = int(employees[employees["name"] == emp_sel].iloc[0]["id"])
                run_fn("UPDATE key_management SET status='ausgegeben', issued_to=?, issued_date=?, return_date=NULL WHERE id=?",
                       (eid, date.today().isoformat(), kid))
                log_fn("key_issued", f"{key_sel} → {emp_sel}")
                st.success(f"✅ {key_sel} an {emp_sel} ausgegeben. Bitte Quittung unterschreiben!")
                st.rerun()

    with tabs[3]:
        issued = df_fn("SELECT id, key_no || ' – ' || description AS label FROM key_management WHERE status='ausgegeben'")
        if issued.empty:
            st.info("Keine ausgegeben Schlüssel.")
        else:
            key_ret = st.selectbox("Rückgabe von", issued["label"].tolist())
            cond    = st.selectbox("Zustand", ["einwandfrei","leicht beschädigt","stark beschädigt"])
            notes_r = st.text_input("Notizen zur Rückgabe")
            if st.button("📥 Rückgabe buchen", type="primary"):
                kid = int(issued[issued["label"] == key_ret].iloc[0]["id"])
                status = "verfügbar" if cond == "einwandfrei" else "defekt"
                run_fn("UPDATE key_management SET status=?,issued_to=NULL,return_date=?,notes=? WHERE id=?",
                       (status, date.today().isoformat(), notes_r or cond, kid))
                log_fn("key_returned", key_ret)
                st.success(f"✅ {key_ret} zurückgebucht ({cond})")
                st.rerun()

    with tabs[4]:
        lost = df_fn("SELECT key_no AS Nr, description AS Beschreibung, issued_date AS Ausgegeben FROM key_management WHERE status='verloren'")
        if not lost.empty:
            st.error(f"⚠️ {len(lost)} Schlüssel als verloren markiert!")
            st.dataframe(lost, use_container_width=True)
        else:
            st.success("✅ Keine verlorenen Schlüssel.")
        
        issued2 = df_fn("SELECT id, key_no || ' – ' || description AS label FROM key_management WHERE status='ausgegeben'")
        if not issued2.empty:
            key_lost = st.selectbox("Als verloren melden", issued2["label"].tolist())
            if st.button("🚨 Als verloren melden"):
                kid = int(issued2[issued2["label"] == key_lost].iloc[0]["id"])
                run_fn("UPDATE key_management SET status='verloren' WHERE id=?", (kid,))
                log_fn("key_lost", key_lost)
                st.error(f"🚨 {key_lost} als verloren gemeldet! Schloss wechseln!")
                st.rerun()


# ─────────────────────────────────────────────────────────────
# 5. §34a GewO Registrierungs-Center
# ─────────────────────────────────────────────────────────────

def page_gewa34a_center(df_fn, run_fn) -> None:
    st.title("📜 §34a GewO Registrierungs-Center")
    st.caption("Nachweise, Registrierungen und Schulungen für das Bewachungsgewerbe.")

    tabs = st.tabs(["📋 Übersicht", "⚠️ Ablaufende Nachweise",
                    "📊 Compliance-Status", "ℹ️ Anforderungen"])

    with tabs[0]:
        stats = df_fn("""
            SELECT e.name AS Mitarbeiter, e.employee_no AS Nr,
                   COUNT(CASE WHEN eq.qualification='Unterrichtung §34a GewO' THEN 1 END) AS Unterrichtung,
                   COUNT(CASE WHEN eq.qualification='Sachkundeprüfung §34a GewO' THEN 1 END) AS Sachkunde,
                   COUNT(CASE WHEN eq.qualification='Bewacherregistrierung' THEN 1 END) AS Registriert,
                   MIN(CASE WHEN eq.qualification='Unterrichtung §34a GewO'
                        THEN eq.expiry_date END) AS Unterr_Ablauf
            FROM employees e LEFT JOIN employee_qualifications eq ON eq.employee_id=e.id
            WHERE e.active=1
            GROUP BY e.id ORDER BY e.name
        """)

        if not stats.empty:
            compliant = len(stats[(stats["Unterrichtung"]>0) & (stats["Registriert"]>0)])
            c1, c2, c3 = st.columns(3)
            c1.metric("Aktive Mitarbeiter", len(stats))
            c2.metric("✅ Compliant", compliant)
            c3.metric("⚠️ Nicht compliant", len(stats) - compliant)
            st.dataframe(stats, use_container_width=True)
        else:
            st.info("Keine aktiven Mitarbeiter erfasst.")

    with tabs[1]:
        today = date.today().isoformat()
        warn90 = (date.today() + timedelta(days=90)).isoformat()
        expiring = df_fn(f"""
            SELECT e.name AS Mitarbeiter, eq.qualification AS Qualifikation,
                   eq.expiry_date AS Ablauf,
                   CAST(julianday(eq.expiry_date) - julianday('now') AS INT) AS Tage_verbleibend
            FROM employee_qualifications eq JOIN employees e ON e.id=eq.employee_id
            WHERE eq.expiry_date IS NOT NULL
              AND eq.expiry_date <= '{warn90}'
              AND e.active=1
            ORDER BY eq.expiry_date
        """)
        if not expiring.empty:
            expired = expiring[expiring["Tage_verbleibend"] < 0]
            soon = expiring[expiring["Tage_verbleibend"] >= 0]
            if not expired.empty:
                st.error(f"❌ {len(expired)} ABGELAUFENE §34a-Nachweise!")
                st.dataframe(expired, use_container_width=True)
            if not soon.empty:
                st.warning(f"⚠️ {len(soon)} Nachweise laufen in 90 Tagen ab!")
                st.dataframe(soon, use_container_width=True)
        else:
            st.success("✅ Alle §34a-Nachweise aktuell!")

    with tabs[2]:
        st.subheader("§34a GewO Compliance-Check")
        REQUIRED = ["Unterrichtung §34a GewO","Bewacherregistrierung"]
        RECOMMENDED = ["Sachkundeprüfung §34a GewO","Erste-Hilfe-Kurs"]

        for emp_data in df_fn("SELECT id, name FROM employees WHERE active=1 ORDER BY name").to_dict("records"):
            has_quals = df_fn("SELECT qualification FROM employee_qualifications WHERE employee_id=?",
                              (emp_data["id"],))["qualification"].tolist() if not df_fn("SELECT qualification FROM employee_qualifications WHERE employee_id=?", (emp_data["id"],)).empty else []
            missing_req = [q for q in REQUIRED if q not in has_quals]
            missing_rec = [q for q in RECOMMENDED if q not in has_quals]
            status = "✅ OK" if not missing_req else f"❌ Fehlt: {', '.join(missing_req)}"
            with st.expander(f"{emp_data['name']} — {status}"):
                if missing_req:
                    st.error(f"PFLICHT fehlt: {', '.join(missing_req)}")
                if missing_rec:
                    st.info(f"Empfohlen fehlt: {', '.join(missing_rec)}")
                if not missing_req and not missing_rec:
                    st.success("Alle Qualifikationen vorhanden")

    with tabs[3]:
        st.markdown("""
**§34a GewO – Anforderungen Bewachungsgewerbe:**

| Anforderung | Für wen | Rechtliche Grundlage |
|---|---|---|
| Unterrichtung (40h) | Alle Mitarbeiter | §34a Abs. 1 GewO |
| Sachkundeprüfung IHK | Türsteher, Pförtner, Ermittler | §34a Abs. 1 Satz 5 GewO |
| Bewacherregistrierung | Alle Mitarbeiter | §11b BewachVO |
| Führungszeugnis (polizeiliches) | Alle Mitarbeiter | §34a Abs. 1 GewO |
| Zuverlässigkeitsprüfung | Gewerbetreibende + Mitarbeiter | §34a Abs. 1 GewO |

**Bewacherregister:**
- Eintragung Mitarbeiter: www.bewacherregister.de
- Kosten: 11,80 € je Mitarbeiter + Jahr
- Aktualisierung: bei Änderungen unverzüglich

**Neue Anforderungen ab 2023:**
- Digitale Meldung über Bewacherregister verpflichtend
- Nachweise auf Anfrage bereithalten
        """)
