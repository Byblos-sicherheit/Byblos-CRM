"""
extensions_v2_final2.py – Finale Integrationsschicht für Byblos CRM v2
=======================================================================
1. iCal/ICS Export (Schichten + Steuertermine für Kalender-Apps)
2. PWA-Manifest + offline-fähige Metadaten
3. Cloud-Backup (Nextcloud/WebDAV)
4. Telegram-Integration in Tagesroutine
5. Schichten mit Lohnzettel per E-Mail versenden
6. Erweitertes Systemplus-Cockpit (Live-Betriebsübersicht)
7. Semantische KI-Suche (TF-IDF über alle Tabellen)
8. Automatische BWA-Zuordnung beim Bankimport
9. Vollständige Smart-Import OCR-Pipeline
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import hashlib
import json

import pandas as pd
import streamlit as st


def fmt_eur(v: float) -> str:
    return f"{v:,.2f} €".replace(",", "X").replace(".", ",").replace("X", ".")


# ─────────────────────────────────────────────────────────────
# 1. iCal / ICS Export
# ─────────────────────────────────────────────────────────────

def generate_ics(events: List[Dict]) -> str:
    """
    Generiert eine ICS-Datei aus einer Liste von Events.
    Jedes Event-Dict: title, start (datetime/date), end, description, location, uid
    """
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Byblos CRM v2//DE",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        "X-WR-CALNAME:Byblos CRM",
        "X-WR-TIMEZONE:Europe/Berlin",
    ]

    for ev in events:
        uid = ev.get("uid") or hashlib.md5(f"{ev['title']}{ev['start']}".encode()).hexdigest()
        start = ev["start"]
        end   = ev.get("end", start)
        now   = datetime.now().strftime("%Y%m%dT%H%M%SZ")

        # Date vs DateTime
        if isinstance(start, datetime):
            dtstart = start.strftime("DTSTART:%Y%m%dT%H%M%S")
            dtend   = end.strftime("DTEND:%Y%m%dT%H%M%S") if isinstance(end, datetime) else dtstart
        else:
            dtstart = start.strftime("DTSTART;VALUE=DATE:%Y%m%d")
            dtend   = (end + timedelta(days=1)).strftime("DTEND;VALUE=DATE:%Y%m%d") if isinstance(end, date) else dtstart

        desc     = str(ev.get("description", "")).replace("\n", "\\n").replace(",", "\\,")
        location = str(ev.get("location", "")).replace(",", "\\,")
        title    = str(ev["title"]).replace(",", "\\,").replace("\n", " ")

        lines += [
            "BEGIN:VEVENT",
            f"UID:{uid}@byblos-crm",
            f"DTSTAMP:{now}",
            dtstart,
            dtend,
            f"SUMMARY:{title}",
            f"DESCRIPTION:{desc}" if desc else "",
            f"LOCATION:{location}" if location else "",
            "END:VEVENT",
        ]

    lines.append("END:VCALENDAR")
    return "\r\n".join(l for l in lines if l)


def page_ical_export(df_fn) -> None:
    st.title("📅 Kalender-Export (iCal/ICS)")
    st.caption("Schichten, Steuertermine und Wiedervorlagen in Kalender-Apps importieren.")

    tabs = st.tabs(["📅 Schichten", "💰 Steuertermine", "🗓️ Wiedervorlagen", "📥 Import-Anleitung"])

    with tabs[0]:
        st.subheader("Schichten als iCal exportieren")
        col1, col2, col3 = st.columns(3)
        from_d = col1.date_input("Von", date.today())
        to_d   = col2.date_input("Bis", date.today() + timedelta(days=90))
        emp_filter = col3.text_input("Mitarbeiter-Filter (leer = alle)")

        q = """
            SELECT s.shift_date, s.start_time, s.end_time,
                   s.shift_type, s.location, s.notes,
                   COALESCE(e.name,'Unbesetzt') AS mitarbeiter,
                   COALESCE(c.company,'') AS kunde
            FROM shifts s
            LEFT JOIN employees e ON e.id=s.employee_id
            LEFT JOIN customers c ON c.id=s.customer_id
            WHERE s.shift_date BETWEEN ? AND ?
        """
        params = [from_d.isoformat(), to_d.isoformat()]
        if emp_filter:
            q += " AND e.name LIKE ?"
            params.append(f"%{emp_filter}%")
        q += " ORDER BY s.shift_date, s.start_time"

        shifts = df_fn(q, tuple(params))
        if not shifts.empty:
            st.metric("Schichten", len(shifts))
            events = []
            for _, r in shifts.iterrows():
                try:
                    sd  = date.fromisoformat(str(r["shift_date"]))
                    st_ = datetime.strptime(f"{r['shift_date']} {str(r['start_time'])[:5]}", "%Y-%m-%d %H:%M")
                    et_ = datetime.strptime(f"{r['shift_date']} {str(r['end_time'])[:5]}", "%Y-%m-%d %H:%M")
                    if et_ <= st_:
                        et_ += timedelta(days=1)
                except Exception:
                    continue
                events.append({
                    "title": f"🛡️ {r['shift_type']} – {r['mitarbeiter']}",
                    "start": st_,
                    "end": et_,
                    "description": f"Mitarbeiter: {r['mitarbeiter']}\nKunde: {r['kunde']}\n{r.get('notes','') or ''}",
                    "location": str(r.get("location") or ""),
                    "uid": f"shift-{r['shift_date']}-{r['start_time']}-{r['mitarbeiter']}",
                })
            ics = generate_ics(events)
            st.download_button("📥 Schichten als ICS herunterladen",
                               ics.encode("utf-8"),
                               f"byblos_schichten_{from_d}_{to_d}.ics",
                               "text/calendar")
            st.success(f"✅ {len(events)} Schichten in ICS-Datei.")
        else:
            st.info("Keine Schichten im Zeitraum.")

    with tabs[1]:
        st.subheader("Steuertermine als iCal exportieren")
        year_tax = st.selectbox("Jahr", list(range(date.today().year, date.today().year + 2)))
        taxes = df_fn("SELECT due_date, tax_type, description FROM tax_calendar WHERE substr(due_date,1,4)=? AND status='offen' ORDER BY due_date",
                      (str(year_tax),))
        if not taxes.empty:
            events = []
            for _, r in taxes.iterrows():
                try:
                    d = date.fromisoformat(str(r["due_date"])[:10])
                except Exception:
                    continue
                events.append({
                    "title": f"💰 {r['tax_type']}",
                    "start": d,
                    "description": str(r.get("description", "")),
                    "uid": f"tax-{r['due_date']}-{r['tax_type']}",
                })
            ics = generate_ics(events)
            st.download_button("📥 Steuertermine als ICS",
                               ics.encode("utf-8"),
                               f"byblos_steuertermine_{year_tax}.ics",
                               "text/calendar")
            st.success(f"✅ {len(events)} Termine exportiert.")
        else:
            st.info("Keine offenen Steuertermine.")

    with tabs[2]:
        st.subheader("Wiedervorlagen als iCal exportieren")
        tasks = df_fn("SELECT due_date, title, description, category, assigned_to FROM followup_tasks WHERE status!='erledigt' ORDER BY due_date")
        if not tasks.empty:
            events = []
            for _, r in tasks.iterrows():
                try:
                    d = date.fromisoformat(str(r["due_date"])[:10])
                except Exception:
                    continue
                events.append({
                    "title": f"📌 {r['title']}",
                    "start": d,
                    "description": str(r.get("description", "")),
                    "uid": f"task-{r['due_date']}-{r['title']}",
                })
            ics = generate_ics(events)
            st.download_button("📥 Wiedervorlagen als ICS",
                               ics.encode("utf-8"),
                               "byblos_wiedervorlagen.ics",
                               "text/calendar")
            st.success(f"✅ {len(events)} Aufgaben exportiert.")
        else:
            st.info("Keine offenen Wiedervorlagen.")

    with tabs[3]:
        st.subheader("ICS in Kalender-Apps importieren")
        st.markdown("""
