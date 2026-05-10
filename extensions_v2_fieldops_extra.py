"""
extensions_v2_fieldops_extra.py – Letzte fehlende Features
============================================================
1. Einsatzplanung Großveranstaltungen (Events)
2. Dienstanweisung-Generator (Objekt-spezifisch)
3. Wartungsvertrag-Generator aus Inventar
4. Kundenzufriedenheits-Umfragen
5. Darlehens-/Finanzierungs-Tracking
6. Interne Wissensdatenbank / Wiki
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
import json
import secrets

import pandas as pd
import streamlit as st


def fmt_eur(v: float) -> str:
    return f"{v:,.2f} €".replace(",", "X").replace(".", ",").replace("X", ".")


# ─────────────────────────────────────────────────────────────
# DB-Registrierung
# ─────────────────────────────────────────────────────────────

def register_fieldops_extra(run_fn, df_fn) -> None:
    run_fn("""CREATE TABLE IF NOT EXISTS loans (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        loan_no TEXT UNIQUE NOT NULL,
        lender TEXT NOT NULL,
        purpose TEXT,
        loan_amount REAL NOT NULL,
        interest_rate REAL DEFAULT 0,
        start_date TEXT NOT NULL,
        end_date TEXT,
        monthly_rate REAL DEFAULT 0,
        remaining_balance REAL DEFAULT 0,
        status TEXT DEFAULT 'aktiv',
        notes TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )""")
    run_fn("""CREATE TABLE IF NOT EXISTS loan_payments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        loan_id INTEGER NOT NULL,
        payment_date TEXT NOT NULL,
        amount REAL NOT NULL,
        principal REAL DEFAULT 0,
        interest REAL DEFAULT 0,
        notes TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(loan_id) REFERENCES loans(id)
    )""")
    run_fn("""CREATE TABLE IF NOT EXISTS wiki_articles (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        slug TEXT UNIQUE NOT NULL,
        title TEXT NOT NULL,
        category TEXT DEFAULT 'Allgemein',
        content TEXT NOT NULL,
        tags TEXT DEFAULT '[]',
        author TEXT,
        views INTEGER DEFAULT 0,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )""")
    # Seed Wissensdatenbank mit Basis-Artikeln
    starter_articles = [
        ("gewa-34a", "§34a GewO Grundlagen",
         "Sicherheit & Recht",
         """## §34a GewO – Bewachungsgewerbe

### Wer benötigt eine Erlaubnis?
Wer gewerbsmäßig Leben oder Eigentum fremder Personen bewacht, benötigt eine Erlaubnis nach §34a GewO.

### Mitarbeiter-Anforderungen
- **Unterrichtung (40h)**: Alle Mitarbeiter vor Einsatz
- **Sachkundeprüfung**: Für besondere Tätigkeiten (Türsteher, Kontrollräume)
- **Bewacherregistrierung**: Pflicht seit 01.04.2019
- **Führungszeugnis**: Erweitert, max. 3 Jahre alt

### Pflichten des Unternehmers
- Regelmäßige Schulungen dokumentieren
- Dienstanweisungen für jedes Objekt erstellen
- Unfallmeldungen an BG Sicherheitswirtschaft
- Führen eines Wachbuchs (digital oder Papier)

### BG Sicherheitswirtschaft
Kontakt: www.bgsg.de | Tel: 06221 5108-0
"""),
        ("notrufnummern", "Notrufnummern & Erstmaßnahmen",
         "Notfall & Sicherheit",
         """## Wichtige Notrufnummern

| Dienst | Nummer |
|---|---|
| Polizei | **110** |
| Feuerwehr & Rettung | **112** |
| Ärztlicher Bereitschaftsdienst | **116 117** |
| Giftnotruf | **0800 192 11 92** |

## Verhalten im Notfall

### Brand
1. Menschen retten, nicht löschen
2. Feuerwehr rufen (112)
3. Türen schließen (kein Aufzug!)
4. Sammelplatz aufsuchen
5. Rückmeldung an Einsatzleitung

### Einbruch / Alarm
1. KEINE Eigensicherung durch Mitarbeiter
2. Polizei rufen (110)
3. Objekt sichern, nicht betreten
4. Vorgesetzten informieren
5. Protokoll anfertigen
"""),
        ("schicht-checkliste", "Schicht-Checkliste",
         "Betrieb",
         """## Checkliste Schichtbeginn

☐ Dienstanweisung gelesen/bekannt  
☐ Funk/Kommunikation geprüft  
☐ Schlüssel übernommen (Quittung)  
☐ Schlüssel gezählt  
☐ Übergabe-Protokoll gelesen  
☐ Rundgang durchgeführt  
☐ Besonderheiten notiert  

## Checkliste Schichtende

