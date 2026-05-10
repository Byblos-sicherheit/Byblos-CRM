from datetime import date, timedelta
import hashlib
import json
from pathlib import Path
import pandas as pd
import streamlit as st

LIVEOPS_ROLES = ["Inhaber/Admin", "Buchhaltung", "Einsatzleitung", "Vertrieb", "Mitarbeiter", "Kunde/Portal"]
LIVEOPS_AREAS = [
    "Dashboard", "Kunden", "Rechnungen", "Ausgaben", "Bank", "Import", "Verträge",
    "Firmenprofile", "Dienstplan", "Mitarbeiter", "Compliance", "Backup", "Einstellungen"
]
PORTAL_DOC_STATUS = ["Entwurf", "Intern geprüft", "An Kunde gesendet", "Vom Kunden bestätigt", "Unterschrieben", "Abgelehnt", "Archiviert"]
WORKFLOW_STATUS = ["neu", "in arbeit", "wartet auf kunde", "wartet intern", "erledigt", "blockiert"]


def register_liveops(run, df):
    """Create production workflow, role matrix and customer portal preparation tables."""
    run("""
    CREATE TABLE IF NOT EXISTS role_permissions_matrix (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        role_name TEXT NOT NULL,
        area TEXT NOT NULL,
        can_view INTEGER DEFAULT 1,
        can_create INTEGER DEFAULT 0,
        can_edit INTEGER DEFAULT 0,
        can_delete INTEGER DEFAULT 0,
        can_export INTEGER DEFAULT 0,
        notes TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )""")
    run("""
    CREATE TABLE IF NOT EXISTS workflow_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT,
        title TEXT NOT NULL,
        area TEXT,
        related_table TEXT,
        related_id TEXT,
        customer_id INTEGER,
        service_line TEXT,
        priority TEXT DEFAULT 'mittel',
        status TEXT DEFAULT 'neu',
        owner TEXT,
        due_date TEXT,
        notes TEXT
    )""")
    run("""
    CREATE TABLE IF NOT EXISTS customer_portal_links (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        customer_id INTEGER,
        document_id INTEGER,
        token_hash TEXT,
        status TEXT DEFAULT 'vorbereitet',
        expires_at TEXT,
        last_action_at TEXT,
        notes TEXT
    )""")
    run("""
    CREATE TABLE IF NOT EXISTS service_checklists (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        service_line TEXT NOT NULL,
        business_type TEXT DEFAULT 'B2B und B2C',
        checklist_name TEXT NOT NULL,
        checklist_items TEXT,
        active INTEGER DEFAULT 1,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )""")
    run("""
    CREATE TABLE IF NOT EXISTS system_health_checks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        check_name TEXT,
        status TEXT,
        severity TEXT,
        details TEXT
    )""")
    try:
        existing = int(df("SELECT COUNT(*) AS n FROM role_permissions_matrix").iloc[0]["n"])
    except Exception:
        existing = 0
    if existing == 0:
        defaults = []
        for role in LIVEOPS_ROLES:
            for area in LIVEOPS_AREAS:
                if role == "Inhaber/Admin":
                    perms = (1, 1, 1, 1, 1)
                elif role == "Buchhaltung":
                    perms = (1, int(area in ["Rechnungen", "Ausgaben", "Bank", "Import"]), int(area in ["Rechnungen", "Ausgaben", "Bank", "Import"]), 0, int(area in ["Rechnungen", "Ausgaben", "Bank", "Kunden", "Backup"]))
                elif role == "Einsatzleitung":
                    perms = (1, int(area in ["Dienstplan", "Mitarbeiter", "Kunden"]), int(area in ["Dienstplan", "Mitarbeiter", "Kunden"]), 0, 0)
                elif role == "Vertrieb":
                    perms = (1, int(area in ["Kunden", "Verträge"]), int(area in ["Kunden", "Verträge"]), 0, 0)
                elif role == "Mitarbeiter":
                    perms = (int(area in ["Dashboard", "Dienstplan"]), 0, 0, 0, 0)
                else:
                    perms = (int(area in ["Verträge", "Rechnungen"]), 0, 0, 0, 0)
                defaults.append((role, area, *perms, "Startmatrix automatisch erstellt"))
        for row in defaults:
            run("""INSERT INTO role_permissions_matrix(role_name,area,can_view,can_create,can_edit,can_delete,can_export,notes)
                   VALUES(?,?,?,?,?,?,?,?)""", row)
    try:
        checklist_count = int(df("SELECT COUNT(*) AS n FROM service_checklists").iloc[0]["n"])
    except Exception:
        checklist_count = 0
    if checklist_count == 0:
        checklists = {
            "Sicherheitsdienst": ["Objektadresse prüfen", "Einsatzzeiten festlegen", "Ansprechpartner aufnehmen", "Bewachungsziel dokumentieren", "Notfallkontakt hinterlegen", "Personalqualifikation prüfen"],
            "Reinigung": ["Flächen erfassen", "Reinigungsintervall festlegen", "Materialbedarf klären", "Schlüssel/Zutritt dokumentieren", "Abnahmeprozess festlegen"],
            "Hausmeister": ["Objektzustand erfassen", "Regelleistungen definieren", "Sonderaufgaben klären", "Zutritt/Schlüssel prüfen", "Mängelmeldung-Prozess festlegen"],
            "Umzug": ["Startadresse erfassen", "Zieladresse erfassen", "Etagen/Aufzug prüfen", "Volumen schätzen", "Termin bestätigen", "Halteverbotszone prüfen"],
            "Entrümpelung": ["Objektart erfassen", "Menge schätzen", "Entsorgungswege prüfen", "Fotos/Dokumentation aufnehmen", "Termin bestätigen", "Abnahme festlegen"],
        }
        for service, items in checklists.items():
            run("INSERT INTO service_checklists(service_line,business_type,checklist_name,checklist_items) VALUES(?,?,?,?)", (service, "B2B und B2C", f"{service} Standard-Checkliste", json.dumps(items, ensure_ascii=False)))


