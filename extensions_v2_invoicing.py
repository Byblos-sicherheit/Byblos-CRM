"""CRM Stufe 6 – Seite "Rechnungsentwurf": Auftrag → Entwurf → Pflichtangaben → Freigabe → Testexport."""
from __future__ import annotations

from datetime import date

import streamlit as st

import crm_stage6


def _new_tab(conn, log_fn) -> None:
    rows = conn.execute("""SELECT o.id, o.offer_no, c.company, o.net_total FROM offers o JOIN customers c ON c.id=o.customer_id
                           WHERE o.status='angenommen' AND o.id NOT IN (SELECT offer_id FROM invoice_drafts)
                           ORDER BY o.id DESC""").fetchall()
    if not rows:
        st.info("Keine angenommenen Angebote ohne Rechnungsentwurf.")
        return
    labels = {f"{r[1]} – {r[2]} – {r[3]:.2f} € netto": r[0] for r in rows}
    pick = st.selectbox("Angenommenes Angebot (Auftrag)", list(labels), key="inv_offer")
    if st.button("🧾 Rechnungsentwurf anlegen"):
        draft = crm_stage6.draft_from_offer(conn, labels[pick])
        log_fn("invoice_draft", f"Angebot {labels[pick]} → Entwurf {draft}")
        st.success(f"Entwurf #{draft} angelegt. Unter „Prüfen & Freigeben“ vervollständigen.")


def _edit_form(conn, d) -> None:
    with st.form(f"inv_edit_{d['id']}"):
        desc = st.text_area("Leistungsbeschreibung", d["description"] or "")
        a, b = st.columns(2)
        service = a.date_input("Leistungsdatum / Ende Leistungszeitraum",
                               date.fromisoformat(d["service_date"]) if d["service_date"] else date.today())
        due = b.number_input("Zahlungsziel (Tage)", min_value=0, max_value=120, value=int(d["due_days"]))
        net = a.number_input("Netto (€)", min_value=0.0, value=float(d["net_total"]), step=50.0)
        cases = list(crm_stage6.TAX_CASES)
        case = b.selectbox("Steuerfall (mit Steuerberater abstimmen)", cases, index=cases.index(d["tax_case"]))
        reason = a.text_input("Begründung Steuerfall (Pflicht außer bei 19 %)", d["tax_reason"] or "")
        vat_id = b.text_input("USt-IdNr. Leistungsempfänger (Pflicht bei § 13b)", d["recipient_vat_id"] or "")
        if st.form_submit_button("💾 Speichern"):
            crm_stage6.update_draft(conn, d["id"], description=desc, service_date=service.isoformat(), due_days=int(due),
                                    net_total=net, tax_case=case, tax_reason=reason, recipient_vat_id=vat_id)
            st.rerun()


def _review_tab(conn, log_fn, user, role) -> None:
    rows = conn.execute("""SELECT d.id, c.company, d.sparte, d.net_total FROM invoice_drafts d
                           JOIN customers c ON c.id=d.customer_id WHERE d.status='Entwurf' ORDER BY d.id DESC""").fetchall()
    if not rows:
        st.info("Keine offenen Rechnungsentwürfe.")
        return
    labels = {f"Entwurf #{r[0]} – {r[1]} ({r[2]}) – {r[3]:.2f} € netto": r[0] for r in rows}
    d = crm_stage6.get_draft(conn, labels[st.selectbox("Entwurf", list(labels), key="inv_draft")])
    issuer = crm_stage6.ISSUERS[d["sparte"]]
    st.caption(f"Absender: {issuer['name']} · {issuer['street']}, {issuer['city']} · {issuer['email']} · USt-IdNr. {issuer['vat_id']}")
    _edit_form(conn, d)
    checks = crm_stage6.check(conn, d["id"])
    st.table([{"Pflichtangabe": n, "Status": "✅" if ok else "❌", "Hinweis": h} for n, ok, h in checks])
    if not all(ok for _, ok, _ in checks):
        st.warning("Freigabe erst, wenn alle Pflichtangaben erfüllt sind.")
        return
    if role not in crm_stage6.FINANCE_ROLES:
        st.info("Freigabe nur durch Inhaber/Admin oder Buchhaltung.")
        return
    confirmed = st.checkbox("Ich habe den Entwurf geprüft. Rechnung jetzt mit fortlaufender Nummer erstellen.", key="inv_confirm")
    if st.button("✅ Freigeben", disabled=not confirmed):
        try:
            _, invoice_no = crm_stage6.approve(conn, d["id"], user, role, confirmed)
        except (ValueError, PermissionError) as exc:
            st.error(str(exc))
        else:
            log_fn("invoice_approve", f"Entwurf {d['id']} → {invoice_no}")
            st.success(f"Rechnung {invoice_no} erstellt (Status offen). Ein Versand erfolgt nicht automatisch.")


def _export_tab(conn, log_fn, user) -> None:
    st.warning("Testexport: bucht nichts und ändert keine Rechnung. Konten und Format vor produktiver Nutzung "
               "mit dem Steuerberater abstimmen.")
    period = st.text_input("Monat (JJJJ-MM)", date.today().strftime("%Y-%m"), key="inv_period")
    if st.button("📤 Testexport erzeugen"):
        try:
            data, n = crm_stage6.export_test(conn, period, user)
        except ValueError:
            st.error("Monat im Format JJJJ-MM angeben.")
            return
        log_fn("invoice_test_export", f"{period}: {n} Rechnungen")
        st.download_button("CSV herunterladen", data.encode("utf-8-sig"), f"testexport_{period}.csv", "text/csv")
        st.caption(f"{n} freigegebene Rechnungen aus Stufe 6.")


def page_invoicing_v2(conn_fn, df_fn, log_fn, user, role) -> None:
    st.title("🧾 Rechnungsentwurf")
    if role not in crm_stage6.FINANCE_ROLES:
        st.error("Keine Berechtigung für Rechnungen.")
        return
    with conn_fn() as conn:
        crm_stage6.ensure_tables(conn)
        tabs = st.tabs(["🆕 Aus Auftrag", "🔎 Prüfen & Freigeben", "📤 Testexport", "📋 Übersicht"])
        with tabs[0]:
            _new_tab(conn, log_fn)
        with tabs[1]:
            _review_tab(conn, log_fn, user, role)
        with tabs[2]:
            _export_tab(conn, log_fn, user)
        with tabs[3]:
            st.dataframe(df_fn("""SELECT d.id AS Entwurf, c.company AS Kunde, d.sparte AS Sparte, d.tax_case AS Steuerfall,
                                  d.net_total AS Netto, d.status AS Status, i.invoice_no AS Rechnung, i.status AS Zahlstatus,
                                  i.paid_amount AS Bezahlt, d.approved_by AS Freigabe, d.approved_at AS Freigegeben_am
                                  FROM invoice_drafts d JOIN customers c ON c.id=d.customer_id
                                  LEFT JOIN invoices i ON i.id=d.invoice_id ORDER BY d.id DESC"""),
                         use_container_width=True)
