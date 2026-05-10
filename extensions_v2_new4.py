"""
extensions_v2_new4.py – Lohnabrechnung + Berichte + Aging + Wiedervorlagen
===========================================================================
1. Lohnabrechnung (Lohnzettel-PDF je Mitarbeiter)
2. Einsatzbericht-PDF (Objektbericht je Schicht/Periode)
3. Angebots-PDF mit Firmenlogo und Unterschriftsfeld
4. Debitorenalterung / Aging Report (0-30, 31-60, 61-90, >90 Tage)
5. Wiedervorlagen-Kalender (offene Folgeaufgaben)
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Optional

import pandas as pd
import streamlit as st


def fmt_eur(v: float) -> str:
    return f"{v:,.2f} €".replace(",", "X").replace(".", ",").replace("X", ".")


# ─────────────────────────────────────────────────────────────
# DB-Registrierung
# ─────────────────────────────────────────────────────────────

def register_new4(run_fn, df_fn) -> None:
    run_fn("""CREATE TABLE IF NOT EXISTS payroll_records (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        employee_id INTEGER NOT NULL,
        payroll_month TEXT NOT NULL,
        gross_salary REAL DEFAULT 0,
        health_ins_employee REAL DEFAULT 0,
        pension_ins_employee REAL DEFAULT 0,
        unemployment_ins_employee REAL DEFAULT 0,
        care_ins_employee REAL DEFAULT 0,
        income_tax REAL DEFAULT 0,
        solidarity_surcharge REAL DEFAULT 0,
        net_salary REAL DEFAULT 0,
        overtime_pay REAL DEFAULT 0,
        bonus REAL DEFAULT 0,
        deductions REAL DEFAULT 0,
        employer_contribution REAL DEFAULT 0,
        hours_worked REAL DEFAULT 0,
        notes TEXT,
        pdf_path TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(employee_id, payroll_month),
        FOREIGN KEY(employee_id) REFERENCES employees(id)
    )""")
    run_fn("""CREATE TABLE IF NOT EXISTS followup_tasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        due_date TEXT NOT NULL,
        title TEXT NOT NULL,
        description TEXT,
        priority TEXT DEFAULT 'normal',
        category TEXT DEFAULT 'allgemein',
        assigned_to TEXT,
        customer_id INTEGER,
        ref_type TEXT,
        ref_id INTEGER,
        status TEXT DEFAULT 'offen',
        completed_at TEXT,
        notes TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(customer_id) REFERENCES customers(id)
    )""")
    run_fn("""CREATE TABLE IF NOT EXISTS employee_qualifications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        employee_id INTEGER NOT NULL,
        qualification TEXT NOT NULL,
        issuer TEXT,
        issued_date TEXT,
        expiry_date TEXT,
        certificate_no TEXT,
        notes TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(employee_id) REFERENCES employees(id)
    )""")


# ─────────────────────────────────────────────────────────────
# 1. Lohnabrechnung
# ─────────────────────────────────────────────────────────────

def generate_payroll_pdf(employee_id: int, month: str, df_fn,
                          get_setting_fn, output_dir: Path) -> Optional[Path]:
    """Erstellt einen Lohnzettel als PDF."""
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib import colors
        from reportlab.lib.units import mm
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer,
                                         Table, TableStyle, HRFlowable)
    except ImportError:
        return None

    emp = df_fn("SELECT * FROM employees WHERE id=?", (employee_id,))
    if emp.empty:
        return None
    emp = emp.iloc[0].to_dict()

    pay = df_fn("SELECT * FROM payroll_records WHERE employee_id=? AND payroll_month=?",
                (employee_id, month))
    if pay.empty:
        return None
    pay = pay.iloc[0].to_dict()

    co_name   = get_setting_fn("company_name", "Byblos Sicherheitsdienst")
    co_street = get_setting_fn("company_street", "")
    co_zip    = get_setting_fn("company_zip_city", "")
    co_iban   = get_setting_fn("company_iban", "")

    filename = f"lohnzettel_{str(emp.get('employee_no','MA')).replace('/','_')}_{month}.pdf"
    output_path = output_dir / filename

    doc = SimpleDocTemplate(str(output_path), pagesize=A4,
                            rightMargin=18*mm, leftMargin=18*mm,
                            topMargin=15*mm, bottomMargin=15*mm)
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="Sm", fontSize=8, leading=10))
    styles.add(ParagraphStyle(name="SmB", fontSize=8, leading=10, fontName="Helvetica-Bold"))
    story = []

    # Kopf
    story.append(Paragraph(f"<b>{co_name}</b>", styles["h1"]))
    story.append(Paragraph(f"{co_street} · {co_zip}", styles["Sm"]))
    story.append(Spacer(1, 5*mm))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#c0392b")))
    story.append(Spacer(1, 5*mm))

    # Mitarbeiter-Info
    months_de = ["Januar","Februar","März","April","Mai","Juni",
                 "Juli","August","September","Oktober","November","Dezember"]
    try:
        month_name = months_de[int(month[5:7]) - 1] + " " + month[:4]
    except Exception:
        month_name = month

    story.append(Paragraph(f"<b>Lohnabrechnung {month_name}</b>", styles["h2"]))
    story.append(Spacer(1, 3*mm))

    info_data = [
        ["Mitarbeiter:", str(emp.get("name", ""))],
        ["Mitarbeiter-Nr.:", str(emp.get("employee_no", ""))],
        ["Abrechnungsmonat:", month_name],
        ["Geleistete Stunden:", f"{float(pay.get('hours_worked') or 0):.2f} h"],
    ]
    info_table = Table(info_data, colWidths=[55*mm, 110*mm])
    info_table.setStyle(TableStyle([
        ("FONTNAME", (0,0), (0,-1), "Helvetica-Bold"),
        ("FONTSIZE", (0,0), (-1,-1), 9),
        ("ROWBACKGROUNDS", (0,0), (-1,-1), [colors.white, colors.HexColor("#f5f5f5")]),
        ("GRID", (0,0), (-1,-1), 0.3, colors.HexColor("#dddddd")),
    ]))
    story.append(info_table)
    story.append(Spacer(1, 6*mm))

    # Lohn-Berechnung
    story.append(Paragraph("<b>Lohnberechnung</b>", styles["h3"]))
    gross     = float(pay.get("gross_salary") or 0)
    ot_pay    = float(pay.get("overtime_pay") or 0)
    bonus     = float(pay.get("bonus") or 0)
    health    = float(pay.get("health_ins_employee") or 0)
    pension   = float(pay.get("pension_ins_employee") or 0)
    unemploy  = float(pay.get("unemployment_ins_employee") or 0)
    care      = float(pay.get("care_ins_employee") or 0)
    inc_tax   = float(pay.get("income_tax") or 0)
    soli      = float(pay.get("solidarity_surcharge") or 0)
    other_ded = float(pay.get("deductions") or 0)
    net       = float(pay.get("net_salary") or 0)

    pay_data = [
        ["", "Betrag"],
        ["Grundlohn (Brutto)", f"{gross:.2f} €"],
        ["Überstundenvergütung", f"{ot_pay:.2f} €"],
        ["Bonus / Prämie", f"{bonus:.2f} €"],
        ["= Gesamtbrutto", f"{(gross + ot_pay + bonus):.2f} €"],
        ["", ""],
        ["Abzüge Arbeitnehmer", ""],
        ["Krankenversicherung AN", f"- {health:.2f} €"],
        ["Rentenversicherung AN", f"- {pension:.2f} €"],
        ["Arbeitslosenversicherung AN", f"- {unemploy:.2f} €"],
        ["Pflegeversicherung AN", f"- {care:.2f} €"],
        ["Lohnsteuer", f"- {inc_tax:.2f} €"],
        ["Solidaritätszuschlag", f"- {soli:.2f} €"],
        ["Sonstige Abzüge", f"- {other_ded:.2f} €"],
        ["", ""],
        ["= NETTOLOHN", f"{net:.2f} €"],
    ]

    pay_table = Table(pay_data, colWidths=[120*mm, 45*mm])
    pay_table.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#1a2744")),
        ("TEXTCOLOR", (0,0), (-1,0), colors.white),
        ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTNAME", (0,3), (-1,3), "Helvetica-Bold"),
        ("FONTNAME", (0,-1), (-1,-1), "Helvetica-Bold"),
        ("BACKGROUND", (0,-1), (-1,-1), colors.HexColor("#1a2744")),
        ("TEXTCOLOR", (0,-1), (-1,-1), colors.white),
        ("BACKGROUND", (0,3), (-1,3), colors.HexColor("#e8f5e9")),
        ("FONTSIZE", (0,0), (-1,-1), 9),
        ("ALIGN", (1,0), (1,-1), "RIGHT"),
        ("GRID", (0,0), (-1,-1), 0.25, colors.HexColor("#cccccc")),
        ("ROWBACKGROUNDS", (0,1), (-1,-2), [colors.white, colors.HexColor("#f8f8f8")]),
    ]))
    story.append(pay_table)
    story.append(Spacer(1, 8*mm))

    # Arbeitgeber-Beitrag
    ag = float(pay.get("employer_contribution") or 0)
    if ag > 0:
        story.append(Paragraph(f"Arbeitgeber-Sozialabgaben: <b>{ag:.2f} €</b> "
                               f"(nicht im Nettolohn enthalten)", styles["Sm"]))
        story.append(Spacer(1, 4*mm))

    # Auszahlung
    story.append(Paragraph(
        f"Auszahlungsbetrag: <b>{net:.2f} €</b><br/>"
        f"Überweisung auf das Konto des Mitarbeiters.",
        styles["Normal"]
    ))
    story.append(Spacer(1, 10*mm))

    # Unterschriften
    sig_data = [
        ["Arbeitgeber", "", "Arbeitnehmer"],
        ["", "", ""],
        ["", "", ""],
        [co_name, "", str(emp.get("name",""))],
        ["Datum: ___________", "", "Datum: ___________"],
    ]
    sig_table = Table(sig_data, colWidths=[75*mm, 15*mm, 75*mm])
    sig_table.setStyle(TableStyle([
        ("LINEABOVE", (0,2), (0,2), 0.5, colors.black),
        ("LINEABOVE", (2,2), (2,2), 0.5, colors.black),
        ("FONTSIZE", (0,0), (-1,-1), 8),
        ("FONTNAME", (0,0), (0,0), "Helvetica-Bold"),
        ("FONTNAME", (2,0), (2,0), "Helvetica-Bold"),
    ]))
    story.append(sig_table)
    story.append(Spacer(1, 6*mm))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#cccccc")))
    story.append(Paragraph(
        "Dieser Lohnzettel ist maschinell erstellt und gilt ohne Unterschrift. "
        "Aufbewahrungsfrist: 10 Jahre.",
        styles["Sm"]
    ))

    doc.build(story)
    return output_path


def page_payroll(run_fn, df_fn, log_fn, get_setting_fn, base_dir: Path) -> None:
    st.title("💶 Lohnabrechnung")

    payroll_dir = base_dir / "generated" / "payroll"
    payroll_dir.mkdir(parents=True, exist_ok=True)

    tabs = st.tabs(["📋 Übersicht", "➕ Abrechnung erstellen",
                    "📄 PDF-Lohnzettel", "📊 Jahres-Lohnkonto"])

    # ── Tab 0: Übersicht ──────────────────────────────────────
    with tabs[0]:
        col1, col2 = st.columns(2)
        year_f  = col1.selectbox("Jahr", list(range(date.today().year, date.today().year - 3, -1)))
        month_f = col2.selectbox("Monat", list(range(1, 13)),
                                  index=date.today().month - 1,
                                  format_func=lambda m: ["Jan","Feb","Mär","Apr","Mai","Jun",
                                                          "Jul","Aug","Sep","Okt","Nov","Dez"][m-1])
        month_str = f"{year_f}-{month_f:02d}"

        data = df_fn("""
            SELECT e.name AS Mitarbeiter, e.employee_no AS Nr,
                   p.gross_salary AS Brutto, p.net_salary AS Netto,
                   p.hours_worked AS Stunden, p.overtime_pay AS Überstunden_EUR,
                   p.income_tax AS Lohnsteuer, p.employer_contribution AS AG_Beitrag,
                   p.payroll_month AS Monat
            FROM payroll_records p JOIN employees e ON e.id=p.employee_id
            WHERE p.payroll_month=?
            ORDER BY e.name
        """, (month_str,))

        if not data.empty:
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Mitarbeiter", len(data))
            c2.metric("Bruttogehälter", fmt_eur(float(data["Brutto"].sum())))
            c3.metric("Nettogehälter", fmt_eur(float(data["Netto"].sum())))
            c4.metric("AG-Kosten gesamt", fmt_eur(
                float(data["Brutto"].sum()) + float(data["AG_Beitrag"].sum())))
            st.dataframe(data, use_container_width=True)
            csv = data.to_csv(index=False, sep=";").encode("utf-8-sig")
            st.download_button("📥 Lohnliste CSV", csv, f"lohnliste_{month_str}.csv", "text/csv")
        else:
            st.info(f"Noch keine Abrechnungen für {month_str}.")

    # ── Tab 1: Abrechnung erstellen ───────────────────────────
    with tabs[1]:
        employees = df_fn("SELECT id, employee_no || ' – ' || name AS label, name FROM employees WHERE active=1 ORDER BY name")
        if employees.empty:
            st.warning("Keine aktiven Mitarbeiter.")
            return

        with st.form("payroll_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            emp_label = col1.selectbox("Mitarbeiter *", employees["label"].tolist())
            month_in  = col2.text_input("Monat (YYYY-MM) *", date.today().strftime("%Y-%m"))

            st.subheader("Vergütung")
            a, b, c = st.columns(3)
            gross       = a.number_input("Grundlohn Brutto (€)", min_value=0.0, value=2000.0, step=50.0)
            hours       = b.number_input("Geleistete Stunden", min_value=0.0, value=160.0, step=0.5)
            ot_pay      = c.number_input("Überstunden-Vergütung (€)", min_value=0.0, value=0.0, step=10.0)
            bonus       = a.number_input("Bonus / Prämie (€)", min_value=0.0, value=0.0, step=50.0)

            st.subheader("Abzüge Arbeitnehmer")
            a2, b2, c2 = st.columns(3)
            health    = a2.number_input("KV (€)", min_value=0.0, value=round(gross * 0.073, 2), step=1.0)
            pension   = b2.number_input("RV (€)", min_value=0.0, value=round(gross * 0.093, 2), step=1.0)
            unemploy  = c2.number_input("AV (€)", min_value=0.0, value=round(gross * 0.013, 2), step=1.0)
            care      = a2.number_input("PV (€)", min_value=0.0, value=round(gross * 0.0175, 2), step=1.0)
            inc_tax   = b2.number_input("Lohnsteuer (€)", min_value=0.0, value=0.0, step=10.0)
            soli      = c2.number_input("Soli (€)", min_value=0.0, value=0.0, step=1.0)
            other_ded = a2.number_input("Sonstige Abzüge (€)", min_value=0.0, value=0.0, step=5.0)

            total_deductions = health + pension + unemploy + care + inc_tax + soli + other_ded
            net = gross + ot_pay + bonus - total_deductions
            ag_contrib = round((health + pension + unemploy + care), 2)  # AG zahlt gleichviel

            st.info(f"**Nettolohn: {fmt_eur(net)}** · Abzüge: {fmt_eur(total_deductions)} · AG-Beitrag: {fmt_eur(ag_contrib)}")
            notes = st.text_area("Notizen")
            submitted = st.form_submit_button("💾 Lohnabrechnung speichern", type="primary")

        if submitted and month_in:
            eid = int(employees[employees["label"] == emp_label].iloc[0]["id"])
            run_fn("""INSERT OR REPLACE INTO payroll_records
                (employee_id,payroll_month,gross_salary,net_salary,hours_worked,
                 overtime_pay,bonus,health_ins_employee,pension_ins_employee,
                 unemployment_ins_employee,care_ins_employee,income_tax,
                 solidarity_surcharge,deductions,employer_contribution,notes)
                VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                   (eid, month_in, gross, net, hours, ot_pay, bonus,
                    health, pension, unemploy, care, inc_tax, soli,
                    other_ded, ag_contrib, notes))
            log_fn("payroll_saved", f"{emp_label} {month_in}")
            st.success(f"✅ Lohnabrechnung für {emp_label} ({month_in}) gespeichert!")
            st.rerun()

    # ── Tab 2: PDF-Lohnzettel ─────────────────────────────────
    with tabs[2]:
        employees2 = df_fn("SELECT id, employee_no || ' – ' || name AS label FROM employees WHERE active=1 ORDER BY name")
        col1, col2 = st.columns(2)
        emp2   = col1.selectbox("Mitarbeiter", employees2["label"].tolist() if not employees2.empty else ["—"])
        month2 = col2.text_input("Monat", date.today().strftime("%Y-%m"), key="pay_pdf_month")

        if st.button("📄 Lohnzettel-PDF erstellen", type="primary") and not employees2.empty:
            eid2 = int(employees2[employees2["label"] == emp2].iloc[0]["id"])
            with st.spinner("PDF wird erstellt..."):
                path = generate_payroll_pdf(eid2, month2, df_fn, get_setting_fn, payroll_dir)
            if path and path.exists():
                st.success(f"✅ {path.name}")
                st.download_button("📥 Lohnzettel herunterladen",
                                   path.read_bytes(), path.name, "application/pdf")
                run_fn("UPDATE payroll_records SET pdf_path=? WHERE employee_id=? AND payroll_month=?",
                       (str(path), eid2, month2))
            else:
                st.error("PDF-Erstellung fehlgeschlagen (ReportLab prüfen).")

        # Alle Lohnzettel eines Monats
        st.divider()
        all_month = st.text_input("Alle PDFs für Monat erstellen:", date.today().strftime("%Y-%m"), key="all_pay")
        if st.button(f"📄 Alle Lohnzettel für {all_month} erstellen"):
            pending = df_fn("""
                SELECT p.employee_id, e.name FROM payroll_records p
                JOIN employees e ON e.id=p.employee_id
                WHERE p.payroll_month=? AND (p.pdf_path IS NULL OR p.pdf_path='')
            """, (all_month,))
            created = 0
            for _, row in pending.iterrows():
                path = generate_payroll_pdf(int(row["employee_id"]), all_month,
                                            df_fn, get_setting_fn, payroll_dir)
                if path:
                    run_fn("UPDATE payroll_records SET pdf_path=? WHERE employee_id=? AND payroll_month=?",
                           (str(path), int(row["employee_id"]), all_month))
                    created += 1
            st.success(f"✅ {created} Lohnzettel erstellt in {payroll_dir}")

    # ── Tab 3: Jahres-Lohnkonto ───────────────────────────────
    with tabs[3]:
        employees3 = df_fn("SELECT id, employee_no || ' – ' || name AS label FROM employees ORDER BY name")
        if employees3.empty:
            st.info("Keine Mitarbeiter.")
            return
        sel3  = st.selectbox("Mitarbeiter", employees3["label"].tolist())
        year3 = st.selectbox("Jahr", list(range(date.today().year, date.today().year - 5, -1)), key="pay_year3")
        eid3  = int(employees3[employees3["label"] == sel3].iloc[0]["id"])

        annual = df_fn("""
            SELECT payroll_month AS Monat, gross_salary AS Brutto,
                   net_salary AS Netto, hours_worked AS Stunden,
                   overtime_pay AS Überstunden_EUR, income_tax AS Lohnsteuer,
                   employer_contribution AS AG_Beitrag
            FROM payroll_records
            WHERE employee_id=? AND substr(payroll_month,1,4)=?
            ORDER BY payroll_month
        """, (eid3, str(year3)))

        if not annual.empty:
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Bruttogehälter", fmt_eur(float(annual["Brutto"].sum())))
            c2.metric("Nettogehälter", fmt_eur(float(annual["Netto"].sum())))
            c3.metric("Lohnsteuer gesamt", fmt_eur(float(annual["Lohnsteuer"].sum())))
            c4.metric("Geleistete Stunden", f"{float(annual['Stunden'].sum()):.0f} h")
            st.dataframe(annual, use_container_width=True)
            st.bar_chart(annual.set_index("Monat")[["Brutto","Netto"]])
        else:
            st.info(f"Keine Abrechnungen für {sel3} in {year3}.")


