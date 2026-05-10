"""
extensions_v2_payroll_recon_ops.py – Abrechnung & Buchführung für Byblos CRM v2
================================================================================
1.  Buchungsjournal (alle Buchungen chronologisch)
2.  Kassenbuch (Bareinnahmen/-ausgaben)
3.  Reisekostenabrechnung (km-Satz, Verpflegung)
4.  Personalplanung Soll/Ist (Monat)
5.  Kostenstellenrechnung
6.  Debitorenkontenblatt je Kunde
7.  UStVA XML (Umsatzsteuer-Voranmeldung Vorbereitung)
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pandas as pd
import streamlit as st


def fmt_eur(v: float) -> str:
    return f"{v:,.2f} €".replace(",","X").replace(".",",").replace("X",".")


# ─────────────────────────────────────────────────────────────
# DB-Registrierung
# ─────────────────────────────────────────────────────────────

def register_payroll_recon(run_fn, df_fn) -> None:
    run_fn("""CREATE TABLE IF NOT EXISTS cash_book (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        entry_date TEXT NOT NULL,
        description TEXT NOT NULL,
        amount REAL NOT NULL,
        direction TEXT NOT NULL,
        category TEXT DEFAULT 'Sonstiges',
        receipt_no TEXT,
        balance REAL DEFAULT 0,
        notes TEXT,
        created_by TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )""")
    run_fn("""CREATE TABLE IF NOT EXISTS travel_expenses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        employee_id INTEGER,
        travel_date TEXT NOT NULL,
        destination TEXT NOT NULL,
        purpose TEXT NOT NULL,
        km_driven REAL DEFAULT 0,
        km_rate REAL DEFAULT 0.30,
        meals_breakfast REAL DEFAULT 0,
        meals_lunch REAL DEFAULT 0,
        meals_dinner REAL DEFAULT 0,
        hotel REAL DEFAULT 0,
        other_costs REAL DEFAULT 0,
        total_reimbursement REAL DEFAULT 0,
        status TEXT DEFAULT 'offen',
        approved_by TEXT,
        notes TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(employee_id) REFERENCES employees(id)
    )""")
    run_fn("""CREATE TABLE IF NOT EXISTS cost_centers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        cost_center_no TEXT UNIQUE NOT NULL,
        name TEXT NOT NULL,
        description TEXT,
        manager TEXT,
        active INTEGER DEFAULT 1,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )""")
    run_fn("ALTER TABLE invoices ADD COLUMN cost_center_id INTEGER" if 'cost_center_id' not in
           [r['name'] for r in df_fn("PRAGMA table_info(invoices)").to_dict('records')]
           else "SELECT 1")
    run_fn("ALTER TABLE expenses ADD COLUMN cost_center_id INTEGER" if 'cost_center_id' not in
           [r['name'] for r in df_fn("PRAGMA table_info(expenses)").to_dict('records')]
           else "SELECT 1")


# ─────────────────────────────────────────────────────────────
# 1. Buchungsjournal
# ─────────────────────────────────────────────────────────────

def page_booking_journal(df_fn) -> None:
    st.title("📒 Buchungsjournal")
    st.caption("Chronologische Übersicht aller Buchungen (Rechnungen + Ausgaben + Zahlungen).")

    col1, col2, col3 = st.columns(3)
    from_d = col1.date_input("Von", date.today().replace(day=1))
    to_d   = col2.date_input("Bis", date.today())
    filter_type = col3.selectbox("Typ", ["alle","Einnahmen","Ausgaben","Zahlungen"])

    entries = []

    # Rechnungen (Forderungen)
    invs = df_fn(f"""
        SELECT i.invoice_date AS datum, 'Rechnung erstellt' AS typ,
               i.invoice_no AS belegnr, c.company AS partner,
               i.gross_total AS soll, 0 AS haben,
               i.status AS status
        FROM invoices i JOIN customers c ON c.id=i.customer_id
        WHERE i.invoice_date BETWEEN '{from_d.isoformat()}' AND '{to_d.isoformat()}'
        ORDER BY i.invoice_date
    """)
    for _, r in invs.iterrows():
        entries.append({"Datum":r["datum"],"Typ":"🧾 "+r["typ"],"Beleg":r["belegnr"],
                        "Partner":r["partner"],"Soll":float(r["soll"]),"Haben":0.0,"Status":r["status"]})

    # Zahlungseingänge
    payments = df_fn(f"""
        SELECT p.payment_date AS datum, 'Zahlungseingang' AS typ,
               i.invoice_no AS belegnr, c.company AS partner,
               0 AS soll, p.amount AS haben, 'bezahlt' AS status
        FROM payments p
        JOIN invoices i ON i.id=p.invoice_id
        JOIN customers c ON c.id=i.customer_id
        WHERE p.payment_date BETWEEN '{from_d.isoformat()}' AND '{to_d.isoformat()}'
    """)
    for _, r in payments.iterrows():
        entries.append({"Datum":r["datum"],"Typ":"💰 Zahlung","Beleg":r["belegnr"],
                        "Partner":r["partner"],"Soll":0.0,"Haben":float(r["haben"]),"Status":"bezahlt"})

    # Ausgaben
    exps = df_fn(f"""
        SELECT e.expense_date AS datum, 'Ausgabe' AS typ,
               e.expense_no AS belegnr, COALESCE(s.name,'Sonstiges') AS partner,
               e.gross_amount AS soll, 0 AS haben, e.status AS status
        FROM expenses e LEFT JOIN suppliers s ON s.id=e.supplier_id
        WHERE e.expense_date BETWEEN '{from_d.isoformat()}' AND '{to_d.isoformat()}'
    """)
    for _, r in exps.iterrows():
        entries.append({"Datum":r["datum"],"Typ":"📤 "+r["typ"],"Beleg":r["belegnr"],
                        "Partner":str(r["partner"])[:30],"Soll":0.0,"Haben":float(r["soll"]),"Status":r["status"]})

    if not entries:
        st.info("Keine Buchungen im Zeitraum.")
        return

    df_j = pd.DataFrame(entries).sort_values("Datum")

    # Filter
    if filter_type == "Einnahmen":
        df_j = df_j[df_j["Typ"].str.contains("Rechnung")]
    elif filter_type == "Ausgaben":
        df_j = df_j[df_j["Typ"].str.contains("Ausgabe")]
    elif filter_type == "Zahlungen":
        df_j = df_j[df_j["Typ"].str.contains("Zahlung")]

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Buchungen gesamt", len(df_j))
    c2.metric("Einnahmen (Soll)", fmt_eur(float(df_j["Soll"].sum())))
    c3.metric("Ausgaben (Haben)", fmt_eur(float(df_j["Haben"].sum())))
    c4.metric("Saldo", fmt_eur(float(df_j["Soll"].sum()) - float(df_j["Haben"].sum())))

    st.dataframe(df_j, use_container_width=True, height=450)
    csv = df_j.to_csv(index=False, sep=";").encode("utf-8-sig")
    st.download_button("📥 Journal als CSV",
                       csv, f"buchungsjournal_{from_d}_{to_d}.csv", "text/csv")


# ─────────────────────────────────────────────────────────────
# 2. Kassenbuch
# ─────────────────────────────────────────────────────────────

def page_cash_book(run_fn, df_fn, log_fn, current_user_fn) -> None:
    st.title("💵 Kassenbuch")
    st.caption("Bareinnahmen und -ausgaben erfassen (Nebenkasse).")

    user = current_user_fn() or {}

    tabs = st.tabs(["📋 Kassenbuch", "➕ Eintrag", "📊 Monatsabschluss"])

    with tabs[0]:
        month = st.text_input("Monat", date.today().strftime("%Y-%m"), key="cb_month")
        entries = df_fn(f"""
            SELECT entry_date AS Datum, description AS Beschreibung,
                   CASE WHEN direction='ein' THEN amount ELSE 0 END AS Einnahme,
                   CASE WHEN direction='aus' THEN amount ELSE 0 END AS Ausgabe,
                   balance AS Kassenstand, receipt_no AS Beleg, category AS Kategorie
            FROM cash_book
            WHERE substr(entry_date,1,7)='{month}'
            ORDER BY entry_date, id
        """)

        # Anfangsbestand
        opening = df_fn(f"""
            SELECT COALESCE(balance,0) AS bal FROM cash_book
            WHERE entry_date < '{month}-01'
            ORDER BY entry_date DESC, id DESC LIMIT 1
        """)
        opening_balance = float(opening.iloc[0]["bal"]) if not opening.empty else 0.0

        if not entries.empty:
            total_in  = float(entries["Einnahme"].sum())
            total_out = float(entries["Ausgabe"].sum())
            closing   = opening_balance + total_in - total_out

            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Anfangsbestand", fmt_eur(opening_balance))
            c2.metric("+ Einnahmen", fmt_eur(total_in))
            c3.metric("– Ausgaben", fmt_eur(total_out))
            c4.metric("= Kassenbestand", fmt_eur(closing))

            st.dataframe(entries, use_container_width=True, height=350)
            csv = entries.to_csv(index=False, sep=";").encode("utf-8-sig")
            st.download_button("📥 Kassenbuch CSV", csv,
                               f"kassenbuch_{month}.csv", "text/csv")
        else:
            st.info(f"Keine Einträge für {month}.")

    with tabs[1]:
        # Letzten Kassenstand ermitteln
        last = df_fn("SELECT COALESCE(MAX(balance),0) AS bal FROM cash_book")
        current_balance = float(last.iloc[0]["bal"]) if not last.empty else 0.0

        CATS = ["Bareinnahme Rechnung","Porto","Büromaterial","Reinigung","Verpflegung",
                "Fahrtkosten","Kleinreparatur","Sonstiges"]

        with st.form("cash_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            entry_date   = col1.date_input("Datum", date.today())
            direction    = col2.selectbox("Art", ["ein (Einnahme)","aus (Ausgabe)"])
            description  = st.text_input("Beschreibung *")
            col3, col4   = st.columns(2)
            amount       = col3.number_input("Betrag (€)", min_value=0.01, value=10.0, step=0.50)
            category     = col4.selectbox("Kategorie", CATS)
            receipt_no   = col1.text_input("Belegnummer")
            notes        = st.text_area("Notizen")
            submitted    = st.form_submit_button("💾 Buchen", type="primary")

        if submitted and description:
            dir_code = "ein" if direction.startswith("ein") else "aus"
            new_bal  = current_balance + amount if dir_code == "ein" else current_balance - amount
            run_fn("""INSERT INTO cash_book(entry_date,description,amount,direction,
                      category,receipt_no,balance,notes,created_by)
                      VALUES(?,?,?,?,?,?,?,?,?)""",
                   (entry_date.isoformat(), description, amount, dir_code,
                    category, receipt_no, new_bal, notes,
                    user.get("username","system")))
            log_fn("cash_booked", f"{dir_code} {amount}€ – {description}")
            st.success(f"✅ Gebucht. Kassenstand: {fmt_eur(new_bal)}")
            st.rerun()

    with tabs[2]:
        year_m = st.selectbox("Jahr", list(range(date.today().year, date.today().year-3,-1)), key="cb_year")
        monthly = df_fn(f"""
            SELECT substr(entry_date,1,7) AS Monat,
                   SUM(CASE WHEN direction='ein' THEN amount ELSE 0 END) AS Einnahmen,
                   SUM(CASE WHEN direction='aus' THEN amount ELSE 0 END) AS Ausgaben,
                   COUNT(*) AS Buchungen
            FROM cash_book WHERE substr(entry_date,1,4)='{year_m}'
            GROUP BY substr(entry_date,1,7) ORDER BY Monat
        """)
        if not monthly.empty:
            monthly["Saldo"] = monthly["Einnahmen"] - monthly["Ausgaben"]
            st.dataframe(monthly, use_container_width=True)
            st.bar_chart(monthly.set_index("Monat")[["Einnahmen","Ausgaben"]])


# ─────────────────────────────────────────────────────────────
# 3. Reisekostenabrechnung
# ─────────────────────────────────────────────────────────────

# Aktuelle Pauschalen (2024 – jährlich prüfen!)
MEAL_ALLOWANCES = {
    "8+ Stunden Abwesenheit": 14.0,
    "24 Stunden Abwesenheit": 28.0,
    "Ausland (Richtsatz DE)": 28.0,
}
KM_RATE_DEFAULT = 0.30  # §9 EStG


def page_travel_expenses(run_fn, df_fn, next_number_fn, log_fn, current_user_fn) -> None:
    st.title("🚗 Reisekostenabrechnung")
    st.caption("Km-Geld, Verpflegungspauschalen und sonstige Reisekosten.")

    user = current_user_fn() or {}
    is_mgr = user.get("role","").lower() in ("admin","manager","administrator")

    tabs = st.tabs(["➕ Neue Abrechnung", "📋 Meine Abrechnungen",
                    "✅ Genehmigen (Manager)", "📊 Auswertung", "ℹ️ Pauschalen"])

    with tabs[0]:
        employees = df_fn("SELECT id, employee_no || ' – ' || name AS label FROM employees WHERE active=1 ORDER BY name")
        if employees.empty:
            st.info("Keine Mitarbeiter.")
            return

        with st.form("travel_form", clear_on_submit=True):
            emp_label = st.selectbox("Mitarbeiter *", employees["label"].tolist())
            col1, col2 = st.columns(2)
            travel_date = col1.date_input("Reisedatum", date.today())
            destination = col2.text_input("Reiseziel *")
            purpose     = st.text_input("Zweck / Anlass *")

            st.subheader("Fahrtkosten")
            col3, col4 = st.columns(2)
            km       = col3.number_input("Gefahrene km (Hin- und Rückfahrt)", min_value=0.0, value=0.0, step=1.0)
            km_rate  = col4.number_input("km-Satz (€/km)", min_value=0.0, value=KM_RATE_DEFAULT, step=0.01)
            km_total = round(km * km_rate, 2)
            if km > 0:
                st.caption(f"Km-Erstattung: {km:.0f} km × {km_rate:.2f} €/km = **{fmt_eur(km_total)}**")

            st.subheader("Verpflegungspauschalen (netto)")
            col5, col6, col7 = st.columns(3)
            breakfast = col5.number_input("Frühstück (€)", min_value=0.0, value=0.0, step=0.50)
            lunch     = col6.number_input("Mittagessen (€)", min_value=0.0, value=0.0, step=0.50)
            dinner    = col7.number_input("Abendessen (€)", min_value=0.0, value=0.0, step=0.50)

            st.subheader("Sonstige Kosten")
            col8, col9 = st.columns(2)
            hotel  = col8.number_input("Hotel / Übernachtung (€)", min_value=0.0, value=0.0, step=10.0)
            other  = col9.number_input("Sonstige (Parkgebühren, Bahn etc., €)", min_value=0.0, value=0.0, step=1.0)
            notes  = st.text_area("Notizen / Belege")

            total = round(km_total + breakfast + lunch + dinner + hotel + other, 2)
            st.info(f"💰 **Gesamterstattung: {fmt_eur(total)}**")
            submitted = st.form_submit_button("💾 Abrechnung einreichen", type="primary")

        if submitted and destination and purpose:
            eid = int(employees[employees["label"] == emp_label].iloc[0]["id"])
            run_fn("""INSERT INTO travel_expenses(employee_id,travel_date,destination,
                      purpose,km_driven,km_rate,meals_breakfast,meals_lunch,meals_dinner,
                      hotel,other_costs,total_reimbursement,status,notes)
                      VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                   (eid, travel_date.isoformat(), destination, purpose,
                    km, km_rate, breakfast, lunch, dinner, hotel, other, total, "offen", notes))
            log_fn("travel_submitted", f"{emp_label} {destination} {fmt_eur(total)}")
            st.success(f"✅ Reisekostenabrechnung über {fmt_eur(total)} eingereicht!")
            st.rerun()

    with tabs[1]:
        my_trips = df_fn("""
            SELECT te.id, te.travel_date AS Datum, te.destination AS Ziel,
                   te.purpose AS Zweck, te.total_reimbursement AS Gesamt_EUR,
                   te.status AS Status, te.km_driven AS km,
                   te.approved_by AS Genehmigt_von
            FROM travel_expenses te JOIN employees e ON e.id=te.employee_id
            ORDER BY te.travel_date DESC
        """)
        if not my_trips.empty:
            c1, c2 = st.columns(2)
            c1.metric("Abrechnungen gesamt", len(my_trips))
            c2.metric("Offen", len(my_trips[my_trips["Status"]=="offen"]))
            st.dataframe(my_trips.drop(columns=["id"]), use_container_width=True)
        else:
            st.info("Noch keine Reisekostenabrechnungen.")

    with tabs[2]:
        if not is_mgr:
            st.info("Nur Manager können Reisekostenabrechnungen genehmigen.")
            return
        pending = df_fn("""
            SELECT te.id, e.name AS Mitarbeiter, te.travel_date AS Datum,
                   te.destination AS Ziel, te.purpose AS Zweck,
                   te.total_reimbursement AS Betrag, te.notes AS Notizen
            FROM travel_expenses te JOIN employees e ON e.id=te.employee_id
            WHERE te.status='offen' ORDER BY te.travel_date
        """)
        if not pending.empty:
            for _, row in pending.iterrows():
                tid = int(row["id"])
                with st.expander(f"🚗 {row['Mitarbeiter']} – {row['Ziel']} · {fmt_eur(float(row['Betrag']))}"):
                    col1, col2 = st.columns(2)
                    col1.write(f"**Datum:** {row['Datum']}  \n**Zweck:** {row['Zweck']}")
                    if row.get("Notizen"): col2.caption(row["Notizen"])
                    c1, c2 = st.columns(2)
                    if c1.button("✅ Genehmigen", key=f"tappr_{tid}", type="primary"):
                        run_fn("UPDATE travel_expenses SET status='genehmigt', approved_by=? WHERE id=?",
                               (user.get("username","admin"), tid))
                        log_fn("travel_approved", f"id={tid}")
                        st.rerun()
                    if c2.button("❌ Ablehnen", key=f"trej_{tid}"):
                        run_fn("UPDATE travel_expenses SET status='abgelehnt' WHERE id=?", (tid,))
                        st.rerun()
        else:
            st.success("✅ Keine offenen Abrechnungen.")

    with tabs[3]:
        year_t = st.selectbox("Jahr", list(range(date.today().year, date.today().year-3,-1)), key="travel_year")
        stats = df_fn(f"""
            SELECT e.name AS Mitarbeiter,
                   COUNT(*) AS Dienstreisen,
                   ROUND(SUM(te.km_driven),0) AS km_gesamt,
                   ROUND(SUM(te.total_reimbursement),2) AS Erstattung_EUR
            FROM travel_expenses te JOIN employees e ON e.id=te.employee_id
            WHERE substr(te.travel_date,1,4)='{year_t}' AND te.status='genehmigt'
            GROUP BY e.id ORDER BY Erstattung_EUR DESC
        """)
        if not stats.empty:
            c1, c2 = st.columns(2)
            c1.metric("Gesamterstattungen", fmt_eur(float(stats["Erstattung_EUR"].sum())))
            c2.metric("Gesamtkilometer", f"{float(stats['km_gesamt'].sum()):.0f} km")
            st.dataframe(stats, use_container_width=True)
            st.bar_chart(stats.set_index("Mitarbeiter")["Erstattung_EUR"])

    with tabs[4]:
        st.markdown(f"""
**Steuerfreie Erstattungspauschalen (§9 EStG, 2024):**

| Position | Betrag |
|---|---|
| km-Geld (eigenes Kfz) | {KM_RATE_DEFAULT:.2f} €/km |
| Motorrad / Moped | 0,20 €/km |
| Fahrrad | 0,05 €/km |
| Verpflegung bei 8h+ Abwesenheit | 14,00 €/Tag |
| Verpflegung bei 24h Abwesenheit | 28,00 €/Tag |
| An- und Abreisetag | 14,00 €/Tag |

**Hinweis:** Pauschalen ändern sich ggf. jährlich. Bitte mit Steuerberater abstimmen.
Belege für Hotelübernachtungen und sonstige Kosten aufbewahren!
        """)


