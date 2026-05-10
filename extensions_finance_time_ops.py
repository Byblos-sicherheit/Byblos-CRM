"""
Byblos CRM extension: Finance & Time Ops.

Diese Erweiterung ergänzt das E-Rechnung-/Zeiterfassungsmodul um operative
Funktionen: Zahlungsstatus, Mahnwesen, Versandvorbereitung, XRechnung-
Prüfhinweise, Zeitfreigabe und Abrechnungsläufe.

Wichtig: Die Prüfungen sind Plausibilitätschecks, kein rechtsverbindlicher
XRechnung-/EN-16931-Validator.
"""
from __future__ import annotations

import csv
import hashlib
import io
from datetime import date, datetime, timedelta

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


def register_finance_time_ops(run, df):
    for sql in [
        "ALTER TABLE invoices ADD COLUMN payment_status TEXT DEFAULT 'offen'",
        "ALTER TABLE invoices ADD COLUMN paid_date TEXT",
        "ALTER TABLE invoices ADD COLUMN paid_amount REAL DEFAULT 0",
        "ALTER TABLE invoices ADD COLUMN reminder_level INTEGER DEFAULT 0",
        "ALTER TABLE invoices ADD COLUMN last_reminder_at TEXT",
        "ALTER TABLE invoices ADD COLUMN sent_at TEXT",
        "ALTER TABLE invoices ADD COLUMN email_status TEXT DEFAULT 'nicht_versendet'",
        "ALTER TABLE invoices ADD COLUMN buyer_reference TEXT",
        "ALTER TABLE invoices ADD COLUMN leitweg_id TEXT",
    ]:
        try:
            run(sql)
        except Exception:
            pass

    run("""
    CREATE TABLE IF NOT EXISTS payment_transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        invoice_id INTEGER,
        amount REAL DEFAULT 0,
        paid_date TEXT,
        method TEXT,
        reference TEXT,
        note TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )""")
    run("""
    CREATE TABLE IF NOT EXISTS invoice_email_outbox (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        invoice_id INTEGER,
        recipient TEXT,
        subject TEXT,
        body TEXT,
        attachment_note TEXT,
        status TEXT DEFAULT 'entwurf',
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        sent_at TEXT
    )""")
    run("""
    CREATE TABLE IF NOT EXISTS einvoice_validation_checks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        invoice_id INTEGER,
        check_name TEXT,
        result TEXT,
        severity TEXT,
        note TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )""")
    run("""
    CREATE TABLE IF NOT EXISTS time_approval_batches (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        batch_no TEXT UNIQUE,
        customer_id INTEGER,
        period_from TEXT,
        period_to TEXT,
        total_hours REAL DEFAULT 0,
        status TEXT DEFAULT 'entwurf',
        approved_by TEXT,
        approved_at TEXT,
        invoice_id INTEGER,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )""")
    run("""
    CREATE TABLE IF NOT EXISTS billing_runs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        run_no TEXT UNIQUE,
        run_date TEXT,
        period_from TEXT,
        period_to TEXT,
        customer_id INTEGER,
        source TEXT,
        total_hours REAL DEFAULT 0,
        total_amount REAL DEFAULT 0,
        status TEXT DEFAULT 'entwurf',
        note TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )""")


def _invoice_options(df):
    inv = df("SELECT id, invoice_no, invoice_date, gross_total, status, payment_status FROM invoices ORDER BY invoice_date DESC, id DESC")
    if inv.empty:
        return inv
    inv["label"] = inv.apply(lambda r: f"#{int(r['id'])} · {r.get('invoice_no','')} · {r.get('invoice_date','')} · {float(r.get('gross_total') or 0):.2f} EUR", axis=1)
    return inv


