"""
extensions_v2_enhancements.py – Byblos CRM v2 Erweiterungen
=============================================================
Neue Module:
  - Benachrichtigungssystem (Mahnungen, überfällige Dienste, SLA)
  - Erweitertes KPI-Tracking mit Trend-Pfeilen
  - Kalenderansicht für Dienstplan
  - Schnellaktionen-Cockpit
  - Dark-Mode CSS-Injektion
  - Export-Helper für mehrere Formate
  - Angebots-/Auftragsmanagement
  - Notfall-Protokoll / Schichtübergabe
"""

from __future__ import annotations

import json
import sqlite3
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
import streamlit as st


# ──────────────────────────────────────────────────────────────
# 1. CSS / Dark-Mode Styling
# ──────────────────────────────────────────────────────────────

CUSTOM_CSS = """
<style>
/* Sidebar Verbesserungen */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0d1117 0%, #1a1f2e 100%);
    border-right: 1px solid #2d3142;
}
[data-testid="stSidebar"] .stSelectbox label,
[data-testid="stSidebar"] .stRadio label {
    color: #c0c6d4 !important;
    font-size: 0.85rem;
}
/* KPI-Karten */
[data-testid="stMetric"] {
    background: #1a1f2e;
    border: 1px solid #2d3142;
    border-radius: 12px;
    padding: 12px 16px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.3);
}
[data-testid="stMetricValue"] {
    color: #e8eaf0 !important;
    font-weight: 700;
}
[data-testid="stMetricDelta"] {
    font-size: 0.85rem;
}
/* Alert-Boxen */
.byblos-alert-danger {
    background: rgba(192, 57, 43, 0.15);
    border-left: 4px solid #c0392b;
    padding: 10px 14px;
    border-radius: 4px;
    margin-bottom: 8px;
    color: #e8eaf0;
}
.byblos-alert-warning {
    background: rgba(243, 156, 18, 0.15);
    border-left: 4px solid #f39c12;
    padding: 10px 14px;
    border-radius: 4px;
    margin-bottom: 8px;
    color: #e8eaf0;
}
.byblos-alert-success {
    background: rgba(39, 174, 96, 0.15);
    border-left: 4px solid #27ae60;
    padding: 10px 14px;
    border-radius: 4px;
    margin-bottom: 8px;
    color: #e8eaf0;
}
/* Tabellen */
[data-testid="stDataFrame"] {
    border-radius: 8px;
    overflow: hidden;
}
/* Buttons */
.stButton > button {
    border-radius: 6px;
    font-weight: 600;
    transition: all 0.2s ease;
}
.stButton > button:hover {
    transform: translateY(-1px);
    box-shadow: 0 4px 12px rgba(192, 57, 43, 0.4);
}
/* Badges */
.badge-red    { background:#c0392b; color:#fff; padding:2px 8px; border-radius:12px; font-size:0.75rem; font-weight:700; }
.badge-orange { background:#e67e22; color:#fff; padding:2px 8px; border-radius:12px; font-size:0.75rem; font-weight:700; }
.badge-green  { background:#27ae60; color:#fff; padding:2px 8px; border-radius:12px; font-size:0.75rem; font-weight:700; }
.badge-blue   { background:#2980b9; color:#fff; padding:2px 8px; border-radius:12px; font-size:0.75rem; font-weight:700; }
/* Kalender-Grid */
.cal-header { background:#1a1f2e; padding:6px; text-align:center; font-weight:700; color:#c0392b; border-radius:4px; }
.cal-cell   { background:#0e1117; border:1px solid #2d3142; padding:6px; border-radius:4px; min-height:60px; }
.cal-cell-today { background:#1a1f2e; border:1px solid #c0392b; }
.cal-shift  { background:#c0392b22; border-left:3px solid #c0392b; padding:2px 4px; font-size:0.75rem; border-radius:2px; margin-bottom:2px; }
/* Print-Styles */
@media print {
    [data-testid="stSidebar"], .stButton { display: none !important; }
}
</style>
"""


def inject_css() -> None:
    """Injiziert das angepasste CSS in die Streamlit-App."""
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


# ──────────────────────────────────────────────────────────────
# 2. Benachrichtigungssystem
# ──────────────────────────────────────────────────────────────

def register_notifications(run_fn, df_fn) -> None:
    """Erstellt die Notifications-Tabelle falls nicht vorhanden."""
    run_fn("""
    CREATE TABLE IF NOT EXISTS notifications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        type TEXT NOT NULL,
        level TEXT DEFAULT 'info',
        title TEXT NOT NULL,
        message TEXT,
        ref_type TEXT,
        ref_id INTEGER,
        read INTEGER DEFAULT 0,
        dismissed INTEGER DEFAULT 0
    )""")


