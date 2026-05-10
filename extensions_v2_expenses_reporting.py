"""
extensions_v2_expenses_reporting.py – Ausgaben v2 + PDF-Reporting
==================================================================
Enthält:
  1. Vollständige Ausgabenverwaltung v2 (Bearbeiten, Löschen, KI-Kategorisierung)
  2. Detaillierte BWA-Auswertung mit Trend
  3. PDF-Monatsbericht
  4. Quartalsbericht
  5. Jahres-GuV-Zusammenfassung
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd
import streamlit as st


def fmt_eur(v: float) -> str:
    return f"{v:,.2f} €".replace(",", "X").replace(".", ",").replace("X", ".")


# ─────────────────────────────────────────────────────────────
# 1. Ausgabenverwaltung v2
# ─────────────────────────────────────────────────────────────

def page_expenses_v2(run_fn, df_fn, next_number_fn, log_fn,
                     save_receipt_fn, refresh_fn,
                     bwa_categories, expense_payment) -> None:
    st.title("📤 Ausgaben & BWA")

    tabs = st.tabs([
        "📋 Übersicht", "➕ Ausgabe erfassen",
        "✏️ Bearbeiten / Zahlung", "📊 BWA-Auswertung",
        "📈 Trend-Analyse", "📤 Steuerberater-Export"
    ])

    # ── Tab 0: Übersicht ──────────────────────────────────────
    with tabs[0]:
        col_s, col_f1, col_f2 = st.columns([3, 1, 1])
        q = col_s.text_input("🔍 Suche (Beschreibung, Lieferant, Kostenart)")
        status_f = col_f1.selectbox("Status", ["alle", "offen", "teilbezahlt", "bezahlt"])
        month_f  = col_f2.text_input("Monat (YYYY-MM)", "")

        base_q = """
            SELECT e.id, e.expense_no AS Nr, e.expense_date AS Datum,
                   e.bwa_month AS BWA_Monat,
                   COALESCE(s.name,'–') AS Lieferant,
                   e.description AS Beschreibung, e.category AS Kostenart,
                   e.net_amount AS Netto, e.vat_rate AS MwSt_Pct,
                   e.vat_amount AS Vorsteuer, e.gross_amount AS Brutto,
                   e.paid_amount AS Bezahlt,
                   ROUND(e.gross_amount - e.paid_amount, 2) AS Offen,
                   e.status AS Status, e.payment_method AS Zahlungsart
            FROM expenses e LEFT JOIN suppliers s ON s.id=e.supplier_id
        """
        where, params = [], []
        if q:
            where.append("(e.description LIKE ? OR s.name LIKE ? OR e.category LIKE ?)")
            params += [f"%{q}%"] * 3
        if status_f != "alle":
            where.append("e.status = ?"); params.append(status_f)
        if month_f:
            where.append("e.bwa_month = ?"); params.append(month_f)
        w = ("WHERE " + " AND ".join(where)) if where else ""
        data = df_fn(base_q + w + " ORDER BY e.expense_date DESC", tuple(params))

        if not data.empty:
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Belege", len(data))
            c2.metric("Brutto gesamt", fmt_eur(float(data["Brutto"].sum())))
            c3.metric("Bezahlt", fmt_eur(float(data["Bezahlt"].sum())))
            c4.metric("Offen", fmt_eur(float(data["Offen"].sum())))
            st.dataframe(data.drop(columns=["id"]), use_container_width=True, height=380)
            csv = data.drop(columns=["id"]).to_csv(index=False, sep=";").encode("utf-8-sig")
            st.download_button("📥 CSV-Export", csv, "ausgaben_export.csv", "text/csv")
        else:
            st.info("Keine Ausgaben gefunden.")

    # ── Tab 1: Erfassen ───────────────────────────────────────
    with tabs[1]:
        suppliers = df_fn("SELECT id, name FROM suppliers ORDER BY name")
        categories = df_fn("SELECT category FROM expense_categories ORDER BY category")
        cat_list = categories["category"].tolist() if not categories.empty else bwa_categories

        with st.form("expense_v2_form", clear_on_submit=True):
            a, b, c = st.columns(3)
            expense_no  = a.text_input("Ausgaben-Nr.", next_number_fn("expenses", "expense_no", "AUS-"))
            receipt_no  = b.text_input("Beleg-/Rechnungsnummer")
            expense_date = c.date_input("Belegdatum", date.today())

            d, e, f = st.columns(3)
            sup_names = suppliers["name"].tolist() if not suppliers.empty else []
            supplier_name = d.selectbox("Lieferant", ["—"] + sup_names)
            category = e.selectbox("BWA-Kostenart *", cat_list)
            payment_method = f.selectbox("Zahlungsart", expense_payment if expense_payment else
                                         ["Überweisung", "Bar", "Karte", "SEPA", "Sonstiges"])
            description = st.text_input("Beschreibung *")

            a2, b2, c2, d2 = st.columns(4)
            net_amount  = a2.number_input("Netto (€)", min_value=0.0, value=0.0, step=10.0)
            vat_rate    = b2.number_input("MwSt %", min_value=0.0, value=19.0, step=1.0)
            paid_amount = c2.number_input("Bezahlt (€)", min_value=0.0, value=0.0, step=10.0)
            due_date    = d2.date_input("Fällig bis", date.today() + timedelta(days=30))

            paid_date = st.date_input("Bezahlt am (leer = offen)", value=None)
            notes     = st.text_area("Notizen / Verwendungszweck")
            receipt   = st.file_uploader("Beleg hochladen (PDF/JPG/PNG)",
                                          type=["pdf", "jpg", "jpeg", "png"])

            # KI-Vorschlag
            if description:
                try:
                    from ml_logic import predict_category
                    cat_ai, conf_ai = predict_category(description)
                    st.info(f"🤖 KI-Vorschlag: **{cat_ai}** ({conf_ai:.0f}%)")
                except Exception:
                    pass

            submitted = st.form_submit_button("💾 Ausgabe speichern", type="primary")

        if submitted:
            if not description.strip():
                st.error("Beschreibung ist Pflichtfeld.")
            elif net_amount <= 0:
                st.error("Netto-Betrag muss größer als 0 sein.")
            else:
                sid = None
                if supplier_name != "—" and not suppliers.empty:
                    match = suppliers[suppliers["name"] == supplier_name]
                    if not match.empty:
                        sid = int(match.iloc[0]["id"])
                vat_amount   = round(net_amount * vat_rate / 100, 2)
                gross_amount = round(net_amount + vat_amount, 2)
                if paid_amount <= 0:
                    status = "offen"
                elif paid_amount < gross_amount - 0.01:
                    status = "teilbezahlt"
                else:
                    status = "bezahlt"
                receipt_path = save_receipt_fn(receipt) if receipt else ""
                bwa_month = expense_date.strftime("%Y-%m")

                run_fn("""INSERT INTO expenses(expense_no,receipt_no,supplier_id,expense_date,due_date,paid_date,
                          description,category,net_amount,vat_rate,vat_amount,gross_amount,paid_amount,
                          payment_method,status,receipt_path,bwa_month,notes)
                          VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                       (expense_no, receipt_no, sid, expense_date.isoformat(), due_date.isoformat(),
                        paid_date.isoformat() if paid_date else None, description, category,
                        net_amount, vat_rate, vat_amount, gross_amount, paid_amount,
                        payment_method, status, receipt_path, bwa_month, notes))
                log_fn("expense_created", f"{expense_no} {description}")
                st.success(f"✅ Ausgabe {expense_no} gespeichert!")
                st.rerun()

    # ── Tab 2: Bearbeiten / Zahlung ───────────────────────────
    with tabs[2]:
        expenses_list = df_fn("""
            SELECT e.id, e.expense_no || ' – ' || e.description || ' (' || e.expense_date || ')' AS label,
                   e.gross_amount, e.paid_amount, e.status
            FROM expenses e ORDER BY e.expense_date DESC LIMIT 200
        """)
        if expenses_list.empty:
            st.info("Keine Ausgaben vorhanden.")
            return

        sel = st.selectbox("Ausgabe auswählen", expenses_list["label"].tolist())
        eid = int(expenses_list[expenses_list["label"] == sel].iloc[0]["id"])
        row = df_fn("SELECT * FROM expenses WHERE id=?", (eid,)).iloc[0].to_dict()
        suppliers = df_fn("SELECT id, name FROM suppliers ORDER BY name")
        categories = df_fn("SELECT category FROM expense_categories ORDER BY category")
        cat_list = categories["category"].tolist() if not categories.empty else bwa_categories

        with st.form("expense_edit_v2"):
            a, b = st.columns(2)
            expense_no_e  = a.text_input("Nr.", str(row.get("expense_no", "")))
            expense_date_e = b.text_input("Datum", str(row.get("expense_date", "")))
            desc_e = st.text_input("Beschreibung", str(row.get("description", "")))

            cur_cat = str(row.get("category", ""))
            cat_idx = cat_list.index(cur_cat) if cur_cat in cat_list else 0
            cat_e = st.selectbox("Kostenart", cat_list, index=cat_idx)

            a2, b2, c2 = st.columns(3)
            net_e  = a2.number_input("Netto", value=float(row.get("net_amount") or 0), step=10.0)
            vat_e  = b2.number_input("MwSt %", value=float(row.get("vat_rate") or 19), step=1.0)
            notes_e = st.text_area("Notizen", str(row.get("notes") or ""))

            status_opts = ["offen", "teilbezahlt", "bezahlt"]
            cur_status = str(row.get("status", "offen"))
            status_e = c2.selectbox("Status", status_opts,
                                    index=status_opts.index(cur_status) if cur_status in status_opts else 0)
            save = st.form_submit_button("💾 Speichern", type="primary")

        if save and desc_e:
            vat_amt_e = round(net_e * vat_e / 100, 2)
            gross_e   = round(net_e + vat_amt_e, 2)
            run_fn("""UPDATE expenses SET expense_no=?,expense_date=?,description=?,category=?,
                      net_amount=?,vat_rate=?,vat_amount=?,gross_amount=?,status=?,notes=?
                      WHERE id=?""",
                   (expense_no_e, expense_date_e, desc_e, cat_e,
                    net_e, vat_e, vat_amt_e, gross_e, status_e, notes_e, eid))
            log_fn("expense_updated", f"id={eid}")
            st.success("✅ Ausgabe aktualisiert!")
            st.rerun()

        # Zahlung buchen
        st.divider()
        st.subheader("💳 Zahlung buchen")
        gross = float(expenses_list[expenses_list["label"] == sel].iloc[0]["gross_amount"])
        paid  = float(expenses_list[expenses_list["label"] == sel].iloc[0]["paid_amount"])
        offen = round(gross - paid, 2)
        c1, c2 = st.columns(2)
        c1.metric("Offen", fmt_eur(offen))

        with st.form("expense_pay_v2"):
            a, b = st.columns(2)
            pay_amt  = a.number_input("Zahlbetrag (€)", min_value=0.01, value=offen, step=10.0)
            pay_date = b.date_input("Zahlungsdatum", date.today())
            full_pay = st.checkbox("Vollständig beglichen", value=abs(pay_amt - offen) < 0.02)
            if st.form_submit_button("💾 Zahlung buchen", type="primary") and offen > 0:
                run_fn("UPDATE expenses SET paid_amount=COALESCE(paid_amount,0)+?, paid_date=? WHERE id=?",
                       (pay_amt, pay_date.isoformat(), eid))
                if full_pay:
                    run_fn("UPDATE expenses SET status='bezahlt' WHERE id=?", (eid,))
                refresh_fn(eid)
                log_fn("expense_payment", f"id={eid} amt={pay_amt}")
                st.success(f"✅ Zahlung {fmt_eur(pay_amt)} gebucht!")
                st.rerun()

        # Beleg anzeigen
        receipt_p = str(row.get("receipt_path") or "")
        if receipt_p and Path(receipt_p).exists():
            st.divider()
            st.subheader("📎 Beleg")
            if receipt_p.lower().endswith(".pdf"):
                st.download_button("📥 Beleg herunterladen", Path(receipt_p).read_bytes(),
                                   file_name=Path(receipt_p).name, mime="application/pdf")
            else:
                try:
                    st.image(receipt_p, caption="Beleg", use_container_width=True)
                except Exception:
                    st.download_button("📥 Beleg herunterladen", Path(receipt_p).read_bytes(),
                                       file_name=Path(receipt_p).name)

        # Löschen
        st.divider()
        if str(row.get("status")) == "offen":
            if st.button("🗑️ Ausgabe löschen"):
                run_fn("DELETE FROM expenses WHERE id=?", (eid,))
                log_fn("expense_deleted", f"id={eid}")
                st.success("Gelöscht.")
                st.rerun()
        else:
            st.caption("Bezahlte/gebuchte Ausgaben können nicht gelöscht werden.")

    # ── Tab 3: BWA-Auswertung ─────────────────────────────────
    with tabs[3]:
        st.subheader("BWA-Monatsauswertung")
        col1, col2 = st.columns(2)
        month = col1.text_input("Monat (YYYY-MM)", date.today().strftime("%Y-%m"))
        show_detail = col2.checkbox("Detailansicht je Kostenart", value=True)

        # Kosten je Kategorie
        summary = df_fn("""
            SELECT category AS Kostenart, COUNT(*) AS Belege,
                   SUM(net_amount) AS Netto, SUM(vat_amount) AS Vorsteuer,
                   SUM(gross_amount) AS Brutto, SUM(paid_amount) AS Bezahlt,
                   ROUND(SUM(gross_amount)-SUM(paid_amount),2) AS Offen
            FROM expenses WHERE bwa_month=?
            GROUP BY category ORDER BY Brutto DESC
        """, (month,))

        # Umsatz des Monats
        revenue_paid = float(df_fn("""
            SELECT COALESCE(SUM(gross_total),0) AS v FROM invoices
            WHERE substr(invoice_date,1,7)=? AND status='bezahlt'
        """, (month,)).iloc[0]["v"])
        revenue_all = float(df_fn("""
            SELECT COALESCE(SUM(gross_total),0) AS v FROM invoices
            WHERE substr(invoice_date,1,7)=?
        """, (month,)).iloc[0]["v"])

        gross_exp = float(summary["Brutto"].sum()) if not summary.empty else 0.0
        net_exp   = float(summary["Netto"].sum()) if not summary.empty else 0.0
        vst       = float(summary["Vorsteuer"].sum()) if not summary.empty else 0.0

        # KPI-Zeile
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Umsatz (bezahlt)", fmt_eur(revenue_paid))
        c2.metric("Ausgaben (brutto)", fmt_eur(gross_exp))
        c3.metric("Vorsteuer", fmt_eur(vst))
        c4.metric("BWA-Ergebnis", fmt_eur(revenue_paid - gross_exp),
                  "positiv ✅" if revenue_paid > gross_exp else "negativ ⚠️")

        if not summary.empty:
            if show_detail:
                st.dataframe(summary, use_container_width=True)
            st.bar_chart(summary.set_index("Kostenart")["Brutto"])

        st.warning("⚠️ Operative Auswertung – keine steuerliche Beratung. Bitte mit Steuerberater abstimmen.")

    # ── Tab 4: Trend-Analyse ──────────────────────────────────
    with tabs[4]:
        st.subheader("Kostenentwicklung (letzte 12 Monate)")
        trend = df_fn("""
            SELECT bwa_month AS Monat, category AS Kostenart,
                   SUM(gross_amount) AS Brutto
            FROM expenses
            WHERE bwa_month >= strftime('%Y-%m', date('now','-12 months'))
            GROUP BY bwa_month, category
            ORDER BY bwa_month
        """)
        if not trend.empty:
            pivot = trend.pivot_table(
                index="Monat", columns="Kostenart", values="Brutto", fill_value=0
            )
            st.line_chart(pivot)
            st.dataframe(pivot, use_container_width=True)

        # Umsatz vs. Ausgaben
        st.subheader("Umsatz vs. Ausgaben (12 Monate)")
        rev_trend = df_fn("""
            SELECT substr(invoice_date,1,7) AS Monat, SUM(gross_total) AS Umsatz
            FROM invoices WHERE status='bezahlt'
                AND invoice_date >= date('now','-12 months')
            GROUP BY substr(invoice_date,1,7) ORDER BY Monat
        """)
        exp_trend = df_fn("""
            SELECT bwa_month AS Monat, SUM(gross_amount) AS Ausgaben
            FROM expenses
            WHERE bwa_month >= strftime('%Y-%m', date('now','-12 months'))
            GROUP BY bwa_month ORDER BY Monat
        """)
        if not rev_trend.empty and not exp_trend.empty:
            merged = rev_trend.merge(exp_trend, on="Monat", how="outer").fillna(0)
            merged["Ergebnis"] = merged["Umsatz"] - merged["Ausgaben"]
            st.bar_chart(merged.set_index("Monat")[["Umsatz", "Ausgaben"]])
            st.line_chart(merged.set_index("Monat")[["Ergebnis"]])

    # ── Tab 5: Steuerberater-Export ───────────────────────────
    with tabs[5]:
        st.subheader("Export für BWA / Steuerberater")
        col1, col2 = st.columns(2)
        from_month = col1.text_input("Von Monat", (date.today().replace(day=1) - timedelta(days=90)).strftime("%Y-%m"))
        to_month   = col2.text_input("Bis Monat", date.today().strftime("%Y-%m"))

        export_q = """
            SELECT e.expense_date AS Belegdatum, e.bwa_month AS BWA_Monat,
                   e.expense_no AS AusgabenNr, e.receipt_no AS BelegNr,
                   COALESCE(s.name,'') AS Lieferant, e.description AS Buchungstext,
                   e.category AS Kostenart, e.net_amount AS Netto,
                   e.vat_rate AS MwSt_Pct, e.vat_amount AS Vorsteuer,
                   e.gross_amount AS Brutto, e.paid_amount AS Bezahlt,
                   e.status AS Status, e.payment_method AS Zahlungsart, e.notes AS Notiz
            FROM expenses e LEFT JOIN suppliers s ON s.id=e.supplier_id
            WHERE e.bwa_month BETWEEN ? AND ?
            ORDER BY e.expense_date
        """
        export_data = df_fn(export_q, (from_month, to_month))

        if not export_data.empty:
            c1, c2, c3 = st.columns(3)
            c1.metric("Belege", len(export_data))
            c2.metric("Netto gesamt", fmt_eur(float(export_data["Netto"].sum())))
            c3.metric("Brutto gesamt", fmt_eur(float(export_data["Brutto"].sum())))
            st.dataframe(export_data, use_container_width=True, height=300)

            col1, col2 = st.columns(2)
            csv_data = export_data.to_csv(index=False, sep=";").encode("utf-8-sig")
            col1.download_button("📥 CSV-Export",
                                 csv_data, f"ausgaben_{from_month}_{to_month}.csv", "text/csv")
            try:
                import openpyxl
                from io import BytesIO
                buf = BytesIO()
                with pd.ExcelWriter(buf, engine="openpyxl") as writer:
                    export_data.to_excel(writer, sheet_name="Ausgaben_BWA", index=False)
                    # BWA-Zusammenfassung
                    summary_e = df_fn("""
                        SELECT category AS Kostenart, SUM(net_amount) AS Netto,
                               SUM(vat_amount) AS Vorsteuer, SUM(gross_amount) AS Brutto
                        FROM expenses WHERE bwa_month BETWEEN ? AND ?
                        GROUP BY category ORDER BY Brutto DESC
                    """, (from_month, to_month))
                    if not summary_e.empty:
                        summary_e.to_excel(writer, sheet_name="BWA_Zusammenfassung", index=False)
                buf.seek(0)
                col2.download_button("📊 Excel-Export",
                                     buf.read(), f"byblos_bwa_{from_month}_{to_month}.xlsx",
                                     "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
            except Exception as ex:
                col2.warning(f"Excel nicht verfügbar: {ex}")
        else:
            st.info("Keine Ausgaben im gewählten Zeitraum.")


# ─────────────────────────────────────────────────────────────
# 2. Reporting-Center
# ─────────────────────────────────────────────────────────────

def page_reporting_center(run_fn, df_fn, base_dir: Path) -> None:
    """Zentrales Reporting mit Download-Berichten."""
    st.title("📑 Reporting-Center")

    tabs = st.tabs([
        "📅 Monatsbericht", "📊 Quartalsbericht",
        "📈 Jahres-GuV", "👥 Kunden-Ranking",
        "👷 Mitarbeiter-Report"
    ])

    # ── Monatsbericht ─────────────────────────────────────────
    with tabs[0]:
        st.subheader("Monatsbericht")
        col1, col2 = st.columns(2)
        year  = col1.selectbox("Jahr", list(range(date.today().year, date.today().year - 5, -1)))
        month_num = col2.selectbox("Monat", list(range(1, 13)),
                                   index=date.today().month - 1,
                                   format_func=lambda m: ["Jan","Feb","Mär","Apr","Mai","Jun",
                                                           "Jul","Aug","Sep","Okt","Nov","Dez"][m-1])
        month_str = f"{year}-{month_num:02d}"

        inv_m = df_fn("""
            SELECT i.invoice_no AS Nr, c.company AS Kunde, i.invoice_date AS Datum,
                   i.gross_total AS Brutto, i.paid_amount AS Bezahlt, i.status AS Status
            FROM invoices i JOIN customers c ON c.id=i.customer_id
            WHERE substr(i.invoice_date,1,7)=? ORDER BY i.invoice_date
        """, (month_str,))
        exp_m = df_fn("""
            SELECT e.expense_no AS Nr, COALESCE(s.name,'–') AS Lieferant,
                   e.expense_date AS Datum, e.gross_amount AS Brutto,
                   e.category AS Kostenart, e.status AS Status
            FROM expenses e LEFT JOIN suppliers s ON s.id=e.supplier_id
            WHERE e.bwa_month=? ORDER BY e.expense_date
        """, (month_str,))
        shifts_m = df_fn("""
            SELECT COUNT(*) AS Schichten,
                   SUM(CASE WHEN employee_id IS NULL THEN 1 ELSE 0 END) AS Unbesetzt
            FROM shifts WHERE substr(shift_date,1,7)=?
        """, (month_str,))

        rev_paid = float(inv_m[inv_m["Status"]=="bezahlt"]["Brutto"].sum()) if not inv_m.empty else 0
        rev_all  = float(inv_m["Brutto"].sum()) if not inv_m.empty else 0
        exp_all  = float(exp_m["Brutto"].sum()) if not exp_m.empty else 0
        result   = rev_paid - exp_all

        st.markdown(f"### 📅 Bericht für {month_str}")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Umsatz fakturiert", fmt_eur(rev_all))
        c2.metric("Davon bezahlt", fmt_eur(rev_paid))
        c3.metric("Ausgaben", fmt_eur(exp_all))
        c4.metric("Ergebnis", fmt_eur(result),
                  "✅ Gewinn" if result >= 0 else "⚠️ Verlust")

        if not shifts_m.empty:
            n_shifts = int(shifts_m.iloc[0].get("Schichten", 0) or 0)
            n_unbes  = int(shifts_m.iloc[0].get("Unbesetzt", 0) or 0)
            st.caption(f"🗓️ {n_shifts} Schichten geplant · {n_unbes} unbesetzt")

        col_inv, col_exp = st.columns(2)
        with col_inv:
            st.subheader(f"Rechnungen ({len(inv_m) if not inv_m.empty else 0})")
            if not inv_m.empty:
                st.dataframe(inv_m, use_container_width=True)
        with col_exp:
            st.subheader(f"Ausgaben ({len(exp_m) if not exp_m.empty else 0})")
            if not exp_m.empty:
                st.dataframe(exp_m, use_container_width=True)

        # Excel-Monatsbericht
        if st.button("📊 Monatsbericht als Excel erstellen", type="primary"):
            try:
                from io import BytesIO
                buf = BytesIO()
                with pd.ExcelWriter(buf, engine="openpyxl") as writer:
                    summary_df = pd.DataFrame([{
                        "Kennzahl": "Umsatz fakturiert", "Wert_EUR": rev_all,
                    }, {
                        "Kennzahl": "Umsatz bezahlt", "Wert_EUR": rev_paid,
                    }, {
                        "Kennzahl": "Ausgaben gesamt", "Wert_EUR": exp_all,
                    }, {
                        "Kennzahl": "Ergebnis (bez. Umsatz - Ausgaben)", "Wert_EUR": result,
                    }])
                    summary_df.to_excel(writer, sheet_name="Zusammenfassung", index=False)
                    if not inv_m.empty:
                        inv_m.to_excel(writer, sheet_name="Rechnungen", index=False)
                    if not exp_m.empty:
                        exp_m.to_excel(writer, sheet_name="Ausgaben", index=False)
                buf.seek(0)
                st.download_button(
                    f"📥 Monatsbericht_{month_str}.xlsx herunterladen",
                    buf.read(), f"monatsbericht_{month_str}.xlsx",
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            except Exception as e:
                st.error(f"Excel-Fehler: {e}")

    # ── Quartalsbericht ───────────────────────────────────────
    with tabs[1]:
        st.subheader("Quartalsbericht")
        col1, col2 = st.columns(2)
        q_year    = col1.selectbox("Jahr", list(range(date.today().year, date.today().year - 5, -1)), key="q_year")
        q_quarter = col2.selectbox("Quartal", [1, 2, 3, 4], index=(date.today().month - 1) // 3)

        q_months = [f"{q_year}-{(q_quarter-1)*3+m:02d}" for m in range(1, 4)]

        inv_q = df_fn("""
            SELECT substr(invoice_date,1,7) AS Monat,
                   SUM(gross_total) AS Umsatz_gesamt,
                   SUM(CASE WHEN status='bezahlt' THEN gross_total ELSE 0 END) AS Bezahlt,
                   COUNT(*) AS Rechnungen
            FROM invoices WHERE substr(invoice_date,1,7) IN (?,?,?)
            GROUP BY substr(invoice_date,1,7) ORDER BY Monat
        """, tuple(q_months))
        exp_q = df_fn("""
            SELECT bwa_month AS Monat,
                   SUM(gross_amount) AS Ausgaben,
                   SUM(vat_amount) AS Vorsteuer,
                   COUNT(*) AS Belege
            FROM expenses WHERE bwa_month IN (?,?,?)
            GROUP BY bwa_month ORDER BY Monat
        """, tuple(q_months))

        st.markdown(f"### Q{q_quarter}/{q_year} — {q_months[0]} bis {q_months[-1]}")
        if not inv_q.empty or not exp_q.empty:
            merged = (inv_q.merge(exp_q, on="Monat", how="outer").fillna(0)
                      if not inv_q.empty and not exp_q.empty
                      else inv_q if not inv_q.empty else exp_q)
            if "Bezahlt" in merged.columns and "Ausgaben" in merged.columns:
                merged["Ergebnis"] = merged["Bezahlt"] - merged["Ausgaben"]

            st.dataframe(merged, use_container_width=True)
            if "Bezahlt" in merged.columns and "Ausgaben" in merged.columns:
                st.bar_chart(merged.set_index("Monat")[["Bezahlt", "Ausgaben"]])

            c1, c2, c3 = st.columns(3)
            c1.metric("Umsatz bezahlt", fmt_eur(float(merged.get("Bezahlt", pd.Series([0])).sum())))
            c2.metric("Ausgaben", fmt_eur(float(merged.get("Ausgaben", pd.Series([0])).sum())))
            if "Ergebnis" in merged.columns:
                c3.metric("Quartalsergebnis", fmt_eur(float(merged["Ergebnis"].sum())))
        else:
            st.info("Keine Daten für dieses Quartal.")

    # ── Jahres-GuV ────────────────────────────────────────────
    with tabs[2]:
        st.subheader("Jahres-GuV (vereinfacht)")
        g_year = st.selectbox("Jahr", list(range(date.today().year, date.today().year - 10, -1)), key="g_year")

        inv_y = df_fn("""
            SELECT SUM(gross_total) AS Umsatz_gesamt,
                   SUM(net_total) AS Umsatz_netto,
                   SUM(CASE WHEN status='bezahlt' THEN gross_total ELSE 0 END) AS Bezahlt,
                   SUM(CASE WHEN status IN ('offen','ueberfaellig') THEN gross_total ELSE 0 END) AS Offen,
                   COUNT(*) AS Rechnungen
            FROM invoices WHERE substr(invoice_date,1,4)=?
        """, (str(g_year),)).iloc[0].to_dict()

        exp_y = df_fn("""
            SELECT SUM(gross_amount) AS Ausgaben_gesamt,
                   SUM(net_amount) AS Ausgaben_netto,
                   SUM(vat_amount) AS Vorsteuer_gesamt,
                   COUNT(*) AS Belege
            FROM expenses WHERE substr(bwa_month,1,4)=?
        """, (str(g_year),)).iloc[0].to_dict()

        cat_y = df_fn("""
            SELECT category AS Kostenart,
                   SUM(gross_amount) AS Brutto,
                   SUM(net_amount) AS Netto
            FROM expenses WHERE substr(bwa_month,1,4)=?
            GROUP BY category ORDER BY Brutto DESC
        """, (str(g_year),))

        u_ges = float(inv_y.get("Umsatz_gesamt") or 0)
        u_bez = float(inv_y.get("Bezahlt") or 0)
        u_netto = float(inv_y.get("Umsatz_netto") or 0)
        a_ges = float(exp_y.get("Ausgaben_gesamt") or 0)
        a_netto = float(exp_y.get("Ausgaben_netto") or 0)
        vst = float(exp_y.get("Vorsteuer_gesamt") or 0)
        ergebnis_brutto = u_bez - a_ges
        ergebnis_netto  = u_netto - a_netto

        st.markdown(f"### GuV {g_year}")
        row1 = st.columns(4)
        row1[0].metric("Umsatz (fakturiert)", fmt_eur(u_ges))
        row1[1].metric("Umsatz (bezahlt)", fmt_eur(u_bez))
        row1[2].metric("Ausgaben (brutto)", fmt_eur(a_ges))
        row1[3].metric("Vorsteuer", fmt_eur(vst))

        row2 = st.columns(2)
        row2[0].metric("Ergebnis (brutto)", fmt_eur(ergebnis_brutto),
                       "✅" if ergebnis_brutto >= 0 else "❌")
        row2[1].metric("Ergebnis (netto)", fmt_eur(ergebnis_netto),
                       "✅" if ergebnis_netto >= 0 else "❌")

        if not cat_y.empty:
            st.subheader("Kostenstruktur")
            st.dataframe(cat_y, use_container_width=True)
            st.bar_chart(cat_y.set_index("Kostenart")["Brutto"])

        # Monatsweise
        monthly_y = df_fn("""
            SELECT substr(invoice_date,1,7) AS Monat,
                   SUM(CASE WHEN status='bezahlt' THEN gross_total ELSE 0 END) AS Umsatz
            FROM invoices WHERE substr(invoice_date,1,4)=?
            GROUP BY substr(invoice_date,1,7) ORDER BY Monat
        """, (str(g_year),))
        exp_monthly_y = df_fn("""
            SELECT bwa_month AS Monat, SUM(gross_amount) AS Ausgaben
            FROM expenses WHERE substr(bwa_month,1,4)=?
            GROUP BY bwa_month ORDER BY Monat
        """, (str(g_year),))
        if not monthly_y.empty:
            combined = monthly_y.merge(exp_monthly_y, on="Monat", how="outer").fillna(0)
            combined["Ergebnis"] = combined["Umsatz"] - combined["Ausgaben"]
            st.subheader("Jahresverlauf monatlich")
            st.bar_chart(combined.set_index("Monat")[["Umsatz","Ausgaben"]])
            st.line_chart(combined.set_index("Monat")[["Ergebnis"]])

    # ── Kunden-Ranking ────────────────────────────────────────
    with tabs[3]:
        st.subheader("🏆 Kunden-Ranking nach Umsatz")
        r_year = st.selectbox("Jahr", ["alle"] + [str(y) for y in range(date.today().year, date.today().year-5,-1)], key="r_year")
        where_r = f"AND substr(i.invoice_date,1,4)='{r_year}'" if r_year != "alle" else ""
        ranking = df_fn(f"""
            SELECT c.company AS Kunde, COUNT(i.id) AS Rechnungen,
                   SUM(i.gross_total) AS Umsatz_gesamt,
                   SUM(CASE WHEN i.status='bezahlt' THEN i.gross_total ELSE 0 END) AS Bezahlt,
                   ROUND(SUM(CASE WHEN i.status='bezahlt' THEN i.gross_total ELSE 0 END)*100.0/
                         NULLIF(SUM(i.gross_total),0), 1) AS Zahlquote_Pct
            FROM invoices i JOIN customers c ON c.id=i.customer_id
            WHERE i.status NOT IN ('storniert') {where_r}
            GROUP BY c.id ORDER BY Umsatz_gesamt DESC LIMIT 20
        """)
        if not ranking.empty:
            st.dataframe(ranking, use_container_width=True)
            st.bar_chart(ranking.set_index("Kunde")["Umsatz_gesamt"])

    # ── Mitarbeiter-Report ────────────────────────────────────
    with tabs[4]:
        st.subheader("👷 Mitarbeiter-Einsatzreport")
        r_year2 = st.selectbox("Jahr", list(range(date.today().year, date.today().year-5,-1)), key="r_year2")
        emp_report = df_fn("""
            SELECT e.name AS Mitarbeiter,
                   COUNT(s.id) AS Schichten,
                   SUM(CASE WHEN s.status='abgeschlossen' THEN 1 ELSE 0 END) AS Abgeschlossen,
                   SUM(CASE WHEN s.status='ausgefallen' THEN 1 ELSE 0 END) AS Ausgefallen,
                   COUNT(DISTINCT s.customer_id) AS Verschiedene_Kunden
            FROM shifts s JOIN employees e ON e.id=s.employee_id
            WHERE substr(s.shift_date,1,4)=?
            GROUP BY e.id ORDER BY Schichten DESC
        """, (str(r_year2),))
        if not emp_report.empty:
            st.dataframe(emp_report, use_container_width=True)
            st.bar_chart(emp_report.set_index("Mitarbeiter")["Schichten"])
        else:
            st.info("Keine Schichtdaten für dieses Jahr.")

        # Zeiterfassung-Statistik
        st.subheader("Zeiterfassung nach Mitarbeiter")
        time_rep = df_fn("""
            SELECT e.name AS Mitarbeiter,
                   COUNT(t.id) AS Einträge,
                   ROUND(SUM(t.net_hours),1) AS Gesamtstunden,
                   ROUND(SUM(t.overtime_hours),1) AS Überstunden,
                   ROUND(AVG(t.net_hours),2) AS Ø_Stunden_pro_Tag
            FROM time_entries t JOIN employees e ON e.id=t.employee_id
            WHERE substr(t.date,1,4)=?
            GROUP BY e.id ORDER BY Gesamtstunden DESC
        """, (str(r_year2),))
        if not time_rep.empty:
            st.dataframe(time_rep, use_container_width=True)
