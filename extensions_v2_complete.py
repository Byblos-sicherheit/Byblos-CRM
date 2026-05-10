"""
extensions_v2_complete.py – Abschluss-Modul Byblos CRM v2
==========================================================
1. Stornorechnungen (PDF + Gegenbuchung)
2. Zeiterfassung Überstunden-Ausgleich
3. Minijobler/Midijob-Berechnung
4. Vertragsüberwachung + Verlängerungswarnung
5. BWA Jahresvergleich (IST vs. Vorjahr)
6. ZUGFeRD 2.3 E-Rechnung (XML in PDF eingebettet)
7. Serienbrief / Briefvorlage
8. Datenbank-Migrations-System
9. Rate-Limiting / Brute-Force-Schutz
10. GDPR-Datenbereinigung
11. WhatsApp Business-Hinweis + API-Vorbereitung
12. Kundensignatur per E-Mail (Link-basiert)
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import json
import hashlib
import re

import pandas as pd
import streamlit as st


def fmt_eur(v: float) -> str:
    return f"{v:,.2f} €".replace(",", "X").replace(".", ",").replace("X", ".")


# ─────────────────────────────────────────────────────────────
# DB-Registrierung + Migrations-System
# ─────────────────────────────────────────────────────────────

SCHEMA_VERSION = 10  # Erhöhen bei jeder Schema-Änderung


def register_complete(run_fn, df_fn) -> None:
    run_fn("""CREATE TABLE IF NOT EXISTS schema_versions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        version INTEGER UNIQUE NOT NULL,
        applied_at TEXT DEFAULT CURRENT_TIMESTAMP,
        description TEXT
    )""")
    run_fn("""CREATE TABLE IF NOT EXISTS overtime_compensations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        employee_id INTEGER NOT NULL,
        comp_date TEXT NOT NULL,
        hours REAL NOT NULL,
        comp_type TEXT DEFAULT 'Freizeit',
        reason TEXT,
        approved_by TEXT,
        status TEXT DEFAULT 'beantragt',
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(employee_id) REFERENCES employees(id)
    )""")
    run_fn("""CREATE TABLE IF NOT EXISTS contract_monitoring (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        customer_id INTEGER,
        contract_title TEXT NOT NULL,
        start_date TEXT NOT NULL,
        end_date TEXT,
        auto_renew INTEGER DEFAULT 0,
        notice_period_days INTEGER DEFAULT 30,
        monthly_value REAL DEFAULT 0,
        status TEXT DEFAULT 'aktiv',
        notes TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(customer_id) REFERENCES customers(id)
    )""")
    run_fn("""CREATE TABLE IF NOT EXISTS serial_letters (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        template_name TEXT UNIQUE NOT NULL,
        subject TEXT,
        body_html TEXT NOT NULL,
        variables TEXT DEFAULT '[]',
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )""")
    run_fn("""CREATE TABLE IF NOT EXISTS login_attempts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ip_address TEXT,
        username TEXT,
        success INTEGER DEFAULT 0,
        attempt_time TEXT DEFAULT CURRENT_TIMESTAMP
    )""")
    run_fn("""CREATE TABLE IF NOT EXISTS signature_requests (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        document_type TEXT NOT NULL,
        document_id INTEGER,
        recipient_email TEXT NOT NULL,
        recipient_name TEXT,
        token TEXT UNIQUE NOT NULL,
        status TEXT DEFAULT 'ausstehend',
        signed_at TEXT,
        ip_address TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )""")
    run_fn("""CREATE TABLE IF NOT EXISTS gdpr_deletion_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        data_type TEXT NOT NULL,
        record_id INTEGER,
        deleted_by TEXT,
        reason TEXT,
        deleted_at TEXT DEFAULT CURRENT_TIMESTAMP
    )""")

    # Schema-Version eintragen
    try:
        existing = df_fn("SELECT version FROM schema_versions ORDER BY version DESC LIMIT 1")
        current_v = int(existing.iloc[0]["version"]) if not existing.empty else 0
        if current_v < SCHEMA_VERSION:
            run_fn("INSERT OR IGNORE INTO schema_versions(version,description) VALUES(?,?)",
                   (SCHEMA_VERSION, f"Byblos CRM v2 Schema {SCHEMA_VERSION}"))
    except Exception:
        pass


# ─────────────────────────────────────────────────────────────
# 1. Stornorechnungen
# ─────────────────────────────────────────────────────────────

def generate_storno_pdf(original_inv_id: int, storno_inv_id: int, df_fn,
                         get_setting_fn, base_dir: Path) -> Optional[Path]:
    """Erstellt eine Stornorechnung als PDF."""
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib import colors
        from reportlab.lib.units import mm
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer,
                                         Table, TableStyle, HRFlowable)
    except ImportError:
        return None

    orig = df_fn("""SELECT i.*, c.company, c.street, c.zip_city, c.customer_no
                    FROM invoices i JOIN customers c ON c.id=i.customer_id WHERE i.id=?""",
                 (original_inv_id,))
    storno = df_fn("SELECT * FROM invoices WHERE id=?", (storno_inv_id,))
    if orig.empty or storno.empty:
        return None

    orig = orig.iloc[0].to_dict()
    storno_row = storno.iloc[0].to_dict()
    co_name  = get_setting_fn("company_name", "Byblos Sicherheitsdienst")
    co_iban  = get_setting_fn("company_iban", "")
    storno_no = str(storno_row.get("invoice_no", "STORNO"))
    output_path = base_dir / "generated" / "invoices" / f"{storno_no}.pdf"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    doc = SimpleDocTemplate(str(output_path), pagesize=A4,
                            rightMargin=18*mm, leftMargin=18*mm,
                            topMargin=15*mm, bottomMargin=15*mm)
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="Sm", fontSize=8, leading=10))
    story = []

    story.append(Paragraph(f"<b>STORNORECHNUNG</b>", styles["h1"]))
    story.append(Paragraph(
        f"<font color='red'><b>STORNO / GUTSCHRIFT</b></font>", styles["h2"]
    ))
    story.append(HRFlowable(width="100%", thickness=2, color=colors.red))
    story.append(Spacer(1, 5*mm))

    info_data = [
        ["Stornorechnung-Nr.:", storno_no],
        ["Storno zu Rechnung:", str(orig.get("invoice_no",""))],
        ["Datum:", date.today().isoformat()],
        ["Kunde:", str(orig.get("company",""))],
        ["Storno-Betrag:", f"- {float(orig.get('gross_total',0)):.2f} €"],
    ]
    t = Table(info_data, colWidths=[55*mm, 110*mm])
    t.setStyle(TableStyle([
        ("FONTNAME",(0,0),(0,-1),"Helvetica-Bold"),
        ("FONTSIZE",(0,0),(-1,-1),9),
        ("GRID",(0,0),(-1,-1),0.25,colors.HexColor("#ddd")),
        ("ROWBACKGROUNDS",(0,0),(-1,-1),[colors.white,colors.HexColor("#f5f5f5")]),
    ]))
    story.append(t)
    story.append(Spacer(1, 6*mm))

    story.append(Paragraph(
        f"Hiermit stornieren wir die Rechnung <b>{orig.get('invoice_no','')}</b> "
        f"vom {orig.get('invoice_date','')} in vollem Umfang.<br/><br/>"
        f"Der Betrag von <b>{float(orig.get('gross_total',0)):.2f} €</b> wird Ihnen "
        f"gutgeschrieben bzw. erstattet.<br/><br/>"
        f"Bei Rückfragen stehen wir gerne zur Verfügung.",
        styles["Normal"]
    ))
    story.append(Spacer(1, 8*mm))

    storno_data = [
        ["Ursprünglicher Rechnungsbetrag", f"{float(orig.get('gross_total',0)):.2f} €"],
        ["Storno-Betrag (Gutschrift)", f"- {float(orig.get('gross_total',0)):.2f} €"],
        ["Verbleibender Saldo", "0,00 €"],
    ]
    st_table = Table(storno_data, colWidths=[120*mm, 45*mm])
    st_table.setStyle(TableStyle([
        ("FONTNAME",(0,-1),(-1,-1),"Helvetica-Bold"),
        ("BACKGROUND",(0,-1),(-1,-1),colors.HexColor("#e8f5e9")),
        ("GRID",(0,0),(-1,-1),0.25,colors.HexColor("#ddd")),
        ("ALIGN",(1,0),(1,-1),"RIGHT"),
    ]))
    story.append(st_table)
    story.append(Spacer(1, 8*mm))
    story.append(Paragraph(
        f"Bankverbindung: {co_name} · IBAN: {co_iban}",
        styles["Sm"]
    ))
    doc.build(story)
    return output_path


def page_storno_invoices(run_fn, df_fn, next_number_fn, log_fn,
                          get_setting_fn, refresh_totals_fn, base_dir: Path) -> None:
    st.title("❌ Stornorechnungen")
    st.caption("Erstellt eine Stornorechnung (Gegenbuchung) zur Originalrechnung.")

    tabs = st.tabs(["➕ Storno erstellen", "📋 Stornohistorie"])

    with tabs[0]:
        invoices = df_fn("""
            SELECT i.id, i.invoice_no || ' – ' || c.company || ' (' ||
                   ROUND(i.gross_total,2) || ' €)' AS label, i.status
            FROM invoices i JOIN customers c ON c.id=i.customer_id
            WHERE i.status NOT IN ('storniert')
            ORDER BY i.invoice_date DESC LIMIT 100
        """)
        if invoices.empty:
            st.info("Keine Rechnungen vorhanden.")
            return

        sel = st.selectbox("Zu stornier ende Rechnung", invoices["label"].tolist())
        iid = int(invoices[invoices["label"] == sel].iloc[0]["id"])
        orig_row = df_fn("SELECT * FROM invoices WHERE id=?", (iid,)).iloc[0].to_dict()
        cid      = int(orig_row.get("customer_id", 0))

        st.warning(f"⚠️ Stornorechnung zu: **{orig_row.get('invoice_no')}** "
                   f"über **{fmt_eur(float(orig_row.get('gross_total',0)))}**")
        reason = st.text_area("Storno-Begründung *", "Stornierung der Originalrechnung auf Wunsch des Kunden.")

        if st.button("❌ Stornorechnung erstellen", type="primary") and reason:
            storno_no = next_number_fn("invoices", "invoice_no", "STOR-")
            gross = float(orig_row.get("gross_total", 0))
            net   = float(orig_row.get("net_total", 0))
            vat   = float(orig_row.get("vat_total", 0))
            vat_r = float(orig_row.get("vat_rate", 19))

            run_fn("""INSERT INTO invoices(invoice_no,customer_id,invoice_date,service_date,
                      due_date,description,net_total,vat_rate,vat_total,gross_total,paid_amount,status,notes)
                      VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                   (storno_no, cid, date.today().isoformat(),
                    str(orig_row.get("service_date","")),
                    date.today().isoformat(),
                    f"STORNO zu {orig_row.get('invoice_no','')} – {reason}",
                    -net, vat_r, -vat, -gross, 0, "storniert", reason))

            storno_id = int(df_fn("SELECT id FROM invoices WHERE invoice_no=?",
                                   (storno_no,)).iloc[0]["id"])
            run_fn("UPDATE invoices SET status='storniert', notes=? WHERE id=?",
                   (f"Storniert durch {storno_no}", iid))
            refresh_totals_fn(storno_id)

            path = generate_storno_pdf(iid, storno_id, df_fn, get_setting_fn, base_dir)
            if path and path.exists():
                run_fn("UPDATE invoices SET pdf_path=? WHERE id=?", (str(path), storno_id))
                st.download_button("📥 Stornorechnung PDF", path.read_bytes(),
                                   path.name, "application/pdf")
            log_fn("storno_created", f"{storno_no} zu {orig_row.get('invoice_no')}")
            st.success(f"✅ Stornorechnung {storno_no} erstellt!")
            st.rerun()

    with tabs[1]:
        stornos = df_fn("""
            SELECT invoice_no AS Nr, invoice_date AS Datum, description AS Beschreibung,
                   ROUND(gross_total,2) AS Betrag, status AS Status
            FROM invoices WHERE status='storniert' OR invoice_no LIKE 'STOR-%'
            ORDER BY invoice_date DESC
        """)
        if not stornos.empty:
            st.dataframe(stornos, use_container_width=True)
        else:
            st.info("Noch keine Stornorechnungen.")