def page_payments_reminders(run, df):
    st.title("Zahlungen & Mahnwesen")
    tabs = st.tabs(["Offene Rechnungen", "Zahlung buchen", "Mahnläufe", "Outbox"])

    with tabs[0]:
        st.subheader("Offene / überfällige Rechnungen")
        data = df("""
            SELECT i.id, i.invoice_no, i.invoice_date, i.due_date, c.company AS kunde,
                   i.gross_total, COALESCE(i.paid_amount,0) AS bezahlt,
                   ROUND(i.gross_total-COALESCE(i.paid_amount,0),2) AS offen,
                   i.payment_status, i.reminder_level, i.last_reminder_at
            FROM invoices i LEFT JOIN customers c ON c.id=i.customer_id
            WHERE COALESCE(i.gross_total,0) > COALESCE(i.paid_amount,0)
            ORDER BY i.due_date ASC, i.id DESC
        """)
        st.dataframe(data, use_container_width=True)
        _download_df("Offene Rechnungen exportieren", data, "offene_rechnungen.csv")

    with tabs[1]:
        inv = _invoice_options(df)
        if inv.empty:
            st.info("Keine Rechnungen vorhanden.")
        else:
            selected = st.selectbox("Rechnung", inv["label"].tolist())
            invoice_id = int(inv[inv["label"] == selected].iloc[0]["id"])
            with st.form("payment_booking_form"):
                amount = st.number_input("Zahlbetrag", min_value=0.0, value=0.0, step=10.0)
                paid_date = st.date_input("Zahlungsdatum", date.today()).isoformat()
                method = st.selectbox("Methode", ["Ueberweisung", "Kreditkarte", "Bar", "SEPA-Lastschrift", "Sonstige"])
                reference = st.text_input("Referenz / Kontoauszug", "")
                note = st.text_area("Notiz", "")
                if st.form_submit_button("Zahlung buchen"):
                    run("INSERT INTO payment_transactions(invoice_id, amount, paid_date, method, reference, note) VALUES(?,?,?,?,?,?)", (invoice_id, amount, paid_date, method, reference, note))
                    total_paid = _money(df("SELECT COALESCE(SUM(amount),0) AS v FROM payment_transactions WHERE invoice_id=?", (invoice_id,)).iloc[0]["v"])
                    gross = _money(df("SELECT gross_total FROM invoices WHERE id=?", (invoice_id,)).iloc[0]["gross_total"])
                    status = "bezahlt" if total_paid >= gross and gross > 0 else "teilbezahlt"
                    run("UPDATE invoices SET paid_amount=?, paid_date=?, payment_status=?, status=? WHERE id=?", (total_paid, paid_date if status == "bezahlt" else None, status, status if status == "bezahlt" else "offen", invoice_id))
                    st.success("Zahlung gebucht.")
                    st.rerun()

    with tabs[2]:
        st.subheader("Mahnvorschläge")
        grace_days = st.number_input("Tage nach Fälligkeit", min_value=0, value=3, step=1)
        cutoff = (date.today() - timedelta(days=int(grace_days))).isoformat()
        overdue = df("""
            SELECT i.id, i.invoice_no, i.due_date, c.company AS kunde, c.email,
                   i.gross_total, COALESCE(i.paid_amount,0) AS bezahlt,
                   ROUND(i.gross_total-COALESCE(i.paid_amount,0),2) AS offen,
                   COALESCE(i.reminder_level,0) AS mahnstufe
            FROM invoices i LEFT JOIN customers c ON c.id=i.customer_id
            WHERE i.due_date < ? AND COALESCE(i.gross_total,0) > COALESCE(i.paid_amount,0)
            ORDER BY i.due_date ASC
        """, (cutoff,))
        st.dataframe(overdue, use_container_width=True)
        if st.button("Mahn-Entwürfe für alle angezeigten Rechnungen erzeugen", width="stretch") and not overdue.empty:
            created = 0
            for _, r in overdue.iterrows():
                level = int(r.get("mahnstufe") or 0) + 1
                subject = f"Zahlungserinnerung / Mahnung {level}: Rechnung {r.get('invoice_no','')}"
                body = f"Sehr geehrte Damen und Herren,\n\nzu Ihrer Rechnung {r.get('invoice_no','')} ist aktuell ein offener Betrag von {float(r.get('offen') or 0):.2f} EUR vorhanden. Bitte prüfen Sie den Zahlungsausgleich.\n\nMit freundlichen Grüßen\nByblos"
                run("INSERT INTO invoice_email_outbox(invoice_id, recipient, subject, body, attachment_note, status) VALUES(?,?,?,?,?,?)", (int(r['id']), r.get('email',''), subject, body, "Rechnung/Mahnung als PDF beifügen", "entwurf"))
                run("UPDATE invoices SET reminder_level=?, last_reminder_at=?, payment_status='ueberfaellig', status='ueberfaellig' WHERE id=?", (level, _today(), int(r['id'])))
                created += 1
            st.success(f"{created} Mahn-Entwürfe erzeugt.")
            st.rerun()

    with tabs[3]:
        outbox = df("SELECT * FROM invoice_email_outbox ORDER BY created_at DESC LIMIT 200")
        st.dataframe(outbox, use_container_width=True)
        st.caption("Die Outbox erzeugt absichtlich Entwürfe. Der echte Versand sollte erst nach SMTP-Test und Freigabe aktiviert werden.")