def generate_notifications(run_fn, df_fn) -> int:
    """
    Scannt die Datenbank auf Ereignisse und erzeugt neue Benachrichtigungen.
    Gibt die Anzahl neu erstellter Benachrichtigungen zurück.
    """
    today = date.today().isoformat()
    warn_date = (date.today() + timedelta(days=3)).isoformat()
    count = 0

    def _add(type_: str, level: str, title: str, msg: str, ref_type: str = "", ref_id: int = 0):
        nonlocal count
        # Duplikate vermeiden (gleicher Typ und ref_id heute)
        existing = df_fn(
            "SELECT id FROM notifications WHERE type=? AND ref_id=? AND date(created_at)=date('now')",
            (type_, ref_id)
        )
        if existing.empty:
            run_fn(
                "INSERT INTO notifications(type,level,title,message,ref_type,ref_id) VALUES(?,?,?,?,?,?)",
                (type_, level, title, msg, ref_type, ref_id)
            )
            count += 1

    # Überfällige Rechnungen
    try:
        overdue = df_fn(
            "SELECT id, invoice_no, company, gross_total FROM invoices i "
            "JOIN customers c ON c.id=i.customer_id "
            "WHERE i.status='offen' AND i.due_date < ? AND i.due_date != ''",
            (today,)
        )
        for _, row in overdue.iterrows():
            _add("overdue_invoice", "danger",
                 f"Rechnung {row['invoice_no']} überfällig",
                 f"{row['company']} · {row['gross_total']:,.2f} EUR",
                 "invoice", int(row["id"]))
    except Exception:
        pass

    # Schichten ohne Mitarbeiter in den nächsten 3 Tagen
    try:
        unstaffed = df_fn(
            "SELECT id, shift_date, location FROM shifts "
            "WHERE employee_id IS NULL AND shift_date BETWEEN ? AND ? AND status='geplant'",
            (today, warn_date)
        )
        for _, row in unstaffed.iterrows():
            _add("unstaffed_shift", "warning",
                 f"Schicht ohne Mitarbeiter: {row['shift_date']}",
                 f"Ort: {row.get('location', '-')}",
                 "shift", int(row["id"]))
    except Exception:
        pass

    # Mitarbeiter mit unbezahlten Überstunden > 20h
    try:
        overtime = df_fn(
            "SELECT employee_id, SUM(overtime_hours) AS ot FROM time_entries "
            "WHERE status='freigegeben' AND overtime_hours > 0 "
            "GROUP BY employee_id HAVING SUM(overtime_hours) > 20"
        )
        for _, row in overtime.iterrows():
            _add("overtime_pending", "warning",
                 f"Mitarbeiter hat >20h Überstunden",
                 f"Mitarbeiter-ID {int(row['employee_id'])}: {row['ot']:.1f}h offen",
                 "employee", int(row["employee_id"]))
    except Exception:
        pass

    # Backup älter als 7 Tage
    try:
        last_backup = df_fn("SELECT MAX(created_at) AS ts FROM backups")
        if not last_backup.empty and last_backup.iloc[0]["ts"]:
            ts = last_backup.iloc[0]["ts"]
            try:
                bdate = datetime.fromisoformat(str(ts)[:19]).date()
                if (date.today() - bdate).days > 7:
                    _add("backup_old", "warning",
                         "Backup älter als 7 Tage",
                         f"Letztes Backup: {bdate.isoformat()}",
                         "backup", 0)
            except Exception:
                pass
        else:
            _add("no_backup", "danger", "Kein Backup vorhanden",
                 "Bitte erstelle ein Backup unter Export & Backup Center.",
                 "backup", 0)
    except Exception:
        pass

    return count


def show_notification_bell(df_fn) -> None:
    """Zeigt ein Glöckchen-Icon mit Anzahl ungelesener Benachrichtigungen in der Sidebar."""
    try:
        unread = df_fn("SELECT COUNT(*) AS n FROM notifications WHERE read=0 AND dismissed=0")
        n = int(unread.iloc[0]["n"]) if not unread.empty else 0
        if n > 0:
            st.sidebar.markdown(
                f'<div style="text-align:center; padding:4px 0;">'
                f'<span class="badge-red">🔔 {n} Hinweis{"e" if n != 1 else ""}</span></div>',
                unsafe_allow_html=True
            )
    except Exception:
        pass