# ─────────────────────────────────────────────────────────────
# 2. Überstunden-Ausgleich
# ─────────────────────────────────────────────────────────────

def page_overtime_compensation(run_fn, df_fn, log_fn, current_user_fn) -> None:
    st.title("⏱️ Überstunden-Ausgleich")
    st.caption("Überstunden als Freizeitausgleich oder Auszahlung verwalten.")

    user = current_user_fn() or {}
    is_mgr = user.get("role","").lower() in ("admin","manager","administrator")

    tabs = st.tabs(["📊 Überstunden-Konto", "➕ Ausgleich beantragen",
                    "✅ Genehmigen", "📋 Historie"])

    with tabs[0]:
        employees = df_fn("SELECT id, employee_no || ' – ' || name AS label FROM employees WHERE active=1 ORDER BY name")
        if employees.empty:
            st.info("Keine Mitarbeiter.")
            return

        year = st.selectbox("Jahr", list(range(date.today().year, date.today().year-3,-1)))
        ot_data = df_fn("""
            SELECT e.name AS Mitarbeiter,
                   ROUND(SUM(t.overtime_hours),2) AS Überstunden_gesamt,
                   ROUND(COALESCE((SELECT SUM(oc.hours) FROM overtime_compensations oc
                                   WHERE oc.employee_id=e.id AND oc.status='genehmigt'
                                   AND substr(oc.comp_date,1,4)=?),0),2) AS Ausgeglichen,
                   ROUND(SUM(t.overtime_hours) -
                         COALESCE((SELECT SUM(oc.hours) FROM overtime_compensations oc
                                   WHERE oc.employee_id=e.id AND oc.status='genehmigt'
                                   AND substr(oc.comp_date,1,4)=?),0),2) AS Rest_Überstunden
            FROM time_entries t JOIN employees e ON e.id=t.employee_id
            WHERE substr(t.date,1,4)=? AND t.overtime_hours>0
            GROUP BY e.id ORDER BY Rest_Überstunden DESC
        """, (str(year), str(year), str(year)))

        if not ot_data.empty:
            c1, c2 = st.columns(2)
            c1.metric("Mitarbeiter mit Überstunden", len(ot_data[ot_data["Rest_Überstunden"]>0]))
            c2.metric("Gesamt-Überstunden", f"{float(ot_data['Rest_Überstunden'].sum()):.1f} h")
            st.dataframe(ot_data, use_container_width=True)
            st.bar_chart(ot_data.set_index("Mitarbeiter")["Rest_Überstunden"])
        else:
            st.info("Keine Überstunden-Daten für dieses Jahr.")

    with tabs[1]:
        employees2 = df_fn("SELECT id, name FROM employees WHERE active=1 ORDER BY name")
        with st.form("ot_comp_form", clear_on_submit=True):
            emp_name = st.selectbox("Mitarbeiter", employees2["name"].tolist() if not employees2.empty else ["—"])
            col1, col2 = st.columns(2)
            comp_date = col1.date_input("Freizeitausgleich am", date.today() + timedelta(days=7))
            hours     = col2.number_input("Stunden", min_value=0.5, value=8.0, step=0.5)
            comp_type = col1.selectbox("Art", ["Freizeit","Auszahlung","Urlaub anrechnen"])
            reason    = st.text_area("Begründung")
            submitted = st.form_submit_button("📨 Antrag einreichen", type="primary")

        if submitted and not employees2.empty:
            eid = int(employees2[employees2["name"] == emp_name].iloc[0]["id"])
            run_fn("""INSERT INTO overtime_compensations(employee_id,comp_date,hours,comp_type,reason,status)
                      VALUES(?,?,?,?,?,?)""",
                   (eid, comp_date.isoformat(), hours, comp_type, reason, "beantragt"))
            log_fn("overtime_comp_requested", f"{emp_name} {hours}h {comp_type}")
            st.success(f"✅ {hours}h Ausgleich für {emp_name} beantragt!")
            st.rerun()

    with tabs[2]:
        if not is_mgr:
            st.warning("Nur Manager können Ausgleiche genehmigen.")
            return
        pending = df_fn("""
            SELECT oc.id, e.name AS Mitarbeiter, oc.comp_date AS Datum,
                   oc.hours AS Stunden, oc.comp_type AS Art, oc.reason AS Grund
            FROM overtime_compensations oc JOIN employees e ON e.id=oc.employee_id
            WHERE oc.status='beantragt'
        """)
        if not pending.empty:
            for _, row in pending.iterrows():
                ocid = int(row["id"])
                with st.expander(f"⏱️ {row['Mitarbeiter']} – {row['Stunden']}h {row['Art']} am {row['Datum']}"):
                    if row.get("Grund"): st.caption(row["Grund"])
                    col1, col2 = st.columns(2)
                    if col1.button("✅ Genehmigen", key=f"oc_ok_{ocid}", type="primary"):
                        run_fn("UPDATE overtime_compensations SET status='genehmigt', approved_by=? WHERE id=?",
                               (user.get("username","admin"), ocid))
                        st.rerun()
                    if col2.button("❌ Ablehnen", key=f"oc_no_{ocid}"):
                        run_fn("UPDATE overtime_compensations SET status='abgelehnt' WHERE id=?", (ocid,))
                        st.rerun()
        else:
            st.success("✅ Keine ausstehenden Anträge.")

    with tabs[3]:
        hist = df_fn("""
            SELECT e.name AS Mitarbeiter, oc.comp_date AS Datum,
                   oc.hours AS Stunden, oc.comp_type AS Art,
                   oc.status AS Status, oc.approved_by AS Genehmigt_von
            FROM overtime_compensations oc JOIN employees e ON e.id=oc.employee_id
            ORDER BY oc.comp_date DESC LIMIT 100
        """)
        if not hist.empty:
            st.dataframe(hist, use_container_width=True)
        else:
            st.info("Noch keine Ausgleiche.")


