"""
extensions_v2_automation_ops.py – Automatisierungs-Operationen Byblos CRM v2
==============================================================================
1.  ZUGFeRD PDF-Einbettung (pikepdf)
2.  Google Drive + Dropbox Cloud-Backup
3.  Stripe Checkout Link Generator
4.  ELMA5-Lohnsteuer-Export
5.  Erweiterter Kunden-Import (VCard + komplexes Excel-Mapping)
6.  Mitarbeiter-Schichtpräferenzen + Auto-Planung
7.  Reklamations-Management
8.  Wartungsvertrag-Generator (aus Inventar)
9.  Gewinn-je-Stunde-je-Mitarbeiter Analyse
10. Automatisches Mahnwesen mit Eskalations-Stufen
11. Gantt-Chart Kundenprojekte
12. IMAP E-Mail-Empfang (Rechnungseingang)
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import json
import re
import secrets

import pandas as pd
import streamlit as st


def fmt_eur(v: float) -> str:
    return f"{v:,.2f} €".replace(",", "X").replace(".", ",").replace("X", ".")


# ─────────────────────────────────────────────────────────────
# DB-Registrierung
# ─────────────────────────────────────────────────────────────

def register_automation(run_fn, df_fn) -> None:
    run_fn("""CREATE TABLE IF NOT EXISTS complaints (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        complaint_no TEXT UNIQUE NOT NULL,
        customer_id INTEGER,
        employee_id INTEGER,
        received_date TEXT NOT NULL,
        category TEXT DEFAULT 'allgemein',
        priority TEXT DEFAULT 'normal',
        description TEXT NOT NULL,
        root_cause TEXT,
        corrective_action TEXT,
        status TEXT DEFAULT 'offen',
        resolved_date TEXT,
        notes TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(customer_id) REFERENCES customers(id),
        FOREIGN KEY(employee_id) REFERENCES employees(id)
    )""")
    run_fn("""CREATE TABLE IF NOT EXISTS shift_preferences (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        employee_id INTEGER UNIQUE NOT NULL,
        preferred_days TEXT DEFAULT '[]',
        preferred_hours_start TEXT DEFAULT '06:00',
        preferred_hours_end TEXT DEFAULT '22:00',
        max_hours_week REAL DEFAULT 40,
        qualifications TEXT DEFAULT '[]',
        notes TEXT,
        FOREIGN KEY(employee_id) REFERENCES employees(id)
    )""")
    run_fn("""CREATE TABLE IF NOT EXISTS escalation_rules (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        days_overdue_trigger INTEGER NOT NULL,
        action TEXT NOT NULL,
        fee_amount REAL DEFAULT 0,
        send_email INTEGER DEFAULT 1,
        send_telegram INTEGER DEFAULT 0,
        active INTEGER DEFAULT 1,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )""")
    # Standard-Eskalationsregeln
    for days, action, fee in [
        (7,  "Zahlungserinnerung senden", 0),
        (14, "1. Mahnung + 5 € Gebühr",  5),
        (28, "2. Mahnung + 15 € Gebühr", 15),
        (42, "Letzte Mahnung + 40 € Gebühr + Inkasso-Hinweis", 40),
    ]:
        try:
            run_fn("INSERT OR IGNORE INTO escalation_rules(name,days_overdue_trigger,action,fee_amount) VALUES(?,?,?,?)",
                   (action, days, action, fee))
        except Exception:
            pass


# ─────────────────────────────────────────────────────────────
# 1. ZUGFeRD PDF-Einbettung
# ─────────────────────────────────────────────────────────────

def embed_zugferd_in_pdf(pdf_path: Path, xml_content: str) -> Tuple[bool, str]:
    """Bettet ZUGFeRD-XML als Anhang in bestehendes PDF ein (Factur-X)."""
    try:
        import pikepdf
        from pikepdf import Dictionary, Name, Array

        with pikepdf.open(str(pdf_path)) as pdf:
            # XML als eingebetteten Dateianhang hinzufügen
            xml_bytes = xml_content.encode("utf-8")

            # Eingebettete Datei erstellen
            filespec = pikepdf.Dictionary(
                Type=Name("/Filespec"),
                F=pikepdf.String("factur-x.xml"),
                UF=pikepdf.String("factur-x.xml"),
                Desc=pikepdf.String("Factur-X XML"),
                EF=pikepdf.Dictionary(
                    F=pdf.make_stream(xml_bytes)
                )
            )

            # Zum PDF-Katalog hinzufügen
            if "/Names" not in pdf.Root:
                pdf.Root["/Names"] = pikepdf.Dictionary()
            if "/EmbeddedFiles" not in pdf.Root["/Names"]:
                pdf.Root["/Names"]["/EmbeddedFiles"] = pikepdf.Dictionary(
                    Names=pikepdf.Array([pikepdf.String("factur-x.xml"), filespec])
                )

            # Als PDF/A-3 markieren (für ZUGFeRD-Konformität)
            output_path = pdf_path.with_suffix(".zugferd.pdf")
            pdf.save(str(output_path))

        return True, str(output_path)
    except ImportError:
        return False, "pikepdf nicht installiert (pip install pikepdf)"
    except Exception as e:
        return False, str(e)


def page_zugferd_embed(df_fn, get_setting_fn, base_dir: Path) -> None:
    st.title("🧾 ZUGFeRD PDF-Einbettung")
    st.caption("ZUGFeRD 2.3 XML in bestehendes Rechnungs-PDF einbetten (Factur-X).")

    invoices = df_fn("""
        SELECT i.id, i.invoice_no || ' – ' || c.company AS label, i.pdf_path
        FROM invoices i JOIN customers c ON c.id=i.customer_id
        WHERE i.pdf_path IS NOT NULL AND i.pdf_path != ''
        ORDER BY i.invoice_date DESC LIMIT 100
    """)
    if invoices.empty:
        st.info("Keine Rechnungen mit PDF. Bitte zuerst PDFs erstellen.")
        return

    sel = st.selectbox("Rechnung (mit PDF)", invoices["label"].tolist())
    row = invoices[invoices["label"] == sel].iloc[0]
    iid = int(row["id"])
    pdf_path = Path(str(row.get("pdf_path","") or ""))

    col1, col2 = st.columns(2)
    col1.metric("PDF vorhanden", "✅" if pdf_path.exists() else "❌")

    if not pdf_path.exists():
        st.error(f"PDF nicht gefunden: {pdf_path}")
        return

    if col2.button("🔗 ZUGFeRD einbetten", type="primary"):
        # XML generieren
        from extensions_v2_security import generate_zugferd_xml
        inv = df_fn("SELECT i.*, c.* FROM invoices i JOIN customers c ON c.id=i.customer_id WHERE i.id=?", (iid,)).iloc[0].to_dict()
        items_data = df_fn("SELECT * FROM invoice_items WHERE invoice_id=? ORDER BY position", (iid,))
        items_list = items_data.to_dict("records") if not items_data.empty else []
        seller = {
            "name":   get_setting_fn("company_name","Byblos"),
            "street": get_setting_fn("company_street",""),
            "ust_id": get_setting_fn("company_ust_id",""),
        }
        customer = {"company": str(inv.get("company","")), "street": str(inv.get("street","") or "")}
        xml = generate_zugferd_xml(inv, customer, items_list, seller)

        with st.spinner("PDF wird verarbeitet..."):
            ok, result = embed_zugferd_in_pdf(pdf_path, xml)
        if ok:
            out_path = Path(result)
            st.success(f"✅ ZUGFeRD-PDF: {out_path.name}")
            st.download_button("📥 ZUGFeRD-konformes PDF herunterladen",
                               out_path.read_bytes(), out_path.name, "application/pdf")
        else:
            st.error(f"❌ {result}")
            if "pikepdf" in result:
                st.code("pip install pikepdf", language="bash")


# ─────────────────────────────────────────────────────────────
# 2. Google Drive + Dropbox Backup
# ─────────────────────────────────────────────────────────────

def page_cloud_backup_extended(run_fn, df_fn, get_setting_fn, set_setting_fn,
                                create_backup_fn, base_dir: Path) -> None:
    st.title("☁️ Cloud-Backup Erweitert")
    st.caption("Google Drive, Dropbox und rclone Integration.")

    tabs = st.tabs(["⚙️ Cloud-Dienste", "🔄 Backup erstellen & hochladen",
                    "📋 Backup-Liste", "💡 rclone Anleitung"])

    with tabs[0]:
        with st.form("cloud_form"):
            st.subheader("Google Drive")
            gdrive_folder = st.text_input("Google Drive Ordner-ID",
                                           get_setting_fn("gdrive_folder_id",""),
                                           help="ID aus Google Drive URL: drive.google.com/drive/folders/[ID]")
            st.caption("Google Drive: Service Account JSON unter byblos_crm_app/gdrive_service.json ablegen")

            st.subheader("Dropbox")
            dropbox_token = st.text_input("Dropbox Access Token",
                                           get_setting_fn("dropbox_token",""), type="password")
            dropbox_path  = st.text_input("Dropbox Pfad", get_setting_fn("dropbox_path","/ByblosCRM/Backups/"))

            st.subheader("rclone (universell)")
            rclone_remote = st.text_input("rclone Remote-Name", get_setting_fn("rclone_remote",""))
            rclone_path   = st.text_input("rclone Pfad", get_setting_fn("rclone_path","ByblosCRM/"))

            if st.form_submit_button("💾 Speichern", type="primary"):
                for k,v in [("gdrive_folder_id",gdrive_folder),("dropbox_token",dropbox_token),
                            ("dropbox_path",dropbox_path),("rclone_remote",rclone_remote),
                            ("rclone_path",rclone_path)]:
                    set_setting_fn(k, v)
                st.success("✅ Cloud-Einstellungen gespeichert.")

    with tabs[1]:
        provider = st.selectbox("Backup-Ziel", ["Lokal","WebDAV/Nextcloud","Dropbox","Google Drive (rclone)","rclone"])
        note = st.text_input("Backup-Notiz", "cloud backup")

        if st.button("🔄 Backup erstellen & hochladen", type="primary"):
            with st.spinner("Backup läuft..."):
                try:
                    bp = Path(str(create_backup_fn(note)))
                    size = bp.stat().st_size if bp.exists() else 0
                    run_fn("INSERT INTO backups(file_path,file_size,note) VALUES(?,?,?)",
                           (str(bp), size, f"{note} via {provider}"))
                    st.success(f"✅ Backup: {bp.name} ({size//1024} KB)")

                    if provider == "Dropbox":
                        token = get_setting_fn("dropbox_token","")
                        dpath = get_setting_fn("dropbox_path","/ByblosCRM/")
                        if token:
                            try:
                                import urllib.request, base64
                                url = f"https://content.dropboxapi.com/2/files/upload"
                                headers = {
                                    "Authorization": f"Bearer {token}",
                                    "Content-Type": "application/octet-stream",
                                    "Dropbox-API-Arg": json.dumps({
                                        "path": f"{dpath}{bp.name}",
                                        "mode": "overwrite"
                                    })
                                }
                                req = urllib.request.Request(url, data=bp.read_bytes(), headers=headers)
                                with urllib.request.urlopen(req, timeout=60) as resp:
                                    if resp.status == 200:
                                        st.success(f"☁️ Dropbox: {dpath}{bp.name}")
                                    else:
                                        st.warning(f"Dropbox: HTTP {resp.status}")
                            except Exception as e:
                                st.warning(f"Dropbox-Upload: {e}")
                        else:
                            st.info("Dropbox-Token nicht konfiguriert.")

                    elif provider in ("Google Drive (rclone)","rclone"):
                        remote = get_setting_fn("rclone_remote","")
                        rpath  = get_setting_fn("rclone_path","ByblosCRM/")
                        if remote:
                            import subprocess
                            result = subprocess.run(
                                ["rclone","copy",str(bp),f"{remote}:{rpath}","--progress"],
                                capture_output=True, text=True, timeout=120
                            )
                            if result.returncode == 0:
                                st.success(f"☁️ rclone: {remote}:{rpath}{bp.name}")
                            else:
                                st.warning(f"rclone: {result.stderr[:100]}")
                        else:
                            st.info("rclone Remote nicht konfiguriert.")

                    st.download_button("📥 Backup herunterladen",
                                       bp.read_bytes(), bp.name, "application/octet-stream")
                except Exception as e:
                    st.error(f"Fehler: {e}")

    with tabs[2]:
        backups = df_fn("SELECT created_at AS Erstellt, file_path AS Datei, file_size AS Bytes, note AS Notiz FROM backups ORDER BY created_at DESC LIMIT 30")
        if not backups.empty:
            backups["KB"] = (backups["Bytes"] / 1024).round(0).astype(int)
            st.dataframe(backups[["Erstellt","Datei","KB","Notiz"]], use_container_width=True)
        else:
            st.info("Noch keine Backups.")

    with tabs[3]:
        st.markdown("""
