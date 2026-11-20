"""CRM Stufe 2 – Seite "Leads": Bewerbungen/Anfragen mit Statuskette, Kontaktverlauf und Versandprüfung."""
from __future__ import annotations

import streamlit as st

import crm_stage1
import crm_stage2


def _customer_options(conn) -> dict:
    rows = conn.execute("SELECT id, customer_no, company, sparte, email, distance_km FROM customers ORDER BY company").fetchall()
    return {f"{r[1] or ''} – {r[2]}": r for r in rows}


def _new_lead(conn, log_fn) -> None:
    options = _customer_options(conn)
    if not options:
        st.info("Bitte zuerst Kunden anlegen.")
        return
    label = st.selectbox("Kunde", list(options), key="lead_new_customer")
    cid, _, _, cust_sparte, cust_email, km = options[label]
    st.caption(f"Radius: {crm_stage1.radius_status(km)}" + (f" ({km} km Luftlinie)" if km is not None else ""))
    history = crm_stage2.contact_history(conn, cid)
    if history:
        st.warning(f"{len(history)} frühere Kontakte zu diesem Kunden – vor dem Anschreiben prüfen:")
        st.table([{"Art": h[0], "Datum": h[1], "Details": h[2]} for h in history])
    with st.form("lead_new_form", clear_on_submit=True):
        a, b = st.columns(2)
        sparten = list(crm_stage2.SENDERS)
        sparte = a.selectbox("Sparte *", sparten, index=sparten.index(cust_sparte) if cust_sparte in sparten else 0)
        channel = b.selectbox("Kanal *", crm_stage2.CHANNELS)
        title = a.text_input("Leistung / Ausschreibung *")
        source = b.text_input("Quelle (z. B. Vergabeportal, Link, Anfrage)")
        legal = a.selectbox("Rechtsgrundlage für die Kontaktaufnahme", crm_stage2.LEGAL_BASES)
        recipient = b.text_input("Empfänger (E-Mail/Portal)", cust_email or "")
        notes = st.text_area("Notizen")
        if st.form_submit_button("➕ Lead anlegen", type="primary"):
            try:
                lead_id = crm_stage2.create_lead(conn, cid, sparte, title, channel, legal, recipient, source, notes)
            except ValueError as exc:
                st.error(str(exc))
            else:
                log_fn("lead_created", f"{lead_id}: {title}")
                st.success(f"Lead {lead_id} angelegt (Status neu).")


def _edit_lead(conn, log_fn) -> None:
    rows = conn.execute("""SELECT l.id, l.title, c.company, l.status FROM leads l JOIN customers c ON c.id=l.customer_id
                           ORDER BY l.id DESC""").fetchall()
    if not rows:
        st.info("Noch keine Leads.")
        return
    labels = {f"#{r[0]} {r[2]} – {r[1]} [{r[3]}]": r[0] for r in rows}
    lead_id = labels[st.selectbox("Lead", list(labels), key="lead_edit_sel")]
    lead = dict(zip([d[0] for d in conn.execute("SELECT * FROM leads WHERE id=?", (lead_id,)).description],
                    conn.execute("SELECT * FROM leads WHERE id=?", (lead_id,)).fetchone()))
    st.markdown(f"**Status:** {lead['status']} · **Sparte:** {lead['sparte']} · **Kanal:** {lead['channel']} · "
                f"**Rechtsgrundlage:** {lead['legal_basis']} · **Absender:** {crm_stage2.SENDERS[lead['sparte']]}")
    if lead["status"] == "Entwurf":
        reasons = crm_stage2.check_send(conn, lead_id)
        if reasons:
            st.error("Versand nicht zulässig:\n" + "\n".join(f"- {r}" for r in reasons))
            if any(r.startswith("Grenzfall") for r in reasons) and st.button("Straßenentfernung geprüft – im Radius"):
                crm_stage2.confirm_radius(conn, lead_id)
                log_fn("lead_radius_confirmed", str(lead_id))
                st.rerun()
        else:
            st.success("Versandprüfung bestanden.")
    allowed = sorted(crm_stage2.TRANSITIONS[lead["status"]])
    if allowed:
        with st.form("lead_status_form"):
            to_status = st.selectbox("Neuer Status", allowed)
            note = st.text_input("Notiz / Nachweis")
            st.caption("„gesendet“ protokolliert einen außerhalb erfolgten Versand – hier wird nichts verschickt.")
            if st.form_submit_button("Status ändern"):
                try:
                    crm_stage2.transition(conn, lead_id, to_status, note)
                except ValueError as exc:
                    st.error(str(exc))
                else:
                    log_fn("lead_status", f"{lead_id}: {lead['status']} → {to_status}")
                    st.rerun()
    st.subheader("Kontaktverlauf des Kunden")
    st.table([{"Art": h[0], "Datum": h[1], "Details": h[2]} for h in crm_stage2.contact_history(conn, lead["customer_id"])])


def page_leads_v2(conn_fn, df_fn, log_fn) -> None:
    st.title("🎯 Leads & Bewerbungen")
    with conn_fn() as conn:
        crm_stage2.ensure_tables(conn)
        f1, f2 = st.columns(2)
        status = f1.selectbox("Status", ["Alle"] + list(crm_stage2.STATUSES), key="lead_filter_status")
        sparte = f2.selectbox("Sparte", ["Alle"] + list(crm_stage2.SENDERS), key="lead_filter_sparte")
        where, params = ["1=1"], []
        if status != "Alle":
            where.append("l.status=?")
            params.append(status)
        if sparte != "Alle":
            where.append("l.sparte=?")
            params.append(sparte)
        tabs = st.tabs(["📋 Übersicht", "➕ Neuer Lead", "✏️ Bearbeiten"])
        with tabs[0]:
            st.dataframe(df_fn(f"""SELECT l.id, c.company AS Kunde, l.sparte AS Sparte, l.title AS Leistung, l.channel AS Kanal,
                                   l.legal_basis AS Rechtsgrundlage, l.status AS Status, l.updated_at AS Aktualisiert
                                   FROM leads l JOIN customers c ON c.id=l.customer_id
                                   WHERE {' AND '.join(where)} ORDER BY l.updated_at DESC""", tuple(params)),
                         use_container_width=True)
        with tabs[1]:
            _new_lead(conn, log_fn)
        with tabs[2]:
            _edit_lead(conn, log_fn)
