"""
Byblos CRM extension: E-Rechnung und Zeiterfassung.

Wichtig: Die XRechnung/XML-Erzeugung ist ein technischer Export-Entwurf.
Vor produktiver Nutzung muss die XML gegen EN 16931/XRechnung validiert und
steuerlich/rechtlich geprüft werden.
"""
from __future__ import annotations

import csv
import hashlib
import io
import html
from datetime import date, datetime, timedelta
from pathlib import Path
import xml.etree.ElementTree as ET

import pandas as pd
import streamlit as st


def _money(value) -> float:
    try:
        return round(float(value or 0), 2)
    except Exception:
        return 0.0


def _today() -> str:
    return date.today().isoformat()


def _next_invoice_number(df, prefix="BY") -> str:
    year = date.today().year
    rows = df("SELECT invoice_no FROM invoices WHERE invoice_no LIKE ? ORDER BY invoice_no DESC LIMIT 1", (f"{prefix}-{year}-%",))
    if rows.empty:
        n = 1
    else:
        last = str(rows.iloc[0]["invoice_no"])
        try:
            n = int(last.split("-")[-1]) + 1
        except Exception:
            n = 1
    return f"{prefix}-{year}-{n:05d}"


def _company_defaults(df):
    rows = df("SELECT * FROM company_profiles ORDER BY is_default DESC, id ASC LIMIT 1")
    if rows.empty:
        return {"name": "Byblos", "email": "", "phone": "", "address": "", "iban": "", "bic": ""}
    return rows.iloc[0].to_dict()


def _customer(df, customer_id):
    rows = df("SELECT * FROM customers WHERE id=?", (customer_id,))
    return rows.iloc[0].to_dict() if not rows.empty else {}


def _invoice_items(df, invoice_id):
    return df("SELECT * FROM invoice_items WHERE invoice_id=? ORDER BY position, id", (invoice_id,))


def _invoice(df, invoice_id):
    rows = df("SELECT * FROM invoices WHERE id=?", (invoice_id,))
    return rows.iloc[0].to_dict() if not rows.empty else {}


def _build_basic_xrechnung_xml(run, df, invoice_id: int) -> bytes:
    """Create a structured XML draft for an invoice.

    This is intentionally conservative and marked as a draft. It contains the
    most important invoice data in a structured XML envelope. A production
    XRechnung export must be generated/validated with a certified EN 16931
    library or validator.
    """
    inv = _invoice(df, invoice_id)
    if not inv:
        raise ValueError("Rechnung nicht gefunden")
    customer = _customer(df, inv.get("customer_id"))
    company = _company_defaults(df)
    items = _invoice_items(df, invoice_id)

    root = ET.Element("ByblosEInvoiceDraft", attrib={
        "profile": "XRechnung-DRAFT",
        "warning": "Nicht ohne EN-16931/XRechnung-Validator produktiv verwenden",
        "generated_at": datetime.now().isoformat(timespec="seconds"),
    })
    seller = ET.SubElement(root, "Seller")
    for key in ["name", "address", "email", "phone", "iban", "bic"]:
        ET.SubElement(seller, key).text = str(company.get(key, "") or "")
    buyer = ET.SubElement(root, "Buyer")
    for key in ["customer_no", "company", "contact_person", "street", "zip", "city", "email", "vat_id"]:
        ET.SubElement(buyer, key).text = str(customer.get(key, "") or "")
    invoice = ET.SubElement(root, "Invoice")
    for key in ["invoice_no", "invoice_date", "service_date", "due_date", "description", "net_total", "vat_rate", "vat_total", "gross_total", "status"]:
        ET.SubElement(invoice, key).text = str(inv.get(key, "") or "")
    payment = ET.SubElement(root, "Payment")
    ET.SubElement(payment, "method").text = str(inv.get("payment_method", "Ueberweisung") or "Ueberweisung")
    ET.SubElement(payment, "iban").text = str(company.get("iban", "") or "")
    ET.SubElement(payment, "bic").text = str(company.get("bic", "") or "")
    lines = ET.SubElement(root, "Lines")
    for _, item in items.iterrows():
        line = ET.SubElement(lines, "Line")
        for key in ["position", "description", "quantity", "unit", "unit_price", "total"]:
            ET.SubElement(line, key).text = str(item.get(key, "") or "")
    xml_bytes = ET.tostring(root, encoding="utf-8", xml_declaration=True)
    digest = hashlib.sha256(xml_bytes).hexdigest()
    run("INSERT INTO einvoice_exports(invoice_id, format, file_name, sha256, status, note) VALUES(?,?,?,?,?,?)",
        (invoice_id, "XRechnung-DRAFT-XML", f"{inv.get('invoice_no')}.xml", digest, "entwurf", "Technischer Entwurf; Validierung erforderlich"))
    return xml_bytes


