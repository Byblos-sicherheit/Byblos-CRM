import os
import sqlite3
import hashlib
import secrets
import shutil
import zipfile
import smtplib
import json
import re
import io
import pdfplumber

try:
    import pytesseract
except Exception:
    pytesseract = None

try:
    from pdf2image import convert_from_bytes
except Exception:
    convert_from_bytes = None

try:
    from PIL import Image as PILImage
except Exception:
    PILImage = None

from email.message import EmailMessage
from datetime import date, datetime, timedelta
from pathlib import Path

import pandas as pd
import streamlit as st
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfbase.pdfmetrics import stringWidth
from extensions_complete_system import (
    register_complete_system,
    register_systemplus,
    page_bulk_invoice_import,
    page_quick_search_ai,
    page_company_profiles,
    page_contracts_documents,
    page_systemplus_cockpit,
    page_compliance_center,
    page_export_backup_center,
)
from extensions_liveops import (
    register_liveops,
    page_liveops_cockpit,
    page_role_permissions_matrix,
    page_customer_portal_prep,
    page_service_checklists,
)
from extensions_fieldops import (
    register_fieldops,
    page_fieldops_cockpit,
    page_employees_field,
    page_objects_field,
    page_shift_planner,
    page_service_reports,
    page_fieldops_exports,
)
from extensions_einvoice_time import (
    register_einvoice_time,
    page_einvoice_center,
    page_time_tracking,
)
from extensions_finance_time_ops import (
    register_finance_time_ops,
    page_payments_reminders,
    page_einvoice_validation,
    page_time_approval_billing,
)
from extensions_payroll_recon_ops import (
    register_payroll_recon_ops,
    page_open_items_control,
    page_time_accounts_absences,
    page_ops_quality_checks,
)

# Import the machine learning helpers.  These provide functions to
# classify text and to store new examples when the user confirms a match.
try:
    # Attempt relative import when running as part of a package.
    from .ml_logic import predict_category, add_training_example
except Exception:
    # Fallback to absolute import when executed as a script.  The
    # directory containing this file is added to sys.path so that
    # ``ml_logic.py`` can be found.
    import sys as _sys
    from pathlib import Path as _Path
    _base_dir = _Path(__file__).resolve().parent
    if str(_base_dir) not in _sys.path:
        _sys.path.append(str(_base_dir))
    from ml_logic import predict_category, add_training_example

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "byblos_crm.db"
INVOICE_DIR = BASE_DIR / "generated" / "invoices"
IMPORT_DIR = BASE_DIR / "imports"
ASSET_DIR = BASE_DIR / "assets"
INVOICE_DIR.mkdir(parents=True, exist_ok=True)
IMPORT_DIR.mkdir(parents=True, exist_ok=True)
ASSET_DIR.mkdir(parents=True, exist_ok=True)

COMPANY = {
    "name": "Byblos Sicherheitsdienst & Service",
    "street": "Hauptstr 19",
    "city": "38474 Tuelau",
    "country": "Deutschland",
    "phone": "+49 (0) 176 42988324",
    "email": "info@byblos-sicherheit.de",
    "website": "https://byblos-sicherheit.de",
    "ust": "DE364648388",
    "bank": "Sparkasse",
    "iban": "DE83 2695 1311 0162 7691 52",
    "bic": "NOLADE21GFW",
}

STATUS = ["offen", "bezahlt", "ueberfaellig", "storniert"]
CONTACT_TYPES = ["Telefon", "E-Mail", "WhatsApp", "Termin", "Notiz"]
SHIFT_TYPES = ["Tag", "Nacht", "Event", "Objektschutz", "Reinigung", "Hausmeister", "Sonstiges"]
EXPENSE_STATUS = ["offen", "bezahlt", "teilbezahlt", "storniert"]
EXPENSE_PAYMENT = ["Überweisung", "Bar", "EC/Kreditkarte", "Lastschrift", "PayPal", "Sonstiges"]
BWA_CATEGORIES = [
    "4000 Wareneinsatz / Fremdleistungen",
    "4100 Personal / Löhne",
    "4200 Raumkosten / Miete",
    "4300 Versicherungen / Beiträge",
    "4400 Fahrzeugkosten",
    "4500 Werbung / Marketing",
    "4600 Reisekosten / Verpflegung",
    "4700 Bürobedarf / Telefon / Software",
    "4800 Rechts- und Beratungskosten",
    "4900 Sonstige betriebliche Aufwendungen",
    "1576 Vorsteuer 19%",
    "1571 Vorsteuer 7%"
]

st.set_page_config(
    page_title="Byblos CRM",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        "Get Help": "mailto:info@byblos-sicherheit.de",
        "Report a bug": "mailto:info@byblos-sicherheit.de",
        "About": "**Byblos CRM v2.0**\nByblos Sicherheitsdienst & Service\nhttps://byblos-sicherheit.de",
    },
)


def conn():
    return sqlite3.connect(DB_PATH, check_same_thread=False)


def run(sql, params=()):
    with conn() as c:
        cur = c.execute(sql, params)
        c.commit()
        return cur


def df(sql, params=()):
    with conn() as c:
        return pd.read_sql_query(sql, c, params=params)