# ─────────────────────────────────────────────────────────────
# 2. Einsatzbericht-PDF
# ─────────────────────────────────────────────────────────────

def generate_mission_report_pdf(customer_id: int, from_date: str, to_date: str,
                                 df_fn, get_setting_fn, output_dir: Path) -> Optional[Path]:
    """Erstellt einen Einsatzbericht-PDF für einen Kunden."""
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib import colors
        from reportlab.lib.units import mm
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer,
                                         Table, TableStyle, HRFlowable)
    except ImportError:
        return None

    cust = df_fn("SELECT * FROM customers WHERE id=?", (customer_id,))
    if cust.empty:
        return None
    cust = cust.iloc[0].to_dict()

    shifts = df_fn("""
        SELECT s.shift_date AS Datum, s.start_time AS Von, s.end_time AS Bis,
               s.shift_type AS Art, s.location AS Ort, s.status AS Status,
               COALESCE(e.name,'–') AS Mitarbeiter, s.notes AS Notiz
        FROM shifts s LEFT JOIN employees e ON e.id=s.employee_id
        WHERE s.customer_id=? AND s.shift_date BETWEEN ? AND ?
        ORDER BY s.shift_date, s.start_time
    """, (customer_id, from_date, to_date))

    co_name = get_setting_fn("company_name", "Byblos Sicherheitsdienst")
    output_path = output_dir / f"einsatzbericht_{cust.get('customer_no','K')}_{from_date}_{to_date}.pdf"

    doc = SimpleDocTemplate(str(output_path), pagesize=A4,
                            rightMargin=18*mm, leftMargin=18*mm,
                            topMargin=15*mm, bottomMargin=15*mm)
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="Sm", fontSize=8, leading=10))
    story = []

    story.append(Paragraph(f"<b>EINSATZBERICHT</b>", styles["h1"]))
    story.append(Paragraph(f"<b>{co_name}</b>", styles["h2"]))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#c0392b")))
    story.append(Spacer(1, 5*mm))

    story.append(Paragraph(f"<b>Auftraggeber:</b> {cust.get('company','')}", styles["Normal"]))
    story.append(Paragraph(f"<b>Ansprechperson:</b> {cust.get('contact_person','')}", styles["Normal"]))
    story.append(Paragraph(f"<b>Berichtszeitraum:</b> {from_date} bis {to_date}", styles["Normal"]))
    story.append(Spacer(1, 5*mm))

    if not shifts.empty:
        total = len(shifts)
        done  = len(shifts[shifts["Status"] == "abgeschlossen"])
        story.append(Paragraph(f"<b>Einsätze gesamt:</b> {total} · <b>Abgeschlossen:</b> {done} · <b>Erfüllungsrate:</b> {done/total*100:.0f}%", styles["Normal"]))
        story.append(Spacer(1, 4*mm))

        rows = [["Datum","Von","Bis","Typ","Mitarbeiter","Ort","Status"]]
        for _, r in shifts.iterrows():
            rows.append([str(r["Datum"]), str(r["Von"])[:5], str(r["Bis"])[:5],
                         str(r["Art"]), str(r["Mitarbeiter"])[:20],
                         str(r["Ort"])[:20], str(r["Status"])])
        t = Table(rows, colWidths=[20*mm,12*mm,12*mm,25*mm,35*mm,35*mm,22*mm])
        t.setStyle(TableStyle([
            ("BACKGROUND",(0,0),(-1,0),colors.HexColor("#1a2744")),
            ("TEXTCOLOR",(0,0),(-1,0),colors.white),
            ("FONTNAME",(0,0),(-1,0),"Helvetica-Bold"),
            ("FONTSIZE",(0,0),(-1,-1),7),
            ("GRID",(0,0),(-1,-1),0.25,colors.HexColor("#cccccc")),
            ("ROWBACKGROUNDS",(0,1),(-1,-1),[colors.white,colors.HexColor("#f5f5f5")]),
        ]))
        story.append(t)
    else:
        story.append(Paragraph("Keine Einsätze im angegebenen Zeitraum.", styles["Normal"]))

    story.append(Spacer(1, 12*mm))
    sig_data = [["Auftraggeber","","Auftragnehmer"],["","",""],
                [cust.get("company",""),"",co_name],
                ["Datum: ___________","","Datum: ___________"]]
    sig_t = Table(sig_data, colWidths=[75*mm,15*mm,75*mm])
    sig_t.setStyle(TableStyle([
        ("LINEABOVE",(0,1),(0,1),0.5,colors.black),
        ("LINEABOVE",(2,1),(2,1),0.5,colors.black),
        ("FONTSIZE",(0,0),(-1,-1),8),
        ("FONTNAME",(0,0),(0,0),"Helvetica-Bold"),
        ("FONTNAME",(2,0),(2,0),"Helvetica-Bold"),
    ]))
    story.append(sig_t)
    doc.build(story)
    return output_path