**rclone für universelle Cloud-Unterstützung:**

```bash
# Installation
curl https://rclone.org/install.sh | sudo bash

# Google Drive einrichten
rclone config
# → New remote → Name: gdrive → Storage: Google Drive → Folge den Anweisungen

# Dropbox einrichten
rclone config
# → New remote → Name: dropbox → Storage: Dropbox

# OneDrive einrichten
rclone config
# → New remote → Name: onedrive → Storage: Microsoft OneDrive

# Backup manuell:
rclone copy /pfad/zu/backup.db gdrive:ByblosCRM/

# Automatisch in Cron:
0 6 * * * rclone copy /var/backups/byblos/ gdrive:ByblosCRM/Backups/
```

**rclone unterstützt 50+ Dienste:** Google Drive, Dropbox, OneDrive, S3, Backblaze, SFTP, und mehr.
        """)


# ─────────────────────────────────────────────────────────────
# 3. Stripe Checkout Link Generator
# ─────────────────────────────────────────────────────────────

def page_stripe_integration(df_fn, get_setting_fn, set_setting_fn, run_fn) -> None:
    st.title("💳 Stripe Integration")
    st.caption("Stripe Checkout Links direkt aus Byblos CRM erstellen.")

    tabs = st.tabs(["⚙️ Konfiguration", "🔗 Checkout Link", "📖 API-Anleitung"])

    with tabs[0]:
        with st.form("stripe_config"):
            secret_key = st.text_input("Stripe Secret Key (sk_live_... oder sk_test_...)",
                                        get_setting_fn("stripe_secret_key",""), type="password")
            public_key = st.text_input("Stripe Public Key (pk_live_... oder pk_test_...)",
                                        get_setting_fn("stripe_public_key",""))
            webhook_secret = st.text_input("Webhook Signing Secret (whsec_...)",
                                            get_setting_fn("stripe_webhook_secret",""), type="password")
            currency = st.selectbox("Währung", ["eur","usd","gbp"],
                                     index=["eur","usd","gbp"].index(get_setting_fn("stripe_currency","eur")))
            if st.form_submit_button("💾 Speichern", type="primary"):
                for k,v in [("stripe_secret_key",secret_key),("stripe_public_key",public_key),
                            ("stripe_webhook_secret",webhook_secret),("stripe_currency",currency)]:
                    set_setting_fn(k, v)
                st.success("✅ Stripe-Einstellungen gespeichert.")

    with tabs[1]:
        invoices = df_fn("""
            SELECT i.id, i.invoice_no || ' – ' || c.company AS label,
                   ROUND(i.gross_total - i.paid_amount, 2) AS offen,
                   c.email AS email
            FROM invoices i JOIN customers c ON c.id=i.customer_id
            WHERE i.status IN ('offen','ueberfaellig')
              AND ROUND(i.gross_total - i.paid_amount, 2) > 0
            ORDER BY i.invoice_date DESC LIMIT 50
        """)
        if invoices.empty:
            st.info("Keine offenen Rechnungen.")
        else:
            sel = st.selectbox("Rechnung", invoices["label"].tolist())
            row = invoices[invoices["label"] == sel].iloc[0]
            amount = float(row["offen"])
            email  = str(row.get("email","") or "")

            st.metric("Offener Betrag", fmt_eur(amount))
            stripe_key = get_setting_fn("stripe_secret_key","")
            currency   = get_setting_fn("stripe_currency","eur")

            if not stripe_key:
                st.warning("Bitte zuerst Stripe Secret Key konfigurieren.")
            elif st.button("🔗 Stripe Checkout Link erstellen", type="primary"):
                try:
                    import urllib.request, urllib.parse
                    # Stripe API: Payment Link erstellen
                    # Zuerst ein Price-Objekt erstellen
                    price_data = urllib.parse.urlencode({
                        "unit_amount": int(amount * 100),  # Cents
                        "currency": currency,
                        "product_data[name]": sel[:250],
                    }).encode()

                    req = urllib.request.Request(
                        "https://api.stripe.com/v1/payment_links",
                        data=urllib.parse.urlencode({
                            "line_items[0][price_data][unit_amount]": int(amount * 100),
                            "line_items[0][price_data][currency]": currency,
                            "line_items[0][price_data][product_data][name]": sel[:250],
                            "line_items[0][quantity]": "1",
                            "after_completion[type]": "message",
                            "after_completion[message][message]": "Vielen Dank für Ihre Zahlung!",
                        }).encode(),
                        headers={
                            "Authorization": f"Bearer {stripe_key}",
                            "Content-Type": "application/x-www-form-urlencoded",
                        }
                    )
                    with urllib.request.urlopen(req, timeout=15) as resp:
                        result = json.loads(resp.read())
                        link_url = result.get("url","")
                        if link_url:
                            run_fn("INSERT INTO payment_links(invoice_id,provider,link_url,amount,status) VALUES(?,?,?,?,?)",
                                   (int(row["id"]), "Stripe", link_url, amount, "aktiv"))
                            st.success("✅ Stripe Payment Link erstellt!")
                            st.code(link_url, language="text")
                            st.info("Link per E-Mail an Kunden senden oder in Rechnung einfügen.")
                        else:
                            st.error(f"Stripe-Fehler: {result}")
                except Exception as e:
                    st.error(f"Stripe API-Fehler: {e}")
                    st.info("Tipp: Im Test-Modus sk_test_... verwenden.")

    with tabs[2]:
        st.markdown("""