# ─────────────────────────────────────────────────────────────
# 3. Minijobler / Midijob Lohnberechnung
# ─────────────────────────────────────────────────────────────

MINIJOB_LIMIT  = 538.0   # 2024: 538 €/Monat (aktuell prüfen!)
MIDIJOB_LIMIT  = 2000.0  # Midijob bis 2.000 €/Monat
PAUSCHSTEUER   = 0.02    # 2% Pauschsteuer Minijob (Arbeitgeber)
PAUSCHAL_SV_AG = 0.28    # 28% Pauschale AG-Anteil SV (Minijob)


def calculate_minijob(monthly_hours: float, hourly_rate: float) -> Dict:
    gross = round(monthly_hours * hourly_rate, 2)
    is_minijob = gross <= MINIJOB_LIMIT
    is_midijob = MINIJOB_LIMIT < gross <= MIDIJOB_LIMIT

    if is_minijob:
        ag_cost     = round(gross * PAUSCHAL_SV_AG, 2)
        ag_tax      = round(gross * PAUSCHSTEUER, 2)
        total_ag    = round(gross + ag_cost + ag_tax, 2)
        net         = gross  # Minijob: kein AN-Abzug (pauschal)
        return {"art":"Minijob","gross":gross,"net":net,"ag_cost":ag_cost,
                "ag_tax":ag_tax,"total_ag":total_ag,"in_limit":True}
    elif is_midijob:
        # Gleitzone: AN-Beitrag reduziert
        an_rate = round(0.2 * (gross - MINIJOB_LIMIT) / (MIDIJOB_LIMIT - MINIJOB_LIMIT), 4)
        an_sv   = round(gross * an_rate, 2)
        ag_sv   = round(gross * 0.2, 2)
        net     = round(gross - an_sv, 2)
        return {"art":"Midijob","gross":gross,"net":net,"ag_cost":ag_sv,
                "ag_tax":0,"total_ag":round(gross+ag_sv,2),"in_limit":True}
    else:
        return {"art":"Normaler AN","gross":gross,"net":gross*0.68,
                "ag_cost":gross*0.2,"ag_tax":0,"total_ag":gross*1.2,"in_limit":False}