def _safe_count(df, sql):
    try:
        return int(df(sql).iloc[0][0])
    except Exception:
        return 0


def run_health_scan(run, df):
    """Create a current health snapshot. Keeps previous rows for history."""
    checks = []
    open_imports = _safe_count(df, "SELECT COUNT(*) FROM import_queue WHERE status='neu'")
    checks.append(("Offene Import-Prüfliste", "ok" if open_imports < 20 else "warnung", "mittel" if open_imports < 20 else "hoch", f"{open_imports} offene Importe"))
    draft_docs = _safe_count(df, "SELECT COUNT(*) FROM crm_documents WHERE status='Entwurf'")
    checks.append(("Dokumente im Entwurf", "ok" if draft_docs < 10 else "warnung", "mittel", f"{draft_docs} Entwürfe"))
    unsigned_docs = _safe_count(df, "SELECT COUNT(*) FROM crm_documents WHERE status!='Unterschrieben'")
    checks.append(("Nicht unterschriebene Dokumente", "info", "mittel", f"{unsigned_docs} Dokumente nicht unterschrieben"))
    overdue_tasks = _safe_count(df, "SELECT COUNT(*) FROM workflow_items WHERE status NOT IN ('erledigt') AND due_date IS NOT NULL AND due_date < date('now')")
    checks.append(("Überfällige Workflows", "ok" if overdue_tasks == 0 else "warnung", "hoch" if overdue_tasks else "niedrig", f"{overdue_tasks} überfällig"))
    missing_customer_contact = _safe_count(df, "SELECT COUNT(*) FROM customers WHERE COALESCE(email,'')='' AND COALESCE(phone,'')=''")
    checks.append(("Kunden ohne Kontakt", "ok" if missing_customer_contact == 0 else "warnung", "mittel", f"{missing_customer_contact} Kunden ohne E-Mail und Telefon"))
    for check in checks:
        run("INSERT INTO system_health_checks(check_name,status,severity,details) VALUES(?,?,?,?)", check)
    return checks


