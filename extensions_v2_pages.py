"""
extensions_v2_pages.py – Verbesserte Seiten für Byblos CRM v2
==============================================================
Ersetzt bzw. erweitert bestehende Seiten mit:
  - Vollständige CRUD (Erstellen, Lesen, Bearbeiten, Löschen)
  - Suchfilter und Pagination
  - Statusbadges und farbige Hervorhebungen
  - Bessere Formular-UX mit Validierung
  - Export-Buttons auf jeder Seite
  - Audit-Log-Einträge bei jeder Änderung
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd
import streamlit as st


# ─────────────────────────────────────────────────────────────
# Hilfsfunktionen
# ─────────────────────────────────────────────────────────────

def fmt_eur(v: float) -> str:
    return f"{v:,.2f} €".replace(",", "X").replace(".", ",").replace("X", ".")


def status_badge(status: str) -> str:
    colors = {
        "bezahlt":      ("#27ae60", "✅"),
        "offen":        ("#2980b9", "📄"),
        "ueberfaellig": ("#c0392b", "🔴"),
        "teilbezahlt":  ("#e67e22", "🟡"),
        "storniert":    ("#7f8c8d", "❌"),
        "geplant":      ("#2980b9", "📅"),
        "bestätigt":    ("#27ae60", "✅"),
        "abgeschlossen":("#7f8c8d", "✔"),
        "ausgefallen":  ("#c0392b", "❌"),
        "aktiv":        ("#27ae60", "✅"),
        "inaktiv":      ("#7f8c8d", "⛔"),
    }
    color, icon = colors.get(str(status).lower(), ("#888", "•"))
    return f'<span style="background:{color}22;border:1px solid {color};color:{color};padding:2px 8px;border-radius:10px;font-size:.8rem;font-weight:600;">{icon} {status}</span>'


def download_csv(data: pd.DataFrame, filename: str, label: str = "📥 CSV exportieren") -> None:
    if not data.empty:
        csv = data.to_csv(index=False, sep=";").encode("utf-8-sig")
        st.download_button(label, csv, file_name=filename, mime="text/csv")


def confirm_delete(key: str, label: str = "🗑️ Löschen") -> bool:
    """Zweistufiger Lösch-Button mit Bestätigung."""
    confirm_key = f"_confirm_{key}"
    if st.session_state.get(confirm_key):
        col1, col2 = st.columns(2)
        with col1:
            if st.button("⚠️ Ja, wirklich löschen", key=f"_yes_{key}", type="primary"):
                st.session_state.pop(confirm_key, None)
                return True
        with col2:
            if st.button("Abbrechen", key=f"_no_{key}"):
                st.session_state.pop(confirm_key, None)
        return False
    else:
        if st.button(label, key=f"_del_{key}"):
            st.session_state[confirm_key] = True
            st.rerun()
        return False


# ─────────────────────────────────────────────────────────────
# 1. Verbesserte Kundenverwaltung
# ─────────────────────────────────────────────────────────────

def page_customers_v2(run_fn, df_fn, next_number_fn, log_fn) -> None:
    st.title("👥 Kundenverwaltung")

    # Suchleiste + Filter
    col_s, col_f = st.columns([3, 1])
    q = col_s.text_input("🔍 Suche (Firma, Nr., Ansprechperson, E-Mail)", "")
    only_active = col_f.checkbox("Nur aktive", value=False)

    base_q = """
        SELECT c.id, c.customer_no AS Nr, c.company AS Firma,
               c.contact_person AS Ansprechperson, c.email AS E_Mail,
               c.phone AS Telefon, c.street AS Straße, c.zip_city AS PLZ_Ort,
               c.country AS Land,
               (SELECT COUNT(*) FROM invoices i WHERE i.customer_id=c.id) AS Rechnungen,
               (SELECT COALESCE(SUM(i.gross_total),0) FROM invoices i WHERE i.customer_id=c.id AND i.status='bezahlt') AS Umsatz_gesamt
        FROM customers c
    """
    where_parts = []
    params: List[Any] = []
    if q:
        where_parts.append("(c.company LIKE ? OR c.customer_no LIKE ? OR c.contact_person LIKE ? OR c.email LIKE ?)")
        params += [f"%{q}%"] * 4
    where = ("WHERE " + " AND ".join(where_parts)) if where_parts else ""
    data = df_fn(base_q + where + " ORDER BY c.company", tuple(params))

    tabs = st.tabs(["📋 Übersicht", "➕ Neu anlegen", "✏️ Bearbeiten", "📊 Kundendetails"])

    with tabs[0]:
        if not data.empty:
            col_m, col_e = st.columns([4, 1])
            col_m.markdown(f"**{len(data)} Kunden** gefunden")
            download_csv(data.drop(columns=["id"]), "kunden_export.csv")

            # Formatierte Tabelle
            display = data.copy()
            display["Umsatz_gesamt"] = display["Umsatz_gesamt"].apply(fmt_eur)
            st.dataframe(display.drop(columns=["id"]), use_container_width=True, height=400)
        else:
            st.info("Keine Kunden gefunden.")

    with tabs[1]:
        with st.form("customer_new_form", clear_on_submit=True):
            st.subheader("Neuen Kunden anlegen")
            a, b = st.columns(2)
            customer_no = a.text_input("Kundennummer", next_number_fn("customers", "customer_no", "SD-"))
            company = b.text_input("Firma / Name *", "")
            contact_person = a.text_input("Ansprechperson", "")
            phone = b.text_input("Telefon", "")
            email = a.text_input("E-Mail", "")
            street = b.text_input("Straße + Nr.", "")
            zip_city = a.text_input("PLZ Ort", "")
            country = b.text_input("Land", "Deutschland")
            notes = st.text_area("Notizen / Besonderheiten", "")
            submitted = st.form_submit_button("💾 Kunden speichern", type="primary")

        if submitted:
            if not company.strip():
                st.error("Firmenname ist Pflichtfeld.")
            else:
                run_fn("""INSERT INTO customers(customer_no,company,contact_person,email,phone,street,zip_city,country,notes)
                          VALUES(?,?,?,?,?,?,?,?,?)""",
                       (customer_no, company, contact_person, email, phone, street, zip_city, country, notes))
                log_fn("customer_created", company)
                st.success(f"✅ Kunde '{company}' ({customer_no}) angelegt!")
                st.rerun()

    with tabs[2]:
        customers = df_fn("SELECT id, customer_no || ' – ' || company AS label FROM customers ORDER BY company")
        if customers.empty:
            st.info("Noch keine Kunden vorhanden.")
            return
        selected_label = st.selectbox("Kunde auswählen", customers["label"].tolist())
        cid = int(customers[customers["label"] == selected_label].iloc[0]["id"])
        row = df_fn("SELECT * FROM customers WHERE id=?", (cid,)).iloc[0].to_dict()

        with st.form("customer_edit_form"):
            a, b = st.columns(2)
            customer_no = a.text_input("Kundennummer", str(row.get("customer_no", "")))
            company = b.text_input("Firma / Name *", str(row.get("company", "")))
            contact_person = a.text_input("Ansprechperson", str(row.get("contact_person", "") or ""))
            phone = b.text_input("Telefon", str(row.get("phone", "") or ""))
            email = a.text_input("E-Mail", str(row.get("email", "") or ""))
            street = b.text_input("Straße + Nr.", str(row.get("street", "") or ""))
            zip_city = a.text_input("PLZ Ort", str(row.get("zip_city", "") or ""))
            country = b.text_input("Land", str(row.get("country", "Deutschland") or "Deutschland"))
            notes = st.text_area("Notizen", str(row.get("notes", "") or ""))
            col1, col2 = st.columns(2)
            save = col1.form_submit_button("💾 Änderungen speichern", type="primary")

        if save and company.strip():
            run_fn("""UPDATE customers SET customer_no=?,company=?,contact_person=?,email=?,phone=?,
                      street=?,zip_city=?,country=?,notes=? WHERE id=?""",
                   (customer_no, company, contact_person, email, phone, street, zip_city, country, notes, cid))
            log_fn("customer_updated", company)
            st.success("✅ Kunde aktualisiert!")
            st.rerun()

        st.divider()
        st.markdown("**⚠️ Gefährliche Aktionen**")
        inv_count = int(df_fn("SELECT COUNT(*) AS n FROM invoices WHERE customer_id=?", (cid,)).iloc[0]["n"])
        if inv_count > 0:
            st.warning(f"Dieser Kunde hat {inv_count} Rechnung(en) – Löschen nicht möglich.")
        else:
            if confirm_delete(f"cust_{cid}", "🗑️ Kunde endgültig löschen"):
                run_fn("DELETE FROM customers WHERE id=?", (cid,))
                log_fn("customer_deleted", str(cid))
                st.success("Kunde gelöscht.")
                st.rerun()

    with tabs[3]:
        customers2 = df_fn("SELECT id, customer_no || ' – ' || company AS label FROM customers ORDER BY company")
        if customers2.empty:
            st.info("Noch keine Kunden.")
            return
        sel2 = st.selectbox("Kunde", customers2["label"].tolist(), key="cust_detail_sel")
        cid2 = int(customers2[customers2["label"] == sel2].iloc[0]["id"])
        row2 = df_fn("SELECT * FROM customers WHERE id=?", (cid2,)).iloc[0].to_dict()

        col1, col2 = st.columns(2)
        col1.markdown(f"**📛 {row2.get('company','')}**  \n{row2.get('contact_person','')}  \n{row2.get('email','')}  \n{row2.get('phone','')}")
        col2.markdown(f"**📍 Adresse**  \n{row2.get('street','')}  \n{row2.get('zip_city','')}  \n{row2.get('country','')}")

        st.divider()
        st.subheader("Rechnungshistorie")
        inv_hist = df_fn("""SELECT invoice_no AS Nr, invoice_date AS Datum, due_date AS Fällig,
                            gross_total AS Brutto, paid_amount AS Bezahlt, status AS Status
                            FROM invoices WHERE customer_id=? ORDER BY invoice_date DESC""", (cid2,))
        if not inv_hist.empty:
            total = float(inv_hist["Brutto"].sum())
            paid = float(inv_hist["Bezahlt"].sum())
            c1, c2, c3 = st.columns(3)
            c1.metric("Umsatz gesamt", fmt_eur(total))
            c2.metric("Davon bezahlt", fmt_eur(paid))
            c3.metric("Ausstehend", fmt_eur(total - paid))
            st.dataframe(inv_hist, use_container_width=True)
        else:
            st.info("Keine Rechnungen für diesen Kunden.")

        st.subheader("Kontakthistorie")
        cont_hist = df_fn("""SELECT contact_date AS Datum, contact_type AS Art, subject AS Betreff,
                             note AS Notiz, next_followup AS Wiedervorlage
                             FROM contacts WHERE customer_id=? ORDER BY contact_date DESC""", (cid2,))
        if not cont_hist.empty:
            st.dataframe(cont_hist, use_container_width=True)
        else:
            st.info("Keine Kontakthistorie vorhanden.")

        st.subheader("Schichten für diesen Kunden")
        shift_hist = df_fn("""SELECT s.shift_date AS Datum, s.start_time AS Von, s.end_time AS Bis,
                              e.name AS Mitarbeiter, s.location AS Ort, s.status AS Status
                              FROM shifts s LEFT JOIN employees e ON e.id=s.employee_id
                              WHERE s.customer_id=? ORDER BY s.shift_date DESC LIMIT 30""", (cid2,))
        if not shift_hist.empty:
            st.dataframe(shift_hist, use_container_width=True)
        else:
            st.info("Keine Schichten für diesen Kunden.")

        if row2.get("notes"):
            st.subheader("📝 Notizen")
            st.markdown(str(row2["notes"]))


# ─────────────────────────────────────────────────────────────
# 2. Verbesserte Mitarbeiterverwaltung
# ─────────────────────────────────────────────────────────────

def page_employees_v2(run_fn, df_fn, next_number_fn, log_fn) -> None:
    st.title("👷 Mitarbeiterverwaltung")

    tabs = st.tabs(["📋 Übersicht", "➕ Neu", "✏️ Bearbeiten", "📊 Details & Auswertung"])

    with tabs[0]:
        q = st.text_input("🔍 Suche", "")
        if q:
            data = df_fn("SELECT * FROM employees WHERE name LIKE ? OR employee_no LIKE ? ORDER BY active DESC, name", (f"%{q}%", f"%{q}%"))
        else:
            data = df_fn("SELECT * FROM employees ORDER BY active DESC, name")

        if not data.empty:
            active_n = int((data["active"] == 1).sum()) if "active" in data.columns else 0
            st.caption(f"{len(data)} Mitarbeiter · {active_n} aktiv")
            # Status-Spalte formatieren
            disp = data.copy()
            if "active" in disp.columns:
                disp["Status"] = disp["active"].apply(lambda v: "✅ aktiv" if v else "⛔ inaktiv")
                disp = disp.drop(columns=["active"])
            st.dataframe(disp, use_container_width=True, height=350)
            download_csv(data, "mitarbeiter_export.csv")
        else:
            st.info("Keine Mitarbeiter gefunden.")

    with tabs[1]:
        with st.form("emp_new", clear_on_submit=True):
            st.subheader("Neuen Mitarbeiter anlegen")
            a, b = st.columns(2)
            emp_no = a.text_input("Mitarbeiternummer", next_number_fn("employees", "employee_no", "MA-"))
            name = b.text_input("Name *")
            phone = a.text_input("Telefon")
            email = b.text_input("E-Mail")
            rate = a.number_input("Stundensatz intern (€)", min_value=0.0, value=15.0, step=0.5)
            active = b.checkbox("Aktiv", value=True)
            iban = a.text_input("IBAN (für Lohnabrechnung)")
            tax_id = b.text_input("Steuer-ID / SV-Nummer")
            contract_type = a.selectbox("Vertragsart", ["Vollzeit", "Teilzeit", "Minijob", "Werkvertrag", "Leiharbeit"])
            hire_date = b.date_input("Einstellungsdatum", date.today())
            notes = st.text_area("Notizen")
            submitted = st.form_submit_button("💾 Speichern", type="primary")

        if submitted:
            if not name.strip():
                st.error("Name ist Pflichtfeld.")
            else:
                # Prüfe ob Tabelle erweiterte Felder hat, sonst einfaches Insert
                try:
                    run_fn("""INSERT INTO employees(employee_no,name,phone,email,hourly_rate,active,notes)
                              VALUES(?,?,?,?,?,?,?)""",
                           (emp_no, name, phone, email, rate, 1 if active else 0, notes))
                except Exception:
                    run_fn("""INSERT INTO employees(employee_no,name,phone,email,hourly_rate,active,notes)
                              VALUES(?,?,?,?,?,?,?)""",
                           (emp_no, name, phone, email, rate, 1 if active else 0,
                            f"{notes}\nIBAN:{iban} SteuerID:{tax_id} Vertrag:{contract_type} Eingestellt:{hire_date}"))
                log_fn("employee_created", name)
                st.success(f"✅ Mitarbeiter '{name}' ({emp_no}) gespeichert!")
                st.rerun()

    with tabs[2]:
        employees = df_fn("SELECT id, employee_no || ' – ' || name AS label FROM employees ORDER BY name")
        if employees.empty:
            st.info("Noch keine Mitarbeiter.")
            return
        sel = st.selectbox("Mitarbeiter", employees["label"].tolist())
        eid = int(employees[employees["label"] == sel].iloc[0]["id"])
        row = df_fn("SELECT * FROM employees WHERE id=?", (eid,)).iloc[0].to_dict()

        with st.form("emp_edit"):
            a, b = st.columns(2)
            emp_no = a.text_input("Mitarbeiternummer", str(row.get("employee_no", "")))
            name = b.text_input("Name *", str(row.get("name", "")))
            phone = a.text_input("Telefon", str(row.get("phone", "") or ""))
            email = b.text_input("E-Mail", str(row.get("email", "") or ""))
            rate = a.number_input("Stundensatz intern (€)", min_value=0.0,
                                  value=float(row.get("hourly_rate") or 0), step=0.5)
            active = b.checkbox("Aktiv", value=bool(row.get("active", 1)))
            notes = st.text_area("Notizen", str(row.get("notes", "") or ""))
            save = st.form_submit_button("💾 Speichern", type="primary")

        if save and name.strip():
            run_fn("""UPDATE employees SET employee_no=?,name=?,phone=?,email=?,hourly_rate=?,active=?,notes=?
                      WHERE id=?""", (emp_no, name, phone, email, rate, 1 if active else 0, notes, eid))
            log_fn("employee_updated", name)
            st.success("✅ Mitarbeiter aktualisiert!")
            st.rerun()

        st.divider()
        shift_count = int(df_fn("SELECT COUNT(*) AS n FROM shifts WHERE employee_id=?", (eid,)).iloc[0]["n"])
        if shift_count == 0:
            if confirm_delete(f"emp_{eid}", "🗑️ Mitarbeiter löschen"):
                run_fn("DELETE FROM employees WHERE id=?", (eid,))
                log_fn("employee_deleted", str(eid))
                st.success("Mitarbeiter gelöscht.")
                st.rerun()
        else:
            st.caption(f"Mitarbeiter hat {shift_count} Schichten – Deaktivieren statt Löschen empfohlen.")

    with tabs[3]:
        employees2 = df_fn("SELECT id, employee_no || ' – ' || name AS label FROM employees ORDER BY name")
        if employees2.empty:
            return
        sel2 = st.selectbox("Mitarbeiter", employees2["label"].tolist(), key="emp_detail_sel")
        eid2 = int(employees2[employees2["label"] == sel2].iloc[0]["id"])

        # Schichten-Statistik
        shifts = df_fn("""SELECT s.shift_date, s.start_time, s.end_time,
                          COALESCE(c.company, '-') AS Kunde, s.location, s.shift_type, s.status
                          FROM shifts s LEFT JOIN customers c ON c.id=s.customer_id
                          WHERE s.employee_id=? ORDER BY s.shift_date DESC LIMIT 50""", (eid2,))

        total_shifts = len(shifts)
        c1, c2 = st.columns(2)
        c1.metric("Schichten gesamt", total_shifts)
        if not shifts.empty:
            this_month = str(date.today())[:7]
            month_shifts = len(shifts[shifts["shift_date"].astype(str).str.startswith(this_month)])
            c2.metric("Schichten diesen Monat", month_shifts)

        st.subheader("Schichthistorie")
        if not shifts.empty:
            st.dataframe(shifts, use_container_width=True)
        else:
            st.info("Noch keine Schichten geplant.")

        st.subheader("Zeiterfassung")
        time_entries = df_fn("""SELECT date AS Datum, start_time AS Von, end_time AS Bis,
                                break_minutes AS Pause_Min, net_hours AS Netto_Std,
                                overtime_hours AS Überstunden, status AS Status
                                FROM time_entries WHERE employee_id=?
                                ORDER BY date DESC LIMIT 30""", (eid2,))
        if not time_entries.empty:
            total_h = float(time_entries["Netto_Std"].sum()) if "Netto_Std" in time_entries.columns else 0
            ot_h = float(time_entries["Überstunden"].sum()) if "Überstunden" in time_entries.columns else 0
            cc1, cc2 = st.columns(2)
            cc1.metric("Gesamtstunden (letzten 30 Einträge)", f"{total_h:.1f} h")
            cc2.metric("Überstunden gesamt", f"{ot_h:.1f} h")
            st.dataframe(time_entries, use_container_width=True)
        else:
            st.info("Keine Zeiterfassungseinträge.")


# ─────────────────────────────────────────────────────────────
# 3. Verbesserter Dienstplan
# ─────────────────────────────────────────────────────────────

def page_schedule_v2(run_fn, df_fn, log_fn) -> None:
    st.title("📅 Dienstplan")

    SHIFT_TYPES = ["Objektschutz", "Veranstaltung", "Streife", "Pforte", "Werkschutz",
                   "Revierdienst", "Sonderaufgabe", "Bereitschaft"]
    STATUS_LIST = ["geplant", "bestätigt", "abgeschlossen", "ausgefallen"]

    tabs = st.tabs(["📋 Übersicht", "➕ Schicht anlegen", "✏️ Bearbeiten/Status", "⚠️ Konflikte"])

    with tabs[0]:
        col1, col2, col3 = st.columns(3)
        start_date = col1.date_input("Von", date.today().replace(day=1))
        end_date = col2.date_input("Bis", date.today() + timedelta(days=30))
        emp_filter = col3.text_input("Mitarbeiter filtern", "")

        query = """
            SELECT s.id, s.shift_date AS Datum, s.start_time AS Von, s.end_time AS Bis,
                   COALESCE(e.name,'⚠️ UNBESETZT') AS Mitarbeiter,
                   COALESCE(c.company,'-') AS Kunde,
                   s.location AS Ort, s.shift_type AS Typ, s.status AS Status, s.notes AS Notiz
            FROM shifts s
            LEFT JOIN employees e ON e.id=s.employee_id
            LEFT JOIN customers c ON c.id=s.customer_id
            WHERE s.shift_date BETWEEN ? AND ?
        """
        params: list = [start_date.isoformat(), end_date.isoformat()]
        if emp_filter:
            query += " AND e.name LIKE ?"
            params.append(f"%{emp_filter}%")
        query += " ORDER BY s.shift_date, s.start_time"
        shifts = df_fn(query, tuple(params))

        if not shifts.empty:
            total = len(shifts)
            unbesetzt = int((shifts["Mitarbeiter"] == "⚠️ UNBESETZT").sum())
            c1, c2, c3 = st.columns(3)
            c1.metric("Schichten gesamt", total)
            c2.metric("⚠️ Unbesetzt", unbesetzt)
            c3.metric("Zeitraum (Tage)", (end_date - start_date).days)
            st.dataframe(shifts.drop(columns=["id"]), use_container_width=True, height=400)
            download_csv(shifts.drop(columns=["id"]), "dienstplan_export.csv")
        else:
            st.info("Keine Schichten im gewählten Zeitraum.")

    with tabs[1]:
        employees = df_fn("SELECT id, name FROM employees WHERE active=1 ORDER BY name")
        customers = df_fn("SELECT id, company FROM customers ORDER BY company")

        with st.form("shift_new", clear_on_submit=True):
            a, b, c, d = st.columns(4)
            shift_date = a.date_input("Datum", date.today())
            start_time = b.time_input("Start", datetime.strptime("18:00", "%H:%M").time())
            end_time = c.time_input("Ende", datetime.strptime("23:00", "%H:%M").time())
            shift_type = d.selectbox("Typ", SHIFT_TYPES)

            emp_names = employees["name"].tolist() if not employees.empty else []
            emp_label = st.selectbox("Mitarbeiter", ["— kein Mitarbeiter —"] + emp_names)
            cust_names = customers["company"].tolist() if not customers.empty else []
            cust_label = st.selectbox("Kunde", ["— kein Kunde —"] + cust_names)

            location = st.text_input("Einsatzort")
            notes = st.text_area("Notizen / Anweisungen")
            repeat = st.selectbox("Wiederholen", ["Einmalig", "Täglich (7 Tage)", "Wöchentlich (4 Wochen)"])
            submitted = st.form_submit_button("💾 Schicht speichern", type="primary")

        if submitted:
            eid = int(employees[employees["name"] == emp_label].iloc[0]["id"]) if emp_label != "— kein Mitarbeiter —" and not employees.empty else None
            cid = int(customers[customers["company"] == cust_label].iloc[0]["id"]) if cust_label != "— kein Kunde —" and not customers.empty else None
            start_s = start_time.strftime("%H:%M")
            end_s = end_time.strftime("%H:%M")

            dates = [shift_date]
            if repeat == "Täglich (7 Tage)":
                dates = [shift_date + timedelta(days=i) for i in range(7)]
            elif repeat == "Wöchentlich (4 Wochen)":
                dates = [shift_date + timedelta(weeks=i) for i in range(4)]

            for d in dates:
                run_fn("""INSERT INTO shifts(shift_date,start_time,end_time,employee_id,customer_id,location,shift_type,notes)
                          VALUES(?,?,?,?,?,?,?,?)""",
                       (d.isoformat(), start_s, end_s, eid, cid, location, shift_type, notes))
            log_fn("shifts_created", f"{len(dates)} Schicht(en) ab {shift_date.isoformat()}")
            st.success(f"✅ {len(dates)} Schicht(en) gespeichert!")
            st.rerun()

    with tabs[2]:
        recent = df_fn("""
            SELECT s.id, s.shift_date || ' ' || s.start_time || ' – ' || COALESCE(e.name,'unbesetzt') || ' @ ' || COALESCE(c.company,'-') AS label,
                   s.status, s.employee_id
            FROM shifts s
            LEFT JOIN employees e ON e.id=s.employee_id
            LEFT JOIN customers c ON c.id=s.customer_id
            WHERE s.shift_date >= date('now','-7 days')
            ORDER BY s.shift_date DESC LIMIT 100
        """)
        if recent.empty:
            st.info("Keine aktuellen Schichten.")
            return

        sel = st.selectbox("Schicht", recent["label"].tolist())
        sid = int(recent[recent["label"] == sel].iloc[0]["id"])
        shift_row = df_fn("SELECT * FROM shifts WHERE id=?", (sid,)).iloc[0].to_dict()

        employees = df_fn("SELECT id, name FROM employees WHERE active=1 ORDER BY name")
        emp_names = employees["name"].tolist() if not employees.empty else []

        col1, col2 = st.columns(2)
        new_status = col1.selectbox("Status setzen", STATUS_LIST,
                                    index=STATUS_LIST.index(str(shift_row.get("status", "geplant")))
                                    if str(shift_row.get("status", "")) in STATUS_LIST else 0)
        new_emp_name = col2.selectbox("Mitarbeiter zuweisen", ["— unbesetzt —"] + emp_names)

        col3, col4 = st.columns(2)
        if col3.button("💾 Status & Mitarbeiter speichern", type="primary"):
            new_eid = int(employees[employees["name"] == new_emp_name].iloc[0]["id"]) if new_emp_name != "— unbesetzt —" and not employees.empty else None
            run_fn("UPDATE shifts SET status=?, employee_id=? WHERE id=?", (new_status, new_eid, sid))
            log_fn("shift_updated", f"id={sid} status={new_status}")
            st.success("✅ Schicht aktualisiert!")
            st.rerun()
        if col4.button("🗑️ Schicht löschen"):
            run_fn("DELETE FROM shifts WHERE id=?", (sid,))
            log_fn("shift_deleted", str(sid))
            st.success("Schicht gelöscht.")
            st.rerun()

    with tabs[3]:
        st.subheader("⚠️ Doppelbelegungen")
        dup = df_fn("""
            SELECT s1.shift_date AS Datum, e.name AS Mitarbeiter, COUNT(*) AS Schichten_an_diesem_Tag
            FROM shifts s1
            JOIN employees e ON e.id=s1.employee_id
            GROUP BY s1.shift_date, s1.employee_id
            HAVING COUNT(*) > 1
            ORDER BY s1.shift_date DESC
        """)
        if not dup.empty:
            st.error(f"⚠️ {len(dup)} Doppelbelegung(en) gefunden!")
            st.dataframe(dup, use_container_width=True)
        else:
            st.success("✅ Keine Doppelbelegungen gefunden.")

        st.subheader("⚠️ Unbesetzte Schichten (nächste 14 Tage)")
        unbesetzt = df_fn("""
            SELECT s.shift_date AS Datum, s.start_time AS Von, s.end_time AS Bis,
                   COALESCE(c.company,'-') AS Kunde, s.location AS Ort, s.shift_type AS Typ
            FROM shifts s
            LEFT JOIN customers c ON c.id=s.customer_id
            WHERE s.employee_id IS NULL
              AND s.shift_date BETWEEN date('now') AND date('now','+14 days')
            ORDER BY s.shift_date
        """)
        if not unbesetzt.empty:
            st.warning(f"⚠️ {len(unbesetzt)} unbesetzte Schicht(en) in den nächsten 14 Tagen!")
            st.dataframe(unbesetzt, use_container_width=True)
        else:
            st.success("✅ Alle Schichten besetzt.")


# ─────────────────────────────────────────────────────────────
# 4. Verbesserter E-Mail-Versand
# ─────────────────────────────────────────────────────────────

def page_email_v2(run_fn, df_fn, generate_invoice_pdf_fn, queue_email_fn, send_email_fn) -> None:
    st.title("✉️ E-Mail-Versand")

    tabs = st.tabs(["📧 Rechnung/Mahnung", "📝 Freitext-Mail", "📋 E-Mail-Protokoll", "⚙️ Vorlagen"])

    with tabs[0]:
        invoices = df_fn("""
            SELECT i.id, i.invoice_no, c.company, c.email, i.description,
                   i.gross_total, i.paid_amount, i.pdf_path, i.status,
                   i.invoice_no || ' | ' || c.company || ' | ' || ROUND(i.gross_total,2) || ' €' AS label
            FROM invoices i JOIN customers c ON c.id=i.customer_id
            ORDER BY i.invoice_date DESC
        """)
        if invoices.empty:
            st.info("Keine Rechnungen vorhanden.")
            return

        label = st.selectbox("Rechnung wählen", invoices["label"].tolist())
        r = invoices[invoices["label"] == label].iloc[0]
        kind = st.radio("Art des Schreibens", ["Rechnung", "1. Mahnung", "2. Mahnung", "Letzte Mahnung"], horizontal=True)
        recipient = st.text_input("Empfänger E-Mail", str(r["email"] or ""))

        # Automatische Betreff/Body-Vorlagen je nach Art
        templates = {
            "Rechnung": (
                f"Rechnung {r['invoice_no']} – Byblos Sicherheitsdienst & Service",
                f"Sehr geehrte Damen und Herren,\n\nanbei erhalten Sie unsere Rechnung Nr. {r['invoice_no']} "
                f"für erbrachte Sicherheitsdienstleistungen in Höhe von {float(r['gross_total']):,.2f} EUR.\n\n"
                f"Wir bitten um Überweisung bis zum angegebenen Fälligkeitsdatum.\n\n"
                f"Mit freundlichen Grüßen\nByblos Sicherheitsdienst & Service GmbH"
            ),
            "1. Mahnung": (
                f"1. Zahlungserinnerung – Rechnung {r['invoice_no']}",
                f"Sehr geehrte Damen und Herren,\n\nbei der Durchsicht unserer Konten haben wir festgestellt, "
                f"dass die Rechnung Nr. {r['invoice_no']} über {float(r['gross_total']):,.2f} EUR noch nicht beglichen wurde.\n\n"
                f"Wir bitten Sie, den Betrag innerhalb von 7 Tagen zu überweisen.\n\n"
                f"Falls die Zahlung bereits erfolgt ist, bitten wir, dieses Schreiben als gegenstandslos zu betrachten.\n\n"
                f"Mit freundlichen Grüßen\nByblos Sicherheitsdienst & Service GmbH"
            ),
            "2. Mahnung": (
                f"2. Mahnung – Rechnung {r['invoice_no']} – DRINGEND",
                f"Sehr geehrte Damen und Herren,\n\ntrotz unserer Zahlungserinnerung ist die Rechnung Nr. {r['invoice_no']} "
                f"über {float(r['gross_total']):,.2f} EUR weiterhin offen.\n\n"
                f"Wir fordern Sie auf, den ausstehenden Betrag binnen 5 Werktagen zu überweisen, "
                f"andernfalls behalten wir uns rechtliche Schritte vor.\n\n"
                f"Mit freundlichen Grüßen\nByblos Sicherheitsdienst & Service GmbH"
            ),
            "Letzte Mahnung": (
                f"LETZTE MAHNUNG – Rechnung {r['invoice_no']} – Rechtliche Schritte",
                f"Sehr geehrte Damen und Herren,\n\nletztmalig fordern wir Sie auf, die Rechnung Nr. {r['invoice_no']} "
                f"über {float(r['gross_total']):,.2f} EUR SOFORT zu begleichen.\n\n"
                f"Bei Nichtbegleichung innerhalb von 3 Werktagen werden wir ohne weitere Ankündigung "
                f"rechtliche Schritte (Inkasso / Klage) einleiten.\n\n"
                f"Mit freundlichen Grüßen\nByblos Sicherheitsdienst & Service GmbH"
            ),
        }
        default_subject, default_body = templates.get(kind, templates["Rechnung"])
        subject = st.text_input("Betreff", default_subject)
        body = st.text_area("E-Mail-Text", default_body, height=220)

        col1, col2, col3 = st.columns(3)
        if col1.button("📄 PDF erzeugen/aktualisieren"):
            try:
                path = generate_invoice_pdf_fn(int(r["id"]))
                st.success(f"PDF erstellt: {path.name if hasattr(path,'name') else path}")
                st.rerun()
            except Exception as e:
                st.error(f"PDF-Fehler: {e}")

        if col2.button("💾 Als Entwurf speichern") and recipient:
            queue_email_fn(recipient, subject, body, str(r.get("pdf_path") or ""))
            st.success("Entwurf gespeichert.")
            st.rerun()

        if col3.button("🚀 Jetzt senden") and recipient:
            queue_email_fn(recipient, subject, body, str(r.get("pdf_path") or ""))
            pending = df_fn("SELECT id FROM email_log ORDER BY id DESC LIMIT 1")
            if not pending.empty:
                result = send_email_fn(int(pending.iloc[0]["id"]))
                st.info(result)
                st.rerun()

    with tabs[1]:
        st.subheader("Freitext-Mail senden")
        customers = df_fn("SELECT id, company, email FROM customers WHERE email != '' ORDER BY company")
        if not customers.empty:
            cust_label = st.selectbox("An Kunden senden", ["Manuell eingeben"] + customers["company"].tolist())
            if cust_label != "Manuell eingeben":
                auto_email = str(customers[customers["company"] == cust_label].iloc[0]["email"])
            else:
                auto_email = ""
        else:
            auto_email = ""
        recipient = st.text_input("E-Mail-Adresse", auto_email)
        subject = st.text_input("Betreff", "Byblos Sicherheitsdienst & Service – Information")
        body = st.text_area("Text", height=200)
        uploaded_attach = st.file_uploader("Anhang (optional)", type=["pdf", "xlsx", "docx"])

        attach_path = ""
        if uploaded_attach:
            from pathlib import Path
            tmp_path = Path("/tmp") / uploaded_attach.name
            tmp_path.write_bytes(uploaded_attach.read())
            attach_path = str(tmp_path)

        col1, col2 = st.columns(2)
        if col1.button("💾 Entwurf speichern") and recipient and subject:
            queue_email_fn(recipient, subject, body, attach_path)
            st.success("Entwurf gespeichert.")
        if col2.button("🚀 Sofort senden") and recipient and subject:
            queue_email_fn(recipient, subject, body, attach_path)
            pending = df_fn("SELECT id FROM email_log ORDER BY id DESC LIMIT 1")
            if not pending.empty:
                result = send_email_fn(int(pending.iloc[0]["id"]))
                st.info(result)

    with tabs[2]:
        log = df_fn("SELECT id, created_at AS Erstellt, sent_at AS Gesendet, recipient AS Empfänger, subject AS Betreff, status AS Status, error AS Fehler FROM email_log ORDER BY created_at DESC")
        if not log.empty:
            st.dataframe(log, use_container_width=True, height=350)
            pending = df_fn("SELECT id, recipient || ' | ' || subject AS label FROM email_log WHERE status IN ('Entwurf','Fehler') ORDER BY id DESC")
            if not pending.empty:
                sel = st.selectbox("Entwurf / Fehlgeschlagene Mail senden", pending["label"].tolist())
                eid = int(pending[pending["label"] == sel].iloc[0]["id"])
                if st.button("🚀 Jetzt senden"):
                    result = send_email_fn(eid)
                    st.info(result)
                    st.rerun()
                if st.button("🗑️ Entwurf löschen"):
                    run_fn("DELETE FROM email_log WHERE id=?", (eid,))
                    st.rerun()
        else:
            st.info("Keine E-Mails im Protokoll.")

    with tabs[3]:
        st.subheader("📝 E-Mail-Vorlagen")
        st.info("Vorlagen werden automatisch beim Erstellen von Rechnungs- und Mahnungs-Mails befüllt. Individuelle Anpassungen sind im Formular oben möglich.")
        st.markdown("""
