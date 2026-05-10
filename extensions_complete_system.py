from pathlib import Path
import json
import pandas as pd
import streamlit as st

SERVICES_BYBLOS = ["Sicherheitsdienst", "Reinigung", "Hausmeister", "Umzug", "Entrümpelung"]
BUSINESS_TYPES_BYBLOS = ["B2B", "B2C", "B2B und B2C"]
DOC_TYPES_BYBLOS = ["Vertrag", "Angebot", "Datenschutzerklärung", "AGB", "AVV", "Leistungsbeschreibung", "Abnahmeprotokoll", "Einverständnis"]


def register_complete_system(run, df):
    run("""
    CREATE TABLE IF NOT EXISTS company_profiles (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        brand_name TEXT,
        service_line TEXT,
        business_type TEXT DEFAULT 'B2B und B2C',
        email TEXT,
        phone TEXT,
        website TEXT,
        address TEXT,
        tax_no TEXT,
        iban TEXT,
        logo_path TEXT,
        active INTEGER DEFAULT 1,
        notes TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )""")
    run("""
    CREATE TABLE IF NOT EXISTS crm_documents (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        doc_type TEXT NOT NULL,
        title TEXT NOT NULL,
        customer_id INTEGER,
        company_profile_id INTEGER,
        service_line TEXT,
        business_type TEXT,
        content TEXT,
        status TEXT DEFAULT 'Entwurf',
        signed_by TEXT,
        signed_at TEXT,
        signature_text TEXT,
        pdf_path TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT
    )""")
    run("""
    CREATE TABLE IF NOT EXISTS crm_search_index (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        source_table TEXT,
        source_id INTEGER,
        title TEXT,
        body TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )""")
    run("""
    CREATE TABLE IF NOT EXISTS ai_questions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        question TEXT NOT NULL,
        answer TEXT,
        source_hint TEXT
    )""")
    if df("SELECT COUNT(*) AS n FROM company_profiles").iloc[0]["n"] == 0:
        defaults = [
            ("Byblos Sicherheitsdienst", "byblos-sicherheit.de", "Sicherheitsdienst"),
            ("Byblos Reinigung", "byblos-reinigung.de", "Reinigung"),
            ("Byblos Hausmeisterservice", "byblos-hausmeisterservice.de", "Hausmeister"),
            ("Byblos Umzug", "Byblos Umzug", "Umzug"),
            ("Byblos Entrümpelung", "byblos-entruempelung.de", "Entrümpelung"),
        ]
        for name, brand, service in defaults:
            run("INSERT INTO company_profiles(name,brand_name,service_line,business_type,notes) VALUES(?,?,?,?,?)", (name, brand, service, "B2B und B2C", "automatisch angelegt"))