☐ Abschlussbericht verfasst  
☐ Schlüssel übergeben (Quittung)  
☐ Besonderheiten an Nachfolger  
☐ Wachbuch abgezeichnet  
☐ Dienstfahrzeug übergeben  
"""),
    ]
    for slug, title, cat, content in starter_articles:
        try:
            run_fn("INSERT OR IGNORE INTO wiki_articles(slug,title,category,content,author) VALUES(?,?,?,?,?)",
                   (slug, title, cat, content, "System"))
        except Exception:
            pass


# ─────────────────────────────────────────────────────────────
# 1. Einsatzplanung Großveranstaltungen
# ─────────────────────────────────────────────────────────────

def page_event_security(run_fn, df_fn, next_number_fn, log_fn) -> None:
    st.title("🎪 Einsatzplanung Großveranstaltungen")
    st.caption("Planung und Koordination von Veranstaltungsschutz-Einsätzen.")

    tabs = st.tabs(["📋 Alle Veranstaltungen", "➕ Neue Veranstaltung",
                    "👥 Personal zuweisen", "📊 Auswertung"])

    with tabs[0]:
        events = df_fn("""
            SELECT e.id, e.event_no AS Nr, e.event_name AS Veranstaltung,
                   e.event_date AS Datum, e.event_time_start AS Von,
                   e.event_time_end AS Bis, e.venue AS Veranstaltungsort,
                   COALESCE(c.company,'–') AS Auftraggeber,
                   e.expected_visitors AS Besucher,
                   e.staff_required AS Personal_Soll,
                   e.staff_assigned AS Personal_Ist,
                   e.status AS Status
            FROM events_security e LEFT JOIN customers c ON c.id=e.customer_id
            ORDER BY e.event_date DESC
        """)
        if not events.empty:
            today = date.today().isoformat()
            upcoming = events[events["Datum"] >= today]
            c1, c2, c3 = st.columns(3)
            c1.metric("Veranstaltungen gesamt", len(events))
            c2.metric("Bevorstehend", len(upcoming))
            c3.metric("Personal geplant", int(events["Personal_Soll"].sum()))

            filter_status = st.selectbox("Status filtern",
                ["alle","geplant","bestätigt","laufend","abgeschlossen","abgesagt"])
            df_show = events if filter_status == "alle" else events[events["Status"]==filter_status]
            st.dataframe(df_show.drop(columns=["id"]), use_container_width=True, height=350)
        else:
            st.info("Noch keine Veranstaltungen geplant.")

    with tabs[1]:
        customers = df_fn("SELECT id, customer_no || ' – ' || company AS label FROM customers ORDER BY company")
        with st.form("event_form", clear_on_submit=True):
            ev_no = st.text_input("Veranstaltungs-Nr.",
                                   next_number_fn("events_security","event_no","EVT-"))
            col1, col2 = st.columns(2)
            name  = col1.text_input("Veranstaltungsname *")
            venue = col2.text_input("Veranstaltungsort *")
            col3, col4, col5 = st.columns(3)
            ev_date = col3.date_input("Datum *", date.today() + timedelta(days=30))
            t_start = col4.time_input("Beginn", datetime.strptime("18:00","%H:%M").time())
            t_end   = col5.time_input("Ende",   datetime.strptime("23:00","%H:%M").time())
            cust_label = col1.selectbox("Auftraggeber",
                ["—"] + (customers["label"].tolist() if not customers.empty else []))
            expected_v = col2.number_input("Erwartete Besucher", min_value=0, value=500, step=100)
            col6, col7 = st.columns(2)
            staff_req  = col6.number_input("Benötigtes Personal", min_value=1, value=5, step=1)
            brief_time = col7.time_input("Briefing-Zeit",
                                          datetime.strptime("17:00","%H:%M").time())
            equipment  = st.text_area("Benötigte Ausrüstung (Funkgeräte, Absperrbänder, etc.)")
            concept    = st.text_area("Sicherheitskonzept (Aufgaben, Positionen, Ablauf)")
            notes      = st.text_area("Notizen")
            submitted  = st.form_submit_button("💾 Veranstaltung speichern", type="primary")

        if submitted and name and venue:
            cid = None
            if cust_label != "—" and not customers.empty:
                match = customers[customers["label"] == cust_label]
                if not match.empty: cid = int(match.iloc[0]["id"])
            run_fn("""INSERT INTO events_security(event_no,customer_id,event_name,event_date,
                      event_time_start,event_time_end,venue,expected_visitors,
                      staff_required,equipment_needed,security_concept,briefing_time,notes)
                      VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                   (ev_no, cid, name, ev_date.isoformat(),
                    t_start.strftime("%H:%M"), t_end.strftime("%H:%M"),
                    venue, expected_v, staff_req, equipment, concept,
                    brief_time.strftime("%H:%M"), notes))
            log_fn("event_created", f"{ev_no} {name}")
            st.success(f"✅ Veranstaltung '{name}' am {ev_date.isoformat()} angelegt!")
            st.rerun()

    with tabs[2]:
        ev_list = df_fn("""
            SELECT id, event_no || ' – ' || event_name || ' (' || event_date || ')' AS label,
                   staff_required, staff_assigned
            FROM events_security WHERE status IN ('geplant','bestätigt')
            ORDER BY event_date
        """)
        if ev_list.empty:
            st.info("Keine geplanten Veranstaltungen.")
            return
        sel = st.selectbox("Veranstaltung", ev_list["label"].tolist())
        eid = int(ev_list[ev_list["label"] == sel].iloc[0]["id"])
        req = int(ev_list[ev_list["label"] == sel].iloc[0]["staff_required"])
        asn = int(ev_list[ev_list["label"] == sel].iloc[0]["staff_assigned"])
        st.metric("Personal Soll/Ist", f"{asn}/{req}")

        # Schichten für diese Veranstaltung
        ev_data = df_fn("SELECT * FROM events_security WHERE id=?", (eid,)).iloc[0].to_dict()
        employees = df_fn("SELECT id, employee_no || ' – ' || name AS label FROM employees WHERE active=1 ORDER BY name")

        selected_emps = st.multiselect(
            "Mitarbeiter zuweisen",
            employees["label"].tolist() if not employees.empty else [],
            max_selections=req
        )
        shift_type = st.text_input("Aufgabe/Position", "Veranstaltungsschutz")
        if selected_emps and st.button(f"✅ {len(selected_emps)} Mitarbeiter einplanen", type="primary"):
            created = 0
            for emp_label in selected_emps:
                eid2 = int(employees[employees["label"] == emp_label].iloc[0]["id"])
                run_fn("""INSERT INTO shifts(employee_id,customer_id,shift_date,
                          start_time,end_time,shift_type,status,location)
                          VALUES(?,?,?,?,?,?,?,?)""",
                       (eid2, ev_data.get("customer_id"),
                        str(ev_data.get("event_date","")),
                        str(ev_data.get("event_time_start","00:00")),
                        str(ev_data.get("event_time_end","23:59")),
                        shift_type, "geplant", str(ev_data.get("venue",""))))
                created += 1
            run_fn("UPDATE events_security SET staff_assigned=staff_assigned+? WHERE id=?",
                   (created, eid))
            log_fn("event_staff_assigned", f"{sel}: {created} MA")
            st.success(f"✅ {created} Mitarbeiter für '{sel}' eingeplant!")
            st.rerun()

    with tabs[3]:
        stats = df_fn("""
            SELECT status AS Status, COUNT(*) AS Veranstaltungen,
                   SUM(expected_visitors) AS Besucher_gesamt,
                   SUM(staff_required) AS Personal_gesamt
            FROM events_security GROUP BY status
        """)
        if not stats.empty:
            st.dataframe(stats, use_container_width=True)