def page_liveops_cockpit(run, df):
    st.title("Live-Betrieb Cockpit")
    st.caption("Tägliche Steuerung: offene Workflows, überfällige Punkte, Systemzustand und nächste Aktionen.")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Workflows offen", _safe_count(df, "SELECT COUNT(*) FROM workflow_items WHERE status NOT IN ('erledigt')"))
    c2.metric("Überfällig", _safe_count(df, "SELECT COUNT(*) FROM workflow_items WHERE status NOT IN ('erledigt') AND due_date IS NOT NULL AND due_date < date('now')"))
    c3.metric("Portal Links", _safe_count(df, "SELECT COUNT(*) FROM customer_portal_links"))
    c4.metric("Health Checks", _safe_count(df, "SELECT COUNT(*) FROM system_health_checks"))
    if st.button("Systemzustand prüfen"):
        checks = run_health_scan(run, df)
        st.success(f"{len(checks)} Prüfungen gespeichert.")
        st.rerun()
    st.subheader("Neue Aufgabe / Workflow")
    with st.form("workflow_new"):
        a, b = st.columns(2)
        title = a.text_input("Titel")
        area = b.selectbox("Bereich", LIVEOPS_AREAS)
        service = a.selectbox("Leistung", ["", "Sicherheitsdienst", "Reinigung", "Hausmeister", "Umzug", "Entrümpelung"])
        priority = b.selectbox("Priorität", ["hoch", "mittel", "niedrig"], index=1)
        owner = a.text_input("Verantwortlich")
        due = b.text_input("Frist", placeholder="YYYY-MM-DD")
        notes = st.text_area("Notizen")
        if st.form_submit_button("Workflow speichern") and title.strip():
            run("""INSERT INTO workflow_items(title,area,service_line,priority,status,owner,due_date,notes)
                   VALUES(?,?,?,?,?,?,?,?)""", (title, area, service, priority, "neu", owner, due, notes))
            st.success("Workflow gespeichert.")
            st.rerun()
    st.subheader("Offene Workflows")
    data = df("SELECT id, title, area, service_line, priority, status, owner, due_date, created_at FROM workflow_items WHERE status NOT IN ('erledigt') ORDER BY CASE priority WHEN 'hoch' THEN 1 WHEN 'mittel' THEN 2 ELSE 3 END, due_date, id DESC")
    st.dataframe(data, use_container_width=True)
    wid = st.number_input("Workflow-ID bearbeiten", min_value=0, step=1)
    if wid:
        row = df("SELECT * FROM workflow_items WHERE id=?", (int(wid),))
        if not row.empty:
            status = st.selectbox("Status setzen", WORKFLOW_STATUS)
            note = st.text_area("Neue Notiz / Ergänzung")
            c1, c2 = st.columns(2)
            if c1.button("Status speichern"):
                old_notes = row.iloc[0].get("notes") or ""
                merged_notes = old_notes + ("\n" + note if note else "")
                run("UPDATE workflow_items SET status=?, notes=?, updated_at=CURRENT_TIMESTAMP WHERE id=?", (status, merged_notes, int(wid)))
                st.success("Aktualisiert.")
                st.rerun()
            if c2.button("Workflow löschen"):
                run("DELETE FROM workflow_items WHERE id=?", (int(wid),))
                st.warning("Gelöscht.")
                st.rerun()
    st.subheader("Letzte Systemprüfungen")
    st.dataframe(df("SELECT created_at, check_name, status, severity, details FROM system_health_checks ORDER BY id DESC LIMIT 50"), use_container_width=True)


def page_role_permissions_matrix(run, df):
    st.title("Rollen & Rechte Matrix")
    st.caption("Startpunkt für Rechtekonzept. Produktiv vor Livegang mit echten Rollen prüfen.")
    data = df("SELECT * FROM role_permissions_matrix ORDER BY role_name, area")
    st.dataframe(data, use_container_width=True)
    st.subheader("Recht anpassen")
    rid = st.number_input("Matrix-ID", min_value=0, step=1)
    if rid:
        row = df("SELECT * FROM role_permissions_matrix WHERE id=?", (int(rid),))
        if not row.empty:
            r = row.iloc[0]
            c1, c2, c3, c4, c5 = st.columns(5)
            view = c1.checkbox("View", value=bool(r["can_view"]))
            create = c2.checkbox("Create", value=bool(r["can_create"]))
            edit = c3.checkbox("Edit", value=bool(r["can_edit"]))
            delete = c4.checkbox("Delete", value=bool(r["can_delete"]))
            export = c5.checkbox("Export", value=bool(r["can_export"]))
            notes = st.text_area("Notiz", r["notes"] or "")
            if st.button("Recht speichern"):
                run("""UPDATE role_permissions_matrix SET can_view=?,can_create=?,can_edit=?,can_delete=?,can_export=?,notes=? WHERE id=?""", (int(view), int(create), int(edit), int(delete), int(export), notes, int(rid)))
                st.success("Gespeichert.")
                st.rerun()