def build_document_template(doc_type, service_line, business_type, customer_name="", company_name="Byblos"):
    service = service_line or "Dienstleistung"
    btype = business_type or "B2B und B2C"
    customer = customer_name or "[Kunde]"
    templates = {
        "Vertrag": f"""DIENSTLEISTUNGSVERTRAG

Zwischen {company_name} und {customer} wird folgender Vertrag geschlossen.

Leistung: {service}
Zielgruppe: {btype}

1. Leistungsumfang
Der Auftragnehmer erbringt die vereinbarten Leistungen fachgerecht, zuverlässig und nach schriftlicher Beauftragung.

2. Einsatzort und Zeiten
Einsatzort, Termine, Personalstärke und Sonderwünsche werden im Auftrag oder Angebot festgelegt.

3. Vergütung
Die Vergütung ergibt sich aus Angebot, Rechnung oder separater Preisvereinbarung.

4. Pflichten des Auftraggebers
Der Auftraggeber stellt notwendige Informationen, Zugangsmöglichkeiten und Ansprechpartner bereit.

5. Datenschutz und Vertraulichkeit
Personenbezogene Daten werden nur zweckgebunden verarbeitet. Vertrauliche Informationen sind geheim zu halten.

6. Unterschrift
Mit der Bestätigung akzeptieren beide Parteien diesen Vertrag.""",
        "Datenschutzerklärung": f"""DATENSCHUTZERKLÄRUNG

Diese Erklärung beschreibt die Verarbeitung personenbezogener Daten im Zusammenhang mit {service}.

Verantwortlicher: {company_name}
Zweck: Angebot, Vertragserfüllung, Einsatzplanung, Rechnungsstellung und Kundenkommunikation.
Rechtsgrundlage: Vertrag, vorvertragliche Maßnahmen, berechtigtes Interesse oder Einwilligung.
Speicherdauer: Daten werden nur so lange gespeichert, wie es für Zweck, Nachweis oder gesetzliche Pflichten erforderlich ist.
Betroffenenrechte: Auskunft, Berichtigung, Löschung, Einschränkung, Widerspruch und Datenübertragbarkeit nach DSGVO.

Hinweis: Diese Vorlage muss vor produktiver Nutzung rechtlich geprüft werden.""",
        "AGB": f"""ALLGEMEINE GESCHÄFTSBEDINGUNGEN

1. Geltungsbereich
Diese Bedingungen gelten für Leistungen im Bereich {service} für {btype}.

2. Angebot und Vertragsschluss
Angebote sind freibleibend, sofern nicht schriftlich anders vereinbart.

3. Leistungsänderungen
Änderungen müssen schriftlich bestätigt werden.

4. Zahlung
Rechnungen sind innerhalb der vereinbarten Zahlungsfrist zu begleichen.

5. Haftung
Haftung richtet sich nach gesetzlichen Vorgaben und vereinbarten Leistungsgrenzen.

6. Schlussbestimmungen
Sollten einzelne Klauseln unwirksam sein, bleibt der Rest wirksam.

Hinweis: Diese AGB-Vorlage ersetzt keine anwaltliche Prüfung.""",
        "AVV": f"""AUFTRAGSVERARBEITUNGSVERTRAG (AVV)

Zwischen {company_name} und {customer} wird eine AVV-Vorlage für {service} vorbereitet.

1. Gegenstand und Dauer
Die Verarbeitung erfolgt nur im Rahmen der vereinbarten Leistung.

2. Art und Zweck
Zweck ist die Durchführung, Dokumentation und Abrechnung der Leistung.

3. Kategorien personenbezogener Daten
Kontakt-, Vertrags-, Einsatz-, Rechnungs- und Kommunikationsdaten.

4. Technische und organisatorische Maßnahmen
Zugriffsschutz, Rollenrechte, Backups, Protokollierung und Vertraulichkeit.

5. Weisungen
Daten werden nur nach dokumentierter Weisung verarbeitet.

Hinweis: Diese AVV muss juristisch final geprüft werden.""",
    }
    return templates.get(doc_type, f"""{doc_type.upper()}

Leistung: {service}
Zielgruppe: {btype}
Kunde: {customer}
Firma: {company_name}

Inhalt bitte prüfen, anpassen und freigeben.

Unterschrift / Bestätigung: __________________________""")


def rebuild_search_index(run, df):
    run("DELETE FROM crm_search_index")
    sources = [
        ("customers", "id", "company", "COALESCE(customer_no,'') || ' ' || COALESCE(contact_person,'') || ' ' || COALESCE(email,'') || ' ' || COALESCE(phone,'') || ' ' || COALESCE(notes,'')"),
        ("invoices", "id", "invoice_no", "COALESCE(description,'') || ' ' || COALESCE(status,'') || ' ' || COALESCE(gross_total,0)"),
        ("expenses", "id", "expense_no", "COALESCE(description,'') || ' ' || COALESCE(category,'') || ' ' || COALESCE(gross_amount,0)"),
        ("crm_documents", "id", "title", "COALESCE(doc_type,'') || ' ' || COALESCE(service_line,'') || ' ' || COALESCE(content,'') || ' ' || COALESCE(status,'')"),
        ("company_profiles", "id", "name", "COALESCE(service_line,'') || ' ' || COALESCE(brand_name,'') || ' ' || COALESCE(email,'') || ' ' || COALESCE(notes,'')"),
    ]
    for table, idcol, titlecol, bodyexpr in sources:
        try:
            rows = df(f"SELECT {idcol} AS id, {titlecol} AS title, {bodyexpr} AS body FROM {table}")
            for _, r in rows.iterrows():
                run("INSERT INTO crm_search_index(source_table,source_id,title,body) VALUES(?,?,?,?)", (table, int(r["id"]), str(r["title"]), str(r["body"])))
        except Exception:
            pass