def _csv_for_invoice(df, invoice_id: int) -> bytes:
    inv = _invoice(df, invoice_id)
    customer = _customer(df, inv.get("customer_id")) if inv else {}
    items = _invoice_items(df, invoice_id)
    out = io.StringIO()
    writer = csv.writer(out, delimiter=";")
    writer.writerow(["Rechnung", inv.get("invoice_no", "")])
    writer.writerow(["Kunde", customer.get("company", "")])
    writer.writerow(["Datum", inv.get("invoice_date", "")])
    writer.writerow([])
    writer.writerow(["Pos", "Beschreibung", "Menge", "Einheit", "Einzelpreis", "Gesamt"])
    for _, item in items.iterrows():
        writer.writerow([item.get("position", ""), item.get("description", ""), item.get("quantity", ""), item.get("unit", ""), item.get("unit_price", ""), item.get("total", "")])
    writer.writerow([])
    writer.writerow(["Netto", inv.get("net_total", 0)])
    writer.writerow(["USt", inv.get("vat_total", 0)])
    writer.writerow(["Brutto", inv.get("gross_total", 0)])
    return out.getvalue().encode("utf-8-sig")


def register_einvoice_time(run, df):
    # Extend invoices safely.
    for sql in [
        "ALTER TABLE invoices ADD COLUMN payment_method TEXT DEFAULT 'Ueberweisung'",
        "ALTER TABLE invoices ADD COLUMN einvoice_status TEXT DEFAULT 'nicht_erstellt'",
        "ALTER TABLE invoices ADD COLUMN einvoice_xml_path TEXT",
        "ALTER TABLE invoices ADD COLUMN template_name TEXT DEFAULT 'standard'",
        "ALTER TABLE company_profiles ADD COLUMN iban TEXT",
        "ALTER TABLE company_profiles ADD COLUMN bic TEXT",
        "ALTER TABLE company_profiles ADD COLUMN tax_no TEXT",
        "ALTER TABLE company_profiles ADD COLUMN vat_id TEXT",
    ]:
        try:
            run(sql)
        except Exception:
            pass
    run("""
    CREATE TABLE IF NOT EXISTS einvoice_exports (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        invoice_id INTEGER NOT NULL,
        format TEXT,
        file_name TEXT,
        sha256 TEXT,
        status TEXT DEFAULT 'entwurf',
        note TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )""")
    run("""
    CREATE TABLE IF NOT EXISTS invoice_templates (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE,
        company_profile_id INTEGER,
        logo_path TEXT,
        footer_text TEXT,
        payment_text TEXT,
        active INTEGER DEFAULT 1,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )""")
    run("""
    CREATE TABLE IF NOT EXISTS time_entries (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        employee_id INTEGER,
        customer_id INTEGER,
        object_id INTEGER,
        service_type TEXT,
        work_date TEXT NOT NULL,
        start_time TEXT,
        end_time TEXT,
        break_minutes INTEGER DEFAULT 0,
        hours REAL DEFAULT 0,
        billable INTEGER DEFAULT 1,
        invoice_id INTEGER,
        status TEXT DEFAULT 'offen',
        note TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )""")
    run("""
    CREATE TABLE IF NOT EXISTS payment_methods (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE,
        description TEXT,
        active INTEGER DEFAULT 1
    )""")
    for name, desc in [
        ("Ueberweisung", "SEPA-Überweisung auf hinterlegtes Firmenkonto"),
        ("Kreditkarte", "Kreditkartenzahlung über externen Zahlungsanbieter"),
        ("Bar", "Barzahlung, nur mit Quittung"),
        ("SEPA-Lastschrift", "Lastschrift nur mit Mandat"),
    ]:
        try:
            run("INSERT OR IGNORE INTO payment_methods(name, description) VALUES(?,?)", (name, desc))
        except Exception:
            pass