def _run_einvoice_checks(run, df, invoice_id: int):
    run("DELETE FROM einvoice_validation_checks WHERE invoice_id=?", (invoice_id,))
    inv = df("SELECT * FROM invoices WHERE id=?", (invoice_id,))
    if inv.empty:
        return
    inv = inv.iloc[0].to_dict()
    cust = df("SELECT * FROM customers WHERE id=?", (inv.get("customer_id"),))
    customer = cust.iloc[0].to_dict() if not cust.empty else {}
    items = df("SELECT * FROM invoice_items WHERE invoice_id=?", (invoice_id,))

    checks = []
    def add(name, ok, severity, note):
        checks.append((invoice_id, name, "OK" if ok else "FEHLT", severity, note))

    add("Rechnungsnummer", bool(inv.get("invoice_no")), "rot", "Pflichtfeld für jede Rechnung.")
    add("Rechnungsdatum", bool(inv.get("invoice_date")), "rot", "Pflichtfeld.")
    add("Fälligkeit", bool(inv.get("due_date")), "gelb", "Für Zahlungssteuerung wichtig.")
    add("Kunde", bool(inv.get("customer_id")), "rot", "Kundenbezug fehlt.")
    add("Kundenname", bool(customer.get("company")), "rot", "Empfängername fehlt.")
    add("Kundenadresse", bool(customer.get("street") or customer.get("zip_city") or customer.get("city")), "rot", "Adresse für E-Rechnung/Rechnung prüfen.")
    add("Positionen", not items.empty, "rot", "Mindestens eine Rechnungsposition erforderlich.")
    add("Zahlungsmethode", bool(inv.get("payment_method")), "gelb", "Zahlungsmethode nicht gesetzt.")
    add("Leitweg-ID / Buyer Reference", bool(inv.get("leitweg_id") or inv.get("buyer_reference")), "gelb", "Für öffentliche Auftraggeber regelmäßig erforderlich; bei B2B je nach Empfänger prüfen.")
    add("USt-Berechnung", _money(inv.get("gross_total")) >= _money(inv.get("net_total")), "rot", "Brutto sollte Netto plus Steuer enthalten.")

    for c in checks:
        run("INSERT INTO einvoice_validation_checks(invoice_id, check_name, result, severity, note) VALUES(?,?,?,?,?)", c)


def page_einvoice_validation(run, df):
    st.title("E-Rechnung Validierung & Versandvorbereitung")
    st.warning("Dies ist eine Plausibilitätsprüfung. Sie ersetzt keinen EN-16931/XRechnung-Validator.")
    inv = _invoice_options(df)
    if inv.empty:
        st.info("Keine Rechnungen vorhanden.")
        return
    selected = st.selectbox("Rechnung prüfen", inv["label"].tolist())
    invoice_id = int(inv[inv["label"] == selected].iloc[0]["id"])
    c1, c2 = st.columns(2)
    if c1.button("Plausibilitätsprüfung ausführen", width="stretch"):
        _run_einvoice_checks(run, df, invoice_id)
        st.success("Prüfung ausgeführt.")
    if c2.button("Versand-Entwurf erzeugen", width="stretch"):
        invrow = df("SELECT i.invoice_no, c.email FROM invoices i LEFT JOIN customers c ON c.id=i.customer_id WHERE i.id=?", (invoice_id,)).iloc[0]
        subject = f"Rechnung {invrow.get('invoice_no','')}"
        body = "Sehr geehrte Damen und Herren,\n\nanbei erhalten Sie unsere Rechnung. Bitte prüfen Sie die angehängten Dokumente.\n\nMit freundlichen Grüßen\nByblos"
        run("INSERT INTO invoice_email_outbox(invoice_id, recipient, subject, body, attachment_note, status) VALUES(?,?,?,?,?,?)", (invoice_id, invrow.get("email", ""), subject, body, "PDF + XML nach Freigabe beifügen", "entwurf"))
        run("UPDATE invoices SET email_status='entwurf' WHERE id=?", (invoice_id,))
        st.success("Versand-Entwurf erstellt.")

    checks = df("SELECT check_name, result, severity, note, created_at FROM einvoice_validation_checks WHERE invoice_id=? ORDER BY id", (invoice_id,))
    st.dataframe(checks, use_container_width=True)
    outbox = df("SELECT recipient, subject, status, created_at FROM invoice_email_outbox WHERE invoice_id=? ORDER BY created_at DESC", (invoice_id,))
    st.subheader("Versand-Entwürfe")
    st.dataframe(outbox, use_container_width=True)