def ai_answer_local(question, df):
    q = question.lower()
    hints = []
    if any(x in q for x in ["rechnung", "offen", "bezahlt", "umsatz"]):
        open_sum = float(df("SELECT COALESCE(SUM(gross_total-paid_amount),0) AS v FROM invoices WHERE status IN ('offen','ueberfaellig')").iloc[0]["v"])
        cnt = int(df("SELECT COUNT(*) AS n FROM invoices WHERE status IN ('offen','ueberfaellig')").iloc[0]["n"])
        hints.append(f"Offene Rechnungen: {cnt}, Summe: {open_sum:.2f} EUR.")
    if any(x in q for x in ["kunde", "kunden"]):
        cnt = int(df("SELECT COUNT(*) AS n FROM customers").iloc[0]["n"])
        hints.append(f"Kunden im CRM: {cnt}.")
    if any(x in q for x in ["vertrag", "agb", "datenschutz", "avv"]):
        cnt = int(df("SELECT COUNT(*) AS n FROM crm_documents").iloc[0]["n"])
        signed = int(df("SELECT COUNT(*) AS n FROM crm_documents WHERE status='Unterschrieben'").iloc[0]["n"])
        hints.append(f"Dokumente/Verträge: {cnt}, unterschrieben/bestätigt: {signed}.")
    if any(x in q for x in ["sicherheitsdienst", "reinigung", "hausmeister", "umzug", "entrümpelung", "entruempelung"]):
        hints.append("Die Leistungen sind im System als Sicherheitsdienst, Reinigung, Hausmeister, Umzug und Entrümpelung hinterlegt. Sie können B2B und B2C genutzt werden.")
    if not hints:
        hints.append("Ich kann lokal ohne externe API CRM-Daten auswerten. Stelle Fragen zu Kunden, Rechnungen, Ausgaben, Verträgen, Datenschutz, AGB, AVV oder Suche.")
    return "\n".join(hints)


def page_quick_search_ai(run, df):
    st.title("Schnellsuche & KI-Fragen")
    st.caption("Kunden, Rechnungen, Ausgaben, Dokumente und Firmenprofile schnell finden. KI-Fragen laufen lokal regelbasiert ohne externe API.")
    if st.button("Suchindex neu aufbauen"):
        rebuild_search_index(run, df)
        st.success("Suchindex aktualisiert.")
    query = st.text_input("Suchen", placeholder="Kunde, Rechnung, Vertrag, AGB, Sicherheitsdienst ...")
    if query:
        like = f"%{query}%"
        results = df("SELECT source_table AS Bereich, source_id AS ID, title AS Titel, substr(body,1,240) AS Treffer FROM crm_search_index WHERE title LIKE ? OR body LIKE ? ORDER BY created_at DESC LIMIT 100", (like, like))
        if results.empty:
            rebuild_search_index(run, df)
            results = df("SELECT source_table AS Bereich, source_id AS ID, title AS Titel, substr(body,1,240) AS Treffer FROM crm_search_index WHERE title LIKE ? OR body LIKE ? ORDER BY created_at DESC LIMIT 100", (like, like))
        st.dataframe(results, use_container_width=True)
    st.divider()
    st.subheader("KI Chat Board")
    question = st.text_area("Frage an das CRM", placeholder="Welche offenen Rechnungen gibt es? Wie viele Verträge sind unterschrieben? Was finde ich zu Reinigung?")
    if st.button("Antwort generieren") and question.strip():
        answer = ai_answer_local(question, df)
        run("INSERT INTO ai_questions(question,answer,source_hint) VALUES(?,?,?)", (question, answer, "lokale CRM-Regeln"))
        st.success(answer)
    st.dataframe(df("SELECT created_at, question AS Frage, answer AS Antwort FROM ai_questions ORDER BY id DESC LIMIT 50"), use_container_width=True)


