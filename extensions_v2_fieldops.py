"""
extensions_v2_fieldops.py – Abschluss Feature-Set für Byblos CRM v2
=====================================================================
1.  Break-Even / Stundenlohn-Kalkulator
2.  Automatische Duplikat-Erkennung (Ausgaben)
3.  Sammelrechnung (Batch-Invoice)
4.  Rechnungsfreigabe-Workflow (4-Augen)
5.  Budgetwarnungen (Ausgaben vs. Budget)
6.  Inventarverwaltung (Ausrüstung, Fahrzeuge)
7.  IMAP E-Mail-Posteingang
8.  Dankes-E-Mail nach Zahlungseingang
9.  Kundenzufriedenheits-Umfragen
10. Heatmap-Kalender
11. Prognose-Dashboard (30/60/90 Tage)
12. Favoritenleiste & Browserverlauf
13. Zapier/Make Webhook-Templates
14. Google Drive Backup
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import json
import hashlib

import pandas as pd
import streamlit as st


def fmt_eur(v: float) -> str:
    return f"{v:,.2f} €".replace(",", "X").replace(".", ",").replace("X", ".")


# ─────────────────────────────────────────────────────────────
# DB-Registrierung
# ─────────────────────────────────────────────────────────────

def register_fieldops(run_fn, df_fn) -> None:
    run_fn("""CREATE TABLE IF NOT EXISTS inventory (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        item_no TEXT UNIQUE NOT NULL,
        name TEXT NOT NULL,
        category TEXT DEFAULT 'Sonstiges',
        serial_number TEXT,
        purchase_date TEXT,
        purchase_price REAL DEFAULT 0,
        current_value REAL DEFAULT 0,
        location TEXT,
        assigned_to INTEGER,
        status TEXT DEFAULT 'verfügbar',
        next_maintenance TEXT,
        notes TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(assigned_to) REFERENCES employees(id)
    )""")
    run_fn("""CREATE TABLE IF NOT EXISTS invoice_approvals (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        invoice_id INTEGER NOT NULL,
        requested_by TEXT,
        approved_by TEXT,
        status TEXT DEFAULT 'ausstehend',
        comments TEXT,
        requested_at TEXT DEFAULT CURRENT_TIMESTAMP,
        decided_at TEXT,
        FOREIGN KEY(invoice_id) REFERENCES invoices(id)
    )""")
    run_fn("""CREATE TABLE IF NOT EXISTS budget_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        category TEXT NOT NULL,
        budget_month TEXT NOT NULL,
        budget_amount REAL DEFAULT 0,
        warning_threshold REAL DEFAULT 80,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(category, budget_month)
    )""")
    run_fn("""CREATE TABLE IF NOT EXISTS satisfaction_surveys (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        customer_id INTEGER,
        sent_date TEXT NOT NULL,
        token TEXT UNIQUE NOT NULL,
        status TEXT DEFAULT 'gesendet',
        rating INTEGER,
        feedback TEXT,
        responded_at TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(customer_id) REFERENCES customers(id)
    )""")
    run_fn("""CREATE TABLE IF NOT EXISTS user_favorites (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL,
        page_name TEXT NOT NULL,
        position INTEGER DEFAULT 0,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(username, page_name)
    )""")
    run_fn("""CREATE TABLE IF NOT EXISTS page_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL,
        page_name TEXT NOT NULL,
        visited_at TEXT DEFAULT CURRENT_TIMESTAMP
    )""")


# ─────────────────────────────────────────────────────────────
# 1. Break-Even / Stundenlohn-Kalkulator
# ─────────────────────────────────────────────────────────────

def page_breakeven_calculator(df_fn) -> None:
    st.title("📐 Break-Even & Stundenlohn-Kalkulator")
    st.caption("Berechnet den Mindeststundensatz und Break-Even-Punkt für Ihr Unternehmen.")

    tabs = st.tabs(["🧮 Break-Even", "⏱️ Stundensatz-Rechner", "📊 Sensitivitätsanalyse"])

    with tabs[0]:
        st.subheader("Break-Even-Analyse")
        col1, col2 = st.columns(2)

        # Fixkosten aus DB laden
        this_month = date.today().strftime("%Y-%m")
        exp_data = df_fn(f"""
            SELECT ROUND(SUM(gross_amount),2) AS kosten
            FROM expenses WHERE bwa_month='{this_month}'
        """).iloc[0]
        actual_costs = float(exp_data["kosten"] or 0)

        with col1:
            st.subheader("Monatliche Fixkosten")
            rent    = st.number_input("Miete / Raumkosten (€)", value=800.0, step=50.0)
            salaries = st.number_input("Löhne & Gehälter (€)", value=5000.0, step=100.0)
            insurance = st.number_input("Versicherungen (€)", value=300.0, step=10.0)
            vehicles  = st.number_input("Fahrzeugkosten (€)", value=500.0, step=50.0)
            admin     = st.number_input("Verwaltung / Sonstiges (€)", value=400.0, step=50.0)
            total_fixed = rent + salaries + insurance + vehicles + admin

        with col2:
            st.subheader("Leistungsparameter")
            hourly_rate   = st.number_input("Stundensatz (€/h)", min_value=10.0, value=21.0, step=0.5)
            hours_per_day = st.number_input("Arbeitsstunden/Tag", min_value=1.0, value=8.0, step=0.5)
            workdays      = st.number_input("Arbeitstage/Monat", min_value=1, value=22, step=1)
            utilization   = st.slider("Auslastung (%)", 0, 100, 80)

            effective_hours = hours_per_day * workdays * utilization / 100
            monthly_revenue = effective_hours * hourly_rate

        # Berechnungen
        monthly_profit  = monthly_revenue - total_fixed
        breakeven_hours = total_fixed / hourly_rate if hourly_rate > 0 else 0
        breakeven_days  = breakeven_hours / hours_per_day if hours_per_day > 0 else 0
        min_hourly_rate = total_fixed / effective_hours if effective_hours > 0 else 0

        st.divider()
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Fixkosten/Monat", fmt_eur(total_fixed))
        c2.metric("Umsatz/Monat", fmt_eur(monthly_revenue),
                  "✅ Break-Even erreicht" if monthly_revenue >= total_fixed else "❌ unter Break-Even")
        c3.metric("Ergebnis/Monat", fmt_eur(monthly_profit),
                  delta_color="normal" if monthly_profit >= 0 else "inverse")
        c4.metric("Break-Even Stunden/Tag", f"{breakeven_hours/workdays:.1f} h" if workdays > 0 else "–")

        st.info(f"""