def page_notifications(run_fn, df_fn) -> None:
    """Seite: Alle Benachrichtigungen / Systemhinweise."""
    st.title("🔔 Benachrichtigungen & Hinweise")

    # Neue generieren
    new_count = generate_notifications(run_fn, df_fn)
    if new_count > 0:
        st.toast(f"{new_count} neue Hinweise generiert", icon="🔔")

    col1, col2 = st.columns([3, 1])
    with col2:
        if st.button("Alle als gelesen markieren"):
            run_fn("UPDATE notifications SET read=1 WHERE read=0")
            st.rerun()
        if st.button("Erledigte ausblenden"):
            run_fn("UPDATE notifications SET dismissed=1 WHERE read=1")
            st.rerun()

    try:
        notes = df_fn(
            "SELECT * FROM notifications WHERE dismissed=0 ORDER BY created_at DESC LIMIT 100"
        )
    except Exception:
        st.info("Benachrichtigungssystem wird initialisiert...")
        return

    if notes.empty:
        st.success("✅ Keine offenen Hinweise – alles in Ordnung!")
        return

    level_icons = {"danger": "🔴", "warning": "🟡", "info": "🔵", "success": "🟢"}
    level_css = {"danger": "byblos-alert-danger", "warning": "byblos-alert-warning",
                 "info": "", "success": "byblos-alert-success"}

    for _, row in notes.iterrows():
        icon = level_icons.get(str(row.get("level", "info")), "ℹ️")
        css_class = level_css.get(str(row.get("level", "info")), "")
        ts = str(row.get("created_at", ""))[:16]
        title = str(row.get("title", ""))
        message = str(row.get("message", ""))
        nid = int(row["id"])
        read_mark = "" if row.get("read") else "**·** "

        st.markdown(
            f'<div class="{css_class}" style="margin-bottom:6px;">'
            f'{icon} {read_mark}<strong>{title}</strong> '
            f'<span style="color:#888;font-size:0.8rem;float:right;">{ts}</span><br>'
            f'<span style="font-size:0.9rem;">{message}</span></div>',
            unsafe_allow_html=True
        )
        c1, c2 = st.columns([1, 6])
        with c1:
            if st.button("✓", key=f"notif_read_{nid}", help="Als erledigt markieren"):
                run_fn("UPDATE notifications SET read=1, dismissed=1 WHERE id=?", (nid,))
                st.rerun()


# ──────────────────────────────────────────────────────────────
# 3. Erweitertes Dashboard mit Trends
# ──────────────────────────────────────────────────────────────