# ─────────────────────────────────────────────────────────────
# 2. Dienstanweisung-Generator
# ─────────────────────────────────────────────────────────────

def generate_duty_instruction_pdf(instruction: dict, object_data: dict,
                                   get_setting_fn, base_dir: Path) -> Optional[Path]:
    """Erstellt eine Dienstanweisung als PDF."""
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib import colors
        from reportlab.lib.units import mm
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable
    except ImportError:
        return None

    co_name = get_setting_fn("company_name", "Byblos Sicherheitsdienst")
    output_dir = base_dir / "generated" / "instructions"
    output_dir.mkdir(parents=True, exist_ok=True)
    fname = f"DA_{str(instruction.get('instruction_no','DA')).replace('/','-')}.pdf"
    output_path = output_dir / fname

    doc = SimpleDocTemplate(str(output_path), pagesize=A4,
                            rightMargin=20*mm, leftMargin=20*mm,
                            topMargin=15*mm, bottomMargin=15*mm)
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="Sm", fontSize=8, leading=10))
    story = []

    story.append(Paragraph(f"<b>DIENSTANWEISUNG</b>", styles["h1"]))
    story.append(Paragraph(f"{co_name} | {instruction.get('instruction_no','')} | Version {instruction.get('version','1.0')}", styles["Sm"]))
    story.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor("#c0392b")))
    story.append(Spacer(1, 5*mm))
    story.append(Paragraph(f"<b>Objekt:</b> {object_data.get('name','')}", styles["Normal"]))
    story.append(Paragraph(f"<b>Adresse:</b> {object_data.get('address','')}", styles["Normal"]))
    story.append(Paragraph(f"<b>Gültig ab:</b> {instruction.get('valid_from','')}", styles["Normal"]))
    story.append(Spacer(1, 5*mm))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#ccc")))
    story.append(Spacer(1, 4*mm))
    story.append(Paragraph(f"<b>{instruction.get('title','')}</b>", styles["h2"]))
    story.append(Spacer(1, 3*mm))

    # Inhalt Zeilenweise
    content = str(instruction.get("content",""))
    for para in content.split("\n"):
        if para.strip():
            story.append(Paragraph(para, styles["Normal"]))
            story.append(Spacer(1, 2*mm))

    story.append(Spacer(1, 10*mm))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#ccc")))
    story.append(Paragraph("Ich bestätige, diese Dienstanweisung gelesen und verstanden zu haben.", styles["Normal"]))
    story.append(Spacer(1, 8*mm))
    sig_line = "_" * 40 + "    " + "_" * 40
    story.append(Paragraph(f"{sig_line}", styles["Normal"]))
    story.append(Paragraph("Name, Datum                                          Unterschrift", styles["Sm"]))

    doc.build(story)
    return output_path


