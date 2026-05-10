"""
extensions_v2_business_ops.py – Business-Operations Features
=============================================================
1.  Tages-Briefing (Morgen-Zusammenfassung)
2.  KPI-Ziele setzen und verfolgen
3.  Kundenwert-Analyse (CLV)
4.  Schicht-Konflikte erkennen
5.  Arbeitszeit-Ampel (ArbZG)
6.  Währungsrechner
7.  Lieferanten-Bewertung
8.  Kunden-Jubiläen
9.  Auto-E-Mail bei Zahlungseingang
10. Einsatzkosten-Kalkulator
"""

from __future__ import annotations
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
import pandas as pd
import streamlit as st


def fmt_eur(v: float) -> str:
    return f"{v:,.2f} EUR".replace(",","X").replace(".",",").replace("X",".")


def register_business_ops(run_fn, df_fn) -> None:
    run_fn("""CREATE TABLE IF NOT EXISTS kpi_goals (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        goal_name TEXT NOT NULL,
        metric TEXT NOT NULL,
        target_value REAL NOT NULL,
        current_value REAL DEFAULT 0,
        period_key TEXT NOT NULL,
        notes TEXT,
        status TEXT DEFAULT 'aktiv',
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )""")
    run_fn("""CREATE TABLE IF NOT EXISTS supplier_ratings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        supplier_id INTEGER NOT NULL,
        rating INTEGER NOT NULL,
        category TEXT DEFAULT 'allgemein',
        comment TEXT,
        rated_by TEXT,
        rated_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(supplier_id) REFERENCES suppliers(id)
    )""")
    run_fn("""CREATE TABLE IF NOT EXISTS customer_anniversaries (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        customer_id INTEGER NOT NULL,
        anniversary_type TEXT DEFAULT 'Vertragsbeginn',
        anniversary_date TEXT NOT NULL,
        notify_days_before INTEGER DEFAULT 7,
        active INTEGER DEFAULT 1,
        FOREIGN KEY(customer_id) REFERENCES customers(id)
    )""")
    run_fn("""CREATE TABLE IF NOT EXISTS payment_auto_emails (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        invoice_id INTEGER NOT NULL,
        sent_at TEXT NOT NULL,
        recipient TEXT,
        subject TEXT,
        status TEXT DEFAULT 'gesendet'
    )""")
    try:
        run_fn("""INSERT OR IGNORE INTO customer_anniversaries(customer_id,anniversary_type,anniversary_date)
            SELECT customer_id,'Erster Auftrag',MIN(substr(invoice_date,1,10))
            FROM invoices WHERE customer_id IS NOT NULL GROUP BY customer_id""")
    except Exception:
        pass


def render_daily_briefing(df_fn, get_setting_fn) -> None:
    today = date.today().isoformat()
    h = datetime.now().hour
    greeting = "Guten Morgen" if h < 12 else "Guten Tag" if h < 17 else "Guten Abend"
    co = get_setting_fn("company_name", "Byblos")
    days_de = ["Montag","Dienstag","Mittwoch","Donnerstag","Freitag","Samstag","Sonntag"]
    months_de = ["Januar","Februar","Maerz","April","Mai","Juni","Juli","August","September","Oktober","November","Dezember"]
    d = date.today()
    date_str = f"{days_de[d.weekday()]}, {d.day}. {months_de[d.month-1]} {d.year}"

    shifts = int(df_fn(f"SELECT COUNT(*) AS n FROM shifts WHERE shift_date='{today}'").iloc[0]["n"])
    unbesetzt = int(df_fn(f"SELECT COUNT(*) AS n FROM shifts WHERE shift_date='{today}' AND employee_id IS NULL").iloc[0]["n"])
    overdue = int(df_fn("SELECT COUNT(*) AS n FROM invoices WHERE status='ueberfaellig'").iloc[0]["n"])

    items = []
    if unbesetzt > 0: items.append(f"{unbesetzt} unbesetzte Schichten")
    if overdue > 0: items.append(f"{overdue} ueberfaellige Rechnungen")
    summary = " | ".join(items) if items else "Alles in Ordnung"

    st.markdown(f"""
<div style="background:linear-gradient(135deg,#1a2744,#2c1810);
            border-left:4px solid #c0392b;
            padding:14px 18px;border-radius:8px;margin-bottom:16px;">
  <div style="font-size:1.1rem;font-weight:bold;color:#e8eaf0;">
    {greeting}, {co}!
  </div>
  <div style="font-size:.85rem;color:#aaa;margin:2px 0 8px;">{date_str}</div>
  <div style="font-size:.9rem;color:#e8eaf0;">
    Heute: <b>{shifts}</b> Schichten &nbsp;|&nbsp; {summary}
  </div>
</div>""", unsafe_allow_html=True)


