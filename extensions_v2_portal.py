"""Seite "Mein Bereich": eigene Einsätze und Leistungsnachweise; für Admins zusätzlich die Konto-Zuordnung."""
from __future__ import annotations

from datetime import date, timedelta

import streamlit as st

import crm_portal


def _assign_tab(conn, log_fn) -> None:
    users = [r[0] for r in conn.execute("SELECT username FROM users WHERE active=1 ORDER BY username")]
    employees = {f"{r[1]} ({r[2] or 'ohne Nr.'})": r[0]
                 for r in conn.execute("SELECT id, name, employee_no FROM employees WHERE active=1 ORDER BY name")}
    st.dataframe([{"Konto": u, "Mitarbeiter": (crm_portal.my_employee(conn, u) or (None, "–"))[1]} for u in users],
                 use_container_width=True)
    if not users or not employees:
        st.info("Es fehlen aktive Benutzerkonten oder Mitarbeiter.")
        return
    a, b = st.columns(2)
    user = a.selectbox("Konto", users, key="portal_user")
    choice = b.selectbox("Mitarbeiter", ["– keine Zuordnung –"] + list(employees), key="portal_emp")
    if st.button("Zuordnung speichern"):
        try:
            crm_portal.link_user(conn, user, employees.get(choice))
        except ValueError as exc:
            st.error(str(exc))
        else:
            log_fn("portal_link", f"{user} → {choice}")
            st.success(f"Gespeichert: {user} → {choice}")


def page_my_area(conn_fn, log_fn, username, role) -> None:
    st.title("👷 Mein Bereich")
    with conn_fn() as conn:
        crm_portal.ensure_columns(conn)
        tabs = st.tabs(["📅 Meine Einsätze", "📝 Meine Leistungsnachweise"]
                       + (["🔗 Konten zuordnen"] if role == "Inhaber/Admin" else []))
        emp = crm_portal.my_employee(conn, username)
        with tabs[0]:
            if not emp:
                st.info("Ihr Konto ist noch keinem Mitarbeiter zugeordnet. Bitte an die Einsatzleitung oder den Inhaber wenden.")
            else:
                st.caption(f"Angemeldet als {emp[1]} – es werden nur Ihre eigenen Einsätze angezeigt.")
                a, b = st.columns(2)
                start = a.date_input("Von", date.today() - timedelta(days=14), key="portal_from")
                end = b.date_input("Bis", date.today() + timedelta(days=60), key="portal_to")
                shifts = crm_portal.my_shifts(conn, username, start.isoformat(), end.isoformat())
                if shifts:
                    st.dataframe([{k.capitalize(): v for k, v in s.items() if k != "id"} for s in shifts],
                                 use_container_width=True)
                else:
                    st.info("Keine Einsätze im gewählten Zeitraum.")
        with tabs[1]:
            reports = crm_portal.my_reports(conn, username) if emp else []
            if reports:
                st.dataframe(reports, use_container_width=True)
            else:
                st.info("Keine eigenen Leistungsnachweise vorhanden.")
        if role == "Inhaber/Admin":
            with tabs[2]:
                _assign_tab(conn, log_fn)