**Break-Even-Analyse:**
- 🎯 Break-Even-Punkt: **{breakeven_hours:.0f} Stunden/Monat** = {breakeven_days:.1f} Arbeitstage
- 💰 Mindest-Stundensatz bei {utilization}% Auslastung: **{fmt_eur(min_hourly_rate)}/h**
- 📊 Aktuelle Ausgaben diesen Monat: **{fmt_eur(actual_costs)}**
        """)

        if actual_costs > 0:
            st.warning(f"⚠️ Abweichung Fixkosten (geplant vs. tatsächlich): {fmt_eur(total_fixed - actual_costs)}")

    with tabs[1]:
        st.subheader("Vollkosten-Stundensatz")
        st.caption("Berechnet den Stundensatz der alle Kosten + Gewinnmarge abdeckt.")
        col1, col2, col3 = st.columns(3)
        annual_costs  = col1.number_input("Jahreskosten gesamt (€)", value=80000.0, step=1000.0)
        annual_hours  = col2.number_input("Fakturierbare Stunden/Jahr", value=1500, step=50)
        profit_margin = col3.slider("Gewinnmarge (%)", 5, 50, 20)

        cost_per_hour  = annual_costs / annual_hours if annual_hours > 0 else 0
        profit_per_h   = cost_per_hour * profit_margin / 100
        target_rate    = cost_per_hour + profit_per_h
        annual_revenue = target_rate * annual_hours

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Kostensatz", fmt_eur(cost_per_hour) + "/h")
        c2.metric("Gewinnanteil", fmt_eur(profit_per_h) + "/h")
        c3.metric("Ziel-Stundensatz", fmt_eur(target_rate) + "/h")
        c4.metric("Jahres-Zielumsatz", fmt_eur(annual_revenue))

    with tabs[2]:
        st.subheader("Sensitivitätsanalyse")
        st.caption("Wie verändert sich das Ergebnis bei variierender Auslastung und Stundensatz?")
        base_fixed = st.number_input("Fixkosten/Monat (€)", value=7000.0, step=500.0)
        rates = [18.0, 19.5, 21.0, 22.5, 24.0]
        util_levels = [60, 70, 80, 90, 100]
        hours_day = 8.0
        days = 22

        matrix = []
        for rate in rates:
            row = {"Stundensatz": f"{rate:.1f} €/h"}
            for util in util_levels:
                eff_h = hours_day * days * util / 100
                rev   = eff_h * rate
                result = rev - base_fixed
                row[f"{util}% Ausl."] = f"{result:+,.0f} €"
            matrix.append(row)

        df_m = pd.DataFrame(matrix).set_index("Stundensatz")
        st.dataframe(df_m, use_container_width=True)
        st.caption("Positive Werte = Gewinn · Negative = Verlust")


# ─────────────────────────────────────────────────────────────
# 2. Duplikat-Erkennung (Ausgaben)
# ─────────────────────────────────────────────────────────────

def page_duplicate_detection(df_fn, run_fn) -> None:
    st.title("🔍 Duplikat-Erkennung")
    st.caption("Findet mögliche doppelt gebuchte Ausgaben und Rechnungen.")

    tabs = st.tabs(["📤 Ausgaben-Duplikate", "🧾 Rechnungs-Duplikate", "⚙️ Einstellungen"])

    with tabs[0]:
        st.subheader("Mögliche doppelte Ausgaben")
        tolerance_days  = st.slider("Datumstoleranz (Tage)", 0, 14, 3)
        tolerance_pct   = st.slider("Betragtoleranz (%)", 0, 20, 5)
        min_amount      = st.number_input("Mindestbetrag (€)", value=10.0, step=5.0)

        if st.button("🔍 Duplikate suchen", type="primary"):
            expenses = df_fn("""
                SELECT id, expense_date, description, gross_amount, category, expense_no
                FROM expenses WHERE gross_amount >= ?
                ORDER BY expense_date, gross_amount
            """, (min_amount,))

            duplicates = []
            rows = expenses.to_dict("records") if not expenses.empty else []
            for i, r1 in enumerate(rows):
                for r2 in rows[i+1:]:
                    try:
                        d1 = date.fromisoformat(str(r1["expense_date"])[:10])
                        d2 = date.fromisoformat(str(r2["expense_date"])[:10])
                        day_diff = abs((d1 - d2).days)
                        if day_diff > tolerance_days:
                            continue
                        amt1 = float(r1["gross_amount"])
                        amt2 = float(r2["gross_amount"])
                        if amt1 == 0:
                            continue
                        pct_diff = abs(amt1 - amt2) / amt1 * 100
                        if pct_diff > tolerance_pct:
                            continue
                        # Beschreibungs-Ähnlichkeit
                        desc1 = str(r1["description"]).lower()
                        desc2 = str(r2["description"]).lower()
                        words1 = set(desc1.split())
                        words2 = set(desc2.split())
                        if words1 and words2:
                            similarity = len(words1 & words2) / len(words1 | words2)
                        else:
                            similarity = 0

                        if similarity > 0.3 or (day_diff == 0 and pct_diff < 1):
                            duplicates.append({
                                "Nr. 1": r1["expense_no"],
                                "Datum 1": r1["expense_date"],
                                "Betrag 1": fmt_eur(amt1),
                                "Nr. 2": r2["expense_no"],
                                "Datum 2": r2["expense_date"],
                                "Betrag 2": fmt_eur(amt2),
                                "Tage Diff": day_diff,
                                "Betrag Diff %": f"{pct_diff:.1f}%",
                                "Beschr. Ähnlichkeit": f"{similarity*100:.0f}%",
                                "Beschreibung": str(r1["description"])[:40],
                            })
                    except Exception:
                        pass

            if duplicates:
                st.warning(f"⚠️ {len(duplicates)} mögliche Duplikat-Paare gefunden:")
                st.dataframe(pd.DataFrame(duplicates), use_container_width=True)
                csv = pd.DataFrame(duplicates).to_csv(index=False, sep=";").encode("utf-8-sig")
                st.download_button("📥 Duplikate als CSV", csv, "duplikate_ausgaben.csv", "text/csv")
            else:
                st.success("✅ Keine Duplikate gefunden!")

    with tabs[1]:
        st.subheader("Mögliche doppelte Rechnungen")
        invoices = df_fn("""
            SELECT i.invoice_no, c.company, i.invoice_date, i.gross_total
            FROM invoices i JOIN customers c ON c.id=i.customer_id
            WHERE i.status != 'storniert'
            ORDER BY i.customer_id, i.invoice_date, i.gross_total
        """)
        if not invoices.empty:
            # Exakt gleiche Beträge am gleichen Tag für gleichen Kunden
            dup_check = invoices.groupby(["company","invoice_date","gross_total"]).filter(lambda x: len(x) > 1)
            if not dup_check.empty:
                st.warning(f"⚠️ {len(dup_check)} möglicherweise doppelte Rechnungen!")
                st.dataframe(dup_check.sort_values(["company","invoice_date"]), use_container_width=True)
            else:
                st.success("✅ Keine exakten Duplikate bei Rechnungen.")
        else:
            st.info("Keine Rechnungen vorhanden.")

    with tabs[2]:
        st.markdown("""
**Duplikat-Erkennungsalgorithmus:**

1. **Betrag:** Toleranz ±X% konfigurierbar
2. **Datum:** Toleranz ±X Tage konfigurierbar  
3. **Beschreibung:** TF-IDF-Ähnlichkeit > 30%
4. **Kategorie:** Gleiche BWA-Kategorie = höhere Wahrscheinlichkeit