def page_company_profiles(run, df, ASSET_DIR, COMPANY):
    st.title("Firmenprofile & Logos")
    st.caption("Mehrere Firmen/Marken verwalten: Sicherheitsdienst, Reinigung, Hausmeister, Umzug, Entrümpelung. Je Profil können Daten und Logo angepasst werden.")
    with st.form("company_profile_form"):
        c1, c2 = st.columns(2)
        name = c1.text_input("Firmenname", "Byblos Sicherheitsdienst & Service")
        brand = c2.text_input("Marke / Domain", "byblos-sicherheit.de")
        service = c1.selectbox("Leistung", SERVICES_BYBLOS)
        btype = c2.selectbox("Zielgruppe", BUSINESS_TYPES_BYBLOS, index=2)
        email = c1.text_input("E-Mail", COMPANY.get("email", ""))
        phone = c2.text_input("Telefon", COMPANY.get("phone", ""))
        website = c1.text_input("Website", COMPANY.get("website", ""))
        tax_no = c2.text_input("USt/Steuer", COMPANY.get("ust", ""))
        address = st.text_area("Adresse", f"{COMPANY.get('street','')}\n{COMPANY.get('city','')}\n{COMPANY.get('country','')}")
        iban = st.text_input("IBAN", COMPANY.get("iban", ""))
        notes = st.text_area("Notizen")
        if st.form_submit_button("Firmenprofil speichern"):
            run("""INSERT INTO company_profiles(name,brand_name,service_line,business_type,email,phone,website,address,tax_no,iban,notes)
                   VALUES(?,?,?,?,?,?,?,?,?,?,?)""", (name, brand, service, btype, email, phone, website, address, tax_no, iban, notes))
            st.success("Firmenprofil gespeichert.")
            st.rerun()
    st.subheader("Logo hochladen")
    profiles = df("SELECT id, name || ' - ' || service_line AS label FROM company_profiles ORDER BY id DESC")
    if not profiles.empty:
        selected = st.selectbox("Profil", profiles["label"].tolist())
        pid = int(profiles[profiles["label"] == selected].iloc[0]["id"])
        logo = st.file_uploader("Logo PNG/JPG", type=["png", "jpg", "jpeg"], key="profile_logo")
        if logo and st.button("Logo diesem Profil zuordnen"):
            ext = Path(logo.name).suffix.lower() or ".png"
            path = ASSET_DIR / f"company_profile_{pid}{ext}"
            path.write_bytes(logo.read())
            run("UPDATE company_profiles SET logo_path=? WHERE id=?", (str(path), pid))
            st.success("Logo gespeichert.")
    st.subheader("Gespeicherte Firmenprofile")
    data = df("SELECT * FROM company_profiles ORDER BY id DESC")
    st.dataframe(data, use_container_width=True)
    if not data.empty:
        delete_id = st.number_input("Firmenprofil-ID löschen", min_value=0, step=1)
        if st.button("Firmenprofil löschen") and delete_id:
            run("DELETE FROM company_profiles WHERE id=?", (int(delete_id),))
            st.warning("Gelöscht.")
            st.rerun()