def page_dashboard_v2(run_fn, df_fn) -> None:
    """Verbessertes Dashboard mit Trend-Vergleich Vormonat und Schnellaktionen."""
    inject_css()
    st.title("📊 Dashboard")

    today = date.today()
    start_month = today.replace(day=1).isoformat()
    last_month_start = (today.replace(day=1) - timedelta(days=1)).replace(day=1).isoformat()
    last_month_end = (today.replace(day=1) - timedelta(days=1)).isoformat()

    # KPIs aktueller Monat
    rev_m = float(df_fn("SELECT COALESCE(SUM(gross_total),0) AS v FROM invoices WHERE invoice_date>=? AND status='bezahlt'", (start_month,)).iloc[0]["v"])
    exp_m = float(df_fn("SELECT COALESCE(SUM(gross_amount),0) AS v FROM expenses WHERE expense_date>=?", (start_month,)).iloc[0]["v"])
    open_m = float(df_fn("SELECT COALESCE(SUM(gross_total-paid_amount),0) AS v FROM invoices WHERE status IN ('offen','ueberfaellig')").iloc[0]["v"])
    overdue = int(df_fn("SELECT COUNT(*) AS n FROM invoices WHERE status='ueberfaellig'").iloc[0]["n"])

    # KPIs Vormonat für Delta
    rev_lm = float(df_fn("SELECT COALESCE(SUM(gross_total),0) AS v FROM invoices WHERE invoice_date BETWEEN ? AND ? AND status='bezahlt'", (last_month_start, last_month_end)).iloc[0]["v"])
    exp_lm = float(df_fn("SELECT COALESCE(SUM(gross_amount),0) AS v FROM expenses WHERE expense_date BETWEEN ? AND ?", (last_month_start, last_month_end)).iloc[0]["v"])

    profit_m = rev_m - exp_m
    profit_lm = rev_lm - exp_lm

    def fmt_eur(v): return f"{v:,.2f} €".replace(",", "X").replace(".", ",").replace("X", ".")
    def delta_eur(curr, prev):
        d = curr - prev
        return f"{'+' if d >= 0 else ''}{fmt_eur(d)} ggü. Vormonat"

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("💰 Umsatz bezahlt", fmt_eur(rev_m), delta_eur(rev_m, rev_lm))
    c2.metric("📤 Ausgaben", fmt_eur(exp_m), delta_eur(exp_m, exp_lm))
    c3.metric("📈 Ergebnis", fmt_eur(profit_m), delta_eur(profit_m, profit_lm))
    c4.metric("⏳ Offene Posten", fmt_eur(open_m),
              f"🔴 {overdue} überfällig" if overdue else "✅ Keine überfällig")

    st.divider()

    # Schnellaktionen
    st.subheader("⚡ Schnellaktionen")
    qa1, qa2, qa3, qa4, qa5 = st.columns(5)
    if qa1.button("➕ Neue Rechnung", use_container_width=True):
        st.session_state["_nav_override"] = "Rechnungen"
        st.rerun()
    if qa2.button("👤 Neuer Kunde", use_container_width=True):
        st.session_state["_nav_override"] = "Kunden"
        st.rerun()
    if qa3.button("📅 Dienst planen", use_container_width=True):
        st.session_state["_nav_override"] = "Einsatzplanung"
        st.rerun()
    if qa4.button("💸 Ausgabe buchen", use_container_width=True):
        st.session_state["_nav_override"] = "Ausgaben/BWA"
        st.rerun()
    if qa5.button("🔔 Hinweise", use_container_width=True):
        st.session_state["_nav_override"] = "Benachrichtigungen"
        st.rerun()

    st.divider()

    col_l, col_r = st.columns([2, 1])
    with col_l:
        # Umsatz-Chart letzter 12 Monate
        st.subheader("📅 Umsatz / Ausgaben (letzte 12 Monate)")
        chart_data = df_fn("""
            SELECT substr(invoice_date,1,7) AS monat,
                   SUM(CASE WHEN status='bezahlt' THEN gross_total ELSE 0 END) AS Umsatz_bezahlt,
                   SUM(gross_total) AS Umsatz_gesamt
            FROM invoices
            WHERE invoice_date >= date('now', '-12 months')
            GROUP BY substr(invoice_date,1,7)
            ORDER BY monat
        """)
        exp_chart = df_fn("""
            SELECT substr(expense_date,1,7) AS monat, SUM(gross_amount) AS Ausgaben
            FROM expenses
            WHERE expense_date >= date('now', '-12 months')
            GROUP BY substr(expense_date,1,7)
            ORDER BY monat
        """)
        if not chart_data.empty:
            merged = chart_data.merge(exp_chart, on="monat", how="left").fillna(0)
            merged = merged.set_index("monat")
            st.bar_chart(merged[["Umsatz_bezahlt", "Ausgaben"]])
        else:
            st.info("Noch keine Rechnungsdaten vorhanden.")

    with col_r:
        # Hinweise
        st.subheader("🔔 Aktuelle Hinweise")
        try:
            notes = df_fn(
                "SELECT level, title FROM notifications WHERE dismissed=0 ORDER BY created_at DESC LIMIT 8"
            )
            if notes.empty:
                st.success("Keine offenen Hinweise")
            else:
                icons = {"danger": "🔴", "warning": "🟡", "info": "🔵", "success": "🟢"}
                for _, n in notes.iterrows():
                    icon = icons.get(str(n.get("level", "info")), "ℹ️")
                    st.markdown(f"{icon} {n['title']}")
        except Exception:
            st.info("Keine Hinweise.")

    st.divider()

    # Nächste Dienste
    st.subheader("🗓️ Nächste Dienste (7 Tage)")
    shifts = df_fn("""
        SELECT s.shift_date AS Datum, s.start_time AS Von, s.end_time AS Bis,
               COALESCE(e.name, '⚠️ unbesetzt') AS Mitarbeiter,
               COALESCE(c.company, '-') AS Kunde,
               s.location AS Ort, s.shift_type AS Art, s.status AS Status
        FROM shifts s
        LEFT JOIN employees e ON e.id=s.employee_id
        LEFT JOIN customers c ON c.id=s.customer_id
        WHERE s.shift_date BETWEEN ? AND ?
        ORDER BY s.shift_date, s.start_time LIMIT 30
    """, (today.isoformat(), (today + timedelta(days=7)).isoformat()))
    if not shifts.empty:
        st.dataframe(shifts, use_container_width=True, height=300)
    else:
        st.info("Keine Dienste in den nächsten 7 Tagen geplant.")

    # Letzte Rechnungen
    col_inv, col_exp = st.columns(2)
    with col_inv:
        st.subheader("🧾 Letzte Rechnungen")
        inv = df_fn("""
            SELECT i.invoice_no AS Nr, c.company AS Kunde,
                   i.invoice_date AS Datum, i.gross_total AS Brutto, i.status AS Status
            FROM invoices i JOIN customers c ON c.id=i.customer_id
            ORDER BY i.created_at DESC LIMIT 10
        """)
        if not inv.empty:
            st.dataframe(inv, use_container_width=True, height=250)

    with col_exp:
        st.subheader("📤 Letzte Ausgaben")
        exp = df_fn("""
            SELECT e.expense_no AS Nr, COALESCE(s.name,'-') AS Lieferant,
                   e.expense_date AS Datum, e.gross_amount AS Brutto, e.status AS Status
            FROM expenses e LEFT JOIN suppliers s ON s.id=e.supplier_id
            ORDER BY e.created_at DESC LIMIT 10
        """)
        if not exp.empty:
            st.dataframe(exp, use_container_width=True, height=250)


# ──────────────────────────────────────────────────────────────
# 4. Kalenderansicht für Dienstplan
# ──────────────────────────────────────────────────────────────