def page_minijob_calculator(run_fn, df_fn) -> None:
    st.title("🧮 Minijobler / Midijob Rechner")
    st.caption(f"Berechnung nach aktuellen Grenzen: Minijob ≤{MINIJOB_LIMIT:.0f} €, Midijob ≤{MIDIJOB_LIMIT:.0f} €/Monat.")
    st.warning("⚠️ Grenzen ändern sich jährlich! Bitte mit Steuerberater / Arbeitsagentur abstimmen.")

    tabs = st.tabs(["🧮 Rechner", "📋 Alle Minijobler", "📊 Jahresübersicht"])

    with tabs[0]:
        col1, col2, col3 = st.columns(3)
        hours    = col1.number_input("Stunden/Monat", min_value=0.0, value=20.0, step=0.5)
        rate     = col2.number_input("Stundenlohn (€)", min_value=12.41, value=13.0, step=0.1)
        check_month = col3.text_input("Monat prüfen", date.today().strftime("%Y-%m"))
        result   = calculate_minijob(hours, rate)
        gross = result["gross"]

        # Ampel
        if result["in_limit"] and result["art"] == "Minijob":
            remaining = MINIJOB_LIMIT - gross
            st.success(f"✅ **Minijob** – Brutto {fmt_eur(gross)} · Noch {fmt_eur(remaining)} bis zur Grenze")
        elif result["in_limit"] and result["art"] == "Midijob":
            remaining = MIDIJOB_LIMIT - gross
            st.warning(f"🟡 **Midijob** – Brutto {fmt_eur(gross)} · Noch {fmt_eur(remaining)} bis Regelbesteuerung")
        else:
            excess = gross - MIDIJOB_LIMIT
            st.error(f"🔴 **Über Midijob-Grenze** um {fmt_eur(excess)} – Regelbesteuerung gilt!")

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Bruttolohn", fmt_eur(result["gross"]))
        c2.metric("Nettolohn (AN)", fmt_eur(result["net"]))
        c3.metric("AG-SV-Anteil", fmt_eur(result["ag_cost"]))
        c4.metric("Gesamtkosten AG", fmt_eur(result["total_ag"]))

        # Jahresberechnung
        annual_gross = round(gross * 12, 2)
        st.info(f"📅 Jahresbruttogehalt: **{fmt_eur(annual_gross)}** (Minijob-Jahreslimit: {fmt_eur(MINIJOB_LIMIT*12)})")

    with tabs[1]:
        minis = df_fn("""
            SELECT e.name AS Mitarbeiter, e.employee_no AS Nr,
                   e.hourly_rate AS Stundensatz,
                   ROUND(COALESCE((SELECT SUM(t.net_hours) FROM time_entries t
                                   WHERE t.employee_id=e.id AND substr(t.date,1,7)=?),0),1) AS Stunden_Monat
            FROM employees e WHERE e.active=1
            ORDER BY e.name
        """, (date.today().strftime("%Y-%m"),))

        if not minis.empty:
            minis["Brutto_Monat"] = (minis["Stunden_Monat"] * minis["Stundensatz"]).round(2)
            minis["Status"] = minis["Brutto_Monat"].apply(
                lambda v: "✅ Minijob" if v<=MINIJOB_LIMIT else
                          "🟡 Midijob" if v<=MIDIJOB_LIMIT else "🔴 Regelan")
            st.dataframe(minis, use_container_width=True)
        else:
            st.info("Keine Mitarbeiter gefunden.")

    with tabs[2]:
        year_m = st.selectbox("Jahr", list(range(date.today().year, date.today().year-3,-1)), key="mj_year")
        annual = df_fn("""
            SELECT e.name AS Mitarbeiter,
                   ROUND(SUM(p.gross_salary),2) AS Jahresbrutto,
                   COUNT(*) AS Monate
            FROM payroll_records p JOIN employees e ON e.id=p.employee_id
            WHERE substr(p.payroll_month,1,4)=?
            GROUP BY e.id ORDER BY Jahresbrutto DESC
        """, (str(year_m),))

        if not annual.empty:
            annual["Status"] = annual["Jahresbrutto"].apply(
                lambda v: "✅ Minijob OK" if v <= MINIJOB_LIMIT*12 else "⚠️ Grenze überschritten")
            st.dataframe(annual, use_container_width=True)
        else:
            st.info("Keine Lohndaten für dieses Jahr.")