def page_mission_reports(run_fn, df_fn, get_setting_fn, base_dir: Path) -> None:
    st.title("📋 Einsatzberichte")
    report_dir = base_dir / "generated" / "reports"
    report_dir.mkdir(parents=True, exist_ok=True)

    tabs = st.tabs(["➕ Neuer Bericht", "📁 Gespeicherte Berichte"])

    with tabs[0]:
        customers = df_fn("SELECT id, customer_no || ' – ' || company AS label FROM customers ORDER BY company")
        if customers.empty:
            st.info("Noch keine Kunden.")
            return
        col1, col2, col3 = st.columns(3)
        cust_label = col1.selectbox("Kunde *", customers["label"].tolist())
        from_d = col2.date_input("Von", date.today().replace(day=1))
        to_d   = col3.date_input("Bis", date.today())

        cid = int(customers[customers["label"] == cust_label].iloc[0]["id"])

        # Vorschau
        preview = df_fn("""
            SELECT COUNT(*) AS n,
                   SUM(CASE WHEN status='abgeschlossen' THEN 1 ELSE 0 END) AS done
            FROM shifts WHERE customer_id=? AND shift_date BETWEEN ? AND ?
        """, (cid, from_d.isoformat(), to_d.isoformat())).iloc[0]

        col1, col2 = st.columns(2)
        col1.metric("Schichten gesamt", int(preview["n"] or 0))
        col2.metric("Abgeschlossen", int(preview["done"] or 0))

        if st.button("📄 Einsatzbericht-PDF erstellen", type="primary"):
            with st.spinner("PDF wird erstellt..."):
                path = generate_mission_report_pdf(cid, from_d.isoformat(), to_d.isoformat(),
                                                    df_fn, get_setting_fn, report_dir)
            if path and path.exists():
                st.success(f"✅ {path.name}")
                st.download_button("📥 PDF herunterladen", path.read_bytes(),
                                   path.name, "application/pdf")
            else:
                st.error("PDF-Erstellung fehlgeschlagen.")

    with tabs[1]:
        reports = sorted(report_dir.glob("einsatzbericht_*.pdf"), reverse=True)
        if reports:
            for r in reports[:20]:
                col1, col2 = st.columns([4, 1])
                col1.write(f"📋 {r.name} ({r.stat().st_size//1024} KB)")
                col2.download_button("⬇", r.read_bytes(), r.name,
                                     "application/pdf", key=f"dl_{r.name}")
        else:
            st.info("Noch keine Einsatzberichte erstellt.")