# ─────────────────────────────────────────────────────────────
# 4. Personalplanung Soll/Ist (Monat)
# ─────────────────────────────────────────────────────────────

def page_staffing_overview(df_fn) -> None:
    st.title("👥 Personalplanung Soll/Ist")
    st.caption("Geplante vs. tatsächliche Arbeitsstunden je Mitarbeiter und Monat.")

    col1, col2 = st.columns(2)
    year  = col1.selectbox("Jahr", list(range(date.today().year, date.today().year-3,-1)))
    month = col2.selectbox("Monat", list(range(1,13)), index=date.today().month-1,
                            format_func=lambda m: ["Jan","Feb","Mär","Apr","Mai","Jun",
                                                    "Jul","Aug","Sep","Okt","Nov","Dez"][m-1])
    month_str = f"{year}-{month:02d}"

    # Soll: aus Verträgen / Wochenstunden
    soll = df_fn("""
        SELECT id, employee_no AS Nr, name AS Mitarbeiter,
               COALESCE(weekly_hours,40) AS Wochenstunden,
               COALESCE(weekly_hours,40) / 5.0 AS Stunden_je_Tag
        FROM employees WHERE active=1 ORDER BY name
    """)

    if soll.empty:
        st.info("Keine aktiven Mitarbeiter.")
        return

    # Arbeitstage im Monat
    import calendar
    workdays = sum(1 for d in range(1, calendar.monthrange(year, month)[1]+1)
                   if date(year, month, d).weekday() < 5)

    # Ist: aus Schichten / Zeiterfassung
    ist = df_fn(f"""
        SELECT employee_id,
               ROUND(SUM(
                   CASE
                     WHEN start_time IS NOT NULL AND end_time IS NOT NULL
                     THEN (strftime('%s', end_time) - strftime('%s', start_time)) / 3600.0
                     ELSE 0
                   END
               ),1) AS ist_stunden
        FROM shifts WHERE substr(shift_date,1,7)='{month_str}' AND status='abgeschlossen'
        GROUP BY employee_id
    """)

    # Zeiterfassung falls vorhanden
    time_entries = df_fn(f"""
        SELECT employee_id, ROUND(SUM(net_hours),1) AS erfasste_stunden
        FROM time_entries WHERE substr(date,1,7)='{month_str}'
        GROUP BY employee_id
    """)

    # Merge
    result = soll.copy()
    result["Soll_Stunden"] = result["Wochenstunden"] / 5.0 * workdays

    # Ist aus Zeiterfassung bevorzugen, sonst Schichten
    ist_dict = {}
    if not time_entries.empty:
        ist_dict.update(dict(zip(time_entries["employee_id"], time_entries["erfasste_stunden"])))
    if not ist.empty:
        for eid, h in zip(ist["employee_id"], ist["ist_stunden"]):
            if eid not in ist_dict:
                ist_dict[int(eid)] = float(h)

    result["Ist_Stunden"]  = result["id"].map(lambda x: ist_dict.get(int(x), 0.0))
    result["Differenz"]    = (result["Ist_Stunden"] - result["Soll_Stunden"]).round(1)
    result["Erfüllung_%"]  = (result["Ist_Stunden"] / result["Soll_Stunden"].replace(0,1) * 100).round(1)

    # KPIs
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Arbeitstage im Monat", workdays)
    c2.metric("Gesamte Soll-Stunden", f"{float(result['Soll_Stunden'].sum()):.0f} h")
    c3.metric("Gesamte Ist-Stunden",  f"{float(result['Ist_Stunden'].sum()):.0f} h")
    c4.metric("Ø Erfüllung",          f"{float(result['Erfüllung_%'].mean()):.0f}%")

    # Farbkodierung
    def color_row(row):
        pct = float(row["Erfüllung_%"])
        if pct < 80:   return "🔴 unter Plan"
        elif pct < 95: return "🟡 leicht unter"
        elif pct <= 105: return "🟢 auf Plan"
        else:            return "🔵 über Plan"

    result["Status"] = result.apply(color_row, axis=1)

    st.dataframe(
        result[["Nr","Mitarbeiter","Wochenstunden","Soll_Stunden","Ist_Stunden","Differenz","Erfüllung_%","Status"]],
        use_container_width=True
    )
    st.bar_chart(result.set_index("Mitarbeiter")[["Soll_Stunden","Ist_Stunden"]])