# ─────────────────────────────────────────────────────────────
# 4. Vertragsüberwachung
# ─────────────────────────────────────────────────────────────

def page_contract_monitoring(run_fn, df_fn, next_number_fn, log_fn) -> None:
    st.title("📋 Vertragsüberwachung")
    st.caption("Laufzeitüberwachung und automatische Verlängerungswarnungen für Kundenverträge.")

    tabs = st.tabs(["⚠️ Ablaufende Verträge", "📋 Alle Verträge",
                    "➕ Vertrag anlegen", "📊 Vertragsstatistik"])

    with tabs[0]:
        today = date.today().isoformat()
        warn90 = (date.today() + timedelta(days=90)).isoformat()

        expiring = df_fn("""
            SELECT cm.id, cm.contract_title AS Vertrag,
                   COALESCE(c.company,'–') AS Kunde,
                   cm.end_date AS Enddatum,
                   CAST(julianday(cm.end_date) - julianday('now') AS INT) AS Tage_verbleibend,
                   cm.notice_period_days AS Kündigungsfrist_Tage,
                   cm.monthly_value AS Monatswert_EUR,
                   cm.auto_renew AS Auto_Verlängerung
            FROM contract_monitoring cm
            LEFT JOIN customers c ON c.id=cm.customer_id
            WHERE cm.status='aktiv' AND cm.end_date IS NOT NULL
              AND cm.end_date <= ?
            ORDER BY cm.end_date
        """, (warn90,))

        if expiring.empty:
            st.success("✅ Keine Verträge laufen in den nächsten 90 Tagen ab.")
        else:
            already_expired = expiring[expiring["Tage_verbleibend"] < 0]
            in_notice = expiring[(expiring["Tage_verbleibend"] >= 0) &
                                  (expiring["Tage_verbleibend"] <= expiring["Kündigungsfrist_Tage"])]
            upcoming = expiring[expiring["Tage_verbleibend"] > expiring["Kündigungsfrist_Tage"]]

            c1, c2, c3 = st.columns(3)
            c1.metric("❌ Abgelaufen", len(already_expired))
            c2.metric("⚠️ In Kündigungsfrist", len(in_notice))
            c3.metric("📅 Läuft bald ab", len(upcoming))

            if not already_expired.empty:
                st.error("❌ Abgelaufene Verträge:")
                st.dataframe(already_expired.drop(columns=["id"]), use_container_width=True)
            if not in_notice.empty:
                st.warning("⚠️ Jetzt kündigen oder verlängern! Kündigungsfrist läuft:")
                st.dataframe(in_notice.drop(columns=["id"]), use_container_width=True)
            if not upcoming.empty:
                st.info("Laufen in 90 Tagen ab:")
                st.dataframe(upcoming.drop(columns=["id"]), use_container_width=True)

    with tabs[1]:
        status_f = st.selectbox("Status", ["alle","aktiv","gekündigt","abgelaufen","pausiert"])
        q = "SELECT cm.id, cm.contract_title AS Vertrag, COALESCE(c.company,'–') AS Kunde, cm.start_date AS Start, cm.end_date AS Ende, cm.monthly_value AS Monat_EUR, cm.notice_period_days AS Frist_Tage, cm.auto_renew AS Auto_Verl, cm.status AS Status FROM contract_monitoring cm LEFT JOIN customers c ON c.id=cm.customer_id"
        if status_f != "alle":
            q += f" WHERE cm.status='{status_f}'"
        q += " ORDER BY cm.end_date NULLS LAST"
        data = df_fn(q)
        if not data.empty:
            total_val = float(data[data["Status"]=="aktiv"]["Monat_EUR"].sum()) if not data[data["Status"]=="aktiv"].empty else 0
            c1, c2 = st.columns(2)
            c1.metric("Aktive Verträge", len(data[data["Status"]=="aktiv"]))
            c2.metric("Monatlicher Vertragswert", fmt_eur(total_val))
            st.dataframe(data.drop(columns=["id"]), use_container_width=True, height=350)

            # Status ändern
            sel = st.selectbox("Vertrag verwalten", data["Vertrag"].tolist())
            cid_row = data[data["Vertrag"]==sel].iloc[0]
            vid = int(cid_row["id"])
            new_s = st.selectbox("Neuer Status", ["aktiv","gekündigt","abgelaufen","pausiert"])
            if st.button("💾 Status setzen"):
                run_fn("UPDATE contract_monitoring SET status=? WHERE id=?", (new_s, vid))
                st.success(f"Status auf '{new_s}' gesetzt."); st.rerun()

    with tabs[2]:
        customers = df_fn("SELECT id, customer_no || ' – ' || company AS label FROM customers ORDER BY company")
        with st.form("contract_form", clear_on_submit=True):
            title = st.text_input("Vertragsbezeichnung *", "Objektschutzvertrag")
            cust_label = st.selectbox("Kunde", ["—"] + (customers["label"].tolist() if not customers.empty else []))
            col1, col2, col3 = st.columns(3)
            start_d = col1.date_input("Vertragsbeginn", date.today())
            end_d   = col2.date_input("Vertragsende", date.today() + timedelta(days=365))
            notice  = col3.number_input("Kündigungsfrist (Tage)", min_value=0, value=30, step=30)
            col4, col5 = st.columns(2)
            monthly_val = col4.number_input("Monatswert (€)", min_value=0.0, value=0.0, step=100.0)
            auto_renew  = col5.checkbox("Automatische Verlängerung", value=False)
            notes = st.text_area("Notizen")
            submitted = st.form_submit_button("💾 Vertrag speichern", type="primary")

        if submitted and title:
            cid2 = None
            if cust_label != "—" and not customers.empty:
                match = customers[customers["label"]==cust_label]
                if not match.empty:
                    cid2 = int(match.iloc[0]["id"])
            run_fn("""INSERT INTO contract_monitoring(customer_id,contract_title,start_date,end_date,
                      notice_period_days,monthly_value,auto_renew,notes)
                      VALUES(?,?,?,?,?,?,?,?)""",
                   (cid2, title, start_d.isoformat(), end_d.isoformat(),
                    notice, monthly_val, 1 if auto_renew else 0, notes))
            log_fn("contract_added", title)
            st.success(f"✅ Vertrag '{title}' gespeichert!")
            st.rerun()

    with tabs[3]:
        stats = df_fn("""
            SELECT status AS Status, COUNT(*) AS Verträge,
                   SUM(monthly_value) AS Monatswert
            FROM contract_monitoring GROUP BY status
        """)
        if not stats.empty:
            st.dataframe(stats, use_container_width=True)
            total_annual = float(stats[stats["Status"]=="aktiv"]["Monatswert"].sum()) * 12 if not stats[stats["Status"]=="aktiv"].empty else 0
            st.metric("Vertraglich gesicherter Jahresumsatz", fmt_eur(total_annual))