def page_contracts_documents(run, df):
    st.title("Verträge, AGB, Datenschutz, AVV & Unterschrift")
    st.caption("Dokumente je Leistung und Zielgruppe erstellen, korrigieren, löschen und als bestätigt/unterschrieben speichern.")
    custs = df("SELECT id, company FROM customers ORDER BY company")
    profiles = df("SELECT id, name, service_line, business_type FROM company_profiles ORDER BY id DESC")
    with st.form("doc_create_form"):
        c1, c2 = st.columns(2)
        doc_type = c1.selectbox("Dokumenttyp", DOC_TYPES_BYBLOS)
        service = c2.selectbox("Leistung", SERVICES_BYBLOS)
        btype = c1.selectbox("Zielgruppe", BUSINESS_TYPES_BYBLOS, index=2)
        customer_label = c2.selectbox("Kunde", ["[ohne Kunde]"] + (custs["company"].tolist() if not custs.empty else []))
        profile_label = c1.selectbox("Firmenprofil", ["Standard Byblos"] + ([f"{r['id']} - {r['name']} - {r['service_line']}" for _, r in profiles.iterrows()] if not profiles.empty else []))
        company_name = "Byblos"
        profile_id = None
        if profile_label != "Standard Byblos":
            profile_id = int(profile_label.split(" - ")[0])
            company_name = str(profiles[profiles["id"] == profile_id].iloc[0]["name"])
        customer_id = None if customer_label == "[ohne Kunde]" else int(custs[custs["company"] == customer_label].iloc[0]["id"])
        title = st.text_input("Titel", f"{doc_type} - {service} - {btype}")
        content = st.text_area("Inhalt", build_document_template(doc_type, service, btype, customer_label if customer_label != "[ohne Kunde]" else "", company_name), height=360)
        if st.form_submit_button("Dokument speichern"):
            run("""INSERT INTO crm_documents(doc_type,title,customer_id,company_profile_id,service_line,business_type,content,status)
                   VALUES(?,?,?,?,?,?,?,?)""", (doc_type, title, customer_id, profile_id, service, btype, content, "Entwurf"))
            st.success("Dokument gespeichert.")
            st.rerun()
    st.divider()
    docs = df("SELECT id, doc_type, title, service_line, business_type, status, signed_by, signed_at, created_at FROM crm_documents ORDER BY id DESC")
    st.dataframe(docs, use_container_width=True)
    if not docs.empty:
        doc_id = st.number_input("Dokument-ID bearbeiten", min_value=0, step=1)
        if doc_id:
            row = df("SELECT * FROM crm_documents WHERE id=?", (int(doc_id),))
            if not row.empty:
                r = row.iloc[0]
                new_title = st.text_input("Titel bearbeiten", r["title"])
                new_content = st.text_area("Inhalt korrigieren", r["content"] or "", height=300)
                signer = st.text_input("Unterschrift / Name", r["signed_by"] or "")
                sig_text = st.text_area("Bestätigungstext", r["signature_text"] or "Ich bestätige den Inhalt dieses Dokuments.")
                c1, c2, c3 = st.columns(3)
                if c1.button("Korrektur speichern"):
                    run("UPDATE crm_documents SET title=?, content=?, updated_at=CURRENT_TIMESTAMP WHERE id=?", (new_title, new_content, int(doc_id)))
                    st.success("Gespeichert.")
                    st.rerun()
                if c2.button("Als unterschrieben speichern"):
                    run("UPDATE crm_documents SET status='Unterschrieben', signed_by=?, signature_text=?, signed_at=CURRENT_TIMESTAMP, updated_at=CURRENT_TIMESTAMP WHERE id=?", (signer, sig_text, int(doc_id)))
                    st.success("Unterschrieben/Bestätigt gespeichert.")
                    st.rerun()
                if c3.button("Dokument löschen"):
                    run("DELETE FROM crm_documents WHERE id=?", (int(doc_id),))
                    st.warning("Gelöscht.")
                    st.rerun()


def page_bulk_invoice_import(run, df, queue_dataframe_import, process_import_queue_item, extract_pdf_text, extract_image_text, enqueue_import):
    st.title("Mehrere Rechnungen importieren & korrigieren")
    st.caption("Mehrere PDF/Bild/CSV/Excel-Rechnungen gleichzeitig hochladen. Das CRM scannt Daten, legt sie in die Prüfliste und erlaubt Korrektur oder Löschen.")
    files = st.file_uploader("Mehrere Rechnungen/Belege auswählen", type=["pdf", "png", "jpg", "jpeg", "csv", "xlsx", "xls"], accept_multiple_files=True)
    force_type = st.selectbox("Import-Typ", ["automatisch", "rechnungen", "ausgaben", "kunden", "bank"])
    if files and st.button("Alle Dateien scannen und importieren"):
        total = 0
        skipped = 0
        for f in files:
            name = f.name.lower()
            try:
                if name.endswith(".csv"):
                    data = pd.read_csv(f, sep=None, engine="python")
                elif name.endswith((".xlsx", ".xls")):
                    data = pd.read_excel(f)
                else:
                    raw = extract_pdf_text(f) if name.endswith(".pdf") else extract_image_text(f)
                    data = pd.DataFrame([{"quelle": f.name, "erkannter_text": raw, "betrag": "", "rechnungsnummer": ""}])
                _, q, s = queue_dataframe_import(data, f.name, None if force_type == "automatisch" else force_type)
                total += q
                skipped += s
            except Exception as e:
                enqueue_import("rechnungen", f.name, {"fehler": str(e)}, "", None, 0, "pruefen", f"Fehler beim Scan: {e}")
        st.success(f"Import abgeschlossen: {total} neu, {skipped} Dubletten/übersprungen.")
        st.rerun()
    st.subheader("Prüfliste / Korrektur")
    q = df("SELECT id, import_type, source_file, confidence, status, reason, raw_data, created_at FROM import_queue ORDER BY id DESC LIMIT 300")
    st.dataframe(q.drop(columns=["raw_data"]) if not q.empty else q, use_container_width=True)
    if not q.empty:
        qid = st.number_input("Import-ID korrigieren/löschen", min_value=0, step=1)
        if qid:
            row = df("SELECT * FROM import_queue WHERE id=?", (int(qid),))
            if not row.empty:
                raw = json.loads(row.iloc[0]["raw_data"])
                edited = st.text_area("Rohdaten JSON korrigieren", json.dumps(raw, ensure_ascii=False, indent=2), height=260)
                c1, c2, c3 = st.columns(3)
                if c1.button("Korrektur speichern"):
                    json.loads(edited)
                    run("UPDATE import_queue SET raw_data=?, status='neu', reason='manuell korrigiert' WHERE id=?", (edited, int(qid)))
                    st.success("Korrektur gespeichert.")
                    st.rerun()
                if c2.button("Jetzt speichern/verarbeiten"):
                    st.success(process_import_queue_item(int(qid), force=True, learn=True))
                    st.rerun()
                if c3.button("Import löschen"):
                    run("DELETE FROM import_queue WHERE id=?", (int(qid),))
                    st.warning("Import gelöscht.")
                    st.rerun()