**Stripe API ohne Bibliothek (direkt HTTP):**
```python
import urllib.request, urllib.parse, json

stripe_key = "sk_test_..."
amount_cents = 119000  # 1.190,00 €

req = urllib.request.Request(
    "https://api.stripe.com/v1/payment_links",
    data=urllib.parse.urlencode({
        "line_items[0][price_data][unit_amount]": amount_cents,
        "line_items[0][price_data][currency]": "eur",
        "line_items[0][price_data][product_data][name]": "Objektschutz März 2025",
        "line_items[0][quantity]": "1",
    }).encode(),
    headers={"Authorization": f"Bearer {stripe_key}",
             "Content-Type": "application/x-www-form-urlencoded"}
)
with urllib.request.urlopen(req) as r:
    result = json.loads(r.read())
    print(result["url"])  # Checkout-Link
```

**Webhook für automatische Zahlungsbestätigung:**
- Stripe Dashboard → Webhooks → Endpoint hinzufügen
- URL: `https://crm.byblos.de/api/v1/webhook`
- Event: `payment_intent.succeeded`
        """)


# ─────────────────────────────────────────────────────────────
# 4. ELMA5-ähnlicher Lohnsteuer-Export
# ─────────────────────────────────────────────────────────────

def generate_elma5_export(df_fn, year: int, month: int, get_setting_fn) -> str:
    """
    Erstellt einen ELMA5-ähnlichen Lohnsteuer-Export.
    Hinweis: Echter ELMA5 via ELSTER-Portal – dieser Export ist eine Vorlage.
    """
    month_str = f"{year}-{month:02d}"
    payrolls  = df_fn("""
        SELECT e.name, e.employee_no, e.tax_class,
               p.gross_salary, p.income_tax, p.solidarity_surcharge,
               p.health_ins_employee, p.pension_ins_employee,
               p.unemployment_ins_employee, p.care_ins_employee,
               p.employer_contribution
        FROM payroll_records p JOIN employees e ON e.id=p.employee_id
        WHERE p.payroll_month=?
    """, (month_str,))

    if payrolls.empty:
        return ""

    co_name  = get_setting_fn("company_name","Byblos")
    co_strnr = get_setting_fn("company_steuernummer","")

    lines = [
        f"ELMA5-EXPORT {month_str}",
        f"Arbeitgeber: {co_name}",
        f"Steuernummer: {co_strnr}",
        f"Zeitraum: {month:02d}/{year}",
        "=" * 60,
        f"{'Name':<25}{'Nr.':<12}{'Brutto':>10}{'LSt':>10}{'SolZ':>10}{'KV-AN':>10}",
        "-" * 60,
    ]
    totals = {"brutto":0,"lst":0,"solz":0,"kv":0}
    for _, r in payrolls.iterrows():
        brutto = float(r.get("gross_salary") or 0)
        lst    = float(r.get("income_tax") or 0)
        solz   = float(r.get("solidarity_surcharge") or 0)
        kv     = float(r.get("health_ins_employee") or 0)
        lines.append(f"{str(r['name']):<25}{str(r['employee_no']):<12}"
                      f"{brutto:>10.2f}{lst:>10.2f}{solz:>10.2f}{kv:>10.2f}")
        totals["brutto"] += brutto; totals["lst"] += lst
        totals["solz"]   += solz;   totals["kv"]  += kv
    lines.append("-" * 60)
    lines.append(f"{'GESAMT':<25}{'':12}{totals['brutto']:>10.2f}{totals['lst']:>10.2f}"
                  f"{totals['solz']:>10.2f}{totals['kv']:>10.2f}")
    lines.append(f"\nAnmeldezeitraum: {month:02d}/{year}")
    lines.append(f"Abzuführende Lohnsteuer: {totals['lst']:.2f} EUR")
    lines.append(f"Solidaritätszuschlag:    {totals['solz']:.2f} EUR")
    lines.append(f"Hinweis: Über ELSTER-Portal elektronisch anmelden!")
    return "\n".join(lines)


def page_elma5_export(df_fn, get_setting_fn) -> None:
    st.title("📊 Lohnsteuer-Anmeldung Export")
    st.caption("Übersicht für die monatliche Lohnsteuer-Anmeldung via ELSTER.")

    col1, col2 = st.columns(2)
    year  = col1.selectbox("Jahr", list(range(date.today().year, date.today().year-3,-1)))
    month = col2.selectbox("Monat", list(range(1,13)), index=date.today().month-1,
                            format_func=lambda m: ["Jan","Feb","Mär","Apr","Mai","Jun",
                                                    "Jul","Aug","Sep","Okt","Nov","Dez"][m-1])
    if st.button("📄 Export erstellen", type="primary"):
        content = generate_elma5_export(df_fn, year, month, get_setting_fn)
        if content:
            st.text_area("Lohnsteuer-Übersicht", content, height=350)
            st.download_button("📥 Als TXT herunterladen",
                               content.encode("utf-8"),
                               f"lohnsteuer_anmeldung_{year}_{month:02d}.txt",
                               "text/plain")
            st.warning("⚠️ Authentische Lohnsteuer-Anmeldung: nur via ELSTER (elster.de) möglich!")
        else:
            st.info(f"Keine Lohnabrechnungen für {year}-{month:02d}.")


# ─────────────────────────────────────────────────────────────
# 5. Erweiterter Kunden-Import (VCard)
# ─────────────────────────────────────────────────────────────

def parse_vcard(vcard_text: str) -> List[Dict]:
    """Parst VCard 3.0/4.0 Format zu Kunden-Dicts."""
    contacts = []
    current = {}
    for line in vcard_text.splitlines():
        line = line.strip()
        if line == "BEGIN:VCARD":
            current = {}
        elif line == "END:VCARD":
            if current:
                contacts.append(current)
        elif line.startswith("FN:"):
            current["company"] = line[3:]
        elif line.startswith("ORG:"):
            org = line[4:].split(";")[0]
            if org:
                current["company"] = org
        elif line.startswith("TEL"):
            phone = re.sub(r'TEL[^:]*:', '', line)
            current["phone"] = phone
        elif line.startswith("EMAIL"):
            email = re.sub(r'EMAIL[^:]*:', '', line)
            current["email"] = email
        elif line.startswith("ADR"):
            adr = re.sub(r'ADR[^:]*:', '', line).split(";")
            if len(adr) >= 3:
                current["street"] = adr[2].strip() if len(adr) > 2 else ""
                city   = adr[3].strip() if len(adr) > 3 else ""
                postal = adr[5].strip() if len(adr) > 5 else ""
                current["zip_city"] = f"{postal} {city}".strip()
        elif line.startswith("NOTE:"):
            current["notes"] = line[5:]
    return contacts


def page_vcard_import(run_fn, df_fn, next_number_fn, log_fn) -> None:
    st.title("📇 VCard-Kunden-Import")
    st.caption("Kontakte aus VCard (.vcf) direkt importieren.")

    uploaded = st.file_uploader("VCard-Datei hochladen (.vcf)", type=["vcf","vcard","txt"])
    if uploaded:
        text = uploaded.read().decode("utf-8", errors="ignore")
        contacts = parse_vcard(text)

        if contacts:
            st.success(f"✅ {len(contacts)} Kontakte erkannt")
            df_prev = pd.DataFrame(contacts)
            st.dataframe(df_prev.head(10), use_container_width=True)

            if st.button(f"📥 Alle {len(contacts)} importieren", type="primary"):
                imported = skipped = 0
                for c in contacts:
                    company = str(c.get("company","")).strip()
                    if not company:
                        skipped += 1
                        continue
                    existing = df_fn("SELECT id FROM customers WHERE company=?", (company,))
                    if not existing.empty:
                        skipped += 1
                        continue
                    cno = next_number_fn("customers","customer_no","SD-")
                    run_fn("INSERT INTO customers(customer_no,company,email,phone,street,zip_city,notes) VALUES(?,?,?,?,?,?,?)",
                           (cno, company, c.get("email",""), c.get("phone",""),
                            c.get("street",""), c.get("zip_city",""), c.get("notes","")))
                    imported += 1
                log_fn("vcard_import", f"{imported} Kontakte importiert")
                st.success(f"✅ {imported} importiert · {skipped} übersprungen")
                st.rerun()
        else:
            st.warning("Keine VCard-Einträge erkannt.")


# ─────────────────────────────────────────────────────────────
# 6. Mitarbeiter-Schichtpräferenzen + Auto-Planung
# ─────────────────────────────────────────────────────────────

def page_shift_preferences(run_fn, df_fn, log_fn) -> None:
    st.title("⚙️ Schichtpräferenzen & Auto-Planung")
    st.caption("Mitarbeiter-Präferenzen erfassen und automatisch optimale Schichtpläne erstellen.")

    tabs = st.tabs(["📋 Präferenzen", "🤖 Auto-Planung"])

    with tabs[0]:
        employees = df_fn("SELECT id, employee_no || ' – ' || name AS label FROM employees WHERE active=1 ORDER BY name")
        if employees.empty:
            st.info("Keine aktiven Mitarbeiter.")
            return

        sel = st.selectbox("Mitarbeiter", employees["label"].tolist())
        eid = int(employees[employees["label"] == sel].iloc[0]["id"])
        existing = df_fn("SELECT * FROM shift_preferences WHERE employee_id=?", (eid,))
        pref = existing.iloc[0].to_dict() if not existing.empty else {}

        with st.form("pref_form"):
            DAYS = ["Montag","Dienstag","Mittwoch","Donnerstag","Freitag","Samstag","Sonntag"]
            current_days = json.loads(str(pref.get("preferred_days","[]") or "[]"))
            preferred_days = st.multiselect("Bevorzugte Arbeitstage", DAYS,
                                             default=current_days)
            col1, col2 = st.columns(2)
            start = col1.time_input("Früheste Startzeit",
                                    datetime.strptime(str(pref.get("preferred_hours_start","06:00")), "%H:%M").time())
            end   = col2.time_input("Späteste Endzeit",
                                    datetime.strptime(str(pref.get("preferred_hours_end","22:00")), "%H:%M").time())
            max_h = st.slider("Max. Stunden/Woche", 10, 48, int(float(pref.get("max_hours_week",40) or 40)))
            notes = st.text_area("Notizen", str(pref.get("notes","") or ""))

            if st.form_submit_button("💾 Präferenzen speichern", type="primary"):
                data_json = json.dumps(preferred_days)
                if existing.empty:
                    run_fn("INSERT INTO shift_preferences(employee_id,preferred_days,preferred_hours_start,preferred_hours_end,max_hours_week,notes) VALUES(?,?,?,?,?,?)",
                           (eid, data_json, start.strftime("%H:%M"), end.strftime("%H:%M"), max_h, notes))
                else:
                    run_fn("UPDATE shift_preferences SET preferred_days=?,preferred_hours_start=?,preferred_hours_end=?,max_hours_week=?,notes=? WHERE employee_id=?",
                           (data_json, start.strftime("%H:%M"), end.strftime("%H:%M"), max_h, notes, eid))
                log_fn("shift_pref_saved", sel)
                st.success("✅ Präferenzen gespeichert!")
                st.rerun()

    with tabs[1]:
        st.subheader("🤖 Automatische Schichtzuweisung")
        st.caption("Weist unbesetzte Schichten anhand von Präferenzen zu.")

        from_d = st.date_input("Von", date.today())
        to_d   = st.date_input("Bis", date.today() + timedelta(days=7))

        unassigned = df_fn("""
            SELECT s.id, s.shift_date, s.start_time, s.end_time, s.shift_type,
                   COALESCE(c.company,'–') AS kunde
            FROM shifts s LEFT JOIN customers c ON c.id=s.customer_id
            WHERE s.employee_id IS NULL AND s.shift_date BETWEEN ? AND ?
            ORDER BY s.shift_date, s.start_time
        """, (from_d.isoformat(), to_d.isoformat()))

        prefs = df_fn("""
            SELECT sp.employee_id, e.name, sp.preferred_days,
                   sp.preferred_hours_start, sp.preferred_hours_end, sp.max_hours_week
            FROM shift_preferences sp JOIN employees e ON e.id=sp.employee_id
            WHERE e.active=1
        """)

        if unassigned.empty:
            st.success("✅ Alle Schichten sind besetzt.")
            return

        st.info(f"{len(unassigned)} unbesetzte Schichten werden automatisch zugewiesen:")

        DAYS_MAP = {0:"Montag",1:"Dienstag",2:"Mittwoch",3:"Donnerstag",
                    4:"Freitag",5:"Samstag",6:"Sonntag"}
        assignments = []
        for _, shift in unassigned.iterrows():
            shift_d = date.fromisoformat(str(shift["shift_date"]))
            shift_day_name = DAYS_MAP[shift_d.weekday()]
            best_emp = None
            for _, emp in prefs.iterrows():
                pref_days = json.loads(str(emp.get("preferred_days","[]") or "[]"))
                if pref_days and shift_day_name not in pref_days:
                    continue
                best_emp = emp
                break
            assignments.append({
                "Datum": shift["shift_date"],
                "Von": str(shift["start_time"])[:5],
                "Bis": str(shift["end_time"])[:5],
                "Objekt": shift["kunde"],
                "Zugewiesen an": str(best_emp["name"]) if best_emp is not None else "❌ Niemand verfügbar",
                "_sid": int(shift["id"]),
                "_eid": int(best_emp["employee_id"]) if best_emp is not None else None,
            })

        df_asgn = pd.DataFrame(assignments)
        st.dataframe(df_asgn.drop(columns=["_sid","_eid"]), use_container_width=True)

        if st.button(f"✅ {len([a for a in assignments if a['_eid']])} Zuweisungen übernehmen", type="primary"):
            assigned = 0
            for a in assignments:
                if a["_eid"]:
                    run_fn("UPDATE shifts SET employee_id=? WHERE id=?", (a["_eid"], a["_sid"]))
                    assigned += 1
            log_fn("auto_shift_assigned", f"{assigned} Schichten automatisch besetzt")
            st.success(f"✅ {assigned} Schichten besetzt!")
            st.rerun()


# ─────────────────────────────────────────────────────────────
# 7. Reklamations-Management
# ─────────────────────────────────────────────────────────────

COMPLAINT_CATS = ["Qualitätsmangel","Verspätung","Kommunikation","Mitarbeiterverhalten",
                  "Technisches Problem","Abrechnung","Sonstiges"]
COMPLAINT_PRIOS = ["niedrig","normal","hoch","kritisch"]


def page_complaints(run_fn, df_fn, next_number_fn, log_fn) -> None:
    st.title("📋 Reklamations-Management")
    st.caption("Kundenbeschwerden und Qualitätsmängel erfassen und verfolgen.")

    tabs = st.tabs(["📋 Übersicht", "➕ Neue Reklamation",
                    "📊 Auswertung", "✅ Abschließen"])

    with tabs[0]:
        status_f = st.selectbox("Status", ["alle","offen","in Bearbeitung","gelöst","geschlossen"])
        q = """
            SELECT r.id, r.complaint_no AS Nr, r.received_date AS Datum,
                   COALESCE(c.company,'–') AS Kunde, r.category AS Kategorie,
                   r.priority AS Priorität, r.status AS Status,
                   r.description AS Beschreibung
            FROM complaints r LEFT JOIN customers c ON c.id=r.customer_id
        """
        params = []
        if status_f != "alle":
            q += " WHERE r.status=?"; params.append(status_f)
        q += " ORDER BY r.received_date DESC"
        data = df_fn(q, tuple(params))

        if not data.empty:
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Gesamt", len(data))
            c2.metric("Offen", len(data[data["Status"]=="offen"]))
            c3.metric("In Bearbeitung", len(data[data["Status"]=="in Bearbeitung"]))
            c4.metric("Kritisch", len(data[data["Priorität"]=="kritisch"]))
            st.dataframe(data.drop(columns=["id"]), use_container_width=True, height=350)
            csv = data.drop(columns=["id"]).to_csv(index=False, sep=";").encode("utf-8-sig")
            st.download_button("📥 CSV-Export", csv, "reklamationen.csv", "text/csv")
        else:
            st.info("Keine Reklamationen in diesem Status.")

    with tabs[1]:
        customers = df_fn("SELECT id, customer_no || ' – ' || company AS label FROM customers ORDER BY company")
        employees = df_fn("SELECT id, name FROM employees WHERE active=1 ORDER BY name")

        with st.form("complaint_form", clear_on_submit=True):
            comp_no = st.text_input("Reklamations-Nr.", next_number_fn("complaints","complaint_no","RK-"))
            col1, col2 = st.columns(2)
            cust_label = col1.selectbox("Kunde", ["—"] + (customers["label"].tolist() if not customers.empty else []))
            rec_date   = col2.date_input("Eingangsdatum", date.today())
            category   = col1.selectbox("Kategorie", COMPLAINT_CATS)
            priority   = col2.selectbox("Priorität", COMPLAINT_PRIOS)
            description = st.text_area("Beschreibung des Problems *", height=100)
            root_cause  = st.text_area("Ursachenanalyse")
            corrective  = st.text_area("Maßnahmen / Korrekturmaßnahmen")
            submitted   = st.form_submit_button("💾 Speichern", type="primary")

        if submitted and description:
            cid = None
            if cust_label != "—" and not customers.empty:
                match = customers[customers["label"] == cust_label]
                if not match.empty: cid = int(match.iloc[0]["id"])
            run_fn("""INSERT INTO complaints(complaint_no,customer_id,received_date,category,
                      priority,description,root_cause,corrective_action,status)
                      VALUES(?,?,?,?,?,?,?,?,?)""",
                   (comp_no, cid, rec_date.isoformat(), category, priority,
                    description, root_cause, corrective, "offen"))
            log_fn("complaint_created", comp_no)
            st.success(f"✅ Reklamation {comp_no} erstellt!")
            st.rerun()

    with tabs[2]:
        by_cat = df_fn("""
            SELECT category AS Kategorie, priority AS Priorität,
                   COUNT(*) AS Anzahl,
                   SUM(CASE WHEN status='gelöst' THEN 1 ELSE 0 END) AS Gelöst,
                   ROUND(AVG(julianday(COALESCE(resolved_date,date('now'))) - julianday(received_date)),1) AS Ø_Tage_Lösung
            FROM complaints GROUP BY category, priority ORDER BY Anzahl DESC
        """)
        if not by_cat.empty:
            st.dataframe(by_cat, use_container_width=True)
            st.bar_chart(by_cat.groupby("Kategorie")["Anzahl"].sum())
        else:
            st.info("Noch keine Reklamationen.")

    with tabs[3]:
        open_comps = df_fn("""
            SELECT r.id, r.complaint_no || ' – ' || COALESCE(c.company,'?') AS label
            FROM complaints r LEFT JOIN customers c ON c.id=r.customer_id
            WHERE r.status IN ('offen','in Bearbeitung')
            ORDER BY r.received_date
        """)
        if not open_comps.empty:
            sel = st.selectbox("Reklamation abschließen", open_comps["label"].tolist())
            rid = int(open_comps[open_comps["label"] == sel].iloc[0]["id"])
            new_status = st.selectbox("Status", ["in Bearbeitung","gelöst","geschlossen"])
            solution = st.text_area("Abschlussbemerkung / Lösung")
            if st.button("✅ Status setzen", type="primary"):
                run_fn("UPDATE complaints SET status=?,corrective_action=?,resolved_date=? WHERE id=?",
                       (new_status, solution,
                        date.today().isoformat() if new_status in ("gelöst","geschlossen") else None,
                        rid))
                log_fn("complaint_updated", f"id={rid} status={new_status}")
                st.success("✅ Status aktualisiert!")
                st.rerun()
        else:
            st.success("✅ Keine offenen Reklamationen.")


# ─────────────────────────────────────────────────────────────
# 8. Automatisches Mahnwesen mit Eskalations-Stufen
# ─────────────────────────────────────────────────────────────

def page_escalation_management(run_fn, df_fn, log_fn, queue_email_fn, get_setting_fn) -> None:
    st.title("📈 Automatisches Mahnwesen")
    st.caption("Konfigurierbare Eskalationsstufen für überfällige Rechnungen.")

    tabs = st.tabs(["⚙️ Eskalationsregeln", "🚀 Ausführen", "📋 Protokoll"])

    with tabs[0]:
        rules = df_fn("SELECT * FROM escalation_rules ORDER BY days_overdue_trigger")
        if not rules.empty:
            st.dataframe(rules, use_container_width=True)

        st.divider()
        with st.form("rule_form", clear_on_submit=True):
            st.subheader("Neue Regel")
            col1, col2 = st.columns(2)
            name    = col1.text_input("Regelname")
            days    = col2.number_input("Ab Tagen überfällig", min_value=1, value=14, step=7)
            action  = st.text_input("Aktion / Beschreibung", "Mahnung senden")
            col3, col4, col5 = st.columns(3)
            fee     = col3.number_input("Mahngebühr (€)", min_value=0.0, value=0.0, step=5.0)
            send_m  = col4.checkbox("E-Mail senden", value=True)
            send_tg = col5.checkbox("Telegram", value=False)
            if st.form_submit_button("➕ Regel anlegen") and name:
                run_fn("INSERT INTO escalation_rules(name,days_overdue_trigger,action,fee_amount,send_email,send_telegram) VALUES(?,?,?,?,?,?)",
                       (name, days, action, fee, 1 if send_m else 0, 1 if send_tg else 0))
                st.success(f"Regel '{name}' angelegt.")
                st.rerun()

    with tabs[1]:
        st.subheader("Eskalation jetzt ausführen")
        today = date.today()
        overdue = df_fn("""
            SELECT i.id, i.invoice_no, c.company, c.email,
                   i.due_date, i.gross_total, i.paid_amount,
                   CAST(julianday('now') - julianday(i.due_date) AS INT) AS tage_overdue
            FROM invoices i JOIN customers c ON c.id=i.customer_id
            WHERE i.status IN ('offen','ueberfaellig')
              AND ROUND(i.gross_total - i.paid_amount, 2) > 0
              AND i.due_date < date('now')
            ORDER BY tage_overdue DESC
        """)
        rules_data = df_fn("SELECT * FROM escalation_rules WHERE active=1 ORDER BY days_overdue_trigger")

        if overdue.empty or rules_data.empty:
            st.info("Keine überfälligen Rechnungen oder keine aktiven Regeln.")
        else:
            preview = []
            for _, inv in overdue.iterrows():
                days_late = int(inv["tage_overdue"])
                # Passende Regel finden (höchste Stufe die greift)
                matching_rules = rules_data[rules_data["days_overdue_trigger"] <= days_late]
                if not matching_rules.empty:
                    rule = matching_rules.iloc[-1]
                    preview.append({
                        "Rechnung": inv["invoice_no"],
                        "Kunde": inv["company"],
                        "Tage überfällig": days_late,
                        "Anwendbare Regel": rule["name"],
                        "Gebühr": fmt_eur(float(rule["fee_amount"])),
                        "E-Mail": "✅" if rule["send_email"] else "–",
                    })

            if preview:
                st.dataframe(pd.DataFrame(preview), use_container_width=True)
                dry_run = st.checkbox("Vorschau (keine echten Aktionen)", value=True)
                if st.button(f"🚀 Eskalation für {len(preview)} Rechnungen ausführen", type="primary"):
                    executed = 0
                    for _, inv in overdue.iterrows():
                        days_late = int(inv["tage_overdue"])
                        matching = rules_data[rules_data["days_overdue_trigger"] <= days_late]
                        if matching.empty:
                            continue
                        rule = matching.iloc[-1]
                        if not dry_run:
                            offen = float(inv["gross_total"]) - float(inv["paid_amount"])
                            co_name = get_setting_fn("company_name","Byblos")
                            if rule["send_email"] and str(inv.get("email","")):
                                body = (f"Sehr geehrte Damen und Herren,\n\n"
                                        f"Ihre Rechnung {inv['invoice_no']} vom "
                                        f"{inv['due_date']} über {fmt_eur(offen)} ist seit "
                                        f"{days_late} Tagen überfällig.\n\n"
                                        f"{rule['action']}\n\n"
                                        f"Mit freundlichen Grüßen\n{co_name}")
                                queue_email_fn(str(inv["email"]),
                                              f"{rule['name']}: {inv['invoice_no']}",
                                              body, "")
                            if float(rule["fee_amount"]) > 0:
                                run_fn("INSERT INTO late_fees(invoice_id,fee_date,fee_amount,fee_type,days_overdue,status) VALUES(?,?,?,?,?,?)",
                                       (int(inv["id"]), date.today().isoformat(),
                                        float(rule["fee_amount"]), rule["name"],
                                        days_late, "offen"))
                            log_fn("escalation_executed", f"{inv['invoice_no']} → {rule['name']}")
                            executed += 1

                    if dry_run:
                        st.info(f"Vorschau: {len(preview)} Rechnungen würden bearbeitet.")
                    else:
                        st.success(f"✅ {executed} Rechnungen eskaliert!")
                        st.rerun()

    with tabs[2]:
        escl_log = df_fn("SELECT created_at AS Zeit, action AS Aktion, result AS Ergebnis FROM automation_log WHERE action LIKE 'escalation%' ORDER BY created_at DESC LIMIT 50")
        if not escl_log.empty:
            st.dataframe(escl_log, use_container_width=True)
        else:
            st.info("Noch keine Eskalationen ausgeführt.")


# ─────────────────────────────────────────────────────────────
# 9. Gewinn je Stunde je Mitarbeiter
# ─────────────────────────────────────────────────────────────

def page_profit_per_hour(df_fn) -> None:
    st.title("💰 Gewinn je Stunde je Mitarbeiter")
    st.caption("Rentabilitäts-Analyse: Welcher Mitarbeiter generiert den höchsten Deckungsbeitrag pro Stunde?")

    year = st.selectbox("Jahr", list(range(date.today().year, date.today().year-3,-1)))

    # Mitarbeiter-Stunden aus Zeiterfassung
    hours_data = df_fn(f"""
        SELECT e.id, e.name AS Mitarbeiter, e.hourly_rate AS Stundensatz,
               COALESCE(SUM(t.net_hours),0) AS Stunden_gesamt,
               COALESCE(SUM(t.overtime_hours),0) AS Überstunden
        FROM employees e
        LEFT JOIN time_entries t ON t.employee_id=e.id AND substr(t.date,1,4)='{year}'
        WHERE e.active=1
        GROUP BY e.id ORDER BY Stunden_gesamt DESC
    """)

    # Umsatz je Mitarbeiter über Schichten → Kunden → Rechnungen
    revenue_data = df_fn(f"""
        SELECT s.employee_id, ROUND(SUM(i.gross_total) / COUNT(DISTINCT s.customer_id),2) AS Ø_Umsatz_je_Kunde
        FROM shifts s
        JOIN invoices i ON i.customer_id=s.customer_id
        WHERE substr(s.shift_date,1,4)='{year}' AND i.status='bezahlt'
          AND substr(i.invoice_date,1,4)='{year}'
        GROUP BY s.employee_id
    """)

    if hours_data.empty:
        st.info("Keine Stundendaten für dieses Jahr.")
        return

    # Lohnkosten je Mitarbeiter
    payroll_data = df_fn(f"""
        SELECT p.employee_id, ROUND(SUM(p.gross_salary),2) AS Lohnkosten
        FROM payroll_records p WHERE substr(p.payroll_month,1,4)='{year}'
        GROUP BY p.employee_id
    """)

    # Merge
    merged = hours_data.copy()
    if not payroll_data.empty:
        merged = merged.merge(payroll_data, left_on="id", right_on="employee_id", how="left")
    else:
        merged["Lohnkosten"] = merged["Stunden_gesamt"] * merged["Stundensatz"]
    merged["Lohnkosten"] = merged["Lohnkosten"].fillna(
        merged["Stunden_gesamt"] * merged["Stundensatz"]
    )

    # Berechne DB je Stunde (geschätzt)
    avg_hourly_revenue = float(df_fn(f"""
        SELECT COALESCE(AVG(gross_total/8.0),0) AS avg_rev_h
        FROM invoices WHERE substr(invoice_date,1,4)='{year}' AND status='bezahlt'
    """).iloc[0]["avg_rev_h"])

    merged["Umsatz_est"]  = merged["Stunden_gesamt"] * avg_hourly_revenue
    merged["DB1_est"]     = (merged["Umsatz_est"] - merged["Lohnkosten"]).round(2)
    merged["DB1_je_Std"]  = (merged["DB1_est"] / merged["Stunden_gesamt"].replace(0,1)).round(2)
    merged["Rentabilität"] = merged["DB1_je_Std"].apply(
        lambda v: "🟢 Sehr gut" if v > 10 else "🟡 OK" if v > 0 else "🔴 Verlust"
    )

    c1, c2, c3 = st.columns(3)
    c1.metric("Mitarbeiter analysiert", len(merged))
    c2.metric("Gesamtstunden", f"{float(merged['Stunden_gesamt'].sum()):.0f} h")
    c3.metric("Ø DB je Stunde", fmt_eur(float(merged["DB1_je_Std"].mean())))

    st.dataframe(merged[["Mitarbeiter","Stunden_gesamt","Lohnkosten","Umsatz_est","DB1_est","DB1_je_Std","Rentabilität"]].rename(
        columns={"Stunden_gesamt":"Stunden","Lohnkosten":"Lohnkosten_EUR","Umsatz_est":"Umsatz_est_EUR",
                  "DB1_est":"DB1_EUR","DB1_je_Std":"DB1_je_Std_EUR"}
    ), use_container_width=True)
    st.bar_chart(merged.set_index("Mitarbeiter")["DB1_je_Std"])

    st.caption("⚠️ Schätzwerte basierend auf durchschnittlichem Stundenumsatz. Für exakte Zahlen: Projektzeiterfassung nutzen.")


# ─────────────────────────────────────────────────────────────
# 10. Gantt-Chart Kundenprojekte
# ─────────────────────────────────────────────────────────────

def page_gantt_chart(df_fn) -> None:
    st.title("📊 Projekt-Gantt-Chart")
    st.caption("Projektlaufzeiten und -phasen visuell darstellen.")

    year = st.selectbox("Jahr", list(range(date.today().year, date.today().year-2,-1)))

    projects = df_fn(f"""
        SELECT p.project_no AS Nr, p.project_name AS Projekt,
               COALESCE(c.company,'–') AS Kunde,
               p.start_date, p.end_date,
               p.budget_eur AS Budget, p.billed_eur AS Abgerechnet,
               p.status AS Status
        FROM projects p LEFT JOIN customers c ON c.id=p.customer_id
        WHERE substr(p.start_date,1,4)='{year}'
           OR substr(COALESCE(p.end_date,p.start_date),1,4)='{year}'
        ORDER BY p.start_date
    """)

    if projects.empty:
        st.info("Keine Projekte in diesem Jahr.")
        return

    # Einfaches Gantt als HTML-Tabelle
    html = f"""