def page_duty_instructions(run_fn, df_fn, next_number_fn, log_fn,
                            get_setting_fn, base_dir: Path) -> None:
    st.title("📋 Dienstanweisungen")
    st.caption("Objekt-spezifische Dienstanweisungen erstellen, verwalten und als PDF drucken.")

    TEMPLATES = {
        "Objektschutz Standard": """AUFGABEN:
1. Regelmäßige Rundgänge alle 2 Stunden durchführen
2. Alle Türen und Fenster auf Verschluss prüfen
3. Verdächtige Personen ansprechen und ggf. melden
4. Wachbuch nach jedem Rundgang ausfüllen
5. Schlüssel nur nach Legitimation aushändigen

VERHALTEN BEI STÖRUNGEN:
- Polizei (110) oder Feuerwehr (112) rufen
- Objekt sichern, nicht selbst eingreifen
- Vorgesetzten informieren: [NUMMER]
- Protokoll anfertigen

VERBOTEN:
- Schlüssel weitergeben ohne Quittung
- Objekt unbewacht verlassen
- Handy privat im Dienst nutzen""",

        "Empfang / Zutrittskontrolle": """AUFGABEN:
1. Alle Personen beim Betreten registrieren
2. Ausweiskontrolle bei Fremden
3. Besucherbuch führen
4. Schließanlage überwachen
5. Pakete und Lieferungen annehmen und dokumentieren

ZUTRITTSBERECHTIGUNG:
- Mitarbeiter: Ausweis/Chip
- Besucher: Anmeldung prüfen, Besucherausweis ausstellen
- Handwerker: Auftrag prüfen, Begleitperson

MELDUNGEN:
- Unerlaubter Zutritt sofort melden
- Verdächtige Gegenstände: 110 rufen, Bereich sperren""",
    }

    tabs = st.tabs(["📋 Alle Anweisungen", "➕ Neue Anweisung",
                    "📄 PDF drucken", "✍️ Kenntnisnahme"])

    with tabs[0]:
        instructions = df_fn("""
            SELECT da.id, da.instruction_no AS Nr, da.title AS Titel,
                   COALESCE(o.name,'Alle') AS Objekt, da.version AS Version,
                   da.valid_from AS Gültig_ab, da.active AS Aktiv
            FROM duty_instructions da LEFT JOIN objects o ON o.id=da.object_id
            ORDER BY da.valid_from DESC
        """)
        if not instructions.empty:
            st.dataframe(instructions.drop(columns=["id"]), use_container_width=True)
        else:
            st.info("Noch keine Dienstanweisungen.")

    with tabs[1]:
        objects = df_fn("SELECT id, name FROM objects WHERE active=1 ORDER BY name")
        with st.form("da_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            da_no   = col1.text_input("DA-Nr.",
                                       next_number_fn("duty_instructions","instruction_no","DA-"))
            version = col2.text_input("Version", "1.0")
            title   = st.text_input("Titel der Dienstanweisung *")
            obj_sel = st.selectbox("Objekt (leer = alle)",
                                    ["Alle Objekte"] + (objects["name"].tolist() if not objects.empty else []))
            col3, col4 = st.columns(2)
            valid_from = col3.date_input("Gültig ab", date.today())
            valid_until = col4.date_input("Gültig bis (optional)", date.today() + timedelta(days=365))
            has_end = col4.checkbox("Ablaufdatum setzen", value=False)

            template = st.selectbox("Vorlage laden", ["– Eigener Text –"] + list(TEMPLATES.keys()))
            default_content = TEMPLATES.get(template, "")
            content = st.text_area("Inhalt der Dienstanweisung *", default_content, height=300)
            submitted = st.form_submit_button("💾 Speichern", type="primary")

        if submitted and title and content:
            oid = None
            if obj_sel != "Alle Objekte" and not objects.empty:
                match = objects[objects["name"] == obj_sel]
                if not match.empty: oid = int(match.iloc[0]["id"])
            run_fn("""INSERT INTO duty_instructions(instruction_no,object_id,title,version,
                      content,valid_from,valid_until,created_by)
                      VALUES(?,?,?,?,?,?,?,?)""",
                   (da_no, oid, title, version, content, valid_from.isoformat(),
                    valid_until.isoformat() if has_end else None, "admin"))
            log_fn("duty_instruction_created", f"{da_no} {title}")
            st.success(f"✅ Dienstanweisung '{title}' erstellt!"); st.rerun()

    with tabs[2]:
        da_list = df_fn("""
            SELECT da.id, da.instruction_no || ' – ' || da.title AS label
            FROM duty_instructions da WHERE da.active=1 ORDER BY da.instruction_no
        """)
        if da_list.empty:
            st.info("Keine aktiven Dienstanweisungen.")
            return
        sel_da = st.selectbox("Dienstanweisung auswählen", da_list["label"].tolist())
        da_id  = int(da_list[da_list["label"] == sel_da].iloc[0]["id"])

        if st.button("📄 PDF erstellen", type="primary"):
            da_data = df_fn("SELECT * FROM duty_instructions WHERE id=?", (da_id,)).iloc[0].to_dict()
            obj_data = {}
            if da_data.get("object_id"):
                obj_row = df_fn("SELECT * FROM objects WHERE id=?", (da_data["object_id"],))
                if not obj_row.empty:
                    obj_data = obj_row.iloc[0].to_dict()

            with st.spinner("PDF wird erstellt..."):
                path = generate_duty_instruction_pdf(da_data, obj_data, get_setting_fn, base_dir)
            if path and path.exists():
                st.success(f"✅ {path.name}")
                st.download_button("📥 PDF herunterladen",
                                   path.read_bytes(), path.name, "application/pdf")
            else:
                st.error("PDF-Erstellung fehlgeschlagen.")

    with tabs[3]:
        st.subheader("Kenntnisnahme verwalten")
        da_list2 = df_fn("SELECT id, instruction_no || ' – ' || title AS label FROM duty_instructions WHERE active=1")
        employees = df_fn("SELECT id, name FROM employees WHERE active=1 ORDER BY name")
        if not da_list2.empty and not employees.empty:
            sel_da2 = st.selectbox("Dienstanweisung", da_list2["label"].tolist(), key="ack_da")
            da_id2 = int(da_list2[da_list2["label"] == sel_da2].iloc[0]["id"])
            # Wer hat bestätigt?
            ack_json = df_fn("SELECT acknowledged_by FROM duty_instructions WHERE id=?", (da_id2,))
            acks = json.loads(str(ack_json.iloc[0]["acknowledged_by"]) or "[]") if not ack_json.empty else []

            col1, col2 = st.columns(2)
            col1.subheader("✅ Bestätigt")
            col1.write("\n".join(acks) if acks else "– Niemand –")
            not_acked = [e for e in employees["name"].tolist() if e not in acks]
            col2.subheader("⏳ Ausstehend")
            col2.write("\n".join(not_acked) if not_acked else "– Alle bestätigt –")

            emp_sel = st.selectbox("Kenntnisnahme eintragen", not_acked) if not_acked else None
            if emp_sel and st.button("✅ Kenntnisnahme bestätigen", type="primary"):
                new_acks = json.dumps(acks + [emp_sel])
                run_fn("UPDATE duty_instructions SET acknowledged_by=? WHERE id=?", (new_acks, da_id2))
                st.success(f"✅ {emp_sel} hat Kenntnis bestätigt.")
                st.rerun()