# -----------------------------------------------------------------------------
# SYSTEMPLUS: Betriebssicherheit, Audit, Compliance, Export, Rollen-Check
# -----------------------------------------------------------------------------

def register_systemplus(run, df):
    """Create additional production-readiness tables for audit, compliance and exports."""
    run("""
    CREATE TABLE IF NOT EXISTS audit_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        actor TEXT,
        area TEXT,
        action TEXT,
        object_type TEXT,
        object_id TEXT,
        details TEXT,
        risk_level TEXT DEFAULT 'normal'
    )""")
    run("""
    CREATE TABLE IF NOT EXISTS compliance_checks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        check_name TEXT NOT NULL,
        area TEXT,
        status TEXT DEFAULT 'offen',
        priority TEXT DEFAULT 'mittel',
        owner TEXT,
        due_date TEXT,
        notes TEXT
    )""")
    run("""
    CREATE TABLE IF NOT EXISTS export_jobs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        export_type TEXT NOT NULL,
        status TEXT DEFAULT 'geplant',
        file_path TEXT,
        checksum TEXT,
        notes TEXT
    )""")
    run("""
    CREATE TABLE IF NOT EXISTS data_quality_issues (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        source_table TEXT,
        source_id TEXT,
        issue_type TEXT,
        severity TEXT DEFAULT 'mittel',
        description TEXT,
        status TEXT DEFAULT 'offen'
    )""")
    # Seed core compliance checks once.
    try:
        count = int(df("SELECT COUNT(*) AS n FROM compliance_checks").iloc[0]["n"])
    except Exception:
        count = 0
    if count == 0:
        checks = [
            ("DSGVO Datenschutzerklärung juristisch prüfen", "Recht", "offen", "hoch"),
            ("AGB je Leistung prüfen", "Recht", "offen", "hoch"),
            ("AVV Vorlage prüfen", "Recht", "offen", "hoch"),
            ("Backup-Wiederherstellung testen", "Betrieb", "offen", "hoch"),
            ("Rollen/Rechte für Mitarbeiter prüfen", "Sicherheit", "offen", "mittel"),
            ("Echte Rechnungserkennung mit Beispieldaten testen", "Import", "offen", "hoch"),
            ("Signatur-/Unterschriftenprozess intern freigeben", "Verträge", "offen", "mittel"),
        ]
        for c in checks:
            run("INSERT INTO compliance_checks(check_name,area,status,priority) VALUES(?,?,?,?)", c)