# ─────────────────────────────────────────────────────────────
# 3. Debitorenalterung (Aging Report)
# ─────────────────────────────────────────────────────────────

def page_aging_report(df_fn) -> None:
    st.title("⏳ Debitorenalterung (Aging Report)")
    st.caption("Offene Rechnungen nach Fälligkeitsalter gruppiert (0-30, 31-60, 61-90, >90 Tage).")

    today = date.today()

    aging = df_fn("""
        SELECT i.invoice_no AS Nr, c.company AS Kunde, c.email AS E_Mail,
               i.invoice_date AS Rechnungsdatum, i.due_date AS Fällig,
               CAST(julianday('now') - julianday(i.due_date) AS INTEGER) AS Tage_Überfällig,
               ROUND(i.gross_total - i.paid_amount, 2) AS Offen_EUR,
               i.gross_total AS Brutto, i.status AS Status
        FROM invoices i JOIN customers c ON c.id=i.customer_id
        WHERE i.status IN ('offen','ueberfaellig','teilbezahlt')
          AND ROUND(i.gross_total - i.paid_amount, 2) > 0
        ORDER BY Tage_Überfällig DESC
    """)

    if aging.empty:
        st.success("✅ Keine offenen Posten!")
        return

    def bucket(days: int) -> str:
        if days <= 0:   return "🟢 Noch nicht fällig"
        elif days <= 30: return "🟡 1–30 Tage"
        elif days <= 60: return "🟠 31–60 Tage"
        elif days <= 90: return "🔴 61–90 Tage"
        else:            return "⛔ >90 Tage"

    aging["Altersgruppe"] = aging["Tage_Überfällig"].apply(bucket)

    # KPI-Zeile
    total_open = float(aging["Offen_EUR"].sum())
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Offene Rechnungen", len(aging))
    c2.metric("Summe offen", fmt_eur(total_open))
    over_30 = float(aging[aging["Tage_Überfällig"] > 30]["Offen_EUR"].sum())
    over_60 = float(aging[aging["Tage_Überfällig"] > 60]["Offen_EUR"].sum())
    over_90 = float(aging[aging["Tage_Überfällig"] > 90]["Offen_EUR"].sum())
    c3.metric("🟠 >30 Tage", fmt_eur(over_30))
    c4.metric("🔴 >60 Tage", fmt_eur(over_60))
    c5.metric("⛔ >90 Tage", fmt_eur(over_90))

    # Altersgruppen-Zusammenfassung
    st.subheader("Zusammenfassung nach Altersgruppen")
    summary = aging.groupby("Altersgruppe").agg(
        Rechnungen=("Nr", "count"),
        Summe_EUR=("Offen_EUR", "sum")
    ).reset_index()
    summary["Anteil_Pct"] = (summary["Summe_EUR"] / total_open * 100).round(1)
    summary["Summe_EUR"]  = summary["Summe_EUR"].round(2)
    st.dataframe(summary, use_container_width=True)
    st.bar_chart(summary.set_index("Altersgruppe")["Summe_EUR"])

    st.divider()
    # Detailliste mit Farbfilter
    group_filter = st.selectbox("Detailansicht filtern", ["alle"] + summary["Altersgruppe"].tolist())
    detail = aging if group_filter == "alle" else aging[aging["Altersgruppe"] == group_filter]
    st.dataframe(detail.drop(columns=["Altersgruppe"]), use_container_width=True, height=350)

    # Export
    csv = aging.to_csv(index=False, sep=";").encode("utf-8-sig")
    st.download_button("📥 Aging-Report CSV", csv,
                       f"aging_report_{today.isoformat()}.csv", "text/csv")

    # Handlungsempfehlungen
    if over_90 > 0:
        st.error(f"⛔ **{fmt_eur(over_90)}** sind seit über 90 Tagen überfällig! "
                 f"Inkasso-Verfahren prüfen.")
    elif over_60 > 0:
        st.warning(f"🔴 **{fmt_eur(over_60)}** über 60 Tage offen — "
                   f"letzte Mahnung / Zahlungsvereinbarung empfohlen.")