def page_calendar_view(run_fn, df_fn) -> None:
    """Kalenderansicht für den Einsatzplan."""
    inject_css()
    st.title("📅 Kalender-Einsatzplan")

    col_nav1, col_nav2, col_nav3 = st.columns([1, 3, 1])
    today = date.today()

    if "cal_year" not in st.session_state:
        st.session_state["cal_year"] = today.year
    if "cal_month" not in st.session_state:
        st.session_state["cal_month"] = today.month

    with col_nav1:
        if st.button("◀ Vormonat"):
            if st.session_state["cal_month"] == 1:
                st.session_state["cal_month"] = 12
                st.session_state["cal_year"] -= 1
            else:
                st.session_state["cal_month"] -= 1
            st.rerun()

    year = st.session_state["cal_year"]
    month = st.session_state["cal_month"]

    import calendar
    month_name = calendar.month_name[month]
    col_nav2.markdown(f"### {month_name} {year}", unsafe_allow_html=False)

    with col_nav3:
        if st.button("Nächster ▶"):
            if st.session_state["cal_month"] == 12:
                st.session_state["cal_month"] = 1
                st.session_state["cal_year"] += 1
            else:
                st.session_state["cal_month"] += 1
            st.rerun()

    # Dienste des Monats laden
    month_start = date(year, month, 1).isoformat()
    if month == 12:
        month_end = date(year + 1, 1, 1).isoformat()
    else:
        month_end = date(year, month + 1, 1).isoformat()

    shifts = df_fn("""
        SELECT s.shift_date, s.start_time, s.end_time,
               COALESCE(e.name, '?') AS mitarbeiter,
               COALESCE(c.company, '-') AS kunde,
               s.shift_type, s.status, s.location
        FROM shifts s
        LEFT JOIN employees e ON e.id=s.employee_id
        LEFT JOIN customers c ON c.id=s.customer_id
        WHERE s.shift_date >= ? AND s.shift_date < ?
        ORDER BY s.shift_date, s.start_time
    """, (month_start, month_end))

    # Dienste nach Datum gruppieren
    shifts_by_date: Dict[str, list] = {}
    for _, row in shifts.iterrows():
        d = str(row["shift_date"])
        if d not in shifts_by_date:
            shifts_by_date[d] = []
        shifts_by_date[d].append(row)

    # Wochentag-Header
    day_names = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]
    header_cols = st.columns(7)
    for i, name in enumerate(day_names):
        color = "#c0392b" if i >= 5 else "#6c757d"
        header_cols[i].markdown(
            f'<div style="text-align:center;font-weight:700;color:{color};padding:4px;">{name}</div>',
            unsafe_allow_html=True
        )

    # Kalender-Grid
    cal = calendar.monthcalendar(year, month)
    for week in cal:
        cols = st.columns(7)
        for i, day_num in enumerate(week):
            with cols[i]:
                if day_num == 0:
                    st.markdown('<div style="min-height:70px;"></div>', unsafe_allow_html=True)
                    continue
                day_str = date(year, month, day_num).isoformat()
                is_today = day_str == today.isoformat()
                day_shifts = shifts_by_date.get(day_str, [])
                border_color = "#c0392b" if is_today else "#2d3142"
                bg_color = "#1a1f2e" if is_today else "#0e1117"
                html = f'<div style="background:{bg_color};border:1px solid {border_color};border-radius:6px;padding:4px 6px;min-height:70px;">'
                html += f'<div style="font-weight:700;color:{"#c0392b" if is_today else "#e8eaf0"};font-size:0.9rem;">{day_num}</div>'
                for s in day_shifts[:3]:
                    emp = str(s["mitarbeiter"])[:12]
                    time_str = f"{str(s['start_time'])[:5]}"
                    status_colors = {"geplant": "#2980b9", "bestätigt": "#27ae60",
                                     "abgeschlossen": "#7f8c8d", "ausgefallen": "#c0392b"}
                    sc = status_colors.get(str(s.get("status", "geplant")), "#2980b9")
                    html += f'<div style="background:{sc}22;border-left:2px solid {sc};padding:1px 3px;font-size:0.7rem;border-radius:2px;margin-top:2px;color:#e8eaf0;">{time_str} {emp}</div>'
                if len(day_shifts) > 3:
                    html += f'<div style="font-size:0.7rem;color:#888;">+{len(day_shifts)-3} weitere</div>'
                html += '</div>'
                st.markdown(html, unsafe_allow_html=True)


# ──────────────────────────────────────────────────────────────
# 5. Angebots- und Auftragsmanagement
# ──────────────────────────────────────────────────────────────

def register_offers(run_fn, df_fn) -> None:
    """Erstellt Angebots- und Auftragstabellen."""
    run_fn("""
    CREATE TABLE IF NOT EXISTS offers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        offer_no TEXT UNIQUE,
        customer_id INTEGER,
        offer_date TEXT NOT NULL,
        valid_until TEXT,
        description TEXT,
        net_total REAL DEFAULT 0,
        vat_rate REAL DEFAULT 19,
        vat_total REAL DEFAULT 0,
        gross_total REAL DEFAULT 0,
        status TEXT DEFAULT 'entwurf',
        notes TEXT,
        pdf_path TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(customer_id) REFERENCES customers(id)
    )""")
    run_fn("""
    CREATE TABLE IF NOT EXISTS offer_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        offer_id INTEGER NOT NULL,
        position INTEGER,
        description TEXT NOT NULL,
        quantity REAL DEFAULT 1,
        unit TEXT DEFAULT 'Stunden',
        unit_price REAL DEFAULT 0,
        total REAL DEFAULT 0,
        FOREIGN KEY(offer_id) REFERENCES offers(id)
    )""")