# ─────────────────────────────────────────────────────────────
# 5. Kostenstellenrechnung
# ─────────────────────────────────────────────────────────────

def page_cost_centers(run_fn, df_fn, next_number_fn, log_fn) -> None:
    st.title("📂 Kostenstellenrechnung")
    st.caption("Kosten und Erlöse auf Abteilungen/Kostenstellen verteilen.")

    tabs = st.tabs(["📊 Auswertung", "➕ Kostenstelle anlegen", "🔗 Zuweisung"])

    with tabs[0]:
        month = st.text_input("Monat", date.today().strftime("%Y-%m"), key="cc_month")

        centers = df_fn("SELECT id, name FROM cost_centers WHERE active=1 ORDER BY name")
        if centers.empty:
            st.info("Keine Kostenstellen angelegt.")
            return

        revenues = df_fn(f"""
            SELECT cc.name AS Kostenstelle,
                   ROUND(SUM(i.gross_total),2) AS Erlöse_EUR
            FROM invoices i
            JOIN cost_centers cc ON cc.id=i.cost_center_id
            WHERE substr(i.invoice_date,1,7)='{month}'
            GROUP BY cc.id
        """)
        costs_data = df_fn(f"""
            SELECT cc.name AS Kostenstelle,
                   ROUND(SUM(e.gross_amount),2) AS Kosten_EUR
            FROM expenses e
            JOIN cost_centers cc ON cc.id=e.cost_center_id
            WHERE e.bwa_month='{month}'
            GROUP BY cc.id
        """)

        if not revenues.empty or not costs_data.empty:
            merged = centers.rename(columns={"name":"Kostenstelle"}).merge(
                revenues, on="Kostenstelle", how="left"
            ).merge(costs_data, on="Kostenstelle", how="left").fillna(0)
            merged["Ergebnis"] = merged["Erlöse_EUR"] - merged["Kosten_EUR"]
            st.dataframe(merged.drop(columns=["id"]), use_container_width=True)
            st.bar_chart(merged.set_index("Kostenstelle")[["Erlöse_EUR","Kosten_EUR"]])
        else:
            st.info(f"Keine Buchungen auf Kostenstellen in {month}.")

    with tabs[1]:
        with st.form("cc_form", clear_on_submit=True):
            cc_no   = st.text_input("Kostenstellen-Nr.", next_number_fn("cost_centers","cost_center_no","KST-"))
            name    = st.text_input("Bezeichnung *")
            manager = st.text_input("Verantwortlicher")
            desc    = st.text_area("Beschreibung")
            if st.form_submit_button("💾 Speichern", type="primary") and name:
                run_fn("INSERT INTO cost_centers(cost_center_no,name,manager,description) VALUES(?,?,?,?)",
                       (cc_no, name, manager, desc))
                log_fn("cost_center_created", name)
                st.success(f"✅ Kostenstelle '{name}' angelegt!"); st.rerun()

    with tabs[2]:
        st.subheader("Rechnungen und Ausgaben Kostenstellen zuweisen")
        centers = df_fn("SELECT id, cost_center_no || ' – ' || name AS label FROM cost_centers WHERE active=1")
        if centers.empty:
            st.info("Bitte zuerst Kostenstellen anlegen.")
            return

        col1, col2 = st.columns(2)
        entity_type = col1.selectbox("Typ", ["Rechnung","Ausgabe"])
        cc_label    = col2.selectbox("Kostenstelle", centers["label"].tolist())
        ccid        = int(centers[centers["label"] == cc_label].iloc[0]["id"])

        if entity_type == "Rechnung":
            items = df_fn("SELECT id, invoice_no || ' – ' || ROUND(gross_total,2) || ' €' AS label FROM invoices WHERE cost_center_id IS NULL ORDER BY invoice_date DESC LIMIT 50")
        else:
            items = df_fn("SELECT id, expense_no || ' – ' || description AS label FROM expenses WHERE cost_center_id IS NULL ORDER BY expense_date DESC LIMIT 50")

        if not items.empty:
            sel = st.multiselect(f"Zu '{cc_label}' zuweisen", items["label"].tolist())
            if sel and st.button("🔗 Zuweisen", type="primary"):
                for s in sel:
                    iid = int(items[items["label"] == s].iloc[0]["id"])
                    table = "invoices" if entity_type == "Rechnung" else "expenses"
                    run_fn(f"UPDATE {table} SET cost_center_id=? WHERE id=?", (ccid, iid))
                st.success(f"✅ {len(sel)} {entity_type}(en) zugewiesen!")
                st.rerun()


