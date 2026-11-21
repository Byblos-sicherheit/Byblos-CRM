"""CRM Stufe 7 – Seite "KPI & Automationen": Kennzahlen mit Quelle, Protokoll und nachgewiesenem Automationsstatus."""
from __future__ import annotations

import json
from datetime import date

import streamlit as st

import crm_stage7


def page_reporting_v2(conn_fn, df_fn, log_fn, user) -> None:
    st.title("📈 KPI & Automationen")
    st.caption("Alle Werte stammen ausschließlich aus Daten im CRM. Jede Kennzahl nennt Quelle und Datensätze.")
    with conn_fn() as conn:
        crm_stage7.ensure_tables(conn)
        tabs = st.tabs(["📊 Kennzahlen", "⚙️ Automationen", "🗂️ Protokoll"])
        with tabs[0]:
            today = date.today()
            a, b = st.columns(2)
            start = a.date_input("Von", today.replace(day=1), key="kpi_start")
            end = b.date_input("Bis", today, key="kpi_end")
            try:
                values = crm_stage7.kpis(conn, start.isoformat(), end.isoformat())
            except ValueError as exc:
                st.error(str(exc))
                return
            cols = st.columns(3)
            for i, k in enumerate(values):
                cols[i % 3].metric(k["name"], f"{k['value']} {k['unit']}")
            st.table([{"Kennzahl": k["name"], "Wert": k["value"], "Quelle": k["source"],
                       "Datensätze (IDs)": ", ".join(map(str, k["ids"][:30])) + (" …" if len(k["ids"]) > 30 else ""),
                       "Hinweis": k["note"]} for k in values])
            if st.button("🧾 Stand protokollieren"):
                snap_id, _ = crm_stage7.snapshot(conn, start.isoformat(), end.isoformat(), user)
                log_fn("kpi_snapshot", f"#{snap_id} {start}–{end}")
                st.success(f"Kennzahlen als Protokoll #{snap_id} gespeichert (mit Prüfsumme).")
        with tabs[1]:
            st.info("„aktiv (nachgewiesen)“ erscheint nur, wenn ein Job an mindestens "
                    f"{crm_stage7.MIN_PROVEN_RUNS} Tagen fehlerfrei protokolliert wurde und der letzte Lauf aktuell ist. "
                    "Manuelle Einzelläufe gelten nicht als Automation.")
            st.table([{"Automation": s["label"], "Status": s["status"], "Letzter Lauf": s["last_run"] or "–", "Läufe": s["runs"]}
                      for s in (crm_stage7.job_status(conn, job) for job in crm_stage7.JOBS)])
        with tabs[2]:
            snaps = conn.execute("SELECT id, ts, period_start, period_end, created_by, data, sha256 FROM kpi_snapshots "
                                 "ORDER BY id DESC LIMIT 50").fetchall()
            if not snaps:
                st.info("Noch keine protokollierten Stände.")
            for sid, ts, ps, pe, by, data, sha in snaps:
                with st.expander(f"#{sid} · {ts} · {ps} bis {pe} · {by or '–'}"):
                    st.table([{"Kennzahl": k["name"], "Wert": k["value"]} for k in json.loads(data)])
                    st.caption(f"SHA-256: {sha}")
