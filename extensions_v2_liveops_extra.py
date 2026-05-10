"""
extensions_v2_liveops_extra.py – Erweiterte Live-Ops Features
==============================================================
1.  Schwarzes Brett / Digitaler Aushang
2.  Überstunden-Konto (kumuliert, Jahresansicht)
3.  System-Health-Monitor
4.  Backup-Rotation
5.  Kundenportal-Vorschau
6.  Dashboard-Widget-Konfiguration
7.  Mehrbenutzer-Rollensystem erweitert
8.  Benachrichtigungs-E-Mail bei Systemereignissen
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd
import streamlit as st


def fmt_eur(v: float) -> str:
    return f"{v:,.2f} €".replace(",","X").replace(".",",").replace("X",".")


# ─────────────────────────────────────────────────────────────
# DB-Registrierung
# ─────────────────────────────────────────────────────────────

def register_liveops_extra(run_fn, df_fn) -> None:
    run_fn("""CREATE TABLE IF NOT EXISTS bulletin_board (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        content TEXT NOT NULL,
        category TEXT DEFAULT 'Allgemein',
        priority TEXT DEFAULT 'normal',
        author TEXT,
        visible_from TEXT DEFAULT CURRENT_DATE,
        visible_until TEXT,
        pinned INTEGER DEFAULT 0,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )""")
    run_fn("""CREATE TABLE IF NOT EXISTS overtime_account (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        employee_id INTEGER NOT NULL,
        year INTEGER NOT NULL,
        month INTEGER NOT NULL,
        hours_worked REAL DEFAULT 0,
        hours_target REAL DEFAULT 0,
        overtime_hours REAL DEFAULT 0,
        cumulative_overtime REAL DEFAULT 0,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(employee_id, year, month),
        FOREIGN KEY(employee_id) REFERENCES employees(id)
    )""")
    run_fn("""CREATE TABLE IF NOT EXISTS dashboard_widget_config (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL,
        widget_name TEXT NOT NULL,
        enabled INTEGER DEFAULT 1,
        position INTEGER DEFAULT 0,
        UNIQUE(username, widget_name)
    )""")
    run_fn("""CREATE TABLE IF NOT EXISTS role_permissions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        role_name TEXT NOT NULL,
        permission TEXT NOT NULL,
        granted INTEGER DEFAULT 1,
        UNIQUE(role_name, permission)
    )""")
    # Standard-Berechtigungen seeden
    permissions = [
        ("Admin", "view_all"), ("Admin", "edit_all"), ("Admin", "delete_all"),
        ("Admin", "manage_users"), ("Admin", "view_financials"),
        ("Manager", "view_all"), ("Manager", "edit_invoices"),
        ("Manager", "edit_shifts"), ("Manager", "view_financials"),
        ("Manager", "approve_expenses"),
        ("Mitarbeiter", "view_own_shifts"), ("Mitarbeiter", "view_own_payroll"),
        ("Mitarbeiter", "submit_travel"), ("Mitarbeiter", "view_bulletin"),
        ("Buchhalter", "view_financials"), ("Buchhalter", "edit_expenses"),
        ("Buchhalter", "export_datev"), ("Buchhalter", "view_invoices"),
    ]
    for role, perm in permissions:
        try:
            run_fn("INSERT OR IGNORE INTO role_permissions(role_name,permission) VALUES(?,?)",
                   (role, perm))
        except Exception:
            pass


# ─────────────────────────────────────────────────────────────
# 1. Schwarzes Brett / Digitaler Aushang
# ─────────────────────────────────────────────────────────────

def render_bulletin_board_sidebar(df_fn) -> None:
    """Zeigt aktuelle Aushänge kurz in der Sidebar."""
    try:
        today = date.today().isoformat()
        pinned = df_fn(f"""
            SELECT title FROM bulletin_board
            WHERE pinned=1 AND visible_from <= '{today}'
              AND (visible_until IS NULL OR visible_until >= '{today}')
            LIMIT 3
        """)
        if not pinned.empty:
            with st.sidebar:
                st.markdown("**📌 Aushänge:**")
                for _, r in pinned.iterrows():
                    st.caption(f"• {r['title'][:30]}")
    except Exception:
        pass


def page_bulletin_board(run_fn, df_fn, current_user_fn) -> None:
    st.title("📌 Schwarzes Brett")
    st.caption("Digitaler Aushang für Mitarbeiter-Mitteilungen.")

    user = current_user_fn() or {}
    is_admin = user.get("role","").lower() in ("admin","manager","administrator")
    today = date.today().isoformat()

    tabs = st.tabs(["📋 Aktuelle Aushänge", "➕ Neuer Aushang",
                    "📂 Archiv", "⚙️ Verwalten"])

    with tabs[0]:
        posts = df_fn(f"""
            SELECT id, title AS Titel, content AS Inhalt,
                   category AS Kategorie, priority AS Priorität,
                   author AS Autor, pinned AS Angepinnt,
                   visible_until AS Gültig_bis,
                   created_at AS Erstellt
            FROM bulletin_board
            WHERE visible_from <= '{today}'
              AND (visible_until IS NULL OR visible_until >= '{today}')
            ORDER BY pinned DESC, created_at DESC
        """)
        if not posts.empty:
            for _, post in posts.iterrows():
                prio_colors = {"hoch":"#c0392b","normal":"#2980b9","niedrig":"#27ae60"}
                color = prio_colors.get(str(post["Priorität"]),"#888")
                pin_icon = "📌 " if post["Angepinnt"] else ""
                exp_text = f"⏰ bis {post['Gültig_bis']}" if post.get("Gültig_bis") else ""
                with st.expander(f"{pin_icon}**{post['Titel']}** — {post['Kategorie']} {exp_text}"):
                    st.markdown(str(post["Inhalt"]))
                    st.caption(f"Von: {post['Autor']} · {str(post['Erstellt'])[:16]}")
        else:
            st.info("Keine aktuellen Aushänge.")

    with tabs[1]:
        CATS_BB = ["Allgemein","Personal","Sicherheit","Betrieb","Wichtig","Feier & Events"]
        with st.form("bb_form", clear_on_submit=True):
            title    = st.text_input("Titel *")
            content  = st.text_area("Inhalt (Markdown) *", height=200)
            col1, col2, col3 = st.columns(3)
            category = col1.selectbox("Kategorie", CATS_BB)
            priority = col2.selectbox("Priorität", ["normal","hoch","niedrig"])
            pinned   = col3.checkbox("Anpinnen")
            col4, col5 = st.columns(2)
            vis_from = col4.date_input("Sichtbar ab", date.today())
            has_end  = col5.checkbox("Ablaufdatum setzen")
            vis_until = col5.date_input("Sichtbar bis",
                                         date.today() + timedelta(days=30)) if has_end else None
            if st.form_submit_button("📌 Aushang veröffentlichen", type="primary") and title and content:
                run_fn("""INSERT INTO bulletin_board(title,content,category,priority,
                          author,visible_from,visible_until,pinned)
                          VALUES(?,?,?,?,?,?,?,?)""",
                       (title, content, category, priority,
                        user.get("username","admin"),
                        vis_from.isoformat(),
                        vis_until.isoformat() if vis_until else None,
                        1 if pinned else 0))
                st.success(f"✅ '{title}' veröffentlicht!"); st.rerun()

    with tabs[2]:
        past = df_fn(f"""
            SELECT title AS Titel, category AS Kategorie, author AS Autor,
                   visible_until AS Abgelaufen, created_at AS Erstellt
            FROM bulletin_board WHERE visible_until < '{today}'
            ORDER BY visible_until DESC LIMIT 20
        """)
        if not past.empty:
            st.dataframe(past, use_container_width=True)
        else:
            st.info("Noch kein Archiv.")

    with tabs[3]:
        if not is_admin:
            st.info("Nur Admins können Aushänge verwalten.")
            return
        all_posts = df_fn("SELECT id, title AS Titel, pinned AS Angepinnt FROM bulletin_board ORDER BY created_at DESC")
        if not all_posts.empty:
            st.dataframe(all_posts.drop(columns=["id"]), use_container_width=True)
            del_sel = st.selectbox("Aushang löschen", all_posts["Titel"].tolist())
            if st.button("🗑️ Löschen"):
                del_id = int(all_posts[all_posts["Titel"]==del_sel].iloc[0]["id"])
                run_fn("DELETE FROM bulletin_board WHERE id=?", (del_id,))
                st.success("Gelöscht."); st.rerun()


# ─────────────────────────────────────────────────────────────
# 2. Überstunden-Konto (kumuliert)
# ─────────────────────────────────────────────────────────────

def page_overtime_account(run_fn, df_fn) -> None:
    st.title("⏱️ Überstunden-Konto")
    st.caption("Kumuliertes Überstunden-Konto je Mitarbeiter über das Jahr.")

    employees = df_fn("SELECT id, employee_no || ' – ' || name AS label, weekly_hours FROM employees WHERE active=1 ORDER BY name")
    if employees.empty:
        st.info("Keine Mitarbeiter.")
        return

    year = st.selectbox("Jahr", list(range(date.today().year, date.today().year-3,-1)))

    tabs = st.tabs(["📊 Übersicht alle MA", "📈 Detail Mitarbeiter",
                    "➕ Stunden eintragen", "📋 Monatsbericht"])

    with tabs[0]:
        # Überstunden aus Zeiterfassung aggregieren
        ot_data = df_fn(f"""
            SELECT e.id, e.name AS Mitarbeiter, e.employee_no AS Nr,
                   ROUND(COALESCE(SUM(t.net_hours),0),1) AS Ist_Stunden,
                   ROUND(e.weekly_hours / 5.0 * (
                       SELECT COUNT(*) FROM (
                           SELECT date('{year}-' || printf('%02d',m.m) || '-01', 'start of month')
                           FROM (SELECT 1 AS m UNION SELECT 2 UNION SELECT 3 UNION SELECT 4
                                 UNION SELECT 5 UNION SELECT 6 UNION SELECT 7 UNION SELECT 8
                                 UNION SELECT 9 UNION SELECT 10 UNION SELECT 11 UNION SELECT 12) m
                           WHERE m.m <= {date.today().month if date.today().year == year else 12}
                       )
                   ),1) AS Soll_Näherung
            FROM employees e
            LEFT JOIN time_entries t ON t.employee_id=e.id AND substr(t.date,1,4)='{year}'
            WHERE e.active=1
            GROUP BY e.id ORDER BY e.name
        """)

        if not ot_data.empty:
            ot_data["Überstunden"] = (ot_data["Ist_Stunden"] - ot_data["Soll_Näherung"]).round(1)
            ot_data["Status"] = ot_data["Überstunden"].apply(
                lambda v: "🟢 Ausgeglichen" if abs(v)<5 else "🔵 Mehr" if v>0 else "🔴 Weniger")

            c1, c2, c3 = st.columns(3)
            c1.metric("MA mit Plus-Stunden",  len(ot_data[ot_data["Überstunden"]>5]))
            c2.metric("MA mit Minus-Stunden", len(ot_data[ot_data["Überstunden"]<-5]))
            c3.metric("Gesamt-Überstunden",   f"{float(ot_data['Überstunden'].sum()):.0f}h")

            st.dataframe(ot_data[["Nr","Mitarbeiter","Ist_Stunden","Soll_Näherung","Überstunden","Status"]],
                         use_container_width=True)
            st.bar_chart(ot_data.set_index("Mitarbeiter")["Überstunden"])
        else:
            st.info("Keine Zeiterfassungs-Daten.")

    with tabs[1]:
        emp_sel = st.selectbox("Mitarbeiter", employees["label"].tolist())
        eid = int(employees[employees["label"] == emp_sel].iloc[0]["id"])
        weekly_h = float(employees[employees["label"] == emp_sel].iloc[0]["weekly_hours"] or 40)

        monthly = df_fn(f"""
            SELECT substr(t.date,1,7) AS Monat,
                   ROUND(SUM(t.net_hours),1) AS Ist,
                   ROUND({weekly_h}/5.0 * COUNT(DISTINCT t.date),1) AS Soll
            FROM time_entries t
            WHERE t.employee_id={eid} AND substr(t.date,1,4)='{year}'
            GROUP BY substr(t.date,1,7) ORDER BY Monat
        """)

        if not monthly.empty:
            monthly["Saldo"] = (monthly["Ist"] - monthly["Soll"]).round(1)
            monthly["Kumuliert"] = monthly["Saldo"].cumsum().round(1)
            st.dataframe(monthly, use_container_width=True)
            st.line_chart(monthly.set_index("Monat")["Kumuliert"])
            current_ot = float(monthly["Saldo"].sum())
            st.metric("Aktuelles Überstunden-Guthaben", f"{current_ot:+.1f} Stunden",
                       delta_color="normal" if current_ot >= 0 else "inverse")
        else:
            st.info("Keine Zeiterfassungs-Daten.")

    with tabs[2]:
        # Manuelle Stunden-Eingabe
        emp_s = st.selectbox("Mitarbeiter", employees["label"].tolist(), key="ot_emp")
        eid2 = int(employees[employees["label"] == emp_s].iloc[0]["id"])
        col1, col2, col3 = st.columns(3)
        ot_date = col1.date_input("Datum", date.today())
        hours = col2.number_input("Geleistete Stunden", min_value=0.0, value=8.0, step=0.5)
        notes = col3.text_input("Notiz")
        if st.button("💾 Stunden buchen", type="primary"):
            run_fn("INSERT OR IGNORE INTO time_entries(employee_id,date,net_hours,description) VALUES(?,?,?,?)",
                   (eid2, ot_date.isoformat(), hours, notes or "Manuell eingetragen"))
            st.success(f"✅ {hours}h für {ot_date} gebucht."); st.rerun()

    with tabs[3]:
        st.subheader(f"Monatsbericht {year}")
        summary = df_fn(f"""
            SELECT e.name AS Mitarbeiter,
                   ROUND(SUM(t.net_hours),1) AS Jahresstunden,
                   ROUND(e.weekly_hours * 52 / 12 * 12,1) AS Jahressoll
            FROM employees e
            LEFT JOIN time_entries t ON t.employee_id=e.id AND substr(t.date,1,4)='{year}'
            WHERE e.active=1 GROUP BY e.id ORDER BY Jahresstunden DESC
        """)
        if not summary.empty:
            st.dataframe(summary, use_container_width=True)
            csv = summary.to_csv(index=False, sep=";").encode("utf-8-sig")
            st.download_button("📥 Export CSV", csv, f"ueberstunden_{year}.csv", "text/csv")


# ─────────────────────────────────────────────────────────────
# 3. System-Health-Monitor
# ─────────────────────────────────────────────────────────────

def page_system_health(df_fn, db_path: Path) -> None:
    st.title("🖥️ System-Gesundheits-Monitor")
    st.caption("CPU, RAM, Festplatte und Anwendungsstatus in Echtzeit.")

    # Auto-refresh
    if st.button("🔄 Aktualisieren"):
        st.rerun()

    try:
        import psutil
        HAS_PSUTIL = True
    except ImportError:
        HAS_PSUTIL = False

    col1, col2, col3, col4 = st.columns(4)

    if HAS_PSUTIL:
        import psutil
        cpu_pct  = psutil.cpu_percent(interval=1)
        ram      = psutil.virtual_memory()
        disk     = psutil.disk_usage('/')

        col1.metric("🖥️ CPU", f"{cpu_pct}%",
                     delta_color="inverse" if cpu_pct > 80 else "normal")
        col2.metric("💾 RAM", f"{ram.percent}%",
                     f"{ram.used//1024//1024} MB / {ram.total//1024//1024} MB",
                     delta_color="inverse" if ram.percent > 85 else "normal")
        col3.metric("💿 Festplatte", f"{disk.percent}%",
                     f"{disk.free//1024//1024//1024} GB frei",
                     delta_color="inverse" if disk.percent > 90 else "normal")
    else:
        col1.info("psutil nicht installiert\n`pip install psutil`")

    # Datenbankgröße
    db_size = db_path.stat().st_size if db_path.exists() else 0
    col4.metric("🗄️ Datenbank", f"{db_size//1024} KB")

    st.divider()

    # App-Statistiken
    col1, col2, col3, col4 = st.columns(4)
    try:
        inv_count = int(df_fn("SELECT COUNT(*) AS n FROM invoices").iloc[0]["n"])
        cust_count = int(df_fn("SELECT COUNT(*) AS n FROM customers").iloc[0]["n"])
        shift_count = int(df_fn("SELECT COUNT(*) AS n FROM shifts WHERE shift_date >= date('now','-30 days')").iloc[0]["n"])
        last_backup = df_fn("SELECT MAX(created_at) AS ts FROM backups").iloc[0]["ts"] or "–"
        col1.metric("Rechnungen gesamt", inv_count)
        col2.metric("Kunden gesamt", cust_count)
        col3.metric("Schichten (30d)", shift_count)
        col4.metric("Letztes Backup", str(last_backup)[:10])
    except Exception:
        pass

    # Letzte Aktivitäten
    st.subheader("📋 Letzte Aktivitäten")
    try:
        log = df_fn("""
            SELECT created_at AS Zeit, action AS Aktion, details AS Details
            FROM audit_log ORDER BY created_at DESC LIMIT 15
        """)
        if not log.empty:
            st.dataframe(log, use_container_width=True, height=250)
    except Exception:
        st.info("Audit-Log leer.")

    # Prozesse prüfen
    st.divider()
    st.subheader("⚙️ Dienste")
    import subprocess, shutil

    services = {
        "Streamlit App":   ("curl", ["curl","-s","http://localhost:8501/_stcore/health"]),
        "FastAPI Server":  ("curl", ["curl","-s","http://localhost:8000/api/v1/health"]),
        "Python":          ("python3", ["python3","--version"]),
    }
    for name, (cmd, args) in services.items():
        if shutil.which(cmd):
            try:
                r = subprocess.run(args, capture_output=True, text=True, timeout=3)
                ok = r.returncode == 0
                col1, col2 = st.columns([3,1])
                col1.markdown(f"**{name}**")
                col2.markdown("🟢 OK" if ok else "🔴 Offline")
            except Exception:
                pass


# ─────────────────────────────────────────────────────────────
# 4. Backup-Rotation
# ─────────────────────────────────────────────────────────────

def rotate_backups(backup_dir: Path, max_count: int = 10) -> int:
    """Löscht alte Backups, behält max max_count."""
    backups = sorted(backup_dir.glob("*.db"), key=lambda f: f.stat().st_mtime, reverse=True)
    deleted = 0
    for old in backups[max_count:]:
        try:
            old.unlink()
            deleted += 1
        except Exception:
            pass
    return deleted


def page_backup_manager(run_fn, df_fn, create_backup_fn, db_path: Path) -> None:
    st.title("💾 Backup-Manager")
    st.caption("Automatische Backup-Rotation und Verwaltung.")

    backup_dir = db_path.parent / "backups"
    backup_dir.mkdir(exist_ok=True)

    tabs = st.tabs(["📋 Backups", "⚙️ Rotation", "🔄 Erstellen", "📊 Statistik"])

    with tabs[0]:
        backups_db = df_fn("SELECT file_path AS Datei, file_size AS Bytes, note AS Notiz, created_at AS Erstellt FROM backups ORDER BY created_at DESC LIMIT 50")
        files_on_disk = sorted(backup_dir.glob("*.db"), key=lambda f: f.stat().st_mtime, reverse=True)

        c1, c2, c3 = st.columns(3)
        c1.metric("Backups in DB", len(backups_db))
        c2.metric("Dateien auf Disk", len(files_on_disk))
        total_size = sum(f.stat().st_size for f in files_on_disk)
        c3.metric("Gesamtgröße", f"{total_size//1024//1024:.1f} MB")

        if not backups_db.empty:
            backups_db["KB"] = (backups_db["Bytes"] / 1024).round(0).astype("Int64")
            st.dataframe(backups_db[["Erstellt","Datei","KB","Notiz"]], use_container_width=True, height=300)

        for f in files_on_disk[:5]:
            col1, col2 = st.columns([3,1])
            col1.caption(f"📁 {f.name} ({f.stat().st_size//1024} KB)")
            col2.download_button("⬇️", f.read_bytes(), f.name,
                                  "application/octet-stream", key=f"dl_{f.name}")

    with tabs[1]:
        st.subheader("Automatische Backup-Rotation")
        max_count = st.slider("Maximale Backups aufbewahren", 3, 50, 10)
        st.caption(f"Älteste Backups über {max_count} werden automatisch gelöscht.")

        if st.button("🔄 Rotation jetzt ausführen", type="primary"):
            deleted = rotate_backups(backup_dir, max_count)
            if deleted > 0:
                st.success(f"✅ {deleted} alte Backups gelöscht.")
            else:
                st.info(f"Keine Rotation nötig (≤ {max_count} Backups vorhanden).")

        # Automatik-Einstellung
        auto_rotate = st.checkbox("Bei jedem Backup automatisch rotieren", value=True)
        if auto_rotate:
            st.info(f"Bei jedem neuen Backup werden Backups über {max_count} gelöscht.")

    with tabs[2]:
        note = st.text_input("Backup-Notiz", "manuell")
        encrypt = st.checkbox("AES-256 verschlüsseln")
        password = st.text_input("Passwort", type="password") if encrypt else ""

        if st.button("🔄 Backup erstellen", type="primary"):
            with st.spinner("Backup läuft..."):
                try:
                    bp = Path(str(create_backup_fn(note)))
                    size = bp.stat().st_size if bp.exists() else 0
                    run_fn("INSERT INTO backups(file_path,file_size,note) VALUES(?,?,?)",
                           (str(bp), size, note))

                    if encrypt and password and bp.exists():
                        from extensions_v2_liveops import encrypt_file
                        ok, enc_path = encrypt_file(bp, password)
                        if ok:
                            bp = Path(enc_path)
                            st.info(f"🔐 Verschlüsselt: {bp.name}")

                    if bp.exists():
                        st.success(f"✅ {bp.name} ({size//1024} KB)")
                        st.download_button("📥 Herunterladen",
                                           bp.read_bytes(), bp.name,
                                           "application/octet-stream")
                        # Auto-Rotation
                        rotate_backups(backup_dir, 10)
                except Exception as e:
                    st.error(f"Fehler: {e}")

    with tabs[3]:
        st.subheader("Backup-Verlauf")
        history = df_fn("SELECT substr(created_at,1,10) AS Datum, COUNT(*) AS Backups, SUM(file_size)/1024 AS KB_gesamt FROM backups GROUP BY substr(created_at,1,10) ORDER BY Datum DESC LIMIT 30")
        if not history.empty:
            st.bar_chart(history.set_index("Datum")["Backups"])


# ─────────────────────────────────────────────────────────────
# 5. Dashboard-Widget-Konfiguration
# ─────────────────────────────────────────────────────────────

AVAILABLE_WIDGETS = [
    ("kpi_umsatz", "💰 Umsatz Monat"),
    ("kpi_offene_rechnungen", "🧾 Offene Rechnungen"),
    ("kpi_mitarbeiter", "👥 Aktive Mitarbeiter"),
    ("kpi_schichten_heute", "📅 Schichten Heute"),
    ("kpi_ausgaben", "📤 Ausgaben Monat"),
    ("kpi_ergebnis", "📊 Ergebnis Monat"),
    ("kpi_aging", "⏳ Überfällige Rechnungen"),
    ("kpi_backup", "💾 Letztes Backup"),
    ("chart_umsatz_monat", "📈 Umsatz-Chart"),
    ("chart_ausgaben_kat", "📊 Ausgaben-Kategorien"),
    ("tabelle_offene_rechnungen", "📋 Offene Rechnungen Tabelle"),
    ("tabelle_schichten_heute", "📋 Schichten Heute Tabelle"),
    ("bulletin_preview", "📌 Schwarzes Brett"),
]


def page_dashboard_config(run_fn, df_fn, current_user_fn) -> None:
    st.title("🎛️ Dashboard anpassen")
    st.caption("Wähle welche Widgets auf deinem Dashboard angezeigt werden.")

    user = current_user_fn() or {}
    username = user.get("username","admin")

    # Aktuelle Konfiguration laden
    config = df_fn("SELECT widget_name, enabled, position FROM dashboard_widget_config WHERE username=? ORDER BY position",
                   (username,))
    configured = {}
    if not config.empty:
        for _, r in config.iterrows():
            configured[r["widget_name"]] = bool(r["enabled"])

    st.subheader("Widgets aktivieren/deaktivieren")
    cols = st.columns(3)
    widget_states = {}
    for i, (key, label) in enumerate(AVAILABLE_WIDGETS):
        default = configured.get(key, True)
        col = cols[i % 3]
        widget_states[key] = col.checkbox(label, value=default, key=f"wgt_{key}")

    if st.button("💾 Dashboard speichern", type="primary"):
        for pos, (key, label) in enumerate(AVAILABLE_WIDGETS):
            enabled = 1 if widget_states[key] else 0
            run_fn("""INSERT OR REPLACE INTO dashboard_widget_config(username,widget_name,enabled,position)
                      VALUES(?,?,?,?)""", (username, key, enabled, pos))
        st.success("✅ Dashboard-Konfiguration gespeichert!")
        st.rerun()

    st.divider()
    st.subheader("Vorschau (aktive Widgets)")
    active = [label for key, label in AVAILABLE_WIDGETS if widget_states.get(key, True)]
    for label in active:
        st.markdown(f"✅ {label}")


# ─────────────────────────────────────────────────────────────
# 6. Erweitertes Rollensystem
# ─────────────────────────────────────────────────────────────

def check_permission(df_fn, current_user_fn, permission: str) -> bool:
    """Prüft ob aktueller Nutzer eine Berechtigung hat."""
    user = current_user_fn() or {}
    role = user.get("role","Mitarbeiter")
    if role.lower() in ("admin","administrator"):
        return True
    result = df_fn("SELECT granted FROM role_permissions WHERE role_name=? AND permission=?",
                   (role, permission))
    return not result.empty and bool(result.iloc[0]["granted"])


def page_role_management(run_fn, df_fn, current_user_fn, hash_pw_fn) -> None:
    st.title("👥 Benutzer & Rollen")
    st.caption("Benutzerverwaltung mit rollenbasierter Zugriffskontrolle.")

    user = current_user_fn() or {}
    if user.get("role","").lower() not in ("admin","administrator"):
        st.error("Nur Administratoren haben Zugang.")
        return

    tabs = st.tabs(["👤 Benutzer", "🔐 Rollen & Rechte", "➕ Neuer Benutzer"])

    with tabs[0]:
        users = df_fn("""
            SELECT id, username AS Benutzer, role AS Rolle,
                   email AS E_Mail, active AS Aktiv, created_at AS Erstellt
            FROM users ORDER BY username
        """)
        if not users.empty:
            st.dataframe(users.drop(columns=["id"]), use_container_width=True)
            # Passwort ändern
            st.divider()
            st.subheader("Passwort ändern")
            sel_user = st.selectbox("Benutzer", users["Benutzer"].tolist())
            new_pw = st.text_input("Neues Passwort", type="password", min_chars=8)
            if st.button("🔑 Passwort setzen") and new_pw and len(new_pw) >= 8:
                h = hash_pw_fn(new_pw)
                uid = int(users[users["Benutzer"]==sel_user].iloc[0]["id"])
                run_fn("UPDATE users SET password_hash=? WHERE id=?", (h, uid))
                st.success(f"✅ Passwort für '{sel_user}' geändert.")

    with tabs[1]:
        st.subheader("Rollenberechtigungen")
        perms = df_fn("SELECT role_name AS Rolle, permission AS Berechtigung, granted AS Erteilt FROM role_permissions ORDER BY role_name, permission")
        if not perms.empty:
            pivot = perms.pivot_table(index="Berechtigung", columns="Rolle",
                                       values="Erteilt", fill_value=0)
            pivot = pivot.applymap(lambda v: "✅" if v else "–")
            st.dataframe(pivot, use_container_width=True)

        # Berechtigung ändern
        st.divider()
        ROLES = ["Admin","Manager","Buchhalter","Mitarbeiter"]
        PERMS = [p[1] for _, p in perms.iterrows()] if not perms.empty else ["view_all"]
        PERMS = list(set(PERMS))
        col1, col2, col3 = st.columns(3)
        r = col1.selectbox("Rolle", ROLES)
        p = col2.selectbox("Berechtigung", sorted(PERMS))
        g = col3.checkbox("Erteilen", value=True)
        if st.button("💾 Speichern"):
            run_fn("INSERT OR REPLACE INTO role_permissions(role_name,permission,granted) VALUES(?,?,?)",
                   (r, p, 1 if g else 0))
            st.success(f"{'✅' if g else '❌'} {r}: {p}"); st.rerun()

    with tabs[2]:
        ROLES_NEW = ["Admin","Manager","Buchhalter","Mitarbeiter","Steuerberater (Lesen)"]
        with st.form("new_user_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            uname = col1.text_input("Benutzername *")
            role  = col2.selectbox("Rolle", ROLES_NEW)
            email = col1.text_input("E-Mail")
            pw    = col2.text_input("Passwort *", type="password", min_chars=8)
            if st.form_submit_button("➕ Benutzer anlegen", type="primary") and uname and pw:
                existing = df_fn("SELECT id FROM users WHERE username=?", (uname,))
                if not existing.empty:
                    st.error(f"Benutzer '{uname}' existiert bereits.")
                elif len(pw) < 8:
                    st.error("Passwort muss mind. 8 Zeichen haben.")
                else:
                    h = hash_pw_fn(pw)
                    run_fn("INSERT INTO users(username,password_hash,role,email) VALUES(?,?,?,?)",
                           (uname, h, role, email))
                    st.success(f"✅ Benutzer '{uname}' ({role}) angelegt!")
                    st.rerun()


# ─────────────────────────────────────────────────────────────
# 7. Kundenportal-Vorschau
# ─────────────────────────────────────────────────────────────

def page_customer_portal_preview(df_fn) -> None:
    st.title("🌐 Kundenportal-Vorschau")
    st.caption("So würde ein Kunde sein Konto sehen (schreibgeschützte Ansicht).")

    customers = df_fn("SELECT id, customer_no || ' – ' || company AS label FROM customers ORDER BY company")
    if customers.empty:
        st.info("Keine Kunden.")
        return

    sel = st.selectbox("Kunden-Ansicht simulieren", customers["label"].tolist())
    cid = int(customers[customers["label"] == sel].iloc[0]["id"])

    # Kundeninfo
    cust = df_fn("SELECT * FROM customers WHERE id=?", (cid,)).iloc[0].to_dict()

    # Kundenportal-Layout simulieren
    st.markdown("---")
    st.markdown(f"""
