"""
extensions_v2_core_pages.py – Vollständige Kernseiten für Byblos CRM v2
=======================================================================
Verbesserte Versionen aller noch ausstehenden Seiten:
  - Rechnungen (vollständig: Positionen inline, Zahlung, Status, Storno, PDF-Preview)
  - Kontakthistorie (Timeline-Ansicht)
  - Benutzerverwaltung (Rollen, Passwort-Reset)
  - Automatik (Cron-Scheduler, Logs in Echtzeit)
  - Archiv / GoBD (Dokumentensuche, Download)
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, List

import pandas as pd
import streamlit as st


# ─────────────────────────────────────────────────────────────
# Hilfsfunktionen
# ─────────────────────────────────────────────────────────────

def fmt_eur(v: float) -> str:
    return f"{v:,.2f} €".replace(",", "X").replace(".", ",").replace("X", ".")


def _badge(status: str) -> str:
    colors_map = {
        "bezahlt":      "#27ae60", "offen":        "#2980b9",
        "ueberfaellig": "#c0392b", "teilbezahlt":  "#e67e22",
        "storniert":    "#7f8c8d", "entwurf":      "#95a5a6",
    }
    c = colors_map.get(str(status).lower(), "#888")
    return f'<span style="background:{c}22;border:1px solid {c};color:{c};padding:1px 8px;border-radius:8px;font-size:.8rem;">{status}</span>'


# ─────────────────────────────────────────────────────────────
# 1. Vollständige Rechnungsverwaltung
# ─────────────────────────────────────────────────────────────

def page_invoices_v2(run_fn, df_fn, next_number_fn, log_fn,
                     refresh_totals_fn, gen_pdf_fn) -> None:
    st.title("🧾 Rechnungsverwaltung")

    INV_STATUS = ["offen", "teilbezahlt", "bezahlt", "ueberfaellig", "storniert"]

    tabs = st.tabs([
        "📋 Übersicht", "➕ Neue Rechnung",
        "📝 Positionen", "💳 Zahlung buchen",
        "📄 PDF & Versand", "✏️ Bearbeiten / Status"
    ])

    # ── Tab 0: Übersicht ──────────────────────────────────────
    with tabs[0]:
        col_s, col_f1, col_f2 = st.columns([3, 1, 1])
        q = col_s.text_input("🔍 Suche (Rechnungsnr., Kunde, Beschreibung)", "")
        status_f = col_f1.selectbox("Status", ["alle"] + INV_STATUS)
        year_f = col_f2.selectbox("Jahr", ["alle"] + [str(y) for y in range(date.today().year, date.today().year - 5, -1)])

        base = """
            SELECT i.id, i.invoice_no AS Nr, c.company AS Kunde,
                   i.invoice_date AS Datum, i.due_date AS Fällig,
                   i.description AS Leistung,
                   i.net_total AS Netto, i.vat_total AS USt,
                   i.gross_total AS Brutto, i.paid_amount AS Bezahlt,
                   ROUND(i.gross_total - i.paid_amount, 2) AS Offen,
                   i.status AS Status
            FROM invoices i JOIN customers c ON c.id = i.customer_id
        """
        where, params = [], []
        if q:
            where.append("(i.invoice_no LIKE ? OR c.company LIKE ? OR i.description LIKE ?)")
            params += [f"%{q}%"] * 3
        if status_f != "alle":
            where.append("i.status = ?"); params.append(status_f)
        if year_f != "alle":
            where.append("substr(i.invoice_date,1,4) = ?"); params.append(year_f)
        w = ("WHERE " + " AND ".join(where)) if where else ""
        data = df_fn(base + w + " ORDER BY i.invoice_date DESC, i.invoice_no DESC", tuple(params))

        if not data.empty:
            # KPI-Zeile
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Rechnungen", len(data))
            c2.metric("Umsatz gesamt", fmt_eur(float(data["Brutto"].sum())))
            c3.metric("Bezahlt", fmt_eur(float(data["Bezahlt"].sum())))
            c4.metric("Offen", fmt_eur(float(data["Offen"].sum())))
            st.dataframe(data.drop(columns=["id"]), use_container_width=True, height=380)
            csv = data.drop(columns=["id"]).to_csv(index=False, sep=";").encode("utf-8-sig")
            st.download_button("📥 CSV-Export", csv, "rechnungen_export.csv", "text/csv")
        else:
            st.info("Keine Rechnungen gefunden.")

    # ── Tab 1: Neue Rechnung ──────────────────────────────────
    with tabs[1]:
        customers = df_fn("SELECT id, customer_no || ' – ' || company AS label FROM customers ORDER BY company")
        if customers.empty:
            st.warning("⚠️ Bitte zuerst Kunden anlegen.")
            return

        with st.form("new_invoice_v2", clear_on_submit=True):
            a, b, c = st.columns(3)
            inv_no = a.text_input("Rechnungsnummer", next_number_fn("invoices", "invoice_no", "RE-"))
            cust_label = b.selectbox("Kunde *", customers["label"].tolist())
            inv_date = c.date_input("Rechnungsdatum", date.today())

            d, e, f = st.columns(3)
            service_date = d.text_input("Leistungszeitraum", date.today().strftime("%B %Y"))
            due_date = e.date_input("Fällig bis", date.today() + timedelta(days=14))
            vat_rate = f.number_input("MwSt %", min_value=0.0, max_value=100.0, value=19.0, step=1.0)

            desc = st.text_input("Leistungsbeschreibung *", "Sicherheitsdienstleistungen")
            notes = st.text_area("Interne Notizen")

            st.markdown("**Positionen direkt erfassen** (optional, können auch nachträglich hinzugefügt werden)")
            cols_h = st.columns([3, 1, 1, 1])
            cols_h[0].caption("Bezeichnung"); cols_h[1].caption("Menge"); cols_h[2].caption("Einheit"); cols_h[3].caption("Einzelpreis")

            items = []
            for i in range(1, 6):
                ci = st.columns([3, 1, 1, 1])
                d_i = ci[0].text_input(f"", key=f"ni_desc_{i}", label_visibility="collapsed")
                q_i = ci[1].number_input("", 0.0, step=0.25, key=f"ni_qty_{i}", label_visibility="collapsed")
                u_i = ci[2].text_input("", "Std.", key=f"ni_unit_{i}", label_visibility="collapsed")
                p_i = ci[3].number_input("", 0.0, step=5.0, key=f"ni_price_{i}", label_visibility="collapsed")
                if d_i and q_i > 0:
                    items.append({"pos": i, "desc": d_i, "qty": q_i, "unit": u_i, "price": p_i, "total": round(q_i * p_i, 2)})

            submitted = st.form_submit_button("💾 Rechnung anlegen", type="primary")

        if submitted:
            if not desc.strip():
                st.error("Leistungsbeschreibung ist Pflichtfeld.")
            else:
                cid = int(customers[customers["label"] == cust_label].iloc[0]["id"])
                run_fn("""INSERT INTO invoices(invoice_no,customer_id,invoice_date,service_date,due_date,
                          description,vat_rate,status,notes)
                          VALUES(?,?,?,?,?,?,?,?,?)""",
                       (inv_no, cid, inv_date.isoformat(), service_date,
                        due_date.isoformat(), desc, vat_rate, "offen", notes))
                iid = int(df_fn("SELECT id FROM invoices WHERE invoice_no=?", (inv_no,)).iloc[0]["id"])
                for it in items:
                    run_fn("""INSERT INTO invoice_items(invoice_id,position,description,quantity,unit,unit_price,total)
                              VALUES(?,?,?,?,?,?,?)""",
                           (iid, it["pos"], it["desc"], it["qty"], it["unit"], it["price"], it["total"]))
                refresh_totals_fn(iid)
                log_fn("invoice_created", inv_no)
                st.success(f"✅ Rechnung {inv_no} angelegt!")
                st.rerun()

    # ── Tab 2: Positionen verwalten ───────────────────────────
    with tabs[2]:
        invoices = df_fn("""
            SELECT i.id, i.invoice_no || ' – ' || c.company || ' (' || i.invoice_date || ')' AS label,
                   i.gross_total, i.status
            FROM invoices i JOIN customers c ON c.id=i.customer_id
            ORDER BY i.invoice_date DESC
        """)
        if invoices.empty:
            st.info("Keine Rechnungen vorhanden.")
            return

        sel = st.selectbox("Rechnung", invoices["label"].tolist(), key="pos_sel")
        iid = int(invoices[invoices["label"] == sel].iloc[0]["id"])
        inv_status = str(invoices[invoices["label"] == sel].iloc[0]["status"])

        # Vorhandene Positionen
        pos_data = df_fn("""
            SELECT id, position AS Pos, description AS Bezeichnung,
                   quantity AS Menge, unit AS Einheit,
                   unit_price AS Einzelpreis, total AS Gesamt
            FROM invoice_items WHERE invoice_id=? ORDER BY position
        """, (iid,))

        if not pos_data.empty:
            st.dataframe(pos_data.drop(columns=["id"]), use_container_width=True)
            # Einzelne Position löschen
            del_pos = st.selectbox("Position löschen", ["—"] + [f"Pos {r['Pos']}: {r['Bezeichnung']}" for _, r in pos_data.iterrows()])
            if del_pos != "—" and inv_status not in ("bezahlt", "storniert"):
                if st.button("🗑️ Position löschen"):
                    pos_num = int(del_pos.split(":")[0].replace("Pos ", ""))
                    pid = int(pos_data[pos_data["Pos"] == pos_num].iloc[0]["id"])
                    run_fn("DELETE FROM invoice_items WHERE id=?", (pid,))
                    refresh_totals_fn(iid)
                    st.success("Position gelöscht.")
                    st.rerun()

        if inv_status in ("bezahlt", "storniert"):
            st.info(f"Rechnung ist '{inv_status}' – Positionen können nicht mehr geändert werden.")
        else:
            with st.form("add_pos_v2", clear_on_submit=True):
                st.subheader("➕ Position hinzufügen")
                next_pos = int(pos_data["Pos"].max() + 1) if not pos_data.empty else 1
                a, b, c, d = st.columns([3, 1, 1, 1])
                p_desc = a.text_input("Bezeichnung *")
                p_qty = b.number_input("Menge", min_value=0.0, value=1.0, step=0.25)
                p_unit = c.text_input("Einheit", "Stunden")
                p_price = d.number_input("Einzelpreis (€)", min_value=0.0, value=21.0, step=0.5)
                if st.form_submit_button("➕ Position speichern", type="primary") and p_desc:
                    total = round(p_qty * p_price, 2)
                    run_fn("""INSERT INTO invoice_items(invoice_id,position,description,quantity,unit,unit_price,total)
                              VALUES(?,?,?,?,?,?,?)""",
                           (iid, next_pos, p_desc, p_qty, p_unit, p_price, total))
                    refresh_totals_fn(iid)
                    log_fn("invoice_item_added", f"inv={iid} pos={next_pos}")
                    st.success("✅ Position gespeichert!")
                    st.rerun()

        # Aktuelle Summen
        inv_row = df_fn("SELECT net_total,vat_rate,vat_total,gross_total,paid_amount FROM invoices WHERE id=?", (iid,)).iloc[0]
        c1, c2, c3 = st.columns(3)
        c1.metric("Netto", fmt_eur(float(inv_row["net_total"])))
        c2.metric(f"MwSt {float(inv_row['vat_rate']):.0f}%", fmt_eur(float(inv_row["vat_total"])))
        c3.metric("Brutto", fmt_eur(float(inv_row["gross_total"])))

    # ── Tab 3: Zahlung buchen ─────────────────────────────────
    with tabs[3]:
        invoices_open = df_fn("""
            SELECT i.id, i.invoice_no || ' – ' || c.company ||
                   ' | Offen: ' || ROUND(i.gross_total - i.paid_amount, 2) || ' €' AS label,
                   i.gross_total, i.paid_amount, i.status
            FROM invoices i JOIN customers c ON c.id=i.customer_id
            WHERE i.status NOT IN ('storniert','bezahlt')
            ORDER BY i.due_date ASC
        """)

        if invoices_open.empty:
            st.success("✅ Keine offenen Rechnungen.")
        else:
            sel = st.selectbox("Offene Rechnung", invoices_open["label"].tolist(), key="pay_sel")
            row = invoices_open[invoices_open["label"] == sel].iloc[0]
            iid = int(row["id"])
            offen = round(float(row["gross_total"]) - float(row["paid_amount"]), 2)

            c1, c2, c3 = st.columns(3)
            c1.metric("Brutto", fmt_eur(float(row["gross_total"])))
            c2.metric("Bereits bezahlt", fmt_eur(float(row["paid_amount"])))
            c3.metric("Noch offen", fmt_eur(offen))

            with st.form("pay_v2"):
                a, b, c = st.columns(3)
                amount = a.number_input("Zahlbetrag (€)", min_value=0.01, value=offen, step=10.0)
                paid_date = b.date_input("Zahlungsdatum", date.today())
                pay_method = c.selectbox("Zahlungsart", ["Überweisung", "Bar", "SEPA-Lastschrift", "PayPal", "Sonstiges"])
                note = st.text_input("Zahlungsnotiz / Verwendungszweck")
                full_payment = st.checkbox("Vollständig beglichen (auch bei Abweichung)", value=abs(amount - offen) < 0.02)

                if st.form_submit_button("💳 Zahlung speichern", type="primary"):
                    run_fn("UPDATE invoices SET paid_amount=COALESCE(paid_amount,0)+?, paid_date=? WHERE id=?",
                           (amount, paid_date.isoformat(), iid))
                    refresh_totals_fn(iid)
                    if full_payment:
                        run_fn("UPDATE invoices SET status='bezahlt' WHERE id=?", (iid,))
                    log_fn("payment_booked", f"inv={iid} amount={amount} method={pay_method}")
                    st.success(f"✅ Zahlung über {fmt_eur(amount)} gebucht!")
                    st.rerun()

        st.divider()
        st.subheader("📋 Alle Zahlungen (letzte 50)")
        payments = df_fn("""
            SELECT i.invoice_no AS Rechnung, c.company AS Kunde,
                   i.paid_date AS Zahlungsdatum, i.gross_total AS Brutto,
                   i.paid_amount AS Bezahlt, i.status AS Status
            FROM invoices i JOIN customers c ON c.id=i.customer_id
            WHERE i.paid_amount > 0
            ORDER BY i.paid_date DESC LIMIT 50
        """)
        if not payments.empty:
            st.dataframe(payments, use_container_width=True)

    # ── Tab 4: PDF & Versand ──────────────────────────────────
    with tabs[4]:
        invoices_pdf = df_fn("""
            SELECT i.id, i.invoice_no || ' – ' || c.company AS label, i.pdf_path, i.status
            FROM invoices i JOIN customers c ON c.id=i.customer_id
            ORDER BY i.invoice_date DESC
        """)
        if invoices_pdf.empty:
            st.info("Keine Rechnungen vorhanden.")
            return

        sel = st.selectbox("Rechnung", invoices_pdf["label"].tolist(), key="pdf_sel")
        row = invoices_pdf[invoices_pdf["label"] == sel].iloc[0]
        iid = int(row["id"])

        col1, col2 = st.columns(2)
        if col1.button("📄 PDF erstellen / aktualisieren", type="primary"):
            with st.spinner("PDF wird erstellt..."):
                try:
                    path = gen_pdf_fn(iid)
                    st.success(f"✅ PDF erstellt: {Path(str(path)).name}")
                    log_fn("pdf_generated", f"inv={iid}")
                    st.rerun()
                except Exception as e:
                    st.error(f"PDF-Fehler: {e}")

        pdf_path = str(row.get("pdf_path") or "")
        if pdf_path and Path(pdf_path).exists():
            col2.download_button(
                "📥 PDF herunterladen",
                Path(pdf_path).read_bytes(),
                file_name=Path(pdf_path).name,
                mime="application/pdf"
            )
        else:
            col2.info("Noch kein PDF – bitte erst erstellen.")

        # Direkte E-Mail aus diesem Tab
        st.divider()
        st.subheader("✉️ Direkt per E-Mail senden")
        inv_detail = df_fn("SELECT i.*, c.email, c.company FROM invoices i JOIN customers c ON c.id=i.customer_id WHERE i.id=?", (iid,)).iloc[0]
        email_to = st.text_input("Empfänger", str(inv_detail.get("email") or ""))
        email_kind = st.selectbox("Art", ["Rechnung", "1. Mahnung", "2. Mahnung", "Letzte Mahnung"])
        if st.button("🚀 Per E-Mail senden") and email_to:
            st.info(f"E-Mail '{email_kind}' an {email_to} wird vorbereitet. Bitte im E-Mail-Bereich absenden.")

    # ── Tab 5: Bearbeiten / Status ────────────────────────────
    with tabs[5]:
        invoices_edit = df_fn("""
            SELECT i.id, i.invoice_no || ' – ' || c.company AS label,
                   i.invoice_no, i.invoice_date, i.service_date, i.due_date,
                   i.description, i.vat_rate, i.status, i.notes
            FROM invoices i JOIN customers c ON c.id=i.customer_id
            ORDER BY i.invoice_date DESC
        """)
        if invoices_edit.empty:
            return

        sel = st.selectbox("Rechnung auswählen", invoices_edit["label"].tolist(), key="edit_sel")
        row = invoices_edit[invoices_edit["label"] == sel].iloc[0]
        iid = int(row["id"])

        with st.form("edit_inv"):
            a, b = st.columns(2)
            inv_no_e = a.text_input("Rechnungsnummer", str(row["invoice_no"]))
            status_e = b.selectbox("Status", INV_STATUS, index=INV_STATUS.index(str(row["status"])) if str(row["status"]) in INV_STATUS else 0)
            c1, c2, c3 = st.columns(3)
            inv_date_e = c1.text_input("Rechnungsdatum", str(row["invoice_date"]))
            service_date_e = c2.text_input("Leistungszeitraum", str(row.get("service_date") or ""))
            due_date_e = c3.text_input("Fällig bis", str(row.get("due_date") or ""))
            desc_e = st.text_input("Beschreibung", str(row.get("description") or ""))
            notes_e = st.text_area("Notizen", str(row.get("notes") or ""))
            col1, col2 = st.columns(2)
            save = col1.form_submit_button("💾 Speichern", type="primary")
            storno = col2.form_submit_button("❌ Stornieren")

        if save:
            run_fn("""UPDATE invoices SET invoice_no=?,invoice_date=?,service_date=?,due_date=?,
                      description=?,status=?,notes=? WHERE id=?""",
                   (inv_no_e, inv_date_e, service_date_e, due_date_e, desc_e, status_e, notes_e, iid))
            log_fn("invoice_updated", f"id={iid} status={status_e}")
            st.success("✅ Rechnung aktualisiert!")
            st.rerun()
        if storno:
            run_fn("UPDATE invoices SET status='storniert' WHERE id=?", (iid,))
            log_fn("invoice_cancelled", f"id={iid}")
            st.warning("Rechnung wurde storniert.")
            st.rerun()


# ─────────────────────────────────────────────────────────────
# 2. Vollständige Kontakthistorie
# ─────────────────────────────────────────────────────────────

def page_contacts_v2(run_fn, df_fn, next_number_fn, log_fn) -> None:
    st.title("📞 Kontakthistorie")

    CONTACT_TYPES = ["Telefon", "E-Mail", "Vor-Ort-Termin", "Video-Call", "WhatsApp", "Brief", "Sonstiges"]

    tabs = st.tabs(["📋 Übersicht", "➕ Kontakt erfassen", "📊 Timeline"])

    with tabs[0]:
        q = st.text_input("🔍 Suche (Kunde, Betreff, Notiz)", "")
        if q:
            data = df_fn("""
                SELECT co.id, co.contact_date AS Datum, c.company AS Kunde,
                       co.contact_person AS Ansprechperson,
                       co.contact_type AS Art, co.subject AS Betreff,
                       co.note AS Notiz, co.next_followup AS Wiedervorlage,
                       co.result AS Ergebnis
                FROM contacts co JOIN customers c ON c.id=co.customer_id
                WHERE c.company LIKE ? OR co.subject LIKE ? OR co.note LIKE ?
                ORDER BY co.contact_date DESC
            """, (f"%{q}%", f"%{q}%", f"%{q}%"))
        else:
            data = df_fn("""
                SELECT co.id, co.contact_date AS Datum, c.company AS Kunde,
                       co.contact_person AS Ansprechperson,
                       co.contact_type AS Art, co.subject AS Betreff,
                       co.note AS Notiz, co.next_followup AS Wiedervorlage,
                       co.result AS Ergebnis
                FROM contacts co JOIN customers c ON c.id=co.customer_id
                ORDER BY co.contact_date DESC LIMIT 200
            """)

        if not data.empty:
            st.dataframe(data.drop(columns=["id"]), use_container_width=True, height=400)
            csv = data.drop(columns=["id"]).to_csv(index=False, sep=";").encode("utf-8-sig")
            st.download_button("📥 CSV-Export", csv, "kontakthistorie.csv", "text/csv")
        else:
            st.info("Keine Kontakteinträge gefunden.")

        # Wiedervorlagen heute & morgen
        today = date.today().isoformat()
        tomorrow = (date.today() + timedelta(days=1)).isoformat()
        followups = df_fn("""
            SELECT co.next_followup AS Datum, c.company AS Kunde,
                   co.subject AS Betreff, co.contact_person AS Ansprechperson
            FROM contacts co JOIN customers c ON c.id=co.customer_id
            WHERE co.next_followup BETWEEN ? AND ?
            ORDER BY co.next_followup
        """, (today, tomorrow))
        if not followups.empty:
            st.warning(f"🔔 **{len(followups)} Wiedervorlage(n) heute/morgen:**")
            st.dataframe(followups, use_container_width=True)

    with tabs[1]:
        customers = df_fn("SELECT id, customer_no || ' – ' || company AS label FROM customers ORDER BY company")
        if customers.empty:
            st.warning("Zuerst Kunden anlegen.")
            return

        with st.form("contact_form", clear_on_submit=True):
            a, b = st.columns(2)
            cust_label = a.selectbox("Kunde *", customers["label"].tolist())
            contact_date = b.date_input("Datum", date.today())
            contact_person = a.text_input("Ansprechperson beim Kunden")
            contact_type = b.selectbox("Art", CONTACT_TYPES)
            subject = st.text_input("Betreff / Thema *")
            note = st.text_area("Gesprächsnotiz / Inhalt")
            result = st.selectbox("Ergebnis", ["offen", "positiv", "negativ", "neutral", "Folgetermin vereinbart"])
            next_followup = st.date_input("Wiedervorlage am", value=None)

            submitted = st.form_submit_button("💾 Kontakt speichern", type="primary")

        if submitted:
            if not subject.strip():
                st.error("Betreff ist Pflichtfeld.")
            else:
                cid = int(customers[customers["label"] == cust_label].iloc[0]["id"])
                run_fn("""INSERT INTO contacts(customer_id,contact_date,contact_person,contact_type,subject,note,result,next_followup)
                          VALUES(?,?,?,?,?,?,?,?)""",
                       (cid, contact_date.isoformat(), contact_person, contact_type, subject, note, result,
                        next_followup.isoformat() if next_followup else None))
                log_fn("contact_created", f"cid={cid} subject={subject}")
                st.success("✅ Kontakt gespeichert!")
                st.rerun()

    with tabs[2]:
        st.subheader("📊 Kontakt-Timeline nach Kunde")
        customers2 = df_fn("SELECT id, company AS label FROM customers ORDER BY company")
        if not customers2.empty:
            sel = st.selectbox("Kunde", customers2["label"].tolist())
            cid2 = int(customers2[customers2["label"] == sel].iloc[0]["id"])
            timeline = df_fn("""
                SELECT contact_date AS Datum, contact_type AS Art,
                       subject AS Betreff, note AS Notiz,
                       result AS Ergebnis, next_followup AS Wiedervorlage
                FROM contacts WHERE customer_id=?
                ORDER BY contact_date DESC
            """, (cid2,))
            if not timeline.empty:
                # Einfache Timeline-Darstellung
                for _, row in timeline.iterrows():
                    icons = {"Telefon": "📞", "E-Mail": "📧", "Vor-Ort-Termin": "🤝",
                             "Video-Call": "📹", "WhatsApp": "💬", "Brief": "✉️", "Sonstiges": "📌"}
                    icon = icons.get(str(row.get("Art", "")), "•")
                    result_colors = {"positiv": "#27ae60", "negativ": "#c0392b",
                                     "neutral": "#7f8c8d", "offen": "#2980b9",
                                     "Folgetermin vereinbart": "#e67e22"}
                    rc = result_colors.get(str(row.get("Ergebnis", "")), "#888")
                    st.markdown(
                        f'<div style="border-left:3px solid {rc};padding:8px 12px;margin-bottom:8px;background:#1a1f2e;border-radius:4px;">'
                        f'<strong>{row["Datum"]}</strong> {icon} {row["Art"]} – <strong>{row["Betreff"]}</strong>'
                        f'<span style="color:{rc};float:right;font-size:.8rem;">{row["Ergebnis"]}</span><br/>'
                        f'<span style="color:#9aa0b4;font-size:.88rem;">{row["Notiz"]}</span>'
                        + (f'<br/><span style="font-size:.8rem;">🔔 Wiedervorlage: {row["Wiedervorlage"]}</span>' if row.get("Wiedervorlage") else "")
                        + '</div>',
                        unsafe_allow_html=True
                    )
            else:
                st.info("Keine Kontakthistorie für diesen Kunden.")


# ─────────────────────────────────────────────────────────────
# 3. Vollständige Benutzerverwaltung
# ─────────────────────────────────────────────────────────────

def page_users_v2(run_fn, df_fn, hash_pw_fn, current_user_fn, log_fn) -> None:
    st.title("👤 Benutzerverwaltung")

    u = current_user_fn() or {}
    if u.get("role", "").lower() not in ("admin", "administrator"):
        st.error("❌ Nur Administratoren können Benutzer verwalten.")
        return

    ROLES = ["admin", "manager", "user", "readonly"]

    tabs = st.tabs(["👥 Übersicht", "➕ Neuer Benutzer", "✏️ Bearbeiten / Passwort-Reset"])

    with tabs[0]:
        users = df_fn("""
            SELECT id, username AS Benutzer, role AS Rolle,
                   CASE WHEN active=1 THEN '✅ aktiv' ELSE '⛔ inaktiv' END AS Status,
                   created_at AS Erstellt, last_login AS Letzter_Login
            FROM users ORDER BY active DESC, username
        """)
        if not users.empty:
            st.dataframe(users.drop(columns=["id"]), use_container_width=True)
            st.caption(f"{len(users)} Benutzer · {int((users['Status']=='✅ aktiv').sum())} aktiv")

    with tabs[1]:
        with st.form("new_user", clear_on_submit=True):
            a, b = st.columns(2)
            username = a.text_input("Benutzername *")
            role = b.selectbox("Rolle", ROLES)
            pw1 = a.text_input("Passwort *", type="password")
            pw2 = b.text_input("Passwort wiederholen *", type="password")
            active = a.checkbox("Aktiv", value=True)
            submitted = st.form_submit_button("💾 Benutzer anlegen", type="primary")

        if submitted:
            if not username.strip():
                st.error("Benutzername ist Pflichtfeld.")
            elif pw1 != pw2:
                st.error("Passwörter stimmen nicht überein.")
            elif len(pw1) < 8:
                st.error("Passwort muss mindestens 8 Zeichen haben.")
            elif not df_fn("SELECT id FROM users WHERE username=?", (username,)).empty:
                st.error(f"Benutzer '{username}' existiert bereits.")
            else:
                run_fn("INSERT INTO users(username,password_hash,role,active) VALUES(?,?,?,?)",
                       (username, hash_pw_fn(pw1), role, 1 if active else 0))
                log_fn("user_created", username)
                st.success(f"✅ Benutzer '{username}' (Rolle: {role}) angelegt!")
                st.rerun()

    with tabs[2]:
        users_raw = df_fn("SELECT id, username || ' (' || role || ')' AS label, username, role, active FROM users ORDER BY username")
        if users_raw.empty:
            return
        sel = st.selectbox("Benutzer", users_raw["label"].tolist())
        uid = int(users_raw[users_raw["label"] == sel].iloc[0]["id"])
        row = users_raw[users_raw["label"] == sel].iloc[0]

        with st.form("edit_user"):
            a, b = st.columns(2)
            new_role = a.selectbox("Rolle", ROLES, index=ROLES.index(str(row["role"])) if str(row["role"]) in ROLES else 1)
            new_active = b.checkbox("Aktiv", value=bool(row["active"]))
            st.subheader("Passwort zurücksetzen (leer lassen = nicht ändern)")
            new_pw1 = a.text_input("Neues Passwort", type="password")
            new_pw2 = b.text_input("Wiederholen", type="password")
            save = st.form_submit_button("💾 Speichern", type="primary")

        if save:
            run_fn("UPDATE users SET role=?,active=? WHERE id=?", (new_role, 1 if new_active else 0, uid))
            if new_pw1 and new_pw1 == new_pw2 and len(new_pw1) >= 8:
                run_fn("UPDATE users SET password_hash=? WHERE id=?", (hash_pw_fn(new_pw1), uid))
                st.success("✅ Passwort geändert.")
            elif new_pw1:
                st.warning("Passwort nicht geändert (Passwörter stimmen nicht überein oder < 8 Zeichen).")
            log_fn("user_updated", f"id={uid} role={new_role} active={new_active}")
            st.success("✅ Benutzer aktualisiert!")
            st.rerun()

        st.divider()
        if str(row.get("username")) != u.get("username"):
            if st.button("⛔ Benutzer sperren / deaktivieren"):
                run_fn("UPDATE users SET active=0 WHERE id=?", (uid,))
                log_fn("user_deactivated", f"id={uid}")
                st.warning("Benutzer deaktiviert.")
                st.rerun()
        else:
            st.caption("Du kannst dich nicht selbst sperren.")


# ─────────────────────────────────────────────────────────────
# 4. Verbesserte Automatik-Seite
# ─────────────────────────────────────────────────────────────

def page_automation_v2(run_fn, df_fn, log_fn,
                       mark_overdue_fn, daily_automation_fn,
                       queue_overdue_fn, calc_kpis_fn,
                       create_backup_fn, verify_backup_fn,
                       get_setting_fn) -> None:
    st.title("⚙️ Automatik & Monitoring")

    tabs = st.tabs([
        "🔄 Tagesroutine", "🔴 Mahnwesen", "📊 KPIs & Trends",
        "💾 Backup-Monitor", "📋 Automatik-Log", "⏰ Cron-Einrichtung"
    ])

    with tabs[0]:
        st.subheader("Tagesroutine")
        st.markdown("""
        Die Tagesroutine führt folgende Schritte durch:
        - Überfällige Rechnungen markieren
        - Mahnungs-E-Mails vorbereiten (optional senden)
        - KPIs berechnen und speichern
        - Vollbackup erstellen
        - Automatik-Log eintragen
        """)
        a, b = st.columns(2)
        send_now = a.checkbox("Mahnungen sofort per SMTP senden",
                              value=get_setting_fn("auto_send_reminders", "0") == "1")
        do_backup = b.checkbox("Backup nach Routine erstellen", value=True)

        if st.button("▶️ Tagesroutine jetzt starten", type="primary"):
            with st.spinner("Routine läuft..."):
                try:
                    results = daily_automation_fn(send_reminders=send_now, create_backup=do_backup)
                    for line in results:
                        st.success(line)
                    log_fn("daily_routine_manual", "ausgeführt über UI")
                except Exception as e:
                    st.error(f"Fehler: {e}")

        st.divider()
        st.subheader("Automatik-Status")
        last_auto = df_fn("SELECT MAX(created_at) AS ts FROM automation_log WHERE action='daily_routine'")
        if not last_auto.empty and last_auto.iloc[0]["ts"]:
            ts = str(last_auto.iloc[0]["ts"])[:16]
            age_h = (datetime.now() - datetime.fromisoformat(ts)).total_seconds() / 3600
            if age_h > 25:
                st.warning(f"⚠️ Letzte Routine: **{ts}** ({age_h:.0f} Stunden her) — Cron läuft nicht?")
            else:
                st.success(f"✅ Letzte Routine: **{ts}** ({age_h:.1f} Stunden her)")
        else:
            st.info("Noch keine automatische Routine ausgeführt.")

    with tabs[1]:
        st.subheader("🔴 Offene und überfällige Rechnungen")
        if st.button("Überfällige Rechnungen neu markieren"):
            mark_overdue_fn()
            st.success("Erledigt.")
            st.rerun()

        overdue = df_fn("""
            SELECT i.invoice_no AS Nr, c.company AS Kunde, c.email AS E_Mail,
                   i.invoice_date AS Datum, i.due_date AS Fällig_seit,
                   ROUND(i.gross_total - i.paid_amount, 2) AS Offen_EUR,
                   CAST(julianday('now') - julianday(i.due_date) AS INT) AS Tage_überfällig
            FROM invoices i JOIN customers c ON c.id=i.customer_id
            WHERE i.status = 'ueberfaellig'
            ORDER BY i.due_date ASC
        """)

        if overdue.empty:
            st.success("✅ Keine überfälligen Rechnungen!")
        else:
            total_overdue = float(overdue["Offen_EUR"].sum())
            c1, c2 = st.columns(2)
            c1.metric("Überfällige Rechnungen", len(overdue))
            c2.metric("Ausstehender Betrag", fmt_eur(total_overdue))
            st.dataframe(overdue, use_container_width=True)

            col1, col2 = st.columns(2)
            if col1.button("📨 Mahnungen als Entwurf vorbereiten"):
                try:
                    created, sent = queue_overdue_fn(False)
                    st.success(f"{created} Mahnungs-Entwürfe erstellt.")
                except Exception as e:
                    st.error(f"Fehler: {e}")
            if col2.button("🚀 Mahnungen jetzt per SMTP senden"):
                try:
                    created, sent = queue_overdue_fn(True)
                    st.success(f"{created} vorbereitet, {sent} gesendet.")
                except Exception as e:
                    st.error(f"Fehler: {e}")

    with tabs[2]:
        st.subheader("📊 KPIs")
        if st.button("KPIs heute berechnen und speichern"):
            try:
                kpis = calc_kpis_fn()
                st.json(kpis)
                st.success("✅ KPIs gespeichert.")
            except Exception as e:
                st.error(f"Fehler: {e}")

        kpi_history = df_fn("SELECT * FROM daily_kpis ORDER BY kpi_date DESC LIMIT 90")
        if not kpi_history.empty:
            st.dataframe(kpi_history, use_container_width=True)
            # Trend-Chart
            if "total_invoiced" in kpi_history.columns and "total_paid" in kpi_history.columns:
                chart_data = kpi_history[["kpi_date","total_invoiced","total_paid"]].set_index("kpi_date")
                st.line_chart(chart_data)
        else:
            st.info("Noch keine KPI-Daten.")

    with tabs[3]:
        st.subheader("💾 Backup-Monitor")
        col1, col2 = st.columns(2)
        if col1.button("🔄 Backup jetzt erstellen"):
            with st.spinner("Backup läuft..."):
                try:
                    b = create_backup_fn("manuell über Automatik")
                    b_path = str(b)
                    size = Path(b_path).stat().st_size if Path(b_path).exists() else 0
                    run_fn("INSERT INTO backups(file_path,file_size,note) VALUES(?,?,?)",
                           (b_path, size, "manuell über Automatik"))
                    st.success(f"✅ Backup: {Path(b_path).name} ({size/1024:.0f} KB)")
                except Exception as e:
                    st.error(f"Fehler: {e}")
        if col2.button("🔍 Letztes Backup prüfen"):
            try:
                ok, msg = verify_backup_fn()
                if ok:
                    st.success(f"✅ {msg}")
                else:
                    st.error(f"❌ {msg}")
            except Exception as e:
                st.error(f"Fehler: {e}")

        backups = df_fn("SELECT file_path AS Datei, file_size AS Größe_Bytes, note AS Notiz, created_at AS Erstellt FROM backups ORDER BY created_at DESC LIMIT 20")
        if not backups.empty:
            backups["Größe_KB"] = (backups["Größe_Bytes"] / 1024).round(0).astype(int)
            st.dataframe(backups[["Erstellt","Datei","Größe_KB","Notiz"]], use_container_width=True)
        else:
            st.info("Noch keine Backups vorhanden.")

    with tabs[4]:
        auto_log = df_fn("SELECT created_at AS Zeit, action AS Aktion, result AS Ergebnis FROM automation_log ORDER BY created_at DESC LIMIT 200")
        if not auto_log.empty:
            st.dataframe(auto_log, use_container_width=True, height=400)
        else:
            st.info("Noch keine Automatik-Log-Einträge.")

    with tabs[5]:
        st.subheader("⏰ Cron-Einrichtung (Linux/Mac Server)")
        st.markdown("""