def page_einvoice_center(run, df, base_dir=None):
    st.title("E-Rechnung / Rechnungserstellung")
    st.warning("XRechnung: Dieses Modul erzeugt einen strukturierten XML-Entwurf. Für echte gesetzliche Konformität muss die XML gegen EN 16931/XRechnung validiert werden.")
    tabs = st.tabs(["Neue Rechnung", "Export", "Vorlagen/Zahlung", "Prüfung"])
    with tabs[0]:
        customers = df("SELECT id, customer_no || ' - ' || company AS label FROM customers ORDER BY company")
        if customers.empty:
            st.info("Zuerst Kunden anlegen.")
            return
        customer_label = st.selectbox("Kunde", customers["label"].tolist())
        customer_id = int(customers[customers["label"] == customer_label].iloc[0]["id"])
        payment_methods = df("SELECT name FROM payment_methods WHERE active=1 ORDER BY name")
        default_no = _next_invoice_number(df)
        with st.form("new_einvoice_invoice"):
            invoice_no = st.text_input("Rechnungsnummer", default_no)
            invoice_date = st.date_input("Rechnungsdatum", date.today()).isoformat()
            service_date = st.date_input("Leistungsdatum", date.today()).isoformat()
            due_date = st.date_input("Fällig am", date.today() + timedelta(days=14)).isoformat()
            payment_method = st.selectbox("Zahlungsmethode", payment_methods["name"].tolist() if not payment_methods.empty else ["Ueberweisung"])
            description = st.text_input("Kurzbeschreibung", "Dienstleistung")
            c1, c2, c3 = st.columns(3)
            qty = c1.number_input("Menge/Stunden", min_value=0.0, value=1.0, step=0.5)
            unit = c2.text_input("Einheit", "Stunden")
            price = c3.number_input("Einzelpreis netto", min_value=0.0, value=45.0, step=5.0)
            vat_rate = st.number_input("USt %", min_value=0.0, value=19.0, step=1.0)
            if st.form_submit_button("Rechnung anlegen"):
                net = _money(qty * price)
                vat = _money(net * vat_rate / 100)
                gross = _money(net + vat)
                run("""INSERT INTO invoices(invoice_no, customer_id, invoice_date, service_date, due_date, description, net_total, vat_rate, vat_total, gross_total, status, payment_method)
                       VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""", (invoice_no, customer_id, invoice_date, service_date, due_date, description, net, vat_rate, vat, gross, "offen", payment_method))
                inv_id = int(df("SELECT id FROM invoices WHERE invoice_no=?", (invoice_no,)).iloc[0]["id"])
                run("INSERT INTO invoice_items(invoice_id, position, description, quantity, unit, unit_price, total) VALUES(?,?,?,?,?,?,?)",
                    (inv_id, 1, description, qty, unit, price, net))
                st.success(f"Rechnung {invoice_no} angelegt.")
                st.rerun()
    with tabs[1]:
        invoices = df("SELECT i.id, i.invoice_no, c.company, i.invoice_date, i.gross_total, i.status, COALESCE(i.einvoice_status,'nicht_erstellt') AS einvoice_status FROM invoices i LEFT JOIN customers c ON c.id=i.customer_id ORDER BY i.invoice_date DESC, i.id DESC")
        st.dataframe(invoices, use_container_width=True)
        if not invoices.empty:
            selected = st.selectbox("Rechnung exportieren", invoices["invoice_no"].tolist())
            inv_id = int(invoices[invoices["invoice_no"] == selected].iloc[0]["id"])
            c1, c2 = st.columns(2)
            with c1:
                if st.button("XRechnung-XML-Entwurf erzeugen"):
                    xml_bytes = _build_basic_xrechnung_xml(run, df, inv_id)
                    run("UPDATE invoices SET einvoice_status=?, einvoice_xml_path=? WHERE id=?", ("entwurf", f"{selected}.xml", inv_id))
                    st.download_button("XML herunterladen", xml_bytes, file_name=f"{selected}_xrechnung_entwurf.xml", mime="application/xml")
            with c2:
                csv_bytes = _csv_for_invoice(df, inv_id)
                st.download_button("CSV herunterladen", csv_bytes, file_name=f"{selected}.csv", mime="text/csv")
        st.subheader("E-Rechnungs-Exportprotokoll")
        st.dataframe(df("SELECT * FROM einvoice_exports ORDER BY created_at DESC"), use_container_width=True)
    with tabs[2]:
        st.subheader("Zahlungsmethoden")
        st.dataframe(df("SELECT * FROM payment_methods ORDER BY name"), use_container_width=True)
        with st.form("payment_method_new"):
            name = st.text_input("Neue Zahlungsmethode")
            desc = st.text_input("Beschreibung")
            if st.form_submit_button("Speichern") and name:
                run("INSERT OR IGNORE INTO payment_methods(name, description) VALUES(?,?)", (name, desc))
                st.success("Gespeichert.")
                st.rerun()
        st.subheader("Rechnungsvorlagen")
        st.dataframe(df("SELECT * FROM invoice_templates ORDER BY active DESC, name"), use_container_width=True)
        with st.form("template_new"):
            tname = st.text_input("Vorlagenname", "standard")
            footer = st.text_area("Footer-Text", "Vielen Dank für Ihren Auftrag.")
            paytxt = st.text_area("Zahlungstext", "Bitte überweisen Sie den Rechnungsbetrag fristgerecht unter Angabe der Rechnungsnummer.")
            if st.form_submit_button("Vorlage speichern"):
                run("INSERT OR REPLACE INTO invoice_templates(name, footer_text, payment_text, active) VALUES(?,?,?,1)", (tname, footer, paytxt))
                st.success("Vorlage gespeichert.")
                st.rerun()
    with tabs[3]:
        checks = []
        invoices = df("SELECT * FROM invoices ORDER BY invoice_date DESC LIMIT 200")
        for _, inv in invoices.iterrows():
            missing = []
            if not inv.get("invoice_no"): missing.append("Rechnungsnummer")
            if not inv.get("customer_id"): missing.append("Kunde")
            if not inv.get("invoice_date"): missing.append("Rechnungsdatum")
            if _money(inv.get("gross_total")) <= 0: missing.append("Betrag")
            if not inv.get("payment_method"): missing.append("Zahlungsmethode")
            checks.append({"Rechnung": inv.get("invoice_no"), "Status": "OK" if not missing else "Prüfen", "Fehlt": ", ".join(missing)})
        st.dataframe(pd.DataFrame(checks), use_container_width=True)


