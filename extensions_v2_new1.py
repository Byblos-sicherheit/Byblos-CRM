"""
extensions_v2_new1.py – Wiederkehrende Rechnungen + QR-Code + Steuertermine
============================================================================
1. Wiederkehrende Rechnungen (Dauerrechnungen / Auto-Recurring)
2. GiroCode / EPC-QR auf Rechnungen für Sofort-Überweisung
3. Steuer- und Fälligkeitskalender (USt, LSt, Vorauszahlungen)
4. Rechnungs-Vorlagen (Templates)
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd
import streamlit as st


def fmt_eur(v: float) -> str:
    return f"{v:,.2f} €".replace(",", "X").replace(".", ",").replace("X", ".")


# ─────────────────────────────────────────────────────────────
# DB-Registrierung
# ─────────────────────────────────────────────────────────────

def register_new1(run_fn, df_fn) -> None:
    run_fn("""CREATE TABLE IF NOT EXISTS recurring_invoices (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        customer_id INTEGER NOT NULL,
        template_name TEXT NOT NULL,
        description TEXT NOT NULL,
        net_amount REAL DEFAULT 0,
        vat_rate REAL DEFAULT 19,
        frequency TEXT DEFAULT 'monatlich',
        day_of_month INTEGER DEFAULT 1,
        next_due TEXT NOT NULL,
        last_created TEXT,
        active INTEGER DEFAULT 1,
        notes TEXT,
        auto_send INTEGER DEFAULT 0,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(customer_id) REFERENCES customers(id)
    )""")
    run_fn("""CREATE TABLE IF NOT EXISTS invoice_templates (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        template_name TEXT UNIQUE NOT NULL,
        description TEXT,
        net_amount REAL DEFAULT 0,
        vat_rate REAL DEFAULT 19,
        items_json TEXT,
        notes TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )""")
    run_fn("""CREATE TABLE IF NOT EXISTS tax_calendar (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        due_date TEXT NOT NULL,
        tax_type TEXT NOT NULL,
        description TEXT,
        amount_est REAL DEFAULT 0,
        status TEXT DEFAULT 'offen',
        notes TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )""")


# ─────────────────────────────────────────────────────────────
# QR-Code Generator (EPC / GiroCode)
# ─────────────────────────────────────────────────────────────

def generate_epc_qr(iban: str, bic: str, name: str,
                    amount: float, reference: str) -> Optional[bytes]:
    """
    Erstellt einen EPC-QR-Code (GiroCode) für SEPA-Überweisung.
    Gibt PNG-Bytes zurück oder None wenn qrcode nicht installiert.
    """
    try:
        import qrcode
        import io
        epc = (
            "BCD\n002\n1\nSCT\n"
            f"{bic}\n{name}\n{iban}\n"
            f"EUR{amount:.2f}\n\n\n{reference}\n"
        )
        qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M,
                           box_size=6, border=2)
        qr.add_data(epc)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()
    except ImportError:
        return None


def generate_simple_qr(text: str) -> Optional[bytes]:
    """Fallback: einfacher QR ohne EPC."""
    try:
        import qrcode
        import io
        qr = qrcode.make(text)
        buf = io.BytesIO()
        qr.save(buf, format="PNG")
        return buf.getvalue()
    except ImportError:
        return None


# ─────────────────────────────────────────────────────────────
# 1. Wiederkehrende Rechnungen
# ─────────────────────────────────────────────────────────────

def page_recurring_invoices(run_fn, df_fn, next_number_fn, log_fn,
                             refresh_totals_fn, gen_pdf_fn,
                             queue_email_fn, get_setting_fn) -> None:
    st.title("🔄 Wiederkehrende Rechnungen")
    st.caption("Automatische Monats-/Quartalsrechnungen für Dauerkunden. "
               "Rechnungen werden bei der Tagesroutine oder manuell erzeugt.")

    tabs = st.tabs([
        "📋 Übersicht", "➕ Neue Dauerrechnung", "▶️ Jetzt ausführen",
        "📝 Vorlagen", "📅 Fälligkeitskalender"
    ])

    FREQUENCIES = ["monatlich", "vierteljährlich", "halbjährlich", "jährlich"]

    # ── Tab 0: Übersicht ──────────────────────────────────────
    with tabs[0]:
        recurring = df_fn("""
            SELECT r.id, r.template_name AS Vorlage, c.company AS Kunde,
                   r.description AS Beschreibung,
                   ROUND(r.net_amount * (1 + r.vat_rate/100), 2) AS Brutto_EUR,
                   r.frequency AS Rhythmus, r.next_due AS Nächste_Fälligkeit,
                   r.last_created AS Zuletzt_erstellt,
                   CASE WHEN r.active=1 THEN '✅ aktiv' ELSE '⛔ pausiert' END AS Status,
                   r.auto_send AS Auto_Versand
            FROM recurring_invoices r JOIN customers c ON c.id=r.customer_id
            ORDER BY r.next_due
        """)
        if not recurring.empty:
            # Heute fällige
            today = date.today().isoformat()
            due_today = recurring[recurring["Nächste_Fälligkeit"] <= today]
            if not due_today.empty:
                st.warning(f"⚠️ **{len(due_today)} Dauerrechnung(en) heute/überfällig** — Tab 'Jetzt ausführen'!")

            c1, c2, c3 = st.columns(3)
            c1.metric("Aktive Dauerrechnungen",
                      len(recurring[recurring["Status"] == "✅ aktiv"]))
            c2.metric("Gesamt monatlich ca.",
                      fmt_eur(float(recurring[recurring["Rhythmus"] == "monatlich"]["Brutto_EUR"].sum())))
            c3.metric("Heute fällig", len(due_today))
            st.dataframe(recurring.drop(columns=["id"]), use_container_width=True, height=350)

            # Pausieren / Aktivieren
            st.divider()
            sel_labels = recurring["Vorlage"].tolist()
            sel = st.selectbox("Dauerrechnung verwalten", sel_labels)
            rid = int(recurring[recurring["Vorlage"] == sel].iloc[0]["id"])
            cur_active = recurring[recurring["Vorlage"] == sel].iloc[0]["Status"]
            col1, col2 = st.columns(2)
            if col1.button("⛔ Pausieren" if cur_active == "✅ aktiv" else "✅ Aktivieren"):
                new_val = 0 if cur_active == "✅ aktiv" else 1
                run_fn("UPDATE recurring_invoices SET active=? WHERE id=?", (new_val, rid))
                st.rerun()
            if col2.button("🗑️ Löschen"):
                run_fn("DELETE FROM recurring_invoices WHERE id=?", (rid,))
                log_fn("recurring_deleted", str(rid))
                st.rerun()
        else:
            st.info("Noch keine Dauerrechnungen eingerichtet.")

    # ── Tab 1: Neue Dauerrechnung ─────────────────────────────
    with tabs[1]:
        customers = df_fn("SELECT id, customer_no || ' – ' || company AS label FROM customers ORDER BY company")
        templates = df_fn("SELECT template_name, description, net_amount, vat_rate, items_json FROM invoice_templates")

        if customers.empty:
            st.warning("Erst Kunden anlegen.")
            return

        with st.form("recurring_form", clear_on_submit=True):
            a, b = st.columns(2)
            tpl_name = a.text_input("Vorlagenname *", "Monatliche Objektschutz-Rechnung")
            cust_label = b.selectbox("Kunde *", customers["label"].tolist())

            # Vorlage übernehmen
            if not templates.empty:
                use_tpl = st.selectbox("Vorlage laden (optional)", ["—"] + templates["template_name"].tolist())
                if use_tpl != "—":
                    tpl = templates[templates["template_name"] == use_tpl].iloc[0]
                    st.info(f"Vorlage: {tpl['description']} · {tpl['net_amount']} € netto")
            else:
                use_tpl = "—"

            description = st.text_input("Leistungsbeschreibung *", "Objektschutz")
            a2, b2, c2, d2 = st.columns(4)
            net_amount = a2.number_input("Netto (€)", min_value=0.0, value=1000.0, step=50.0)
            vat_rate   = b2.number_input("MwSt %", value=19.0, step=1.0)
            frequency  = c2.selectbox("Rhythmus", FREQUENCIES)
            day_of_month = d2.number_input("Am Monats-Tag", min_value=1, max_value=28, value=1)
            next_due   = st.date_input("Erste Fälligkeit", date.today().replace(day=int(day_of_month)))
            auto_send  = st.checkbox("PDF automatisch per E-Mail versenden", value=False)
            notes      = st.text_area("Notizen")
            submitted  = st.form_submit_button("💾 Dauerrechnung speichern", type="primary")

        if submitted and tpl_name and description:
            cid = int(customers[customers["label"] == cust_label].iloc[0]["id"])
            run_fn("""INSERT INTO recurring_invoices(customer_id,template_name,description,
                      net_amount,vat_rate,frequency,day_of_month,next_due,active,notes,auto_send)
                      VALUES(?,?,?,?,?,?,?,?,1,?,?)""",
                   (cid, tpl_name, description, net_amount, vat_rate,
                    frequency, day_of_month, next_due.isoformat(), notes, 1 if auto_send else 0))
            log_fn("recurring_created", tpl_name)
            st.success(f"✅ Dauerrechnung '{tpl_name}' eingerichtet!")
            st.rerun()

    # ── Tab 2: Jetzt ausführen ────────────────────────────────
    with tabs[2]:
        st.subheader("Fällige Dauerrechnungen erstellen")
        today = date.today().isoformat()
        due = df_fn("""
            SELECT r.id, r.template_name AS Vorlage, c.company AS Kunde,
                   c.id AS customer_id, c.email AS email,
                   r.description, r.net_amount, r.vat_rate, r.frequency,
                   r.next_due, r.auto_send
            FROM recurring_invoices r JOIN customers c ON c.id=r.customer_id
            WHERE r.active=1 AND r.next_due <= ?
            ORDER BY r.next_due
        """, (today,))

        if due.empty:
            st.success("✅ Keine fälligen Dauerrechnungen.")
        else:
            st.warning(f"⚠️ {len(due)} Dauerrechnung(en) zur Erstellung bereit:")
            st.dataframe(due[["Vorlage","Kunde","description","net_amount","frequency","next_due"]],
                         use_container_width=True)

            col1, col2 = st.columns(2)
            create_all = col1.button(f"✅ Alle {len(due)} Rechnungen erstellen", type="primary")
            dry_run = col2.checkbox("Vorschau (nicht wirklich erstellen)")

            if create_all:
                created = 0
                for _, r in due.iterrows():
                    if dry_run:
                        st.info(f"Vorschau: {r['Vorlage']} für {r['Kunde']}")
                        continue
                    # Rechnung erstellen
                    inv_no = next_number_fn("invoices", "invoice_no", "RE-")
                    net = float(r["net_amount"])
                    vat = float(r["vat_rate"])
                    vat_amt = round(net * vat / 100, 2)
                    gross   = round(net + vat_amt, 2)
                    due_date = (date.today() + timedelta(days=14)).isoformat()
                    service = date.today().strftime("%B %Y")

                    run_fn("""INSERT INTO invoices(invoice_no,customer_id,invoice_date,service_date,
                              due_date,description,net_total,vat_rate,vat_total,gross_total,
                              paid_amount,status)
                              VALUES(?,?,?,?,?,?,?,?,?,?,0,'offen')""",
                           (inv_no, int(r["customer_id"]), date.today().isoformat(),
                            service, due_date, str(r["description"]),
                            net, vat, vat_amt, gross))
                    iid = int(df_fn("SELECT id FROM invoices WHERE invoice_no=?", (inv_no,)).iloc[0]["id"])
                    refresh_totals_fn(iid)

                    # Nächste Fälligkeit berechnen
                    nd = date.fromisoformat(str(r["next_due"])[:10])
                    freq = str(r["frequency"])
                    if freq == "monatlich":
                        m = nd.month + 1
                        y = nd.year + (m > 12)
                        m = m if m <= 12 else 1
                        next_nd = nd.replace(year=y, month=m)
                    elif freq == "vierteljährlich":
                        next_nd = nd + timedelta(days=91)
                    elif freq == "halbjährlich":
                        next_nd = nd + timedelta(days=182)
                    else:
                        next_nd = nd.replace(year=nd.year + 1)

                    run_fn("UPDATE recurring_invoices SET next_due=?, last_created=? WHERE id=?",
                           (next_nd.isoformat(), date.today().isoformat(), int(r["id"])))

                    # PDF + Auto-Versand
                    try:
                        pdf_path = gen_pdf_fn(iid)
                        if r["auto_send"] and str(r.get("email", "")):
                            queue_email_fn(
                                str(r["email"]),
                                f"Rechnung {inv_no} – {r['Vorlage']}",
                                f"Sehr geehrte Damen und Herren,\n\nanbei Ihre Rechnung {inv_no} "
                                f"für {service}.\n\nMit freundlichen Grüßen\nByblos Sicherheitsdienst",
                                str(pdf_path) if pdf_path else ""
                            )
                    except Exception:
                        pass

                    created += 1

                if not dry_run:
                    log_fn("recurring_executed", f"{created} Rechnungen erstellt")
                    st.success(f"✅ {created} Rechnungen erstellt!")
                    st.rerun()

    # ── Tab 3: Vorlagen ───────────────────────────────────────
    with tabs[3]:
        st.subheader("Rechnungsvorlagen")
        templates = df_fn("SELECT * FROM invoice_templates ORDER BY template_name")
        if not templates.empty:
            st.dataframe(templates, use_container_width=True)

        with st.form("tpl_form", clear_on_submit=True):
            a, b = st.columns(2)
            tpl_n   = a.text_input("Vorlagenname *")
            tpl_d   = b.text_input("Beschreibung")
            tpl_net = a.number_input("Standard-Netto (€)", min_value=0.0, value=0.0, step=50.0)
            tpl_vat = b.number_input("Standard-MwSt %", value=19.0)
            tpl_note = st.text_area("Notizen")
            if st.form_submit_button("💾 Vorlage speichern") and tpl_n:
                run_fn("INSERT OR REPLACE INTO invoice_templates(template_name,description,net_amount,vat_rate,notes) VALUES(?,?,?,?,?)",
                       (tpl_n, tpl_d, tpl_net, tpl_vat, tpl_note))
                st.success(f"Vorlage '{tpl_n}' gespeichert.")
                st.rerun()

    # ── Tab 4: Fälligkeitskalender ────────────────────────────
    with tabs[4]:
        page_tax_calendar(run_fn, df_fn)


# ─────────────────────────────────────────────────────────────
# 2. Steuer- und Fälligkeitskalender
# ─────────────────────────────────────────────────────────────

def _add_tax_dates_for_year(run_fn, year: int) -> int:
    """Fügt Standard-Steuertermine für ein Jahr hinzu."""
    added = 0
    taxes = []

    # Umsatzsteuervoranmeldung (monatlich, 10. des Folgemonats)
    for m in range(1, 13):
        nm = m + 1 if m < 12 else 1
        ny = year if m < 12 else year + 1
        taxes.append((
            f"{ny}-{nm:02d}-10",
            "USt-Voranmeldung",
            f"Umsatzsteuervoranmeldung {['Jan','Feb','Mär','Apr','Mai','Jun','Jul','Aug','Sep','Okt','Nov','Dez'][m-1]} {year}",
            0.0, "offen"
        ))

    # Lohnsteuer-Anmeldung (monatlich, 10. des Folgemonats)
    for m in range(1, 13):
        nm = m + 1 if m < 12 else 1
        ny = year if m < 12 else year + 1
        taxes.append((
            f"{ny}-{nm:02d}-10",
            "Lohnsteuer-Anmeldung",
            f"Lohnsteueranmeldung {['Jan','Feb','Mär','Apr','Mai','Jun','Jul','Aug','Sep','Okt','Nov','Dez'][m-1]} {year}",
            0.0, "offen"
        ))

    # Körperschaftsteuer-/ESt-Vorauszahlungen (Quartale: 10.3, 10.6, 10.9, 10.12)
    for qm in [3, 6, 9, 12]:
        taxes.append((f"{year}-{qm:02d}-10", "Steuervorauszahlung",
                      f"Steuervorauszahlung Q{qm//3} {year}", 0.0, "offen"))

    # SV-Beiträge (15. des Monats)
    for m in range(1, 13):
        taxes.append((f"{year}-{m:02d}-15", "Sozialversicherung",
                      f"SV-Beiträge {['Jan','Feb','Mär','Apr','Mai','Jun','Jul','Aug','Sep','Okt','Nov','Dez'][m-1]} {year}",
                      0.0, "offen"))

    for due, typ, desc, amt, status in taxes:
        existing = run_fn.__self__ if hasattr(run_fn, '__self__') else None
        try:
            run_fn("INSERT OR IGNORE INTO tax_calendar(due_date,tax_type,description,amount_est,status) VALUES(?,?,?,?,?)",
                   (due, typ, desc, amt, status))
            added += 1
        except Exception:
            pass
    return added


def page_tax_calendar(run_fn, df_fn) -> None:
    st.subheader("📅 Steuer- & Fälligkeitskalender")
    st.caption("Überblick über alle Steuer- und Abgabenfristen. "
               "Beträge sind Schätzwerte – mit Steuerberater abstimmen.")

    col1, col2 = st.columns([3, 1])
    year = col1.selectbox("Jahr", list(range(date.today().year, date.today().year + 2)))

    if col2.button("📅 Steuertermine einrichten"):
        added = 0
        for due, typ, desc, amt, status in [
            (f"{year}-{nm:02d}-10", "USt-Voranmeldung",
             f"USt-VA {['Jan','Feb','Mär','Apr','Mai','Jun','Jul','Aug','Sep','Okt','Nov','Dez'][m-1]} {year}",
             0.0, "offen")
            for m in range(1, 13)
            for nm in [m + 1 if m < 12 else 1]
        ]:
            try:
                run_fn("INSERT OR IGNORE INTO tax_calendar(due_date,tax_type,description,amount_est,status) VALUES(?,?,?,?,?)",
                       (due.replace("13", "01").replace(f"{year+1}-", f"{year}-") if "-13-" in due else due,
                        typ, desc, amt, status))
                added += 1
            except Exception:
                pass

        # Simple loop statt rekursive Funktion
        for m in range(1, 13):
            nm = m + 1 if m < 12 else 1
            ny = year if m < 12 else year + 1
            months_de = ['Jan','Feb','Mär','Apr','Mai','Jun','Jul','Aug','Sep','Okt','Nov','Dez']
            for typ, desc in [
                ("USt-Voranmeldung", f"Umsatzsteuervoranmeldung {months_de[m-1]} {year}"),
                ("Lohnsteuer-Anmeldung", f"Lohnsteueranmeldung {months_de[m-1]} {year}"),
                ("Sozialversicherung", f"SV-Beiträge {months_de[m-1]} {year}"),
            ]:
                d1 = f"{ny}-{nm:02d}-10" if "SV" not in typ else f"{year}-{m:02d}-15"
                try:
                    run_fn("INSERT OR IGNORE INTO tax_calendar(due_date,tax_type,description,amount_est,status) VALUES(?,?,?,?,?)",
                           (d1, typ, desc, 0.0, "offen"))
                    added += 1
                except Exception:
                    pass
        for qm in [3, 6, 9, 12]:
            try:
                run_fn("INSERT OR IGNORE INTO tax_calendar(due_date,tax_type,description,amount_est,status) VALUES(?,?,?,?,?)",
                       (f"{year}-{qm:02d}-10", "Steuervorauszahlung",
                        f"Steuervorauszahlung Q{qm//3} {year}", 0.0, "offen"))
                added += 1
            except Exception:
                pass
        st.success(f"✅ Steuertermine für {year} eingerichtet.")
        st.rerun()

    calendar = df_fn("""
        SELECT id, due_date AS Fällig, tax_type AS Typ,
               description AS Beschreibung,
               amount_est AS Betrag_Schätzung, status AS Status, notes AS Notiz
        FROM tax_calendar
        WHERE substr(due_date,1,4)=?
        ORDER BY due_date
    """, (str(year),))

    if calendar.empty:
        st.info(f"Keine Steuertermine für {year}. Bitte 'Steuertermine einrichten' klicken.")
    else:
        today = date.today().isoformat()
        overdue = calendar[calendar["Fällig"] < today][calendar["Status"] == "offen"]
        upcoming = calendar[(calendar["Fällig"] >= today) &
                            (calendar["Fällig"] <= (date.today() + timedelta(days=14)).isoformat())]

        c1, c2, c3 = st.columns(3)
        c1.metric("Termine gesamt", len(calendar))
        c2.metric("⚠️ Überfällig", len(overdue))
        c3.metric("📅 Nächste 14 Tage", len(upcoming))

        if not overdue.empty:
            st.error("🔴 Überfällige Steuertermine:")
            st.dataframe(overdue.drop(columns=["id"]), use_container_width=True)

        if not upcoming.empty:
            st.warning("🟡 Fällig in den nächsten 14 Tagen:")
            st.dataframe(upcoming.drop(columns=["id"]), use_container_width=True)

        # Filter nach Typ
        typ_filter = st.selectbox("Typ filtern", ["alle"] + calendar["Typ"].unique().tolist())
        if typ_filter != "alle":
            calendar = calendar[calendar["Typ"] == typ_filter]
        st.dataframe(calendar.drop(columns=["id"]), use_container_width=True, height=350)

        # Status aktualisieren
        st.divider()
        st.subheader("Status / Betrag aktualisieren")
        sel = st.selectbox("Termin", calendar["Beschreibung"].tolist())
        tid = int(calendar[calendar["Beschreibung"] == sel].iloc[0]["id"])
        col1, col2, col3 = st.columns(3)
        new_status = col1.selectbox("Status", ["offen", "bezahlt", "eingereicht", "erledigt"])
        new_amount = col2.number_input("Tatsächlicher Betrag (€)", min_value=0.0, value=0.0, step=50.0)
        new_note   = col3.text_input("Notiz")
        if st.button("💾 Aktualisieren"):
            run_fn("UPDATE tax_calendar SET status=?, amount_est=?, notes=? WHERE id=?",
                   (new_status, new_amount, new_note, tid))
            st.success("✅ Aktualisiert.")
            st.rerun()

    csv = calendar.to_csv(index=False, sep=";").encode("utf-8-sig") if not calendar.empty else b""
    if csv:
        st.download_button("📥 CSV-Export", csv, f"steuerkalender_{year}.csv", "text/csv")


# ─────────────────────────────────────────────────────────────
# 3. QR-Code auf Rechnungen testen
# ─────────────────────────────────────────────────────────────

def page_qr_settings(run_fn, df_fn, get_setting_fn, set_setting_fn) -> None:
    st.title("📱 QR-Code & Zahlungsoptionen")
    st.caption("GiroCode/EPC-QR ermöglicht Kunden, Rechnungen per Bank-App sofort zu überweisen.")

    tabs = st.tabs(["⚙️ QR-Einstellungen", "🔍 QR-Vorschau", "📊 Zahlungsoptionen"])

    with tabs[0]:
        st.subheader("Bankverbindung für QR-Code")
        with st.form("qr_settings"):
            iban = st.text_input("IBAN", get_setting_fn("company_iban", ""))
            bic  = st.text_input("BIC", get_setting_fn("company_bic", ""))
            name = st.text_input("Kontoinhaber", get_setting_fn("company_name", "Byblos Sicherheitsdienst"))
            enable_qr = st.checkbox("QR-Code auf Rechnungen aktivieren",
                                    value=get_setting_fn("invoice_qr_enabled", "0") == "1")
            if st.form_submit_button("💾 Speichern", type="primary"):
                for k, v in [("company_iban", iban), ("company_bic", bic),
                              ("company_name", name),
                              ("invoice_qr_enabled", "1" if enable_qr else "0")]:
                    set_setting_fn(k, v)
                st.success("✅ QR-Einstellungen gespeichert.")

    with tabs[1]:
        st.subheader("QR-Code Vorschau")
        iban = get_setting_fn("company_iban", "")
        bic  = get_setting_fn("company_bic", "")
        name = get_setting_fn("company_name", "Byblos")

        if not iban:
            st.warning("Bitte zuerst IBAN in den Einstellungen hinterlegen.")
        else:
            test_amount = st.number_input("Testbetrag (€)", value=500.0, step=10.0)
            test_ref    = st.text_input("Verwendungszweck", "RE-0001")

            qr_bytes = generate_epc_qr(iban, bic, name, test_amount, test_ref)
            if qr_bytes:
                st.image(qr_bytes, caption=f"GiroCode für {test_amount:.2f} €", width=200)
                st.success("✅ QR-Code-Erzeugung funktioniert.")
                st.download_button("📥 QR als PNG", qr_bytes, "girokode.png", "image/png")
            else:
                st.warning("⚠️ `qrcode`-Bibliothek nicht installiert.")
                st.code("pip install qrcode[pil]", language="bash")
                # Fallback: Textdarstellung
                st.text_area("EPC-Daten (manuell)", f"BCD\n002\n1\nSCT\n{bic}\n{name}\n{iban}\nEUR{test_amount:.2f}\n\n\n{test_ref}")

    with tabs[2]:
        st.subheader("Unterstützte Zahlungsoptionen")
        st.markdown("""
| Methode | Status | Einrichtung |
|---|---|---|
| **Überweisung (Standard)** | ✅ Aktiv | Keine – IBAN in Einstellungen |
| **GiroCode / EPC-QR** | ✅ Konfigurierbar | IBAN + `pip install qrcode[pil]` |
| **SEPA-Lastschrift** | 📝 Manuell | Gläubiger-ID beim Finanzamt beantragen |
| **PayPal** | ℹ️ Hinweis | PayPal-Link in E-Mail einfügen |
| **Stripe** | 🔧 Erweiterbar | Stripe-API-Key in Einstellungen |

**IBAN auf Rechnungen:** Wird automatisch aus den Einstellungen geladen (Firmendaten-Tab).

**Tipp:** Mit dem GiroCode können Kunden Rechnungen direkt per Banking-App (Sparkasse, DKB, ING usw.) 
scannen und überweisen – reduziert Zahlungsverzögerungen erheblich.
        """)