# ─────────────────────────────────────────────────────────────
# 3. Wartungsvertrag-Generator aus Inventar
# ─────────────────────────────────────────────────────────────

def page_maintenance_contracts(run_fn, df_fn, next_number_fn, log_fn, get_setting_fn) -> None:
    st.title("🔧 Wartungsvertrag-Generator")
    st.caption("Aus Inventar-Einträgen automatisch Wartungsverträge vorschlagen.")

    tabs = st.tabs(["📋 Fällige Wartungen", "📄 Wartungsvertrag erstellen", "📊 Übersicht"])

    with tabs[0]:
        today = date.today().isoformat()
        warn90 = (date.today() + timedelta(days=90)).isoformat()

        items = df_fn(f"""
            SELECT i.item_no AS Nr, i.name AS Gerät, i.category AS Kategorie,
                   i.location AS Standort,
                   COALESCE(e.name,'–') AS Zugewiesen_an,
                   i.next_maintenance AS Nächste_Wartung,
                   CAST(julianday(i.next_maintenance) - julianday('now') AS INT) AS Tage_verbleibend
            FROM inventory i LEFT JOIN employees e ON e.id=i.assigned_to
            WHERE i.next_maintenance IS NOT NULL AND i.next_maintenance <= '{warn90}'
            ORDER BY i.next_maintenance
        """)
        if not items.empty:
            already_due = items[items["Tage_verbleibend"] < 0]
            upcoming    = items[items["Tage_verbleibend"] >= 0]
            if not already_due.empty:
                st.error(f"❌ {len(already_due)} Wartungen ÜBERFÄLLIG!")
                st.dataframe(already_due, use_container_width=True)
            if not upcoming.empty:
                st.warning(f"⚠️ {len(upcoming)} Wartungen in 90 Tagen fällig:")
                st.dataframe(upcoming, use_container_width=True)
        else:
            st.success("✅ Keine fälligen Wartungen.")

    with tabs[1]:
        inventory = df_fn("SELECT id, item_no || ' – ' || name AS label FROM inventory WHERE active=1 ORDER BY name")
        if inventory.empty:
            st.info("Keine Inventar-Einträge.")
            return
        sel = st.selectbox("Gerät / Anlage", inventory["label"].tolist())
        iid = int(inventory[inventory["label"] == sel].iloc[0]["id"])
        item_data = df_fn("SELECT * FROM inventory WHERE id=?", (iid,)).iloc[0].to_dict()

        st.divider()
        company_name = get_setting_fn("company_name","Byblos Sicherheitsdienst")
        contractor = st.text_input("Wartungsdienstleister")
        col1, col2 = st.columns(2)
        maint_interval = col1.selectbox("Wartungsintervall", ["monatlich","vierteljährlich","halbjährlich","jährlich"])
        maint_cost = col2.number_input("Kosten pro Wartung (€)", min_value=0.0, value=150.0, step=10.0)
        start_date = col1.date_input("Vertragsbeginn", date.today())
        end_date   = col2.date_input("Vertragsende", date.today() + timedelta(days=365))

        # Wartungsplan generieren
        plan = []
        current = start_date
        delta_map = {"monatlich":30,"vierteljährlich":91,"halbjährlich":182,"jährlich":365}
        delta = timedelta(days=delta_map[maint_interval])
        while current <= end_date:
            plan.append(current.isoformat())
            current += delta

        st.info(f"📅 {len(plan)} Wartungstermine generiert · Gesamtkosten: {fmt_eur(len(plan)*maint_cost)}")
        if st.button("📄 Wartungsvertrag anlegen", type="primary") and contractor:
            # Als Lieferanten-Eintrag + Kalendereinträge
            for dt in plan:
                run_fn("INSERT OR IGNORE INTO tax_calendar(due_date,tax_type,description,status) VALUES(?,?,?,?)",
                       (dt, "Wartung", f"{item_data.get('name','')} – Wartung durch {contractor}", "offen"))
            # Nächste Wartung im Inventar aktualisieren
            run_fn("UPDATE inventory SET next_maintenance=? WHERE id=?", (plan[0] if plan else None, iid))
            log_fn("maintenance_contract_created", f"{sel} {contractor}")
            st.success(f"✅ {len(plan)} Wartungstermine in Steuerkalender eingetragen!")
            st.rerun()

    with tabs[2]:
        all_maint = df_fn("""
            SELECT tc.due_date AS Datum, tc.description AS Beschreibung, tc.status AS Status
            FROM tax_calendar tc WHERE tc.tax_type='Wartung'
            ORDER BY tc.due_date
        """)
        if not all_maint.empty:
            c1, c2 = st.columns(2)
            c1.metric("Wartungstermine gesamt", len(all_maint))
            c2.metric("Offen", len(all_maint[all_maint["Status"]=="offen"]))
            st.dataframe(all_maint, use_container_width=True)
        else:
            st.info("Noch keine Wartungsverträge erfasst.")