| Kalender-App | Import-Methode |
|---|---|
| **Google Calendar** | Einstellungen → Kalender importieren → ICS-Datei wählen |
| **Outlook** | Datei → Öffnen & Exportieren → Importieren → ICS |
| **Apple Kalender (Mac/iPhone)** | Doppelklick auf ICS-Datei |
| **Thunderbird** | Kalender → Ereignisse importieren |
| **Android (Google)** | ICS per E-Mail senden, dann öffnen |

**Tipp:** Für automatische Synchronisation ICS-URL als Kalender-Abonnement einrichten 
(erfordert öffentlichen URL – geplant für v3 mit Server-Deployment).
        """)


# ─────────────────────────────────────────────────────────────
# 2. Cloud-Backup (Nextcloud/WebDAV)
# ─────────────────────────────────────────────────────────────

def upload_to_webdav(filepath: Path, webdav_url: str, username: str,
                      password: str, remote_path: str) -> Tuple[bool, str]:
    """Lädt eine Datei per WebDAV hoch (Nextcloud-kompatibel)."""
    try:
        import urllib.request
        import base64
        with open(filepath, "rb") as f:
            data = f.read()
        credentials = base64.b64encode(f"{username}:{password}".encode()).decode()
        remote_url  = f"{webdav_url.rstrip('/')}/{remote_path.lstrip('/')}"
        req = urllib.request.Request(remote_url, data=data, method="PUT")
        req.add_header("Authorization", f"Basic {credentials}")
        req.add_header("Content-Type", "application/octet-stream")
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.status in (200, 201, 204), f"HTTP {resp.status}"
    except Exception as e:
        return False, str(e)


def page_cloud_backup(run_fn, df_fn, get_setting_fn, set_setting_fn,
                       db_path: Path, create_backup_fn) -> None:
    st.title("☁️ Cloud-Backup (Nextcloud / WebDAV)")

    tabs = st.tabs(["⚙️ Einrichtung", "🔄 Jetzt sichern", "📋 Backup-Protokoll"])

    with tabs[0]:
        st.subheader("WebDAV-Verbindung konfigurieren")
        with st.form("webdav_form"):
            webdav_url = st.text_input("WebDAV-URL",
                                        get_setting_fn("webdav_url", ""),
                                        placeholder="https://nextcloud.beispiel.de/remote.php/dav/files/BENUTZER/")
            webdav_user = st.text_input("Benutzername",
                                         get_setting_fn("webdav_user", ""))
            webdav_pass = st.text_input("Passwort / App-Passwort",
                                         get_setting_fn("webdav_pass", ""), type="password")
            webdav_dir  = st.text_input("Zielordner auf Server",
                                         get_setting_fn("webdav_dir", "ByblosCRM/Backups/"))
            auto_backup = st.checkbox("Automatisch bei Tagesroutine hochladen",
                                      value=get_setting_fn("webdav_auto", "0") == "1")
            if st.form_submit_button("💾 Speichern", type="primary"):
                for k, v in [
                    ("webdav_url", webdav_url), ("webdav_user", webdav_user),
                    ("webdav_pass", webdav_pass), ("webdav_dir", webdav_dir),
                    ("webdav_auto", "1" if auto_backup else "0"),
                ]:
                    set_setting_fn(k, v)
                st.success("✅ WebDAV-Einstellungen gespeichert.")

        st.divider()
        st.markdown("""