# ─────────────────────────────────────────────────────────────
# 5. BWA Jahresvergleich (IST vs. Vorjahr)
# ─────────────────────────────────────────────────────────────

def page_bwa_comparison(df_fn) -> None:
    st.title("📊 BWA Jahresvergleich")
    st.caption("Ist-Jahr vs. Vorjahr: Umsatz, Kosten und Ergebnis im Vergleich.")

    col1, col2 = st.columns(2)
    current_year = col1.selectbox("Ist-Jahr", list(range(date.today().year, date.today().year-5,-1)))
    prev_year    = col2.selectbox("Vorjahr", list(range(current_year-1, current_year-6,-1)))

    # Umsätze
    def get_monthly(year: int) -> pd.DataFrame:
        return df_fn(f"""
            SELECT substr(invoice_date,1,7) AS Monat,
                   SUM(gross_total) AS Umsatz_gesamt,
                   SUM(CASE WHEN status='bezahlt' THEN gross_total ELSE 0 END) AS Umsatz_bezahlt
            FROM invoices WHERE substr(invoice_date,1,4)='{year}'
            GROUP BY substr(invoice_date,1,7) ORDER BY Monat
        """)

    def get_expenses(year: int) -> pd.DataFrame:
        return df_fn(f"""
            SELECT bwa_month AS Monat, SUM(gross_amount) AS Ausgaben
            FROM expenses WHERE substr(bwa_month,1,4)='{year}'
            GROUP BY bwa_month ORDER BY bwa_month
        """)

    curr_rev  = get_monthly(current_year)
    prev_rev  = get_monthly(prev_year)
    curr_exp  = get_expenses(current_year)
    prev_exp  = get_expenses(prev_year)

    # Jahressummen
    c_umsatz = float(curr_rev["Umsatz_bezahlt"].sum()) if not curr_rev.empty else 0
    p_umsatz = float(prev_rev["Umsatz_bezahlt"].sum()) if not prev_rev.empty else 0
    c_kosten = float(curr_exp["Ausgaben"].sum()) if not curr_exp.empty else 0
    p_kosten = float(prev_exp["Ausgaben"].sum()) if not prev_exp.empty else 0
    c_erg    = c_umsatz - c_kosten
    p_erg    = p_umsatz - p_kosten

    def delta_pct(curr, prev):
        if prev == 0:
            return "–"
        pct = (curr - prev) / abs(prev) * 100
        return f"{'▲' if pct>=0 else '▼'} {abs(pct):.1f}%"

    st.subheader(f"Jahresvergleich {current_year} vs. {prev_year}")
    col1, col2, col3 = st.columns(3)
    col1.markdown(f"""
| Kennzahl | {current_year} | {prev_year} | Δ |
|---|---|---|---|
| Umsatz (bez.) | **{fmt_eur(c_umsatz)}** | {fmt_eur(p_umsatz)} | {delta_pct(c_umsatz,p_umsatz)} |
| Ausgaben | **{fmt_eur(c_kosten)}** | {fmt_eur(p_kosten)} | {delta_pct(c_kosten,p_kosten)} |
| Ergebnis | **{fmt_eur(c_erg)}** | {fmt_eur(p_erg)} | {delta_pct(c_erg,p_erg)} |
    """)

    # Monatsweiser Chart-Vergleich
    if not curr_rev.empty or not prev_rev.empty:
        st.subheader("Umsatz-Monatsvergleich")
        curr_m = curr_rev.set_index("Monat")["Umsatz_bezahlt"].rename(f"{current_year}") if not curr_rev.empty else pd.Series(dtype=float)
        prev_m = prev_rev.set_index("Monat")["Umsatz_bezahlt"].rename(f"{prev_year}") if not prev_rev.empty else pd.Series(dtype=float)
        chart_df = pd.concat([curr_m, prev_m], axis=1).fillna(0)
        st.bar_chart(chart_df)

    # Kostenstruktur-Vergleich
    st.subheader("Kostenstruktur-Vergleich")
    curr_cat = df_fn(f"SELECT category AS Kostenart, ROUND(SUM(gross_amount),2) AS {current_year} FROM expenses WHERE substr(bwa_month,1,4)='{current_year}' GROUP BY category ORDER BY {current_year} DESC")
    prev_cat = df_fn(f"SELECT category AS Kostenart, ROUND(SUM(gross_amount),2) AS {prev_year} FROM expenses WHERE substr(bwa_month,1,4)='{prev_year}' GROUP BY category ORDER BY {prev_year} DESC")

    if not curr_cat.empty and not prev_cat.empty:
        merged = curr_cat.merge(prev_cat, on="Kostenart", how="outer").fillna(0)
        merged["Δ_EUR"]  = (merged[current_year] - merged[prev_year]).round(2)
        merged["Δ_Pct"] = ((merged["Δ_EUR"] / merged[prev_year].replace(0,1)) * 100).round(1)
        st.dataframe(merged, use_container_width=True)