def audit_log_event(run, actor, area, action, object_type='', object_id='', details='', risk_level='normal'):
    try:
        run("""INSERT INTO audit_events(actor,area,action,object_type,object_id,details,risk_level)
               VALUES(?,?,?,?,?,?,?)""", (actor, area, action, object_type, str(object_id), details, risk_level))
    except Exception:
        pass


def scan_data_quality(run, df):
    """Run simple local data-quality checks and store open issues."""
    run("DELETE FROM data_quality_issues WHERE status='offen'")
    checks = []
    try:
        customers = df("SELECT id, company, email, phone FROM customers")
        for _, r in customers.iterrows():
            if not str(r.get('company') or '').strip():
                checks.append(('customers', r['id'], 'Pflichtfeld', 'hoch', 'Kunde ohne Firmen-/Namenfeld'))
            if not str(r.get('email') or '').strip() and not str(r.get('phone') or '').strip():
                checks.append(('customers', r['id'], 'Kontakt', 'mittel', 'Kunde ohne E-Mail und Telefon'))
    except Exception:
        pass
    try:
        invoices = df("SELECT id, invoice_no, gross_total, status FROM invoices")
        for _, r in invoices.iterrows():
            if not str(r.get('invoice_no') or '').strip():
                checks.append(('invoices', r['id'], 'Rechnung', 'hoch', 'Rechnung ohne Rechnungsnummer'))
            if float(r.get('gross_total') or 0) <= 0:
                checks.append(('invoices', r['id'], 'Betrag', 'hoch', 'Rechnung mit Betrag 0 oder negativ'))
    except Exception:
        pass
    try:
        docs = df("SELECT id, title, doc_type, status FROM crm_documents")
        for _, r in docs.iterrows():
            if str(r.get('status') or '') == 'Entwurf':
                checks.append(('crm_documents', r['id'], 'Dokumentstatus', 'mittel', 'Dokument ist noch Entwurf'))
    except Exception:
        pass
    for table, sid, issue, sev, desc in checks:
        run("""INSERT INTO data_quality_issues(source_table,source_id,issue_type,severity,description,status)
               VALUES(?,?,?,?,?,'offen')""", (table, str(sid), issue, sev, desc))
    return len(checks)


def page_systemplus_cockpit(run, df):
    st.title("SystemPlus Cockpit")
    st.caption("Betriebssicherheit: offene Prüfungen, Datenqualität, Audit-Log und schnelle Steuerung.")
    c1, c2, c3, c4 = st.columns(4)
    def safe_int(sql):
        try:
            return int(df(sql).iloc[0][0])
        except Exception:
            return 0
    c1.metric("Offene Importe", safe_int("SELECT COUNT(*) FROM import_queue WHERE status='neu'"))
    c2.metric("Offene Compliance", safe_int("SELECT COUNT(*) FROM compliance_checks WHERE status!='erledigt'"))
    c3.metric("Datenfehler offen", safe_int("SELECT COUNT(*) FROM data_quality_issues WHERE status='offen'"))
    c4.metric("Dokumente Entwurf", safe_int("SELECT COUNT(*) FROM crm_documents WHERE status='Entwurf'"))
    st.divider()
    if st.button("Datenqualität jetzt prüfen"):
        n = scan_data_quality(run, df)
        audit_log_event(run, 'system', 'Datenqualität', 'scan', details=f'{n} offene Hinweise gefunden')
        st.success(f"Prüfung abgeschlossen: {n} Hinweise gefunden.")
        st.rerun()
    st.subheader("Offene Datenqualität")
    st.dataframe(df("SELECT id, source_table, source_id, issue_type, severity, description, created_at FROM data_quality_issues WHERE status='offen' ORDER BY severity DESC, id DESC LIMIT 200"), use_container_width=True)
    st.subheader("Letzte Audit-Ereignisse")
    st.dataframe(df("SELECT created_at, actor, area, action, object_type, object_id, details, risk_level FROM audit_events ORDER BY id DESC LIMIT 100"), use_container_width=True)