Für vollständige Automatisierung auf einem Linux-Server folgende Crontab-Einträge nutzen.  
Bearbeiten mit: `crontab -e`
        """)
        cron_examples = """# Byblos CRM – Automatische Tagesroutine
# Täglich um 06:00 Uhr
0 6 * * * cd /pfad/zu/byblos_crm_app && python3 -c "
import app; app.init_db()
results = app.run_daily_automation(send_reminders=True, create_backup=True)
print('\\n'.join(results))
" >> /var/log/byblos_crm.log 2>&1

# Wöchentliches Backup jeden Sonntag 03:00
0 3 * * 0 cd /pfad/zu/byblos_crm_app && python3 -c "
import app; app.init_db()
b = app.create_full_backup('woechentlich')
print(f'Backup: {b}')
" >> /var/log/byblos_crm_backup.log 2>&1"""
        st.code(cron_examples, language="bash")

        st.markdown("**Windows (Task Scheduler):**")
        task_xml = """<!-- ByblosCRM Tagesroutine - als .xml importieren in Aufgabenplanung -->
<!-- Aufgabenplanung → Aufgabe importieren → diese Datei wählen -->
<Task>
  <Triggers>
    <CalendarTrigger>
      <StartBoundary>2024-01-01T06:00:00</StartBoundary>
      <ScheduleByDay><DaysInterval>1</DaysInterval></ScheduleByDay>
    </CalendarTrigger>
  </Triggers>
  <Actions>
    <Exec>
      <Command>python.exe</Command>
      <Arguments>-m streamlit run app.py --server.headless true</Arguments>
      <WorkingDirectory>C:\\ByblosCRM\\byblos_crm_app</WorkingDirectory>
    </Exec>
  </Actions>
</Task>"""
        st.code(task_xml, language="xml")