# ─────────────────────────────────────────────────────────────
# 6. GDPR-Datenbereinigung
# ─────────────────────────────────────────────────────────────

def page_gdpr_center(run_fn, df_fn, log_fn, current_user_fn) -> None:
    st.title("🔒 DSGVO / GDPR-Datenschutzcenter")
    st.caption("Datenlöschfristen, Auskunftsrecht und Bereinigung nach DSGVO.")

    user = current_user_fn() or {}
    if user.get("role","").lower() not in ("admin","administrator"):
        st.error("Nur Administratoren können DSGVO-Aktionen durchführen.")
        return

    tabs = st.tabs(["📋 Löschfristen", "🔍 Auskunftsanfrage",
                    "🗑️ Daten löschen", "📊 Datenschutz-Log"])

    RETENTION = {
        "Rechnungen": (10, "Jahre", "§257 HGB, §147 AO"),
        "Buchhaltungsbelege": (10, "Jahre", "§257 HGB"),
        "Verträge": (6, "Jahre", "§195 BGB"),
        "E-Mail-Protokoll": (3, "Jahre", "empfohlen"),
        "Audit-Log": (3, "Jahre", "empfohlen"),
        "Bewerber-Daten": (6, "Monate", "BAG-Recht"),
        "GPS-Stempel": (3, "Jahre", "Datensparsamkeit"),
    }

    with tabs[0]:
        st.subheader("Gesetzliche Aufbewahrungsfristen")
        data = [{"Datenkategorie": k, "Frist": f"{v[0]} {v[1]}", "Rechtsgrundlage": v[2]}
                for k, v in RETENTION.items()]
        st.dataframe(pd.DataFrame(data), use_container_width=True)
        st.info("**Empfehlung:** Jährlich Daten prüfen und abgelaufene Einträge archivieren oder löschen.")

    with tabs[1]:
        st.subheader("Auskunftsanfrage (Art. 15 DSGVO)")
        search_name = st.text_input("Name / E-Mail der betroffenen Person")
        if st.button("🔍 Alle Daten dieser Person suchen") and search_name:
            results = {}
            q = f"%{search_name}%"
            results["Kunden"] = df_fn("SELECT * FROM customers WHERE company LIKE ? OR contact_person LIKE ? OR email LIKE ?", (q,q,q))
            results["Mitarbeiter"] = df_fn("SELECT id, employee_no, name, email, phone FROM employees WHERE name LIKE ? OR email LIKE ?", (q,q))
            results["Kontakte"] = df_fn("SELECT * FROM contacts co JOIN customers c ON c.id=co.customer_id WHERE c.company LIKE ? OR c.email LIKE ?", (q,q))
            results["Rechnungen"] = df_fn("SELECT i.invoice_no, i.invoice_date, i.gross_total FROM invoices i JOIN customers c ON c.id=i.customer_id WHERE c.company LIKE ? OR c.email LIKE ?", (q,q))
            for table, df_res in results.items():
                if not df_res.empty:
                    st.subheader(f"{table} ({len(df_res)} Einträge)")
                    st.dataframe(df_res, use_container_width=True)

    with tabs[2]:
        st.subheader("Daten löschen / anonymisieren")
        st.warning("⚠️ Diese Aktion ist NICHT umkehrbar!")
        del_type = st.selectbox("Datenkategorie", ["GPS-Stempel (älter als X Monate)", "E-Mail-Protokoll (älter als X Monate)", "Audit-Log (älter als X Jahre)", "Login-Versuche (alle)"])
        months_keep = st.number_input("Aufbewahrungszeitraum", min_value=1, value=36, step=6)

        if st.button("🗑️ Jetzt bereinigen", type="primary"):
            confirm = st.session_state.get("gdpr_confirmed", False)
            if not confirm:
                st.session_state["gdpr_confirmed"] = True
                st.warning("Bitte nochmal klicken zur Bestätigung.")
            else:
                st.session_state.pop("gdpr_confirmed", None)
                cutoff = (date.today() - timedelta(days=months_keep*30)).isoformat()
                deleted = 0
                if "GPS" in del_type:
                    r = run_fn(f"DELETE FROM gps_checkins WHERE checkin_time < '{cutoff}'")
                    deleted = r.rowcount if hasattr(r, 'rowcount') else 0
                elif "E-Mail" in del_type:
                    r = run_fn(f"DELETE FROM email_log WHERE created_at < '{cutoff}'")
                    deleted = r.rowcount if hasattr(r, 'rowcount') else 0
                elif "Audit" in del_type:
                    r = run_fn(f"DELETE FROM audit_log WHERE created_at < '{cutoff}'")
                    deleted = r.rowcount if hasattr(r, 'rowcount') else 0
                elif "Login" in del_type:
                    r = run_fn("DELETE FROM login_attempts")
                    deleted = r.rowcount if hasattr(r, 'rowcount') else 0

                run_fn("INSERT INTO gdpr_deletion_log(data_type,deleted_by,reason) VALUES(?,?,?)",
                       (del_type, user.get("username","admin"), f"Löschung {del_type} älter als {months_keep} Monate"))
                log_fn("gdpr_deletion", f"{del_type} – {deleted} Einträge")
                st.success(f"✅ {deleted} Einträge gelöscht.")
                st.rerun()

    with tabs[3]:
        dl_log = df_fn("SELECT deleted_at AS Zeitpunkt, data_type AS Datentyp, deleted_by AS Benutzer, reason AS Grund FROM gdpr_deletion_log ORDER BY deleted_at DESC")
        if not dl_log.empty:
            st.dataframe(dl_log, use_container_width=True)
        else:
            st.info("Noch keine DSGVO-Aktionen durchgeführt.")