def page_offers(run_fn, df_fn) -> None:
    """Seite: Angebotsverwaltung."""
    inject_css()
    st.title("📋 Angebote & Aufträge")
    OFFER_STATUS = ["entwurf", "versendet", "angenommen", "abgelehnt", "abgelaufen"]

    tabs = st.tabs(["📋 Übersicht", "➕ Neues Angebot", "🔄 Status-Pipeline"])

    with tabs[0]:
        status_filter = st.selectbox("Status filtern", ["alle"] + OFFER_STATUS)
        if status_filter == "alle":
            data = df_fn("""
                SELECT o.id, o.offer_no AS Nr, c.company AS Kunde, o.offer_date AS Datum,
                       o.valid_until AS Gültig_bis, o.gross_total AS Brutto, o.status AS Status,
                       o.description AS Beschreibung
                FROM offers o LEFT JOIN customers c ON c.id=o.customer_id
                ORDER BY o.offer_date DESC
            """)
        else:
            data = df_fn("""
                SELECT o.id, o.offer_no AS Nr, c.company AS Kunde, o.offer_date AS Datum,
                       o.valid_until AS Gültig_bis, o.gross_total AS Brutto, o.status AS Status,
                       o.description AS Beschreibung
                FROM offers o LEFT JOIN customers c ON c.id=o.customer_id
                WHERE o.status=? ORDER BY o.offer_date DESC
            """, (status_filter,))
        if not data.empty:
            st.dataframe(data, use_container_width=True)
            # Angenommene Angebote → Rechnung konvertieren
            angenommen = data[data["Status"] == "angenommen"]
            if not angenommen.empty:
                st.subheader("→ In Rechnung umwandeln")
                sel_label = st.selectbox("Angebot auswählen",
                                         [f"{r['Nr']} – {r['Kunde']}" for _, r in angenommen.iterrows()])
                if st.button("✅ Als Rechnung übernehmen"):
                    sel_no = sel_label.split(" – ")[0]
                    offer = df_fn("SELECT * FROM offers WHERE offer_no=?", (sel_no,))
                    if not offer.empty:
                        o = offer.iloc[0]
                        st.info(f"Angebot {sel_no} bereit zur Rechnungsübernahme. "
                                f"Bitte manuell unter Rechnungen anlegen und Daten übernehmen.")
        else:
            st.info("Keine Angebote vorhanden.")

    with tabs[1]:
        customers = df_fn("SELECT id, customer_no || ' - ' || company AS label FROM customers ORDER BY company")
        with st.form("offer_form"):
            # Angebotsnummer auto
            last_offer = df_fn("SELECT offer_no FROM offers ORDER BY id DESC LIMIT 1")
            if not last_offer.empty:
                try:
                    last_n = int(last_offer.iloc[0]["offer_no"].split("-")[-1])
                    offer_no_default = f"ANG-{last_n + 1:04d}"
                except Exception:
                    offer_no_default = "ANG-0001"
            else:
                offer_no_default = "ANG-0001"

            a, b, c = st.columns(3)
            offer_no = a.text_input("Angebots-Nr.", offer_no_default)
            offer_date = b.date_input("Angebotsdatum", date.today())
            valid_until = c.date_input("Gültig bis", date.today() + timedelta(days=30))

            customer_label = st.selectbox("Kunde", customers["label"].tolist() if not customers.empty else [])
            description = st.text_area("Beschreibung / Leistungsumfang")
            status = st.selectbox("Status", OFFER_STATUS)

            st.markdown("**Positionen**")
            cols = st.columns([3, 1, 1, 1, 1])
            cols[0].markdown("Beschreibung")
            cols[1].markdown("Menge")
            cols[2].markdown("Einheit")
            cols[3].markdown("Einzelpreis")
            cols[4].markdown("Gesamt")

            items = []
            for i in range(1, 6):
                c1, c2, c3, c4, c5 = st.columns([3, 1, 1, 1, 1])
                desc_i = c1.text_input(f"Pos {i}", key=f"off_desc_{i}", label_visibility="collapsed")
                qty_i = c2.number_input("", min_value=0.0, value=0.0, step=0.5, key=f"off_qty_{i}", label_visibility="collapsed")
                unit_i = c3.text_input("", "Std.", key=f"off_unit_{i}", label_visibility="collapsed")
                price_i = c4.number_input("", min_value=0.0, value=0.0, step=5.0, key=f"off_price_{i}", label_visibility="collapsed")
                total_i = qty_i * price_i
                c5.markdown(f"**{total_i:,.2f} €**")
                if desc_i and qty_i > 0:
                    items.append({"desc": desc_i, "qty": qty_i, "unit": unit_i, "price": price_i, "total": total_i})

            vat_rate = st.number_input("MwSt %", min_value=0.0, value=19.0, step=1.0)
            notes = st.text_area("Interne Notizen")

            net_total = sum(it["total"] for it in items)
            vat_total = round(net_total * vat_rate / 100, 2)
            gross_total = net_total + vat_total
            st.markdown(f"**Netto: {net_total:,.2f} € | MwSt: {vat_total:,.2f} € | Brutto: {gross_total:,.2f} €**")

            if st.form_submit_button("💾 Angebot speichern") and description and not customers.empty:
                cid = int(customers[customers["label"] == customer_label].iloc[0]["id"])
                run_fn("""INSERT INTO offers(offer_no,customer_id,offer_date,valid_until,description,
                          net_total,vat_rate,vat_total,gross_total,status,notes)
                          VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
                       (offer_no, cid, offer_date.isoformat(), valid_until.isoformat(),
                        description, net_total, vat_rate, vat_total, gross_total, status, notes))
                oid = df_fn("SELECT id FROM offers WHERE offer_no=?", (offer_no,)).iloc[0]["id"]
                for pos, it in enumerate(items, 1):
                    run_fn("""INSERT INTO offer_items(offer_id,position,description,quantity,unit,unit_price,total)
                              VALUES(?,?,?,?,?,?,?)""",
                           (int(oid), pos, it["desc"], it["qty"], it["unit"], it["price"], it["total"]))
                st.success(f"✅ Angebot {offer_no} gespeichert!")
                st.rerun()

    with tabs[2]:
        st.subheader("Status-Pipeline")
        for status in OFFER_STATUS:
            count = df_fn("SELECT COUNT(*) AS n FROM offers WHERE status=?", (status,)).iloc[0]["n"]
            total = df_fn("SELECT COALESCE(SUM(gross_total),0) AS v FROM offers WHERE status=?", (status,)).iloc[0]["v"]
            icon = {"entwurf": "📝", "versendet": "📨", "angenommen": "✅",
                    "abgelehnt": "❌", "abgelaufen": "⏰"}.get(status, "•")
            col1, col2 = st.columns([2, 1])
            col1.markdown(f"{icon} **{status.capitalize()}** – {count} Angebot(e)")
            col2.markdown(f"**{float(total):,.2f} €**")


# ──────────────────────────────────────────────────────────────
# 6. Schichtübergabe-Protokoll
# ──────────────────────────────────────────────────────────────

def register_handover(run_fn, df_fn) -> None:
    """Erstellt Schichtübergabe-Tabelle."""
    run_fn("""
    CREATE TABLE IF NOT EXISTS shift_handovers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        shift_date TEXT NOT NULL,
        location TEXT,
        handover_from TEXT,
        handover_to TEXT,
        incidents TEXT,
        equipment_status TEXT,
        notes TEXT,
        signature_from TEXT,
        signature_to TEXT,
        status TEXT DEFAULT 'offen'
    )""")


def page_handover_protocol(run_fn, df_fn) -> None:
    """Seite: Schichtübergabe-Protokoll."""
    inject_css()
    st.title("📝 Schichtübergabe-Protokoll")

    tabs = st.tabs(["📋 Übersicht", "➕ Neue Übergabe", "📄 Protokoll drucken"])

    with tabs[0]:
        data = df_fn("""
            SELECT id, shift_date AS Datum, location AS Ort,
                   handover_from AS Von, handover_to AS An,
                   status AS Status, created_at AS Erstellt
            FROM shift_handovers ORDER BY shift_date DESC LIMIT 50
        """)
        if not data.empty:
            st.dataframe(data, use_container_width=True)
        else:
            st.info("Noch keine Übergabeprotokolle vorhanden.")

    with tabs[1]:
        with st.form("handover_form"):
            col1, col2, col3 = st.columns(3)
            shift_date = col1.date_input("Schichtdatum", date.today())
            location = col2.text_input("Einsatzort")
            status = col3.selectbox("Status", ["offen", "übergeben", "bestätigt"])

            col4, col5 = st.columns(2)
            handover_from = col4.text_input("Übergebender Mitarbeiter")
            handover_to = col5.text_input("Übernehmender Mitarbeiter")

            incidents = st.text_area("Vorfälle / Besonderheiten während der Schicht",
                                     placeholder="Keine besonderen Vorkommnisse / oder Beschreibung...")
            equipment_status = st.text_area("Ausrüstungsstatus",
                                            placeholder="Funkgeräte OK, Fahrzeug getankt, ...")
            notes = st.text_area("Weitere Notizen / Anweisungen für nächste Schicht")

            col6, col7 = st.columns(2)
            sig_from = col6.text_input("Unterschrift / Kürzel Übergebender")
            sig_to = col7.text_input("Unterschrift / Kürzel Übernehmender")

            if st.form_submit_button("💾 Protokoll speichern"):
                run_fn("""INSERT INTO shift_handovers
                    (shift_date,location,handover_from,handover_to,incidents,equipment_status,notes,signature_from,signature_to,status)
                    VALUES(?,?,?,?,?,?,?,?,?,?)""",
                       (shift_date.isoformat(), location, handover_from, handover_to,
                        incidents, equipment_status, notes, sig_from, sig_to, status))
                st.success("✅ Übergabeprotokoll gespeichert!")
                st.rerun()

    with tabs[2]:
        protocols = df_fn(
            "SELECT id, shift_date || ' – ' || COALESCE(location,'-') AS label FROM shift_handovers ORDER BY shift_date DESC LIMIT 20"
        )
        if not protocols.empty:
            selected = st.selectbox("Protokoll auswählen", protocols["label"].tolist())
            pid = int(protocols[protocols["label"] == selected].iloc[0]["id"])
            p = df_fn("SELECT * FROM shift_handovers WHERE id=?", (pid,)).iloc[0].to_dict()
            st.markdown(f"""