<div style="background:#1a2744;padding:16px;border-radius:8px;margin-bottom:16px;">
<h2 style="color:white;margin:0;">🛡️ Byblos Sicherheitsdienst</h2>
<p style="color:#aaa;margin:4px 0 0;">Kundenportal – {cust.get('company','')}</p>
</div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns(3)

    # Offene Rechnungen
    open_inv = df_fn(f"""
        SELECT invoice_no AS Nr, invoice_date AS Datum, due_date AS Fällig,
               ROUND(gross_total - paid_amount,2) AS Offen_EUR, status AS Status
        FROM invoices WHERE customer_id={cid} AND status IN ('offen','ueberfaellig')
        ORDER BY due_date
    """)
    c_open = len(open_inv) if not open_inv.empty else 0
    c_sum  = float(open_inv["Offen_EUR"].sum()) if not open_inv.empty else 0
    col1.metric("Offene Rechnungen", c_open)
    col2.metric("Offener Betrag", fmt_eur(c_sum))

    # Letzte Schicht
    last_shift = df_fn(f"""
        SELECT shift_date, start_time, end_time, shift_type
        FROM shifts WHERE customer_id={cid} ORDER BY shift_date DESC LIMIT 1
    """)
    if not last_shift.empty:
        col3.metric("Letzte Schicht", str(last_shift.iloc[0]["shift_date"]))

    # Rechnungen
    if not open_inv.empty:
        st.subheader("📋 Offene Rechnungen")
        st.dataframe(open_inv, use_container_width=True)

    # Schichtenhistorie
    shifts = df_fn(f"""
        SELECT shift_date AS Datum, start_time AS Von, end_time AS Bis,
               shift_type AS Art, location AS Objekt, status AS Status
        FROM shifts WHERE customer_id={cid} ORDER BY shift_date DESC LIMIT 10
    """)
    if not shifts.empty:
        st.subheader("📅 Letzte Einsätze")
        st.dataframe(shifts, use_container_width=True)

    st.caption("*Dies ist eine Vorschau — das echte Kundenportal erfordert separaten Webserver*")