# ─────────────────────────────────────────────────────────────
# 7. Serienbrief / Briefvorlage
# ─────────────────────────────────────────────────────────────

def page_serial_letters(run_fn, df_fn, log_fn, queue_email_fn,
                         get_setting_fn) -> None:
    st.title("✉️ Serienbrief / Briefvorlage")
    st.caption("Personalisierte Briefe/E-Mails an mehrere Kunden gleichzeitig.")

    tabs = st.tabs(["📝 Vorlage erstellen", "📨 Versenden", "📋 Vorlagen verwalten"])

    VARIABLES = ["{{name}}", "{{company}}", "{{street}}", "{{zip_city}}",
                 "{{contact_person}}", "{{email}}", "{{datum}}",
                 "{{firmenname}}", "{{sachbearbeiter}}"]

    with tabs[0]:
        with st.form("letter_template", clear_on_submit=True):
            tpl_name = st.text_input("Vorlagenname *")
            subject  = st.text_input("Betreff", "Information – {{firmenname}}")
            body     = st.text_area("Brieftext *", height=250, value="""Sehr geehrte Damen und Herren,

wir freuen uns, Ihnen mitteilen zu dürfen, dass ...

Mit freundlichen Grüßen
{{sachbearbeiter}}
{{firmenname}}""")
            st.caption(f"Verfügbare Platzhalter: {' · '.join(VARIABLES)}")
            if st.form_submit_button("💾 Vorlage speichern") and tpl_name and body:
                run_fn("INSERT OR REPLACE INTO serial_letters(template_name,subject,body_html) VALUES(?,?,?)",
                       (tpl_name, subject, body))
                st.success(f"✅ Vorlage '{tpl_name}' gespeichert!")
                st.rerun()

    with tabs[1]:
        templates = df_fn("SELECT template_name, subject, body_html FROM serial_letters ORDER BY template_name")
        customers  = df_fn("SELECT id, company, contact_person, email, street, zip_city FROM customers ORDER BY company")

        if templates.empty:
            st.info("Noch keine Vorlagen. Bitte zuerst erstellen.")
            return

        sel_tpl = st.selectbox("Vorlage auswählen", templates["template_name"].tolist())
        tpl_row = templates[templates["template_name"]==sel_tpl].iloc[0]

        selected_custs = st.multiselect(
            "Empfänger auswählen (leer = alle mit E-Mail)",
            customers["company"].tolist() if not customers.empty else []
        )
        target_custs = customers[customers["company"].isin(selected_custs)] if selected_custs else customers
        target_custs = target_custs[target_custs["email"].notna() & (target_custs["email"] != "")]

        co_name    = get_setting_fn("company_name", "Byblos")
        sachb      = st.text_input("Sachbearbeiter", "Byblos Sicherheitsdienst")
        dry_run    = st.checkbox("Vorschau (kein Versand)", value=True)

        st.info(f"→ {len(target_custs)} Empfänger")

        if st.button("📨 Serienbrief versenden / vorschauen", type="primary"):
            sent = 0
            previews = []
            for _, cust in target_custs.iterrows():
                personal = str(tpl_row["body_html"])
                personal = personal.replace("{{name}}", str(cust.get("company","")))
                personal = personal.replace("{{company}}", str(cust.get("company","")))
                personal = personal.replace("{{contact_person}}", str(cust.get("contact_person","") or ""))
                personal = personal.replace("{{street}}", str(cust.get("street","") or ""))
                personal = personal.replace("{{zip_city}}", str(cust.get("zip_city","") or ""))
                personal = personal.replace("{{email}}", str(cust.get("email","") or ""))
                personal = personal.replace("{{datum}}", date.today().strftime("%d.%m.%Y"))
                personal = personal.replace("{{firmenname}}", co_name)
                personal = personal.replace("{{sachbearbeiter}}", sachb)
                subj = str(tpl_row["subject"]).replace("{{firmenname}}", co_name).replace("{{company}}", str(cust.get("company","")))

                if dry_run:
                    previews.append({"An": cust.get("email"), "Betreff": subj, "Vorschau": personal[:100]+"..."})
                else:
                    queue_email_fn(str(cust["email"]), subj, personal, "")
                    sent += 1

            if dry_run and previews:
                st.dataframe(pd.DataFrame(previews), use_container_width=True)
                st.info(f"Vorschau: {len(previews)} E-Mails würden vorbereitet.")
            elif not dry_run:
                log_fn("serial_letter_sent", f"{sel_tpl}: {sent} E-Mails")
                st.success(f"✅ {sent} E-Mails in Warteschlange!")

    with tabs[2]:
        all_tpls = df_fn("SELECT id, template_name AS Vorlage, subject AS Betreff FROM serial_letters ORDER BY template_name")
        if not all_tpls.empty:
            st.dataframe(all_tpls.drop(columns=["id"]), use_container_width=True)
            del_sel = st.selectbox("Vorlage löschen", all_tpls["Vorlage"].tolist())
            if st.button("🗑️ Vorlage löschen"):
                run_fn("DELETE FROM serial_letters WHERE template_name=?", (del_sel,))
                st.success(f"'{del_sel}' gelöscht.")
                st.rerun()
        else:
            st.info("Keine Vorlagen.")