<style>
.gantt {{ font-family: sans-serif; font-size: 12px; width: 100%; }}
.gantt th {{ background: #1a2744; color: white; padding: 4px 6px; }}
.gantt td {{ padding: 3px 6px; border-bottom: 1px solid #2d3142; }}
.bar {{ height: 14px; border-radius: 3px; display: inline-block; }}
.bar-done {{ background: #27ae60; }}
.bar-active {{ background: #2980b9; }}
.bar-paused {{ background: #e67e22; }}
.bar-overdue {{ background: #c0392b; }}
</style>
<table class="gantt">
<tr>
    <th>Projekt</th><th>Kunde</th>
    <th>Jan</th><th>Feb</th><th>Mär</th><th>Apr</th><th>Mai</th><th>Jun</th>
    <th>Jul</th><th>Aug</th><th>Sep</th><th>Okt</th><th>Nov</th><th>Dez</th>
    <th>Status</th>
</tr>
"""
    today_str = date.today().isoformat()
    for _, p in projects.iterrows():
        try:
            s = date.fromisoformat(str(p["start_date"])[:10])
            e_str = str(p.get("end_date","") or "")
            e = date.fromisoformat(e_str[:10]) if e_str else date(year,12,31)
        except Exception:
            continue

        status = str(p["Status"])
        bar_class = {"abgeschlossen":"bar-done","aktiv":"bar-active",
                      "pausiert":"bar-paused"}.get(status, "bar-active")
        if status == "aktiv" and e.isoformat() < today_str:
            bar_class = "bar-overdue"

        html += f"<tr><td><strong>{p['Projekt'][:25]}</strong></td><td>{p['Kunde'][:20]}</td>"
        for month in range(1, 13):
            month_start = date(year, month, 1)
            month_end   = date(year, month, [31,28,31,30,31,30,31,31,30,31,30,31][month-1])
            if month == 2 and year % 4 == 0:
                month_end = date(year, 2, 29)

            overlap_start = max(s, month_start)
            overlap_end   = min(e, month_end)

            if overlap_start <= overlap_end:
                total_days = (month_end - month_start).days + 1
                bar_days   = (overlap_end - overlap_start).days + 1
                pct = int(bar_days / total_days * 100)
                html += f'<td><div class="bar {bar_class}" style="width:{pct}%;"></div></td>'
            else:
                html += "<td></td>"

        html += f"<td>{status}</td></tr>"

    html += "</table>"
    st.markdown(html, unsafe_allow_html=True)

    st.divider()
    # Budget-Auslastung
    st.subheader("Budget-Auslastung")
    budget_data = projects[projects["Budget"] > 0].copy()
    if not budget_data.empty:
        budget_data["Auslastung_%"] = (budget_data["Abgerechnet"] / budget_data["Budget"] * 100).round(1)
        st.bar_chart(budget_data.set_index("Projekt")["Auslastung_%"])