# ─────────────────────────────────────────────────────────────
# 4. Darlehens-/Finanzierungs-Tracking
# ─────────────────────────────────────────────────────────────

def page_loan_tracking(run_fn, df_fn, next_number_fn, log_fn) -> None:
    st.title("🏦 Darlehens-Tracking")
    st.caption("Finanzierungen, Darlehen und Ratenzahlungen verwalten.")

    tabs = st.tabs(["📋 Alle Darlehen", "➕ Neues Darlehen",
                    "💳 Rate buchen", "📊 Tilgungsplan"])

    with tabs[0]:
        loans = df_fn("""
            SELECT loan_no AS Nr, lender AS Darlehensgeber, purpose AS Zweck,
                   loan_amount AS Darlehensbetrag, interest_rate AS Zinssatz_Pct,
                   monthly_rate AS Rate_EUR, remaining_balance AS Restschuld,
                   end_date AS Laufzeitende, status AS Status
            FROM loans ORDER BY created_at DESC
        """)
        if not loans.empty:
            c1, c2, c3 = st.columns(3)
            c1.metric("Aktive Darlehen", len(loans[loans["Status"]=="aktiv"]))
            c2.metric("Gesamtschuld", fmt_eur(float(loans[loans["Status"]=="aktiv"]["Restschuld"].sum())))
            c3.metric("Monatliche Raten", fmt_eur(float(loans[loans["Status"]=="aktiv"]["Rate_EUR"].sum())))
            st.dataframe(loans, use_container_width=True)
        else:
            st.info("Noch keine Darlehen erfasst.")

    with tabs[1]:
        with st.form("loan_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            loan_no = col1.text_input("Darlehens-Nr.",
                                       next_number_fn("loans","loan_no","DAR-"))
            lender  = col2.text_input("Darlehensgeber (Bank, Person) *")
            purpose = st.text_input("Verwendungszweck")
            col3, col4, col5 = st.columns(3)
            amount    = col3.number_input("Darlehensbetrag (€)", min_value=100.0, value=10000.0, step=500.0)
            rate_pct  = col4.number_input("Zinssatz (% p.a.)", min_value=0.0, value=5.0, step=0.1)
            monthly   = col5.number_input("Monatliche Rate (€)", min_value=0.0, value=200.0, step=10.0)
            col6, col7 = st.columns(2)
            start_d   = col6.date_input("Start", date.today())
            end_d     = col7.date_input("Laufzeitende", date.today() + timedelta(days=365*5))
            notes     = st.text_area("Notizen")
            submitted = st.form_submit_button("💾 Darlehen anlegen", type="primary")

        if submitted and lender:
            run_fn("""INSERT INTO loans(loan_no,lender,purpose,loan_amount,interest_rate,
                      monthly_rate,remaining_balance,start_date,end_date,notes)
                      VALUES(?,?,?,?,?,?,?,?,?,?)""",
                   (loan_no, lender, purpose, amount, rate_pct, monthly,
                    amount, start_d.isoformat(), end_d.isoformat(), notes))
            log_fn("loan_created", f"{loan_no} {lender} {amount}€")
            st.success(f"✅ Darlehen {loan_no} über {fmt_eur(amount)} angelegt!"); st.rerun()

    with tabs[2]:
        active_loans = df_fn("SELECT id, loan_no || ' – ' || lender || ' (' || remaining_balance || '€)' AS label FROM loans WHERE status='aktiv'")
        if active_loans.empty:
            st.info("Keine aktiven Darlehen.")
            return
        sel = st.selectbox("Darlehen", active_loans["label"].tolist())
        lid = int(active_loans[active_loans["label"] == sel].iloc[0]["id"])
        loan_data = df_fn("SELECT * FROM loans WHERE id=?", (lid,)).iloc[0].to_dict()

        with st.form("pay_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            pay_date   = col1.date_input("Zahlungsdatum", date.today())
            pay_amount = col2.number_input("Betrag (€)", value=float(loan_data.get("monthly_rate",0)), step=10.0)
            interest_portion = round(float(loan_data.get("remaining_balance",0)) *
                                      float(loan_data.get("interest_rate",0)) / 100 / 12, 2)
            principal_portion = round(pay_amount - interest_portion, 2)
            st.caption(f"Davon Zinsen: {fmt_eur(interest_portion)} · Tilgung: {fmt_eur(principal_portion)}")
            if st.form_submit_button("💳 Rate buchen", type="primary"):
                new_balance = max(0, float(loan_data.get("remaining_balance",0)) - principal_portion)
                run_fn("INSERT INTO loan_payments(loan_id,payment_date,amount,principal,interest) VALUES(?,?,?,?,?)",
                       (lid, pay_date.isoformat(), pay_amount, principal_portion, interest_portion))
                run_fn("UPDATE loans SET remaining_balance=? WHERE id=?", (new_balance, lid))
                if new_balance <= 0:
                    run_fn("UPDATE loans SET status='getilgt' WHERE id=?", (lid,))
                    st.success("🎉 Darlehen vollständig getilgt!")
                else:
                    st.success(f"✅ Rate gebucht. Restschuld: {fmt_eur(new_balance)}")
                log_fn("loan_payment", f"{sel} {pay_amount}€")
                st.rerun()

    with tabs[3]:
        all_loans = df_fn("SELECT id, loan_no || ' – ' || lender AS label FROM loans WHERE status='aktiv'")
        if all_loans.empty: return
        sel2 = st.selectbox("Darlehen", all_loans["label"].tolist(), key="tp_sel")
        lid2 = int(all_loans[all_loans["label"] == sel2].iloc[0]["id"])
        payments = df_fn("""
            SELECT payment_date AS Datum, amount AS Rate_EUR,
                   principal AS Tilgung, interest AS Zinsen
            FROM loan_payments WHERE loan_id=? ORDER BY payment_date
        """, (lid2,))
        if not payments.empty:
            st.dataframe(payments, use_container_width=True)
            c1, c2, c3 = st.columns(3)
            c1.metric("Gezahlte Raten", len(payments))
            c2.metric("Gesamttilgung", fmt_eur(float(payments["Tilgung"].sum())))
            c3.metric("Gezahlte Zinsen", fmt_eur(float(payments["Zinsen"].sum())))
        else:
            st.info("Noch keine Ratenzahlungen.")


# ─────────────────────────────────────────────────────────────
# 5. Kundenzufriedenheits-Umfragen
# ─────────────────────────────────────────────────────────────

def page_satisfaction_surveys(run_fn, df_fn, next_number_fn, log_fn,
                               queue_email_fn, get_setting_fn) -> None:
    st.title("⭐ Kundenzufriedenheits-Umfragen")
    st.caption("Automatische Zufriedenheitsbefragung nach Auftragsabschluss.")

    tabs = st.tabs(["📤 Umfrage versenden", "📊 Auswertung", "💬 Feedback"])

    with tabs[0]:
        customers = df_fn("""
            SELECT c.id, c.customer_no || ' – ' || c.company AS label, c.email
            FROM customers c WHERE c.email IS NOT NULL AND c.email != ''
            ORDER BY c.company
        """)
        if customers.empty:
            st.info("Keine Kunden mit E-Mail-Adresse.")
            return

        sel = st.selectbox("Kunde", customers["label"].tolist())
        row = customers[customers["label"] == sel].iloc[0]
        cid = int(row["id"])
        email = str(row["email"])
        co_name = get_setting_fn("company_name","Byblos Sicherheitsdienst")
        base_url = get_setting_fn("payment_base_url","http://localhost:8501")

        last_sent = df_fn("""
            SELECT sent_date FROM satisfaction_surveys WHERE customer_id=?
            ORDER BY sent_date DESC LIMIT 1
        """, (cid,))
        if not last_sent.empty:
            st.caption(f"Letzte Umfrage: {str(last_sent.iloc[0]['sent_date'])[:10]}")

        col1, col2 = st.columns(2)
        send_btn = col1.button("📧 Umfrage versenden", type="primary")
        preview  = col2.button("👁️ E-Mail Vorschau")

        token = secrets.token_urlsafe(16)
        survey_url = f"{base_url}?survey={token}"
        body = (f"Sehr geehrte Damen und Herren,\n\n"
                f"Vielen Dank für Ihr Vertrauen in {co_name}.\n\n"
                f"Wir würden uns sehr freuen, wenn Sie sich 2 Minuten Zeit nehmen, "
                f"um unsere Leistung zu bewerten:\n\n"
                f"👉 {survey_url}\n\n"
                f"Ihre Meinung hilft uns, unseren Service kontinuierlich zu verbessern.\n\n"
                f"Mit freundlichen Grüßen\n{co_name}")

        if preview:
            st.text_area("E-Mail-Vorschau", body, height=200)

        if send_btn:
            queue_email_fn(email, f"Wie zufrieden sind Sie mit {co_name}?", body, "")
            run_fn("""INSERT INTO satisfaction_surveys(customer_id,sent_date,token,status)
                      VALUES(?,?,?,?)""",
                   (cid, date.today().isoformat(), token, "gesendet"))
            log_fn("survey_sent", f"{sel}")
            st.success(f"✅ Umfrage an {email} gesendet!")
            st.rerun()

    with tabs[1]:
        results = df_fn("""
            SELECT ss.sent_date AS Gesendet, c.company AS Kunde,
                   ss.rating AS Bewertung, ss.status AS Status,
                   ss.responded_at AS Beantwortet_am
            FROM satisfaction_surveys ss JOIN customers c ON c.id=ss.customer_id
            ORDER BY ss.sent_date DESC LIMIT 50
        """)
        if not results.empty:
            answered = results[results["Bewertung"].notna()]
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Versendete Umfragen", len(results))
            c2.metric("Rücklaufquote", f"{len(answered)/len(results)*100:.0f}%")
            if not answered.empty:
                avg_rating = float(answered["Bewertung"].mean())
                stars = "⭐" * int(round(avg_rating))
                c3.metric("Ø Bewertung", f"{avg_rating:.1f}/5 {stars}")
                c4.metric("Vollständige Rückantworten", len(answered))
            st.dataframe(results, use_container_width=True)
            # Rating-Chart
            if not answered.empty:
                rating_counts = answered["Bewertung"].value_counts().sort_index()
                st.bar_chart(rating_counts)

    with tabs[2]:
        # Simulate: In der echten App würde ein GET-Parameter den Feedback-Eingang triggern
        st.subheader("Feedback manuell eintragen")
        st.caption("(Automatischer Empfang via URL-Parameter in der Live-Deployment-Version)")
        pending = df_fn("""
            SELECT ss.id, c.company AS Kunde, ss.sent_date AS Gesendet
            FROM satisfaction_surveys ss JOIN customers c ON c.id=ss.customer_id
            WHERE ss.status='gesendet' ORDER BY ss.sent_date DESC LIMIT 20
        """)
        if not pending.empty:
            sel_s = st.selectbox("Umfrage", [f"{r['Kunde']} ({r['Gesendet'][:10]})" for _, r in pending.iterrows()])
            sid   = int(pending.iloc[0]["id"])
            col1, col2 = st.columns(2)
            rating = col1.slider("Bewertung (1–5 Sterne)", 1, 5, 4)
            feedback = col2.text_area("Kommentar")
            if st.button("💾 Feedback speichern"):
                run_fn("UPDATE satisfaction_surveys SET rating=?,feedback=?,status='beantwortet',responded_at=? WHERE id=?",
                       (rating, feedback, datetime.now().isoformat()[:19], sid))
                log_fn("survey_answered", f"id={sid} rating={rating}")
                st.success(f"✅ Bewertung {rating}/5 gespeichert!")
                st.rerun()


# ─────────────────────────────────────────────────────────────
# 6. Interne Wissensdatenbank / Wiki
# ─────────────────────────────────────────────────────────────

def page_wiki(run_fn, df_fn, current_user_fn) -> None:
    st.title("📚 Wissensdatenbank")
    st.caption("Interne Wissensdatenbank für Prozesse, Anweisungen und Best Practices.")

    user = current_user_fn() or {}
    is_admin = user.get("role","").lower() in ("admin","administrator")

    tabs = st.tabs(["🏠 Übersicht", "📖 Artikel lesen",
                    "✏️ Artikel schreiben", "🔍 Suchen"])

    with tabs[0]:
        categories = df_fn("SELECT DISTINCT category FROM wiki_articles ORDER BY category")
        st.subheader("Kategorien")
        if not categories.empty:
            for cat in categories["category"].tolist():
                articles = df_fn("SELECT id, slug, title, views, updated_at FROM wiki_articles WHERE category=? ORDER BY title", (cat,))
                if not articles.empty:
                    with st.expander(f"📂 {cat} ({len(articles)} Artikel)"):
                        for _, art in articles.iterrows():
                            col1, col2 = st.columns([4,1])
                            col1.markdown(f"📄 **{art['title']}**")
                            col2.caption(f"👁 {int(art['views'])}")
        else:
            st.info("Noch keine Artikel.")

    with tabs[1]:
        articles = df_fn("SELECT id, title || ' (' || category || ')' AS label, slug FROM wiki_articles ORDER BY category, title")
        if articles.empty:
            st.info("Keine Artikel vorhanden.")
            return
        sel = st.selectbox("Artikel auswählen", articles["label"].tolist())
        art_id = int(articles[articles["label"] == sel].iloc[0]["id"])
        art = df_fn("SELECT * FROM wiki_articles WHERE id=?", (art_id,)).iloc[0].to_dict()
        run_fn("UPDATE wiki_articles SET views=views+1 WHERE id=?", (art_id,))
        st.subheader(art["title"])
        st.caption(f"Kategorie: {art['category']} · Zuletzt bearbeitet: {str(art.get('updated_at',''))[:10]}")
        st.markdown(str(art["content"]))

    with tabs[2]:
        CATEGORIES_W = ["Allgemein","Sicherheit & Recht","Betrieb","Notfall & Sicherheit",
                         "Personal","IT & Software","Kunden-Service","Qualitätsmanagement"]
        with st.form("wiki_form", clear_on_submit=False):
            title    = st.text_input("Artikeltitel *")
            category = st.selectbox("Kategorie", CATEGORIES_W)
            slug     = st.text_input("URL-Slug (automatisch)", value=title.lower().replace(" ","-").replace("ä","ae").replace("ö","oe").replace("ü","ue") if title else "")
            content  = st.text_area("Inhalt (Markdown unterstützt) *", height=300,
                                     placeholder="## Überschrift\n\nText...")
            if st.form_submit_button("💾 Artikel speichern", type="primary") and title and content:
                clean_slug = slug or title.lower().replace(" ","-")[:50]
                existing = df_fn("SELECT id FROM wiki_articles WHERE slug=?", (clean_slug,))
                if existing.empty:
                    run_fn("INSERT INTO wiki_articles(slug,title,category,content,author) VALUES(?,?,?,?,?)",
                           (clean_slug, title, category, content,
                            user.get("username","anonym")))
                else:
                    run_fn("UPDATE wiki_articles SET title=?,category=?,content=?,author=?,updated_at=datetime('now') WHERE slug=?",
                           (title, category, content, user.get("username","anonym"), clean_slug))
                st.success(f"✅ Artikel '{title}' gespeichert!"); st.rerun()

    with tabs[3]:
        q = st.text_input("🔍 Wissensdatenbank durchsuchen")
        if q and len(q) >= 2:
            results = df_fn(f"SELECT title AS Titel, category AS Kategorie, substr(content,1,100) || '...' AS Vorschau FROM wiki_articles WHERE title LIKE '%{q}%' OR content LIKE '%{q}%'")
            if not results.empty:
                st.success(f"{len(results)} Treffer für '{q}'")
                st.dataframe(results, use_container_width=True)
            else:
                st.info(f"Keine Treffer für '{q}'")