# ─────────────────────────────────────────────────────────────
# 4. Wiedervorlagen-Kalender
# ─────────────────────────────────────────────────────────────

def page_followup_calendar(run_fn, df_fn, log_fn) -> None:
    st.title("🗓️ Wiedervorlagen & Aufgaben")

    PRIORITIES   = ["hoch", "normal", "niedrig"]
    CATEGORIES   = ["Mahnung", "Kundenbesuch", "Angebot", "Vertrag", "Personal",
                    "Behörde", "Buchhaltung", "allgemein"]
    TASK_STATUS  = ["offen", "in Bearbeitung", "erledigt", "verschoben"]

    tabs = st.tabs([
        "🔔 Heute & Überfällig", "📋 Alle Aufgaben",
        "➕ Neue Aufgabe", "📊 Auswertung"
    ])

    # ── Tab 0: Heute & Überfällig ─────────────────────────────
    with tabs[0]:
        today = date.today().isoformat()
        tomorrow = (date.today() + timedelta(days=1)).isoformat()

        urgent = df_fn("""
            SELECT ft.id, ft.due_date AS Fällig, ft.title AS Aufgabe,
                   ft.priority AS Priorität, ft.category AS Kategorie,
                   ft.assigned_to AS Zuständig,
                   COALESCE(c.company,'–') AS Kunde, ft.status AS Status
            FROM followup_tasks ft
            LEFT JOIN customers c ON c.id=ft.customer_id
            WHERE ft.status NOT IN ('erledigt')
              AND ft.due_date <= ?
            ORDER BY ft.due_date, ft.priority
        """, (tomorrow,))

        if not urgent.empty:
            overdue = urgent[urgent["Fällig"] < today]
            due_today = urgent[urgent["Fällig"] == today]
            due_tomorrow = urgent[urgent["Fällig"] == tomorrow]

            c1, c2, c3 = st.columns(3)
            c1.metric("⛔ Überfällig", len(overdue))
            c2.metric("📅 Heute fällig", len(due_today))
            c3.metric("⏰ Morgen fällig", len(due_tomorrow))

            if not overdue.empty:
                st.error("⛔ Überfällige Aufgaben:")
                st.dataframe(overdue.drop(columns=["id"]), use_container_width=True)
            if not due_today.empty:
                st.warning("📅 Heute fällig:")
                for _, row in due_today.iterrows():
                    col1, col2, col3 = st.columns([3, 1, 1])
                    col1.markdown(f"**{row['Aufgabe']}** · {row['Kategorie']} · {row['Kunde']}")
                    col2.markdown(f"_{row['Priorität']}_")
                    if col3.button("✅ Erledigt", key=f"done_{row['id']}"):
                        run_fn("UPDATE followup_tasks SET status='erledigt', completed_at=? WHERE id=?",
                               (datetime.now().isoformat()[:19], int(row["id"])))
                        st.rerun()
        else:
            st.success("✅ Keine überfälligen oder heute fälligen Aufgaben!")

        # Nächste 7 Tage
        next_week = (date.today() + timedelta(days=7)).isoformat()
        upcoming = df_fn("""
            SELECT ft.due_date AS Fällig, ft.title AS Aufgabe,
                   ft.priority AS Priorität, ft.category AS Kategorie,
                   COALESCE(c.company,'–') AS Kunde
            FROM followup_tasks ft
            LEFT JOIN customers c ON c.id=ft.customer_id
            WHERE ft.status NOT IN ('erledigt')
              AND ft.due_date > ? AND ft.due_date <= ?
            ORDER BY ft.due_date
        """, (tomorrow, next_week))
        if not upcoming.empty:
            st.info(f"📅 {len(upcoming)} Aufgabe(n) in den nächsten 7 Tagen")
            st.dataframe(upcoming, use_container_width=True)

    # ── Tab 1: Alle Aufgaben ──────────────────────────────────
    with tabs[1]:
        col1, col2 = st.columns(2)
        status_f = col1.selectbox("Status", ["offen", "in Bearbeitung", "alle", "erledigt"])
        prio_f   = col2.selectbox("Priorität", ["alle"] + PRIORITIES)

        q = "SELECT ft.id, ft.due_date AS Fällig, ft.title AS Aufgabe, ft.priority AS Priorität, ft.category AS Kategorie, ft.assigned_to AS Zuständig, COALESCE(c.company,'–') AS Kunde, ft.status AS Status FROM followup_tasks ft LEFT JOIN customers c ON c.id=ft.customer_id"
        where, params = [], []
        if status_f != "alle":
            where.append("ft.status=?"); params.append(status_f)
        if prio_f != "alle":
            where.append("ft.priority=?"); params.append(prio_f)
        if where:
            q += " WHERE " + " AND ".join(where)
        q += " ORDER BY ft.due_date, ft.priority"
        all_tasks = df_fn(q, tuple(params))

        if not all_tasks.empty:
            st.caption(f"{len(all_tasks)} Aufgaben")
            st.dataframe(all_tasks.drop(columns=["id"]), use_container_width=True, height=350)
            # Status-Änderung
            if not all_tasks[all_tasks["Status"] != "erledigt"].empty:
                task_labels = all_tasks[all_tasks["Status"] != "erledigt"]["Aufgabe"].tolist()
                sel = st.selectbox("Status ändern für:", task_labels)
                tid = int(all_tasks[all_tasks["Aufgabe"] == sel].iloc[0]["id"])
                col1, col2 = st.columns(2)
                new_status = col1.selectbox("Neuer Status", TASK_STATUS)
                if col2.button("💾 Status setzen"):
                    run_fn("UPDATE followup_tasks SET status=? WHERE id=?", (new_status, tid))
                    if new_status == "erledigt":
                        run_fn("UPDATE followup_tasks SET completed_at=? WHERE id=?",
                               (datetime.now().isoformat()[:19], tid))
                    st.rerun()
        else:
            st.info("Keine Aufgaben mit diesen Filtern.")

    # ── Tab 2: Neue Aufgabe ───────────────────────────────────
    with tabs[2]:
        customers = df_fn("SELECT id, customer_no || ' – ' || company AS label FROM customers ORDER BY company")
        with st.form("followup_form", clear_on_submit=True):
            title = st.text_input("Aufgabe / Titel *")
            col1, col2, col3 = st.columns(3)
            due_date  = col1.date_input("Fällig bis *", date.today() + timedelta(days=3))
            priority  = col2.selectbox("Priorität", PRIORITIES)
            category  = col3.selectbox("Kategorie", CATEGORIES)
            cust_label = st.selectbox("Kunde (optional)", ["—"] + (customers["label"].tolist() if not customers.empty else []))
            assigned   = st.text_input("Zuständig")
            description = st.text_area("Beschreibung")
            notes       = st.text_area("Notizen")
            submitted = st.form_submit_button("💾 Aufgabe speichern", type="primary")

        if submitted and title:
            cid = None
            if cust_label != "—" and not customers.empty:
                match = customers[customers["label"] == cust_label]
                if not match.empty:
                    cid = int(match.iloc[0]["id"])
            run_fn("""INSERT INTO followup_tasks(due_date,title,description,priority,
                      category,assigned_to,customer_id,notes)
                      VALUES(?,?,?,?,?,?,?,?)""",
                   (due_date.isoformat(), title, description, priority,
                    category, assigned, cid, notes))
            log_fn("followup_created", title)
            st.success(f"✅ Aufgabe '{title}' (fällig: {due_date}) gespeichert!")
            st.rerun()

    # ── Tab 3: Auswertung ─────────────────────────────────────
    with tabs[3]:
        st.subheader("Aufgaben-Statistik")
        stats = df_fn("""
            SELECT status AS Status, priority AS Priorität, COUNT(*) AS Anzahl
            FROM followup_tasks
            GROUP BY status, priority ORDER BY status, priority
        """)
        if not stats.empty:
            st.dataframe(stats, use_container_width=True)
            pivot = stats.pivot_table(index="Status", columns="Priorität",
                                      values="Anzahl", fill_value=0)
            st.bar_chart(pivot)
        else:
            st.info("Noch keine Aufgaben.")