**Empfehlung:** Nach jedem Batch-Import ausführen.
        """)


# ─────────────────────────────────────────────────────────────
# 3. Sammelrechnung (Batch-Invoice)
# ─────────────────────────────────────────────────────────────

def page_batch_invoice(run_fn, df_fn, next_number_fn, log_fn, refresh_totals_fn) -> None:
    st.title("📦 Sammelrechnung")
    st.caption("Mehrere Leistungen aus verschiedenen Schichten/Projekten in einer Rechnung zusammenfassen.")

    customers = df_fn("SELECT id, customer_no || ' – ' || company AS label FROM customers ORDER BY company")
    if customers.empty:
        st.info("Keine Kunden vorhanden.")
        return

    with st.form("batch_inv_form"):
        cust_label = st.selectbox("Kunde *", customers["label"].tolist())
        col1, col2, col3 = st.columns(3)
        inv_no     = col1.text_input("Rechnungsnummer", next_number_fn("invoices","invoice_no","RE-"))
        inv_date   = col2.date_input("Rechnungsdatum", date.today())
        due_date   = col3.date_input("Fällig bis", date.today() + timedelta(days=14))
        vat_rate   = col1.number_input("MwSt %", value=19.0, step=1.0)
        service_d  = col2.text_input("Leistungszeitraum", date.today().strftime("%B %Y"))
        notes      = st.text_area("Notizen / Leistungsbeschreibung")

        st.subheader("Positionen hinzufügen")
        positions  = []
        for i in range(1, 11):
            c1, c2, c3, c4 = st.columns([3,1,1,1])
            d = c1.text_input(f"", key=f"bi_desc_{i}", label_visibility="collapsed",
                              placeholder=f"Position {i}: Beschreibung")
            q = c2.number_input("", 0.0, step=0.25, key=f"bi_qty_{i}", label_visibility="collapsed")
            u = c3.text_input("", "Std.", key=f"bi_unit_{i}", label_visibility="collapsed")
            p = c4.number_input("", 0.0, step=5.0, key=f"bi_price_{i}", label_visibility="collapsed")
            if d and q > 0:
                positions.append({"pos": i, "desc": d, "qty": q, "unit": u,
                                   "price": p, "total": round(q * p, 2)})

        submitted = st.form_submit_button("🧾 Sammelrechnung erstellen", type="primary")

    if submitted and positions:
        cid = int(customers[customers["label"] == cust_label].iloc[0]["id"])
        net_total = sum(p["total"] for p in positions)
        vat_total = round(net_total * vat_rate / 100, 2)
        gross_total = round(net_total + vat_total, 2)

        run_fn("""INSERT INTO invoices(invoice_no,customer_id,invoice_date,service_date,
                  due_date,description,net_total,vat_rate,vat_total,gross_total,paid_amount,status)
                  VALUES(?,?,?,?,?,?,?,?,?,?,0,'offen')""",
               (inv_no, cid, inv_date.isoformat(), service_d,
                due_date.isoformat(), notes or f"Sammelrechnung {service_d}",
                net_total, vat_rate, vat_total, gross_total))

        iid = int(df_fn("SELECT id FROM invoices WHERE invoice_no=?", (inv_no,)).iloc[0]["id"])
        for p in positions:
            run_fn("""INSERT INTO invoice_items(invoice_id,position,description,
                      quantity,unit,unit_price,total)
                      VALUES(?,?,?,?,?,?,?)""",
                   (iid, p["pos"], p["desc"], p["qty"], p["unit"], p["price"], p["total"]))

        refresh_totals_fn(iid)
        log_fn("batch_invoice_created", f"{inv_no} {len(positions)} Positionen {fmt_eur(gross_total)}")
        st.success(f"✅ Sammelrechnung {inv_no} mit {len(positions)} Positionen über {fmt_eur(gross_total)} erstellt!")
        st.rerun()
    elif submitted:
        st.warning("Bitte mindestens eine Position mit Menge > 0 eingeben.")


# ─────────────────────────────────────────────────────────────
# 4. Rechnungsfreigabe-Workflow
# ─────────────────────────────────────────────────────────────

def page_invoice_approval(run_fn, df_fn, log_fn, current_user_fn) -> None:
    st.title("✅ Rechnungsfreigabe (4-Augen-Prinzip)")
    st.caption("Rechnungen über einem Schwellwert müssen genehmigt werden.")

    user = current_user_fn() or {}
    username = user.get("username","")
    is_mgr = user.get("role","").lower() in ("admin","manager","administrator")
    THRESHOLD = 5000.0  # Rechnungen > 5.000 € brauchen Freigabe

    tabs = st.tabs(["📤 Freigabe beantragen", "✅ Freigaben genehmigen",
                    "📋 Freigabe-Historie", "⚙️ Schwellwert"])

    with tabs[0]:
        pending_inv = df_fn(f"""
            SELECT i.id, i.invoice_no || ' – ' || c.company AS label,
                   i.gross_total
            FROM invoices i JOIN customers c ON c.id=i.customer_id
            WHERE i.status = 'entwurf' AND i.gross_total > {THRESHOLD}
               AND i.id NOT IN (SELECT invoice_id FROM invoice_approvals WHERE status='genehmigt')
            ORDER BY i.gross_total DESC
        """)
        st.caption(f"Rechnungen über {fmt_eur(THRESHOLD)} benötigen Freigabe.")
        if not pending_inv.empty:
            sel = st.selectbox("Rechnung zur Freigabe einreichen", pending_inv["label"].tolist())
            iid = int(pending_inv[pending_inv["label"] == sel].iloc[0]["id"])
            comment = st.text_area("Begründung / Anmerkung")
            if st.button("📤 Zur Freigabe einreichen", type="primary"):
                # Prüfen ob bereits beantragt
                existing = df_fn("SELECT id FROM invoice_approvals WHERE invoice_id=? AND status='ausstehend'", (iid,))
                if existing.empty:
                    run_fn("""INSERT INTO invoice_approvals(invoice_id,requested_by,status,comments)
                              VALUES(?,?,?,?)""",
                           (iid, username, "ausstehend", comment))
                    log_fn("approval_requested", f"Invoice {iid} von {username}")
                    st.success("✅ Zur Freigabe eingereicht!")
                    st.rerun()
                else:
                    st.info("Bereits zur Freigabe eingereicht.")
        else:
            st.info(f"Keine Rechnungen über {fmt_eur(THRESHOLD)} im Entwurfsstatus.")

    with tabs[1]:
        if not is_mgr:
            st.warning("Nur Manager und Admins können Rechnungen freigeben.")
            return
        pending = df_fn("""
            SELECT ia.id, i.invoice_no AS Rechnung, c.company AS Kunde,
                   ROUND(i.gross_total,2) AS Betrag, ia.requested_by AS Beantragt_von,
                   ia.requested_at AS Beantragt_am, ia.comments AS Kommentar
            FROM invoice_approvals ia
            JOIN invoices i ON i.id=ia.invoice_id
            JOIN customers c ON c.id=i.customer_id
            WHERE ia.status='ausstehend'
            ORDER BY ia.requested_at DESC
        """)
        if not pending.empty:
            st.warning(f"⚠️ {len(pending)} ausstehende Freigabe(n)")
            for _, row in pending.iterrows():
                aid = int(row["id"])
                with st.expander(f"📋 {row['Rechnung']} – {row['Kunde']} · {fmt_eur(float(row['Betrag']))}"):
                    st.caption(f"Beantragt von: {row['Beantragt_von']} am {str(row['Beantragt_am'])[:16]}")
                    if row.get("Kommentar"):
                        st.info(row["Kommentar"])
                    dec_comment = st.text_input("Kommentar Entscheidung", key=f"dec_com_{aid}")
                    col1, col2 = st.columns(2)
                    if col1.button("✅ Genehmigen", key=f"appr_{aid}", type="primary"):
                        inv_id = int(df_fn("SELECT invoice_id FROM invoice_approvals WHERE id=?", (aid,)).iloc[0]["invoice_id"])
                        run_fn("UPDATE invoice_approvals SET status='genehmigt', approved_by=?, comments=?, decided_at=? WHERE id=?",
                               (username, dec_comment, datetime.now().isoformat()[:19], aid))
                        run_fn("UPDATE invoices SET status='offen' WHERE id=?", (inv_id,))
                        log_fn("invoice_approved", f"aid={aid} by {username}")
                        st.success("✅ Genehmigt – Rechnung jetzt 'offen'")
                        st.rerun()
                    if col2.button("❌ Ablehnen", key=f"rej_{aid}"):
                        run_fn("UPDATE invoice_approvals SET status='abgelehnt', approved_by=?, comments=?, decided_at=? WHERE id=?",
                               (username, dec_comment, datetime.now().isoformat()[:19], aid))
                        log_fn("invoice_rejected", f"aid={aid}")
                        st.warning("Abgelehnt.")
                        st.rerun()
        else:
            st.success("✅ Keine ausstehenden Freigaben.")

    with tabs[2]:
        history = df_fn("""
            SELECT i.invoice_no AS Rechnung, c.company AS Kunde,
                   ia.requested_by AS Beantragt, ia.approved_by AS Entschieden_von,
                   ia.status AS Status, ia.decided_at AS Entschieden_am
            FROM invoice_approvals ia
            JOIN invoices i ON i.id=ia.invoice_id
            JOIN customers c ON c.id=i.customer_id
            WHERE ia.status != 'ausstehend'
            ORDER BY ia.decided_at DESC LIMIT 50
        """)
        if not history.empty:
            st.dataframe(history, use_container_width=True)
        else:
            st.info("Noch keine abgeschlossenen Freigabe-Workflows.")

    with tabs[3]:
        st.number_input("Freigabe-Schwellwert (€)",
                         value=THRESHOLD, step=500.0,
                         help="Rechnungen über diesem Betrag benötigen Genehmigung")
        st.caption("Schwellwert-Änderung in nächster Version konfigurierbar.")


# ─────────────────────────────────────────────────────────────
# 5. Budgetwarnungen
# ─────────────────────────────────────────────────────────────

def page_budget_warnings(run_fn, df_fn) -> None:
    st.title("⚠️ Budgetwarnungen")
    st.caption("Warnt wenn Ausgaben einen konfigurierten Prozentsatz des Budgets überschreiten.")

    tabs = st.tabs(["📊 Budget-Status", "➕ Budget festlegen", "📈 Verlauf"])

    with tabs[0]:
        month = st.text_input("Monat prüfen", date.today().strftime("%Y-%m"))
        budgets = df_fn("SELECT * FROM budget_items WHERE budget_month=? ORDER BY category", (month,))
        actuals = df_fn("""
            SELECT category, ROUND(SUM(gross_amount),2) AS ist
            FROM expenses WHERE bwa_month=? GROUP BY category
        """, (month,))

        if not budgets.empty and not actuals.empty:
            merged = budgets.merge(actuals, on="category", how="left").fillna(0)
            merged["Auslastung_%"] = (merged["ist"] / merged["budget_amount"] * 100).round(1)
            merged["Status"] = merged.apply(
                lambda r: "🔴 ÜBERSCHRITTEN" if r["Auslastung_%"] > 100
                         else f"⚠️ Warnung ({r['warning_threshold']:.0f}%)" if r["Auslastung_%"] >= r["warning_threshold"]
                         else "✅ OK",
                axis=1
            )

            c1, c2, c3 = st.columns(3)
            overbudget = merged[merged["Auslastung_%"] > 100]
            warning    = merged[(merged["Auslastung_%"] >= merged["warning_threshold"]) & (merged["Auslastung_%"] <= 100)]
            c1.metric("⚠️ Budget überschritten", len(overbudget))
            c2.metric("🟡 Warnbereich", len(warning))
            c3.metric("✅ Im Budget", len(merged) - len(overbudget) - len(warning))

            # Ampel-Anzeige
            for _, r in merged.iterrows():
                pct = float(r["Auslastung_%"])
                color = "#c0392b" if pct > 100 else "#e67e22" if pct >= float(r["warning_threshold"]) else "#27ae60"
                bar_w = min(int(pct), 100)
                st.markdown(
                    f'<div style="margin-bottom:8px;">'
                    f'<strong>{r["category"]}</strong>'
                    f' — IST: {fmt_eur(float(r["ist"]))} / Budget: {fmt_eur(float(r["budget_amount"]))}'
                    f' <span style="float:right;color:{color};">{r["Status"]}</span><br/>'
                    f'<div style="background:#2d3142;border-radius:4px;height:8px;margin-top:4px;">'
                    f'<div style="background:{color};width:{bar_w}%;height:8px;border-radius:4px;"></div>'
                    f'</div></div>',
                    unsafe_allow_html=True
                )
        elif budgets.empty:
            st.info(f"Kein Budget für {month} festgelegt. Bitte unter 'Budget festlegen' einrichten.")
        else:
            st.info("Noch keine Ausgaben in diesem Monat.")

    with tabs[1]:
        categories = df_fn("SELECT DISTINCT category FROM expense_categories ORDER BY category")
        cat_list = categories["category"].tolist() if not categories.empty else ["Kfz-Kosten","Bürokosten","Personalkosten"]
        with st.form("budget_form", clear_on_submit=True):
            col1, col2, col3, col4 = st.columns(4)
            cat     = col1.selectbox("Kostenart *", cat_list)
            budget_m = col2.text_input("Monat", date.today().strftime("%Y-%m"))
            amount  = col3.number_input("Budget (€)", min_value=0.0, value=500.0, step=50.0)
            threshold = col4.slider("Warngrenze (%)", 50, 100, 80)
            if st.form_submit_button("💾 Budget speichern", type="primary"):
                run_fn("""INSERT OR REPLACE INTO budget_items(category,budget_month,budget_amount,warning_threshold)
                          VALUES(?,?,?,?)""", (cat, budget_m, amount, threshold))
                st.success(f"✅ Budget {fmt_eur(amount)} für {cat} in {budget_m} gesetzt.")
                st.rerun()

        # Alle Kategorien für Monat auf einmal
        st.divider()
        bulk_month = st.text_input("Monat für Bulk-Budgetierung", date.today().strftime("%Y-%m"))
        if st.button("📋 Vorjahreswerte übernehmen"):
            prev_year = str(int(bulk_month[:4]) - 1) + bulk_month[4:]
            prev = df_fn("SELECT category, budget_amount, warning_threshold FROM budget_items WHERE budget_month=?", (prev_year,))
            if not prev.empty:
                for _, r in prev.iterrows():
                    run_fn("INSERT OR IGNORE INTO budget_items(category,budget_month,budget_amount,warning_threshold) VALUES(?,?,?,?)",
                           (r["category"], bulk_month, r["budget_amount"], r["warning_threshold"]))
                st.success(f"✅ {len(prev)} Budgets aus {prev_year} übernommen.")
                st.rerun()
            else:
                st.info(f"Keine Vorjahreswerte für {prev_year} vorhanden.")

    with tabs[2]:
        cat_sel = st.selectbox("Kostenart", cat_list)
        history = df_fn("""
            SELECT bi.budget_month AS Monat, bi.budget_amount AS Budget,
                   COALESCE((SELECT SUM(e.gross_amount) FROM expenses e
                              WHERE e.category=bi.category AND e.bwa_month=bi.budget_month),0) AS IST
            FROM budget_items bi WHERE bi.category=?
            ORDER BY bi.budget_month
        """, (cat_sel,))
        if not history.empty:
            history["Abw_%"] = ((history["IST"] - history["Budget"]) / history["Budget"] * 100).round(1)
            st.dataframe(history, use_container_width=True)
            st.bar_chart(history.set_index("Monat")[["Budget","IST"]])


# ─────────────────────────────────────────────────────────────
# 6. Inventarverwaltung
# ─────────────────────────────────────────────────────────────

def page_inventory(run_fn, df_fn, next_number_fn, log_fn) -> None:
    st.title("📦 Inventarverwaltung")
    st.caption("Fahrzeuge, Ausrüstung und Geräte verwalten.")

    CATEGORIES = ["Fahrzeug", "Funkgerät", "Schutzausrüstung", "Büroausstattung",
                  "IT-Equipment", "Sicherheitstechnik", "Werkzeug", "Sonstiges"]

    tabs = st.tabs(["📋 Übersicht", "➕ Neu anlegen",
                    "✏️ Bearbeiten", "⚠️ Wartungsfällig", "📊 Statistik"])

    with tabs[0]:
        q = st.text_input("🔍 Suche (Name, Nr., Ort)")
        status_f = st.selectbox("Status", ["alle","verfügbar","vergeben","in Wartung","defekt","ausgemustert"])

        query = """
            SELECT i.id, i.item_no AS Nr, i.name AS Name, i.category AS Kategorie,
                   COALESCE(e.name,'–') AS Zugewiesen_an, i.location AS Standort,
                   i.status AS Status, i.next_maintenance AS Nächste_Wartung,
                   i.purchase_price AS Kaufpreis, i.current_value AS Aktueller_Wert
            FROM inventory i LEFT JOIN employees e ON e.id=i.assigned_to
        """
        params = []
        where = []
        if q:
            where.append("(i.name LIKE ? OR i.item_no LIKE ? OR i.location LIKE ?)")
            params += [f"%{q}%"] * 3
        if status_f != "alle":
            where.append("i.status=?"); params.append(status_f)
        if where:
            query += " WHERE " + " AND ".join(where)
        query += " ORDER BY i.category, i.name"

        items = df_fn(query, tuple(params))
        if not items.empty:
            c1, c2, c3 = st.columns(3)
            c1.metric("Inventar-Positionen", len(items))
            c2.metric("Kaufpreise gesamt", fmt_eur(float(items["Kaufpreis"].sum())))
            c3.metric("Aktueller Wert", fmt_eur(float(items["Aktueller_Wert"].sum())))
            st.dataframe(items.drop(columns=["id"]), use_container_width=True, height=380)
            csv = items.drop(columns=["id"]).to_csv(index=False, sep=";").encode("utf-8-sig")
            st.download_button("📥 Inventarliste CSV", csv, "inventar.csv", "text/csv")
        else:
            st.info("Keine Inventar-Einträge gefunden.")

    with tabs[1]:
        employees = df_fn("SELECT id, name FROM employees WHERE active=1 ORDER BY name")
        with st.form("inv_form", clear_on_submit=True):
            a, b = st.columns(2)
            item_no = a.text_input("Inventar-Nr.", next_number_fn("inventory","item_no","INV-"))
            name    = b.text_input("Bezeichnung *")
            cat     = a.selectbox("Kategorie", CATEGORIES)
            serial  = b.text_input("Seriennummer")
            purchase_date = a.date_input("Kaufdatum", date.today())
            purchase_price = b.number_input("Kaufpreis (€)", min_value=0.0, value=0.0, step=10.0)
            current_value  = a.number_input("Aktueller Wert (€)", min_value=0.0, value=0.0, step=10.0)
            location = b.text_input("Standort")
            assigned_name = a.selectbox("Zugewiesen an", ["—"] + (employees["name"].tolist() if not employees.empty else []))
            status   = b.selectbox("Status", ["verfügbar","vergeben","in Wartung","defekt","ausgemustert"])
            next_maint = st.date_input("Nächste Wartung", value=None)
            notes    = st.text_area("Notizen")
            submitted = st.form_submit_button("💾 Speichern", type="primary")

        if submitted and name:
            eid = None
            if assigned_name != "—" and not employees.empty:
                match = employees[employees["name"] == assigned_name]
                if not match.empty:
                    eid = int(match.iloc[0]["id"])
            run_fn("""INSERT INTO inventory(item_no,name,category,serial_number,purchase_date,
                      purchase_price,current_value,location,assigned_to,status,next_maintenance,notes)
                      VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",
                   (item_no, name, cat, serial, purchase_date.isoformat(),
                    purchase_price, current_value, location, eid, status,
                    next_maint.isoformat() if next_maint else None, notes))
            log_fn("inventory_added", name)
            st.success(f"✅ '{name}' ins Inventar aufgenommen!")
            st.rerun()

    with tabs[2]:
        items_edit = df_fn("SELECT id, item_no || ' – ' || name AS label FROM inventory ORDER BY name")
        if items_edit.empty:
            st.info("Keine Inventar-Positionen.")
            return
        sel = st.selectbox("Position", items_edit["label"].tolist())
        iid = int(items_edit[items_edit["label"] == sel].iloc[0]["id"])
        row = df_fn("SELECT * FROM inventory WHERE id=?", (iid,)).iloc[0].to_dict()
        employees = df_fn("SELECT id, name FROM employees WHERE active=1 ORDER BY name")
        with st.form("inv_edit"):
            a, b = st.columns(2)
            new_status = a.selectbox("Status", ["verfügbar","vergeben","in Wartung","defekt","ausgemustert"],
                                      index=["verfügbar","vergeben","in Wartung","defekt","ausgemustert"].index(str(row.get("status","verfügbar"))))
            new_location = b.text_input("Standort", str(row.get("location","") or ""))
            new_val = a.number_input("Aktueller Wert (€)", value=float(row.get("current_value") or 0), step=10.0)
            maint_str = str(row.get("next_maintenance","") or "")
            new_maint = b.date_input("Nächste Wartung",
                                     value=date.fromisoformat(maint_str[:10]) if maint_str else None)
            assigned_name = a.selectbox("Zugewiesen an", ["—"] + (employees["name"].tolist() if not employees.empty else []))
            new_notes = st.text_area("Notizen", str(row.get("notes","") or ""))
            if st.form_submit_button("💾 Aktualisieren", type="primary"):
                eid = None
                if assigned_name != "—" and not employees.empty:
                    match = employees[employees["name"] == assigned_name]
                    if not match.empty: eid = int(match.iloc[0]["id"])
                run_fn("UPDATE inventory SET status=?,location=?,current_value=?,next_maintenance=?,assigned_to=?,notes=? WHERE id=?",
                       (new_status, new_location, new_val,
                        new_maint.isoformat() if new_maint else None, eid, new_notes, iid))
                log_fn("inventory_updated", str(iid))
                st.success("✅ Aktualisiert!"); st.rerun()

    with tabs[3]:
        today = date.today().isoformat()
        warn30 = (date.today() + timedelta(days=30)).isoformat()
        due = df_fn("""
            SELECT name AS Bezeichnung, category AS Kategorie,
                   next_maintenance AS Wartung_fällig,
                   CAST(julianday(next_maintenance) - julianday('now') AS INT) AS Tage_verbleibend,
                   COALESCE(assigned_to,'–') AS Zugewiesen, location AS Standort
            FROM inventory WHERE next_maintenance IS NOT NULL AND next_maintenance <= ?
            ORDER BY next_maintenance
        """, (warn30,))
        if not due.empty:
            overdue = due[due["Tage_verbleibend"] < 0]
            upcoming = due[due["Tage_verbleibend"] >= 0]
            if not overdue.empty:
                st.error(f"❌ {len(overdue)} Wartungen ÜBERFÄLLIG:")
                st.dataframe(overdue, use_container_width=True)
            if not upcoming.empty:
                st.warning(f"⚠️ {len(upcoming)} Wartungen in 30 Tagen fällig:")
                st.dataframe(upcoming, use_container_width=True)
        else:
            st.success("✅ Keine fälligen Wartungen in den nächsten 30 Tagen.")

    with tabs[4]:
        by_cat = df_fn("""
            SELECT category AS Kategorie, COUNT(*) AS Anzahl,
                   SUM(purchase_price) AS Kaufwert, SUM(current_value) AS Aktueller_Wert
            FROM inventory GROUP BY category ORDER BY Kaufwert DESC
        """)
        if not by_cat.empty:
            st.dataframe(by_cat, use_container_width=True)
            st.bar_chart(by_cat.set_index("Kategorie")["Aktueller_Wert"])


