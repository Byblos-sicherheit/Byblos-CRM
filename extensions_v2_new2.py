"""
extensions_v2_new2.py – Urlaubsplanung + Fahrtenbuch + SLA + Projekte
======================================================================
1. Mitarbeiter-Urlaubsplanung (Antrag, Genehmigung, Resturlaub)
2. Fahrtenbuch (km-Erfassung, Kilometerpauschale, Export)
3. SLA-Monitoring (Vertragserfüllung je Objekt)
4. Kundenprojekt-Tracking (Phasen, Budget, Zeitbuchung)
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Dict, List

import pandas as pd
import streamlit as st


def fmt_eur(v: float) -> str:
    return f"{v:,.2f} €".replace(",", "X").replace(".", ",").replace("X", ".")


# ─────────────────────────────────────────────────────────────
# DB-Registrierung
# ─────────────────────────────────────────────────────────────

def register_new2(run_fn, df_fn) -> None:
    run_fn("""CREATE TABLE IF NOT EXISTS leave_requests (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        employee_id INTEGER NOT NULL,
        leave_type TEXT DEFAULT 'Urlaub',
        start_date TEXT NOT NULL,
        end_date TEXT NOT NULL,
        days_requested REAL DEFAULT 1,
        status TEXT DEFAULT 'beantragt',
        approved_by TEXT,
        notes TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(employee_id) REFERENCES employees(id)
    )""")
    run_fn("""CREATE TABLE IF NOT EXISTS leave_balances (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        employee_id INTEGER UNIQUE NOT NULL,
        year INTEGER NOT NULL,
        entitlement REAL DEFAULT 24,
        taken REAL DEFAULT 0,
        carry_over REAL DEFAULT 0,
        FOREIGN KEY(employee_id) REFERENCES employees(id)
    )""")
    run_fn("""CREATE TABLE IF NOT EXISTS mileage_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        employee_id INTEGER,
        log_date TEXT NOT NULL,
        from_location TEXT NOT NULL,
        to_location TEXT NOT NULL,
        km_distance REAL DEFAULT 0,
        purpose TEXT,
        vehicle TEXT DEFAULT 'Dienst-Kfz',
        reimbursement_rate REAL DEFAULT 0.30,
        reimbursement_amount REAL DEFAULT 0,
        status TEXT DEFAULT 'offen',
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(employee_id) REFERENCES employees(id)
    )""")
    run_fn("""CREATE TABLE IF NOT EXISTS sla_contracts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        customer_id INTEGER NOT NULL,
        contract_name TEXT NOT NULL,
        location TEXT,
        target_hours_weekly REAL DEFAULT 0,
        target_shifts_weekly INTEGER DEFAULT 0,
        start_date TEXT NOT NULL,
        end_date TEXT,
        hourly_rate REAL DEFAULT 0,
        status TEXT DEFAULT 'aktiv',
        notes TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(customer_id) REFERENCES customers(id)
    )""")
    run_fn("""CREATE TABLE IF NOT EXISTS projects (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        project_no TEXT UNIQUE,
        customer_id INTEGER,
        project_name TEXT NOT NULL,
        description TEXT,
        start_date TEXT,
        end_date TEXT,
        budget_eur REAL DEFAULT 0,
        billed_eur REAL DEFAULT 0,
        status TEXT DEFAULT 'aktiv',
        notes TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(customer_id) REFERENCES customers(id)
    )""")
    run_fn("""CREATE TABLE IF NOT EXISTS project_time (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        project_id INTEGER NOT NULL,
        employee_id INTEGER,
        log_date TEXT NOT NULL,
        hours REAL DEFAULT 0,
        description TEXT,
        billable INTEGER DEFAULT 1,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(project_id) REFERENCES projects(id),
        FOREIGN KEY(employee_id) REFERENCES employees(id)
    )""")


# ─────────────────────────────────────────────────────────────
# 1. Urlaubsplanung
# ─────────────────────────────────────────────────────────────

def page_leave_planning(run_fn, df_fn, log_fn, current_user_fn) -> None:
    st.title("🏖️ Urlaubsplanung")

    LEAVE_TYPES = ["Urlaub", "Krankheit", "Gleitzeit", "Sonderurlaub",
                   "Unbezahlter Urlaub", "Fortbildung", "Elternzeit"]
    LEAVE_STATUS = ["beantragt", "genehmigt", "abgelehnt", "storniert"]

    tabs = st.tabs([
        "📋 Antragsübersicht", "➕ Antrag stellen",
        "✅ Genehmigen", "📊 Urlaubskonto", "📅 Jahresübersicht"
    ])

    user = current_user_fn() or {}
    is_manager = user.get("role", "").lower() in ("admin", "manager", "administrator")

    # ── Tab 0: Übersicht ──────────────────────────────────────
    with tabs[0]:
        col1, col2 = st.columns(2)
        status_f = col1.selectbox("Status", ["alle"] + LEAVE_STATUS)
        year_f   = col2.selectbox("Jahr", list(range(date.today().year, date.today().year - 3, -1)))

        query = """
            SELECT lr.id, e.name AS Mitarbeiter, lr.leave_type AS Art,
                   lr.start_date AS Von, lr.end_date AS Bis,
                   lr.days_requested AS Tage,
                   lr.status AS Status, lr.approved_by AS Genehmigt_von,
                   lr.notes AS Notiz, lr.created_at AS Beantragt
            FROM leave_requests lr JOIN employees e ON e.id=lr.employee_id
            WHERE substr(lr.start_date,1,4)=?
        """
        params = [str(year_f)]
        if status_f != "alle":
            query += " AND lr.status=?"; params.append(status_f)
        query += " ORDER BY lr.start_date DESC"

        data = df_fn(query, tuple(params))
        if not data.empty:
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Anträge", len(data))
            c2.metric("Genehmigt", len(data[data["Status"]=="genehmigt"]))
            c3.metric("Beantragt", len(data[data["Status"]=="beantragt"]))
            c4.metric("Urlaubstage gesamt", float(data[data["Status"]=="genehmigt"]["Tage"].sum()))
            st.dataframe(data.drop(columns=["id"]), use_container_width=True, height=350)
            csv = data.drop(columns=["id"]).to_csv(index=False, sep=";").encode("utf-8-sig")
            st.download_button("📥 CSV-Export", csv, f"urlaub_{year_f}.csv", "text/csv")
        else:
            st.info("Keine Urlaubsanträge in diesem Zeitraum.")

    # ── Tab 1: Antrag stellen ─────────────────────────────────
    with tabs[1]:
        employees = df_fn("SELECT id, name FROM employees WHERE active=1 ORDER BY name")
        if employees.empty:
            st.warning("Keine aktiven Mitarbeiter.")
            return

        with st.form("leave_form", clear_on_submit=True):
            emp_label = st.selectbox("Mitarbeiter *", employees["name"].tolist())
            leave_type = st.selectbox("Urlaubsart", LEAVE_TYPES)
            a, b = st.columns(2)
            start = a.date_input("Von *", date.today())
            end   = b.date_input("Bis *", date.today())
            notes = st.text_area("Notizen / Begründung")

            # Arbeitstage berechnen (Mo-Fr)
            if start <= end:
                days = sum(1 for d in range((end - start).days + 1)
                          if (start + timedelta(days=d)).weekday() < 5)
                st.info(f"📅 {days} Arbeitstag(e) ({(end - start).days + 1} Kalendertage)")
            else:
                days = 0
                st.error("Enddatum vor Startdatum!")

            submitted = st.form_submit_button("📨 Antrag einreichen", type="primary")

        if submitted and days > 0:
            eid = int(employees[employees["name"] == emp_label].iloc[0]["id"])
            run_fn("""INSERT INTO leave_requests(employee_id,leave_type,start_date,end_date,days_requested,status,notes)
                      VALUES(?,?,?,?,?,?,?)""",
                   (eid, leave_type, start.isoformat(), end.isoformat(), days, "beantragt", notes))
            log_fn("leave_request", f"{emp_label}: {leave_type} {start}–{end} ({days}d)")
            st.success(f"✅ Antrag für {emp_label} eingereicht: {leave_type} {start} – {end} ({days} Arbeitstage)")
            st.rerun()

    # ── Tab 2: Genehmigen ─────────────────────────────────────
    with tabs[2]:
        if not is_manager:
            st.warning("Nur Manager und Admins können Anträge genehmigen.")
            return

        pending = df_fn("""
            SELECT lr.id, e.name AS Mitarbeiter, lr.leave_type AS Art,
                   lr.start_date AS Von, lr.end_date AS Bis,
                   lr.days_requested AS Tage, lr.notes AS Notiz
            FROM leave_requests lr JOIN employees e ON e.id=lr.employee_id
            WHERE lr.status='beantragt'
            ORDER BY lr.start_date
        """)
        if pending.empty:
            st.success("✅ Keine offenen Urlaubsanträge.")
        else:
            st.info(f"{len(pending)} offene Antrag/Anträge")
            for _, row in pending.iterrows():
                rid = int(row["id"])
                with st.expander(f"🏖️ {row['Mitarbeiter']} – {row['Art']} {row['Von']}→{row['Bis']} ({row['Tage']}d)"):
                    if row.get("Notiz"):
                        st.caption(f"Notiz: {row['Notiz']}")
                    col1, col2, col3 = st.columns(3)
                    if col1.button("✅ Genehmigen", key=f"appr_{rid}", type="primary"):
                        run_fn("UPDATE leave_requests SET status='genehmigt', approved_by=? WHERE id=?",
                               (user.get("username","admin"), rid))
                        # Urlaubskonto aktualisieren
                        eid = int(df_fn("SELECT employee_id FROM leave_requests WHERE id=?", (rid,)).iloc[0]["employee_id"])
                        year = int(str(row["Von"])[:4])
                        bal = df_fn("SELECT id, taken FROM leave_balances WHERE employee_id=? AND year=?", (eid, year))
                        if bal.empty:
                            run_fn("INSERT INTO leave_balances(employee_id,year,entitlement,taken) VALUES(?,?,24,?)",
                                   (eid, year, float(row["Tage"])))
                        else:
                            run_fn("UPDATE leave_balances SET taken=taken+? WHERE id=?",
                                   (float(row["Tage"]), int(bal.iloc[0]["id"])))
                        log_fn("leave_approved", f"id={rid}")
                        st.success("Genehmigt!"); st.rerun()
                    if col2.button("❌ Ablehnen", key=f"rej_{rid}"):
                        run_fn("UPDATE leave_requests SET status='abgelehnt', approved_by=? WHERE id=?",
                               (user.get("username","admin"), rid))
                        st.rerun()
                    if col3.button("💬 Kommentieren", key=f"com_{rid}"):
                        st.info("Kommentarfeld in Notizen eintragen und nochmal einreichen.")

    # ── Tab 3: Urlaubskonto ───────────────────────────────────
    with tabs[3]:
        year_k = st.selectbox("Jahr", list(range(date.today().year, date.today().year - 3, -1)), key="leave_year_k")
        employees = df_fn("SELECT id, name FROM employees WHERE active=1 ORDER BY name")
        if employees.empty:
            st.info("Keine Mitarbeiter.")
            return

        balances = []
        for _, emp in employees.iterrows():
            eid = int(emp["id"])
            bal = df_fn("SELECT * FROM leave_balances WHERE employee_id=? AND year=?", (eid, year_k))
            taken = df_fn("""
                SELECT COALESCE(SUM(days_requested),0) AS t
                FROM leave_requests WHERE employee_id=? AND status='genehmigt'
                AND substr(start_date,1,4)=?
            """, (eid, str(year_k))).iloc[0]["t"]
            entitlement = float(bal.iloc[0]["entitlement"]) if not bal.empty else 24.0
            carry = float(bal.iloc[0]["carry_over"]) if not bal.empty else 0.0
            total = entitlement + carry
            remaining = total - float(taken or 0)
            balances.append({
                "Mitarbeiter": emp["name"],
                "Anspruch": entitlement,
                "Übertrag": carry,
                "Gesamt": total,
                "Genommen": float(taken or 0),
                "Rest": remaining,
                "⚠️": "❗" if remaining < 0 else "✅",
            })

        if balances:
            df_bal = pd.DataFrame(balances)
            st.dataframe(df_bal, use_container_width=True)

            # Anspruch anpassen
            st.divider()
            sel_emp = st.selectbox("Urlaubsanspruch anpassen für", employees["name"].tolist())
            eid_sel = int(employees[employees["name"] == sel_emp].iloc[0]["id"])
            col1, col2, col3 = st.columns(3)
            new_ent   = col1.number_input("Jahresanspruch (Tage)", min_value=0.0, value=24.0, step=0.5)
            new_carry = col2.number_input("Übertrag Vorjahr", min_value=0.0, value=0.0, step=0.5)
            if col3.button("💾 Speichern"):
                existing = df_fn("SELECT id FROM leave_balances WHERE employee_id=? AND year=?", (eid_sel, year_k))
                if existing.empty:
                    run_fn("INSERT INTO leave_balances(employee_id,year,entitlement,carry_over,taken) VALUES(?,?,?,?,0)",
                           (eid_sel, year_k, new_ent, new_carry))
                else:
                    run_fn("UPDATE leave_balances SET entitlement=?, carry_over=? WHERE id=?",
                           (new_ent, new_carry, int(existing.iloc[0]["id"])))
                st.success("Urlaubskonto aktualisiert.")
                st.rerun()

    # ── Tab 4: Jahresübersicht ────────────────────────────────
    with tabs[4]:
        st.subheader("Urlaubskalender Jahresübersicht")
        year_j = st.selectbox("Jahr", list(range(date.today().year, date.today().year - 2, -1)), key="leave_year_j")
        all_leave = df_fn("""
            SELECT e.name AS Mitarbeiter, lr.leave_type AS Art,
                   lr.start_date AS Von, lr.end_date AS Bis,
                   lr.days_requested AS Tage, lr.status AS Status
            FROM leave_requests lr JOIN employees e ON e.id=lr.employee_id
            WHERE substr(lr.start_date,1,4)=? AND lr.status IN ('beantragt','genehmigt')
            ORDER BY lr.start_date
        """, (str(year_j),))

        if not all_leave.empty:
            st.dataframe(all_leave, use_container_width=True)

            # Einfache Heatmap: Monate × Mitarbeiter
            st.subheader("Urlaubstage je Mitarbeiter und Monat")
            pivot_data = []
            months = ['Jan','Feb','Mär','Apr','Mai','Jun','Jul','Aug','Sep','Okt','Nov','Dez']
            for _, row in all_leave.iterrows():
                try:
                    start = date.fromisoformat(str(row["Von"])[:10])
                    m = start.month
                    pivot_data.append({"Mitarbeiter": row["Mitarbeiter"],
                                       "Monat": months[m-1],
                                       "Tage": float(row["Tage"])})
                except Exception:
                    pass
            if pivot_data:
                pvt = pd.DataFrame(pivot_data)
                pivot = pvt.groupby(["Mitarbeiter","Monat"])["Tage"].sum().unstack(fill_value=0)
                # Spalten nach Monatsreihenfolge sortieren
                ordered_cols = [m for m in months if m in pivot.columns]
                pivot = pivot[ordered_cols]
                st.dataframe(pivot, use_container_width=True)
        else:
            st.info("Keine Urlaubsanträge für dieses Jahr.")


# ─────────────────────────────────────────────────────────────
# 2. Fahrtenbuch
# ─────────────────────────────────────────────────────────────

KM_RATE_EMPLOYEE = 0.30   # € pro km (Arbeitnehmer privat-Kfz)
KM_RATE_COMPANY  = 0.00   # Dienst-Kfz: keine Pauschale, nur Benzinkosten


def page_mileage_log(run_fn, df_fn, next_number_fn, log_fn) -> None:
    st.title("🚗 Fahrtenbuch")
    st.caption("Erfassung aller Dienstfahrten inkl. Kilometerpauschale-Berechnung.")

    tabs = st.tabs(["📋 Übersicht", "➕ Fahrt erfassen",
                    "📊 Abrechnung", "📤 Export"])

    # ── Tab 0: Übersicht ──────────────────────────────────────
    with tabs[0]:
        col1, col2 = st.columns(2)
        month = col1.text_input("Monat (YYYY-MM)", date.today().strftime("%Y-%m"))
        emp_f = col2.text_input("Mitarbeiter filtern")

        query = """
            SELECT m.id, m.log_date AS Datum, e.name AS Mitarbeiter,
                   m.from_location AS Von, m.to_location AS Nach,
                   m.km_distance AS km, m.purpose AS Zweck,
                   m.vehicle AS Fahrzeug, m.reimbursement_rate AS Rate_EUR_km,
                   m.reimbursement_amount AS Erstattung_EUR, m.status AS Status
            FROM mileage_log m LEFT JOIN employees e ON e.id=m.employee_id
            WHERE substr(m.log_date,1,7)=?
        """
        params = [month]
        if emp_f:
            query += " AND e.name LIKE ?"
            params.append(f"%{emp_f}%")
        query += " ORDER BY m.log_date DESC"

        data = df_fn(query, tuple(params))
        if not data.empty:
            c1, c2, c3 = st.columns(3)
            c1.metric("Fahrten", len(data))
            c2.metric("Km gesamt", f"{float(data['km'].sum()):,.0f} km")
            c3.metric("Erstattung gesamt", fmt_eur(float(data["Erstattung_EUR"].sum())))
            st.dataframe(data.drop(columns=["id"]), use_container_width=True, height=350)
        else:
            st.info("Keine Fahrten in diesem Zeitraum.")

    # ── Tab 1: Fahrt erfassen ─────────────────────────────────
    with tabs[1]:
        employees = df_fn("SELECT id, name FROM employees WHERE active=1 ORDER BY name")
        with st.form("mileage_form", clear_on_submit=True):
            a, b = st.columns(2)
            emp_name = a.selectbox("Mitarbeiter", employees["name"].tolist() if not employees.empty else ["—"])
            log_date = b.date_input("Datum", date.today())
            from_loc = a.text_input("Von *")
            to_loc   = b.text_input("Nach *")
            km = a.number_input("Kilometer (hin)", min_value=0.0, value=0.0, step=0.5)
            return_trip = b.checkbox("Hin- und Rückfahrt", value=True)
            vehicle = a.selectbox("Fahrzeug", ["Privat-Kfz", "Dienst-Kfz", "ÖPNV", "Sonstiges"])
            purpose = st.text_input("Zweck *", "Kundeneinsatz")
            custom_rate = st.number_input("Erstattungssatz (€/km)",
                                          value=KM_RATE_EMPLOYEE if vehicle=="Privat-Kfz" else 0.0,
                                          min_value=0.0, step=0.01)
            submitted = st.form_submit_button("💾 Fahrt speichern", type="primary")

        if submitted and from_loc and to_loc and km > 0:
            total_km = km * 2 if return_trip else km
            eid = None
            if not employees.empty and emp_name in employees["name"].values:
                eid = int(employees[employees["name"] == emp_name].iloc[0]["id"])
            amount = round(total_km * custom_rate, 2)
            run_fn("""INSERT INTO mileage_log(employee_id,log_date,from_location,to_location,
                      km_distance,purpose,vehicle,reimbursement_rate,reimbursement_amount,status)
                      VALUES(?,?,?,?,?,?,?,?,?,?)""",
                   (eid, log_date.isoformat(), from_loc, to_loc,
                    total_km, purpose, vehicle, custom_rate, amount, "offen"))
            log_fn("mileage_added", f"{total_km}km {from_loc}→{to_loc}")
            st.success(f"✅ {total_km:.1f} km erfasst · Erstattung: {fmt_eur(amount)}")
            st.rerun()

    # ── Tab 2: Abrechnung ─────────────────────────────────────
    with tabs[2]:
        st.subheader("Reisekostenabrechnung je Mitarbeiter")
        col1, col2 = st.columns(2)
        month2 = col1.text_input("Monat", date.today().strftime("%Y-%m"), key="mile_month2")
        employees2 = df_fn("SELECT id, name FROM employees WHERE active=1 ORDER BY name")
        if employees2.empty:
            st.info("Keine Mitarbeiter.")
            return
        sel_emp = col2.selectbox("Mitarbeiter", employees2["name"].tolist())
        eid2 = int(employees2[employees2["name"] == sel_emp].iloc[0]["id"])

        detail = df_fn("""
            SELECT log_date AS Datum, from_location AS Von, to_location AS Nach,
                   km_distance AS km, purpose AS Zweck, vehicle AS Fahrzeug,
                   reimbursement_amount AS Erstattung_EUR, status AS Status
            FROM mileage_log WHERE employee_id=? AND substr(log_date,1,7)=?
            ORDER BY log_date
        """, (eid2, month2))

        if not detail.empty:
            total_km = float(detail["km"].sum())
            total_eur = float(detail["Erstattung_EUR"].sum())
            c1, c2 = st.columns(2)
            c1.metric("Fahrten", len(detail))
            c2.metric(f"Kilometer · Erstattung", f"{total_km:.0f} km · {fmt_eur(total_eur)}")
            st.dataframe(detail, use_container_width=True)

            if st.button("✅ Als abgerechnet markieren"):
                ids = df_fn("SELECT id FROM mileage_log WHERE employee_id=? AND substr(log_date,1,7)=?",
                            (eid2, month2))
                for _, r in ids.iterrows():
                    run_fn("UPDATE mileage_log SET status='abgerechnet' WHERE id=?", (int(r["id"]),))
                log_fn("mileage_settled", f"{sel_emp} {month2}")
                st.success("Als abgerechnet markiert.")
                st.rerun()
        else:
            st.info("Keine Fahrten in diesem Zeitraum.")

    # ── Tab 3: Export ─────────────────────────────────────────
    with tabs[3]:
        st.subheader("Fahrtenbuch-Export")
        col1, col2 = st.columns(2)
        from_m = col1.text_input("Von Monat", date.today().strftime("%Y-01"))
        to_m   = col2.text_input("Bis Monat", date.today().strftime("%Y-%m"))
        all_data = df_fn("""
            SELECT m.log_date AS Datum, e.name AS Mitarbeiter,
                   m.from_location AS Von, m.to_location AS Nach,
                   m.km_distance AS km, m.purpose AS Zweck,
                   m.vehicle AS Fahrzeug, m.reimbursement_rate AS Rate_EUR,
                   m.reimbursement_amount AS Erstattung_EUR, m.status AS Status
            FROM mileage_log m LEFT JOIN employees e ON e.id=m.employee_id
            WHERE substr(m.log_date,1,7) BETWEEN ? AND ?
            ORDER BY m.log_date, e.name
        """, (from_m, to_m))
        if not all_data.empty:
            csv = all_data.to_csv(index=False, sep=";").encode("utf-8-sig")
            st.download_button("📥 Fahrtenbuch CSV", csv, f"fahrtenbuch_{from_m}_{to_m}.csv", "text/csv")
            st.metric(f"Fahrten gesamt ({from_m}–{to_m})", len(all_data))
            st.metric("Erstattung gesamt", fmt_eur(float(all_data["Erstattung_EUR"].sum())))


# ─────────────────────────────────────────────────────────────
# 3. SLA-Monitoring
# ─────────────────────────────────────────────────────────────

def page_sla_monitoring(run_fn, df_fn, next_number_fn, log_fn) -> None:
    st.title("📊 SLA-Monitoring")
    st.caption("Vertragserfüllung je Objekt: Geleistete vs. vereinbarte Stunden/Schichten.")

    tabs = st.tabs(["📋 SLA-Übersicht", "➕ SLA-Vertrag anlegen", "📈 Erfüllungsanalyse"])

    # ── Tab 0: Übersicht ──────────────────────────────────────
    with tabs[0]:
        contracts = df_fn("""
            SELECT s.id, s.contract_name AS Vertrag, c.company AS Kunde,
                   s.location AS Objekt, s.target_hours_weekly AS Soll_Std_Woche,
                   s.target_shifts_weekly AS Soll_Schichten_Woche,
                   s.start_date AS Start, s.end_date AS Ende,
                   s.status AS Status
            FROM sla_contracts s JOIN customers c ON c.id=s.customer_id
            ORDER BY s.status DESC, c.company
        """)
        if not contracts.empty:
            active = contracts[contracts["Status"] == "aktiv"]
            st.metric("Aktive SLA-Verträge", len(active))
            st.dataframe(contracts.drop(columns=["id"]), use_container_width=True)
        else:
            st.info("Noch keine SLA-Verträge eingerichtet.")

    # ── Tab 1: Anlegen ────────────────────────────────────────
    with tabs[1]:
        customers = df_fn("SELECT id, customer_no || ' – ' || company AS label FROM customers ORDER BY company")
        if customers.empty:
            st.warning("Zuerst Kunden anlegen.")
            return

        with st.form("sla_form", clear_on_submit=True):
            cust_label = st.selectbox("Kunde *", customers["label"].tolist())
            a, b = st.columns(2)
            contract_name = a.text_input("Vertragsname *", "Objektschutz Monat")
            location = b.text_input("Objekt / Einsatzort")
            target_h = a.number_input("Soll-Stunden/Woche", min_value=0.0, value=40.0, step=4.0)
            target_s = b.number_input("Soll-Schichten/Woche", min_value=0, value=5, step=1)
            start_d = a.date_input("Vertragsbeginn", date.today())
            end_d   = b.date_input("Vertragsende", date.today() + timedelta(days=365))
            hourly_rate = a.number_input("Stundensatz (€)", min_value=0.0, value=21.0, step=0.5)
            notes = st.text_area("Notizen")
            submitted = st.form_submit_button("💾 SLA-Vertrag anlegen", type="primary")

        if submitted and contract_name:
            cid = int(customers[customers["label"] == cust_label].iloc[0]["id"])
            run_fn("""INSERT INTO sla_contracts(customer_id,contract_name,location,
                      target_hours_weekly,target_shifts_weekly,start_date,end_date,
                      hourly_rate,status,notes)
                      VALUES(?,?,?,?,?,?,?,'aktiv',?,?)""",
                   (cid, contract_name, location, target_h, target_s,
                    start_d.isoformat(), end_d.isoformat(), hourly_rate, notes))
            log_fn("sla_created", contract_name)
            st.success(f"✅ SLA-Vertrag '{contract_name}' angelegt!")
            st.rerun()

    # ── Tab 2: Erfüllungsanalyse ──────────────────────────────
    with tabs[2]:
        st.subheader("SLA-Erfüllungsanalyse")
        contracts2 = df_fn("""
            SELECT s.id, s.contract_name || ' – ' || c.company AS label,
                   s.customer_id, s.location, s.target_hours_weekly,
                   s.target_shifts_weekly, s.start_date, s.end_date
            FROM sla_contracts s JOIN customers c ON c.id=s.customer_id
            WHERE s.status='aktiv'
        """)
        if contracts2.empty:
            st.info("Keine aktiven SLA-Verträge.")
            return

        sel = st.selectbox("SLA-Vertrag", contracts2["label"].tolist())
        row = contracts2[contracts2["label"] == sel].iloc[0]

        col1, col2 = st.columns(2)
        month_from = col1.text_input("Von Monat", (date.today() - timedelta(days=30)).strftime("%Y-%m"))
        month_to   = col2.text_input("Bis Monat", date.today().strftime("%Y-%m"))

        # Geleistete Schichten für diesen Kunden in diesem Zeitraum
        actual = df_fn("""
            SELECT substr(shift_date,1,7) AS Monat,
                   COUNT(*) AS Schichten_IST
            FROM shifts WHERE customer_id=?
              AND substr(shift_date,1,7) BETWEEN ? AND ?
              AND status IN ('abgeschlossen','bestätigt','geplant')
            GROUP BY substr(shift_date,1,7)
            ORDER BY Monat
        """, (int(row["customer_id"]), month_from, month_to))

        # Soll-Schichten pro Monat (ca. 4 Wochen)
        target_monthly = float(row["target_shifts_weekly"]) * 4

        if not actual.empty:
            actual["Soll_Schichten"] = target_monthly
            actual["Erfüllung_Pct"]  = (actual["Schichten_IST"] / target_monthly * 100).round(1)
            actual["Status"] = actual["Erfüllung_Pct"].apply(
                lambda v: "✅ OK" if v >= 95 else "⚠️ Achtung" if v >= 80 else "❌ Unterschreitung"
            )
            c1, c2, c3 = st.columns(3)
            avg_fulfill = float(actual["Erfüllung_Pct"].mean())
            c1.metric("Ø Erfüllung", f"{avg_fulfill:.1f}%")
            c2.metric("Soll/Monat", f"{target_monthly:.0f} Schichten")
            c3.metric("IST Ø/Monat", f"{float(actual['Schichten_IST'].mean()):.0f} Schichten")
            st.dataframe(actual, use_container_width=True)
            st.bar_chart(actual.set_index("Monat")[["Schichten_IST","Soll_Schichten"]])

            # Warnung wenn Erfüllung unter 90%
            below = actual[actual["Erfüllung_Pct"] < 90]
            if not below.empty:
                st.error(f"⚠️ SLA-Unterschreitung in {len(below)} Monat/Monaten unter 90%!")
        else:
            st.info("Keine Schichtdaten für diesen Vertrag und Zeitraum.")


# ─────────────────────────────────────────────────────────────
# 4. Kundenprojekt-Tracking
# ─────────────────────────────────────────────────────────────

def page_project_tracking(run_fn, df_fn, next_number_fn, log_fn) -> None:
    st.title("📁 Kundenprojekte")
    st.caption("Projekte mit Budget, Zeiterfassung und Abrechnung.")

    tabs = st.tabs([
        "📋 Projekte", "➕ Neues Projekt",
        "⏱️ Zeit buchen", "💰 Budget & Abrechnung"
    ])

    # ── Tab 0: Übersicht ──────────────────────────────────────
    with tabs[0]:
        projects = df_fn("""
            SELECT p.id, p.project_no AS Nr, p.project_name AS Projekt,
                   COALESCE(c.company,'–') AS Kunde,
                   p.start_date AS Start, p.end_date AS Ende,
                   p.budget_eur AS Budget_EUR,
                   p.billed_eur AS Abgerechnet_EUR,
                   ROUND(p.budget_eur - p.billed_eur, 2) AS Rest_Budget,
                   p.status AS Status
            FROM projects p LEFT JOIN customers c ON c.id=p.customer_id
            ORDER BY p.status, p.start_date DESC
        """)
        if not projects.empty:
            active = projects[projects["Status"] == "aktiv"]
            c1, c2, c3 = st.columns(3)
            c1.metric("Aktive Projekte", len(active))
            c2.metric("Budget gesamt", fmt_eur(float(active["Budget_EUR"].sum())))
            c3.metric("Rest-Budget", fmt_eur(float(active["Rest_Budget"].sum())))
            st.dataframe(projects.drop(columns=["id"]), use_container_width=True)
        else:
            st.info("Noch keine Projekte angelegt.")

    # ── Tab 1: Neu ────────────────────────────────────────────
    with tabs[1]:
        customers = df_fn("SELECT id, customer_no || ' – ' || company AS label FROM customers ORDER BY company")
        with st.form("project_form", clear_on_submit=True):
            a, b = st.columns(2)
            p_no   = a.text_input("Projektnummer", next_number_fn("projects", "project_no", "PRJ-"))
            p_name = b.text_input("Projektname *")
            cust_label = st.selectbox("Kunde", ["—"] + (customers["label"].tolist() if not customers.empty else []))
            desc  = st.text_area("Beschreibung")
            a2, b2, c2, d2 = st.columns(4)
            start = a2.date_input("Start", date.today())
            end   = b2.date_input("Ende", date.today() + timedelta(days=90))
            budget = c2.number_input("Budget (€)", min_value=0.0, value=0.0, step=100.0)
            status = d2.selectbox("Status", ["aktiv","pausiert","abgeschlossen","storniert"])
            notes = st.text_area("Notizen")
            submitted = st.form_submit_button("💾 Projekt anlegen", type="primary")

        if submitted and p_name:
            cid = None
            if cust_label != "—" and not customers.empty:
                match = customers[customers["label"] == cust_label]
                if not match.empty:
                    cid = int(match.iloc[0]["id"])
            run_fn("""INSERT INTO projects(project_no,customer_id,project_name,description,
                      start_date,end_date,budget_eur,status,notes)
                      VALUES(?,?,?,?,?,?,?,?,?)""",
                   (p_no, cid, p_name, desc, start.isoformat(), end.isoformat(), budget, status, notes))
            log_fn("project_created", p_name)
            st.success(f"✅ Projekt '{p_name}' angelegt!")
            st.rerun()

    # ── Tab 2: Zeit buchen ────────────────────────────────────
    with tabs[2]:
        projects2 = df_fn("SELECT id, project_no || ' – ' || project_name AS label FROM projects WHERE status='aktiv' ORDER BY project_name")
        employees = df_fn("SELECT id, name FROM employees WHERE active=1 ORDER BY name")
        if projects2.empty:
            st.info("Keine aktiven Projekte.")
            return

        with st.form("proj_time_form", clear_on_submit=True):
            a, b = st.columns(2)
            proj_label = a.selectbox("Projekt *", projects2["label"].tolist())
            emp_name   = b.selectbox("Mitarbeiter", ["—"] + (employees["name"].tolist() if not employees.empty else []))
            log_date   = a.date_input("Datum", date.today())
            hours      = b.number_input("Stunden *", min_value=0.25, value=1.0, step=0.25)
            desc       = st.text_input("Beschreibung / Tätigkeit")
            billable   = st.checkbox("Fakturierbar", value=True)
            submitted  = st.form_submit_button("⏱️ Zeit buchen", type="primary")

        if submitted and hours > 0:
            pid = int(projects2[projects2["label"] == proj_label].iloc[0]["id"])
            eid = None
            if emp_name != "—" and not employees.empty:
                match = employees[employees["name"] == emp_name]
                if not match.empty:
                    eid = int(match.iloc[0]["id"])
            run_fn("INSERT INTO project_time(project_id,employee_id,log_date,hours,description,billable) VALUES(?,?,?,?,?,?)",
                   (pid, eid, log_date.isoformat(), hours, desc, 1 if billable else 0))
            log_fn("project_time", f"{proj_label}: {hours}h {desc}")
            st.success(f"✅ {hours}h auf '{proj_label}' gebucht.")
            st.rerun()

        # Letzte Buchungen
        last_time = df_fn("""
            SELECT p.project_name AS Projekt, e.name AS Mitarbeiter,
                   pt.log_date AS Datum, pt.hours AS Stunden,
                   pt.description AS Tätigkeit,
                   CASE WHEN pt.billable=1 THEN '✅' ELSE '–' END AS Fakturierbar
            FROM project_time pt
            JOIN projects p ON p.id=pt.project_id
            LEFT JOIN employees e ON e.id=pt.employee_id
            ORDER BY pt.log_date DESC LIMIT 20
        """)
        if not last_time.empty:
            st.subheader("Letzte Buchungen")
            st.dataframe(last_time, use_container_width=True)

    # ── Tab 3: Budget & Abrechnung ────────────────────────────
    with tabs[3]:
        st.subheader("Projekt-Budget & Abrechnung")
        projects3 = df_fn("SELECT id, project_no || ' – ' || project_name AS label, budget_eur, billed_eur FROM projects ORDER BY project_name")
        if projects3.empty:
            st.info("Keine Projekte.")
            return

        sel = st.selectbox("Projekt", projects3["label"].tolist())
        pid = int(projects3[projects3["label"] == sel].iloc[0]["id"])
        budget = float(projects3[projects3["label"] == sel].iloc[0]["budget_eur"])
        billed = float(projects3[projects3["label"] == sel].iloc[0]["billed_eur"])

        # Zeiterfassung für dieses Projekt
        time_data = df_fn("""
            SELECT e.name AS Mitarbeiter,
                   SUM(pt.hours) AS Stunden_gesamt,
                   SUM(CASE WHEN pt.billable=1 THEN pt.hours ELSE 0 END) AS Fakturierbar
            FROM project_time pt LEFT JOIN employees e ON e.id=pt.employee_id
            WHERE pt.project_id=? GROUP BY pt.employee_id
        """, (pid,))

        total_h = float(time_data["Stunden_gesamt"].sum()) if not time_data.empty else 0
        bill_h  = float(time_data["Fakturierbar"].sum()) if not time_data.empty else 0

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Budget", fmt_eur(budget))
        c2.metric("Abgerechnet", fmt_eur(billed))
        c3.metric("Rest-Budget", fmt_eur(budget - billed))
        c4.metric("Geleistete Std.", f"{total_h:.1f} h")

        if not time_data.empty:
            st.dataframe(time_data, use_container_width=True)

        # Betrag abrechnen
        st.divider()
        with st.form("proj_bill_form"):
            bill_amount = st.number_input("Abgerechneter Betrag (€)", min_value=0.0, value=0.0, step=100.0)
            if st.form_submit_button("💰 Abrechnung buchen", type="primary") and bill_amount > 0:
                run_fn("UPDATE projects SET billed_eur=COALESCE(billed_eur,0)+? WHERE id=?",
                       (bill_amount, pid))
                log_fn("project_billed", f"pid={pid} amount={bill_amount}")
                st.success(f"✅ {fmt_eur(bill_amount)} abgerechnet.")
                st.rerun()