def init_db():
    run("""
    CREATE TABLE IF NOT EXISTS customers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        customer_no TEXT UNIQUE,
        company TEXT NOT NULL,
        contact_person TEXT,
        email TEXT,
        phone TEXT,
        street TEXT,
        zip_city TEXT,
        country TEXT DEFAULT 'Deutschland',
        notes TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )""")
    run("""
    CREATE TABLE IF NOT EXISTS contacts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        customer_id INTEGER NOT NULL,
        contact_date TEXT NOT NULL,
        contact_type TEXT NOT NULL,
        subject TEXT,
        note TEXT,
        next_followup TEXT,
        FOREIGN KEY(customer_id) REFERENCES customers(id)
    )""")
    run("""
    CREATE TABLE IF NOT EXISTS invoices (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        invoice_no TEXT UNIQUE,
        customer_id INTEGER NOT NULL,
        invoice_date TEXT NOT NULL,
        service_date TEXT,
        due_date TEXT,
        description TEXT,
        net_total REAL DEFAULT 0,
        vat_rate REAL DEFAULT 19,
        vat_total REAL DEFAULT 0,
        gross_total REAL DEFAULT 0,
        paid_amount REAL DEFAULT 0,
        paid_date TEXT,
        status TEXT DEFAULT 'offen',
        pdf_path TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(customer_id) REFERENCES customers(id)
    )""")
    run("""
    CREATE TABLE IF NOT EXISTS invoice_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        invoice_id INTEGER NOT NULL,
        position INTEGER,
        description TEXT NOT NULL,
        quantity REAL DEFAULT 1,
        unit TEXT DEFAULT 'Stunden',
        unit_price REAL DEFAULT 0,
        total REAL DEFAULT 0,
        FOREIGN KEY(invoice_id) REFERENCES invoices(id)
    )""")
    run("""
    CREATE TABLE IF NOT EXISTS employees (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        employee_no TEXT UNIQUE,
        name TEXT NOT NULL,
        phone TEXT,
        email TEXT,
        hourly_rate REAL DEFAULT 0,
        active INTEGER DEFAULT 1,
        notes TEXT
    )""")
    run("""
    CREATE TABLE IF NOT EXISTS shifts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        shift_date TEXT NOT NULL,
        start_time TEXT NOT NULL,
        end_time TEXT NOT NULL,
        employee_id INTEGER,
        customer_id INTEGER,
        location TEXT,
        shift_type TEXT,
        status TEXT DEFAULT 'geplant',
        notes TEXT,
        FOREIGN KEY(employee_id) REFERENCES employees(id),
        FOREIGN KEY(customer_id) REFERENCES customers(id)
    )""")
    run("""
    CREATE TABLE IF NOT EXISTS suppliers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        supplier_no TEXT UNIQUE,
        name TEXT NOT NULL,
        contact_person TEXT,
        email TEXT,
        phone TEXT,
        street TEXT,
        zip_city TEXT,
        tax_no TEXT,
        notes TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )""")
    run("""
    CREATE TABLE IF NOT EXISTS expenses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        expense_no TEXT UNIQUE,
        receipt_no TEXT,
        supplier_id INTEGER,
        expense_date TEXT NOT NULL,
        due_date TEXT,
        paid_date TEXT,
        description TEXT NOT NULL,
        category TEXT,
        net_amount REAL DEFAULT 0,
        vat_rate REAL DEFAULT 19,
        vat_amount REAL DEFAULT 0,
        gross_amount REAL DEFAULT 0,
        paid_amount REAL DEFAULT 0,
        payment_method TEXT,
        status TEXT DEFAULT 'offen',
        receipt_path TEXT,
        bwa_month TEXT,
        notes TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(supplier_id) REFERENCES suppliers(id)
    )""")
    run("""
    CREATE TABLE IF NOT EXISTS expense_categories (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        category TEXT UNIQUE,
        bwa_group TEXT,
        tax_hint TEXT
    )""")
    run("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        role TEXT NOT NULL DEFAULT 'Admin',
        active INTEGER DEFAULT 1,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )""")
    run("""
    CREATE TABLE IF NOT EXISTS bank_transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        booking_date TEXT,
        value_date TEXT,
        payer_payee TEXT,
        purpose TEXT,
        amount REAL DEFAULT 0,
        currency TEXT DEFAULT 'EUR',
        matched_type TEXT,
        matched_id INTEGER,
        status TEXT DEFAULT 'neu',
        source_file TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )""")
    run("""
    CREATE TABLE IF NOT EXISTS audit_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ts TEXT DEFAULT CURRENT_TIMESTAMP,
        username TEXT,
        action TEXT,
        details TEXT
    )""")
    run("""
    CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value TEXT
    )""")
    run("""
    CREATE TABLE IF NOT EXISTS archive_documents (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        doc_type TEXT,
        ref_no TEXT,
        file_name TEXT,
        file_path TEXT,
        sha256 TEXT,
        archived_at TEXT DEFAULT CURRENT_TIMESTAMP,
        locked INTEGER DEFAULT 1,
        note TEXT
    )""")
    run("""
    CREATE TABLE IF NOT EXISTS email_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        sent_at TEXT,
        recipient TEXT,
        subject TEXT,
        body TEXT,
        attachment_path TEXT,
        status TEXT DEFAULT 'Entwurf',
        error TEXT
    )""")
    run("""
    CREATE TABLE IF NOT EXISTS backups (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        file_path TEXT,
        file_size INTEGER,
        sha256 TEXT,
        note TEXT
    )""")
    run("""
    CREATE TABLE IF NOT EXISTS automation_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        job_name TEXT,
        status TEXT,
        details TEXT
    )""")
    run("""
    CREATE TABLE IF NOT EXISTS daily_kpis (
        kpi_date TEXT PRIMARY KEY,
        revenue_month REAL DEFAULT 0,
        paid_month REAL DEFAULT 0,
        expense_month REAL DEFAULT 0,
        open_invoices REAL DEFAULT 0,
        overdue_invoices REAL DEFAULT 0,
        profit_month REAL DEFAULT 0,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )""")
    run("""
    CREATE TABLE IF NOT EXISTS imports (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        file_name TEXT NOT NULL,
        invoice_no TEXT,
        customer_hint TEXT,
        amount_hint REAL,
        import_status TEXT DEFAULT 'neu',
        note TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )""")
    run("""
    CREATE TABLE IF NOT EXISTS import_queue (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        import_type TEXT NOT NULL,
        source_file TEXT,
        raw_data TEXT,
        detected_target TEXT,
        detected_id INTEGER,
        confidence REAL DEFAULT 0,
        action TEXT DEFAULT 'pruefen',
        status TEXT DEFAULT 'neu',
        reason TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        processed_at TEXT
    )""")
    run("""
    CREATE TABLE IF NOT EXISTS matching_rules (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        rule_type TEXT NOT NULL,
        pattern TEXT NOT NULL,
        target_type TEXT NOT NULL,
        target_id INTEGER,
        category TEXT,
        confidence REAL DEFAULT 95,
        active INTEGER DEFAULT 1,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        note TEXT
    )""")
    run("""
    CREATE TABLE IF NOT EXISTS import_dedup (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        fingerprint TEXT UNIQUE,
        import_type TEXT,
        source_file TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )""")
    # register_complete_system(run, df)  # moved to try/except
    # register_systemplus moved to try/except block below
    # register_liveops(run, df)  # moved to try/except
    # register_fieldops(run, df)  # moved to try/except
    # register_einvoice_time(run, df)  # moved to try/except
    # register_finance_time_ops(run, df)  # moved to try/except
    # register_payroll_recon_ops(run, df)  # moved to try/except
    try:
        from extensions_v2_enhancements import register_all_v2
        register_all_v2(run, df)
    except Exception:
        pass
    try:
        from extensions_v2_new1 import register_new1
        register_new1(run, df)
    except Exception:
        pass
    try:
        from extensions_v2_new2 import register_new2
        register_new2(run, df)
    except Exception:
        pass
    try:
        from extensions_v2_new3 import register_new3
        register_new3(run, df)
    except Exception:
        pass
    try:
        from extensions_v2_new4 import register_new4
        register_new4(run, df)
    except Exception:
        pass
    try:
        from extensions_v2_new5 import register_new5
        register_new5(run, df)
    except Exception:
        pass
    try:
        from extensions_v2_prod2 import register_prod2
        register_prod2(run, df)
    except Exception:
        pass
    try:
        from extensions_v2_ultra import register_ultra
        register_ultra(run, df)
    except Exception:
        pass
    try:
        from extensions_v2_complete import register_complete
        register_complete(run, df)
    except Exception:
        pass
    try:
        from extensions_v2_systemplus import register_systemplus
        register_systemplus(run, df)
    except Exception:
        pass
    try:
        from extensions_v2_xtra import register_xtra
        register_xtra(run, df)
    except Exception:
        pass
    try:
        from extensions_v2_liveops import register_liveops
        register_liveops(run, df)
    except Exception:
        pass
    try:
        from extensions_v2_security import register_security
        register_security(run, df)
    except Exception:
        pass
    try:
        from extensions_v2_fieldops import register_fieldops
        register_fieldops(run, df)
    except Exception:
        pass
    try:
        from extensions_v2_automation_ops import register_automation
        register_automation(run, df)
    except Exception:
        pass
    try:
        from extensions_v2_payroll_recon_ops import register_payroll_recon
        register_payroll_recon(run, df)
    except Exception:
        pass
    try:
        from extensions_v2_einvoice_time import register_einvoice_time
        register_einvoice_time(run, df)
    except Exception:
        pass
    try:
        from extensions_v2_fieldops_extra import register_fieldops_extra
        register_fieldops_extra(run, df)
    except Exception:
        pass
    try:
        from extensions_v2_liveops_extra import register_liveops_extra
        register_liveops_extra(run, df)
    except Exception:
        pass
    try:
        from extensions_v2_business_ops import register_business_ops
        register_business_ops(run, df)
    except Exception:
        pass
    seed_if_empty()


def hash_password(password):
    salt = secrets.token_hex(16)
    digest = hashlib.sha256((salt + password).encode('utf-8')).hexdigest()
    return f"{salt}${digest}"

def verify_password(password, stored):
    try:
        salt, digest = stored.split('$', 1)
        return hashlib.sha256((salt + password).encode('utf-8')).hexdigest() == digest
    except Exception:
        return False

def current_user():
    return st.session_state.get('user')

def require_role(allowed):
    user = current_user()
    return bool(user and user.get('role') in allowed)

def log_action(action, details=''):
    user = current_user() or {}
    try:
        run("INSERT INTO audit_log(username,action,details) VALUES(?,?,?)", (user.get('username','system'), action, details))
    except Exception:
        pass

def seed_if_empty():
    if df("SELECT COUNT(*) AS n FROM users").iloc[0]["n"] == 0:
        run("INSERT INTO users(username,password_hash,role,active) VALUES(?,?,?,1)", ('admin', hash_password('admin123'), 'Admin'))
    if df("SELECT COUNT(*) AS n FROM expense_categories").iloc[0]["n"] == 0:
        for cat in BWA_CATEGORIES:
            run("INSERT OR IGNORE INTO expense_categories(category,bwa_group,tax_hint) VALUES(?,?,?)", (cat, cat.split(" ",1)[-1] if " " in cat else cat, "für BWA/Steuerberater prüfen"))
    smtp_defaults = {
        'smtp_host': 'mail.byblos-sicherheit.de',
        'smtp_port': '465',
        'smtp_user': 'info@byblos-sicherheit.de',
        'smtp_sender': 'info@byblos-sicherheit.de',
        'smtp_ssl': '1',
        'company_email': 'info@byblos-sicherheit.de',
        'auto_reminder_days_after_due': '1',
        'auto_send_reminders': '0',
        'backup_cloud_path': '',
    }
    for k, v in smtp_defaults.items():
        if df("SELECT value FROM settings WHERE key=?", (k,)).empty:
            run("INSERT INTO settings(key,value) VALUES(?,?)", (k, v))
    if df("SELECT COUNT(*) AS n FROM customers").iloc[0]["n"] == 0:
        customers = [
            ("SD-001", "Ralf Grimm", "Herr Grimm", "", "", "Schuetzenfest", "38465 Altendorf", "Deutschland", "Import aus alter Rechnung"),
            ("SD-002", "ToSa Security & Service GmbH u. Co. KG", "Nadine El Sayed", "", "+49 (0) 176 42988324", "Hamburgerstr. 2b", "30880 Laatzen", "Deutschland", "Stammkunde Events/Messe"),
            ("SD-0004", "KOETTER SE & Co. KG Security, Hamburg", "Nadine El Sayed", "", "+49 (0) 176 42988324", "Pelikanplatz 33", "30177 Hannover", "Deutschland", "Stammkunde"),
            ("SD-0005", "LIGANOVA GMBH", "Stefan Henske", "", "", "Herdweg 59", "70174 Stuttgart", "Deutschland", "Import aus alter Rechnung"),
        ]
        for c in customers:
            run("""INSERT INTO customers(customer_no, company, contact_person, email, phone, street, zip_city, country, notes)
                   VALUES(?,?,?,?,?,?,?,?,?)""", c)
    if df("SELECT COUNT(*) AS n FROM employees").iloc[0]["n"] == 0:
        for e in [("MA-001", "Fadl Allah El Sayed", "", "", 0, 1, ""), ("MA-002", "Nadine El Sayed", "", "", 0, 1, "")]:
            run("INSERT INTO employees(employee_no,name,phone,email,hourly_rate,active,notes) VALUES(?,?,?,?,?,?,?)", e)
    if df("SELECT COUNT(*) AS n FROM invoices").iloc[0]["n"] == 0:
        old = [
            ("RE-0001", "SD-001", "2024-05-26", "2024-05-25", "Schuetzenfest", 552.00, 656.88),
            ("RE-0002", "SD-002", "2024-06-04", "20.04.2024-26.04.2024", "Messe Hannover", 3264.83, 3885.14),
            ("RE-0003", "SD-002", "2024-06-18", "2024-06-13", "Ideen Expo Hannover", 483.00, 574.77),
            ("RE-0004", "SD-0005", "2024-07-08", "2024-06-30", "Bewachung Tuelau", 301.30, 358.55),
            ("RE-0006", "SD-0004", "2024-07-03", "Juli 2024", "Sicherheitskraefte", 2540.00, 3022.60),
            ("RE-0010", "SD-002", "2024-08-06", "Juli 2024", "Bruce Springsteen", 2409.75, 2867.60),
            ("RE-0012", "SD-002", "2024-08-08", "Juli 2024", "ACDC", 4530.75, 5391.59),
            ("RE-0015", "SD-0004", "2024-09-09", "August 2024", "Sicherheitskraefte", 5069.40, 6032.59),
            ("RE-0021", "SD-002", "2024-10-04", "September 2024", "Messe IAA", 13112.14, 15603.44),
            ("RE-0025", "SD-0004", "2024-10-04", "September 2024", "Neue Land Str. 6", 9387.00, 11170.53),
        ]
        for inv_no, cust_no, inv_date, service, desc, net, gross in old:
            cust = df("SELECT id FROM customers WHERE customer_no=?", (cust_no,))
            if not cust.empty:
                cid = int(cust.iloc[0]["id"])
                due = (datetime.strptime(inv_date, "%Y-%m-%d").date() + timedelta(days=14)).isoformat()
                vat = round(gross - net, 2)
                run("""INSERT INTO invoices(invoice_no,customer_id,invoice_date,service_date,due_date,description,net_total,vat_rate,vat_total,gross_total,status)
                       VALUES(?,?,?,?,?,?,?,?,?,?,?)""", (inv_no, cid, inv_date, service, due, desc, net, 19, vat, gross, "offen"))


def next_number(table, col, prefix):
    data = df(f"SELECT {col} FROM {table} WHERE {col} LIKE ? ORDER BY {col} DESC LIMIT 1", (f"{prefix}%",))
    if data.empty or not data.iloc[0][col]:
        return f"{prefix}0001"
    raw = str(data.iloc[0][col]).replace(prefix, "").replace("-", "")
    try:
        n = int(raw) + 1
    except ValueError:
        n = 1
    if prefix.endswith("-"):
        return f"{prefix}{n:04d}"
    return f"{prefix}{n:04d}"


def refresh_invoice_totals(invoice_id):
    items = df("SELECT COALESCE(SUM(total),0) AS net FROM invoice_items WHERE invoice_id=?", (invoice_id,))
    net = float(items.iloc[0]["net"])
    inv = df("SELECT vat_rate, paid_amount, due_date FROM invoices WHERE id=?", (invoice_id,))
    vat_rate = float(inv.iloc[0]["vat_rate"] or 19)
    paid = float(inv.iloc[0]["paid_amount"] or 0)
    due_date = inv.iloc[0]["due_date"]
    vat = round(net * vat_rate / 100, 2)
    gross = round(net + vat, 2)
    status = "bezahlt" if paid >= gross and gross > 0 else "offen"
    if status == "offen" and due_date:
        try:
            if datetime.strptime(due_date, "%Y-%m-%d").date() < date.today():
                status = "ueberfaellig"
        except Exception:
            pass
    run("UPDATE invoices SET net_total=?, vat_total=?, gross_total=?, status=? WHERE id=?", (net, vat, gross, status, invoice_id))



def refresh_expense_totals(expense_id):
    exp = df("SELECT net_amount, vat_rate, paid_amount, due_date FROM expenses WHERE id=?", (expense_id,))
    if exp.empty:
        return
    row = exp.iloc[0]
    net = float(row["net_amount"] or 0)
    vat_rate = float(row["vat_rate"] or 0)
    paid = float(row["paid_amount"] or 0)
    vat = round(net * vat_rate / 100, 2)
    gross = round(net + vat, 2)
    if paid <= 0:
        status = "offen"
    elif paid < gross:
        status = "teilbezahlt"
    else:
        status = "bezahlt"
    run("UPDATE expenses SET vat_amount=?, gross_amount=?, status=? WHERE id=?", (vat, gross, status, expense_id))

def save_uploaded_receipt(uploaded_file):
    if not uploaded_file:
        return None
    receipt_dir = BASE_DIR / "generated" / "receipts"
    receipt_dir.mkdir(parents=True, exist_ok=True)
    safe = uploaded_file.name.replace("/", "_").replace("\\", "_")
    target = receipt_dir / f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{safe}"
    target.write_bytes(uploaded_file.read())
    return str(target)

def generate_invoice_pdf(invoice_id):
    inv = df("""SELECT i.*, c.customer_no,c.company,c.contact_person,c.street,c.zip_city,c.country,c.email,c.phone
                FROM invoices i JOIN customers c ON c.id=i.customer_id WHERE i.id=?""", (invoice_id,))
    if inv.empty:
        return None
    inv = inv.iloc[0]
    items = df("SELECT position, description, quantity, unit, unit_price, total FROM invoice_items WHERE invoice_id=? ORDER BY position", (invoice_id,))
    path = INVOICE_DIR / f"{inv['invoice_no']}.pdf"

    # Firmendaten bevorzugt aus Settings (editierbar über Einstellungen)
    co_name  = get_setting("company_name",    COMPANY.get("name", ""))
    co_street= get_setting("company_street",  COMPANY.get("street", ""))
    co_zip   = get_setting("company_zip_city",COMPANY.get("city", ""))
    co_phone = get_setting("company_phone",   COMPANY.get("phone", ""))
    co_email = get_setting("company_email",   COMPANY.get("email", ""))
    co_web   = get_setting("company_web",     COMPANY.get("website", ""))
    co_iban  = get_setting("company_iban",    COMPANY.get("iban", ""))
    co_bic   = get_setting("company_bic",     COMPANY.get("bic", ""))
    co_bank  = get_setting("company_bank",    COMPANY.get("bank", ""))
    co_ust   = get_setting("company_ust_id",  COMPANY.get("ust", ""))
    co_tax   = get_setting("company_tax_no",  COMPANY.get("tax_no", ""))

    doc = SimpleDocTemplate(str(path), pagesize=A4, rightMargin=18*mm, leftMargin=18*mm, topMargin=14*mm, bottomMargin=14*mm)
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="Small", fontSize=8, leading=10))
    styles.add(ParagraphStyle(name="SmallBold", fontSize=8, leading=10, fontName="Helvetica-Bold"))
    styles.add(ParagraphStyle(name="H", fontSize=18, leading=22, textColor=colors.HexColor("#0f172a"), spaceAfter=12))
    story = []

    # Kopfzeile: Logo links, Firmenname rechts
    logo = ASSET_DIR / "logo.png"
    head_left = Paragraph(
        f"<b>{co_name}</b><br/>{co_street}<br/>{co_zip}<br/>"
        f"Tel: {co_phone}<br/>{co_email}<br/>{co_web}",
        styles["Small"]
    )
    if logo.exists():
        head_right = Image(str(logo), width=42*mm, height=22*mm)
    else:
        head_right = Paragraph(f"<b>{co_name}</b>", styles["H"])

    t = Table([[head_left, head_right]], colWidths=[110*mm, 55*mm])
    t.setStyle(TableStyle([("VALIGN", (0,0), (-1,-1), "TOP"), ("ALIGN", (1,0), (1,0), "RIGHT")]))
    story.append(t)
    story.append(Spacer(1, 10*mm))

    # Empfängeradresse & Rechnungsmeta
    addr = (f"<b>{inv['company']}</b><br/>"
            f"{inv.get('contact_person') or ''}<br/>"
            f"{inv.get('street') or ''}<br/>"
            f"{inv.get('zip_city') or ''}<br/>"
            f"{inv.get('country') or ''}")
    status_text = str(inv.get("status", "")).upper()
    meta = (f"<b>RECHNUNG</b><br/>"
            f"Rechnungsnummer: <b>{inv['invoice_no']}</b><br/>"
            f"Kundennummer: {inv['customer_no']}<br/>"
            f"Rechnungsdatum: {inv['invoice_date']}<br/>"
            f"Leistungsdatum: {inv.get('service_date') or ''}<br/>"
            f"Fällig bis: <b>{inv.get('due_date') or ''}</b><br/>"
            f"Status: {status_text}")
    story.append(Table([[Paragraph(addr, styles["Normal"]), Paragraph(meta, styles["Normal"])]], colWidths=[95*mm, 70*mm]))
    story.append(Spacer(1, 8*mm))

    # Anredetext
    story.append(Paragraph(
        f"Sehr geehrte Damen und Herren,<br/>"
        f"vielen Dank für Ihr Vertrauen. Wir stellen Ihnen folgende Leistungen in Rechnung:<br/>"
        f"<b>{inv.get('description') or ''}</b>",
        styles["Normal"]
    ))
    story.append(Spacer(1, 6*mm))

    # Positionstabelle
    rows = [["Pos.", "Bezeichnung", "Menge", "Einheit", "Einzelpreis", "Gesamt"]]
    for _, r in items.iterrows():
        rows.append([
            int(r["position"] or 0), r["description"],
            f"{float(r['quantity']):.2f}", r["unit"],
            f"{float(r['unit_price']):.2f} €", f"{float(r['total']):.2f} €"
        ])
    # Summenzeilen
    rows += [
        ["", "", "", "", "Nettobetrag", f"{float(inv['net_total']):.2f} €"],
        ["", "", "", "", f"MwSt. {float(inv['vat_rate']):.0f} %", f"{float(inv['vat_total']):.2f} €"],
        ["", "", "", "", "Rechnungsbetrag", f"{float(inv['gross_total']):.2f} €"],
    ]
    if float(inv.get("paid_amount") or 0) > 0:
        rows.append(["", "", "", "", "Bereits bezahlt", f"{float(inv['paid_amount']):.2f} €"])
        rest = float(inv["gross_total"]) - float(inv["paid_amount"])
        rows.append(["", "", "", "", "Noch zu zahlen", f"{rest:.2f} €"])

    table = Table(rows, colWidths=[12*mm, 72*mm, 16*mm, 18*mm, 28*mm, 28*mm])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#1a2744")),
        ("TEXTCOLOR", (0,0), (-1,0), colors.white),
        ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
        ("GRID", (0,0), (-1,-1), 0.25, colors.HexColor("#cbd5e1")),
        ("ALIGN", (2,1), (-1,-1), "RIGHT"),
        ("FONTNAME", (4,-3), (-1,-1), "Helvetica-Bold"),
        ("BACKGROUND", (4,-1), (-1,-1), colors.HexColor("#1a2744")),
        ("TEXTCOLOR", (4,-1), (-1,-1), colors.white),
        ("BACKGROUND", (4,-3), (-1,-2), colors.HexColor("#e2e8f0")),
        ("ROWBACKGROUNDS", (0,1), (-1,-4), [colors.white, colors.HexColor("#f8fafc")]),
    ]))
    story.append(table)
    story.append(Spacer(1, 8*mm))

    # Bankverbindung & Fußzeile
    story.append(Paragraph(
        f"Bitte überweisen Sie den Gesamtbetrag innerhalb der Zahlungsfrist "
        f"unter Angabe der Rechnungsnummer <b>{inv['invoice_no']}</b> als Verwendungszweck.<br/><br/>"
        f"Bankverbindung: {co_bank}<br/>"
        f"IBAN: <b>{co_iban}</b>  |  BIC: {co_bic}<br/>"
        f"USt.-IdNr.: {co_ust}  |  Steuernummer: {co_tax}",
        styles["Small"]
    ))
    story.append(Spacer(1, 8*mm))
    story.append(Paragraph("Mit freundlichen Grüßen<br/><b>" + co_name + "</b>", styles["Normal"]))

    doc.build(story)
    run("UPDATE invoices SET pdf_path=? WHERE id=?", (str(path), invoice_id))
    return path
    run("UPDATE invoices SET pdf_path=? WHERE id=?", (str(path), invoice_id))
    archive_file(path, "Rechnung", str(inv["invoice_no"]), "PDF-Export Rechnung")
    return path


def style():
    st.markdown("""
    <style>
    .block-container {padding-top: 1.2rem; padding-bottom: 1rem;}
    div[data-testid="stMetric"] {
        background: #1a1f2e;
        border: 1px solid #2d3142;
        border-radius: 12px;
        padding: 14px 18px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.35);
    }
    div[data-testid="stMetricValue"] { color: #e8eaf0 !important; font-weight: 700; }
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0d1117 0%, #151b26 100%);
        border-right: 1px solid #2d3142;
    }
    .stButton > button {
        border-radius: 6px; font-weight: 600;
        transition: all 0.18s ease;
    }
    .stButton > button:hover {
        transform: translateY(-1px);
        box-shadow: 0 4px 14px rgba(192,57,43,0.35);
    }
    [data-testid="stDataFrame"] { border-radius: 8px; overflow: hidden; }
    .byblos-alert-danger  { background:rgba(192,57,43,0.15); border-left:4px solid #c0392b; padding:10px 14px; border-radius:4px; margin-bottom:6px; }
    .byblos-alert-warning { background:rgba(243,156,18,0.15); border-left:4px solid #f39c12; padding:10px 14px; border-radius:4px; margin-bottom:6px; }
    .byblos-alert-success { background:rgba(39,174,96,0.15);  border-left:4px solid #27ae60; padding:10px 14px; border-radius:4px; margin-bottom:6px; }
    .badge-red    { background:#c0392b; color:#fff; padding:2px 8px; border-radius:12px; font-size:.75rem; font-weight:700; }
    .badge-orange { background:#e67e22; color:#fff; padding:2px 8px; border-radius:12px; font-size:.75rem; font-weight:700; }
    .badge-green  { background:#27ae60; color:#fff; padding:2px 8px; border-radius:12px; font-size:.75rem; font-weight:700; }
    .badge-blue   { background:#2980b9; color:#fff; padding:2px 8px; border-radius:12px; font-size:.75rem; font-weight:700; }
    @media print { [data-testid="stSidebar"], .stButton { display:none!important; } }
    </style>
    """, unsafe_allow_html=True)


def export_excel():
    path = BASE_DIR / "byblos_crm_export.xlsx"
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        for name, query in {
            "Kunden": "SELECT * FROM customers",
            "Kontakthistorie": "SELECT * FROM contacts",
            "Rechnungen": "SELECT * FROM invoices",
            "Rechnungspositionen": "SELECT * FROM invoice_items",
            "Mitarbeiter": "SELECT * FROM employees",
            "Dienstplan": "SELECT * FROM shifts",
            "Lieferanten": "SELECT * FROM suppliers",
            "Ausgaben_BWA": "SELECT * FROM expenses",
            "BWA_Kategorien": "SELECT * FROM expense_categories",
            "Importe": "SELECT * FROM imports",
            "Banktransaktionen": "SELECT * FROM bank_transactions",
            "Benutzer": "SELECT id,username,role,active,created_at FROM users",
            "Audit_Log": "SELECT * FROM audit_log",
        }.items():
            df(query).to_excel(writer, sheet_name=name, index=False)
    return path



def sha256_file(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def get_setting(key, default=''):
    data = df("SELECT value FROM settings WHERE key=?", (key,))
    return default if data.empty else str(data.iloc[0]['value'] or '')


def set_setting(key, value):
    run("INSERT OR REPLACE INTO settings(key,value) VALUES(?,?)", (key, str(value)))


def archive_file(source_path, doc_type, ref_no='', note=''):
    source = Path(source_path)
    if not source.exists():
        return None
    archive_dir = BASE_DIR / 'archive' / doc_type / datetime.now().strftime('%Y-%m')
    archive_dir.mkdir(parents=True, exist_ok=True)
    safe_name = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{source.name}".replace(' ', '_')
    target = archive_dir / safe_name
    shutil.copy2(source, target)
    digest = sha256_file(target)
    run("INSERT INTO archive_documents(doc_type,ref_no,file_name,file_path,sha256,note) VALUES(?,?,?,?,?,?)", (doc_type, ref_no, target.name, str(target), digest, note))
    log_action('archive_file', f'{doc_type} {ref_no} {target.name}')
    return target


def create_full_backup(note='manuell'):
    backup_dir = BASE_DIR / 'backups'
    backup_dir.mkdir(parents=True, exist_ok=True)
    out = backup_dir / f"byblos_crm_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
    with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED) as z:
        for rel in ['byblos_crm.db', 'generated', 'imports', 'assets', 'archive']:
            item = BASE_DIR / rel
            if item.is_file():
                z.write(item, item.name)
            elif item.exists():
                for f in item.rglob('*'):
                    if f.is_file():
                        z.write(f, f.relative_to(BASE_DIR))
    digest = sha256_file(out)
    run("INSERT INTO backups(file_path,file_size,sha256,note) VALUES(?,?,?,?)", (str(out), out.stat().st_size, digest, note))
    log_action('backup_created', out.name)
    return out


def queue_email(recipient, subject, body, attachment_path=''):
    run("INSERT INTO email_log(recipient,subject,body,attachment_path,status) VALUES(?,?,?,?,?)", (recipient, subject, body, attachment_path, 'Entwurf'))
    log_action('email_queued', f'{recipient} | {subject}')


def send_email_smtp(email_id):
    row = df("SELECT * FROM email_log WHERE id=?", (email_id,))
    if row.empty:
        return 'E-Mail nicht gefunden.'
    r = row.iloc[0]
    host = get_setting('smtp_host')
    port = int(get_setting('smtp_port', '587') or 587)
    user = get_setting('smtp_user')
    password = get_setting('smtp_password')
    sender = get_setting('smtp_sender', COMPANY['email'])
    if not host or not user or not password:
        return 'SMTP ist nicht vollständig eingerichtet. In Einstellungen zuerst SMTP-Daten speichern.'
    msg = EmailMessage()
    msg['From'] = sender
    msg['To'] = r['recipient']
    msg['Subject'] = r['subject']
    msg.set_content(r['body'] or '')
    att = str(r['attachment_path'] or '')
    if att and Path(att).exists():
        p = Path(att)
        msg.add_attachment(p.read_bytes(), maintype='application', subtype='octet-stream', filename=p.name)
    try:
        use_ssl = get_setting('smtp_ssl', '1') == '1' or port == 465
        if use_ssl:
            with smtplib.SMTP_SSL(host, port) as smtp:
                smtp.login(user, password)
                smtp.send_message(msg)
        else:
            with smtplib.SMTP(host, port) as smtp:
                smtp.starttls()
                smtp.login(user, password)
                smtp.send_message(msg)
        run("UPDATE email_log SET status='Gesendet', sent_at=CURRENT_TIMESTAMP, error='' WHERE id=?", (email_id,))
        log_action('email_sent', str(email_id))
        return 'E-Mail gesendet.'
    except Exception as e:
        run("UPDATE email_log SET status='Fehler', error=? WHERE id=?", (str(e), email_id))
        return f'Fehler beim Versand: {e}'


def automation_log(job_name, status, details=''):
    run("INSERT INTO automation_log(job_name,status,details) VALUES(?,?,?)", (job_name, status, details))
    log_action(f'automation_{job_name}', f'{status}: {details}')


def mark_overdue_invoices():
    today = date.today().isoformat()
    run("""UPDATE invoices
           SET status='ueberfaellig'
           WHERE status='offen' AND due_date IS NOT NULL AND due_date < ?
             AND COALESCE(paid_amount,0) < COALESCE(gross_total,0)""", (today,))
    n = int(df("SELECT COUNT(*) AS n FROM invoices WHERE status='ueberfaellig'").iloc[0]['n'])
    automation_log('mark_overdue', 'ok', f'{n} überfällige Rechnungen markiert/gefunden')
    return n


def queue_overdue_reminders(send_now=False):
    days = int(get_setting('auto_reminder_days_after_due', '1') or 1)
    cutoff = (date.today() - timedelta(days=days)).isoformat()
    overdue = df("""SELECT i.*, c.company, c.email
                    FROM invoices i JOIN customers c ON c.id=i.customer_id
                    WHERE i.status='ueberfaellig'
                      AND i.due_date <= ?
                      AND COALESCE(i.paid_amount,0) < COALESCE(i.gross_total,0)""", (cutoff,))
    created = 0
    sent = 0
    for _, r in overdue.iterrows():
        if not str(r['email'] or '').strip():
            continue
        already = df("SELECT id FROM email_log WHERE subject LIKE ? AND status IN ('Entwurf','Gesendet')", (f"%{r['invoice_no']}%Mahnung%",))
        if not already.empty:
            continue
        rest = float(r['gross_total'] or 0) - float(r['paid_amount'] or 0)
        subject = f"Mahnung {r['invoice_no']} - offener Betrag {rest:.2f} EUR"
        body = ("Sehr geehrte Damen und Herren,\n\n"
                f"die Rechnung {r['invoice_no']} ist seit dem {r['due_date']} fällig. "
                f"Der offene Betrag beträgt {rest:.2f} EUR.\n\n"
                "Bitte überweisen Sie den offenen Betrag zeitnah unter Angabe der Rechnungsnummer. "
                "Sollte die Zahlung bereits erfolgt sein, betrachten Sie diese Nachricht bitte als gegenstandslos.\n\n"
                "Mit freundlichen Grüßen\nByblos Sicherheitsdienst & Service")
        attachment = str(r['pdf_path'] or '')
        if not attachment or not Path(attachment).exists():
            try:
                attachment = str(generate_invoice_pdf(int(r['id'])))
            except Exception:
                attachment = ''
        queue_email(str(r['email']), subject, body, attachment)
        created += 1
        if send_now:
            email_id = int(df("SELECT MAX(id) AS id FROM email_log").iloc[0]['id'])
            result = send_email_smtp(email_id)
            if 'gesendet' in result.lower():
                sent += 1
    automation_log('overdue_reminders', 'ok', f'{created} Mahnungen vorbereitet, {sent} gesendet')
    return created, sent


def auto_match_all_new_bank_transactions():
    txs = df("SELECT id FROM bank_transactions WHERE status='neu'")
    for _, r in txs.iterrows():
        auto_match_bank_transaction(int(r['id']))
    proposed = int(df("SELECT COUNT(*) AS n FROM bank_transactions WHERE status='vorgeschlagen'").iloc[0]['n'])
    automation_log('bank_auto_match', 'ok', f'{len(txs)} Transaktionen geprüft, {proposed} Vorschläge offen')
    return len(txs), proposed


def calculate_daily_kpis(kpi_day=None):
    d = kpi_day or date.today().isoformat()
    month = d[:7]
    revenue_month = float(df("SELECT COALESCE(SUM(gross_total),0) AS v FROM invoices WHERE substr(invoice_date,1,7)=?", (month,)).iloc[0]['v'])
    paid_month = float(df("SELECT COALESCE(SUM(paid_amount),0) AS v FROM invoices WHERE substr(paid_date,1,7)=?", (month,)).iloc[0]['v'])
    expense_month = float(df("SELECT COALESCE(SUM(gross_amount),0) AS v FROM expenses WHERE substr(expense_date,1,7)=?", (month,)).iloc[0]['v'])
    open_invoices = float(df("SELECT COALESCE(SUM(gross_total-paid_amount),0) AS v FROM invoices WHERE status IN ('offen','ueberfaellig')").iloc[0]['v'])
    overdue_invoices = float(df("SELECT COALESCE(SUM(gross_total-paid_amount),0) AS v FROM invoices WHERE status='ueberfaellig'").iloc[0]['v'])
    profit_month = revenue_month - expense_month
    run("""INSERT OR REPLACE INTO daily_kpis(kpi_date,revenue_month,paid_month,expense_month,open_invoices,overdue_invoices,profit_month)
           VALUES(?,?,?,?,?,?,?)""", (d, revenue_month, paid_month, expense_month, open_invoices, overdue_invoices, profit_month))
    automation_log('daily_kpis', 'ok', f'{d}: Umsatz {revenue_month:.2f}, Ausgaben {expense_month:.2f}')
    return {
        'Datum': d,
        'Umsatz Monat brutto': revenue_month,
        'Zahlungseingang Monat': paid_month,
        'Ausgaben Monat brutto': expense_month,
        'Offene Rechnungen': open_invoices,
        'Überfällige Rechnungen': overdue_invoices,
        'Ergebnis grob': profit_month,
    }


def verify_latest_backup():
    b = df("SELECT * FROM backups ORDER BY created_at DESC LIMIT 1")
    if b.empty:
        return False, 'Kein Backup vorhanden.'
    path = Path(str(b.iloc[0]['file_path']))
    if not path.exists():
        return False, f"Backup-Datei fehlt: {path}"
    if sha256_file(path) != str(b.iloc[0]['sha256']):
        return False, 'SHA-256-Prüfsumme stimmt nicht.'
    try:
        with zipfile.ZipFile(path, 'r') as z:
            bad = z.testzip()
        if bad:
            return False, f'ZIP beschädigt bei Datei: {bad}'
    except Exception as e:
        return False, f'ZIP-Test fehlgeschlagen: {e}'
    return True, f'Backup geprüft: {path.name}'


def run_daily_automation(send_reminders=False, create_backup=True):
    results = []

    # 0. Wiederkehrende Rechnungen erstellen (fällige)
    try:
        today_str = __import__('datetime').date.today().isoformat()
        due_recurring = df("""
            SELECT r.id, r.customer_id, r.description, r.net_amount, r.vat_rate,
                   r.frequency, r.auto_send, c.email
            FROM recurring_invoices r JOIN customers c ON c.id=r.customer_id
            WHERE r.active=1 AND r.next_due<=?
        """, (today_str,))
        rec_created = 0
        for _, r in due_recurring.iterrows():
            inv_no = next_number("invoices","invoice_no","RE-")
            net = float(r["net_amount"])
            vat = float(r["vat_rate"])
            vat_amt = round(net * vat / 100, 2)
            gross = round(net + vat_amt, 2)
            run("""INSERT INTO invoices(invoice_no,customer_id,invoice_date,service_date,due_date,
                   description,net_total,vat_rate,vat_total,gross_total,paid_amount,status)
                   VALUES(?,?,?,?,?,?,?,?,?,?,0,'offen')""",
                (__import__('datetime').date.today().isoformat(), int(r["customer_id"]),
                 __import__('datetime').date.today().isoformat(),
                 __import__('datetime').date.today().strftime("%B %Y"),
                 (__import__('datetime').date.today() + __import__('datetime').timedelta(days=14)).isoformat(),
                 str(r["description"]), net, vat, vat_amt, gross))
            # Nächste Fälligkeit
            freq = str(r["frequency"])
            nd = __import__('datetime').date.fromisoformat(str(r["next_due"])[:10] if hasattr(r,"next_due") else today_str)
            if freq == "monatlich":
                m, y = (nd.month+1, nd.year) if nd.month<12 else (1, nd.year+1)
                nnd = nd.replace(year=y, month=m)
            elif freq == "vierteljährlich":
                nnd = nd + __import__('datetime').timedelta(days=91)
            elif freq == "halbjährlich":
                nnd = nd + __import__('datetime').timedelta(days=182)
            else:
                nnd = nd.replace(year=nd.year+1)
            run("UPDATE recurring_invoices SET next_due=?,last_created=? WHERE id=?",
                (nnd.isoformat(), today_str, int(r["id"])))
            rec_created += 1
        if rec_created:
            results.append(f"Dauerrechnungen erstellt: {rec_created}")
    except Exception as e:
        results.append(f"Dauerrechnungen Fehler: {e}")

    # 1. Überfällige Rechnungen markieren
    n_overdue = mark_overdue_invoices()
    results.append(f"Überfällig markiert: {n_overdue}")

    # 2. Mahnungen vorbereiten / senden
    c, snt = queue_overdue_reminders(send_now=send_reminders)
    results.append(f"Mahnungen vorbereitet: {c}, gesendet: {snt}")

    # 3. Banktransaktionen abgleichen
    try:
        checked, proposed = auto_match_all_new_bank_transactions()
        results.append(f"Banktransaktionen geprüft: {checked}, Vorschläge: {proposed}")
    except Exception as e:
        results.append(f"Bank-Abgleich Fehler: {e}")

    # 4. KPIs berechnen
    try:
        kpis = calculate_daily_kpis()
        results.append(f"KPIs berechnet: {list(kpis.keys())[:4]}")
    except Exception as e:
        results.append(f"KPI-Fehler: {e}")

    # 5. Backup erstellen
    if create_backup:
        try:
            backup_path = create_full_backup("automatisch täglich")
            bp = Path(str(backup_path))
            size = bp.stat().st_size if bp.exists() else 0
            run("INSERT INTO backups(file_path,file_size,note) VALUES(?,?,?)",
                (str(bp), size, "tägl. Automatik"))
            results.append(f"Backup: {bp.name} ({size//1024} KB)")

            # Cloud-Backup
            webdav_url  = get_setting("webdav_url")
            webdav_auto = get_setting("webdav_auto")
            if webdav_url and webdav_auto == "1":
                try:
                    from extensions_v2_final2 import upload_to_webdav
                    ok, msg = upload_to_webdav(
                        bp, webdav_url,
                        get_setting("webdav_user"), get_setting("webdav_pass"),
                        get_setting("webdav_dir","ByblosCRM/") + bp.name
                    )
                    results.append(f"Cloud-Backup: {'✅' if ok else '❌'} {msg}")
                except Exception as e:
                    results.append(f"Cloud-Backup Fehler: {e}")
        except Exception as e:
            results.append(f"Backup-Fehler: {e}")

    # 6. Telegram-Benachrichtigung
    try:
        tg_enabled = get_setting("telegram_enabled")
        if tg_enabled == "1":
            from extensions_v2_new3 import send_telegram
            token   = get_setting("telegram_token")
            chat_id = get_setting("telegram_chat_id")
            if token and chat_id:
                summary = f"🛡️ *Byblos CRM Tagesroutine*\n" + "\n".join(f"• {r}" for r in results[:5])
                send_telegram(token, chat_id, summary)
                results.append("Telegram: Zusammenfassung gesendet")
    except Exception as e:
        results.append(f"Telegram Fehler: {e}")

    # 7. Automatik-Log
    try:
        run("INSERT INTO automation_log(action,result) VALUES(?,?)",
            ("daily_routine", "; ".join(results[:8])))
    except Exception:
        pass

    return results

def normalize_text(value):
    text = str(value or '').lower()
    replacements = {'ä':'ae','ö':'oe','ü':'ue','ß':'ss'}
    for a,b in replacements.items():
        text = text.replace(a,b)
    return re.sub(r'\s+', ' ', text).strip()


def money(value):
    if value is None:
        return 0.0
    txt = str(value).strip().replace('€','').replace('EUR','').replace('eur','')
    if ',' in txt and '.' in txt:
        txt = txt.replace('.', '').replace(',', '.')
    elif ',' in txt:
        txt = txt.replace(',', '.')
    return float(pd.to_numeric(txt, errors='coerce') or 0.0)


def fingerprint(import_type, row):
    raw = json.dumps(row, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256((import_type + '|' + raw).encode('utf-8')).hexdigest()


def detect_import_type(data, file_name=''):
    cols = [normalize_text(c) for c in data.columns]
    joined = ' '.join(cols + [normalize_text(file_name)])
    if any(x in joined for x in ['buchungstag','verwendungszweck','umsatz','valuta','auftraggeber','kontoauszug']):
        return 'bank'
    if any(x in joined for x in ['rechnungsnummer','invoice_no','invoice no','rechnung']) and any(x in joined for x in ['kunde','customer','betrag']):
        return 'rechnungen'
    if any(x in joined for x in ['lieferant','beleg','vorsteuer','kostenart','ausgabe']):
        return 'ausgaben'
    if any(x in joined for x in ['kundennummer','customer_no','firma','company','kunde']):
        return 'kunden'
    return 'unbekannt'


def find_col(data, names):
    norm = {normalize_text(c): c for c in data.columns}
    for n in names:
        nn = normalize_text(n)
        if nn in norm:
            return norm[nn]
    for c in data.columns:
        nc = normalize_text(c)
        if any(normalize_text(n) in nc for n in names):
            return c
    return None


def learn_rule(rule_type, pattern, target_type, target_id=None, category='', confidence=95, note=''):
    pat = normalize_text(pattern)
    if not pat:
        return
    exists = df("SELECT id FROM matching_rules WHERE rule_type=? AND pattern=? AND target_type=? AND COALESCE(target_id,0)=COALESCE(?,0)", (rule_type, pat, target_type, target_id or 0))
    if exists.empty:
        run("INSERT INTO matching_rules(rule_type,pattern,target_type,target_id,category,confidence,note) VALUES(?,?,?,?,?,?,?)", (rule_type, pat, target_type, target_id, category, confidence, note))
        log_action('matching_rule_learned', f'{rule_type}: {pat} -> {target_type}:{target_id or category}')


def rule_match(text):
    t = normalize_text(text)
    rules = df("SELECT * FROM matching_rules WHERE active=1 ORDER BY confidence DESC, id DESC")
    for _, r in rules.iterrows():
        if str(r['pattern']) and str(r['pattern']) in t:
            return dict(r)
    return None


# -----------------------------------------------------------------------------
# PDF and scanned document support
#
def extract_pdf_text(file) -> str:
    """Extract text from an uploaded PDF file, with OCR fallback.

    First, the function tries direct PDF text extraction via pdfplumber.
    That works well for digital PDFs.  If no text is found, it optionally
    falls back to OCR with pytesseract and pdf2image.  OCR requires the
    external Tesseract executable and Poppler to be installed on the host
    machine.  If those tools are missing, the function returns an empty
    string instead of crashing the app.
    """
    raw_bytes = file.getvalue() if hasattr(file, 'getvalue') else file.read()
    parts = []

    try:
        with pdfplumber.open(io.BytesIO(raw_bytes)) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text() or ''
                if page_text.strip():
                    parts.append(page_text)
    except Exception:
        pass

    direct_text = '\n'.join(parts).strip()
    if direct_text:
        return direct_text

    # OCR fallback for scanned PDFs.  This remains optional so that the app
    # can still run on systems where Tesseract or Poppler is not installed.
    if pytesseract is None or convert_from_bytes is None:
        return ''

    try:
        images = convert_from_bytes(raw_bytes, dpi=200)
        ocr_parts = []
        for img in images:
            text = pytesseract.image_to_string(img, lang='deu+eng')
            if text.strip():
                ocr_parts.append(text)
        return '\n'.join(ocr_parts).strip()
    except Exception:
        return ''


def extract_image_text(file) -> str:
    """Extract text from an uploaded image using optional Tesseract OCR."""
    if pytesseract is None or PILImage is None:
        return ''
    try:
        img = PILImage.open(file)
        return pytesseract.image_to_string(img, lang='deu+eng').strip()
    except Exception:
        return ''


def match_customer(text, iban=''):
    t = normalize_text(text + ' ' + iban)
    rule = rule_match(t)
    if rule and rule.get('target_type') == 'customer' and rule.get('target_id'):
        return 'customer', int(rule['target_id']), float(rule['confidence'] or 95), 'Lernregel'
    customers = df("SELECT id, company, customer_no, email, phone, notes FROM customers")
    best = (None, None, 0, '')
    for _, c in customers.iterrows():
        company = normalize_text(c['company'])
        cust_no = normalize_text(c['customer_no'])
        if cust_no and cust_no in t:
            return 'customer', int(c['id']), 98, 'Kundennummer erkannt'
        if company and company in t:
            return 'customer', int(c['id']), 90, 'Kundenname erkannt'
        # token overlap for long company names
        tokens = [x for x in company.split() if len(x) >= 4]
        if tokens:
            score = 60 * sum(1 for x in tokens if x in t) / max(1, len(tokens))
            if score > best[2]:
                best = ('customer', int(c['id']), score, 'Teiltreffer Kundenname')
    return best


def match_invoice(text, amount=0):
    t = normalize_text(text)
    invoices = df("SELECT id, invoice_no, gross_total, paid_amount, status FROM invoices WHERE status!='bezahlt'")
    for _, inv in invoices.iterrows():
        inv_no = normalize_text(inv['invoice_no'])
        rest = round(float(inv['gross_total'] or 0) - float(inv['paid_amount'] or 0), 2)
        if inv_no and inv_no in t:
            return 'invoice', int(inv['id']), 100, 'Rechnungsnummer erkannt'
        if amount > 0 and rest > 0 and abs(float(amount) - rest) < 0.02:
            return 'invoice', int(inv['id']), 85, 'Betrag passt exakt zu offener Rechnung'
    return None, None, 0, ''


def match_expense(text, amount=0):
    t = normalize_text(text)
    rule = rule_match(t)
    if rule and rule.get('target_type') == 'expense_category':
        return 'expense_category', None, float(rule['confidence'] or 90), 'Kostenarten-Lernregel', str(rule.get('category') or '')
    # Existing expenses by number or amount.
    expenses = df("SELECT id, expense_no, gross_amount, paid_amount, status FROM expenses WHERE status!='bezahlt'")
    for _, exp in expenses.iterrows():
        exp_no = normalize_text(exp['expense_no'])
        rest = round(float(exp['gross_amount'] or 0) - float(exp['paid_amount'] or 0), 2)
        if exp_no and exp_no in t:
            return 'expense', int(exp['id']), 100, 'Ausgaben-Nr. erkannt', ''
        if amount < 0 and rest > 0 and abs(abs(float(amount)) - rest) < 0.02:
            return 'expense', int(exp['id']), 85, 'Betrag passt exakt zu offener Ausgabe', ''
    default_rules = {
        'tankstelle': '4400 Fahrzeugkosten', 'shell': '4400 Fahrzeugkosten', 'aral': '4400 Fahrzeugkosten', 'esso': '4400 Fahrzeugkosten',
        'amazon': '4700 Bürobedarf / Telefon / Software', 'telekom': '4700 Bürobedarf / Telefon / Software', 'vodafone': '4700 Bürobedarf / Telefon / Software',
        'miete': '4200 Raumkosten / Miete', 'versicherung': '4300 Versicherungen / Beiträge', 'lohn': '4100 Personal / Löhne',
        'datev': '4800 Rechts- und Beratungskosten', 'steuerberater': '4800 Rechts- und Beratungskosten', 'google': '4500 Werbung / Marketing', 'meta': '4500 Werbung / Marketing'
    }
    for pat, cat in default_rules.items():
        if pat in t:
            return 'expense_category', None, 78, f'Standardregel: {pat}', cat
    return None, None, 0, '', ''


def enqueue_import(import_type, source_file, row, target, target_id, confidence, action, reason):
    fp = fingerprint(import_type, row)
    exists = df("SELECT id FROM import_dedup WHERE fingerprint=?", (fp,))
    if not exists.empty:
        return False, 'Dublettenprüfung: bereits importiert'
    run("INSERT OR IGNORE INTO import_dedup(fingerprint,import_type,source_file) VALUES(?,?,?)", (fp, import_type, source_file))
    run("INSERT INTO import_queue(import_type,source_file,raw_data,detected_target,detected_id,confidence,action,status,reason) VALUES(?,?,?,?,?,?,?,?,?)",
        (import_type, source_file, json.dumps(row, ensure_ascii=False, default=str), target, target_id, confidence, action, 'neu', reason))
    return True, 'in Warteschlange'


def process_import_queue_item(qid, force=False, learn=False):
    q = df("SELECT * FROM import_queue WHERE id=?", (qid,))
    if q.empty:
        return 'Nicht gefunden.'
    r = q.iloc[0]
    raw = json.loads(r['raw_data'])
    conf = float(r['confidence'] or 0)
    if not force and conf < 90:
        return 'Nicht sicher genug. Bitte manuell prüfen oder „erzwingen“ nutzen.'
    it = r['import_type']
    target = r['detected_target']
    target_id = int(r['detected_id']) if r['detected_id'] else None
    try:
        if it == 'bank':
            amount = money(raw.get('amount'))
            cur = run("INSERT INTO bank_transactions(booking_date,value_date,payer_payee,purpose,amount,source_file,status,matched_type,matched_id) VALUES(?,?,?,?,?,?,?,?,?)",
                      (str(raw.get('booking_date',''))[:10], str(raw.get('value_date',''))[:10], raw.get('payer_payee',''), raw.get('purpose',''), amount, r['source_file'], 'vorgeschlagen' if target_id else 'neu', target, target_id))
            if target == 'invoice' and target_id and conf >= 95:
                apply_bank_match(cur.lastrowid)
            elif target == 'expense' and target_id and conf >= 95:
                apply_bank_match(cur.lastrowid)
            elif target == 'expense_category':
                # Create simple paid expense from outgoing bank movement if category confidently known.
                gross = abs(amount)
                if amount < 0 and gross > 0:
                    exp_no = next_number('expenses','expense_no','AU-')
                    category = raw.get('category') or r['reason'].split('|')[-1].strip() if '|' in str(r['reason']) else '4900 Sonstige betriebliche Aufwendungen'
                    supplier_name = raw.get('payer_payee') or 'Unbekannt'
                    srow = df("SELECT id FROM suppliers WHERE lower(name)=lower(?)", (supplier_name,))
                    if srow.empty:
                        run("INSERT INTO suppliers(supplier_no,name,notes) VALUES(?,?,?)", (next_number('suppliers','supplier_no','LF-'), supplier_name, 'automatisch aus Bankimport'))
                        sid = int(df("SELECT MAX(id) AS id FROM suppliers").iloc[0]['id'])
                    else:
                        sid = int(srow.iloc[0]['id'])
                    net = round(gross/1.19,2)
                    vat = round(gross-net,2)
                    run("""INSERT INTO expenses(expense_no,receipt_no,supplier_id,expense_date,description,category,net_amount,vat_rate,vat_amount,gross_amount,paid_amount,payment_method,status,bwa_month,notes)
                           VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", (exp_no, '', sid, str(raw.get('booking_date',''))[:10] or date.today().isoformat(), raw.get('purpose','Bankimport Ausgabe'), category, net, 19, vat, gross, gross, 'Überweisung', 'bezahlt', (str(raw.get('booking_date',''))[:7] or date.today().strftime('%Y-%m')), 'automatisch aus Bankimport'))
        elif it == 'kunden':
            name = raw.get('company') or raw.get('kunde') or raw.get('firma') or raw.get('name') or ''
            if name:
                exists = df("SELECT id FROM customers WHERE lower(company)=lower(?)", (name,))
                if exists.empty:
                    run("""INSERT INTO customers(customer_no,company,contact_person,email,phone,street,zip_city,country,notes)
                           VALUES(?,?,?,?,?,?,?,?,?)""", (raw.get('customer_no') or next_number('customers','customer_no','SD-'), name, raw.get('contact_person',''), raw.get('email',''), raw.get('phone',''), raw.get('street',''), raw.get('zip_city',''), raw.get('country','Deutschland'), 'automatisch importiert'))
        elif it == 'rechnungen':
            inv_no = raw.get('invoice_no') or raw.get('rechnungsnummer') or ''
            if inv_no and not df("SELECT id FROM invoices WHERE invoice_no=?", (inv_no,)).empty:
                run("UPDATE import_queue SET status='doppelt', processed_at=CURRENT_TIMESTAMP WHERE id=?", (qid,))
                return 'Rechnung existiert bereits.'
            cid = target_id if target == 'customer' and target_id else None
            if not cid:
                return 'Kein Kunde erkannt. Bitte manuell zuordnen.'
            gross = money(raw.get('gross_total') or raw.get('betrag') or raw.get('brutto'))
            net = money(raw.get('net_total') or raw.get('netto')) or round(gross/1.19,2)
            vat = round(gross-net,2)
            inv_no = inv_no or next_number('invoices','invoice_no','RE-')
            inv_date = str(raw.get('invoice_date') or raw.get('datum') or date.today().isoformat())[:10]
            due = str(raw.get('due_date') or '')[:10] or (date.today()+timedelta(days=14)).isoformat()
            run("""INSERT INTO invoices(invoice_no,customer_id,invoice_date,service_date,due_date,description,net_total,vat_rate,vat_total,gross_total,status)
                   VALUES(?,?,?,?,?,?,?,?,?,?,?)""", (inv_no, cid, inv_date, raw.get('service_date',''), due, raw.get('description','Import Rechnung'), net, 19, vat, gross, 'offen'))
        elif it == 'ausgaben':
            gross = money(raw.get('gross_amount') or raw.get('brutto') or raw.get('betrag'))
            net = money(raw.get('net_amount') or raw.get('netto')) or round(gross/1.19,2)
            vat = round(gross-net,2)
            supplier_name = raw.get('supplier') or raw.get('lieferant') or raw.get('name') or 'Unbekannt'
            srow = df("SELECT id FROM suppliers WHERE lower(name)=lower(?)", (supplier_name,))
            if srow.empty:
                run("INSERT INTO suppliers(supplier_no,name,notes) VALUES(?,?,?)", (next_number('suppliers','supplier_no','LF-'), supplier_name, 'automatisch importiert'))
                sid = int(df("SELECT MAX(id) AS id FROM suppliers").iloc[0]['id'])
            else:
                sid = int(srow.iloc[0]['id'])
            category = raw.get('category') or raw.get('kostenart') or r['reason'].split('|')[-1].strip() if '|' in str(r['reason']) else '4900 Sonstige betriebliche Aufwendungen'
            exp_date = str(raw.get('expense_date') or raw.get('datum') or date.today().isoformat())[:10]
            run("""INSERT INTO expenses(expense_no,receipt_no,supplier_id,expense_date,description,category,net_amount,vat_rate,vat_amount,gross_amount,paid_amount,payment_method,status,bwa_month,notes)
                   VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", (raw.get('expense_no') or next_number('expenses','expense_no','AU-'), raw.get('receipt_no',''), sid, exp_date, raw.get('description','Import Ausgabe'), category, net, 19, vat, gross, 0, raw.get('payment_method','Überweisung'), 'offen', exp_date[:7], 'automatisch importiert'))
        run("UPDATE import_queue SET status='verarbeitet', processed_at=CURRENT_TIMESTAMP WHERE id=?", (qid,))
        if learn and target_id:
            text = ' '.join(str(v) for v in raw.values())
            # Persist a rule for rule‑based matching and simultaneously
            # accumulate a training example for the machine learning model.
            learn_rule('text', text[:80], target, target_id, note='aus Importbestätigung gelernt')
            try:
                # We do not store the full raw JSON for training because it may
                # contain sensitive data.  Instead we use the concatenated
                # string of values (similar to how rule matching works).
                add_training_example(text, str(target))
            except Exception:
                # Ignore errors while adding training data.
                pass
        log_action('import_processed', f'{it} #{qid} -> {target}:{target_id}')
        return 'Verarbeitet und gespeichert.'
    except Exception as e:
        run("UPDATE import_queue SET status='fehler', reason=?, processed_at=CURRENT_TIMESTAMP WHERE id=?", (str(e), qid))
        return f'Fehler: {e}'


def queue_dataframe_import(data, source_file, import_type=None):
    it = import_type or detect_import_type(data, source_file)
    queued = 0; skipped = 0
    if it == 'bank':
        norm = normalize_bank_columns(data)
        for _, rr in norm.iterrows():
            row = rr.to_dict(); text = f"{row.get('payer_payee','')} {row.get('purpose','')}"; amount = money(row.get('amount'))
            target, tid, conf, reason = match_invoice(text, amount)
            if not target and amount < 0:
                res = match_expense(text, amount); target, tid, conf, reason = res[:4]
                if len(res) > 4 and res[4]: reason = reason + ' | ' + res[4]
            action = 'auto_speichern' if conf >= 95 else 'pruefen'
            ok, _ = enqueue_import('bank', source_file, row, target or '', tid, conf, action, reason)
            queued += int(ok); skipped += int(not ok)
    else:
        for _, rr in data.fillna('').iterrows():
            raw = {str(k): v for k,v in rr.to_dict().items()}
            low = {normalize_text(k): v for k,v in raw.items()}
            text = ' '.join(str(v) for v in raw.values())
            target=''; tid=None; conf=0; reason=''
            if it in ['kunden']:
                # Heuristic classification for customer imports.
                target = 'customer'
                conf = 70
                reason = 'Kundenimport'
            elif it in ['rechnungen']:
                # Attempt to match customer for the invoice.
                target, tid, conf, reason = match_customer(text)
            elif it in ['ausgaben']:
                # Attempt to match existing expense or expense category.
                res = match_expense(text, -abs(money(low.get('betrag') or low.get('brutto') or low.get('gross_amount'))))
                target, tid, conf, reason = res[:4]
                # If a category hint is provided in res[4], set it on the raw row.
                if len(res) > 4 and res[4]:
                    raw['category'] = res[4]
                    reason = reason + ' | ' + res[4]

            # Invoke the AI classifier to see if it can provide a stronger signal.
            try:
                ai_cat, ai_conf = predict_category(text)
            except Exception:
                ai_cat, ai_conf = (None, 0.0)
            # Map AI category names to internal import targets.  When the
            # classifier suggests a category with higher confidence than the
            # existing heuristic, use it as the detected target and reset tid
            # because we cannot infer a specific database ID from AI alone.
            category_map = {
                'invoice': 'invoice',
                'expense': 'expense',
                'customer': 'customer'
            }
            predicted_target = category_map.get(ai_cat or '')
            if predicted_target and ai_conf > conf:
                target = predicted_target
                tid = None
                conf = ai_conf
                reason = f'KI-Vorhersage: {predicted_target}'

            ok, _ = enqueue_import(it, source_file, raw, target or '', tid, conf, 'auto_speichern' if conf >= 95 else 'pruefen', reason)
            queued += int(ok)
            skipped += int(not ok)
    automation_log('smart_import_queue', 'ok', f'{queued} neu, {skipped} Dubletten, Typ {it}')
    return it, queued, skipped


def page_smart_import():
    st.title("Intelligenter Import")
    st.caption("Neue Daten werden erkannt, geprüft und automatisch in Kunden, Rechnungen, Ausgaben oder Banktransaktionen gespeichert. Sichere Treffer werden gebucht; unsichere Treffer landen in der Prüfliste.")
    tabs = st.tabs(["Import hochladen", "Prüfliste", "Lernregeln", "Dubletten/Protokoll"])
    with tabs[0]:
        # Datei-Upload-Widget innerhalb des Tabs; eingerückt, damit der Kontext des "with" gilt.
        f = st.file_uploader("CSV/XLSX/PDF/Bild importieren", type=["csv","xlsx","xls","pdf","png","jpg","jpeg"], key="smart_import_file")
        manual_type = st.selectbox("Typ erzwingen (optional)", ["automatisch", "bank", "kunden", "rechnungen", "ausgaben"])
        if f:
            # Branch on file type: CSV/XLSX handled as before, PDF handled via pdfplumber/OCR.
            name = f.name.lower()
            if name.endswith('.pdf'):
                st.write("PDF-Import")
                # Extract text from the PDF and display a preview.
                text = extract_pdf_text(f)
                if text:
                    st.text_area("Text erkannt", text, height=300)
                else:
                    st.warning("Es konnte kein Text aus dieser PDF extrahiert werden.")
                # Run AI classification on the extracted text to suggest a category.
                ai_cat, ai_conf = predict_category(text)
                # Map AI categories to import types.  Unknown fallback to 'unbekannt'.
                type_map = {'invoice': 'rechnungen', 'expense': 'ausgaben', 'customer': 'kunden'}
                suggested_type = type_map.get(ai_cat or '', 'unbekannt')
                if ai_cat:
                    st.info(f"KI-Vorhersage: {ai_cat} ({ai_conf:.1f} % Sicherheit)")
                else:
                    st.info("Keine KI-Vorhersage möglich. Es sind zu wenige Trainingsdaten vorhanden.")
                # Allow user to override type via manual_type if desired.
                if st.button("In intelligente Warteschlange übernehmen"):
                    # Build a minimal DataFrame for queue import.  The text is placed in a
                    # column that will not match existing schemas so that detection
                    # returns 'unbekannt' and the AI classification is used.
                    pdf_df = pd.DataFrame([{'pdf_text': text}])
                    it, queued, skipped = queue_dataframe_import(pdf_df, f.name, None if manual_type=='automatisch' else manual_type)
                    st.success(f"PDF-Import: {queued} neue Datensätze, {skipped} Dubletten übersprungen.")
                    st.rerun()
            elif name.endswith(('.png', '.jpg', '.jpeg')):
                st.write("Bild-/Scan-Import")
                text = extract_image_text(f)
                if text:
                    st.text_area("Text erkannt", text, height=300)
                else:
                    st.warning("Es konnte kein Text aus dem Bild extrahiert werden. Prüfe, ob Tesseract OCR installiert ist.")
                ai_cat, ai_conf = predict_category(text)
                if ai_cat:
                    st.info(f"KI-Vorhersage: {ai_cat} ({ai_conf:.1f} % Sicherheit)")
                else:
                    st.info("Keine KI-Vorhersage möglich. Es sind zu wenige Trainingsdaten vorhanden oder OCR hat keinen Text geliefert.")
                if st.button("Scan in intelligente Warteschlange übernehmen"):
                    img_df = pd.DataFrame([{'scan_text': text}])
                    it, queued, skipped = queue_dataframe_import(img_df, f.name, None if manual_type=='automatisch' else manual_type)
                    st.success(f"Scan-Import: {queued} neue Datensätze, {skipped} Dubletten übersprungen.")
                    st.rerun()
            else:
                # Handle CSV or Excel files as before.
                data = pd.read_csv(f, sep=None, engine='python') if name.endswith('.csv') else pd.read_excel(f)
                st.write("Vorschau")
                st.dataframe(data.head(20), use_container_width=True)
                guessed = detect_import_type(data, f.name)
                st.info(f"Erkannt: {guessed}")
                if st.button("In intelligente Warteschlange übernehmen"):
                    it, queued, skipped = queue_dataframe_import(data, f.name, None if manual_type=='automatisch' else manual_type)
                    st.success(f"Importtyp {it}: {queued} neue Datensätze, {skipped} Dubletten übersprungen.")
                    st.rerun()
        st.divider()
        st.subheader("Sicherheitslogik")
        st.markdown("""
        - **100% sicher:** Rechnungsnummer gefunden → Rechnung/Zahlung direkt zuordenbar.
        - **95%+ sicher:** gelernte Regel oder eindeutiger Treffer → automatisch speicherbar.
        - **unter 90%:** landet in der Prüfliste, keine stille Falschbuchung.
        - **Dublettenprüfung:** jeder Importdatensatz bekommt einen SHA-256-Fingerprint.
        """)
    with tabs[1]:
        q = df("SELECT id, import_type, source_file, detected_target, detected_id, confidence, action, status, reason, created_at FROM import_queue ORDER BY id DESC LIMIT 500")
        st.dataframe(q, use_container_width=True)
        pending = df("SELECT id, import_type || ' #' || id || ' | ' || COALESCE(reason,'') AS label FROM import_queue WHERE status='neu' ORDER BY confidence DESC, id DESC")
        if not pending.empty:
            label = st.selectbox("Datensatz verarbeiten", pending['label'].tolist())
            qid = int(pending[pending['label']==label].iloc[0]['id'])
            raw = df("SELECT raw_data FROM import_queue WHERE id=?", (qid,)).iloc[0]['raw_data']
            st.json(json.loads(raw))
            c1,c2,c3 = st.columns(3)
            if c1.button("Speichern, wenn sicher"):
                st.success(process_import_queue_item(qid, force=False, learn=True)); st.rerun()
            if c2.button("Manuell erzwingen"):
                st.warning(process_import_queue_item(qid, force=True, learn=True)); st.rerun()
            if c3.button("Ignorieren"):
                run("UPDATE import_queue SET status='ignoriert', processed_at=CURRENT_TIMESTAMP WHERE id=?", (qid,)); st.rerun()
        if st.button("Alle sicheren Treffer automatisch speichern"):
            safe = df("SELECT id FROM import_queue WHERE status='neu' AND confidence>=95")
            results=[]
            for _, rr in safe.iterrows():
                results.append(process_import_queue_item(int(rr['id']), force=False, learn=True))
            st.success(f"{len(results)} sichere Treffer verarbeitet.")
            st.rerun()
    with tabs[2]:
        st.subheader("Lernregel anlegen")
        with st.form("rule_form"):
            rule_type = st.selectbox("Regeltyp", ["text", "iban", "name", "kostenart"])
            pattern = st.text_input("Wenn Text enthält")
            target_type = st.selectbox("Dann zuordnen als", ["customer", "expense_category"])
            custs = df("SELECT id, company FROM customers ORDER BY company")
            target_id = None
            category = ''
            if target_type == 'customer' and not custs.empty:
                lab = st.selectbox("Kunde", custs['company'].tolist())
                target_id = int(custs[custs['company']==lab].iloc[0]['id'])
            if target_type == 'expense_category':
                cats = df("SELECT category FROM expense_categories ORDER BY category")
                category = st.selectbox("BWA-Kategorie", cats['category'].tolist() if not cats.empty else BWA_CATEGORIES)
            confidence = st.slider("Sicherheit", 50, 100, 95)
            if st.form_submit_button("Regel speichern"):
                learn_rule(rule_type, pattern, target_type, target_id, category, confidence, 'manuell angelegt')
                st.success("Regel gespeichert.")
                st.rerun()
        st.dataframe(df("SELECT id, rule_type, pattern, target_type, target_id, category, confidence, active, created_at, note FROM matching_rules ORDER BY id DESC"), use_container_width=True)
    with tabs[3]:
        c1,c2 = st.columns(2)
        c1.metric("Warteschlange offen", int(df("SELECT COUNT(*) AS n FROM import_queue WHERE status='neu'").iloc[0]['n']))
        c2.metric("Dubletten erkannt/gespeichert", int(df("SELECT COUNT(*) AS n FROM import_dedup").iloc[0]['n']))
        st.dataframe(df("SELECT * FROM import_dedup ORDER BY id DESC LIMIT 200"), use_container_width=True)

def sidebar():
    st.sidebar.title("🛡️ Byblos CRM")
    st.sidebar.caption("v2.0 · Byblos Sicherheitsdienst")
    st.sidebar.divider()

    user = current_user() or {}
    role = user.get('role', '-')
    username = user.get('username', '-')
    role_icon = {"admin": "👑", "manager": "💼", "user": "👤"}.get(role, "👤")
    st.sidebar.markdown(f"**{role_icon} {username}** · {role}")
    if st.sidebar.button("🚪 Logout", use_container_width=True):
        st.session_state.pop('user', None)
        st.rerun()
    st.sidebar.divider()

    # Gruppierte Navigation
    SECTIONS = {
        "📊 Übersicht": ["Dashboard", "Berichte", "Reporting-Center", "Benachrichtigungen", "Globale Suche"],
        "👥 CRM": ["Kunden", "Kontakte", "Firmenprofile", "Schnellsuche/KI", "KI-Auswertungen"],
        "💰 Finanzen": ["Rechnungen", "Ausgaben/BWA", "Bank/DATEV", "Zahlungen & Mahnwesen", "Offene Posten", "E-Rechnung", "E-Rechnung Prüfung"],
        "📋 Angebote": ["Angebote"],
        "📥 Import / Export": ["Intelligenter Import", "Mehrfach-Rechnungsimport", "Import", "Export/Backup", "Export & Backup Center"],
        "🚚 Lieferanten": ["Lieferanten"],
        "🔄 Dauerrechnungen": ["Dauerrechnungen", "Steuerkalender", "QR & Zahlung"],
        "🏖️ Personal Plus": ["Urlaubsplanung", "Fahrtenbuch"],
        "📊 SLA & Projekte": ["SLA-Monitoring", "Projekte"],
        "🏦 DATEV & Steuern": ["DATEV-Mapping", "Steuerkalender"],
        "🔔 Benachrichtigungen": ["Push-Benachrichtigungen"],
        "💶 Lohn & Berichte": ["Lohnabrechnung", "Einsatzberichte", "Aging-Report", "Wiedervorlagen"],
        "🎓 Qualifikationen": ["Qualifikationen", "Schichttausch"],
        "🧮 Kalkulation": ["Kostenvoranschlag", "SEPA-Lastschrift"],
        "🔌 API & Integration": ["JSON-API", "Kalender-Export", "KI-Suche", "BWA-Auto"],
        "🛡️ Sicherheit": ["Zwei-Faktor-Auth"],
        "📄 Dokumente": ["Angebots-PDF", "Lohnzettel-Versand", "Rechnungsnummern-Check"],
        "📁 Projektrechnungen": ["Projekt-zu-Rechnung"],
        "🖨️ Druck & Ansicht": ["Druckansicht Dienstplan"],
        "👷 Mitarbeiterportal": ["Mein Bereich", "Interne Nachrichten"],
        "📍 GPS & Stempel": ["GPS-Stempeluhr"],
        "⚠️ Mahnwesen Plus": ["Mahngebühren"],
        "🤖 KI-Assistent": ["KI-Chatbot", "Executive Summary"],
        "🚀 Einrichtung": ["Onboarding-Assistent"],
        "❌ Storno": ["Stornorechnungen"],
        "⏱️ Überstunden": ["Überstunden-Ausgleich"],
        "💼 Minijobler": ["Minijobler-Rechner"],
        "📋 Verträge Plus": ["Vertragsüberwachung"],
        "📊 Vergleich": ["BWA-Jahresvergleich"],
        "🔒 Datenschutz": ["DSGVO-Center"],
        "✉️ Serienbriefe": ["Serienbrief"],
        "🌐 Erweitert": ["Sprache", "OCR-Belegerfassung", "Zahlungslinks", "Webhooks", "Mobile-Modus", "FastAPI-Server"],
        "🏗️ Field-Ops": ["Angebot-zu-Rechnung", "Kunden-Timeline", "Personalakte"],
        "⏱️ Zeit & Personal": ["Deckungsbeitrag", "XLSX-Rechnungsimport"],
        "🔧 Betrieb": ["Verschlüsseltes Backup", "Performance-Monitor"],
        "📋 Verwaltung": ["Benachrichtigungen", "Schicht-Kalender",
                          "ZUGFeRD E-Rechnung", "Signaturen", "DB-Migrationen",
                          "Rate-Limiting", "WhatsApp", "Kunden v2"],
        "✉️ Kommunikation": ["Sammelrechnung", "Freigabe-Workflow", "Zapier-Templates",
                            "Reklamationen", "Eskalations-Mahnwesen", "VCard-Import"],
        "📊 Verwaltung": ["Schichtpräferenzen", "Gewinn-je-Stunde", "Projekt-Gantt",
                          "ZUGFeRD Einbetten", "Cloud-Backup Plus", "Stripe",
                          "Lohnsteuer-Export", "ELMA5"],
        "🏢 Objekte & Wachbuch": ["Objekte", "Wachbuch", "Schlüssel",
                                   "Dienstanweisungen", "§34a Compliance"],
        "📌 Intern": ["Schwarzes Brett", "Überstunden-Konto",
                     "Tages-Briefing", "KPI-Ziele",
                     "Benutzer & Rollen", "Dashboard anpassen"],
        "📊 Analysen": ["CLV-Analyse", "Schicht-Konflikte",
                        "ArbZG-Monitor", "Währungsrechner",
                        "Lieferanten-Bewertung", "Einsatzkalkulator",
                        "Zahlungs-E-Mail"],
        "🖥️ System": ["System-Health", "Backup-Manager", "Kundenportal",
                      "Protokoll-Export", "Passwort-Generator", "Updates"],
        "🌐 Netzwerk": ["Remote-Zugang", "Netzwerk-Status", "DynDNS"],
        "🚨 Protokolle": ["Unfallmeldungen", "Einsatzplanung Events",
                          "Dienstanweisungen", "Wartungsverträge",
                          "Kundenzufriedenheit", "Wissensdatenbank",
                          "Darlehen"],
        "📒 Buchhaltung Plus": ["Buchungsjournal", "Kassenbuch", "Reisekosten",
                                 "Personalplanung", "Kostenstellen",
                                 "Debitorenkonten", "UStVA"],
        "⚙️ System": ["Break-Even", "Duplikat-Check", "Budgetwarnungen",
                       "Inventar", "Heatmap-Kalender", "Prognose-Dashboard", "Favoriten",
                       "Benutzer/Rechte", "Einstellungen", "Systemgesundheit",
                       "Massenaktionen", "PDF-Berichte"],
        "💧 Liquidität": ["Liquiditätsplanung"],
        "✓ Validierung": ["Validierungs-Center"],
        "✅ Genehmigungen": ["Genehmigungs-Workflow"],
        "📦 Lieferschein": ["Lieferscheine"],
        "🔗 Webhooks": ["Webhooks"],
        "📋 Schicht-Vorlagen": ["Schicht-Vorlagen"],
        "🔐 Backup-Krypto": ["Backup-Verschlüsselung"],
        "💼 Personalanalyse": ["Personalkosten"],
        "🔔 Hinweise": ["Hinweis-Center"],
        "☁️ Cloud & Betrieb": ["Cloud-Backup", "Live-Betrieb"],
        "📈 Betrieb": ["Betriebskosten", "Qualitätschecklisten", "Notfallkontakte"],
        "🏗️ Field-Ops": ["Field-Ops Cockpit", "Mitarbeiter Einsatz", "Objekte", "Einsatzplanung", "Leistungsnachweise", "Field-Ops Export"],
        "⏱️ Zeit & Personal": ["Zeiterfassung", "Zeiten freigeben", "Zeitkonto & Payroll", "Dienstplan", "Schichtübergabe", "Mitarbeiter"],
        "🔧 Betrieb": ["SystemPlus Cockpit", "Live-Betrieb", "Ops Prüfungen", "Automatik", "Archiv/GoBD"],
        "📋 Verwaltung": ["Verträge & Dokumente", "Compliance & Recht", "Rollenmatrix", "Kundenportal", "Leistungs-Checklisten"],
        "✉️ Kommunikation": ["E-Mail"],

    }

    all_pages = [p for pages in SECTIONS.values() for p in pages]

    # Section-Auswahl in der Sidebar
    section = st.sidebar.selectbox("Bereich", list(SECTIONS.keys()), label_visibility="collapsed")
    st.sidebar.divider()
    pages_in_section = SECTIONS[section]

    if len(pages_in_section) == 1:
        return pages_in_section[0]
    return st.sidebar.radio("Seite", pages_in_section, label_visibility="collapsed")


def page_dashboard():
    st.title("Dashboard")
    today = date.today().isoformat()
    start_month = date.today().replace(day=1).isoformat()
    inv = df("SELECT * FROM invoices")
    revenue_month = float(df("SELECT COALESCE(SUM(gross_total),0) AS v FROM invoices WHERE invoice_date>=? AND status='bezahlt'", (start_month,)).iloc[0]["v"])
    open_amount = float(df("SELECT COALESCE(SUM(gross_total-paid_amount),0) AS v FROM invoices WHERE status IN ('offen','ueberfaellig')",).iloc[0]["v"])
    expense_month = float(df("SELECT COALESCE(SUM(gross_amount),0) AS v FROM expenses WHERE expense_date>=?", (start_month,)).iloc[0]["v"])
    profit_month = revenue_month - expense_month
    overdue = int(df("SELECT COUNT(*) AS n FROM invoices WHERE status='ueberfaellig'").iloc[0]["n"])
    next_shifts = int(df("SELECT COUNT(*) AS n FROM shifts WHERE shift_date>=? AND shift_date<=?", (today, (date.today()+timedelta(days=7)).isoformat())).iloc[0]["n"])
    c1,c2,c3,c4 = st.columns(4)
    c1.metric("Umsatz bezahlt Monat", f"{revenue_month:,.2f} EUR".replace(",", "X").replace(".", ",").replace("X", "."))
    c2.metric("Ausgaben Monat", f"{expense_month:,.2f} EUR".replace(",", "X").replace(".", ",").replace("X", "."))
    c3.metric("Ergebnis Monat", f"{profit_month:,.2f} EUR".replace(",", "X").replace(".", ",").replace("X", "."))
    c4.metric("Offene Rechnungen", f"{open_amount:,.2f} EUR".replace(",", "X").replace(".", ",").replace("X", "."))
    st.caption(f"Überfällige Rechnungen: {overdue} · Dienste nächste 7 Tage: {next_shifts}")
    st.subheader("Rechnungen nach Monat")
    chart = df("SELECT substr(invoice_date,1,7) AS monat, SUM(gross_total) AS brutto FROM invoices GROUP BY substr(invoice_date,1,7) ORDER BY monat")
    if not chart.empty:
        st.bar_chart(chart.set_index("monat"))
    st.subheader("Nächste Dienste")
    st.dataframe(df("""SELECT s.shift_date AS Datum, s.start_time AS Von, s.end_time AS Bis, e.name AS Mitarbeiter, c.company AS Kunde, s.location AS Ort, s.status AS Status
                     FROM shifts s LEFT JOIN employees e ON e.id=s.employee_id LEFT JOIN customers c ON c.id=s.customer_id
                     WHERE s.shift_date>=? ORDER BY s.shift_date, s.start_time LIMIT 20""", (today,)), use_container_width=True)


def page_customers():
    st.title("Kundenverwaltung")
    q = st.text_input("Suchen", "")
    if q:
        data = df("SELECT * FROM customers WHERE company LIKE ? OR customer_no LIKE ? OR contact_person LIKE ? ORDER BY company", tuple([f"%{q}%"]*3))
    else:
        data = df("SELECT * FROM customers ORDER BY company")
    st.dataframe(data, use_container_width=True)
    st.subheader("Kunde anlegen / bearbeiten")
    customers = df("SELECT id, customer_no || ' - ' || company AS label FROM customers ORDER BY company")
    mode = st.radio("Modus", ["Neu", "Bearbeiten"], horizontal=True)
    selected = None
    if mode == "Bearbeiten" and not customers.empty:
        selected = st.selectbox("Kunde", customers["label"].tolist())
        cid = int(customers[customers["label"]==selected].iloc[0]["id"])
        row = df("SELECT * FROM customers WHERE id=?", (cid,)).iloc[0].to_dict()
    else:
        cid = None
        row = {"customer_no": next_number("customers", "customer_no", "SD-"), "company":"", "contact_person":"", "email":"", "phone":"", "street":"", "zip_city":"", "country":"Deutschland", "notes":""}
    with st.form("customer_form"):
        a,b = st.columns(2)
        customer_no = a.text_input("Kundennummer", row.get("customer_no", ""))
        company = b.text_input("Firma/Name", row.get("company", ""))
        contact_person = a.text_input("Ansprechperson", row.get("contact_person", ""))
        phone = b.text_input("Telefon", row.get("phone", ""))
        email = a.text_input("E-Mail", row.get("email", ""))
        street = b.text_input("Straße", row.get("street", ""))
        zip_city = a.text_input("PLZ Ort", row.get("zip_city", ""))
        country = b.text_input("Land", row.get("country", "Deutschland"))
        notes = st.text_area("Notizen", row.get("notes", ""))
        save = st.form_submit_button("Speichern")
    if save and company:
        if cid:
            run("""UPDATE customers SET customer_no=?,company=?,contact_person=?,email=?,phone=?,street=?,zip_city=?,country=?,notes=? WHERE id=?""", (customer_no,company,contact_person,email,phone,street,zip_city,country,notes,cid))
        else:
            run("""INSERT INTO customers(customer_no,company,contact_person,email,phone,street,zip_city,country,notes) VALUES(?,?,?,?,?,?,?,?,?)""", (customer_no,company,contact_person,email,phone,street,zip_city,country,notes))
        st.success("Kunde gespeichert.")
        st.rerun()


def page_contacts():
    st.title("Kontakthistorie")
    customers = df("SELECT id, customer_no || ' - ' || company AS label FROM customers ORDER BY company")
    if customers.empty:
        st.warning("Bitte zuerst Kunden anlegen.")
        return
    with st.form("contact"):
        label = st.selectbox("Kunde", customers["label"].tolist())
        cid = int(customers[customers["label"]==label].iloc[0]["id"])
        a,b,c = st.columns(3)
        contact_date = a.date_input("Datum", date.today()).isoformat()
        contact_type = b.selectbox("Art", CONTACT_TYPES)
        next_followup = c.date_input("Wiedervorlage", value=None)
        subject = st.text_input("Betreff")
        note = st.text_area("Notiz")
        if st.form_submit_button("Kontakt speichern"):
            run("INSERT INTO contacts(customer_id,contact_date,contact_type,subject,note,next_followup) VALUES(?,?,?,?,?,?)", (cid, contact_date, contact_type, subject, note, next_followup.isoformat() if next_followup else None))
            st.success("Kontakt gespeichert.")
    st.dataframe(df("""SELECT co.contact_date AS Datum, c.company AS Kunde, co.contact_type AS Art, co.subject AS Betreff, co.note AS Notiz, co.next_followup AS Wiedervorlage
                     FROM contacts co JOIN customers c ON c.id=co.customer_id ORDER BY co.contact_date DESC"""), use_container_width=True)


def page_invoices():
    st.title("Rechnungsverwaltung")
    tabs = st.tabs(["Übersicht", "Neue Rechnung", "Positionen/Zahlung", "PDF"])
    with tabs[0]:
        st.dataframe(df("""SELECT i.id, i.invoice_no AS Rechnung, c.company AS Kunde, i.invoice_date AS Datum, i.due_date AS Faellig, i.description AS Leistung,
                         i.net_total AS Netto, i.vat_total AS USt, i.gross_total AS Brutto, i.paid_amount AS Bezahlt, i.status AS Status, i.pdf_path AS PDF
                         FROM invoices i JOIN customers c ON c.id=i.customer_id ORDER BY i.invoice_date DESC, i.invoice_no DESC"""), use_container_width=True)
    with tabs[1]:
        customers = df("SELECT id, customer_no || ' - ' || company AS label FROM customers ORDER BY company")
        if customers.empty:
            st.warning("Bitte zuerst Kunden anlegen.")
            return
        with st.form("new_invoice"):
            a,b,c = st.columns(3)
            inv_no = a.text_input("Rechnungsnummer", next_number("invoices", "invoice_no", "RE-"))
            label = b.selectbox("Kunde", customers["label"].tolist())
            inv_date = c.date_input("Rechnungsdatum", date.today())
            service_date = a.text_input("Leistungsdatum", date.today().strftime("%B %Y"))
            due_date = b.date_input("Fällig bis", date.today()+timedelta(days=14))
            vat_rate = c.number_input("MwSt %", value=19.0, step=1.0)
            desc = st.text_input("Leistungsbeschreibung", "Sicherheitsdienstleistung")
            if st.form_submit_button("Rechnung anlegen"):
                cid = int(customers[customers["label"]==label].iloc[0]["id"])
                run("""INSERT INTO invoices(invoice_no,customer_id,invoice_date,service_date,due_date,description,vat_rate,status)
                       VALUES(?,?,?,?,?,?,?,?)""", (inv_no,cid,inv_date.isoformat(),service_date,due_date.isoformat(),desc,vat_rate,"offen"))
                st.success("Rechnung angelegt. Jetzt Positionen erfassen.")
                st.rerun()
    with tabs[2]:
        invoices = df("SELECT id, invoice_no || ' - ' || description AS label FROM invoices ORDER BY invoice_date DESC")
        if invoices.empty:
            st.info("Keine Rechnungen vorhanden.")
            return
        label = st.selectbox("Rechnung auswählen", invoices["label"].tolist(), key="items_invoice")
        iid = int(invoices[invoices["label"]==label].iloc[0]["id"])
        st.dataframe(df("SELECT position, description, quantity, unit, unit_price, total FROM invoice_items WHERE invoice_id=? ORDER BY position", (iid,)), use_container_width=True)
        with st.form("add_item"):
            a,b,c,d = st.columns(4)
            pos = a.number_input("Pos.", min_value=1, value=1, step=1)
            quantity = b.number_input("Menge", min_value=0.0, value=1.0, step=0.25)
            unit = c.text_input("Einheit", "Stunden")
            price = d.number_input("Einzelpreis", min_value=0.0, value=21.0, step=0.5)
            description = st.text_input("Bezeichnung", "Sicherheitskräfte")
            if st.form_submit_button("Position hinzufügen"):
                total = round(quantity*price, 2)
                run("INSERT INTO invoice_items(invoice_id,position,description,quantity,unit,unit_price,total) VALUES(?,?,?,?,?,?,?)", (iid,pos,description,quantity,unit,price,total))
                refresh_invoice_totals(iid)
                st.success("Position gespeichert.")
                st.rerun()
        st.subheader("Zahlung buchen")
        invrow = df("SELECT gross_total, paid_amount FROM invoices WHERE id=?", (iid,)).iloc[0]
        with st.form("pay"):
            amount = st.number_input("Zahlbetrag", min_value=0.0, value=float(invrow["gross_total"]-invrow["paid_amount"]), step=10.0)
            paid_date = st.date_input("Bezahlt am", date.today())
            if st.form_submit_button("Zahlung speichern"):
                run("UPDATE invoices SET paid_amount=COALESCE(paid_amount,0)+?, paid_date=? WHERE id=?", (amount, paid_date.isoformat(), iid))
                refresh_invoice_totals(iid)
                st.success("Zahlung gebucht.")
                st.rerun()
    with tabs[3]:
        invoices = df("SELECT id, invoice_no || ' - ' || description AS label FROM invoices ORDER BY invoice_date DESC")
        if not invoices.empty:
            label = st.selectbox("Rechnung", invoices["label"].tolist(), key="pdf_invoice")
            iid = int(invoices[invoices["label"]==label].iloc[0]["id"])
            if st.button("PDF erzeugen"):
                path = generate_invoice_pdf(iid)
                st.success(f"PDF erstellt: {path}")
            inv = df("SELECT pdf_path FROM invoices WHERE id=?", (iid,))
            pdf_path = inv.iloc[0]["pdf_path"] if not inv.empty else None
            if pdf_path and Path(pdf_path).exists():
                st.download_button("PDF herunterladen", Path(pdf_path).read_bytes(), file_name=Path(pdf_path).name, mime="application/pdf")



def login_screen():
    st.markdown("""
    <style>
    .block-container { max-width: 460px; padding-top: 60px; }
    [data-testid="stForm"] { background: #1a1f2e; border: 1px solid #2d3142; border-radius: 16px; padding: 32px; box-shadow: 0 8px 32px rgba(0,0,0,0.4); }
    </style>
    """, unsafe_allow_html=True)

    co_name = get_setting("company_name", "Byblos Sicherheitsdienst & Service")

    st.markdown('<div style="text-align:center; margin-bottom: 12px; font-size: 4rem;">🛡️</div>', unsafe_allow_html=True)
    st.markdown(f'<h2 style="text-align:center; color:#e8eaf0; margin-bottom: 4px;">Byblos CRM v2</h2>', unsafe_allow_html=True)
    st.markdown(f'<p style="text-align:center; color:#888; margin-bottom: 24px; font-size:.9rem;">{co_name}</p>', unsafe_allow_html=True)

    # Brute-Force-Schutz: max. 5 Fehlversuche in 15 Min
    try:
        recent_fails = df("""SELECT COUNT(*) AS n FROM login_attempts
                             WHERE success=0 AND attempt_time > datetime('now','-15 minutes')""")
        n_fails = int(recent_fails.iloc[0]['n']) if not recent_fails.empty else 0
        if n_fails >= 5:
            st.error(f"🚫 Zu viele Fehlversuche ({n_fails}). Bitte 15 Minuten warten.")
            st.stop()
    except Exception:
        n_fails = 0

    with st.form("login"):
        username = st.text_input("👤 Benutzername")
        password = st.text_input("🔒 Passwort", type="password")
        col1, col2 = st.columns([3, 2])
        submit = col1.form_submit_button("Einloggen", use_container_width=True, type="primary")
        if col2.form_submit_button("🔐 2FA-Code", use_container_width=True):
            st.session_state["show_2fa"] = True

    # Admin-Warnung wenn noch Standard-Passwort
    try:
        admin = df("SELECT password_hash FROM users WHERE username='admin'")
        if not admin.empty:
            from functools import reduce
            if verify_password("admin123", admin.iloc[0]["password_hash"]):
                st.warning("⚠️ **Sicherheitswarnung**: Standardpasswort aktiv. "
                           "Bitte sofort unter Einstellungen → Passwort ändern!")
    except Exception:
        pass

    st.caption("**Erstanmeldung:** admin / admin123 – bitte sofort ändern.")

    if submit:
        u = df("SELECT * FROM users WHERE username=? AND active=1", (username,))
        success = False
        if not u.empty and verify_password(password, u.iloc[0]["password_hash"]):
            success = True

            # 2FA prüfen
            tfa = df("SELECT enabled FROM two_factor_secrets WHERE username=?", (username,))
            if not tfa.empty and tfa.iloc[0]["enabled"] == 1:
                st.session_state["_pending_2fa_user"] = {
                    "username": username, "role": u.iloc[0]["role"]
                }
                st.session_state["_2fa_required"] = True
                st.rerun()
            else:
                st.session_state["user"] = {"username": username, "role": u.iloc[0]["role"]}
                log_action("login", username)

        # Login-Versuch protokollieren
        try:
            run("INSERT INTO login_attempts(username, success) VALUES(?,?)",
                (username, 1 if success else 0))
        except Exception:
            pass

        if success and not st.session_state.get("_2fa_required"):
            st.rerun()
        elif not success:
            st.error(f"❌ Login fehlgeschlagen. Versuche: {n_fails+1}/5")

    # 2FA-Eingabe
    if st.session_state.get("_2fa_required"):
        st.divider()
        st.subheader("🔐 Zwei-Faktor-Authentifizierung")
        token = st.text_input("6-stelliger Code aus Authenticator-App", max_chars=6, key="login_2fa")
        if st.button("✅ Verifizieren", type="primary"):
            try:
                from extensions_v2_prod1 import verify_totp
                pending = st.session_state.get("_pending_2fa_user", {})
                tfa_data = df("SELECT totp_secret FROM two_factor_secrets WHERE username=?",
                              (pending.get("username"),))
                if not tfa_data.empty and verify_totp(tfa_data.iloc[0]["totp_secret"], token):
                    st.session_state["user"] = pending
                    st.session_state.pop("_2fa_required", None)
                    st.session_state.pop("_pending_2fa_user", None)
                    log_action("login_2fa", pending.get("username"))
                    st.rerun()
                else:
                    st.error("❌ Falscher 2FA-Code")
            except Exception as e:
                st.error(f"2FA-Fehler: {e}")

def normalize_bank_columns(data):
    cols = {c.lower().strip(): c for c in data.columns}
    def pick(options):
        for o in options:
            if o in cols: return cols[o]
        return None
    date_col = pick(["buchungstag","buchungsdatum","booking date","datum","date"])
    value_col = pick(["valuta","wertstellung","value date"])
    name_col = pick(["auftraggeber/empfänger","name","payer_payee","beguenstigter/zahlungspflichtiger","empfänger","auftraggeber"])
    purpose_col = pick(["verwendungszweck","purpose","buchungstext","text","beschreibung"])
    amount_col = pick(["betrag","amount","umsatz","betrag eur"])
    out = pd.DataFrame()
    out["booking_date"] = data[date_col].astype(str) if date_col else ""
    out["value_date"] = data[value_col].astype(str) if value_col else out["booking_date"]
    out["payer_payee"] = data[name_col].astype(str) if name_col else ""
    out["purpose"] = data[purpose_col].astype(str) if purpose_col else ""
    if amount_col:
        out["amount"] = data[amount_col].astype(str).str.replace(".", "", regex=False).str.replace(",", ".", regex=False)
        out["amount"] = pd.to_numeric(out["amount"], errors="coerce").fillna(0.0)
    else:
        out["amount"] = 0.0
    return out

def auto_match_bank_transaction(tx_id):
    tx = df("SELECT * FROM bank_transactions WHERE id=?", (tx_id,))
    if tx.empty: return
    row = tx.iloc[0]
    purpose = str(row["purpose"] or "")
    amount = float(row["amount"] or 0)
    # Incoming money: match invoice by invoice number or exact remaining amount.
    inv = df("SELECT id, invoice_no, gross_total, paid_amount FROM invoices WHERE status!='bezahlt'")
    for _, r in inv.iterrows():
        rest = round(float(r["gross_total"] or 0) - float(r["paid_amount"] or 0), 2)
        if str(r["invoice_no"]) in purpose or (amount > 0 and abs(amount - rest) < 0.02):
            run("UPDATE bank_transactions SET matched_type='invoice', matched_id=?, status='vorgeschlagen' WHERE id=?", (int(r["id"]), tx_id))
            return
    # Outgoing money: match expense by remaining amount.
    exp = df("SELECT id, expense_no, gross_amount, paid_amount FROM expenses WHERE status!='bezahlt'")
    for _, r in exp.iterrows():
        rest = round(float(r["gross_amount"] or 0) - float(r["paid_amount"] or 0), 2)
        if str(r["expense_no"]) in purpose or (amount < 0 and abs(abs(amount) - rest) < 0.02):
            run("UPDATE bank_transactions SET matched_type='expense', matched_id=?, status='vorgeschlagen' WHERE id=?", (int(r["id"]), tx_id))
            return

def apply_bank_match(tx_id):
    tx = df("SELECT * FROM bank_transactions WHERE id=?", (tx_id,))
    if tx.empty: return "Nicht gefunden"
    row = tx.iloc[0]
    amt = float(row["amount"] or 0)
    today_s = str(row["booking_date"] or date.today().isoformat())[:10]
    if row["matched_type"] == "invoice" and row["matched_id"]:
        iid = int(row["matched_id"])
        run("UPDATE invoices SET paid_amount=COALESCE(paid_amount,0)+?, paid_date=? WHERE id=?", (max(amt,0), today_s, iid))
        refresh_invoice_totals(iid)
        run("UPDATE bank_transactions SET status='gebucht' WHERE id=?", (tx_id,))
        log_action("bank_match_invoice", f"tx={tx_id}, invoice={iid}, amount={amt}")
        return "Zahlung zur Rechnung gebucht."
    if row["matched_type"] == "expense" and row["matched_id"]:
        eid = int(row["matched_id"])
        run("UPDATE expenses SET paid_amount=COALESCE(paid_amount,0)+?, paid_date=? WHERE id=?", (abs(min(amt,0)), today_s, eid))
        refresh_expense_totals(eid)
        run("UPDATE bank_transactions SET status='gebucht' WHERE id=?", (tx_id,))
        log_action("bank_match_expense", f"tx={tx_id}, expense={eid}, amount={amt}")
        return "Zahlung zur Ausgabe gebucht."
    return "Keine Zuordnung vorhanden."

def page_bank_datev():
    st.title("Bankabgleich / DATEV")
    tabs = st.tabs(["Kontoauszug importieren", "Abgleich buchen", "DATEV-Export", "Audit"])
    with tabs[0]:
        st.subheader("CSV/Excel Kontoauszug importieren")
        st.caption("Erkannte Spalten: Datum/Buchungstag, Auftraggeber/Empfänger/Name, Verwendungszweck, Betrag/Amount.")
        f = st.file_uploader("Kontoauszug CSV/XLSX", type=["csv","xlsx","xls"])
        if f:
            if f.name.lower().endswith('.csv'):
                data = pd.read_csv(f, sep=None, engine='python')
            else:
                data = pd.read_excel(f)
            norm = normalize_bank_columns(data)
            st.dataframe(norm, use_container_width=True)
            if st.button("Importieren und automatisch zuordnen"):
                for _, r in norm.iterrows():
                    cur = run("INSERT INTO bank_transactions(booking_date,value_date,payer_payee,purpose,amount,source_file) VALUES(?,?,?,?,?,?)", (str(r['booking_date'])[:10], str(r['value_date'])[:10], r['payer_payee'], r['purpose'], float(r['amount']), f.name))
                    auto_match_bank_transaction(cur.lastrowid)
                log_action("bank_import", f.name)
                st.success("Kontoauszug importiert und Zuordnungsvorschläge erstellt.")
                st.rerun()
    with tabs[1]:
        tx = df("SELECT * FROM bank_transactions ORDER BY booking_date DESC, id DESC")
        st.dataframe(tx, use_container_width=True)
        pending = df("SELECT id, booking_date || ' | ' || amount || ' EUR | ' || COALESCE(payer_payee,'') || ' | ' || COALESCE(purpose,'') AS label FROM bank_transactions WHERE status IN ('neu','vorgeschlagen') ORDER BY id DESC")
        if not pending.empty:
            label = st.selectbox("Transaktion", pending['label'].tolist())
            txid = int(pending[pending['label']==label].iloc[0]['id'])
            col1, col2 = st.columns(2)
            with col1:
                invoices = df("SELECT id, invoice_no || ' | Rest ' || ROUND(gross_total-paid_amount,2) || ' EUR | ' || description AS label FROM invoices WHERE status!='bezahlt' ORDER BY invoice_date DESC")
                if not invoices.empty:
                    ilabel = st.selectbox("Manuell Rechnung zuordnen", [''] + invoices['label'].tolist())
                    if st.button("Rechnung setzen") and ilabel:
                        iid = int(invoices[invoices['label']==ilabel].iloc[0]['id'])
                        run("UPDATE bank_transactions SET matched_type='invoice', matched_id=?, status='vorgeschlagen' WHERE id=?", (iid, txid))
                        st.rerun()
            with col2:
                expenses = df("SELECT id, expense_no || ' | Rest ' || ROUND(gross_amount-paid_amount,2) || ' EUR | ' || description AS label FROM expenses WHERE status!='bezahlt' ORDER BY expense_date DESC")
                if not expenses.empty:
                    elabel = st.selectbox("Manuell Ausgabe zuordnen", [''] + expenses['label'].tolist())
                    if st.button("Ausgabe setzen") and elabel:
                        eid = int(expenses[expenses['label']==elabel].iloc[0]['id'])
                        run("UPDATE bank_transactions SET matched_type='expense', matched_id=?, status='vorgeschlagen' WHERE id=?", (eid, txid))
                        st.rerun()
            if st.button("Ausgewählte Zuordnung buchen"):
                st.success(apply_bank_match(txid))
                st.rerun()
    with tabs[2]:
        st.subheader("DATEV-Export-Vorbereitung")
        st.warning("Das ist ein DATEV-naher Buchungsstapel. SKR03/SKR04, Konten, BU-Schlüssel und Importformat bitte vor produktiver Nutzung vom Steuerberater bestätigen lassen.")
        month = st.text_input("Monat YYYY-MM", date.today().strftime('%Y-%m'))
        invoices = df("""SELECT invoice_date AS Belegdatum, invoice_no AS Belegfeld1, company AS Gegenkonto_Name, description AS Buchungstext,
                      gross_total AS Umsatz, vat_total AS Steuer, '8400' AS Konto_Erloese_19, '10000' AS Gegenkonto_Debitor, 'S' AS SollHaben
                      FROM invoices i JOIN customers c ON c.id=i.customer_id WHERE substr(invoice_date,1,7)=?""", (month,))
        expenses = df("""SELECT expense_date AS Belegdatum, expense_no AS Belegfeld1, COALESCE(s.name,'') AS Gegenkonto_Name, e.description AS Buchungstext,
                      e.gross_amount AS Umsatz, e.vat_amount AS Steuer, e.category AS Kostenart, '1200' AS Gegenkonto_Bank_Kasse, 'H' AS SollHaben
                      FROM expenses e LEFT JOIN suppliers s ON s.id=e.supplier_id WHERE substr(expense_date,1,7)=?""", (month,))
        st.write("Rechnungen")
        st.dataframe(invoices, use_container_width=True)
        st.write("Ausgaben")
        st.dataframe(expenses, use_container_width=True)
        out = pd.concat([invoices, expenses], ignore_index=True, sort=False)
        st.download_button("DATEV-nahen CSV-Export herunterladen", out.to_csv(index=False, sep=';').encode('utf-8-sig'), file_name=f"byblos_datev_export_{month}.csv", mime="text/csv")
    with tabs[3]:
        st.dataframe(df("SELECT * FROM audit_log ORDER BY ts DESC LIMIT 500"), use_container_width=True)

def page_users():
    st.title("Benutzer / Rechte")
    if not require_role(['Admin']):
        st.error("Nur Admins dürfen Benutzer verwalten.")
        return
    st.dataframe(df("SELECT id, username, role, active, created_at FROM users ORDER BY username"), use_container_width=True)
    with st.form("user_form"):
        a,b,c = st.columns(3)
        username = a.text_input("Benutzername")
        password = b.text_input("Passwort", type="password")
        role = c.selectbox("Rolle", ["Admin", "Büro", "Disposition", "Lesen"])
        active = st.checkbox("Aktiv", True)
        if st.form_submit_button("Benutzer anlegen") and username and password:
            run("INSERT OR REPLACE INTO users(username,password_hash,role,active) VALUES(?,?,?,?)", (username, hash_password(password), role, 1 if active else 0))
            log_action("user_saved", username)
            st.success("Benutzer gespeichert.")
            st.rerun()
    st.caption("Rollenmodell: Admin = alles; Büro = Kunden/Rechnungen/Ausgaben; Disposition = Dienstplan/Mitarbeiter; Lesen = Auswertung/Export ohne Pflege.")

def page_expenses():
    st.title("Ausgaben / BWA")
    st.caption("Für die BWA: Belege, Lieferanten, Kostenarten, Netto, Vorsteuer, Brutto, Zahlungsstatus und Monatsauswertung.")
    tabs = st.tabs(["Übersicht", "Ausgabe erfassen", "Lieferanten", "BWA-Auswertung", "Steuerberater-Export"] )
    with tabs[0]:
        q = st.text_input("Suche Ausgabe/Lieferant", "")
        query = """SELECT e.id, e.expense_no AS Nr, e.expense_date AS Datum, e.bwa_month AS Monat, s.name AS Lieferant, e.description AS Beschreibung,
                  e.category AS Kostenart, e.net_amount AS Netto, e.vat_rate AS MwSt, e.vat_amount AS Vorsteuer, e.gross_amount AS Brutto,
                  e.paid_amount AS Bezahlt, (e.gross_amount-e.paid_amount) AS Rest, e.status AS Status, e.payment_method AS Zahlung, e.receipt_path AS Beleg
                  FROM expenses e LEFT JOIN suppliers s ON s.id=e.supplier_id"""
        if q:
            data = df(query + " WHERE e.description LIKE ? OR s.name LIKE ? OR e.category LIKE ? ORDER BY e.expense_date DESC", tuple([f"%{q}%"]*3))
        else:
            data = df(query + " ORDER BY e.expense_date DESC")
        st.dataframe(data, use_container_width=True)
    with tabs[1]:
        suppliers = df("SELECT id, name FROM suppliers ORDER BY name")
        categories = df("SELECT category FROM expense_categories ORDER BY category")
        with st.form("expense_form"):
            a,b,c = st.columns(3)
            expense_no = a.text_input("Ausgaben-Nr.", next_number("expenses", "expense_no", "AUS-"))
            receipt_no = b.text_input("Beleg-/Rechnungsnummer")
            expense_date = c.date_input("Belegdatum", date.today())
            d,e,f = st.columns(3)
            supplier_name = d.selectbox("Lieferant", [""] + suppliers["name"].tolist() if not suppliers.empty else [""])
            category = e.selectbox("BWA-Kostenart", categories["category"].tolist() if not categories.empty else BWA_CATEGORIES)
            payment_method = f.selectbox("Zahlungsart", EXPENSE_PAYMENT)
            description = st.text_input("Beschreibung", "")
            a,b,c,d = st.columns(4)
            net_amount = a.number_input("Netto", min_value=0.0, value=0.0, step=10.0)
            vat_rate = b.number_input("MwSt %", min_value=0.0, value=19.0, step=1.0)
            paid_amount = c.number_input("Bezahlt", min_value=0.0, value=0.0, step=10.0)
            due_date = d.date_input("Fällig bis", date.today())
            paid_date = st.date_input("Bezahlt am", value=None)
            receipt = st.file_uploader("Beleg hochladen PDF/JPG/PNG", type=["pdf","jpg","jpeg","png"], key="expense_receipt")
            notes = st.text_area("Notizen")
            if st.form_submit_button("Ausgabe speichern") and description:
                sid = int(suppliers[suppliers["name"]==supplier_name].iloc[0]["id"]) if supplier_name and not suppliers.empty else None
                vat_amount = round(net_amount * vat_rate / 100, 2)
                gross_amount = round(net_amount + vat_amount, 2)
                if paid_amount <= 0:
                    status = "offen"
                elif paid_amount < gross_amount:
                    status = "teilbezahlt"
                else:
                    status = "bezahlt"
                receipt_path = save_uploaded_receipt(receipt)
                bwa_month = expense_date.strftime("%Y-%m")
                run("""INSERT INTO expenses(expense_no,receipt_no,supplier_id,expense_date,due_date,paid_date,description,category,net_amount,vat_rate,vat_amount,gross_amount,paid_amount,payment_method,status,receipt_path,bwa_month,notes)
                       VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (expense_no, receipt_no, sid, expense_date.isoformat(), due_date.isoformat(), paid_date.isoformat() if paid_date else None, description, category, net_amount, vat_rate, vat_amount, gross_amount, paid_amount, payment_method, status, receipt_path, bwa_month, notes))
                st.success("Ausgabe gespeichert.")
                st.rerun()
        st.subheader("Zahlung nachbuchen")
        expenses = df("SELECT id, expense_no || ' - ' || description AS label FROM expenses WHERE status!='bezahlt' ORDER BY expense_date DESC")
        if not expenses.empty:
            label = st.selectbox("Offene Ausgabe", expenses["label"].tolist())
            eid = int(expenses[expenses["label"]==label].iloc[0]["id"])
            with st.form("expense_pay"):
                amount = st.number_input("Zahlbetrag", min_value=0.0, value=0.0, step=10.0, key="expense_pay_amount")
                paid_date2 = st.date_input("Zahlungsdatum", date.today(), key="expense_paid_date2")
                if st.form_submit_button("Zahlung buchen") and amount > 0:
                    run("UPDATE expenses SET paid_amount=COALESCE(paid_amount,0)+?, paid_date=? WHERE id=?", (amount, paid_date2.isoformat(), eid))
                    refresh_expense_totals(eid)
                    st.success("Zahlung gebucht.")
                    st.rerun()
    with tabs[2]:
        st.subheader("Lieferanten")
        st.dataframe(df("SELECT * FROM suppliers ORDER BY name"), use_container_width=True)
        with st.form("supplier_form"):
            a,b = st.columns(2)
            supplier_no = a.text_input("Lieferanten-Nr.", next_number("suppliers", "supplier_no", "LF-"))
            name = b.text_input("Name")
            contact_person = a.text_input("Ansprechperson")
            phone = b.text_input("Telefon")
            email = a.text_input("E-Mail")
            tax_no = b.text_input("USt-ID/Steuernummer")
            street = a.text_input("Straße")
            zip_city = b.text_input("PLZ Ort")
            notes = st.text_area("Notizen", key="supplier_notes")
            if st.form_submit_button("Lieferant speichern") and name:
                run("INSERT INTO suppliers(supplier_no,name,contact_person,email,phone,street,zip_city,tax_no,notes) VALUES(?,?,?,?,?,?,?,?,?)", (supplier_no,name,contact_person,email,phone,street,zip_city,tax_no,notes))
                st.success("Lieferant gespeichert.")
                st.rerun()
    with tabs[3]:
        st.subheader("BWA-Auswertung")
        month = st.text_input("Monat filtern YYYY-MM leer = alle", date.today().strftime("%Y-%m"))
        params = (month,) if month else ()
        where = "WHERE bwa_month=?" if month else ""
        summary = df(f"""SELECT category AS Kostenart, COUNT(*) AS Belege, SUM(net_amount) AS Netto, SUM(vat_amount) AS Vorsteuer, SUM(gross_amount) AS Brutto, SUM(paid_amount) AS Bezahlt, SUM(gross_amount-paid_amount) AS Offen
                     FROM expenses {where} GROUP BY category ORDER BY category""", params)
        st.dataframe(summary, use_container_width=True)
        if not summary.empty:
            st.bar_chart(summary.set_index("Kostenart")[["Brutto"]])
        revenue = float(df("SELECT COALESCE(SUM(gross_total),0) AS v FROM invoices WHERE substr(invoice_date,1,7)=? AND status='bezahlt'", (month or date.today().strftime("%Y-%m"),)).iloc[0]["v"]) if month else float(df("SELECT COALESCE(SUM(gross_total),0) AS v FROM invoices WHERE status='bezahlt'").iloc[0]["v"])
        gross_exp = float(summary["Brutto"].sum()) if not summary.empty else 0.0
        st.metric("BWA-Ergebnis grob: bezahlter Umsatz minus Ausgaben brutto", f"{revenue-gross_exp:,.2f} EUR".replace(",", "X").replace(".", ",").replace("X", "."))
        st.warning("Hinweis: Das ist eine operative Auswertung für deine BWA-Vorbereitung, keine steuerliche Beratung. Kontierung bitte mit Steuerberater abstimmen.")
    with tabs[4]:
        st.subheader("Export für BWA / Steuerberater")
        export = df("""SELECT e.expense_date AS Belegdatum, e.bwa_month AS Monat, e.expense_no AS AusgabenNr, e.receipt_no AS BelegNr, s.name AS Lieferant,
                    e.description AS Buchungstext, e.category AS Kostenart, e.net_amount AS Netto, e.vat_rate AS MwStProzent, e.vat_amount AS Vorsteuer,
                    e.gross_amount AS Brutto, e.paid_amount AS Bezahlt, e.status AS Status, e.payment_method AS Zahlungsart, e.receipt_path AS Belegpfad, e.notes AS Notiz
                    FROM expenses e LEFT JOIN suppliers s ON s.id=e.supplier_id ORDER BY e.expense_date DESC""")
        st.dataframe(export, use_container_width=True)
        csv = export.to_csv(index=False, sep=';').encode('utf-8-sig')
        st.download_button("CSV für Steuerberater herunterladen", csv, file_name="byblos_ausgaben_bwa_export.csv", mime="text/csv")
        path = BASE_DIR / "byblos_bwa_ausgaben_export.xlsx"
        with pd.ExcelWriter(path, engine="openpyxl") as writer:
            export.to_excel(writer, sheet_name="Ausgaben_BWA", index=False)
            df("SELECT category,bwa_group,tax_hint FROM expense_categories ORDER BY category").to_excel(writer, sheet_name="Kostenarten", index=False)
        st.download_button("Excel für Steuerberater herunterladen", path.read_bytes(), file_name=path.name, mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

def page_schedule():
    st.title("Dienstplan")
    employees = df("SELECT id, name FROM employees WHERE active=1 ORDER BY name")
    customers = df("SELECT id, company FROM customers ORDER BY company")
    with st.form("shift"):
        a,b,c,d = st.columns(4)
        shift_date = a.date_input("Datum", date.today())
        start_time = b.time_input("Start", value=datetime.strptime("18:00", "%H:%M").time())
        end_time = c.time_input("Ende", value=datetime.strptime("23:00", "%H:%M").time())
        shift_type = d.selectbox("Typ", SHIFT_TYPES)
        emp_label = st.selectbox("Mitarbeiter", employees["name"].tolist() if not employees.empty else [])
        cust_label = st.selectbox("Kunde", customers["company"].tolist() if not customers.empty else [])
        location = st.text_input("Ort")
        notes = st.text_area("Notizen")
        if st.form_submit_button("Schicht speichern"):
            eid = int(employees[employees["name"]==emp_label].iloc[0]["id"]) if emp_label else None
            cid = int(customers[customers["company"]==cust_label].iloc[0]["id"]) if cust_label else None
            run("INSERT INTO shifts(shift_date,start_time,end_time,employee_id,customer_id,location,shift_type,notes) VALUES(?,?,?,?,?,?,?,?)", (shift_date.isoformat(), start_time.strftime("%H:%M"), end_time.strftime("%H:%M"), eid, cid, location, shift_type, notes))
            st.success("Schicht gespeichert.")
            st.rerun()
    st.subheader("Übersicht")
    start = st.date_input("Ab Datum", date.today().replace(day=1), key="schedule_start")
    st.dataframe(df("""SELECT s.shift_date AS Datum, s.start_time AS Von, s.end_time AS Bis, e.name AS Mitarbeiter, c.company AS Kunde, s.location AS Ort, s.shift_type AS Typ, s.status AS Status
                     FROM shifts s LEFT JOIN employees e ON e.id=s.employee_id LEFT JOIN customers c ON c.id=s.customer_id
                     WHERE s.shift_date>=? ORDER BY s.shift_date, s.start_time""", (start.isoformat(),)), use_container_width=True)
    st.subheader("Warnung Doppelbelegung")
    dup = df("""SELECT s1.shift_date, e.name, COUNT(*) AS Anzahl
                FROM shifts s1 JOIN employees e ON e.id=s1.employee_id
                GROUP BY s1.shift_date, s1.employee_id HAVING COUNT(*)>1""")
    st.dataframe(dup, use_container_width=True)


def page_employees():
    st.title("Mitarbeiter")
    st.dataframe(df("SELECT * FROM employees ORDER BY active DESC, name"), use_container_width=True)
    with st.form("emp"):
        a,b = st.columns(2)
        no = a.text_input("Mitarbeiternummer", next_number("employees", "employee_no", "MA-"))
        name = b.text_input("Name")
        phone = a.text_input("Telefon")
        email = b.text_input("E-Mail")
        rate = a.number_input("Stundensatz intern", min_value=0.0, value=0.0)
        active = b.checkbox("Aktiv", True)
        notes = st.text_area("Notizen")
        if st.form_submit_button("Mitarbeiter speichern") and name:
            run("INSERT INTO employees(employee_no,name,phone,email,hourly_rate,active,notes) VALUES(?,?,?,?,?,?,?)", (no,name,phone,email,rate,1 if active else 0,notes))
            st.success("Mitarbeiter gespeichert.")
            st.rerun()


def page_import():
    st.title("Import alter Rechnungen")
    st.write("PDFs oder Excel-Dateien hochladen. Die Datei wird archiviert; Rechnungsdaten kannst du danach sauber in Rechnungen übernehmen.")
    uploaded = st.file_uploader("Datei hochladen", type=["pdf", "xlsx", "xls", "csv"], accept_multiple_files=True)
    for f in uploaded:
        target = IMPORT_DIR / f.name
        target.write_bytes(f.read())
        run("INSERT INTO imports(file_name, import_status, note) VALUES(?,?,?)", (f.name, "neu", "hochgeladen"))
        st.success(f"Importiert: {f.name}")
    st.dataframe(df("SELECT * FROM imports ORDER BY created_at DESC"), use_container_width=True)


def page_export():
    st.title("Export / Backup")
    if st.button("Excel-Export erstellen"):
        path = export_excel()
        st.success(f"Export erstellt: {path.name}")
        st.download_button("Excel herunterladen", path.read_bytes(), file_name=path.name, mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    if DB_PATH.exists():
        st.download_button("SQLite-Datenbank herunterladen", DB_PATH.read_bytes(), file_name="byblos_crm_backup.db")



def page_email():
    st.title("E-Mail-Versand")
    st.caption("Rechnungen und Mahnungen als Entwurf vorbereiten oder per SMTP direkt senden.")
    tabs = st.tabs(["Rechnung/Mahnung vorbereiten", "E-Mail-Protokoll"])
    with tabs[0]:
        invoices = df("""SELECT i.id, i.invoice_no, c.company, c.email, i.description, i.gross_total, i.pdf_path,
                       i.invoice_no || ' | ' || c.company || ' | ' || ROUND(i.gross_total,2) || ' EUR' AS label
                       FROM invoices i JOIN customers c ON c.id=i.customer_id ORDER BY i.invoice_date DESC""")
        if invoices.empty:
            st.info("Keine Rechnungen vorhanden.")
        else:
            label = st.selectbox("Rechnung", invoices['label'].tolist())
            r = invoices[invoices['label']==label].iloc[0]
            kind = st.radio("Art", ["Rechnung", "Mahnung"], horizontal=True)
            recipient = st.text_input("Empfänger", str(r['email'] or ''))
            subject = st.text_input("Betreff", f"{kind} {r['invoice_no']} - Byblos Sicherheitsdienst & Service")
            default_body = f"Sehr geehrte Damen und Herren,\n\nanbei erhalten Sie unsere {kind.lower()} zur Rechnung {r['invoice_no']}.\n\nMit freundlichen Grüßen\nByblos Sicherheitsdienst & Service"
            body = st.text_area("Text", default_body, height=180)
            attachment = str(r['pdf_path'] or '')
            c1, c2 = st.columns(2)
            if c1.button("PDF erzeugen/aktualisieren"):
                path = generate_invoice_pdf(int(r['id']))
                st.success(f"PDF erstellt: {path.name}")
                st.rerun()
            if c2.button("E-Mail als Entwurf speichern") and recipient:
                queue_email(recipient, subject, body, attachment)
                st.success("E-Mail-Entwurf gespeichert.")
                st.rerun()
    with tabs[1]:
        log = df("SELECT * FROM email_log ORDER BY created_at DESC")
        st.dataframe(log, use_container_width=True)
        pending = df("SELECT id, created_at || ' | ' || recipient || ' | ' || subject AS label FROM email_log WHERE status IN ('Entwurf','Fehler') ORDER BY id DESC")
        if not pending.empty:
            label = st.selectbox("E-Mail senden", pending['label'].tolist())
            email_id = int(pending[pending['label']==label].iloc[0]['id'])
            if st.button("Jetzt per SMTP senden"):
                st.info(send_email_smtp(email_id))
                st.rerun()



def page_automation():
    st.title("Automatik / Monitoring")
    st.caption("Tagesroutinen: überfällige Rechnungen markieren, Mahnungen vorbereiten, Banktransaktionen vorschlagen, KPIs speichern und Backup prüfen.")
    tabs = st.tabs(["Tagesroutine", "Mahnungen", "KPIs", "Monitoring/Backup", "Automatik-Log"])
    with tabs[0]:
        send_now = st.checkbox("Mahnungen sofort per SMTP senden", value=get_setting('auto_send_reminders','0') == '1')
        create_backup = st.checkbox("Vollbackup nach Routine erstellen", value=True)
        if st.button("Tagesroutine jetzt ausführen"):
            for line in run_daily_automation(send_reminders=send_now, create_backup=create_backup):
                st.success(line)
        st.info("Für echte Automatik per Cron: siehe Datei `crontab_examples.txt` im Paket.")
    with tabs[1]:
        mark_overdue_invoices()
        overdue = df("""SELECT i.invoice_no, c.company, c.email, i.due_date,
                          ROUND(i.gross_total-i.paid_amount,2) AS offen, i.status
                       FROM invoices i JOIN customers c ON c.id=i.customer_id
                       WHERE i.status='ueberfaellig'
                       ORDER BY i.due_date ASC""")
        st.dataframe(overdue, use_container_width=True)
        c1, c2 = st.columns(2)
        if c1.button("Mahnungen als Entwurf vorbereiten"):
            created, sent = queue_overdue_reminders(False)
            st.success(f"{created} Mahnungen als Entwurf erstellt.")
        if c2.button("Mahnungen jetzt senden"):
            created, sent = queue_overdue_reminders(True)
            st.success(f"{created} Mahnungen vorbereitet, {sent} gesendet.")
    with tabs[2]:
        if st.button("KPIs heute berechnen"):
            st.json(calculate_daily_kpis())
        st.dataframe(df("SELECT * FROM daily_kpis ORDER BY kpi_date DESC LIMIT 60"), use_container_width=True)
    with tabs[3]:
        if st.button("Backup jetzt erstellen und prüfen"):
            b = create_full_backup('manuell über Automatik')
            ok, msg = verify_latest_backup()
            st.success(f"Backup erstellt: {b.name}")
            st.info(msg)
        ok, msg = verify_latest_backup()
        st.metric("Letztes Backup geprüft", "OK" if ok else "Problem")
        st.write(msg)
        st.code("bash scripts/check_crm.sh\nbash scripts/backup_daily.sh\nbash scripts/restore_test.sh")
    with tabs[4]:
        st.dataframe(df("SELECT * FROM automation_log ORDER BY created_at DESC LIMIT 500"), use_container_width=True)

def page_archive_gobd():
    st.title("Archiv / GoBD / Betrieb")
    st.warning("Hinweis: Diese App unterstützt Ablage, Hash-Prüfsummen, Audit-Log und Exporte. Eine vollständige GoBD-/Steuerprüfung kann nur dein Steuerberater/IT-Dienstleister bestätigen.")
    tabs = st.tabs(["Archiv", "Backups", "GoBD-Checkliste", "Systemprüfung"])
    with tabs[0]:
        st.subheader("Revisionsnahes Dokumentenarchiv")
        st.caption("Archivierte Dateien werden kopiert und mit SHA-256-Prüfsumme gespeichert. Nicht direkt im Archivordner bearbeiten.")
        st.dataframe(df("SELECT id, doc_type, ref_no, file_name, archived_at, sha256, note FROM archive_documents ORDER BY archived_at DESC"), use_container_width=True)
        up = st.file_uploader("Dokument manuell archivieren", type=['pdf','png','jpg','jpeg','xlsx','csv'])
        doc_type = st.text_input("Dokumenttyp", "Beleg")
        ref_no = st.text_input("Referenznummer", "")
        if up and st.button("Dokument archivieren"):
            temp = BASE_DIR / 'imports' / up.name
            temp.write_bytes(up.read())
            archive_file(temp, doc_type, ref_no, 'manueller Upload')
            st.success("Dokument archiviert.")
            st.rerun()
    with tabs[1]:
        st.subheader("Backups")
        if st.button("Vollbackup jetzt erstellen"):
            b = create_full_backup('manuell über App')
            st.success(f"Backup erstellt: {b.name}")
            st.download_button("Backup herunterladen", b.read_bytes(), file_name=b.name)
        backups = df("SELECT * FROM backups ORDER BY created_at DESC")
        st.dataframe(backups, use_container_width=True)
    with tabs[2]:
        checks = pd.DataFrame([
            ['Eingangsrechnungen/Belege vollständig erfassen', 'in Ausgaben/BWA + Archiv vorgesehen'],
            ['Ausgangsrechnungen als PDF sichern', 'PDF-Export archiviert automatisch mit Prüfsumme'],
            ['Änderungen nachvollziehbar machen', 'Audit-Log vorhanden'],
            ['Regelmäßige Datensicherung', 'Backup-Funktion vorhanden; externen Speicher einrichten'],
            ['DATEV/Konten final prüfen', 'mit Steuerberater abstimmen'],
            ['Zugriff schützen', 'Login/Rollen vorhanden; Admin-Passwort ändern'],
        ], columns=['Punkt', 'Umsetzung'])
        st.dataframe(checks, use_container_width=True)
    with tabs[3]:
        metrics = {
            'Kunden': int(df('SELECT COUNT(*) AS n FROM customers').iloc[0]['n']),
            'Rechnungen': int(df('SELECT COUNT(*) AS n FROM invoices').iloc[0]['n']),
            'Ausgaben': int(df('SELECT COUNT(*) AS n FROM expenses').iloc[0]['n']),
            'Archivdokumente': int(df('SELECT COUNT(*) AS n FROM archive_documents').iloc[0]['n']),
            'Backups': int(df('SELECT COUNT(*) AS n FROM backups').iloc[0]['n']),
            'Audit-Einträge': int(df('SELECT COUNT(*) AS n FROM audit_log').iloc[0]['n']),
        }
        st.json(metrics)

def page_settings():
    st.title("⚙️ Einstellungen")

    tabs = st.tabs(["🔒 Passwort", "📧 SMTP", "🏢 Firmendaten", "🖼️ Logo", "📊 BWA-Kostenarten", "🗄️ System"])

    with tabs[0]:
        st.subheader("Eigenes Passwort ändern")
        with st.form("change_pw"):
            old = st.text_input("Aktuelles Passwort", type="password")
            new1 = st.text_input("Neues Passwort (min. 8 Zeichen)", type="password")
            new2 = st.text_input("Neues Passwort wiederholen", type="password")
            if st.form_submit_button("🔒 Passwort ändern", type="primary"):
                u = current_user() or {}
                row = df("SELECT password_hash FROM users WHERE username=?", (u.get("username", ""),))
                if row.empty or not verify_password(old, row.iloc[0]["password_hash"]):
                    st.error("Aktuelles Passwort stimmt nicht.")
                elif new1 != new2:
                    st.error("Passwörter stimmen nicht überein.")
                elif len(new1) < 8:
                    st.error("Neues Passwort muss mindestens 8 Zeichen haben.")
                else:
                    run("UPDATE users SET password_hash=? WHERE username=?", (hash_password(new1), u.get("username")))
                    log_action("password_changed", u.get("username"))
                    st.success("✅ Passwort erfolgreich geändert.")

    with tabs[1]:
        st.subheader("SMTP-Einstellungen für E-Mail-Versand")
        with st.form("smtp"):
            a, b = st.columns(2)
            smtp_host = a.text_input("SMTP Host", get_setting("smtp_host", ""))
            smtp_port = b.text_input("SMTP Port", get_setting("smtp_port", "465"))
            smtp_user = a.text_input("SMTP Benutzername", get_setting("smtp_user", ""))
            smtp_password = b.text_input("SMTP Passwort / App-Passwort", get_setting("smtp_password", ""), type="password")
            smtp_sender = a.text_input("Absender-E-Mail", get_setting("smtp_sender", COMPANY.get("email", "")))
            smtp_ssl = b.checkbox("SSL/TLS (Port 465)", value=get_setting("smtp_ssl", "1") == "1")
            reminder_days = a.number_input("Mahnungs-Versand ab X Tagen nach Fälligkeit", min_value=1, value=int(get_setting("auto_reminder_days_after_due", "1")))
            auto_send = b.checkbox("Mahnungen automatisch senden", value=get_setting("auto_send_reminders", "0") == "1")
            if st.form_submit_button("💾 SMTP speichern", type="primary"):
                for k, v in [
                    ("smtp_host", smtp_host), ("smtp_port", smtp_port),
                    ("smtp_user", smtp_user), ("smtp_password", smtp_password),
                    ("smtp_sender", smtp_sender), ("smtp_ssl", "1" if smtp_ssl else "0"),
                    ("auto_reminder_days_after_due", str(reminder_days)),
                    ("auto_send_reminders", "1" if auto_send else "0"),
                ]:
                    set_setting(k, v)
                st.success("✅ SMTP-Einstellungen gespeichert.")
        # SMTP-Test
        st.subheader("SMTP testen")
        test_addr = st.text_input("Test-E-Mail an", get_setting("smtp_sender", ""))
        if st.button("📨 Test-E-Mail senden") and test_addr:
            queue_email(test_addr, "Byblos CRM – SMTP-Test", "Diese Test-E-Mail bestätigt, dass SMTP korrekt konfiguriert ist.", "")
            test_id = df("SELECT id FROM email_log ORDER BY id DESC LIMIT 1")
            if not test_id.empty:
                result = send_email_smtp(int(test_id.iloc[0]["id"]))
                st.info(result)

    with tabs[2]:
        st.subheader("Firmendaten bearbeiten")
        with st.form("company_form"):
            a, b = st.columns(2)
            c_name = a.text_input("Firmenname", get_setting("company_name", COMPANY.get("name", "")))
            c_street = b.text_input("Straße", get_setting("company_street", COMPANY.get("street", "")))
            c_zip = a.text_input("PLZ Ort", get_setting("company_zip_city", COMPANY.get("zip_city", "")))
            c_phone = b.text_input("Telefon", get_setting("company_phone", COMPANY.get("phone", "")))
            c_email = a.text_input("E-Mail", get_setting("company_email", COMPANY.get("email", "")))
            c_web = b.text_input("Website", get_setting("company_web", COMPANY.get("website", "")))
            c_tax = a.text_input("Steuernummer", get_setting("company_tax_no", COMPANY.get("tax_no", "")))
            c_ust = b.text_input("USt-ID", get_setting("company_ust_id", COMPANY.get("ust_id", "")))
            c_iban = a.text_input("IBAN", get_setting("company_iban", COMPANY.get("iban", "")))
            c_bic = b.text_input("BIC", get_setting("company_bic", COMPANY.get("bic", "")))
            c_bank = a.text_input("Bank", get_setting("company_bank", COMPANY.get("bank", "")))
            if st.form_submit_button("💾 Firmendaten speichern", type="primary"):
                for k, v in [
                    ("company_name", c_name), ("company_street", c_street),
                    ("company_zip_city", c_zip), ("company_phone", c_phone),
                    ("company_email", c_email), ("company_web", c_web),
                    ("company_tax_no", c_tax), ("company_ust_id", c_ust),
                    ("company_iban", c_iban), ("company_bic", c_bic), ("company_bank", c_bank),
                ]:
                    set_setting(k, v)
                st.success("✅ Firmendaten gespeichert. Neue PDFs verwenden diese Daten.")

    with tabs[3]:
        st.subheader("Logo hochladen")
        logo = st.file_uploader("Logo als PNG (empfohlen: 400×150 px)", type=["png", "jpg", "jpeg"])
        if logo:
            (ASSET_DIR / "logo.png").write_bytes(logo.read())
            st.success("✅ Logo gespeichert.")
        if (ASSET_DIR / "logo.png").exists():
            st.image(str(ASSET_DIR / "logo.png"), width=250, caption="Aktuelles Logo")

    with tabs[4]:
        st.subheader("BWA-Kostenarten verwalten")
        cats = df("SELECT id, category, bwa_group, tax_hint FROM expense_categories ORDER BY category")
        st.dataframe(cats, use_container_width=True)
        with st.form("cat_form", clear_on_submit=True):
            a, b, c = st.columns(3)
            cat_name = a.text_input("Neue Kostenart")
            bwa_group = b.text_input("BWA-Gruppe")
            tax_hint = c.text_input("Steuerhinweis")
            if st.form_submit_button("➕ Kostenart hinzufügen") and cat_name:
                run("INSERT OR IGNORE INTO expense_categories(category,bwa_group,tax_hint) VALUES(?,?,?)",
                    (cat_name, bwa_group, tax_hint))
                st.success(f"Kostenart '{cat_name}' gespeichert.")
                st.rerun()

    with tabs[5]:
        st.subheader("Systeminformationen")
        st.code(f"Datenbank: {DB_PATH}\nBasisverzeichnis: {BASE_DIR}\nAssets: {ASSET_DIR}")
        db_size = DB_PATH.stat().st_size if DB_PATH.exists() else 0
        log_count = int(df("SELECT COUNT(*) AS n FROM audit_log").iloc[0]["n"])
        c1, c2, c3 = st.columns(3)
        c1.metric("Datenbankgröße", f"{db_size/1024:.0f} KB")
        c2.metric("Audit-Log-Einträge", log_count)
        c3.metric("CRM-Version", "2.0.0")
        st.subheader("Audit-Log (letzte 100 Einträge)")
        audit = df("SELECT created_at AS Zeit, username AS Benutzer, action AS Aktion, details AS Details FROM audit_log ORDER BY created_at DESC LIMIT 100")
        if not audit.empty:
            st.dataframe(audit, use_container_width=True, height=350)
        if st.button("⬇️ Audit-Log als CSV herunterladen"):
            full_log = df("SELECT * FROM audit_log ORDER BY created_at DESC")
            csv = full_log.to_csv(index=False, sep=";").encode("utf-8-sig")
            st.download_button("💾 CSV herunterladen", csv, "audit_log.csv", "text/csv")


def main():
    style()
    init_db()
    if 'user' not in st.session_state:
        login_screen()
        return

    # Benachrichtigungen in Sidebar anzeigen
    try:
        from extensions_v2_enhancements import show_notification_bell
        show_notification_bell(df)
    except Exception:
        pass

    page = sidebar()

    # Nav-Override durch Schnellaktionen
    if "_nav_override" in st.session_state:
        page = st.session_state.pop("_nav_override")

    # Mobile CSS-Optimierung
    try:
        from extensions_v2_sysutils import inject_mobile_css
        inject_mobile_css()
    except Exception:
        pass
    # Schwarzes Brett Pinned Posts in Sidebar
    try:
        from extensions_v2_liveops_extra import render_bulletin_board_sidebar
        render_bulletin_board_sidebar(df)
    except Exception:
        pass
    # Render favorites bar
    try:
        from extensions_v2_fieldops import render_favorites_bar
        render_favorites_bar(df, run, current_user)
    except Exception:
        pass
    # Track page visit
    try:
        from extensions_v2_fieldops import track_page_visit
        track_page_visit(run, current_user, page)
    except Exception:
        pass
    # Render notification bell in sidebar
    try:
        from extensions_v2_security import render_notification_bell
        render_notification_bell(df, run, current_user)
    except Exception:
        pass

    if page == "Dashboard":
        try:
            from extensions_v2_business_ops import render_daily_briefing
            render_daily_briefing(df, get_setting)
        except Exception:
            pass
        try:
            from extensions_v2_ultra import check_onboarding_complete
            if not check_onboarding_complete(df):
                st.info("🚀 **Einrichtung unvollständig** – [Onboarding-Assistent öffnen](#)")
        except Exception:
            pass
        try:
            from extensions_v2_polish import render_startup_tips, check_session_timeout
            check_session_timeout()
            render_startup_tips(df)
        except Exception:
            pass
        try:
            from extensions_v2_enhancements import page_dashboard_v2
            page_dashboard_v2(run, df)
        except Exception:
            page_dashboard()
    elif page == "Kunden":
        try:
            from extensions_v2_pages import page_customers_v2
            page_customers_v2(run, df, next_number, log_action)
        except Exception:
            page_customers()
    elif page == "Kontakte":
        try:
            from extensions_v2_core_pages import page_contacts_v2
            page_contacts_v2(run, df, next_number, log_action)
        except Exception:
            page_contacts()
    elif page == "Rechnungen":
        try:
            from extensions_v2_core_pages import page_invoices_v2
            page_invoices_v2(run, df, next_number, log_action, refresh_invoice_totals, generate_invoice_pdf)
        except Exception:
            page_invoices()
    elif page == "Ausgaben/BWA":
        try:
            from extensions_v2_expenses_reporting import page_expenses_v2
            page_expenses_v2(run, df, next_number, log_action,
                             save_uploaded_receipt, refresh_expense_totals,
                             BWA_CATEGORIES, EXPENSE_PAYMENT)
        except Exception:
            page_expenses()
    elif page == "Bank/DATEV":
        try:
            from extensions_v2_final import page_bank_datev_v2
            page_bank_datev_v2(run, df, log_action, normalize_bank_columns,
                               auto_match_bank_transaction, apply_bank_match)
        except Exception:
            page_bank_datev()
    elif page == "Intelligenter Import":
        try:
            from extensions_v2_prod1 import page_smart_import_v2
            page_smart_import_v2(run, df, next_number, log_action,
                                  extract_pdf_text, refresh_invoice_totals, BASE_DIR)
        except Exception:
            page_smart_import()
    elif page == "Mehrfach-Rechnungsimport": page_bulk_invoice_import(run, df, queue_dataframe_import, process_import_queue_item, extract_pdf_text, extract_image_text, enqueue_import)
    elif page == "Schnellsuche/KI": page_quick_search_ai(run, df)
    elif page == "Firmenprofile": page_company_profiles(run, df, ASSET_DIR, COMPANY)
    elif page == "Verträge & Dokumente": page_contracts_documents(run, df)
    elif page == "SystemPlus Cockpit": page_systemplus_cockpit(run, df)
    elif page == "Live-Betrieb": page_liveops_cockpit(run, df)
    elif page == "Rollenmatrix": page_role_permissions_matrix(run, df)
    elif page == "Kundenportal": page_customer_portal_prep(run, df)
    elif page == "Leistungs-Checklisten": page_service_checklists(run, df)
    elif page == "Compliance & Recht": page_compliance_center(run, df)
    elif page == "Export & Backup Center":
        try:
            from extensions_v2_pages import page_export_v2
            page_export_v2(run, df, DB_PATH, export_excel, create_full_backup)
        except Exception:
            page_export_backup_center(run, df, DB_PATH)
    elif page == "Field-Ops Cockpit": page_fieldops_cockpit(run, df)
    elif page == "Mitarbeiter Einsatz": page_employees_field(run, df)
    elif page == "Objekte": page_objects_field(run, df)
    elif page == "Einsatzplanung": page_shift_planner(run, df)
    elif page == "Leistungsnachweise": page_service_reports(run, df)
    elif page == "Field-Ops Export": page_fieldops_exports(run, df)
    elif page == "E-Rechnung": page_einvoice_center(run, df, BASE_DIR)
    elif page == "E-Rechnung Prüfung": page_einvoice_validation(run, df)
    elif page == "Zahlungen & Mahnwesen": page_payments_reminders(run, df)
    elif page == "Offene Posten": page_open_items_control(run, df)
    elif page == "Zeiterfassung": page_time_tracking(run, df)
    elif page == "Zeiten freigeben": page_time_approval_billing(run, df)
    elif page == "Zeitkonto & Payroll": page_time_accounts_absences(run, df)
    elif page == "Ops Prüfungen": page_ops_quality_checks(run, df)
    elif page == "Dienstplan":
        try:
            from extensions_v2_pages import page_schedule_v2
            page_schedule_v2(run, df, log_action)
        except Exception:
            page_schedule()
    elif page == "Mitarbeiter":
        try:
            from extensions_v2_pages import page_employees_v2
            page_employees_v2(run, df, next_number, log_action)
        except Exception:
            page_employees()
    elif page == "Import":
        try:
            from extensions_v2_final import page_import_v2
            page_import_v2(run, df, BASE_DIR, next_number, log_action,
                           extract_pdf_text, refresh_invoice_totals, refresh_invoice_totals)
        except Exception:
            page_import()
    elif page == "Export/Backup":
        try:
            from extensions_v2_pages import page_export_v2
            page_export_v2(run, df, DB_PATH, export_excel, create_full_backup)
        except Exception:
            page_export()
    elif page == "E-Mail":
        try:
            from extensions_v2_pages import page_email_v2
            page_email_v2(run, df, generate_invoice_pdf, queue_email, send_email_smtp)
        except Exception:
            page_email()
    elif page == "Automatik":
        try:
            from extensions_v2_core_pages import page_automation_v2
            page_automation_v2(run, df, log_action, mark_overdue_invoices, run_daily_automation,
                               queue_overdue_reminders, calculate_daily_kpis,
                               create_full_backup, verify_latest_backup, get_setting)
        except Exception:
            page_automation()
    elif page == "Archiv/GoBD":
        try:
            from extensions_v2_core_pages import page_archive_v2
            page_archive_v2(run, df, BASE_DIR, log_action)
        except Exception:
            page_archive_gobd()
    elif page == "Benutzer/Rechte":
        try:
            from extensions_v2_core_pages import page_users_v2
            page_users_v2(run, df, hash_password, current_user, log_action)
        except Exception:
            page_users()
    elif page == "Einstellungen": page_settings()
    elif page == "KI-Auswertungen":
        try:
            from ml_logic import page_ki_dashboard
            page_ki_dashboard(df)
        except Exception as e:
            st.error(f"KI-Modul Fehler: {e}")
    elif page == "Lieferanten":
        try:
            from extensions_v2_final import page_suppliers_v2
            page_suppliers_v2(run, df, next_number, log_action)
        except Exception as e:
            st.error(f"Lieferanten-Fehler: {e}")
    elif page == "Globale Suche":
        try:
            from extensions_v2_polish import page_global_search
            page_global_search(df)
        except Exception as e:
            st.error(f"Fehler: {e}")
    elif page == "Massenaktionen":
        try:
            from extensions_v2_polish import page_bulk_actions
            page_bulk_actions(run, df, log_action, refresh_invoice_totals,
                              generate_invoice_pdf, queue_email)
        except Exception as e:
            st.error(f"Fehler: {e}")
    elif page == "PDF-Berichte":
        try:
            from extensions_v2_polish import page_pdf_report
            page_pdf_report(df, BASE_DIR)
        except Exception as e:
            st.error(f"Fehler: {e}")
    elif page == "Systemgesundheit":
        try:
            from extensions_v2_final import page_system_health
            page_system_health(run, df, DB_PATH)
        except Exception as e:
            st.error(f"Fehler: {e}")
    elif page == "DATEV-Mapping":
        try:
            from extensions_v2_new3 import page_datev_mapping
            page_datev_mapping(run, df)
        except Exception as e:
            st.error(f"Fehler: {e}")
    elif page == "Push-Benachrichtigungen":
        try:
            from extensions_v2_new3 import page_notifications_setup
            page_notifications_setup(run, df, get_setting, set_setting)
        except Exception as e:
            st.error(f"Fehler: {e}")
    elif page == "Betriebskosten":
        try:
            from extensions_v2_new3 import page_operations_dashboard
            page_operations_dashboard(df)
        except Exception as e:
            st.error(f"Fehler: {e}")
    elif page == "Qualitätschecklisten":
        try:
            from extensions_v2_new3 import page_quality_checklists
            page_quality_checklists(run, df, log_action)
        except Exception as e:
            st.error(f"Fehler: {e}")
    elif page == "Notfallkontakte":
        try:
            from extensions_v2_new3 import page_emergency_contacts
            page_emergency_contacts(run, df, log_action)
        except Exception as e:
            st.error(f"Fehler: {e}")
    elif page == "Lohnabrechnung":
        try:
            from extensions_v2_new4 import page_payroll
            page_payroll(run, df, log_action, get_setting, BASE_DIR)
        except Exception as e:
            st.error(f"Fehler: {e}")
    elif page == "Einsatzberichte":
        try:
            from extensions_v2_new4 import page_mission_reports
            page_mission_reports(run, df, get_setting, BASE_DIR)
        except Exception as e:
            st.error(f"Fehler: {e}")
    elif page == "Aging-Report":
        try:
            from extensions_v2_new4 import page_aging_report
            page_aging_report(df)
        except Exception as e:
            st.error(f"Fehler: {e}")
    elif page == "Wiedervorlagen":
        try:
            from extensions_v2_new4 import page_followup_calendar
            page_followup_calendar(run, df, log_action)
        except Exception as e:
            st.error(f"Fehler: {e}")
    elif page == "Qualifikationen":
        try:
            from extensions_v2_new5 import page_qualifications
            page_qualifications(run, df, log_action)
        except Exception as e:
            st.error(f"Fehler: {e}")
    elif page == "Schichttausch":
        try:
            from extensions_v2_new5 import page_shift_exchange
            page_shift_exchange(run, df, log_action, current_user)
        except Exception as e:
            st.error(f"Fehler: {e}")
    elif page == "SEPA-Lastschrift":
        try:
            from extensions_v2_new5 import page_sepa_export
            page_sepa_export(run, df, get_setting)
        except Exception as e:
            st.error(f"Fehler: {e}")
    elif page == "Kostenvoranschlag":
        try:
            from extensions_v2_new5 import page_cost_estimate
            page_cost_estimate(run, df, next_number, log_action, get_setting)
        except Exception as e:
            st.error(f"Fehler: {e}")
    elif page == "Liquiditätsplanung":
        try:
            from extensions_v2_systemplus import page_liquidity_planning
            page_liquidity_planning(df)
        except Exception as e:
            st.error(f"Fehler: {e}")
    elif page == "Validierungs-Center":
        try:
            from extensions_v2_systemplus import page_validation_center
            page_validation_center(run, df)
        except Exception as e:
            st.error(f"Fehler: {e}")
    elif page == "Genehmigungs-Workflow":
        try:
            from extensions_v2_systemplus import page_approval_workflow
            page_approval_workflow(run, df, log_action, current_user, get_setting, set_setting)
        except Exception as e:
            st.error(f"Fehler: {e}")
    elif page == "Lieferscheine":
        try:
            from extensions_v2_systemplus import page_delivery_notes
            page_delivery_notes(run, df, next_number, log_action, get_setting, BASE_DIR)
        except Exception as e:
            st.error(f"Fehler: {e}")
    elif page == "Webhooks":
        try:
            from extensions_v2_systemplus import page_webhooks
            page_webhooks(run, df, log_action)
        except Exception as e:
            st.error(f"Fehler: {e}")
    elif page == "Schicht-Vorlagen":
        try:
            from extensions_v2_systemplus import page_shift_templates
            page_shift_templates(run, df, log_action)
        except Exception as e:
            st.error(f"Fehler: {e}")
    elif page == "Backup-Verschlüsselung":
        try:
            from extensions_v2_systemplus import page_backup_encryption
            page_backup_encryption(run, df, BASE_DIR)
        except Exception as e:
            st.error(f"Fehler: {e}")
    elif page == "Personalkosten":
        try:
            from extensions_v2_systemplus import page_personnel_costs
            page_personnel_costs(df)
        except Exception as e:
            st.error(f"Fehler: {e}")
    elif page == "Hinweis-Center":
        try:
            from extensions_v2_systemplus import page_notifications_bell
            page_notifications_bell(run, df, current_user)
        except Exception as e:
            st.error(f"Fehler: {e}")
    elif page == "Buchungsjournal":
        try:
            from extensions_v2_payroll_recon_ops import page_booking_journal
            page_booking_journal(df)
        except Exception as e:
            st.error(f"Fehler: {e}")
    elif page == "Kassenbuch":
        try:
            from extensions_v2_payroll_recon_ops import page_cash_book
            page_cash_book(run, df, log_action, current_user)
        except Exception as e:
            st.error(f"Fehler: {e}")
    elif page == "Reisekosten":
        try:
            from extensions_v2_payroll_recon_ops import page_travel_expenses
            page_travel_expenses(run, df, next_number, log_action, current_user)
        except Exception as e:
            st.error(f"Fehler: {e}")
    elif page == "Personalplanung":
        try:
            from extensions_v2_payroll_recon_ops import page_staffing_overview
            page_staffing_overview(df)
        except Exception as e:
            st.error(f"Fehler: {e}")
    elif page == "Kostenstellen":
        try:
            from extensions_v2_payroll_recon_ops import page_cost_centers
            page_cost_centers(run, df, next_number, log_action)
        except Exception as e:
            st.error(f"Fehler: {e}")
    elif page == "Debitorenkonten":
        try:
            from extensions_v2_payroll_recon_ops import page_debtor_account
            page_debtor_account(df)
        except Exception as e:
            st.error(f"Fehler: {e}")
    elif page == "UStVA":
        try:
            from extensions_v2_payroll_recon_ops import page_ustv_a
            page_ustv_a(df, get_setting, set_setting)
        except Exception as e:
            st.error(f"Fehler: {e}")
    elif page == "Objekte":
        try:
            from extensions_v2_einvoice_time import page_objects
            page_objects(run, df, next_number, log_action)
        except Exception as e:
            st.error(f"Fehler: {e}")
    elif page == "Wachbuch":
        try:
            from extensions_v2_einvoice_time import page_watch_log
            page_watch_log(run, df, current_user)
        except Exception as e:
            st.error(f"Fehler: {e}")
    elif page == "Unfallmeldungen":
        try:
            from extensions_v2_einvoice_time import page_incident_reports
            page_incident_reports(run, df, next_number, log_action)
        except Exception as e:
            st.error(f"Fehler: {e}")
    elif page == "Schlüssel":
        try:
            from extensions_v2_einvoice_time import page_key_management
            page_key_management(run, df, next_number, log_action)
        except Exception as e:
            st.error(f"Fehler: {e}")
    elif page == "§34a Compliance":
        try:
            from extensions_v2_einvoice_time import page_gewa34a_center
            page_gewa34a_center(df, run)
        except Exception as e:
            st.error(f"Fehler: {e}")
    elif page == "Tages-Briefing":
        try:
            from extensions_v2_business_ops import page_daily_briefing
            page_daily_briefing(df, get_setting)
        except Exception as e:
            st.error(f"Fehler: {e}")
    elif page == "KPI-Ziele":
        try:
            from extensions_v2_business_ops import page_kpi_goals
            page_kpi_goals(run, df)
        except Exception as e:
            st.error(f"Fehler: {e}")
    elif page == "CLV-Analyse":
        try:
            from extensions_v2_business_ops import page_clv_analysis
            page_clv_analysis(df)
        except Exception as e:
            st.error(f"Fehler: {e}")
    elif page == "Schicht-Konflikte":
        try:
            from extensions_v2_business_ops import page_shift_conflicts
            page_shift_conflicts(df)
        except Exception as e:
            st.error(f"Fehler: {e}")
    elif page == "ArbZG-Monitor":
        try:
            from extensions_v2_business_ops import page_arbzg_monitor
            page_arbzg_monitor(df)
        except Exception as e:
            st.error(f"Fehler: {e}")
    elif page == "Währungsrechner":
        try:
            from extensions_v2_business_ops import page_currency_calculator
            page_currency_calculator(get_setting, set_setting)
        except Exception as e:
            st.error(f"Fehler: {e}")
    elif page == "Lieferanten-Bewertung":
        try:
            from extensions_v2_business_ops import page_supplier_ratings
            page_supplier_ratings(run, df, current_user)
        except Exception as e:
            st.error(f"Fehler: {e}")
    elif page == "Einsatzkalkulator":
        try:
            from extensions_v2_business_ops import page_deployment_calculator
            page_deployment_calculator(df)
        except Exception as e:
            st.error(f"Fehler: {e}")
    elif page == "Zahlungs-E-Mail":
        try:
            from extensions_v2_business_ops import page_payment_email_settings
            page_payment_email_settings(run, df, get_setting, set_setting)
        except Exception as e:
            st.error(f"Fehler: {e}")
    elif page == "Schwarzes Brett":
        try:
            from extensions_v2_liveops_extra import page_bulletin_board
            page_bulletin_board(run, df, current_user)
        except Exception as e:
            st.error(f"Fehler: {e}")
    elif page == "Überstunden-Konto":
        try:
            from extensions_v2_liveops_extra import page_overtime_account
            page_overtime_account(run, df)
        except Exception as e:
            st.error(f"Fehler: {e}")
    elif page == "DynDNS":
        try:
            from extensions_v2_finance_time_ops import page_dyndns_manager
            page_dyndns_manager(run, df, get_setting, set_setting)
        except Exception as e:
            st.error(f"Fehler: {e}")
    elif page in ("Remote-Zugang", "Netzwerk-Status"):
        try:
            from extensions_v2_remote_access import page_network_access
            page_network_access(run, df, get_setting, set_setting)
        except Exception as e:
            st.error(f"Fehler: {e}")
    elif page == "Protokoll-Export":
        try:
            from extensions_v2_sysutils import page_protocol_export
            page_protocol_export(df, BASE_DIR)
        except Exception as e:
            st.error(f"Fehler: {e}")
    elif page == "Passwort-Generator":
        try:
            from extensions_v2_sysutils import page_password_generator
            page_password_generator(run, df, hash_password)
        except Exception as e:
            st.error(f"Fehler: {e}")
    elif page == "Updates":
        try:
            from extensions_v2_sysutils import page_update_checker
            page_update_checker(get_setting, set_setting)
        except Exception as e:
            st.error(f"Fehler: {e}")
    elif page == "System-Health":
        try:
            from extensions_v2_liveops_extra import page_system_health
            page_system_health(df, DB_PATH)
        except Exception as e:
            st.error(f"Fehler: {e}")
    elif page == "Backup-Manager":
        try:
            from extensions_v2_liveops_extra import page_backup_manager
            page_backup_manager(run, df, create_full_backup, DB_PATH)
        except Exception as e:
            st.error(f"Fehler: {e}")
    elif page == "Dashboard anpassen":
        try:
            from extensions_v2_liveops_extra import page_dashboard_config
            page_dashboard_config(run, df, current_user)
        except Exception as e:
            st.error(f"Fehler: {e}")
    elif page == "Benutzer & Rollen":
        try:
            from extensions_v2_liveops_extra import page_role_management
            page_role_management(run, df, current_user, hash_password)
        except Exception as e:
            st.error(f"Fehler: {e}")
    elif page == "Kundenportal":
        try:
            from extensions_v2_liveops_extra import page_customer_portal_preview
            page_customer_portal_preview(df)
        except Exception as e:
            st.error(f"Fehler: {e}")
    elif page == "Einsatzplanung Events":
        try:
            from extensions_v2_fieldops_extra import page_event_security
            page_event_security(run, df, next_number, log_action)
        except Exception as e:
            st.error(f"Fehler: {e}")
    elif page == "Dienstanweisungen":
        try:
            from extensions_v2_fieldops_extra import page_duty_instructions
            page_duty_instructions(run, df, next_number, log_action, get_setting, BASE_DIR)
        except Exception as e:
            st.error(f"Fehler: {e}")
    elif page == "Wartungsverträge":
        try:
            from extensions_v2_fieldops_extra import page_maintenance_contracts
            page_maintenance_contracts(run, df, next_number, log_action, get_setting)
        except Exception as e:
            st.error(f"Fehler: {e}")
    elif page == "Kundenzufriedenheit":
        try:
            from extensions_v2_fieldops_extra import page_satisfaction_surveys
            page_satisfaction_surveys(run, df, next_number, log_action, queue_email, get_setting)
        except Exception as e:
            st.error(f"Fehler: {e}")
    elif page == "Darlehen":
        try:
            from extensions_v2_fieldops_extra import page_loan_tracking
            page_loan_tracking(run, df, next_number, log_action)
        except Exception as e:
            st.error(f"Fehler: {e}")
    elif page == "Wissensdatenbank":
        try:
            from extensions_v2_fieldops_extra import page_wiki
            page_wiki(run, df, current_user)
        except Exception as e:
            st.error(f"Fehler: {e}")
    elif page == "ZUGFeRD Einbetten":
        try:
            from extensions_v2_automation_ops import page_zugferd_embed
            page_zugferd_embed(df, get_setting, BASE_DIR)
        except Exception as e:
            st.error(f"Fehler: {e}")
    elif page == "Cloud-Backup Plus":
        try:
            from extensions_v2_automation_ops import page_cloud_backup_extended
            page_cloud_backup_extended(run, df, get_setting, set_setting, create_full_backup, BASE_DIR)
        except Exception as e:
            st.error(f"Fehler: {e}")
    elif page == "Stripe":
        try:
            from extensions_v2_automation_ops import page_stripe_integration
            page_stripe_integration(df, get_setting, set_setting, run)
        except Exception as e:
            st.error(f"Fehler: {e}")
    elif page in ("Lohnsteuer-Export", "ELMA5"):
        try:
            from extensions_v2_automation_ops import page_elma5_export
            page_elma5_export(df, get_setting)
        except Exception as e:
            st.error(f"Fehler: {e}")
    elif page == "VCard-Import":
        try:
            from extensions_v2_automation_ops import page_vcard_import
            page_vcard_import(run, df, next_number, log_action)
        except Exception as e:
            st.error(f"Fehler: {e}")
    elif page == "Schichtpräferenzen":
        try:
            from extensions_v2_automation_ops import page_shift_preferences
            page_shift_preferences(run, df, log_action)
        except Exception as e:
            st.error(f"Fehler: {e}")
    elif page == "Reklamationen":
        try:
            from extensions_v2_automation_ops import page_complaints
            page_complaints(run, df, next_number, log_action)
        except Exception as e:
            st.error(f"Fehler: {e}")
    elif page == "Eskalations-Mahnwesen":
        try:
            from extensions_v2_automation_ops import page_escalation_management
            page_escalation_management(run, df, log_action, queue_email, get_setting)
        except Exception as e:
            st.error(f"Fehler: {e}")
    elif page == "Gewinn-je-Stunde":
        try:
            from extensions_v2_automation_ops import page_profit_per_hour
            page_profit_per_hour(df)
        except Exception as e:
            st.error(f"Fehler: {e}")
    elif page == "Projekt-Gantt":
        try:
            from extensions_v2_automation_ops import page_gantt_chart
            page_gantt_chart(df)
        except Exception as e:
            st.error(f"Fehler: {e}")
    elif page == "Break-Even":
        try:
            from extensions_v2_fieldops import page_breakeven_calculator
            page_breakeven_calculator(df)
        except Exception as e:
            st.error(f"Fehler: {e}")
    elif page == "Duplikat-Check":
        try:
            from extensions_v2_fieldops import page_duplicate_detection
            page_duplicate_detection(df, run)
        except Exception as e:
            st.error(f"Fehler: {e}")
    elif page == "Sammelrechnung":
        try:
            from extensions_v2_fieldops import page_batch_invoice
            page_batch_invoice(run, df, next_number, log_action, refresh_invoice_totals)
        except Exception as e:
            st.error(f"Fehler: {e}")
    elif page == "Freigabe-Workflow":
        try:
            from extensions_v2_fieldops import page_invoice_approval
            page_invoice_approval(run, df, log_action, current_user)
        except Exception as e:
            st.error(f"Fehler: {e}")
    elif page == "Budgetwarnungen":
        try:
            from extensions_v2_fieldops import page_budget_warnings
            page_budget_warnings(run, df)
        except Exception as e:
            st.error(f"Fehler: {e}")
    elif page == "Inventar":
        try:
            from extensions_v2_fieldops import page_inventory
            page_inventory(run, df, next_number, log_action)
        except Exception as e:
            st.error(f"Fehler: {e}")
    elif page == "Heatmap-Kalender":
        try:
            from extensions_v2_fieldops import page_heatmap_calendar
            page_heatmap_calendar(df)
        except Exception as e:
            st.error(f"Fehler: {e}")
    elif page == "Prognose-Dashboard":
        try:
            from extensions_v2_fieldops import page_forecast_dashboard
            page_forecast_dashboard(df)
        except Exception as e:
            st.error(f"Fehler: {e}")
    elif page == "Favoriten":
        try:
            from extensions_v2_fieldops import page_favorites_manager
            page_favorites_manager(run, df, current_user)
        except Exception as e:
            st.error(f"Fehler: {e}")
    elif page == "Zapier-Templates":
        try:
            from extensions_v2_fieldops import page_zapier_templates
            page_zapier_templates(get_setting)
        except Exception as e:
            st.error(f"Fehler: {e}")
    elif page == "Benachrichtigungen":
        try:
            from extensions_v2_security import page_notifications_manager
            page_notifications_manager(run, df, current_user)
        except Exception as e:
            st.error(f"Fehler: {e}")
    elif page == "ZUGFeRD E-Rechnung":
        try:
            from extensions_v2_security import page_zugferd_export
            page_zugferd_export(df, get_setting, BASE_DIR)
        except Exception as e:
            st.error(f"Fehler: {e}")
    elif page == "Signaturen":
        try:
            from extensions_v2_security import page_document_signatures
            page_document_signatures(run, df, get_setting, queue_email, log_action)
        except Exception as e:
            st.error(f"Fehler: {e}")
    elif page == "DB-Migrationen":
        try:
            from extensions_v2_security import page_schema_migrations
            page_schema_migrations(df)
        except Exception as e:
            st.error(f"Fehler: {e}")
    elif page == "Rate-Limiting":
        try:
            from extensions_v2_security import page_rate_limit_monitor
            page_rate_limit_monitor(df, run)
        except Exception as e:
            st.error(f"Fehler: {e}")
    elif page == "WhatsApp":
        try:
            from extensions_v2_security import page_whatsapp_integration
            page_whatsapp_integration(run, df, get_setting, set_setting)
        except Exception as e:
            st.error(f"Fehler: {e}")
    elif page == "Kunden v2":
        try:
            from extensions_v2_security import page_customers_with_scoring
            page_customers_with_scoring(df, run, next_number, log_action)
        except Exception as e:
            st.error(f"Fehler: {e}")
    elif page == "Angebot-zu-Rechnung":
        try:
            from extensions_v2_liveops import page_offer_to_invoice
            page_offer_to_invoice(run, df, next_number, log_action, refresh_invoice_totals)
        except Exception as e:
            st.error(f"Fehler: {e}")
    elif page == "Kunden-Timeline":
        try:
            from extensions_v2_liveops import page_customer_timeline
            page_customer_timeline(df)
        except Exception as e:
            st.error(f"Fehler: {e}")
    elif page == "Personalakte":
        try:
            from extensions_v2_liveops import page_personnel_file
            page_personnel_file(run, df, log_action, BASE_DIR)
        except Exception as e:
            st.error(f"Fehler: {e}")
    elif page == "Deckungsbeitrag":
        try:
            from extensions_v2_liveops import page_contribution_margin
            page_contribution_margin(run, df, log_action)
        except Exception as e:
            st.error(f"Fehler: {e}")
    elif page == "XLSX-Rechnungsimport":
        try:
            from extensions_v2_liveops import page_xlsx_invoice_import
            page_xlsx_invoice_import(run, df, next_number, log_action, refresh_invoice_totals)
        except Exception as e:
            st.error(f"Fehler: {e}")
    elif page == "Verschlüsseltes Backup":
        try:
            from extensions_v2_liveops import page_encrypted_backup
            page_encrypted_backup(run, df, create_full_backup)
        except Exception as e:
            st.error(f"Fehler: {e}")
    elif page == "Performance-Monitor":
        try:
            from extensions_v2_liveops import page_performance_monitor
            page_performance_monitor(run, df, DB_PATH)
        except Exception as e:
            st.error(f"Fehler: {e}")
    elif page == "Sprache":
        try:
            from extensions_v2_xtra import page_language_settings
            page_language_settings(get_setting, set_setting)
        except Exception as e:
            st.error(f"Fehler: {e}")
    elif page == "OCR-Belegerfassung":
        try:
            from extensions_v2_xtra import page_ocr_import
            page_ocr_import(run, df, BASE_DIR)
        except Exception as e:
            st.error(f"Fehler: {e}")
    elif page == "Zahlungslinks":
        try:
            from extensions_v2_xtra import page_payment_links
            page_payment_links(run, df, get_setting, set_setting)
        except Exception as e:
            st.error(f"Fehler: {e}")
    elif page == "Webhooks":
        try:
            from extensions_v2_xtra import page_webhook_management
            page_webhook_management(run, df, log_action)
        except Exception as e:
            st.error(f"Fehler: {e}")
    elif page == "Mobile-Modus":
        try:
            from extensions_v2_xtra import page_mobile_mode
            page_mobile_mode(get_setting, set_setting)
        except Exception as e:
            st.error(f"Fehler: {e}")
    elif page == "FastAPI-Server":
        try:
            from extensions_v2_xtra import page_api_server_info
            page_api_server_info(run, df, get_setting)
        except Exception as e:
            st.error(f"Fehler: {e}")
    elif page == "Stornorechnungen":
        try:
            from extensions_v2_complete import page_storno_invoices
            page_storno_invoices(run, df, next_number, log_action, get_setting, refresh_invoice_totals, BASE_DIR)
        except Exception as e:
            st.error(f"Fehler: {e}")
    elif page == "Überstunden-Ausgleich":
        try:
            from extensions_v2_complete import page_overtime_compensation
            page_overtime_compensation(run, df, log_action, current_user)
        except Exception as e:
            st.error(f"Fehler: {e}")
    elif page == "Minijobler-Rechner":
        try:
            from extensions_v2_complete import page_minijob_calculator
            page_minijob_calculator(run, df)
        except Exception as e:
            st.error(f"Fehler: {e}")
    elif page == "Vertragsüberwachung":
        try:
            from extensions_v2_complete import page_contract_monitoring
            page_contract_monitoring(run, df, next_number, log_action)
        except Exception as e:
            st.error(f"Fehler: {e}")
    elif page == "BWA-Jahresvergleich":
        try:
            from extensions_v2_complete import page_bwa_comparison
            page_bwa_comparison(df)
        except Exception as e:
            st.error(f"Fehler: {e}")
    elif page == "DSGVO-Center":
        try:
            from extensions_v2_complete import page_gdpr_center
            page_gdpr_center(run, df, log_action, current_user)
        except Exception as e:
            st.error(f"Fehler: {e}")
    elif page == "Serienbrief":
        try:
            from extensions_v2_complete import page_serial_letters
            page_serial_letters(run, df, log_action, queue_email, get_setting)
        except Exception as e:
            st.error(f"Fehler: {e}")
    elif page == "GPS-Stempeluhr":
        try:
            from extensions_v2_ultra import page_gps_checkin
            page_gps_checkin(run, df, log_action, current_user)
        except Exception as e:
            st.error(f"Fehler: {e}")
    elif page == "Mahngebühren":
        try:
            from extensions_v2_ultra import page_late_fees
            page_late_fees(run, df, log_action, refresh_invoice_totals)
        except Exception as e:
            st.error(f"Fehler: {e}")
    elif page == "KI-Chatbot":
        try:
            from extensions_v2_ultra import page_ai_chatbot
            page_ai_chatbot(df)
        except Exception as e:
            st.error(f"Fehler: {e}")
    elif page == "Executive Summary":
        try:
            from extensions_v2_ultra import page_executive_summary
            page_executive_summary(df, get_setting, BASE_DIR)
        except Exception as e:
            st.error(f"Fehler: {e}")
    elif page == "Onboarding-Assistent":
        try:
            from extensions_v2_ultra import page_onboarding
            page_onboarding(run, df, get_setting)
        except Exception as e:
            st.error(f"Fehler: {e}")
    elif page == "Druckansicht Dienstplan":
        try:
            from extensions_v2_prod2 import page_print_schedule
            page_print_schedule(df)
        except Exception as e:
            st.error(f"Fehler: {e}")
    elif page == "Mein Bereich":
        try:
            from extensions_v2_prod2 import page_employee_portal
            page_employee_portal(df, current_user)
        except Exception as e:
            st.error(f"Fehler: {e}")
    elif page == "Interne Nachrichten":
        try:
            from extensions_v2_prod2 import page_internal_chat
            page_internal_chat(run, df, current_user)
        except Exception as e:
            st.error(f"Fehler: {e}")
    elif page == "Zwei-Faktor-Auth":
        try:
            from extensions_v2_prod1 import page_two_factor
            page_two_factor(run, df, hash_password, verify_password, current_user)
        except Exception as e:
            st.error(f"Fehler: {e}")
    elif page == "Angebots-PDF":
        try:
            from extensions_v2_prod1 import page_offer_pdf
            page_offer_pdf(run, df, get_setting, BASE_DIR)
        except Exception as e:
            st.error(f"Fehler: {e}")
    elif page == "Lohnzettel-Versand":
        try:
            from extensions_v2_prod1 import page_payroll_email
            page_payroll_email(run, df, queue_email, send_email_smtp, get_setting, BASE_DIR)
        except Exception as e:
            st.error(f"Fehler: {e}")
    elif page == "Rechnungsnummern-Check":
        try:
            from extensions_v2_prod1 import page_invoice_number_check
            page_invoice_number_check(df)
        except Exception as e:
            st.error(f"Fehler: {e}")
    elif page == "Projekt-zu-Rechnung":
        try:
            from extensions_v2_prod1 import page_project_to_invoice
            page_project_to_invoice(run, df, next_number, log_action, refresh_invoice_totals)
        except Exception as e:
            st.error(f"Fehler: {e}")
    elif page == "Kalender-Export":
        try:
            from extensions_v2_final2 import page_ical_export
            page_ical_export(df)
        except Exception as e:
            st.error(f"Fehler: {e}")
    elif page == "KI-Suche":
        try:
            from extensions_v2_final2 import page_semantic_search
            page_semantic_search(df)
        except Exception as e:
            st.error(f"Fehler: {e}")
    elif page == "BWA-Auto":
        try:
            from extensions_v2_final2 import page_bank_auto_categorize
            page_bank_auto_categorize(run, df)
        except Exception as e:
            st.error(f"Fehler: {e}")
    elif page == "Cloud-Backup":
        try:
            from extensions_v2_final2 import page_cloud_backup
            page_cloud_backup(run, df, get_setting, set_setting, DB_PATH, create_full_backup)
        except Exception as e:
            st.error(f"Fehler: {e}")
    elif page == "Live-Betrieb":
        try:
            from extensions_v2_final2 import page_live_operations
            page_live_operations(df)
        except Exception as e:
            st.error(f"Fehler: {e}")
    elif page == "JSON-API":
        try:
            from extensions_v2_new5 import page_api_center
            page_api_center(run, df, get_setting, set_setting)
        except Exception as e:
            st.error(f"Fehler: {e}")
    elif page == "Dauerrechnungen":
        try:
            from extensions_v2_new1 import page_recurring_invoices
            page_recurring_invoices(run, df, next_number, log_action,
                                    refresh_invoice_totals, generate_invoice_pdf,
                                    queue_email, get_setting)
        except Exception as e:
            st.error(f"Fehler: {e}")
    elif page == "Steuerkalender":
        try:
            from extensions_v2_new1 import page_tax_calendar
            page_tax_calendar(run, df)
        except Exception as e:
            st.error(f"Fehler: {e}")
    elif page == "QR & Zahlung":
        try:
            from extensions_v2_new1 import page_qr_settings
            page_qr_settings(run, df, get_setting, set_setting)
        except Exception as e:
            st.error(f"Fehler: {e}")
    elif page == "Urlaubsplanung":
        try:
            from extensions_v2_new2 import page_leave_planning
            page_leave_planning(run, df, log_action, current_user)
        except Exception as e:
            st.error(f"Fehler: {e}")
    elif page == "Fahrtenbuch":
        try:
            from extensions_v2_new2 import page_mileage_log
            page_mileage_log(run, df, next_number, log_action)
        except Exception as e:
            st.error(f"Fehler: {e}")
    elif page == "SLA-Monitoring":
        try:
            from extensions_v2_new2 import page_sla_monitoring
            page_sla_monitoring(run, df, next_number, log_action)
        except Exception as e:
            st.error(f"Fehler: {e}")
    elif page == "Projekte":
        try:
            from extensions_v2_new2 import page_project_tracking
            page_project_tracking(run, df, next_number, log_action)
        except Exception as e:
            st.error(f"Fehler: {e}")
    # v2-Seiten
    elif page == "Benachrichtigungen":
        try:
            from extensions_v2_enhancements import page_notifications
            page_notifications(run, df)
        except Exception as e:
            st.error(f"Fehler: {e}")
    elif page == "Angebote":
        try:
            from extensions_v2_enhancements import page_offers
            page_offers(run, df)
        except Exception as e:
            st.error(f"Fehler: {e}")
    elif page == "Schichtübergabe":
        try:
            from extensions_v2_enhancements import page_handover_protocol
            page_handover_protocol(run, df)
        except Exception as e:
            st.error(f"Fehler: {e}")
    elif page == "Reporting-Center":
        try:
            from extensions_v2_expenses_reporting import page_reporting_center
            page_reporting_center(run, df, BASE_DIR)
        except Exception as e:
            st.error(f"Fehler: {e}")
    elif page == "Berichte":
        try:
            from extensions_v2_enhancements import page_reports
            page_reports(run, df)
        except Exception as e:
            st.error(f"Fehler: {e}")


if __name__ == "__main__":
    main()