def page_customer_portal_prep(run, df):
    st.title("Kundenportal Vorbereitung")
    st.caption("Noch kein echtes Online-Portal, aber sichere Vorbereitung: Dokumente auswählen, Token vorbereiten, Status verfolgen.")
    customers = df("SELECT id, company FROM customers ORDER BY company")
    docs = df("SELECT id, title, status FROM crm_documents ORDER BY id DESC")
    if customers.empty or docs.empty:
        st.info("Für Portal-Links brauchst du mindestens einen Kunden und ein Dokument.")
    else:
        with st.form("portal_link_form"):
            customer = st.selectbox("Kunde", customers["company"].tolist())
            doc_label = st.selectbox("Dokument", [f"{r['id']} - {r['title']} - {r['status']}" for _, r in docs.iterrows()])
            days = st.number_input("Gültigkeit in Tagen", min_value=1, max_value=90, value=14)
            notes = st.text_area("Notizen")
            if st.form_submit_button("Portal-Link vorbereiten"):
                cid = int(customers[customers["company"] == customer].iloc[0]["id"])
                did = int(doc_label.split(" - ")[0])
                raw_token = f"{cid}:{did}:{date.today().isoformat()}:{hashlib.sha256(str(cid).encode()).hexdigest()[:12]}"
                token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
                expires = (date.today() + timedelta(days=int(days))).isoformat()
                run("""INSERT INTO customer_portal_links(customer_id,document_id,token_hash,status,expires_at,notes)
                       VALUES(?,?,?,?,?,?)""", (cid, did, token_hash, "vorbereitet", expires, notes))
                st.success("Portal-Link vorbereitet. Kein echter Versand, nur sicherer Vorbereitungseintrag.")
                st.code(f"Token-Hash: {token_hash}")
    data = df("""SELECT p.id, c.company AS Kunde, d.title AS Dokument, p.status, p.expires_at, p.created_at, p.last_action_at, substr(p.token_hash,1,16) AS TokenKurz
                 FROM customer_portal_links p
                 LEFT JOIN customers c ON c.id=p.customer_id
                 LEFT JOIN crm_documents d ON d.id=p.document_id
                 ORDER BY p.id DESC""")
    st.dataframe(data, use_container_width=True)
    pid = st.number_input("Portal-ID Status ändern", min_value=0, step=1)
    if pid:
        status = st.selectbox("Neuer Status", ["vorbereitet", "gesendet", "vom kunden geöffnet", "bestätigt", "abgelaufen", "widerrufen"])
        if st.button("Portalstatus speichern"):
            run("UPDATE customer_portal_links SET status=?, last_action_at=CURRENT_TIMESTAMP WHERE id=?", (status, int(pid)))
            st.success("Status gespeichert.")
            st.rerun()


def page_service_checklists(run, df):
    st.title("Leistungs-Checklisten")
    st.caption("Standardisierte Abwicklung je Leistung: Sicherheitsdienst, Reinigung, Hausmeister, Umzug, Entrümpelung.")
    data = df("SELECT * FROM service_checklists ORDER BY service_line, id")
    st.dataframe(data, use_container_width=True)
    with st.form("checklist_form"):
        service = st.selectbox("Leistung", ["Sicherheitsdienst", "Reinigung", "Hausmeister", "Umzug", "Entrümpelung"])
        btype = st.selectbox("Zielgruppe", ["B2B", "B2C", "B2B und B2C"], index=2)
        name = st.text_input("Checklistenname")
        items = st.text_area("Punkte, eine Zeile je Punkt")
        if st.form_submit_button("Checkliste speichern") and name.strip():
            item_list = [x.strip() for x in items.splitlines() if x.strip()]
            run("INSERT INTO service_checklists(service_line,business_type,checklist_name,checklist_items) VALUES(?,?,?,?)", (service, btype, name, json.dumps(item_list, ensure_ascii=False)))
            st.success("Checkliste gespeichert.")
            st.rerun()
    cid = st.number_input("Checkliste löschen ID", min_value=0, step=1)
    if cid and st.button("Checkliste löschen"):
        run("DELETE FROM service_checklists WHERE id=?", (int(cid),))
        st.warning("Gelöscht.")
        st.rerun()