def _calculate_hours(start: str, end: str, break_minutes: int) -> float:
    try:
        s = datetime.strptime(start, "%H:%M")
        e = datetime.strptime(end, "%H:%M")
        if e < s:
            e += timedelta(days=1)
        minutes = max(0, int((e - s).total_seconds() / 60) - int(break_minutes or 0))
        return round(minutes / 60, 2)
    except Exception:
        return 0.0


def page_time_tracking(run, df):
    st.title("Zeiterfassung")
    tabs = st.tabs(["Zeit erfassen", "Übersicht", "Abrechnung", "Export"])
    employees = df("SELECT id, employee_no || ' - ' || name AS label FROM employees WHERE active=1 ORDER BY name")
    customers = df("SELECT id, customer_no || ' - ' || company AS label FROM customers ORDER BY company")
    with tabs[0]:
        if employees.empty or customers.empty:
            st.info("Für Zeiterfassung zuerst Mitarbeiter und Kunden anlegen.")
        else:
            with st.form("time_new"):
                employee_label = st.selectbox("Mitarbeiter", employees["label"].tolist())
                customer_label = st.selectbox("Kunde", customers["label"].tolist())
                employee_id = int(employees[employees["label"] == employee_label].iloc[0]["id"])
                customer_id = int(customers[customers["label"] == customer_label].iloc[0]["id"])
                service_type = st.selectbox("Leistung", ["Sicherheitsdienst", "Reinigung", "Hausmeister", "Umzug", "Entrümpelung"])
                work_date = st.date_input("Datum", date.today()).isoformat()
                c1, c2, c3 = st.columns(3)
                start = c1.text_input("Start", "08:00")
                end = c2.text_input("Ende", "16:00")
                br = c3.number_input("Pause Minuten", min_value=0, value=30, step=5)
                billable = st.checkbox("Abrechenbar", value=True)
                note = st.text_area("Notiz")
                if st.form_submit_button("Zeit speichern"):
                    hours = _calculate_hours(start, end, int(br))
                    run("""INSERT INTO time_entries(employee_id, customer_id, service_type, work_date, start_time, end_time, break_minutes, hours, billable, status, note)
                           VALUES(?,?,?,?,?,?,?,?,?,?,?)""", (employee_id, customer_id, service_type, work_date, start, end, int(br), hours, 1 if billable else 0, "offen", note))
                    st.success(f"Zeit gespeichert: {hours:.2f} Stunden.")
                    st.rerun()
    with tabs[1]:
        q_status = st.selectbox("Status", ["alle", "offen", "freigegeben", "abgerechnet"])
        query = """SELECT t.id, t.work_date AS Datum, e.name AS Mitarbeiter, c.company AS Kunde, t.service_type AS Leistung, t.start_time AS Von, t.end_time AS Bis, t.break_minutes AS Pause, t.hours AS Stunden, t.billable AS Abrechenbar, t.status AS Status, t.note AS Notiz
                   FROM time_entries t LEFT JOIN employees e ON e.id=t.employee_id LEFT JOIN customers c ON c.id=t.customer_id"""
        params = ()
        if q_status != "alle":
            query += " WHERE t.status=?"
            params = (q_status,)
        query += " ORDER BY t.work_date DESC, t.id DESC"
        data = df(query, params)
        st.dataframe(data, use_container_width=True)
        if not data.empty:
            ids = st.multiselect("Einträge freigeben", data["id"].tolist())
            if st.button("Ausgewählte freigeben") and ids:
                for id_ in ids:
                    run("UPDATE time_entries SET status='freigegeben' WHERE id=?", (int(id_),))
                st.success("Freigegeben.")
                st.rerun()
    with tabs[2]:
        open_entries = df("""SELECT t.*, c.company FROM time_entries t LEFT JOIN customers c ON c.id=t.customer_id WHERE t.billable=1 AND t.status IN ('offen','freigegeben') ORDER BY t.work_date""")
        st.dataframe(open_entries, use_container_width=True)
        if not open_entries.empty:
            customer_names = sorted(open_entries["company"].dropna().unique().tolist())
            cname = st.selectbox("Kunde abrechnen", customer_names)
            subset = open_entries[open_entries["company"] == cname]
            total_hours = float(subset["hours"].sum())
            st.metric("Abrechenbare Stunden", f"{total_hours:.2f}")
            price = st.number_input("Stundensatz netto", min_value=0.0, value=45.0, step=5.0)
            if st.button("Rechnung aus Zeiten erstellen"):
                cust_id = int(subset.iloc[0]["customer_id"])
                inv_no = _next_invoice_number(df)
                net = _money(total_hours * price)
                vat = _money(net * 0.19)
                gross = _money(net + vat)
                run("""INSERT INTO invoices(invoice_no, customer_id, invoice_date, service_date, due_date, description, net_total, vat_rate, vat_total, gross_total, status, payment_method)
                       VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""", (inv_no, cust_id, _today(), _today(), (date.today()+timedelta(days=14)).isoformat(), "Abrechnung Zeiterfassung", net, 19, vat, gross, "offen", "Ueberweisung"))
                inv_id = int(df("SELECT id FROM invoices WHERE invoice_no=?", (inv_no,)).iloc[0]["id"])
                run("INSERT INTO invoice_items(invoice_id, position, description, quantity, unit, unit_price, total) VALUES(?,?,?,?,?,?,?)",
                    (inv_id, 1, "Abrechenbare Stunden laut Zeiterfassung", total_hours, "Stunden", price, net))
                for id_ in subset["id"].tolist():
                    run("UPDATE time_entries SET status='abgerechnet', invoice_id=? WHERE id=?", (inv_id, int(id_)))
                st.success(f"Rechnung {inv_no} aus Zeiterfassung erstellt.")
                st.rerun()
    with tabs[3]:
        data = df("SELECT * FROM time_entries ORDER BY work_date DESC")
        st.download_button("Zeiterfassung CSV herunterladen", data.to_csv(index=False, sep=';').encode('utf-8-sig'), file_name="zeiterfassung.csv", mime="text/csv")
        st.dataframe(data, use_container_width=True)