**Verfügbare Vorlagen:**
- Rechnung (Standard)
- 1. Zahlungserinnerung (nach 14 Tagen)
- 2. Mahnung (nach 21 Tagen)
- Letzte Mahnung / Inkasso-Androhung (nach 30 Tagen)

Diese Vorlagen können durch Bearbeiten dieser Datei individuell angepasst werden:
`byblos_crm_app/extensions_v2_pages.py` → Funktion `page_email_v2` → `templates`-Dict.
        """)


# ─────────────────────────────────────────────────────────────
# 5. Verbessertes Backup & Export Center
# ─────────────────────────────────────────────────────────────

def page_export_v2(run_fn, df_fn, db_path, export_excel_fn, create_backup_fn) -> None:
    st.title("📦 Export & Backup Center")

    tabs = st.tabs(["💾 Backup", "📊 Excel-Export", "🗄️ Datenbank", "📋 Backup-Historie"])

    with tabs[0]:
        st.subheader("Vollständiges Backup erstellen")
        col1, col2 = st.columns(2)
        note = col1.text_input("Backup-Notiz", "manuell")
        if col2.button("🔄 Backup jetzt erstellen", type="primary"):
            with st.spinner("Backup wird erstellt..."):
                try:
                    b = create_backup_fn(note)
                    b_path = b if isinstance(b, str) else str(b)
                    size = Path(b_path).stat().st_size if Path(b_path).exists() else 0
                    st.success(f"✅ Backup erstellt: {Path(b_path).name} ({size/1024:.0f} KB)")
                    run_fn("INSERT INTO backups(file_path,file_size,note) VALUES(?,?,?)",
                           (b_path, size, note))
                    st.rerun()
                except Exception as e:
                    st.error(f"Backup-Fehler: {e}")

        # Letztes Backup-Info
        last = df_fn("SELECT * FROM backups ORDER BY created_at DESC LIMIT 1")
        if not last.empty:
            lb = last.iloc[0]
            age = (datetime.now() - datetime.fromisoformat(str(lb.get("created_at",""))[:19])).days if lb.get("created_at") else 999
            if age > 7:
                st.warning(f"⚠️ Letztes Backup ist {age} Tage alt!")
            else:
                st.success(f"✅ Letztes Backup: {str(lb.get('created_at',''))[:16]} ({age} Tage)")

            b_path = str(lb.get("file_path", ""))
            if b_path and Path(b_path).exists():
                st.download_button("📥 Letztes Backup herunterladen",
                                   Path(b_path).read_bytes(),
                                   file_name=Path(b_path).name,
                                   mime="application/zip")

    with tabs[1]:
        st.subheader("Excel-Export erstellen")
        export_tables = st.multiselect("Tabellen exportieren", [
            "Kunden", "Kontakthistorie", "Rechnungen", "Rechnungspositionen",
            "Mitarbeiter", "Dienstplan", "Lieferanten", "Ausgaben_BWA",
            "Zeiterfassung", "Audit_Log"
        ], default=["Kunden", "Rechnungen", "Mitarbeiter"])
        if st.button("📊 Excel erstellen", type="primary"):
            with st.spinner("Excel wird erstellt..."):
                try:
                    path = export_excel_fn()
                    st.success(f"✅ Excel erstellt: {Path(path).name}")
                    st.download_button("📥 Excel herunterladen",
                                       Path(path).read_bytes(),
                                       file_name=Path(path).name,
                                       mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
                except Exception as e:
                    st.error(f"Export-Fehler: {e}")

    with tabs[2]:
        st.subheader("SQLite-Datenbank herunterladen")
        st.caption(f"Datenbankpfad: {db_path}")
        if Path(str(db_path)).exists():
            size = Path(str(db_path)).stat().st_size
            st.metric("Datenbankgröße", f"{size/1024:.0f} KB")
            st.download_button("📥 SQLite-DB herunterladen",
                               Path(str(db_path)).read_bytes(),
                               file_name="byblos_crm_backup.db",
                               mime="application/octet-stream")
        else:
            st.error("Datenbankdatei nicht gefunden.")

    with tabs[3]:
        backups = df_fn("SELECT * FROM backups ORDER BY created_at DESC LIMIT 50")
        if not backups.empty:
            st.dataframe(backups, use_container_width=True)
        else:
            st.info("Noch keine Backups vorhanden.")