def page_compliance_center(run, df):
    st.title("Compliance & Recht")
    st.caption("Prüfstatus für Verträge, Datenschutz, AGB, AVV, Backup und Rollen. Vorlagen ersetzen keine juristische Beratung.")
    with st.form("compliance_form"):
        c1, c2 = st.columns(2)
        name = c1.text_input("Prüfpunkt")
        area = c2.selectbox("Bereich", ["Recht", "Datenschutz", "Betrieb", "Sicherheit", "Import", "Verträge", "Sonstiges"])
        status = c1.selectbox("Status", ["offen", "in Arbeit", "erledigt", "blockiert"])
        priority = c2.selectbox("Priorität", ["hoch", "mittel", "niedrig"])
        owner = c1.text_input("Verantwortlich")
        due = c2.text_input("Frist", placeholder="YYYY-MM-DD")
        notes = st.text_area("Notizen")
        if st.form_submit_button("Prüfpunkt speichern"):
            run("""INSERT INTO compliance_checks(check_name,area,status,priority,owner,due_date,notes)
                   VALUES(?,?,?,?,?,?,?)""", (name, area, status, priority, owner, due, notes))
            audit_log_event(run, owner or 'user', 'Compliance', 'create', 'compliance_check', '', name, 'normal')
            st.success("Gespeichert.")
            st.rerun()
    data = df("SELECT * FROM compliance_checks ORDER BY CASE priority WHEN 'hoch' THEN 1 WHEN 'mittel' THEN 2 ELSE 3 END, id DESC")
    st.dataframe(data, use_container_width=True)
    cid = st.number_input("Prüfpunkt-ID ändern/löschen", min_value=0, step=1)
    if cid:
        c1, c2, c3 = st.columns(3)
        if c1.button("Als erledigt markieren"):
            run("UPDATE compliance_checks SET status='erledigt' WHERE id=?", (int(cid),))
            audit_log_event(run, 'user', 'Compliance', 'done', 'compliance_check', cid, 'als erledigt markiert')
            st.rerun()
        if c2.button("Blockiert markieren"):
            run("UPDATE compliance_checks SET status='blockiert' WHERE id=?", (int(cid),))
            audit_log_event(run, 'user', 'Compliance', 'blocked', 'compliance_check', cid, 'blockiert markiert', 'mittel')
            st.rerun()
        if c3.button("Löschen"):
            run("DELETE FROM compliance_checks WHERE id=?", (int(cid),))
            audit_log_event(run, 'user', 'Compliance', 'delete', 'compliance_check', cid, 'gelöscht', 'hoch')
            st.rerun()


def page_export_backup_center(run, df, DB_PATH):
    st.title("Export & Backup Center")
    st.caption("Schneller Export wichtiger CRM-Daten und Backup-Planung.")
    export_type = st.selectbox("Export", ["Kunden", "Rechnungen", "Ausgaben", "Verträge/Dokumente", "Firmenprofile", "Audit-Log", "Compliance"])
    table_map = {
        "Kunden": "customers",
        "Rechnungen": "invoices",
        "Ausgaben": "expenses",
        "Verträge/Dokumente": "crm_documents",
        "Firmenprofile": "company_profiles",
        "Audit-Log": "audit_events",
        "Compliance": "compliance_checks",
    }
    table = table_map[export_type]
    data = df(f"SELECT * FROM {table} ORDER BY id DESC")
    st.dataframe(data.head(200), use_container_width=True)
    csv = data.to_csv(index=False).encode('utf-8-sig')
    st.download_button("CSV herunterladen", csv, file_name=f"byblos_{table}.csv", mime="text/csv")
    st.divider()
    st.subheader("Backup-Hinweise")
    st.write(f"Datenbankpfad: `{DB_PATH}`")
    st.markdown("""
    Empfohlener Mindestprozess:
    - täglich Datenbank sichern
    - wöchentlich Wiederherstellung testen
    - monatlich Export archivieren
    - Zugriff auf Backups beschränken
    - Kundendaten nur verschlüsselt speichern oder übertragen
    """)
    with st.form("export_job_form"):
        notes = st.text_area("Backup-/Exportnotiz")
        if st.form_submit_button("Exportjob protokollieren"):
            run("INSERT INTO export_jobs(export_type,status,notes) VALUES(?,?,?)", (export_type, 'protokolliert', notes))
            audit_log_event(run, 'user', 'Export', 'record', 'export_job', '', export_type)
            st.success("Protokolliert.")
    st.dataframe(df("SELECT * FROM export_jobs ORDER BY id DESC LIMIT 100"), use_container_width=True)
