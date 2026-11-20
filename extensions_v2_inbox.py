"""CRM Stufe 3 – Seite "Posteingang": Eingang → Kunde → Lead → Angebot → Auftrag, ohne Live-Versand."""
from __future__ import annotations

import imaplib
import socket

import streamlit as st

import crm_stage2
import crm_stage3


def _import_tab(conn, log_fn, archive_dir) -> None:
    mailbox = st.selectbox("Empfangspostfach", list(crm_stage3.MAILBOXES), key="inbox_mailbox")
    files = st.file_uploader("E-Mails als .eml hochladen", type=["eml"], accept_multiple_files=True)
    if files and st.button("📥 Hochgeladene E-Mails übernehmen"):
        new = sum(crm_stage3.import_message(conn, f.getvalue(), mailbox, archive_dir)[1] for f in files)
        log_fn("inbox_import", f"{new} neu von {len(files)} ({mailbox})")
        st.success(f"{new} neu übernommen, {len(files) - new} waren bereits vorhanden.")
    with st.form("inbox_imap_form"):
        st.markdown("**IMAP-Abruf (nur lesend – Mails bleiben ungelesen, nichts wird gelöscht)**")
        a, b = st.columns(2)
        host = a.text_input("IMAP-Server", "mail.byblos-sicherheit.de")
        port = b.number_input("Port", value=993, step=1)
        user = a.text_input("Benutzer", mailbox)
        password = b.text_input("Passwort (wird nicht gespeichert)", type="password")
        if st.form_submit_button("🔄 Abrufen") and password:
            try:
                new, known = crm_stage3.fetch_imap(conn, host, user, password, mailbox, archive_dir, int(port))
            except (imaplib.IMAP4.error, OSError, socket.timeout) as exc:
                st.error(f"Abruf fehlgeschlagen: {exc}")
            else:
                log_fn("inbox_imap", f"{mailbox}: {new} neu, {known} bekannt")
                st.success(f"{new} neue E-Mails, {known} bereits vorhanden.")


def _work_tab(conn, log_fn) -> None:
    rows = conn.execute("SELECT id, received_at, from_addr, subject, status FROM inbox_messages ORDER BY id DESC").fetchall()
    if not rows:
        st.info("Noch keine Eingänge.")
        return
    labels = {f"#{r[0]} {r[1] or ''} {r[2]} – {r[3]} [{r[4]}]": r[0] for r in rows}
    msg_id = labels[st.selectbox("Eingang", list(labels), key="inbox_sel")]
    msg = dict(zip([d[0] for d in conn.execute("SELECT * FROM inbox_messages WHERE id=?", (msg_id,)).description],
                   conn.execute("SELECT * FROM inbox_messages WHERE id=?", (msg_id,)).fetchone()))
    st.markdown(f"**Sparte:** {msg['sparte']} · **Postfach:** {msg['mailbox']} · **Von:** {msg['from_addr']}")
    st.text_area("Inhalt (Auszug)", msg["body_excerpt"] or "", height=150, disabled=True)
    try:
        if not msg["customer_id"]:
            customers = {f"{r[1] or ''} – {r[2]}": r[0] for r in conn.execute("SELECT id, customer_no, company FROM customers ORDER BY company")}
            st.warning("Absender keinem Kunden zugeordnet. Kunde wählen oder zuerst in der Kundenverwaltung anlegen.")
            if customers:
                pick = st.selectbox("Kunde", list(customers), key="inbox_assign")
                if st.button("Zuordnen"):
                    crm_stage3.assign_customer(conn, msg_id, customers[pick])
                    log_fn("inbox_assign", f"{msg_id} → {customers[pick]}")
                    st.rerun()
        elif not msg["lead_id"]:
            title = st.text_input("Leistung", msg["subject"] or "", key="inbox_lead_title")
            if st.button("🎯 Lead aus Anfrage erstellen"):
                lead_id = crm_stage3.lead_from_message(conn, msg_id, title)
                log_fn("inbox_lead", f"{msg_id} → Lead {lead_id}")
                st.rerun()
        elif not msg["offer_id"]:
            a, b = st.columns(2)
            net = a.number_input("Angebot netto (€)", min_value=0.0, step=50.0, key="inbox_offer_net")
            desc = b.text_input("Beschreibung", key="inbox_offer_desc")
            if st.button("📋 Angebotsentwurf anlegen"):
                offer_id = crm_stage3.offer_from_lead(conn, msg["lead_id"], net, desc)
                log_fn("inbox_offer", f"Lead {msg['lead_id']} → Angebot {offer_id}")
                st.rerun()
        elif msg["status"] != "Auftrag":
            lead_status = conn.execute("SELECT status FROM leads WHERE id=?", (msg["lead_id"],)).fetchone()[0]
            st.info(f"Lead-Status: {lead_status}. Das Angebot unter „Leads“ bis „gesendet“ führen (mit Versandprüfung), "
                    "danach hier die Annahme erfassen.")
            if st.button("✅ Angebot angenommen → Auftrag"):
                crm_stage3.accept_offer(conn, msg["offer_id"])
                log_fn("inbox_order", f"Angebot {msg['offer_id']} angenommen")
                st.rerun()
    except ValueError as exc:
        st.error(str(exc))
    st.subheader("Nachvollziehbarer Weg")
    st.table([{"Schritt": s, "Detail": d} for s, d in crm_stage3.trace(conn, msg_id)])


def page_inbox_v2(conn_fn, df_fn, log_fn, role, archive_dir) -> None:
    st.title("📨 Posteingang")
    if role not in crm_stage3.INBOX_ROLES:
        st.error("Keine Berechtigung für den Posteingang.")
        return
    with conn_fn() as conn:
        crm_stage2.ensure_tables(conn)
        crm_stage3.ensure_tables(conn)
        tabs = st.tabs(["📋 Eingänge", "📥 Abrufen / Import", "✏️ Bearbeiten"])
        with tabs[0]:
            f1, f2 = st.columns(2)
            sparte = f1.selectbox("Sparte", ["Alle"] + list(crm_stage2.SENDERS), key="inbox_f_sparte")
            status = f2.selectbox("Status", ["Alle"] + list(crm_stage3.INBOX_STATUSES), key="inbox_f_status")
            where, params = ["1=1"], []
            if sparte != "Alle":
                where.append("m.sparte=?")
                params.append(sparte)
            if status != "Alle":
                where.append("m.status=?")
                params.append(status)
            st.dataframe(df_fn(f"""SELECT m.id, m.received_at AS Eingang, m.mailbox AS Postfach, m.sparte AS Sparte,
                                   m.from_addr AS Von, m.subject AS Betreff, c.company AS Kunde, m.status AS Status
                                   FROM inbox_messages m LEFT JOIN customers c ON c.id=m.customer_id
                                   WHERE {' AND '.join(where)} ORDER BY m.id DESC""", tuple(params)),
                         use_container_width=True)
        with tabs[1]:
            _import_tab(conn, log_fn, archive_dir)
        with tabs[2]:
            _work_tab(conn, log_fn)