# ─────────────────────────────────────────────────────────────
# 6. Debitorenkontenblatt
# ─────────────────────────────────────────────────────────────

def page_debtor_account(df_fn) -> None:
    st.title("📋 Debitorenkontenblatt")
    st.caption("Vollständige Buchungshistorie je Kunde (Forderungen und Zahlungen).")

    customers = df_fn("SELECT id, customer_no || ' – ' || company AS label FROM customers ORDER BY company")
    if customers.empty:
        st.info("Keine Kunden.")
        return

    sel = st.selectbox("Kunde", customers["label"].tolist())
    cid = int(customers[customers["label"] == sel].iloc[0]["id"])

    col1, col2 = st.columns(2)
    from_d = col1.date_input("Von", date(date.today().year, 1, 1))
    to_d   = col2.date_input("Bis", date.today())

    # Kontenblatt-Einträge
    entries = []

    # Rechnungen (Soll-Seite)
    invs = df_fn(f"""
        SELECT invoice_date AS datum, invoice_no AS beleg,
               'Rechnung' AS typ, gross_total AS betrag, status
        FROM invoices
        WHERE customer_id={cid}
          AND invoice_date BETWEEN '{from_d.isoformat()}' AND '{to_d.isoformat()}'
        ORDER BY invoice_date
    """)
    for _, r in invs.iterrows():
        entries.append({"Datum":r["datum"],"Beleg":r["beleg"],"Typ":"Soll",
                        "Betrag":float(r["betrag"]),"Saldo_Änderung":float(r["betrag"]),
                        "Status":r["status"]})

    # Zahlungen (Haben-Seite)
    payments = df_fn(f"""
        SELECT p.payment_date AS datum, i.invoice_no AS beleg,
               'Zahlung' AS typ, p.amount AS betrag
        FROM payments p JOIN invoices i ON i.id=p.invoice_id
        WHERE i.customer_id={cid}
          AND p.payment_date BETWEEN '{from_d.isoformat()}' AND '{to_d.isoformat()}'
        ORDER BY p.payment_date
    """)
    for _, r in payments.iterrows():
        entries.append({"Datum":r["datum"],"Beleg":r["beleg"],"Typ":"Haben",
                        "Betrag":float(r["betrag"]),"Saldo_Änderung":-float(r["betrag"]),
                        "Status":"bezahlt"})

    if not entries:
        st.info("Keine Buchungen in diesem Zeitraum.")
        return

    df_e = pd.DataFrame(entries).sort_values("Datum")
    df_e["Kumulierter_Saldo"] = df_e["Saldo_Änderung"].cumsum()

    # Zusammenfassung
    gesamt_forderungen = float(df_e[df_e["Typ"]=="Soll"]["Betrag"].sum())
    gesamt_zahlungen   = float(df_e[df_e["Typ"]=="Haben"]["Betrag"].sum())
    offener_saldo      = gesamt_forderungen - gesamt_zahlungen

    c1, c2, c3 = st.columns(3)
    c1.metric("Forderungen gesamt", fmt_eur(gesamt_forderungen))
    c2.metric("Zahlungen gesamt", fmt_eur(gesamt_zahlungen))
    c3.metric("Offener Saldo", fmt_eur(offener_saldo),
              delta_color="inverse" if offener_saldo > 0 else "normal")

    st.dataframe(df_e, use_container_width=True, height=350)
    st.line_chart(df_e.set_index("Datum")["Kumulierter_Saldo"])
    csv = df_e.to_csv(index=False, sep=";").encode("utf-8-sig")
    st.download_button("📥 Kontenblatt CSV", csv,
                       f"kontenblatt_{cid}_{from_d}_{to_d}.csv", "text/csv")