# ─────────────────────────────────────────────────────────────
# 5. Verbessertes Archiv & GoBD
# ─────────────────────────────────────────────────────────────

def page_archive_v2(run_fn, df_fn, base_dir: Path, log_fn) -> None:
    st.title("🗄️ Archiv & GoBD-Konformität")

    tabs = st.tabs(["🔍 Dokumentenarchiv", "📋 GoBD-Checkliste", "📤 Jahresabschluss-Export", "ℹ️ GoBD-Info"])

    with tabs[0]:
        st.subheader("Dokumente suchen")
        col_s, col_f = st.columns([3, 1])
        q = col_s.text_input("🔍 Suche (Dateiname, Typ, Beschreibung)")
        doc_type = col_f.selectbox("Dokumenttyp", ["alle", "rechnung", "ausgabe", "backup", "import", "sonstiges"])

        # Alle PDF-Dateien aus erzeugten Verzeichnissen sammeln
        search_dirs = [
            base_dir / "generated",
            base_dir / "imports",
            base_dir / "backups",
            base_dir / "archive",
        ]
        files = []
        for d in search_dirs:
            if d.exists():
                for f in d.rglob("*"):
                    if f.is_file() and (not q or q.lower() in f.name.lower()):
                        files.append({
                            "Datei": f.name,
                            "Typ": d.name,
                            "Größe_KB": round(f.stat().st_size / 1024, 1),
                            "Geändert": datetime.fromtimestamp(f.stat().st_mtime).strftime("%Y-%m-%d %H:%M"),
                            "_path": str(f),
                        })

        if files:
            file_df = pd.DataFrame(files)
            if doc_type != "alle":
                file_df = file_df[file_df["Typ"] == doc_type]
            st.caption(f"{len(file_df)} Dokument(e)")
            st.dataframe(file_df[["Datei","Typ","Größe_KB","Geändert"]], use_container_width=True)

            sel_file = st.selectbox("Datei herunterladen", file_df["Datei"].tolist())
            sel_path = file_df[file_df["Datei"] == sel_file].iloc[0]["_path"]
            if Path(sel_path).exists():
                mime = "application/pdf" if sel_path.endswith(".pdf") else "application/octet-stream"
                st.download_button(f"📥 {sel_file} herunterladen",
                                   Path(sel_path).read_bytes(),
                                   file_name=sel_file, mime=mime)
        else:
            st.info("Keine Dokumente im Archiv gefunden.")

        st.divider()
        st.subheader("📂 Datei ins Archiv hochladen")
        uploaded = st.file_uploader("Dokument hochladen (PDF, XLSX, JPG)", type=["pdf","xlsx","csv","jpg","png"])
        if uploaded:
            archive_dir = base_dir / "archive"
            archive_dir.mkdir(exist_ok=True)
            target = archive_dir / uploaded.name
            target.write_bytes(uploaded.read())
            log_fn("archive_upload", uploaded.name)
            st.success(f"✅ '{uploaded.name}' im Archiv gespeichert.")

    with tabs[1]:
        st.subheader("GoBD-Konformitätsprüfung")
        checks = []

        # Datenbank vorhanden?
        db_ok = (base_dir / "byblos_crm.db").exists()
        checks.append(("SQLite-Datenbank vorhanden", db_ok, "Datenbankdatei byblos_crm.db gefunden"))

        # Backup vorhanden?
        backup_data = df_fn("SELECT MAX(created_at) AS ts FROM backups")
        backup_ok = not backup_data.empty and backup_data.iloc[0]["ts"] is not None
        backup_age = 999
        if backup_ok:
            try:
                backup_age = (datetime.now() - datetime.fromisoformat(str(backup_data.iloc[0]["ts"])[:19])).days
            except Exception:
                backup_age = 999
        backup_fresh = backup_age <= 7
        checks.append(("Backup jünger als 7 Tage", backup_fresh,
                        f"Letztes Backup: {backup_age} Tage alt" if backup_ok else "Kein Backup vorhanden"))

        # Rechnungen vorhanden?
        inv_count = int(df_fn("SELECT COUNT(*) AS n FROM invoices").iloc[0]["n"])
        checks.append(("Rechnungen archiviert", inv_count > 0, f"{inv_count} Rechnungen in der Datenbank"))

        # PDFs vorhanden?
        pdf_count = len(list((base_dir / "generated").rglob("*.pdf"))) if (base_dir / "generated").exists() else 0
        checks.append(("Rechnungs-PDFs vorhanden", pdf_count > 0, f"{pdf_count} PDF(s) im Ordner 'generated'"))

        # Audit-Log aktiv?
        audit_count = int(df_fn("SELECT COUNT(*) AS n FROM audit_log").iloc[0]["n"])
        checks.append(("Audit-Log aktiv", audit_count > 0, f"{audit_count} Einträge im Audit-Log"))

        # Ausgaben vollständig?
        exp_no_receipt = int(df_fn("SELECT COUNT(*) AS n FROM expenses WHERE receipt_path IS NULL OR receipt_path=''").iloc[0]["n"])
        checks.append(("Ausgaben mit Belegen", exp_no_receipt == 0,
                        "Alle Ausgaben haben Belege" if exp_no_receipt == 0
                        else f"⚠️ {exp_no_receipt} Ausgabe(n) ohne Beleg"))

        for label, ok, detail in checks:
            icon = "✅" if ok else "❌"
            color = "#27ae60" if ok else "#c0392b"
            st.markdown(
                f'<div style="background:{color}11;border-left:4px solid {color};padding:8px 12px;border-radius:4px;margin-bottom:6px;">'
                f'{icon} <strong>{label}</strong><br/><span style="font-size:.85rem;color:#aaa;">{detail}</span></div>',
                unsafe_allow_html=True
            )

        score = sum(1 for _, ok, _ in checks if ok)
        st.metric("GoBD-Score", f"{score}/{len(checks)}", f"{'✅ Konform' if score == len(checks) else '⚠️ Handlungsbedarf'}")

    with tabs[2]:
        st.subheader("Jahresabschluss-Export")
        year = st.selectbox("Jahr", [str(y) for y in range(date.today().year, date.today().year - 10, -1)])

        if st.button("📊 Jahresabschluss erstellen", type="primary"):
            with st.spinner("Exportiere..."):
                try:
                    inv_year = df_fn("""
                        SELECT i.invoice_no, c.company, i.invoice_date, i.service_date,
                               i.description, i.net_total, i.vat_rate, i.vat_total,
                               i.gross_total, i.paid_amount, i.status
                        FROM invoices i JOIN customers c ON c.id=i.customer_id
                        WHERE substr(i.invoice_date,1,4)=? ORDER BY i.invoice_date
                    """, (year,))
                    exp_year = df_fn("""
                        SELECT e.expense_date, e.expense_no, s.name AS lieferant,
                               e.description, e.category, e.net_amount, e.vat_rate,
                               e.vat_amount, e.gross_amount, e.status
                        FROM expenses e LEFT JOIN suppliers s ON s.id=e.supplier_id
                        WHERE substr(e.expense_date,1,4)=? ORDER BY e.expense_date
                    """, (year,))

                    export_path = base_dir / f"byblos_jahresabschluss_{year}.xlsx"
                    with pd.ExcelWriter(str(export_path), engine="openpyxl") as writer:
                        if not inv_year.empty:
                            inv_year.to_excel(writer, sheet_name=f"Rechnungen_{year}", index=False)
                        if not exp_year.empty:
                            exp_year.to_excel(writer, sheet_name=f"Ausgaben_{year}", index=False)

                        # Zusammenfassung
                        summary_data = {
                            "Kennzahl": ["Umsatz gesamt", "Umsatz bezahlt", "Ausgaben gesamt", "Ergebnis (grob)"],
                            "Wert_EUR": [
                                float(inv_year["gross_total"].sum()) if not inv_year.empty else 0,
                                float(inv_year[inv_year["status"]=="bezahlt"]["gross_total"].sum()) if not inv_year.empty else 0,
                                float(exp_year["gross_amount"].sum()) if not exp_year.empty else 0,
                                float(inv_year[inv_year["status"]=="bezahlt"]["gross_total"].sum() if not inv_year.empty else 0) - float(exp_year["gross_amount"].sum() if not exp_year.empty else 0),
                            ]
                        }
                        pd.DataFrame(summary_data).to_excel(writer, sheet_name="Zusammenfassung", index=False)

                    log_fn("jahresabschluss_export", year)
                    st.success(f"✅ Jahresabschluss {year} erstellt!")
                    st.download_button(
                        f"📥 Jahresabschluss {year} herunterladen",
                        export_path.read_bytes(),
                        file_name=export_path.name,
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
                except Exception as e:
                    st.error(f"Export-Fehler: {e}")

    with tabs[3]:
        st.subheader("ℹ️ GoBD-Grundsätze")
        st.markdown("""
**Grundsätze ordnungsmäßiger Buchführung und Datenzugriff (GoBD)**

Die GoBD regeln die ordnungsmäßige Führung und Aufbewahrung von Büchern, Aufzeichnungen und Unterlagen in elektronischer Form.

**Wichtige Anforderungen:**

| Anforderung | Byblos CRM |
|---|---|
| Vollständigkeit | ✅ Alle Buchungen in SQLite-DB |
| Richtigkeit | ✅ Audit-Log aller Änderungen |
| Zeitgerechtheit | ✅ Zeitstempel bei allen Einträgen |
| Ordnung | ✅ Nummerierte Belege (RE-, AUS-, MA-) |
| Nachvollziehbarkeit | ✅ Audit-Log mit Benutzer + Aktion |
| Unveränderlichkeit (Schutz) | ⚠️ Bitte regelmäßige Backups sichern |
| Aufbewahrungsfristen | 10 Jahre für Rechnungen |
| Digitale Belege | ✅ PDF-Archiv |

**Aufbewahrungsfristen:**
- Rechnungen, Buchungsbelege: **10 Jahre**
- Verträge, Geschäftsbriefe: **6 Jahre**
- Lohnunterlagen: **10 Jahre**

**Hinweis:** Diese Software ist ein operatives CRM-Werkzeug.  
Die steuerliche Buchführung ist mit einem Steuerberater abzustimmen.
        """)