def page_time_approval_billing(run, df):
    st.title("Zeiten freigeben & abrechnen")
    tabs = st.tabs(["Zeiten prüfen", "Freigabe-Batches", "Abrechnungslauf"])
    with tabs[0]:
        status = st.selectbox("Status", ["offen", "freigegeben", "abgerechnet", "alle"])
        where = "" if status == "alle" else "WHERE t.status=?"
        params = () if status == "alle" else (status,)
        data = df(f"""
            SELECT t.id, t.work_date, t.start_time, t.end_time, t.break_minutes, t.hours, t.service_type,
                   c.company AS kunde, e.name AS mitarbeiter, t.status, t.billable, t.note
            FROM time_entries t
            LEFT JOIN customers c ON c.id=t.customer_id
            LEFT JOIN employees e ON e.id=t.employee_id
            {where}
            ORDER BY t.work_date DESC, t.id DESC
        """, params)
        st.dataframe(data, use_container_width=True)
        _download_df("Zeiten exportieren", data, "zeiten_export.csv")
        ids = st.text_input("IDs freigeben (Komma-getrennt)", "")
        if st.button("Ausgewählte Zeiten freigeben", width="stretch") and ids.strip():
            cleaned = [int(x.strip()) for x in ids.split(",") if x.strip().isdigit()]
            for tid in cleaned:
                run("UPDATE time_entries SET status='freigegeben' WHERE id=?", (tid,))
            st.success(f"{len(cleaned)} Zeiten freigegeben.")
            st.rerun()

    with tabs[1]:
        customers = df("SELECT id, company FROM customers ORDER BY company")
        if customers.empty:
            st.info("Keine Kunden vorhanden.")
        else:
            cust_label = st.selectbox("Kunde", customers["company"].tolist(), key="batch_customer")
            customer_id = int(customers[customers["company"] == cust_label].iloc[0]["id"])
            c1, c2 = st.columns(2)
            p_from = c1.date_input("Von", date.today().replace(day=1)).isoformat()
            p_to = c2.date_input("Bis", date.today()).isoformat()
            total = _money(df("SELECT COALESCE(SUM(hours),0) AS h FROM time_entries WHERE customer_id=? AND work_date BETWEEN ? AND ? AND status='freigegeben' AND billable=1", (customer_id, p_from, p_to)).iloc[0]["h"])
            st.metric("Freigegebene abrechenbare Stunden", total)
            if st.button("Freigabe-Batch erstellen", width="stretch"):
                batch_no = f"TB-{date.today().year}-{datetime.now().strftime('%m%d%H%M%S')}"
                run("INSERT INTO time_approval_batches(batch_no, customer_id, period_from, period_to, total_hours, status) VALUES(?,?,?,?,?,?)", (batch_no, customer_id, p_from, p_to, total, "freigegeben"))
                st.success(f"Batch {batch_no} erstellt.")
        st.dataframe(df("SELECT * FROM time_approval_batches ORDER BY created_at DESC"), use_container_width=True)

    with tabs[2]:
        st.subheader("Abrechnungslauf vorbereiten")
        batches = df("SELECT b.*, c.company FROM time_approval_batches b LEFT JOIN customers c ON c.id=b.customer_id WHERE b.status='freigegeben' ORDER BY b.created_at DESC")
        st.dataframe(batches, use_container_width=True)
        hourly_rate = st.number_input("Stundensatz netto", min_value=0.0, value=45.0, step=5.0)
        if st.button("Abrechnungsläufe für freigegebene Batches erstellen", width="stretch") and not batches.empty:
            count = 0
            for _, b in batches.iterrows():
                total_amount = _money(float(b.get("total_hours") or 0) * hourly_rate)
                run_no = f"BR-{date.today().year}-{int(b['id']):05d}"
                run("INSERT OR IGNORE INTO billing_runs(run_no, run_date, period_from, period_to, customer_id, source, total_hours, total_amount, status, note) VALUES(?,?,?,?,?,?,?,?,?,?)", (run_no, _today(), b.get("period_from"), b.get("period_to"), int(b.get("customer_id") or 0), "time_approval_batch", float(b.get("total_hours") or 0), total_amount, "bereit", f"Batch {b.get('batch_no')}"))
                count += 1
            st.success(f"{count} Abrechnungsläufe vorbereitet.")
        st.dataframe(df("SELECT br.*, c.company FROM billing_runs br LEFT JOIN customers c ON c.id=br.customer_id ORDER BY br.created_at DESC"), use_container_width=True)