# ─────────────────────────────────────────────────────────────
# 7. UStVA XML Vorbereitung
# ─────────────────────────────────────────────────────────────

def generate_ustv_a_xml(df_fn, year: int, month: int, get_setting_fn) -> str:
    """
    Erstellt eine UStVA-Übersicht für die manuelle Eingabe im ELSTER-Portal.
    Hinweis: Echte UStVA nur via ELSTER möglich.
    """
    month_str = f"{year}-{month:02d}"

    # Einnahmen nach MwSt-Satz
    revenues = df_fn(f"""
        SELECT vat_rate, ROUND(SUM(net_total),2) AS netto, ROUND(SUM(vat_total),2) AS ust
        FROM invoices
        WHERE substr(invoice_date,1,7)='{month_str}' AND status IN ('bezahlt','offen')
        GROUP BY vat_rate
    """)

    # Vorsteuer aus Ausgaben
    vorsteuer = df_fn(f"""
        SELECT ROUND(SUM(vat_amount),2) AS vorsteuer
        FROM expenses WHERE bwa_month='{month_str}'
    """).iloc[0]["vorsteuer"] or 0

    co_name   = get_setting_fn("company_name","Byblos")
    co_strnr  = get_setting_fn("company_steuernummer","")
    co_fa     = get_setting_fn("company_finanzamt","")

    lines = [
        f"USt-Voranmeldung {month:02d}/{year}",
        f"Steuerpflichtige: {co_name}",
        f"Steuernummer: {co_strnr}",
        f"Finanzamt: {co_fa}",
        f"Anmeldezeitraum: {month:02d}/{year}",
        "=" * 60,
        "",
        "1. Steuerbare Umsätze:",
    ]

    total_ust = 0
    if not revenues.empty:
        for _, r in revenues.iterrows():
            vat_r = float(r["vat_rate"])
            netto = float(r["netto"])
            ust   = float(r["ust"])
            total_ust += ust
            zeile = {19.0:"KZ 81", 7.0:"KZ 83", 0.0:"KZ 43"}.get(vat_r, "KZ 81")
            lines.append(f"  {vat_r:.0f}% MwSt ({zeile}): Netto {netto:.2f} EUR, USt {ust:.2f} EUR")

    lines += [
        "",
        f"2. Gesamte Umsatzsteuer: {total_ust:.2f} EUR",
        f"3. Abziehbare Vorsteuer: {float(vorsteuer):.2f} EUR",
        f"",
        f"= Zahllast / Erstattung: {total_ust - float(vorsteuer):.2f} EUR",
        "",
        "⚠️  Für die offizielle UStVA: https://www.elster.de",
        "    Über 'Mein ELSTER' > Formulare > Umsatzsteuer-Voranmeldung",
    ]
    return "\n".join(lines)