def page_daily_briefing(df_fn, get_setting_fn) -> None:
    st.title("Tages-Briefing")
    render_daily_briefing(df_fn, get_setting_fn)
    today = date.today().isoformat()
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Schichten heute")
        shifts = df_fn(f"""SELECT s.start_time AS Von, s.end_time AS Bis,
               COALESCE(e.name,'UNBESETZT') AS MA,
               COALESCE(c.company,'-') AS Kunde
        FROM shifts s LEFT JOIN employees e ON e.id=s.employee_id
        LEFT JOIN customers c ON c.id=s.customer_id
        WHERE s.shift_date='{today}' ORDER BY s.start_time""")
        if not shifts.empty:
            st.dataframe(shifts, use_container_width=True)
        else:
            st.info("Keine Schichten heute.")
    with col2:
        st.subheader("Handlungsbedarf")
        overdue = df_fn("""SELECT i.invoice_no AS Nr, c.company AS Kunde,
               ROUND(i.gross_total-i.paid_amount,2) AS Offen
        FROM invoices i JOIN customers c ON c.id=i.customer_id
        WHERE i.status='ueberfaellig' ORDER BY i.due_date LIMIT 5""")
        if not overdue.empty:
            st.error(f"{len(overdue)} ueberfaellige Rechnungen:")
            st.dataframe(overdue, use_container_width=True)
        else:
            st.success("Keine ueberfaelligen Rechnungen")

    st.subheader("Jubilaeume diese Woche")
    week_end = (date.today() + timedelta(days=7)).isoformat()
    ann = df_fn(f"""SELECT c.company AS Kunde, ca.anniversary_type AS Art, ca.anniversary_date AS Datum
        FROM customer_anniversaries ca JOIN customers c ON c.id=ca.customer_id
        WHERE ca.active=1 AND strftime('%m-%d', ca.anniversary_date) BETWEEN
              strftime('%m-%d', '{today}') AND strftime('%m-%d', '{week_end}')""")
    if not ann.empty:
        for _, r in ann.iterrows():
            st.info(f"Jubilaeum: {r['Kunde']} - {r['Art']} ({r['Datum']})")
    else:
        st.info("Keine Jubilaeume diese Woche.")