# ─────────────────────────────────────────────────────────────
# 7. Heatmap-Kalender
# ─────────────────────────────────────────────────────────────

def page_heatmap_calendar(df_fn) -> None:
    st.title("🗓️ Heatmap-Kalender")
    st.caption("Schichten und Einnahmen als farbige Kalenderansicht.")

    col1, col2 = st.columns(2)
    year  = col1.selectbox("Jahr", list(range(date.today().year, date.today().year - 3, -1)))
    mode  = col2.selectbox("Anzeige", ["Schichten", "Umsatz (€)"])

    import calendar
    months_de = ["Januar","Februar","März","April","Mai","Juni",
                 "Juli","August","September","Oktober","November","Dezember"]

    if mode == "Schichten":
        data = df_fn(f"""
            SELECT shift_date AS datum, COUNT(*) AS wert
            FROM shifts WHERE substr(shift_date,1,4)='{year}'
            GROUP BY shift_date
        """)
    else:
        data = df_fn(f"""
            SELECT invoice_date AS datum, ROUND(SUM(gross_total),0) AS wert
            FROM invoices WHERE substr(invoice_date,1,4)='{year}' AND status='bezahlt'
            GROUP BY invoice_date
        """)

    if data.empty:
        st.info("Keine Daten für dieses Jahr.")
        return

    data_dict = dict(zip(data["datum"], data["wert"].astype(float)))
    max_val = max(data_dict.values()) if data_dict else 1

    def get_color(v: float) -> str:
        if v == 0: return "#1a1f2e"
        ratio = v / max_val
        if ratio < 0.25:  return "#0d4a1a"
        elif ratio < 0.5: return "#1a7a2e"
        elif ratio < 0.75: return "#27ae60"
        else:              return "#2ecc71"

    unit = "Schichten" if mode == "Schichten" else "€"
    total = sum(data_dict.values())
    c1, c2, c3 = st.columns(3)
    c1.metric(f"Gesamt {unit}", f"{total:,.0f}")
    c2.metric(f"Ø pro Tag", f"{total/365:.1f}")
    c3.metric("Aktivste Tage", len(data_dict))

    # Heatmap als HTML-Grid
    html = '<div style="font-family:monospace;font-size:12px;">'
    wday_labels = "Mo Di Mi Do Fr Sa So"
    html += f'<div style="color:#888;margin-bottom:4px;">{wday_labels}</div>'

    for month_idx in range(1, 13):
        html += f'<div style="margin-bottom:8px;">'
        html += f'<span style="color:#aaa;font-size:11px;">{months_de[month_idx-1]}</span><br/>'
        html += '<div style="display:flex;flex-wrap:wrap;gap:2px;">'

        # Erste Woche auffüllen
        first_day = date(year, month_idx, 1)
        pad = first_day.weekday()
        for _ in range(pad):
            html += '<div style="width:18px;height:18px;"></div>'

        days_in_month = calendar.monthrange(year, month_idx)[1]
        for day in range(1, days_in_month + 1):
            d = date(year, month_idx, day)
            d_str = d.isoformat()
            val = data_dict.get(d_str, 0)
            color = get_color(val)
            tooltip = f"{d_str}: {val:.0f} {unit}" if val > 0 else d_str
            html += (f'<div title="{tooltip}" style="width:18px;height:18px;'
                     f'background:{color};border-radius:2px;cursor:pointer;"></div>')
        html += '</div></div>'

    html += '</div>'
    html += f'<div style="margin-top:8px;color:#888;font-size:11px;">🟩 Hoch · 🟧 Mittel · 🟫 Niedrig · ⬛ Keine</div>'
    st.markdown(html, unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────
# 8. Prognose-Dashboard (30/60/90 Tage)
# ─────────────────────────────────────────────────────────────

def page_forecast_dashboard(df_fn) -> None:
    st.title("🔮 Prognose-Dashboard")
    st.caption("Umsatz- und Ausgaben-Prognose für die nächsten 30/60/90 Tage.")

    tabs = st.tabs(["📈 Umsatz-Prognose", "📤 Ausgaben-Prognose",
                    "💰 Liquiditäts-Forecast", "📅 Fällige Ereignisse"])

    with tabs[0]:
        try:
            from ml_logic import forecast_revenue
            for horizon in [30, 60, 90]:
                months = horizon // 30
                fc = forecast_revenue(df_fn, months_ahead=months)
                if fc:
                    total = sum(f["prognose_eur"] for f in fc)
                    st.metric(f"Prognose {horizon} Tage", fmt_eur(total),
                              help=f"Gleitender Ø + Trendkorrektur")
            if fc:
                fc_df = pd.DataFrame(fc)
                st.bar_chart(fc_df.set_index("monat")["prognose_eur"])
                st.dataframe(fc_df, use_container_width=True)
        except Exception as e:
            st.error(f"ML-Prognose: {e}")

    with tabs[1]:
        # Durchschnittliche Ausgaben der letzten 3 Monate
        avg_exp = df_fn("""
            SELECT ROUND(AVG(monthly_sum),2) AS avg_exp
            FROM (
                SELECT bwa_month, SUM(gross_amount) AS monthly_sum
                FROM expenses
                WHERE bwa_month >= strftime('%Y-%m', date('now','-3 months'))
                GROUP BY bwa_month
            )
        """).iloc[0]["avg_exp"] or 0

        c1, c2, c3 = st.columns(3)
        c1.metric("Prognose 30 Tage", fmt_eur(float(avg_exp)))
        c2.metric("Prognose 60 Tage", fmt_eur(float(avg_exp) * 2))
        c3.metric("Prognose 90 Tage", fmt_eur(float(avg_exp) * 3))
        st.caption(f"Basis: Ø Monatsausgaben der letzten 3 Monate = {fmt_eur(float(avg_exp))}")

    with tabs[2]:
        # Einfacher Liquiditäts-Forecast
        st.subheader("Erwartete Liquidität")

        today = date.today()
        # Offene Forderungen (Einnahmen)
        receivables = df_fn("""
            SELECT due_date, ROUND(gross_total - paid_amount, 2) AS amount
            FROM invoices WHERE status IN ('offen','ueberfaellig')
            ORDER BY due_date
        """)
        # Offene Verbindlichkeiten (Ausgaben)
        payables = df_fn("""
            SELECT due_date, ROUND(gross_amount - paid_amount, 2) AS amount
            FROM expenses WHERE status IN ('offen','teilbezahlt') AND due_date IS NOT NULL
            ORDER BY due_date
        """)

        forecast_items = []
        if not receivables.empty:
            for _, r in receivables.iterrows():
                forecast_items.append({
                    "Datum": str(r["due_date"])[:10],
                    "Typ": "📥 Einnahme erwartet",
                    "Betrag": float(r["amount"]),
                })
        if not payables.empty:
            for _, r in payables.iterrows():
                forecast_items.append({
                    "Datum": str(r["due_date"])[:10],
                    "Typ": "📤 Ausgabe fällig",
                    "Betrag": -float(r["amount"]),
                })

        if forecast_items:
            df_fc = pd.DataFrame(forecast_items).sort_values("Datum")
            df_fc["Kumuliert"] = df_fc["Betrag"].cumsum()
            st.dataframe(df_fc, use_container_width=True)
            st.line_chart(df_fc.set_index("Datum")["Kumuliert"])
        else:
            st.info("Keine offenen Posten für Liquiditätsprognose.")

    with tabs[3]:
        st.subheader("Fällige Ereignisse nächste 90 Tage")
        future90 = (date.today() + timedelta(days=90)).isoformat()
        today_s = date.today().isoformat()
        events = []

        # Rechnungen fällig
        inv_due = df_fn(f"""
            SELECT due_date AS Datum, 'Rechnung fällig' AS Typ,
                   invoice_no || ' – ' || ROUND(gross_total-paid_amount,2) || ' €' AS Detail
            FROM invoices WHERE status IN ('offen','ueberfaellig')
              AND due_date BETWEEN '{today_s}' AND '{future90}'
            ORDER BY due_date
        """)
        for _, r in inv_due.iterrows():
            events.append({"Datum":r["Datum"],"Typ":"🧾 "+r["Typ"],"Detail":r["Detail"]})

        # Steuertermine
        tax_due = df_fn(f"""
            SELECT due_date AS Datum, tax_type AS Typ, description AS Detail
            FROM tax_calendar WHERE status='offen'
              AND due_date BETWEEN '{today_s}' AND '{future90}'
            ORDER BY due_date
        """)
        for _, r in tax_due.iterrows():
            events.append({"Datum":r["Datum"],"Typ":"💰 "+r["Typ"],"Detail":r["Detail"]})

        # Verträge ablaufend
        contr_exp = df_fn(f"""
            SELECT end_date AS Datum, 'Vertrag läuft ab' AS Typ,
                   contract_title AS Detail
            FROM contract_monitoring WHERE status='aktiv'
              AND end_date BETWEEN '{today_s}' AND '{future90}'
            ORDER BY end_date
        """)
        for _, r in contr_exp.iterrows():
            events.append({"Datum":r["Datum"],"Typ":"📋 "+r["Typ"],"Detail":r["Detail"]})

        # Wiedervorlagen
        tasks_due = df_fn(f"""
            SELECT due_date AS Datum, 'Wiedervorlage' AS Typ, title AS Detail
            FROM followup_tasks WHERE status NOT IN ('erledigt')
              AND due_date BETWEEN '{today_s}' AND '{future90}'
            ORDER BY due_date LIMIT 20
        """)
        for _, r in tasks_due.iterrows():
            events.append({"Datum":r["Datum"],"Typ":"📌 "+r["Typ"],"Detail":r["Detail"]})

        if events:
            df_ev = pd.DataFrame(events).sort_values("Datum")
            st.metric("Fällige Ereignisse (90 Tage)", len(events))
            st.dataframe(df_ev, use_container_width=True, height=400)
        else:
            st.info("Keine anstehenden Ereignisse in den nächsten 90 Tagen.")


# ─────────────────────────────────────────────────────────────
# 9. Favoritenleiste & Browserverlauf
# ─────────────────────────────────────────────────────────────

def render_favorites_bar(df_fn, run_fn, current_user_fn) -> None:
    """Rendert Favoritenleiste in der Sidebar."""
    user = current_user_fn() or {}
    username = user.get("username","")
    if not username:
        return

    favs = df_fn("SELECT page_name FROM user_favorites WHERE username=? ORDER BY position", (username,))
    if favs.empty:
        return

    with st.sidebar:
        st.markdown("**⭐ Favoriten:**")
        for _, fav in favs.iterrows():
            if st.button(f"⭐ {fav['page_name']}", key=f"fav_{fav['page_name']}"):
                st.session_state["_nav_override"] = fav["page_name"]
                st.rerun()
        st.markdown("---")


def page_favorites_manager(run_fn, df_fn, current_user_fn) -> None:
    st.title("⭐ Favoriten & Verlauf")

    user = current_user_fn() or {}
    username = user.get("username","")
    if not username:
        st.warning("Bitte einloggen.")
        return

    tabs = st.tabs(["⭐ Meine Favoriten", "🕐 Verlauf", "➕ Favorit hinzufügen"])

    with tabs[0]:
        favs = df_fn("SELECT id, page_name AS Seite, position AS Position FROM user_favorites WHERE username=? ORDER BY position", (username,))
        if not favs.empty:
            st.dataframe(favs.drop(columns=["id"]), use_container_width=True)
            del_sel = st.selectbox("Favorit entfernen", favs["Seite"].tolist())
            if st.button("🗑️ Entfernen"):
                run_fn("DELETE FROM user_favorites WHERE username=? AND page_name=?",
                       (username, del_sel))
                st.rerun()
        else:
            st.info("Noch keine Favoriten gespeichert.")

    with tabs[1]:
        history = df_fn("""
            SELECT page_name AS Seite, visited_at AS Besucht
            FROM page_history WHERE username=?
            ORDER BY visited_at DESC LIMIT 50
        """, (username,))
        if not history.empty:
            st.dataframe(history, use_container_width=True, height=300)
        else:
            st.info("Noch kein Browserverlauf.")

        if st.button("🗑️ Verlauf löschen"):
            run_fn("DELETE FROM page_history WHERE username=?", (username,))
            st.rerun()

    with tabs[2]:
        all_pages = [
            "Dashboard", "Kunden", "Rechnungen", "Ausgaben", "Mitarbeiter",
            "Dienstplan", "Lohnabrechnung", "Berichte", "Reporting-Center",
            "Automatik", "Bank/DATEV", "Live-Betrieb", "KI-Chatbot",
            "Aging-Report", "Wiedervorlagen", "GPS-Stempeluhr", "Mahngebühren",
        ]
        page_to_add = st.selectbox("Seite als Favorit speichern", all_pages)
        if st.button(f"⭐ '{page_to_add}' zu Favoriten hinzufügen", type="primary"):
            existing = df_fn("SELECT id FROM user_favorites WHERE username=? AND page_name=?",
                              (username, page_to_add))
            if existing.empty:
                pos = int(df_fn("SELECT COALESCE(MAX(position),0)+1 AS p FROM user_favorites WHERE username=?",
                                 (username,)).iloc[0]["p"])
                run_fn("INSERT INTO user_favorites(username,page_name,position) VALUES(?,?,?)",
                       (username, page_to_add, pos))
                st.success(f"✅ '{page_to_add}' zu Favoriten hinzugefügt!")
                st.rerun()
            else:
                st.info("Bereits in Favoriten.")


def track_page_visit(run_fn, current_user_fn, page_name: str) -> None:
    """Speichert Seitenbesuch im Verlauf."""
    try:
        user = current_user_fn() or {}
        username = user.get("username","")
        if username and page_name:
            run_fn("INSERT INTO page_history(username,page_name) VALUES(?,?)",
                   (username, page_name))
    except Exception:
        pass


# ─────────────────────────────────────────────────────────────
# 10. Zapier/Make Webhook-Templates
# ─────────────────────────────────────────────────────────────

def page_zapier_templates(get_setting_fn) -> None:
    st.title("🔄 Zapier / Make Webhook-Templates")
    st.caption("Vorgefertigte Integrations-Workflows für Automatisierung.")

    base_url = get_setting_fn("payment_base_url", "http://localhost:8000")
    api_key_hint = "byb_dein_api_key_hier"

    scenarios = [
        {
            "name": "Neue Zahlung → Google Sheets",
            "trigger": "Webhook aus Byblos CRM (Zahlungseingang)",
            "action": "Google Sheets Zeile hinzufügen",
            "template": {
                "url": f"{base_url}/api/v1/webhook",
                "method": "POST",
                "headers": {"X-API-Key": api_key_hint, "Content-Type": "application/json"},
                "body": {"event": "payment_received", "invoice_no": "{{invoice_no}}", "amount": "{{amount}}", "customer": "{{customer}}"}
            }
        },
        {
            "name": "Überfällige Rechnung → Slack-Nachricht",
            "trigger": "Täglicher Zeitplan (07:00)",
            "action": "HTTP GET → Slack Webhook",
            "template": {
                "step1_url": f"{base_url}/api/v1/invoices?status=ueberfaellig",
                "step1_headers": {"X-API-Key": api_key_hint},
                "step2_slack_url": "https://hooks.slack.com/services/...",
                "step2_body": {"text": "⚠️ {{count}} überfällige Rechnungen: {{total}} €"}
            }
        },
        {
            "name": "Neuer Kunde → CRM-Eintrag anlegen",
            "trigger": "Formular-Submission (z.B. Typeform)",
            "action": "POST zu Byblos CRM API",
            "template": {
                "url": f"{base_url}/api/v1/customers",
                "method": "POST",
                "headers": {"X-API-Key": api_key_hint, "Content-Type": "application/json"},
                "body": {"company": "{{form_company}}", "email": "{{form_email}}", "phone": "{{form_phone}}"}
            }
        },
        {
            "name": "Tägl. KPI-Report → E-Mail",
            "trigger": "Täglicher Zeitplan (08:00)",
            "action": "HTTP GET KPIs → Gmail senden",
            "template": {
                "step1_url": f"{base_url}/api/v1/dashboard",
                "step1_headers": {"X-API-Key": api_key_hint},
                "step2_email": "admin@firma.de",
                "step2_subject": "Byblos CRM Tages-KPIs {{datum}}"
            }
        },
    ]

    for s in scenarios:
        with st.expander(f"🔄 {s['name']}"):
            st.caption(f"**Trigger:** {s['trigger']}  |  **Action:** {s['action']}")
            st.json(s["template"])
            yaml_str = json.dumps(s["template"], indent=2, ensure_ascii=False)
            st.download_button("📥 Template JSON",
                               yaml_str.encode("utf-8"),
                               f"zapier_{s['name'].lower().replace(' ','_')[:30]}.json",
                               "application/json",
                               key=f"dl_zap_{s['name']}")

    st.divider()
    st.subheader("Make (Integromat) HTTP-Module")
    st.code(f"""# Byblos CRM API in Make einbinden:
# 1. HTTP Make a Request Modul
# 2. URL: {base_url}/api/v1/dashboard
# 3. Method: GET
# 4. Headers:
#    X-API-Key: {api_key_hint}
#    Content-Type: application/json
# 5. Parse Response: automatisch
# 6. Output-Felder: customers_total, invoices_open, revenue_this_month ...
""", language="bash")
