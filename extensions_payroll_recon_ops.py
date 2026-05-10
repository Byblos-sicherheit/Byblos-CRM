"""
Byblos CRM extension: Payroll, Reconciliation & Control Ops.

Diese Erweiterung baut auf E-Rechnung, Zeiterfassung und Finance-Time-Ops auf.
Sie ergänzt:
- SEPA-/Bankabgleich-Vorbereitung
- offene-Posten-Kontrolle
- Zeitkonten, Überstunden und Urlaub/Abwesenheiten
- Payroll-/Lohnvorbereitungs-Export
- Rechnungs- und Zeitprüflisten

Hinweis: Diese Funktionen sind operative Prüf- und Exporthilfen. Sie ersetzen
keine Lohnabrechnung, Steuerberatung, Rechtsberatung oder finalen XRechnung-
Validator.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta
import hashlib
import io
import pandas as pd
import streamlit as st


def _today() -> str:
    return date.today().isoformat()


def _money(v) -> float:
    try:
        return round(float(v or 0), 2)
    except Exception:
        return 0.0


def _download_df(label: str, data: pd.DataFrame, file_name: str):
    if data is None or data.empty:
        st.info("Keine Daten für Export vorhanden.")
        return
    st.download_button(
        label,
        data.to_csv(index=False, sep=";").encode("utf-8-sig"),
        file_name=file_name,
        mime="text/csv",
        width="stretch",
    )


def _table_exists(df, table_name: str) -> bool:
    try:
        res = df("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
        return not res.empty
    except Exception:
        return False


def register_payroll_recon_ops(run, df):
    for sql in [
        "ALTER TABLE time_entries ADD COLUMN approved_for_payroll INTEGER DEFAULT 0",
        "ALTER TABLE time_entries ADD COLUMN overtime_hours REAL DEFAULT 0",
        "ALTER TABLE employees ADD COLUMN vacation_days_per_year REAL DEFAULT 24",
        "ALTER TABLE employees ADD COLUMN target_hours_week REAL DEFAULT 40",
        "ALTER TABLE employees ADD COLUMN payroll_no TEXT",
    ]:
        try:
            run(sql)
        except Exception:
            pass

    run("""
    CREATE TABLE IF NOT EXISTS bank_import_batches (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        batch_no TEXT UNIQUE,
        source_file TEXT,
        imported_rows INTEGER DEFAULT 0,
        matched_rows INTEGER DEFAULT 0,
        unmatched_rows INTEGER DEFAULT 0,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )""")
    run("""
    CREATE TABLE IF NOT EXISTS bank_reconciliation_suggestions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        bank_transaction_id INTEGER,
        suggested_type TEXT,
        suggested_id INTEGER,
        confidence REAL DEFAULT 0,
        reason TEXT,
        status TEXT DEFAULT 'offen',
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )""")
    run("""
    CREATE TABLE IF NOT EXISTS employee_absences (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        employee_id INTEGER,
        absence_type TEXT,
        date_from TEXT,
        date_to TEXT,
        days REAL DEFAULT 0,
        status TEXT DEFAULT 'beantragt',
        note TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )""")
    run("""
    CREATE TABLE IF NOT EXISTS payroll_runs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        run_no TEXT UNIQUE,
        period_from TEXT,
        period_to TEXT,
        status TEXT DEFAULT 'entwurf',
        total_hours REAL DEFAULT 0,
        overtime_hours REAL DEFAULT 0,
        absence_days REAL DEFAULT 0,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        approved_at TEXT,
        approved_by TEXT,
        checksum TEXT
    )""")
    run("""
    CREATE TABLE IF NOT EXISTS payroll_run_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        payroll_run_id INTEGER,
        employee_id INTEGER,
        regular_hours REAL DEFAULT 0,
        overtime_hours REAL DEFAULT 0,
        absence_days REAL DEFAULT 0,
        gross_hint REAL DEFAULT 0,
        note TEXT
    )""")
    run("""
    CREATE TABLE IF NOT EXISTS ops_control_checks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        check_date TEXT,
        check_area TEXT,
        check_name TEXT,
        result TEXT,
        severity TEXT,
        note TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )""")


def page_open_items_control(run, df):
    st.title("Offene Posten & Zahlungsabgleich")
    tabs = st.tabs(["Offene Posten", "Bankabgleich", "Prüflog"])

    with tabs[0]:
        st.subheader("Rechnungen mit offenem Betrag")
        open_inv = df("""
            SELECT i.id, i.invoice_no, i.invoice_date, i.due_date, c.company AS kunde,
                   ROUND(i.gross_total,2) AS brutto,
                   ROUND(COALESCE(i.paid_amount,0),2) AS bezahlt,
                   ROUND(i.gross_total-COALESCE(i.paid_amount,0),2) AS offen,
                   i.payment_status, i.reminder_level
            FROM invoices i LEFT JOIN customers c ON c.id=i.customer_id
            WHERE COALESCE(i.gross_total,0) > COALESCE(i.paid_amount,0)
            ORDER BY i.due_date ASC, i.id DESC
        """)
        st.dataframe(open_inv, use_container_width=True)
        _download_df("Offene Posten exportieren", open_inv, "offene_posten.csv")

        st.subheader("Warnungen")
        today = _today()
        overdue = open_inv[open_inv["due_date"].astype(str) < today] if not open_inv.empty and "due_date" in open_inv else pd.DataFrame()
        c1, c2, c3 = st.columns(3)
        c1.metric("Offene Rechnungen", len(open_inv))
        c2.metric("Überfällig", len(overdue))
        c3.metric("Offener Betrag", f"{open_inv['offen'].sum():.2f} EUR" if not open_inv.empty else "0.00 EUR")

    with tabs[1]:
        st.subheader("Banktransaktionen gegen Rechnungen vorschlagen")
        st.caption("Der Abgleich nutzt Betrag, Verwendungszweck, Rechnungsnummer und Kundennamen. Er ist eine Hilfe, keine automatische Buchungsfreigabe.")
        if st.button("Abgleichsvorschläge neu berechnen", width="stretch"):
            tx = df("SELECT * FROM bank_transactions WHERE COALESCE(status,'neu') IN ('neu','unmatched','offen') ORDER BY booking_date DESC, id DESC LIMIT 1000")
            invoices = df("""
                SELECT i.id, i.invoice_no, i.gross_total, COALESCE(i.paid_amount,0) AS paid_amount,
                       c.company, c.email
                FROM invoices i LEFT JOIN customers c ON c.id=i.customer_id
                WHERE COALESCE(i.gross_total,0) > COALESCE(i.paid_amount,0)
            """)
            created = 0
            for _, t in tx.iterrows():
                amount = abs(_money(t.get("amount")))
                purpose = f"{t.get('purpose','')} {t.get('payer_payee','')}".lower()
                best = None
                best_score = 0
                best_reason = []
                for _, inv in invoices.iterrows():
                    due = round(_money(inv.get("gross_total")) - _money(inv.get("paid_amount")), 2)
                    score = 0
                    reason = []
                    if abs(amount - due) < 0.02:
                        score += 55
                        reason.append("Betrag passt exakt zum offenen Betrag")
                    elif due > 0 and abs(amount - due) / max(due, 1) < 0.05:
                        score += 35
                        reason.append("Betrag liegt nahe am offenen Betrag")
                    inv_no = str(inv.get("invoice_no") or "").lower()
                    if inv_no and inv_no in purpose:
                        score += 35
                        reason.append("Rechnungsnummer im Verwendungszweck")
                    company = str(inv.get("company") or "").lower()
                    if company and company[:8] in purpose:
                        score += 10
                        reason.append("Kundenname erkannt")
                    if score > best_score:
                        best_score = score
                        best = inv
                        best_reason = reason
                if best is not None and best_score >= 35:
                    run("""
                        INSERT INTO bank_reconciliation_suggestions(bank_transaction_id, suggested_type, suggested_id, confidence, reason, status)
                        VALUES(?,?,?,?,?,?)
                    """, (int(t["id"]), "invoice", int(best["id"]), float(min(best_score, 100)), " | ".join(best_reason), "offen"))
                    created += 1
            st.success(f"{created} Abgleichsvorschläge erzeugt.")
            st.rerun()

        suggestions = df("""
            SELECT s.id, s.bank_transaction_id, b.booking_date, b.payer_payee, b.purpose, b.amount,
                   s.suggested_type, s.suggested_id, i.invoice_no, s.confidence, s.reason, s.status
            FROM bank_reconciliation_suggestions s
            LEFT JOIN bank_transactions b ON b.id=s.bank_transaction_id
            LEFT JOIN invoices i ON i.id=s.suggested_id
            ORDER BY s.created_at DESC LIMIT 300
        """)
        st.dataframe(suggestions, use_container_width=True)
        if not suggestions.empty:
            selected = st.selectbox("Vorschlag anwenden", suggestions["id"].astype(int).tolist())
            if st.button("Ausgewählten Vorschlag als Zahlung buchen", width="stretch"):
                s = df("""
                    SELECT s.*, b.amount, b.booking_date, b.purpose FROM bank_reconciliation_suggestions s
                    LEFT JOIN bank_transactions b ON b.id=s.bank_transaction_id WHERE s.id=?
                """, (int(selected),))
                if not s.empty:
                    r = s.iloc[0]
                    invoice_id = int(r["suggested_id"])
                    amount = abs(_money(r["amount"]))
                    paid_date = str(r.get("booking_date") or _today())
                    run("INSERT INTO payment_transactions(invoice_id, amount, paid_date, method, reference, note) VALUES(?,?,?,?,?,?)", (invoice_id, amount, paid_date, "Bankabgleich", str(r.get("purpose") or ""), "per Abgleichsvorschlag gebucht"))
                    total_paid = _money(df("SELECT COALESCE(SUM(amount),0) AS v FROM payment_transactions WHERE invoice_id=?", (invoice_id,)).iloc[0]["v"])
                    gross = _money(df("SELECT gross_total FROM invoices WHERE id=?", (invoice_id,)).iloc[0]["gross_total"])
                    status = "bezahlt" if total_paid >= gross and gross > 0 else "teilbezahlt"
                    run("UPDATE invoices SET paid_amount=?, paid_date=?, payment_status=?, status=? WHERE id=?", (total_paid, paid_date if status == "bezahlt" else None, status, status if status == "bezahlt" else "offen", invoice_id))
                    run("UPDATE bank_reconciliation_suggestions SET status='angewendet' WHERE id=?", (int(selected),))
                    st.success("Zahlung aus Abgleichsvorschlag gebucht.")
                    st.rerun()

    with tabs[2]:
        st.subheader("Prüfungen")
        checks = df("SELECT * FROM ops_control_checks ORDER BY created_at DESC LIMIT 300")
        st.dataframe(checks, use_container_width=True)


def page_time_accounts_absences(run, df):
    st.title("Zeitkonto & Abwesenheiten")
    tabs = st.tabs(["Zeitkonto", "Abwesenheiten", "Payroll Export"])

    with tabs[0]:
        st.subheader("Zeitkonto nach Mitarbeiter")
        period_from = st.date_input("Von", date.today().replace(day=1), key="timeacct_from").isoformat()
        period_to = st.date_input("Bis", date.today(), key="timeacct_to").isoformat()
        data = df("""
            SELECT e.id, e.name, e.payroll_no, e.target_hours_week, e.hourly_rate,
                   ROUND(COALESCE(SUM(t.hours),0),2) AS ist_stunden,
                   ROUND(COALESCE(SUM(COALESCE(t.overtime_hours,0)),0),2) AS ueberstunden_markiert,
                   ROUND(COALESCE(SUM(CASE WHEN COALESCE(t.approved,0)=1 THEN t.hours ELSE 0 END),0),2) AS freigegeben
            FROM employees e
            LEFT JOIN time_entries t ON t.employee_id=e.id AND t.work_date BETWEEN ? AND ?
            GROUP BY e.id, e.name, e.payroll_no, e.target_hours_week, e.hourly_rate
            ORDER BY e.name
        """, (period_from, period_to))
        if not data.empty:
            days = (date.fromisoformat(period_to) - date.fromisoformat(period_from)).days + 1
            week_factor = days / 7
            data["soll_stunden"] = (data["target_hours_week"].fillna(40).astype(float) * week_factor).round(2)
            data["saldo"] = (data["ist_stunden"].astype(float) - data["soll_stunden"].astype(float)).round(2)
        st.dataframe(data, use_container_width=True)
        _download_df("Zeitkonto exportieren", data, "zeitkonto.csv")

        st.subheader("Überstunden automatisch markieren")
        if st.button("Positive Salden als Überstundenhinweis speichern", width="stretch") and not data.empty:
            updated = 0
            for _, r in data.iterrows():
                saldo = float(r.get("saldo") or 0)
                if saldo > 0:
                    entries = df("""
                        SELECT id, hours FROM time_entries
                        WHERE employee_id=? AND work_date BETWEEN ? AND ?
                        ORDER BY work_date DESC, id DESC
                    """, (int(r["id"]), period_from, period_to))
                    remaining = saldo
                    for _, te in entries.iterrows():
                        if remaining <= 0:
                            break
                        h = min(float(te.get("hours") or 0), remaining)
                        run("UPDATE time_entries SET overtime_hours=? WHERE id=?", (h, int(te["id"])))
                        remaining -= h
                        updated += 1
            st.success(f"Überstundenhinweise bei {updated} Zeiteinträgen gespeichert.")
            st.rerun()

    with tabs[1]:
        st.subheader("Abwesenheit erfassen")
        employees = df("SELECT id, name FROM employees WHERE active=1 ORDER BY name")
        if employees.empty:
            st.info("Keine Mitarbeiter vorhanden.")
        else:
            with st.form("absence_form"):
                label = st.selectbox("Mitarbeiter", employees.apply(lambda r: f"{int(r['id'])} · {r['name']}", axis=1).tolist())
                employee_id = int(label.split(" · ")[0])
                absence_type = st.selectbox("Typ", ["Urlaub", "Krank", "Fortbildung", "Unbezahlt", "Sonstiges"])
                d1 = st.date_input("Von", date.today(), key="absence_from")
                d2 = st.date_input("Bis", date.today(), key="absence_to")
                status = st.selectbox("Status", ["beantragt", "genehmigt", "abgelehnt", "storniert"])
                note = st.text_area("Notiz", "")
                if st.form_submit_button("Abwesenheit speichern"):
                    days = max((d2 - d1).days + 1, 1)
                    run("""
                        INSERT INTO employee_absences(employee_id, absence_type, date_from, date_to, days, status, note)
                        VALUES(?,?,?,?,?,?,?)
                    """, (employee_id, absence_type, d1.isoformat(), d2.isoformat(), float(days), status, note))
                    st.success("Abwesenheit gespeichert.")
                    st.rerun()
        absences = df("""
            SELECT a.*, e.name AS employee FROM employee_absences a
            LEFT JOIN employees e ON e.id=a.employee_id
            ORDER BY a.date_from DESC, a.id DESC
        """)
        st.dataframe(absences, use_container_width=True)
        _download_df("Abwesenheiten exportieren", absences, "abwesenheiten.csv")

    with tabs[2]:
        st.subheader("Lohnvorbereitungs-Export")
        p_from = st.date_input("Zeitraum von", date.today().replace(day=1), key="payroll_from").isoformat()
        p_to = st.date_input("Zeitraum bis", date.today(), key="payroll_to").isoformat()
        export = _payroll_export_df(df, p_from, p_to)
        st.dataframe(export, use_container_width=True)
        _download_df("Payroll-Export CSV", export, "payroll_export.csv")
        if st.button("Payroll-Lauf als Entwurf speichern", width="stretch"):
            run_no = "PAY-" + datetime.now().strftime("%Y%m%d-%H%M%S")
            checksum = hashlib.sha256(export.to_csv(index=False, sep=";").encode("utf-8")).hexdigest() if not export.empty else ""
            total_hours = float(export["stunden"].sum()) if not export.empty else 0
            overtime = float(export["ueberstunden"].sum()) if not export.empty else 0
            absence = float(export["abwesenheitstage"].sum()) if not export.empty else 0
            cur = run("INSERT INTO payroll_runs(run_no, period_from, period_to, total_hours, overtime_hours, absence_days, checksum) VALUES(?,?,?,?,?,?,?)", (run_no, p_from, p_to, total_hours, overtime, absence, checksum))
            payroll_run_id = cur.lastrowid
            for _, r in export.iterrows():
                run("""
                    INSERT INTO payroll_run_items(payroll_run_id, employee_id, regular_hours, overtime_hours, absence_days, gross_hint, note)
                    VALUES(?,?,?,?,?,?,?)
                """, (payroll_run_id, int(r["employee_id"]), float(r["stunden"]), float(r["ueberstunden"]), float(r["abwesenheitstage"]), float(r["brutto_hinweis"]), "automatisch erzeugt"))
            st.success(f"Payroll-Lauf {run_no} gespeichert.")
            st.rerun()
        st.subheader("Gespeicherte Payroll-Läufe")
        runs = df("SELECT * FROM payroll_runs ORDER BY created_at DESC LIMIT 100")
        st.dataframe(runs, use_container_width=True)


def _payroll_export_df(df, period_from: str, period_to: str) -> pd.DataFrame:
    employees = df("SELECT id, name, payroll_no, hourly_rate FROM employees ORDER BY name")
    rows = []
    for _, e in employees.iterrows():
        hours = df("""
            SELECT COALESCE(SUM(hours),0) AS h, COALESCE(SUM(COALESCE(overtime_hours,0)),0) AS ot
            FROM time_entries WHERE employee_id=? AND work_date BETWEEN ? AND ? AND COALESCE(approved,0)=1
        """, (int(e["id"]), period_from, period_to)).iloc[0]
        abs_days = df("""
            SELECT COALESCE(SUM(days),0) AS d FROM employee_absences
            WHERE employee_id=? AND date_from<=? AND date_to>=? AND status='genehmigt'
        """, (int(e["id"]), period_to, period_from)).iloc[0]["d"]
        h = float(hours["h"] or 0)
        ot = float(hours["ot"] or 0)
        rate = float(e.get("hourly_rate") or 0)
        rows.append({
            "employee_id": int(e["id"]),
            "mitarbeiter": e.get("name"),
            "personalnummer": e.get("payroll_no") or "",
            "stunden": round(h, 2),
            "ueberstunden": round(ot, 2),
            "abwesenheitstage": float(abs_days or 0),
            "stundensatz_hinweis": rate,
            "brutto_hinweis": round(h * rate, 2),
        })
    return pd.DataFrame(rows)


def page_ops_quality_checks(run, df):
    st.title("Ops Qualitätsprüfungen")
    st.caption("Schnellprüfungen für Datenqualität. Ergebnisse sind operative Hinweise, keine Rechts-/Steuerprüfung.")
    if st.button("Prüfungen jetzt ausführen", width="stretch"):
        run("DELETE FROM ops_control_checks WHERE check_date=?", (_today(),))
        _insert_check(run, "Finance", "Rechnungen ohne Fälligkeitsdatum", _count(df, "SELECT COUNT(*) AS n FROM invoices WHERE due_date IS NULL OR due_date=''"), "hoch")
        _insert_check(run, "Finance", "Rechnungen ohne Zahlungsstatus", _count(df, "SELECT COUNT(*) AS n FROM invoices WHERE payment_status IS NULL OR payment_status=''"), "mittel")
        _insert_check(run, "E-Rechnung", "Rechnungen ohne Buyer Reference/Leitweg-ID", _count(df, "SELECT COUNT(*) AS n FROM invoices WHERE (buyer_reference IS NULL OR buyer_reference='') AND (leitweg_id IS NULL OR leitweg_id='')"), "mittel")
        _insert_check(run, "Zeit", "Nicht freigegebene Zeiten", _count(df, "SELECT COUNT(*) AS n FROM time_entries WHERE COALESCE(approved,0)=0"), "mittel")
        _insert_check(run, "Zeit", "Zeiten ohne Mitarbeiter", _count(df, "SELECT COUNT(*) AS n FROM time_entries WHERE employee_id IS NULL"), "hoch")
        _insert_check(run, "Mitarbeiter", "Aktive Mitarbeiter ohne Stundensatz", _count(df, "SELECT COUNT(*) AS n FROM employees WHERE active=1 AND COALESCE(hourly_rate,0)=0"), "niedrig")
        if _table_exists(df, "field_employee_qualifications"):
            _insert_check(run, "FieldOps", "Qualifikationen laufen in 30 Tagen ab", _count(df, "SELECT COUNT(*) AS n FROM field_employee_qualifications WHERE valid_until BETWEEN date('now') AND date('now','+30 day')"), "mittel")
        st.success("Prüfungen ausgeführt.")
        st.rerun()
    data = df("SELECT * FROM ops_control_checks ORDER BY created_at DESC LIMIT 500")
    st.dataframe(data, use_container_width=True)
    _download_df("Prüfprotokoll exportieren", data, "ops_qualitaetspruefungen.csv")


def _count(df, sql: str) -> int:
    try:
        return int(df(sql).iloc[0]["n"])
    except Exception:
        return 0


def _insert_check(run, area: str, name: str, count: int, severity_if_found: str):
    result = "OK" if count == 0 else "WARNUNG"
    severity = "ok" if count == 0 else severity_if_found
    note = "Keine Auffälligkeit" if count == 0 else f"{count} Datensätze prüfen"
    run("INSERT INTO ops_control_checks(check_date, check_area, check_name, result, severity, note) VALUES(?,?,?,?,?,?)", (_today(), area, name, result, severity, note))