def page_kpi_goals(run_fn, df_fn) -> None:
    st.title("KPI-Ziele")
    METRICS = {
        "Monatsumsatz (EUR)": "SELECT COALESCE(SUM(gross_total),0) FROM invoices WHERE substr(invoice_date,1,7)=? AND status='bezahlt'",
        "Neue Kunden":        "SELECT COUNT(*) FROM customers WHERE substr(created_at,1,7)=?",
        "Schichten gesamt":   "SELECT COUNT(*) FROM shifts WHERE substr(shift_date,1,7)=?",
        "Ausgaben (EUR)":     "SELECT COALESCE(SUM(gross_amount),0) FROM expenses WHERE bwa_month=?",
    }
    this_month = date.today().strftime("%Y-%m")
    tabs = st.tabs(["Dashboard", "Ziel definieren", "Alle Ziele"])

    with tabs[0]:
        goals = df_fn(f"SELECT * FROM kpi_goals WHERE status='aktiv' AND period_key='{this_month}' ORDER BY goal_name")
        if goals.empty:
            st.info("Noch keine Ziele. Unter 'Ziel definieren' anlegen.")
        else:
            cols = st.columns(min(len(goals), 3))
            for i, (_, g) in enumerate(goals.iterrows()):
                target = float(g["target_value"])
                try:
                    q = METRICS.get(g["metric"],"")
                    if "?" in q:
                        curr = float(df_fn(q, (this_month,)).iloc[0,0] or 0)
                    else:
                        curr = float(g["current_value"] or 0)
                    run_fn("UPDATE kpi_goals SET current_value=? WHERE id=?", (curr, int(g["id"])))
                except Exception:
                    curr = float(g["current_value"] or 0)
                pct = (curr / target * 100) if target > 0 else 0
                color = "#27ae60" if pct >= 100 else "#e67e22" if pct >= 70 else "#c0392b"
                cols[i % 3].markdown(f"""
<div style="background:#1a1f2e;border:1px solid {color};border-radius:8px;padding:12px;">
  <div style="font-size:.85rem;color:#aaa;">{g["goal_name"]}</div>
  <div style="font-size:1.4rem;font-weight:bold;color:{color};">{pct:.0f}%</div>
  <div style="background:#0e1117;border-radius:4px;height:6px;margin:6px 0;">
    <div style="background:{color};width:{min(pct,100):.0f}%;height:6px;border-radius:4px;"></div>
  </div>
  <div style="font-size:.8rem;color:#888;">IST: {curr:,.0f} / SOLL: {target:,.0f}</div>
</div>""", unsafe_allow_html=True)

    with tabs[1]:
        with st.form("goal_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            name   = col1.text_input("Ziel-Name *")
            metric = col2.selectbox("Kennzahl", list(METRICS.keys()))
            col3, col4 = st.columns(2)
            target = col3.number_input("Zielwert *", min_value=0.0, value=10000.0, step=100.0)
            period_key = col4.text_input("Periode", this_month)
            if st.form_submit_button("Ziel speichern", type="primary") and name:
                run_fn("INSERT INTO kpi_goals(goal_name,metric,target_value,period_key) VALUES(?,?,?,?)",
                       (name, metric, target, period_key))
                st.success(f"Ziel '{name}' gespeichert!")
                st.rerun()

    with tabs[2]:
        all_g = df_fn("SELECT goal_name AS Ziel, metric AS Kennzahl, target_value AS Soll, current_value AS IST, period_key AS Monat FROM kpi_goals ORDER BY period_key DESC")
        if not all_g.empty:
            st.dataframe(all_g, use_container_width=True)


def page_clv_analysis(df_fn) -> None:
    st.title("Kundenwert-Analyse (CLV)")
    years = st.slider("Analysezeitraum (Jahre)", 1, 5, 3)
    cutoff = (date.today() - timedelta(days=365*years)).isoformat()
    clv = df_fn(f"""SELECT c.customer_no AS Nr, c.company AS Kunde,
               ROUND(SUM(i.gross_total),2) AS Umsatz,
               COUNT(DISTINCT i.id) AS Rechnungen,
               ROUND(AVG(i.gross_total),2) AS Avg,
               ROUND(CAST(julianday('now') - julianday(MIN(i.invoice_date)) AS REAL)/365,1) AS Jahre
        FROM customers c JOIN invoices i ON i.customer_id=c.id
        WHERE i.invoice_date >= '{cutoff}'
        GROUP BY c.id ORDER BY Umsatz DESC""")
    if clv.empty:
        st.info("Keine Daten.")
        return
    clv["CLV_jaehrl"] = (clv["Umsatz"] / clv["Jahre"].replace(0,1)).round(0)
    q75 = float(clv["Umsatz"].quantile(0.75))
    q50 = float(clv["Umsatz"].quantile(0.50))
    clv["Segment"] = clv["Umsatz"].apply(lambda v: "Premium" if v>=q75 else "Standard" if v>=q50 else "Basis")
    c1,c2,c3 = st.columns(3)
    c1.metric("Kunden", len(clv))
    c2.metric("Gesamtumsatz", fmt_eur(float(clv["Umsatz"].sum())))
    c3.metric("Premium-Kunden", len(clv[clv["Segment"]=="Premium"]))
    st.dataframe(clv, use_container_width=True)
    st.bar_chart(clv.set_index("Kunde")["CLV_jaehrl"].head(10))


def page_shift_conflicts(df_fn) -> None:
    st.title("Schicht-Konflikte")
    from_d = st.date_input("Von", date.today())
    to_d   = st.date_input("Bis", date.today() + timedelta(days=14))
    if st.button("Konflikte suchen", type="primary"):
        doubles = df_fn(f"""SELECT e.name AS MA, s1.shift_date AS Datum,
               s1.start_time AS Start1, s1.end_time AS Ende1,
               s2.start_time AS Start2, s2.end_time AS Ende2
        FROM shifts s1 JOIN shifts s2 ON s2.employee_id=s1.employee_id
            AND s2.shift_date=s1.shift_date AND s2.id > s1.id
            AND s2.start_time < s1.end_time AND s2.end_time > s1.start_time
        JOIN employees e ON e.id=s1.employee_id
        WHERE s1.shift_date BETWEEN '{from_d.isoformat()}' AND '{to_d.isoformat()}' """)
        if not doubles.empty:
            st.error(f"{len(doubles)} Doppelbuchungen gefunden!")
            st.dataframe(doubles, use_container_width=True)
        else:
            st.success("Keine Konflikte gefunden!")


def page_arbzg_monitor(df_fn) -> None:
    st.title("Arbeitszeit-Ampel (ArbZG)")
    month = st.text_input("Monat", date.today().strftime("%Y-%m"))
    data = df_fn(f"""SELECT e.name AS MA,
               ROUND(COUNT(DISTINCT s.shift_date)*8.0,1) AS Std_Monat,
               COUNT(DISTINCT s.shift_date) AS Tage
        FROM employees e JOIN shifts s ON s.employee_id=e.id
        WHERE e.active=1 AND substr(s.shift_date,1,7)='{month}'
        GROUP BY e.id ORDER BY Std_Monat DESC""")
    if data.empty:
        st.info("Keine Daten.")
        return
    data["Status"] = data["Std_Monat"].apply(
        lambda v: "OK" if v <= 208 else "Warnung" if v <= 230 else "Verstoss")
    c1,c2,c3 = st.columns(3)
    c1.metric("OK", len(data[data["Status"]=="OK"]))
    c2.metric("Warnung", len(data[data["Status"]=="Warnung"]))
    c3.metric("Verstoss", len(data[data["Status"]=="Verstoss"]))
    st.dataframe(data, use_container_width=True)


def page_currency_calculator(get_setting_fn, set_setting_fn) -> None:
    st.title("Waehrungsrechner")
    RATES = {"CHF":0.93,"USD":1.09,"GBP":0.86,"PLN":4.27,"TRY":35.2,"SEK":11.3}
    amount = st.number_input("Betrag (EUR)", min_value=0.0, value=100.0, step=10.0)
    to_c   = st.selectbox("Waehrung", list(RATES.keys()))
    rate   = RATES[to_c]
    st.metric(f"{amount:.2f} EUR =", f"{amount*rate:.2f} {to_c}")
    st.caption(f"Kurs: 1 EUR = {rate} {to_c}")
    cols = st.columns(3)
    for i,(c,r) in enumerate(RATES.items()):
        cols[i%3].metric(c, f"{amount*r:.2f}")


def page_supplier_ratings(run_fn, df_fn, current_user_fn) -> None:
    st.title("Lieferanten-Bewertung")
    user = current_user_fn() or {}
    tabs = st.tabs(["Uebersicht", "Bewertung abgeben"])
    with tabs[0]:
        ratings = df_fn("""SELECT s.name AS Lieferant,
               COUNT(r.id) AS N, ROUND(AVG(r.rating),1) AS Score
        FROM suppliers s LEFT JOIN supplier_ratings r ON r.supplier_id=s.id
        GROUP BY s.id HAVING COUNT(r.id) > 0 ORDER BY Score DESC""")
        if not ratings.empty:
            for _, r in ratings.iterrows():
                stars = "AAAAA"[:int(r["Score"])]
                st.write(f"**{r['Lieferant']}** — {r['Score']}/5 ({r['N']} Bewertungen)")
        else:
            st.info("Noch keine Bewertungen.")
    with tabs[1]:
        suppliers = df_fn("SELECT id, name AS label FROM suppliers ORDER BY name")
        if suppliers.empty:
            st.info("Keine Lieferanten.")
            return
        with st.form("rat_form", clear_on_submit=True):
            sel = st.selectbox("Lieferant", suppliers["label"].tolist())
            rating = st.slider("Bewertung (1-5)", 1, 5, 4)
            comment = st.text_area("Kommentar")
            if st.form_submit_button("Speichern"):
                sid = int(suppliers[suppliers["label"]==sel].iloc[0]["id"])
                run_fn("INSERT INTO supplier_ratings(supplier_id,rating,comment,rated_by) VALUES(?,?,?,?)",
                       (sid, rating, comment, user.get("username","admin")))
                st.success("Gespeichert!")
                st.rerun()


def page_deployment_calculator(df_fn) -> None:
    st.title("Einsatzkosten-Kalkulator")
    col1,col2,col3 = st.columns(3)
    hours = col1.number_input("Stunden/Tag", value=8.0, step=0.5)
    staff = col2.number_input("Mitarbeiter", value=2, step=1)
    days  = col3.number_input("Tage", value=1, step=1)
    total_h = hours * staff * days

    col4,col5,col6 = st.columns(3)
    wage    = col4.number_input("Stundenlohn brutto", value=13.0, step=0.5)
    ag_pct  = col5.number_input("AG-Nebenkosten %", value=28.0, step=1.0)
    margin  = col6.slider("Gewinnmarge %", 5, 50, 20)

    overhead_pct = st.number_input("Gemeinkosten %", value=20.0, step=1.0)
    vat = st.selectbox("MwSt %", [0, 7, 19], index=2)

    labor    = total_h * wage
    ag_cost  = labor * ag_pct / 100
    overhead = (labor + ag_cost) * overhead_pct / 100
    cost     = labor + ag_cost + overhead
    profit   = cost * margin / 100
    net      = cost + profit
    gross    = net * (1 + vat/100)

    c1,c2,c3,c4 = st.columns(4)
    c1.metric("Stunden gesamt", f"{total_h:.0f} h")
    c2.metric("Personalkosten", fmt_eur(labor+ag_cost))
    c3.metric("Netto-Angebot", fmt_eur(net))
    c4.metric("Brutto-Angebot", fmt_eur(gross))
    st.info(f"Effektiver Stundensatz: {gross/total_h:.2f} EUR/h")


def page_payment_email_settings(run_fn, df_fn, get_setting_fn, set_setting_fn) -> None:
    st.title("Auto-E-Mail bei Zahlung")
    enabled = st.checkbox("Aktiv", value=get_setting_fn("auto_payment_email","0") == "1")
    if st.button("Speichern"):
        set_setting_fn("auto_payment_email", "1" if enabled else "0")
        st.success("Gespeichert!")
    sent = df_fn("SELECT sent_at AS Zeit, recipient AS Empfaenger FROM payment_auto_emails ORDER BY sent_at DESC LIMIT 20")
    if not sent.empty:
        st.dataframe(sent, use_container_width=True)