def page_ustv_a(df_fn, get_setting_fn, set_setting_fn) -> None:
    st.title("🧾 Umsatzsteuer-Voranmeldung")
    st.caption("UStVA-Übersicht für die manuelle Eingabe im ELSTER-Portal.")

    tabs = st.tabs(["📊 UStVA Übersicht", "⚙️ Einstellungen", "📖 ELSTER-Anleitung"])

    with tabs[0]:
        col1, col2 = st.columns(2)
        year  = col1.selectbox("Jahr", list(range(date.today().year, date.today().year-3,-1)))
        month = col2.selectbox("Monat", list(range(1,13)), index=date.today().month-1,
                                format_func=lambda m: ["Jan","Feb","Mär","Apr","Mai","Jun",
                                                        "Jul","Aug","Sep","Okt","Nov","Dez"][m-1])
        if st.button("📄 UStVA Übersicht erstellen", type="primary"):
            text = generate_ustv_a_xml(df_fn, year, month, get_setting_fn)
            st.text_area("UStVA-Übersicht", text, height=350)
            st.download_button("📥 Als TXT herunterladen",
                               text.encode("utf-8"),
                               f"ustv_a_{year}_{month:02d}.txt","text/plain")
            st.warning("⚠️ Dies ist KEINE offizielle UStVA. Bitte ELSTER für die Anmeldung nutzen!")

        # Monatsübersicht
        st.divider()
        st.subheader(f"Jahresübersicht {date.today().year}")
        annual = df_fn(f"""
            SELECT substr(invoice_date,1,7) AS Monat,
                   ROUND(SUM(net_total),2) AS Netto,
                   ROUND(SUM(vat_total),2) AS USt_eingenommen
            FROM invoices
            WHERE substr(invoice_date,1,4)='{date.today().year}'
              AND status IN ('bezahlt','offen')
            GROUP BY substr(invoice_date,1,7) ORDER BY Monat
        """)
        vorsteuer_ann = df_fn(f"""
            SELECT bwa_month AS Monat, ROUND(SUM(vat_amount),2) AS Vorsteuer
            FROM expenses WHERE substr(bwa_month,1,4)='{date.today().year}'
            GROUP BY bwa_month ORDER BY bwa_month
        """)
        if not annual.empty:
            merged = annual.merge(vorsteuer_ann, on="Monat", how="left").fillna(0)
            merged["Zahllast"] = (merged["USt_eingenommen"] - merged["Vorsteuer"]).round(2)
            st.dataframe(merged, use_container_width=True)
            st.bar_chart(merged.set_index("Monat")[["USt_eingenommen","Vorsteuer","Zahllast"]])

    with tabs[1]:
        with st.form("ustv_a_settings"):
            strnr   = st.text_input("Steuernummer (ELSTER-Format: z.B. 21/815/08150)",
                                     get_setting_fn("company_steuernummer",""))
            finanzamt = st.text_input("Finanzamt", get_setting_fn("company_finanzamt",""))
            dauerverl = st.checkbox("Dauerfristverlängerung beantragt",
                                    value=get_setting_fn("ust_dauerfrister","0")=="1")
            if st.form_submit_button("💾 Speichern"):
                set_setting_fn("company_steuernummer", strnr)
                set_setting_fn("company_finanzamt", finanzamt)
                set_setting_fn("ust_dauerfrister", "1" if dauerverl else "0")
                st.success("✅ Gespeichert.")

    with tabs[2]:
        st.markdown("""
**UStVA über ELSTER einreichen:**

1. **www.elster.de** aufrufen → Mein ELSTER anmelden
2. **Formulare & Leistungen** → Alle Formulare → Umsatzsteuer-Voranmeldung
3. Steuernummer eingeben (Format: 21/815/08150)
4. Zahlen aus der obigen Übersicht eintragen
5. Prüfen und absenden

**Fristen:**
- Monatliche UStVA: 10. des Folgemonats (mit Dauerfristverlängerung: 10. des übernächsten Monats)
- Quartalsweise: 10. des auf das Quartal folgenden Monats (Umsatz < 7.500 €/Jahr USt)

**Tipp:** Mit ELSTER-Dauerfristverlängerung gewinnen Sie einen Monat Aufschub.
Antrag einmalig stellen (Formular USt 1 H).
        """)