## Schichtübergabe-Protokoll

| Feld | Inhalt |
|------|--------|
| Datum | {p.get('shift_date','')} |
| Ort | {p.get('location','')} |
| Von | {p.get('handover_from','')} |
| An | {p.get('handover_to','')} |
| Status | {p.get('status','')} |
| Erstellt | {str(p.get('created_at',''))[:16]} |

**Vorfälle / Besonderheiten:**
{p.get('incidents','–')}

**Ausrüstungsstatus:**
{p.get('equipment_status','–')}

**Weitere Notizen:**
{p.get('notes','–')}

---
Übergebender: ________________  |  Übernehmender: ________________
""")
        else:
            st.info("Keine Protokolle vorhanden.")


# ──────────────────────────────────────────────────────────────
# 7. Statistik / Reports
# ──────────────────────────────────────────────────────────────

def page_reports(run_fn, df_fn) -> None:
    """Seite: Auswertungen & Berichte."""
    inject_css()
    st.title("📊 Auswertungen & Berichte")

    tabs = st.tabs(["💰 Umsatz", "👥 Kunden", "👷 Mitarbeiter", "📅 Dienste"])

    with tabs[0]:
        st.subheader("Umsatzanalyse")
        year_sel = st.selectbox("Jahr", list(range(date.today().year, date.today().year - 5, -1)))
        rev = df_fn("""
            SELECT substr(invoice_date,1,7) AS Monat,
                   SUM(gross_total) AS Brutto_gesamt,
                   SUM(CASE WHEN status='bezahlt' THEN gross_total ELSE 0 END) AS Bezahlt,
                   SUM(CASE WHEN status IN ('offen','ueberfaellig') THEN gross_total ELSE 0 END) AS Offen,
                   COUNT(*) AS Anzahl
            FROM invoices WHERE substr(invoice_date,1,4)=?
            GROUP BY substr(invoice_date,1,7) ORDER BY Monat
        """, (str(year_sel),))
        if not rev.empty:
            st.dataframe(rev, use_container_width=True)
            st.bar_chart(rev.set_index("Monat")[["Bezahlt", "Offen"]])
            total = float(rev["Brutto_gesamt"].sum())
            paid = float(rev["Bezahlt"].sum())
            st.metric(f"Jahresumsatz {year_sel}", f"{total:,.2f} €".replace(",","X").replace(".","," ).replace("X","."),
                      f"Bezahlt: {paid:,.2f} €".replace(",","X").replace(".",",").replace("X","."))

    with tabs[1]:
        st.subheader("Top-Kunden (nach Umsatz)")
        top = df_fn("""
            SELECT c.company AS Kunde, COUNT(*) AS Rechnungen,
                   SUM(i.gross_total) AS Brutto_gesamt,
                   SUM(CASE WHEN i.status='bezahlt' THEN i.gross_total ELSE 0 END) AS Bezahlt
            FROM invoices i JOIN customers c ON c.id=i.customer_id
            GROUP BY c.id ORDER BY Brutto_gesamt DESC LIMIT 20
        """)
        if not top.empty:
            st.dataframe(top, use_container_width=True)
            st.bar_chart(top.set_index("Kunde")[["Brutto_gesamt"]])

    with tabs[2]:
        st.subheader("Mitarbeiter-Einsätze")
        emp_stats = df_fn("""
            SELECT e.name AS Mitarbeiter,
                   COUNT(s.id) AS Schichten,
                   SUM(CAST((strftime('%s',s.end_time) - strftime('%s',s.start_time)) AS REAL) / 3600.0) AS Stunden_approx
            FROM shifts s JOIN employees e ON e.id=s.employee_id
            WHERE s.status IN ('geplant','bestätigt','abgeschlossen')
            GROUP BY e.id ORDER BY Schichten DESC
        """)
        if not emp_stats.empty:
            st.dataframe(emp_stats, use_container_width=True)
        else:
            st.info("Noch keine Schichtdaten vorhanden.")

    with tabs[3]:
        st.subheader("Dienst-Auswertung")
        shift_stats = df_fn("""
            SELECT shift_type AS Art, status AS Status, COUNT(*) AS Anzahl
            FROM shifts
            GROUP BY shift_type, status ORDER BY Anzahl DESC
        """)
        if not shift_stats.empty:
            st.dataframe(shift_stats, use_container_width=True)
            st.bar_chart(
                shift_stats.groupby("Art")["Anzahl"].sum().reset_index().set_index("Art")
            )


# ──────────────────────────────────────────────────────────────
# 8. Registrierung aller neuen Module
# ──────────────────────────────────────────────────────────────

def register_all_v2(run_fn, df_fn) -> None:
    """Registriert alle v2-Erweiterungen (DB-Init)."""
    register_notifications(run_fn, df_fn)
    register_offers(run_fn, df_fn)
    register_handover(run_fn, df_fn)