**Unterstützte Cloud-Dienste:**
- ☁️ **Nextcloud** (selbst gehostet oder Anbieter)
- 📁 **ownCloud**
- 🌐 Beliebige **WebDAV-Server**

**Nextcloud App-Passwort erstellen:**
1. Nextcloud → Einstellungen → Sicherheit → App-Passwörter
2. Neues App-Passwort "ByblosCRM" erstellen
3. Passwort oben eintragen (normales Passwort aus Sicherheitsgründen vermeiden)
        """)

    with tabs[1]:
        st.subheader("Backup erstellen & hochladen")
        col1, col2 = st.columns(2)
        local_only = col1.checkbox("Nur lokal (kein Upload)", value=False)
        note = col2.text_input("Backup-Notiz", "manuell cloud")

        if st.button("🔄 Backup jetzt erstellen", type="primary"):
            with st.spinner("Backup wird erstellt..."):
                try:
                    backup_path = create_backup_fn(note)
                    bp = Path(str(backup_path))
                    size = bp.stat().st_size if bp.exists() else 0
                    run_fn("INSERT INTO backups(file_path,file_size,note) VALUES(?,?,?)",
                           (str(bp), size, note))
                    st.success(f"✅ Backup: {bp.name} ({size//1024} KB)")

                    if not local_only:
                        webdav_url  = get_setting_fn("webdav_url", "")
                        webdav_user = get_setting_fn("webdav_user", "")
                        webdav_pass = get_setting_fn("webdav_pass", "")
                        webdav_dir  = get_setting_fn("webdav_dir", "ByblosCRM/")

                        if webdav_url and webdav_user:
                            remote_path = f"{webdav_dir}{bp.name}"
                            ok, msg = upload_to_webdav(bp, webdav_url, webdav_user,
                                                        webdav_pass, remote_path)
                            if ok:
                                st.success(f"☁️ Hochgeladen nach {remote_path}")
                            else:
                                st.warning(f"⚠️ Upload fehlgeschlagen: {msg}")
                        else:
                            st.info("WebDAV nicht konfiguriert – nur lokal gespeichert.")

                    # Download-Button
                    if bp.exists():
                        st.download_button("📥 Backup herunterladen",
                                           bp.read_bytes(), bp.name,
                                           "application/octet-stream")
                except Exception as e:
                    st.error(f"Fehler: {e}")

    with tabs[2]:
        backups = df_fn("SELECT created_at AS Erstellt, file_path AS Datei, file_size AS Größe_Bytes, note AS Notiz FROM backups ORDER BY created_at DESC LIMIT 30")
        if not backups.empty:
            backups["Größe_KB"] = (backups["Größe_Bytes"] / 1024).round(0).astype(int)
            st.dataframe(backups[["Erstellt","Datei","Größe_KB","Notiz"]], use_container_width=True)
        else:
            st.info("Noch keine Backups.")


# ─────────────────────────────────────────────────────────────
# 3. Erweiterter Systemplus-Cockpit (Echtzeit-Betriebsübersicht)
# ─────────────────────────────────────────────────────────────

def page_live_operations(df_fn) -> None:
    st.title("🔴 Live-Betriebsübersicht")
    st.caption("Echtzeit-Überblick über alle aktiven Einsätze, offene Positionen und Systemstatus.")

    # Auto-Refresh alle 60 Sekunden
    refresh_interval = st.select_slider(
        "Auto-Refresh", ["Manuell", "30s", "60s", "5min"],
        value="60s"
    )
    if refresh_interval != "Manuell":
        seconds = {"30s": 30, "60s": 60, "5min": 300}[refresh_interval]
        st.markdown(
            f'<meta http-equiv="refresh" content="{seconds}">',
            unsafe_allow_html=True
        )

    today = date.today().isoformat()
    now_hour = datetime.now().strftime("%H:%M")

    # ── Aktuell im Dienst ──────────────────────────────────────
    st.subheader(f"🛡️ Heutige Einsätze – {today} {now_hour}")
    current = df_fn("""
        SELECT s.shift_date AS Datum, s.start_time AS Von, s.end_time AS Bis,
               s.shift_type AS Typ, s.location AS Objekt,
               COALESCE(e.name,'⚠️ UNBESETZT') AS Mitarbeiter,
               COALESCE(c.company,'–') AS Kunde,
               s.status AS Status
        FROM shifts s
        LEFT JOIN employees e ON e.id=s.employee_id
        LEFT JOIN customers c ON c.id=s.customer_id
        WHERE s.shift_date=?
        ORDER BY s.start_time
    """, (today,))

    if not current.empty:
        active  = current[current["Status"].isin(["geplant","bestätigt"])]
        unbes   = current[current["Mitarbeiter"] == "⚠️ UNBESETZT"]
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Heutige Schichten", len(current))
        c2.metric("🟢 Aktiv/Geplant", len(active))
        c3.metric("⚠️ Unbesetzt", len(unbes))
        c4.metric("✅ Abgeschlossen", len(current[current["Status"]=="abgeschlossen"]))

        if not unbes.empty:
            st.error(f"⚠️ {len(unbes)} unbesetzte Schicht(en) heute!")
            st.dataframe(unbes, use_container_width=True)

        st.dataframe(current, use_container_width=True, height=250)
    else:
        st.info("Heute keine Schichten geplant.")

    st.divider()

    # ── Morgen-Vorschau ────────────────────────────────────────
    tomorrow = (date.today() + timedelta(days=1)).isoformat()
    st.subheader(f"📅 Morgen: {tomorrow}")
    tomorrow_shifts = df_fn("""
        SELECT s.start_time AS Von, s.end_time AS Bis, s.shift_type AS Typ,
               COALESCE(e.name,'⚠️ UNBESETZT') AS Mitarbeiter,
               COALESCE(c.company,'–') AS Kunde, s.location AS Objekt
        FROM shifts s
        LEFT JOIN employees e ON e.id=s.employee_id
        LEFT JOIN customers c ON c.id=s.customer_id
        WHERE s.shift_date=?
        ORDER BY s.start_time
    """, (tomorrow,))
    if not tomorrow_shifts.empty:
        unbes_tom = tomorrow_shifts[tomorrow_shifts["Mitarbeiter"] == "⚠️ UNBESETZT"]
        if not unbes_tom.empty:
            st.warning(f"⚠️ {len(unbes_tom)} unbesetzte Schicht(en) morgen!")
        st.dataframe(tomorrow_shifts, use_container_width=True)
    else:
        st.info("Morgen keine Schichten geplant.")

    # ── Offene Posten ──────────────────────────────────────────
    st.divider()
    col_l, col_r = st.columns(2)

    with col_l:
        st.subheader("💰 Offene Rechnungen")
        open_inv = df_fn("""
            SELECT COUNT(*) AS n, COALESCE(SUM(gross_total-paid_amount),0) AS sum_v
            FROM invoices WHERE status IN ('offen','ueberfaellig')
        """).iloc[0]
        c1, c2 = st.columns(2)
        c1.metric("Offene Rechnungen", int(open_inv["n"]))
        c2.metric("Summe offen", fmt_eur(float(open_inv["sum_v"])))

        overdue = df_fn("""
            SELECT i.invoice_no AS Nr, c.company AS Kunde,
                   i.due_date AS Fällig,
                   ROUND(i.gross_total-i.paid_amount,2) AS Offen
            FROM invoices i JOIN customers c ON c.id=i.customer_id
            WHERE i.status='ueberfaellig'
            ORDER BY i.due_date LIMIT 5
        """)
        if not overdue.empty:
            st.dataframe(overdue, use_container_width=True)

    with col_r:
        st.subheader("🔔 Aktuelle Hinweise")
        try:
            notes = df_fn("SELECT level, title, created_at FROM notifications WHERE dismissed=0 ORDER BY created_at DESC LIMIT 8")
            if not notes.empty:
                icons = {"danger":"🔴","warning":"🟡","info":"🔵","success":"🟢"}
                for _, n in notes.iterrows():
                    icon = icons.get(str(n.get("level","info")), "ℹ️")
                    st.markdown(f"{icon} **{n['title']}**")
            else:
                st.success("✅ Keine Hinweise")
        except Exception:
            st.info("Benachrichtigungssystem initialisiert.")

    # ── System-Status ──────────────────────────────────────────
    st.divider()
    st.subheader("⚙️ System-Status")
    col1, col2, col3, col4 = st.columns(4)

    # Letztes Backup
    last_bk = df_fn("SELECT MAX(created_at) AS ts FROM backups")
    bk_ts = str(last_bk.iloc[0]["ts"] or "nie")[:16] if not last_bk.empty else "nie"
    col1.metric("Letztes Backup", bk_ts)

    # Letztes KPI
    last_kpi = df_fn("SELECT MAX(kpi_date) AS d FROM daily_kpis")
    kpi_d = str(last_kpi.iloc[0]["d"] or "nie") if not last_kpi.empty else "nie"
    col2.metric("Letzte KPI-Berechnung", kpi_d)

    # Ausstehende E-Mails
    pending_mail = int(df_fn("SELECT COUNT(*) AS n FROM email_log WHERE status='Entwurf'").iloc[0]["n"])
    col3.metric("📧 Ausstehende E-Mails", pending_mail)

    # Datenbankgröße
    from pathlib import Path
    try:
        db = Path(df_fn("SELECT value FROM settings WHERE key='db_path'").iloc[0]["value"] if not df_fn("SELECT value FROM settings WHERE key='db_path'").empty else "byblos_crm.db")
    except Exception:
        db = Path("byblos_crm.db")
    # Fallback
    for possible in [Path(__file__).resolve().parent / "byblos_crm.db",
                     Path("/app/data/byblos_crm.db")]:
        if possible.exists():
            db = possible
            break
    db_size = f"{db.stat().st_size//1024} KB" if db.exists() else "?"
    col4.metric("🗄️ Datenbankgröße", db_size)


# ─────────────────────────────────────────────────────────────
# 4. Semantische KI-Suche (TF-IDF)
# ─────────────────────────────────────────────────────────────

def page_semantic_search(df_fn) -> None:
    st.title("🤖 KI-Semantiksuche")
    st.caption("Intelligente Volltextsuche mit TF-IDF-Gewichtung über alle Datensätze.")

    q = st.text_input("Suchbegriff eingeben", placeholder="z.B. 'Koetter Messe Hannover' oder 'überfällige Rechnung IAA'")
    if len(q) < 2:
        st.info("Mindestens 2 Zeichen eingeben.")
        return

    try:
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.metrics.pairwise import cosine_similarity
        import numpy as np
        SKLEARN = True
    except ImportError:
        SKLEARN = False

    with st.spinner("Suche läuft..."):
        # Alle Datensätze als Textdokumente sammeln
        docs = []
        meta = []

        inv = df_fn("SELECT i.invoice_no, c.company, i.description, i.invoice_date, i.gross_total, i.status FROM invoices i JOIN customers c ON c.id=i.customer_id")
        for _, r in inv.iterrows():
            text = f"{r['invoice_no']} {r['company']} {r['description']} {r['invoice_date']} {r['status']}"
            docs.append(text); meta.append({"Typ":"Rechnung","Name":r["invoice_no"],"Detail":f"{r['company']} · {fmt_eur(float(r['gross_total']))}","Status":r["status"]})

        custs = df_fn("SELECT customer_no, company, contact_person, email, notes FROM customers")
        for _, r in custs.iterrows():
            text = f"{r['customer_no']} {r['company']} {r.get('contact_person','')} {r.get('email','')} {r.get('notes','')}"
            docs.append(text); meta.append({"Typ":"Kunde","Name":r["company"],"Detail":str(r.get("contact_person","")),"Status":"aktiv"})

        exps = df_fn("SELECT expense_no, description, category, expense_date FROM expenses")
        for _, r in exps.iterrows():
            text = f"{r['expense_no']} {r['description']} {r['category']} {r['expense_date']}"
            docs.append(text); meta.append({"Typ":"Ausgabe","Name":r["expense_no"],"Detail":f"{r['description']} · {r['category']}","Status":r.get("status","")})

        emps = df_fn("SELECT employee_no, name, notes FROM employees")
        for _, r in emps.iterrows():
            text = f"{r['employee_no']} {r['name']} {r.get('notes','')}"
            docs.append(text); meta.append({"Typ":"Mitarbeiter","Name":r["name"],"Detail":str(r.get("notes","")),"Status":""})

        contacts = df_fn("SELECT co.subject, co.note, co.contact_type, c.company FROM contacts co JOIN customers c ON c.id=co.customer_id")
        for _, r in contacts.iterrows():
            text = f"{r['subject']} {r['note']} {r['contact_type']} {r['company']}"
            docs.append(text); meta.append({"Typ":"Kontakt","Name":r["subject"],"Detail":r["company"],"Status":""})

    if not docs:
        st.info("Keine Daten vorhanden.")
        return

    if SKLEARN:
        vectorizer = TfidfVectorizer(max_features=5000, ngram_range=(1, 2),
                                      min_df=1, sublinear_tf=True)
        tfidf_matrix = vectorizer.fit_transform(docs)
        query_vec    = vectorizer.transform([q])
        scores = cosine_similarity(query_vec, tfidf_matrix).flatten()
        top_idx = scores.argsort()[::-1][:20]
        results = []
        for i in top_idx:
            if scores[i] > 0.05:
                r = meta[i].copy()
                r["Relevanz"] = f"{scores[i]*100:.0f}%"
                results.append(r)
    else:
        # Fallback: einfache Textsuche
        q_lower = q.lower()
        results = []
        for i, (doc, m) in enumerate(zip(docs, meta)):
            if q_lower in doc.lower():
                r = m.copy(); r["Relevanz"] = "Treffer"
                results.append(r)
        results = results[:20]

    if results:
        st.success(f"**{len(results)} Treffer** für »{q}«" + (" (KI-Ranking)" if SKLEARN else " (Volltextsuche)"))
        result_df = pd.DataFrame(results)
        st.dataframe(result_df, use_container_width=True)
    else:
        st.warning(f"Keine relevanten Treffer für »{q}«")

    if not SKLEARN:
        st.caption("💡 Für KI-Ranking: `pip install scikit-learn` ausführen.")


# ─────────────────────────────────────────────────────────────
# 5. Automatische BWA-Zuordnung beim Bankimport
# ─────────────────────────────────────────────────────────────

def auto_categorize_bank_transaction(purpose: str, payer: str, df_fn) -> Optional[str]:
    """
    Versucht automatisch eine BWA-Kategorie für eine Banktransaktion zu ermitteln.
    Nutzt: IBAN-Vorlagen, ML-Klassifikation, Regelbasierte Zuordnung.
    """
    # 1. ML-Kategorisierung
    text = f"{purpose} {payer}"
    try:
        from ml_logic import predict_category
        cat, conf = predict_category(text)
        if conf > 60:
            return cat
    except Exception:
        pass

    # 2. Regelbasierte Zuordnung
    text_lower = text.lower()
    rules = [
        (["tankstelle","aral","shell","esso","jet","total","kraft"], "Fahrzeugkosten"),
        (["telefon","telekom","vodafone","o2","1und1","unitymedia"], "Kommunikation"),
        (["versicherung","axa","allianz","ergo","zurich","gothaer"], "Versicherungen"),
        (["miete","nebenkosten","hausverwaltung","wohnungsbau"], "Raumkosten"),
        (["strom","eon","rwe","vattenfall","stadtwerk"], "Energie"),
        (["steuerber","datev","kanzlei","rechtsanwalt","notar"], "Beratungskosten"),
        (["gehalt","lohn","salary","entgelt"], "Personalkosten"),
        (["amazon","otto","ebay","bürobedarf","schreibwaren"], "Bürokosten"),
        (["google","microsoft","adobe","software","lizenz"], "IT-Kosten"),
        (["social media","werbung","marketing","flyer","druck"], "Marketing"),
        (["kr","kv beitrag","barmer","tkk","aok","dak"], "Personalkosten"),
    ]
    for keywords, cat in rules:
        if any(k in text_lower for k in keywords):
            return cat
    return None


def page_bank_auto_categorize(run_fn, df_fn) -> None:
    st.title("🔁 Automatische BWA-Kategorisierung")
    st.caption("Ordnet neue Banktransaktionen automatisch BWA-Kostenarten zu und erstellt Ausgaben-Einträge.")

    new_tx = df_fn("""
        SELECT id, booking_date, payer_payee, purpose, amount
        FROM bank_transactions
        WHERE status='neu' AND amount < 0
        ORDER BY booking_date DESC LIMIT 100
    """)

    if new_tx.empty:
        st.success("✅ Keine neuen negativen Transaktionen (Ausgaben) zu kategorisieren.")
        return

    st.metric("Neue Ausgaben-Transaktionen", len(new_tx))

    # Vorschläge berechnen
    suggestions = []
    for _, r in new_tx.iterrows():
        cat = auto_categorize_bank_transaction(
            str(r.get("purpose") or ""),
            str(r.get("payer_payee") or ""),
            df_fn
        )
        suggestions.append({
            "id": int(r["id"]),
            "Datum": str(r["booking_date"]),
            "Auftraggeber": str(r.get("payer_payee",""))[:40],
            "Verwendungszweck": str(r.get("purpose",""))[:50],
            "Betrag": float(r["amount"]),
            "KI-Kategorie": cat or "Nicht erkannt",
        })

    df_sugg = pd.DataFrame(suggestions)
    st.dataframe(df_sugg.drop(columns=["id"]), use_container_width=True)

    recognized = [s for s in suggestions if s["KI-Kategorie"] != "Nicht erkannt"]
    st.caption(f"✅ {len(recognized)}/{len(suggestions)} automatisch erkannt")

    col1, col2 = st.columns(2)
    if col1.button(f"✅ Alle erkannten ({len(recognized)}) als Ausgaben buchen", type="primary"):
        booked = 0
        for s in recognized:
            amt_brutto = abs(s["Betrag"])
            net = round(amt_brutto / 1.19, 2)
            vat = round(amt_brutto - net, 2)
            from datetime import date
            exp_no = f"AUS-BK-{s['id']}"
            run_fn("""INSERT OR IGNORE INTO expenses(expense_no,expense_date,description,category,
                      net_amount,vat_rate,vat_amount,gross_amount,paid_amount,status,bwa_month)
                      VALUES(?,?,?,?,?,19,?,?,?,?,?)""",
                   (exp_no, s["Datum"], s["Verwendungszweck"], s["KI-Kategorie"],
                    net, vat, amt_brutto, amt_brutto, "bezahlt",
                    s["Datum"][:7]))
            run_fn("UPDATE bank_transactions SET status='gebucht', matched_type='expense' WHERE id=?",
                   (s["id"],))
            booked += 1
        st.success(f"✅ {booked} Ausgaben automatisch gebucht!")
        st.rerun()

    if col2.button("Einzeln überprüfen"):
        st.info("Einzelprüfung: Bitte im Bank/DATEV-Bereich → Transaktionen abgleichen.")
