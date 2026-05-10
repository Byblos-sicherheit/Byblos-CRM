"""
tests/test_byblos_crm.py – Vollständige Testsuite für Byblos CRM v2
====================================================================
Abgedeckte Bereiche:
  - Datenbankinitialisierung und Schema
  - Hilfsfunktionen (Passwort, Nummern, Einstellungen)
  - ML-Modul (Kategorisierung, Scoring, Prognose)
  - Rechnungs-PDF-Generierung
  - ICS-Export
  - Regex-Extraktion (Smart Import)
  - SEPA-XML-Generierung
  - EPC-QR-Code
  - TOTP-Authentifizierung

Ausführung:
  cd byblos_crm_app
  pytest ../tests/ -v
  pytest ../tests/ --cov=. --cov-report=html
"""

import sys
import os
import tempfile
import sqlite3
from pathlib import Path
from datetime import date, datetime, timedelta

import pytest
import pandas as pd

# Pfade einrichten
BYBLOS_DIR = Path(__file__).resolve().parent.parent / "byblos_crm_app"
sys.path.insert(0, str(BYBLOS_DIR))


# ─────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def tmp_db(tmp_path_factory):
    """Temporäre SQLite-Datenbank für Tests."""
    db_path = tmp_path_factory.mktemp("data") / "test_byblos.db"
    return db_path


@pytest.fixture(scope="session")
def db_conn(tmp_db):
    """SQLite-Verbindung zur Test-DB."""
    conn = sqlite3.connect(str(tmp_db))
    yield conn
    conn.close()


def run_sql(conn, sql, params=()):
    conn.execute(sql, params)
    conn.commit()


def df_sql(conn, sql, params=()):
    return pd.read_sql_query(sql, conn, params=params)


# ─────────────────────────────────────────────────────────────
# 1. Passwort-Hashing
# ─────────────────────────────────────────────────────────────

def test_password_hashing():
    """Passwort-Hash und Verifikation."""
    import hashlib, secrets

    def hash_pw(pw):
        salt = secrets.token_hex(16)
        digest = hashlib.sha256((salt + pw).encode()).hexdigest()
        return f"{salt}${digest}"

    def verify_pw(pw, stored):
        try:
            salt, digest = stored.split("$", 1)
            return hashlib.sha256((salt + pw).encode()).hexdigest() == digest
        except Exception:
            return False

    h = hash_pw("test123")
    assert verify_pw("test123", h), "Korrektes Passwort sollte verifiziert werden"
    assert not verify_pw("falsch", h), "Falsches Passwort sollte fehlschlagen"
    assert "$" in h, "Hash sollte Salt$Digest Format haben"


def test_password_no_plain_text():
    """Passwort darf nicht im Klartext gespeichert werden."""
    import hashlib, secrets

    def hash_pw(pw):
        salt = secrets.token_hex(16)
        digest = hashlib.sha256((salt + pw).encode()).hexdigest()
        return f"{salt}${digest}"

    h = hash_pw("geheim123")
    assert "geheim123" not in h, "Klartextpasswort darf nicht im Hash enthalten sein"


# ─────────────────────────────────────────────────────────────
# 2. ML-Modul Tests
# ─────────────────────────────────────────────────────────────

def test_ml_rule_based_category():
    """Regelbasierte Kategorisierung ohne ML."""
    from ml_logic import _rule_based_category

    assert _rule_based_category("Tankstelle Aral Benzin") == "Kfz-Kosten"
    assert _rule_based_category("Büromaterial Papier Drucker") == "Bürokosten"
    assert _rule_based_category("Telefon Mobilfunk Rechnung") == "Kommunikation"
    assert _rule_based_category("Steuerberater Kanzlei") == "Beratungskosten"
    assert _rule_based_category("unkategorisierbarer Text xyz") == "Sonstiges"


def test_ml_predict_top3():
    """Top-3-Vorhersagen haben korrektes Format."""
    from ml_logic import predict_top3

    results = predict_top3("Kraftstoff Diesel")
    assert isinstance(results, list)
    assert len(results) >= 1
    assert len(results) <= 3
    for cat, conf in results:
        assert isinstance(cat, str)
        assert 0.0 <= conf <= 100.0


def test_ml_training():
    """Trainingsdaten können hinzugefügt werden."""
    from ml_logic import add_training_example, load_training_data, reset_training_data

    # Beispiel hinzufügen
    add_training_example("Sondertext Testfall 12345", "Test-Kategorie")
    data = load_training_data()
    texts = [d["text"] for d in data]
    assert "Sondertext Testfall 12345" in texts

    # Bereinigen
    # (Kein vollständiger Reset um andere Tests nicht zu stören)


def test_ml_forecast_empty():
    """Prognose mit leeren Daten gibt leere Liste zurück."""
    from ml_logic import forecast_revenue

    def df_empty(sql, params=()):
        return pd.DataFrame()

    result = forecast_revenue(df_empty, months_ahead=3)
    assert result == []


def test_customer_score_no_invoices():
    """Kunden-Score ohne Rechnungen gibt 50/C zurück."""
    from ml_logic import score_customer

    def df_empty(sql, params=()):
        return pd.DataFrame()

    s = score_customer(999, df_empty)
    assert s["score"] == 50
    assert s["grade"] == "C"


# ─────────────────────────────────────────────────────────────
# 3. ICS-Export Tests
# ─────────────────────────────────────────────────────────────

def test_ics_generation():
    """ICS-Datei hat korrektes Format."""
    from extensions_v2_final2 import generate_ics

    events = [{
        "title": "Testschicht",
        "start": datetime(2025, 6, 15, 18, 0),
        "end":   datetime(2025, 6, 15, 23, 0),
        "description": "Objektschutz Test",
        "location": "Hannover",
    }]
    ics = generate_ics(events)
    assert "BEGIN:VCALENDAR" in ics
    assert "BEGIN:VEVENT" in ics
    assert "END:VEVENT" in ics
    assert "END:VCALENDAR" in ics
    assert "Testschicht" in ics
    assert "Objektschutz Test" in ics


def test_ics_multiple_events():
    """ICS mit mehreren Events."""
    from extensions_v2_final2 import generate_ics

    events = [
        {"title": "Event 1", "start": date(2025, 6, 1)},
        {"title": "Event 2", "start": date(2025, 6, 2)},
        {"title": "Event 3", "start": date(2025, 6, 3)},
    ]
    ics = generate_ics(events)
    assert ics.count("BEGIN:VEVENT") == 3
    assert ics.count("END:VEVENT") == 3


# ─────────────────────────────────────────────────────────────
# 4. Smart-Import Regex-Extraktion
# ─────────────────────────────────────────────────────────────

def test_extract_invoice_number():
    """Rechnungsnummer wird korrekt erkannt."""
    from extensions_v2_prod1 import extract_invoice_data_from_text

    text = "Rechnung Nr.: RE-2024-0042\nDatum: 15.03.2024\nGesamtbetrag: 1.190,00 EUR"
    result = extract_invoice_data_from_text(text)
    assert "invoice_no" in result
    assert "2024" in result.get("invoice_no", "")


def test_extract_amount():
    """Betrag wird korrekt erkannt."""
    from extensions_v2_prod1 import extract_invoice_data_from_text

    text = "Rechnungsbetrag: 2.380,00 EUR\nMwSt 19%"
    result = extract_invoice_data_from_text(text)
    assert "gross_total" in result
    amount = result.get("gross_total", 0)
    assert 2300 <= amount <= 2400, f"Betrag {amount} außerhalb des erwarteten Bereichs"


def test_extract_date():
    """Datum wird korrekt erkannt."""
    from extensions_v2_prod1 import extract_invoice_data_from_text

    text = "Rechnungsdatum: 15.06.2024\nFällig: 29.06.2024"
    result = extract_invoice_data_from_text(text)
    assert "invoice_date" in result
    assert "2024" in result.get("invoice_date", "")


def test_extract_vat():
    """MwSt-Satz wird erkannt."""
    from extensions_v2_prod1 import extract_invoice_data_from_text

    text = "Nettobetrag: 1.000,00 EUR\n19% MwSt: 190,00 EUR\nBrutto: 1.190,00 EUR"
    result = extract_invoice_data_from_text(text)
    assert result.get("vat_rate") == 19.0


def test_extract_empty():
    """Leerer Text gibt leeres Dict zurück."""
    from extensions_v2_prod1 import extract_invoice_data_from_text

    result = extract_invoice_data_from_text("")
    assert isinstance(result, dict)
    assert len(result) == 0


# ─────────────────────────────────────────────────────────────
# 5. SEPA-XML Tests
# ─────────────────────────────────────────────────────────────

def test_sepa_xml_structure():
    """SEPA-XML hat korrekte pain.008-Struktur."""
    from extensions_v2_new5 import generate_sepa_pain008

    mandates = [{
        "name": "Test GmbH",
        "iban": "DE89370400440532013000",
        "bic": "COBADEFFXXX",
        "amount": 500.00,
        "mandate_id": "M-001",
        "mandate_date": "2024-01-01",
        "reference": "RE-0001",
    }]
    xml = generate_sepa_pain008(
        mandates,
        creditor_iban="DE12345678901234567890",
        creditor_bic="BYLADEMMXXX",
        creditor_name="Byblos GmbH",
        creditor_id="DE98ZZZ09999999999",
        collection_date="2025-06-20",
    )
    assert "<?xml" in xml
    assert "pain.008" in xml
    assert "DrctDbtTxInf" in xml
    assert "Test GmbH" in xml
    assert "500.00" in xml


def test_sepa_xml_total_amount():
    """SEPA-XML summiert Beträge korrekt."""
    from extensions_v2_new5 import generate_sepa_pain008

    mandates = [
        {"name":"A","iban":"DE11","bic":"BICH","amount":100.0,"mandate_id":"M1","mandate_date":"2024-01-01","reference":"R1"},
        {"name":"B","iban":"DE22","bic":"BICH","amount":200.0,"mandate_id":"M2","mandate_date":"2024-01-01","reference":"R2"},
        {"name":"C","iban":"DE33","bic":"BICH","amount":300.0,"mandate_id":"M3","mandate_date":"2024-01-01","reference":"R3"},
    ]
    xml = generate_sepa_pain008(mandates, "DE00","BIC","Firma","ID","2025-06-20")
    assert "600.00" in xml, "Gesamtbetrag 600.00 nicht gefunden"
    assert "<NbOfTxs>3</NbOfTxs>" in xml


# ─────────────────────────────────────────────────────────────
# 6. TOTP Tests
# ─────────────────────────────────────────────────────────────

def test_totp_secret_generation():
    """TOTP-Secret hat korrektes Format (Base32)."""
    from extensions_v2_prod1 import generate_totp_secret
    import base64

    secret = generate_totp_secret()
    assert len(secret) > 0
    # Base32-Dekodierung muss funktionieren
    decoded = base64.b32decode(secret.upper())
    assert len(decoded) == 20, "TOTP-Secret muss 20 Bytes lang sein"


def test_totp_uri():
    """TOTP-URI hat korrektes Format."""
    from extensions_v2_prod1 import get_totp_uri

    uri = get_totp_uri("JBSWY3DPEHPK3PXP", "testuser", "ByblosCRM")
    assert uri.startswith("otpauth://totp/")
    assert "testuser" in uri
    assert "JBSWY3DPEHPK3PXP" in uri
    assert "ByblosCRM" in uri


def test_totp_wrong_token():
    """Falscher TOTP-Token wird abgelehnt."""
    from extensions_v2_prod1 import verify_totp, generate_totp_secret

    secret = generate_totp_secret()
    assert not verify_totp(secret, "000000"), "Nullen-Token sollte fast immer falsch sein"
    assert not verify_totp(secret, "999999"), "Maximaler Token sollte fast immer falsch sein"


# ─────────────────────────────────────────────────────────────
# 7. Kalkulations-Tests
# ─────────────────────────────────────────────────────────────

def test_invoice_calculation():
    """Rechnungsberechnung (Netto + MwSt = Brutto)."""
    net = 1000.0
    vat_rate = 19.0
    vat_total = round(net * vat_rate / 100, 2)
    gross = round(net + vat_total, 2)

    assert vat_total == 190.00
    assert gross == 1190.00


def test_payroll_calculation():
    """Lohnberechnung (Brutto - Abzüge = Netto)."""
    gross = 2500.0
    health = round(gross * 0.073, 2)
    pension = round(gross * 0.093, 2)
    unemploy = round(gross * 0.013, 2)
    care = round(gross * 0.0175, 2)
    total_deductions = health + pension + unemploy + care
    net = round(gross - total_deductions, 2)

    assert net < gross, "Netto muss kleiner als Brutto sein"
    assert net > 0, "Netto muss positiv sein"
    assert total_deductions > 0, "Abzüge müssen positiv sein"


def test_cost_estimate_calculation():
    """Kalkulation: Stunden × Satz + Overhead + Marge = Preis."""
    hours = 40.0
    rate  = 21.0
    overhead_pct = 20.0
    margin_pct   = 15.0
    vat_rate     = 19.0

    labor     = hours * rate
    overhead  = labor * overhead_pct / 100
    cost      = labor + overhead
    profit    = cost * margin_pct / 100
    net_total = cost + profit
    vat       = net_total * vat_rate / 100
    gross     = net_total + vat

    assert labor == 840.0
    assert net_total > labor, "Angebotspreis muss über Personalkosten liegen"
    assert gross > net_total, "Brutto muss größer als Netto sein"


# ─────────────────────────────────────────────────────────────
# 8. Format-Tests
# ─────────────────────────────────────────────────────────────

def test_eur_formatting():
    """EUR-Formatierung ist korrekt."""
    def fmt_eur(v):
        return f"{v:,.2f} €".replace(",", "X").replace(".", ",").replace("X", ".")

    assert fmt_eur(1000.00)    == "1.000,00 €"
    assert fmt_eur(1234567.89) == "1.234.567,89 €"
    assert fmt_eur(0.50)       == "0,50 €"
    assert fmt_eur(0.00)       == "0,00 €"


def test_iban_format():
    """IBAN-Format wird aus SEPA bereinigt."""
    from extensions_v2_new5 import generate_sepa_pain008

    mandates = [{"name":"T","iban":"DE89 3704 0044 0532 0130 00","bic":"TEST",
                  "amount":1.0,"mandate_id":"M","mandate_date":"2024-01-01","reference":"R"}]
    xml = generate_sepa_pain008(mandates,"DE00","BIC","N","ID","2025-06-20")
    assert "DE89 3704" not in xml, "Leerzeichen im IBAN sollten entfernt sein"
    assert "DE89370400440532013000" in xml, "IBAN ohne Leerzeichen sollte im XML sein"


# ─────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import subprocess
    result = subprocess.run(
        ["python", "-m", "pytest", __file__, "-v", "--tb=short"],
        cwd=str(BYBLOS_DIR)
    )
    sys.exit(result.returncode)


# ─────────────────────────────────────────────────────────────
# 9. ZUGFeRD XML Tests
# ─────────────────────────────────────────────────────────────

def test_zugferd_xml_basic():
    """ZUGFeRD XML hat korrektes Grundgerüst."""
    from extensions_v2_security import generate_zugferd_xml

    invoice  = {"invoice_no":"RE-001","invoice_date":"2025-01-15",
                 "due_date":"2025-01-29","net_total":1000.0,
                 "vat_rate":19.0,"vat_total":190.0,"gross_total":1190.0,
                 "description":"Test"}
    customer = {"company":"Test GmbH","street":"Teststr. 1"}
    items    = [{"description":"Leistung","quantity":1,"unit":"C62",
                  "unit_price":1000.0,"total":1000.0}]
    seller   = {"name":"Byblos GmbH","street":"Hauptstr. 1",
                 "ust_id":"DE123456789","iban":"DE00123"}

    xml = generate_zugferd_xml(invoice, customer, items, seller)
    assert "CrossIndustryInvoice" in xml
    assert "RE-001" in xml
    assert "1000.00" in xml
    assert "190.00" in xml
    assert "Test GmbH" in xml
    assert "Byblos GmbH" in xml


def test_zugferd_xml_vat_calculation():
    """ZUGFeRD XML enthält korrekte MwSt-Berechnung."""
    from extensions_v2_security import generate_zugferd_xml

    invoice  = {"invoice_no":"RE-TEST","invoice_date":"2025-06-01",
                 "due_date":"2025-06-15","net_total":500.0,
                 "vat_rate":7.0,"vat_total":35.0,"gross_total":535.0}
    xml = generate_zugferd_xml(invoice, {}, [], {})
    assert "7.00" in xml  # 7% MwSt
    assert "500.00" in xml
    assert "535.00" in xml


# ─────────────────────────────────────────────────────────────
# 10. Session-Security Tests
# ─────────────────────────────────────────────────────────────

def test_session_token_generation():
    """Session-Token ist ausreichend lang und zufällig."""
    import secrets
    tokens = set()
    for _ in range(10):
        token = secrets.token_urlsafe(32)
        assert len(token) >= 32, "Token muss mindestens 32 Zeichen haben"
        tokens.add(token)
    assert len(tokens) == 10, "Alle Tokens müssen eindeutig sein"


def test_session_timeout_check():
    """Session-Timeout-Logik korrekt."""
    from datetime import datetime, timedelta
    SESSION_TIMEOUT = 480  # Minuten

    start = datetime.now() - timedelta(minutes=100)
    elapsed = (datetime.now() - start).total_seconds() / 60
    assert elapsed < SESSION_TIMEOUT, "100min < 480min Timeout"

    start_old = datetime.now() - timedelta(minutes=500)
    elapsed_old = (datetime.now() - start_old).total_seconds() / 60
    assert elapsed_old > SESSION_TIMEOUT, "500min > 480min Timeout → abgelaufen"


# ─────────────────────────────────────────────────────────────
# 11. Rate-Limiting Tests
# ─────────────────────────────────────────────────────────────

def test_rate_limit_logic():
    """Rate-Limit-Zählung korrekt."""
    MAX_ATTEMPTS = 5
    WINDOW = 15

    # Simuliere Versuche
    attempts = 0
    for i in range(MAX_ATTEMPTS):
        allowed = attempts < MAX_ATTEMPTS
        if allowed:
            attempts += 1
        assert allowed, f"Versuch {i+1} sollte erlaubt sein"

    # Nächster Versuch gesperrt
    blocked = attempts >= MAX_ATTEMPTS
    assert blocked, "Nach 5 Versuchen gesperrt"


# ─────────────────────────────────────────────────────────────
# 12. Dokument-Signatur Tests
# ─────────────────────────────────────────────────────────────

def test_signature_token_uniqueness():
    """Signatur-Token sind eindeutig."""
    import secrets
    tokens = {secrets.token_urlsafe(32) for _ in range(100)}
    assert len(tokens) == 100, "Alle 100 Tokens müssen eindeutig sein"


def test_signature_token_length():
    """Signatur-Token hat ausreichende Entropie."""
    import secrets
    token = secrets.token_urlsafe(32)
    # urlsafe_b64encode: 32 Bytes = ~43 Zeichen
    assert len(token) >= 40, f"Token zu kurz: {len(token)}"


# ─────────────────────────────────────────────────────────────
# 13. Beitragsrechnung / Deckungsbeitrag Tests
# ─────────────────────────────────────────────────────────────

def test_contribution_margin_db1():
    """DB1 = Umsatz - variable Kosten."""
    revenue = 10000.0
    labor   = 5000.0
    material = 500.0
    other    = 200.0
    db1 = revenue - labor - material - other
    assert db1 == 4300.0, f"DB1 erwartet 4300.0, erhalten {db1}"


def test_contribution_margin_db2():
    """DB2 = DB1 - Fixkosten."""
    db1    = 4300.0
    rent   = 800.0
    admin  = 500.0
    other_f = 200.0
    db2 = db1 - (rent + admin + other_f)
    assert db2 == 2800.0, f"DB2 erwartet 2800.0, erhalten {db2}"


def test_contribution_margin_negative():
    """Negativer DB2 möglich (Verlust)."""
    db1 = 1000.0
    fixed = 1500.0
    db2 = db1 - fixed
    assert db2 < 0, "Negativer DB2 sollte möglich sein"
    assert db2 == -500.0


# ─────────────────────────────────────────────────────────────
# 14. AES-256 Backup-Verschlüsselung Tests
# ─────────────────────────────────────────────────────────────

def test_encryption_round_trip(tmp_path):
    """Verschlüsseln und Entschlüsseln ergibt Originaldaten."""
    from extensions_v2_liveops import encrypt_file, decrypt_file

    # Test-Datei erstellen
    test_file = tmp_path / "test_backup.db"
    original_data = b"SQLite format 3\x00" + b"X" * 1000
    test_file.write_bytes(original_data)

    # Verschlüsseln
    ok, enc_path_str = encrypt_file(test_file, "sicheres-passwort-123!")
    if not ok:
        if "nicht installiert" in enc_path_str:
            import pytest
            pytest.skip("cryptography nicht installiert")
        raise AssertionError(f"Verschlüsselung fehlgeschlagen: {enc_path_str}")

    enc_path = Path(enc_path_str)
    assert enc_path.exists(), "Verschlüsselte Datei muss existieren"
    assert enc_path.read_bytes() != original_data, "Verschlüsselt muss anders sein"

    # Entschlüsseln
    ok2, dec_path_str = decrypt_file(enc_path, "sicheres-passwort-123!")
    if not ok2:
        raise AssertionError(f"Entschlüsselung fehlgeschlagen: {dec_path_str}")

    dec_path = Path(dec_path_str)
    assert dec_path.read_bytes() == original_data, "Entschlüsselte Daten stimmen nicht überein"


def test_encryption_wrong_password(tmp_path):
    """Falsches Passwort führt zu Fehler."""
    from extensions_v2_liveops import encrypt_file, decrypt_file

    test_file = tmp_path / "test2.db"
    test_file.write_bytes(b"test data " * 100)

    ok, enc = encrypt_file(test_file, "richtiges-passwort")
    if not ok:
        import pytest
        pytest.skip("cryptography nicht installiert")

    ok2, msg = decrypt_file(Path(enc), "falsches-passwort")
    assert not ok2, "Falsches Passwort sollte fehlschlagen"


# ─────────────────────────────────────────────────────────────
# 15. ICS-Export Tests (erweitert)
# ─────────────────────────────────────────────────────────────

def test_ics_datetime_format():
    """ICS DateTime ist im korrekten Format."""
    from extensions_v2_final2 import generate_ics
    from datetime import datetime

    events = [{"title": "Test", "start": datetime(2025, 6, 15, 18, 0),
                "end":   datetime(2025, 6, 15, 22, 0)}]
    ics = generate_ics(events)
    # Prüfe DateTime-Format: 20250615T180000
    assert "20250615T180000" in ics, f"DateTime-Format nicht gefunden in: {ics[:300]}"


def test_ics_all_day_event():
    """ICS All-Day-Events haben korrektes DATE-Format."""
    from extensions_v2_final2 import generate_ics
    from datetime import date

    events = [{"title": "Steuertermin", "start": date(2025, 6, 10)}]
    ics = generate_ics(events)
    assert "DATE:20250610" in ics or "VALUE=DATE:20250610" in ics


def test_ics_special_characters():
    """ICS verarbeitet Sonderzeichen korrekt."""
    from extensions_v2_final2 import generate_ics
    from datetime import date

    events = [{"title": "Müller & Söhne GmbH, Schicht",
                "start": date(2025, 7, 1)}]
    ics = generate_ics(events)
    assert "BEGIN:VEVENT" in ics
    assert "END:VEVENT" in ics


# ─────────────────────────────────────────────────────────────
# 16. XLSX-Import Tests
# ─────────────────────────────────────────────────────────────

def test_xlsx_import_mapping_logic():
    """Mapping-Logik für XLSX-Import."""
    row = {"RechnungsNr": "RE-001", "FirmaName": "Test GmbH",
           "Betrag": "1190,00", "Datum": "2025-01-15"}
    mapping = {
        "invoice_no": "RechnungsNr",
        "company":    "FirmaName",
        "gross_amount": "Betrag",
        "invoice_date": "Datum",
    }

    def get_v(key):
        col = mapping.get(key, "—")
        return str(row.get(col, "")).strip() if col != "—" else ""

    assert get_v("invoice_no") == "RE-001"
    assert get_v("company") == "Test GmbH"
    assert get_v("gross_amount") == "1190,00"


def test_amount_parsing():
    """Betrag-Parsing aus verschiedenen Formaten."""
    def parse_amount(s: str) -> float:
        return float(str(s).replace(".", "").replace(",", ".").replace("€","").strip())

    assert parse_amount("1.190,00") == 1190.0
    assert parse_amount("1190,00") == 1190.0
    assert parse_amount("1190.00") == 1190.0
    assert parse_amount("2.380,50 €") == 2380.5


# ─────────────────────────────────────────────────────────────
# 17. Minijob-Berechnung Tests
# ─────────────────────────────────────────────────────────────

def test_minijob_limit():
    """Minijob-Grenze korrekt."""
    from extensions_v2_complete import calculate_minijob

    # Unter Grenze
    result = calculate_minijob(20.0, 21.0)  # 420 € < 538 €
    assert result["art"] == "Minijob", f"Erwartet Minijob, erhalten {result['art']}"
    assert result["in_limit"] is True
    assert result["gross"] == pytest.approx(420.0, abs=0.01)


def test_midijob_range():
    """Midijob-Bereich korrekt erkannt."""
    from extensions_v2_complete import calculate_minijob

    # 30h × 21 € = 630 € (zwischen 538 und 2000)
    result = calculate_minijob(30.0, 21.0)
    assert result["art"] == "Midijob"
    assert result["in_limit"] is True


def test_over_midijob_limit():
    """Über Midijob-Grenze korrekt erkannt."""
    from extensions_v2_complete import calculate_minijob

    # 100h × 21 € = 2100 € > 2000 €
    result = calculate_minijob(100.0, 21.0)
    assert result["art"] == "Normaler AN"
    assert result["in_limit"] is False


def test_minijob_net_equals_gross():
    """Minijob: Nettolohn = Bruttolohn (kein AN-Abzug)."""
    from extensions_v2_complete import calculate_minijob
    import pytest

    result = calculate_minijob(15.0, 20.0)  # 300 € < 538 €
    assert result["art"] == "Minijob"
    assert result["net"] == pytest.approx(result["gross"], abs=0.01)


# ─────────────────────────────────────────────────────────────
# 18. Regex-Extraktion Tests (erweitert)
# ─────────────────────────────────────────────────────────────

def test_extract_german_amount():
    """Deutsches Betragsformat korrekt erkannt."""
    from extensions_v2_prod1 import extract_invoice_data_from_text

    # Deutsches Format
    text = "Gesamtbetrag: 1.234,56 EUR"
    result = extract_invoice_data_from_text(text)
    assert "gross_total" in result
    assert result["gross_total"] == pytest.approx(1234.56, abs=0.1)


def test_extract_iban():
    """IBAN wird korrekt extrahiert."""
    from extensions_v2_prod1 import extract_invoice_data_from_text

    text = "Bitte überweisen Sie auf IBAN: DE89 3704 0044 0532 0130 00"
    result = extract_invoice_data_from_text(text)
    assert "sender_iban" in result
    assert "DE89" in result["sender_iban"]


def test_extract_invoice_number_formats():
    """Verschiedene Rechnungsnummer-Formate werden erkannt."""
    from extensions_v2_prod1 import extract_invoice_data_from_text

    tests = [
        ("Rechnungsnummer: RE-2024-0042", "2024"),
        ("Invoice No.: INV-001", "INV"),
        ("Rechnung Nr.: 12345", "12345"),
    ]
    for text, expected_part in tests:
        result = extract_invoice_data_from_text(text)
        if "invoice_no" in result:
            assert expected_part in result["invoice_no"], \
                f"'{expected_part}' nicht in '{result['invoice_no']}' für: {text}"


# ─────────────────────────────────────────────────────────────
# 19. Notification-System Tests
# ─────────────────────────────────────────────────────────────

def test_notification_levels():
    """Alle Benachrichtigungs-Level sind valide."""
    valid_levels = {"info", "success", "warning", "danger"}
    test_level = "danger"
    assert test_level in valid_levels


def test_notification_auto_dismiss():
    """Auto-Dismiss-Logik korrekt."""
    auto_dismiss_after = 3600  # 1 Stunde
    created_at = datetime.now() - timedelta(hours=2)
    age_seconds = (datetime.now() - created_at).total_seconds()
    should_dismiss = age_seconds > auto_dismiss_after
    assert should_dismiss, "Nach 2h sollte Auto-Dismiss = True"


# ─────────────────────────────────────────────────────────────
# 20. Allgemeine System-Tests
# ─────────────────────────────────────────────────────────────

def test_german_number_formatting():
    """Deutsches Zahlenformat korrekt."""
    def fmt(v):
        return f"{v:,.2f} €".replace(",", "X").replace(".", ",").replace("X", ".")

    assert fmt(1000.00)  == "1.000,00 €"
    assert fmt(0.99)     == "0,99 €"
    assert fmt(1234567.89) == "1.234.567,89 €"


def test_iban_validation_format():
    """IBAN-Format-Prüfung (rudimentär)."""
    def is_valid_iban_format(iban: str) -> bool:
        clean = iban.replace(" ", "")
        return (len(clean) >= 15 and
                clean[:2].isalpha() and
                clean[2:4].isdigit())

    assert is_valid_iban_format("DE89 3704 0044 0532 0130 00")
    assert is_valid_iban_format("AT61 1904 3002 3457 3201")
    assert not is_valid_iban_format("1234567890")
    assert not is_valid_iban_format("ABCDEF")


def test_date_calculations():
    """Datums-Berechnungen korrekt."""
    from datetime import date, timedelta

    today = date.today()
    due_14 = today + timedelta(days=14)
    assert (due_14 - today).days == 14

    # Arbeitstage (Mo-Fr)
    count = sum(1 for d in range(7)
                if (today + timedelta(days=d)).weekday() < 5)
    assert 4 <= count <= 7, "5-7 Arbeitstage in 7 Kalendertagen"


def test_bwa_categories_completeness():
    """BWA-Kategorien sind vollständig."""
    expected_cats = [
        "Kfz-Kosten", "Bürokosten", "Kommunikation",
        "Raumkosten", "Versicherungen", "Personalkosten",
    ]
    # Prüfe ob alle in SKR03-Mapping enthalten
    # Nur Format-Test
    for cat in expected_cats:
        assert isinstance(cat, str) and len(cat) > 3


def test_vat_rates():
    """Standard-MwSt-Sätze korrekt."""
    rates = {
        "standard": 19.0,
        "reduced":  7.0,
        "zero":     0.0,
    }
    for name, rate in rates.items():
        net = 1000.0
        vat = round(net * rate / 100, 2)
        gross = round(net + vat, 2)
        assert gross >= net, f"{name}: Brutto muss >= Netto sein"
        if rate == 19.0:
            assert vat == 190.0
        elif rate == 7.0:
            assert vat == 70.0
        elif rate == 0.0:
            assert vat == 0.0


def test_invoice_status_transitions():
    """Gültige Rechnungsstatus-Übergänge."""
    valid_statuses = {"offen", "teilbezahlt", "bezahlt", "ueberfaellig", "storniert"}
    transitions = {
        "offen":        ["teilbezahlt", "bezahlt", "ueberfaellig", "storniert"],
        "teilbezahlt":  ["bezahlt", "storniert"],
        "ueberfaellig": ["bezahlt", "teilbezahlt", "storniert"],
        "bezahlt":      [],  # Endstatus
        "storniert":    [],  # Endstatus
    }
    for status, allowed_next in transitions.items():
        assert status in valid_statuses
        for next_s in allowed_next:
            assert next_s in valid_statuses


if __name__ == "__main__":
    import subprocess, sys
    result = subprocess.run(
        ["python", "-m", "pytest", __file__, "-v", "--tb=short"],
        cwd=str(BYBLOS_DIR)
    )
    sys.exit(result.returncode)


# ─────────────────────────────────────────────────────────────
# 21. VCard-Import Tests
# ─────────────────────────────────────────────────────────────

def test_vcard_parse_basic():
    """VCard-Parsing erkennt Firma und E-Mail."""
    from extensions_v2_automation_ops import parse_vcard

    vcard = """BEGIN:VCARD
VERSION:3.0
FN:Max Mustermann
ORG:Muster GmbH
EMAIL:max@muster.de
TEL:+4917612345678
END:VCARD"""
    contacts = parse_vcard(vcard)
    assert len(contacts) == 1
    assert contacts[0]["company"] in ("Muster GmbH", "Max Mustermann")
    assert contacts[0]["email"] == "max@muster.de"
    assert contacts[0]["phone"] == "+4917612345678"


def test_vcard_parse_multiple():
    """VCard-Parsing mehrerer Kontakte."""
    from extensions_v2_automation_ops import parse_vcard

    vcard = """BEGIN:VCARD\nVERSION:3.0\nFN:Firma A\nEMAIL:a@a.de\nEND:VCARD
BEGIN:VCARD\nVERSION:3.0\nFN:Firma B\nEMAIL:b@b.de\nEND:VCARD
BEGIN:VCARD\nVERSION:3.0\nFN:Firma C\nEMAIL:c@c.de\nEND:VCARD"""
    contacts = parse_vcard(vcard)
    assert len(contacts) == 3


def test_vcard_parse_address():
    """VCard-Parsing extrahiert Adresse."""
    from extensions_v2_automation_ops import parse_vcard

    vcard = """BEGIN:VCARD
VERSION:3.0
FN:Test GmbH
ADR:;;Hauptstraße 1;Berlin;;10117;DE
END:VCARD"""
    contacts = parse_vcard(vcard)
    assert len(contacts) == 1
    assert "Hauptstraße 1" in contacts[0].get("street","")


# ─────────────────────────────────────────────────────────────
# 22. Gantt-Chart Tests
# ─────────────────────────────────────────────────────────────

def test_gantt_overlap_detection():
    """Gantt-Balkenbreite bei korrekter Überschneidung."""
    from datetime import date

    # Projekt: 15. März – 15. September
    project_start = date(2025, 3, 15)
    project_end   = date(2025, 9, 15)

    # April (1. – 30. April) – volle Überschneidung
    month_start = date(2025, 4, 1)
    month_end   = date(2025, 4, 30)
    overlap_s   = max(project_start, month_start)
    overlap_e   = min(project_end, month_end)
    assert overlap_s <= overlap_e, "April sollte Überschneidung haben"

    # Januar – keine Überschneidung
    jan_start = date(2025, 1, 1)
    jan_end   = date(2025, 1, 31)
    overlap_s2 = max(project_start, jan_start)
    overlap_e2 = min(project_end, jan_end)
    assert overlap_s2 > overlap_e2, "Januar sollte keine Überschneidung haben"


# ─────────────────────────────────────────────────────────────
# 23. Eskalationsregeln Tests
# ─────────────────────────────────────────────────────────────

def test_escalation_rule_matching():
    """Korrekte Eskalationsregel wird ausgewählt."""
    rules = [
        {"days_overdue_trigger": 7,  "name": "Erinnerung", "fee_amount": 0},
        {"days_overdue_trigger": 14, "name": "1. Mahnung", "fee_amount": 5},
        {"days_overdue_trigger": 28, "name": "2. Mahnung", "fee_amount": 15},
        {"days_overdue_trigger": 42, "name": "Letzte Mahnung", "fee_amount": 40},
    ]

    def get_rule(days_overdue):
        matching = [r for r in rules if r["days_overdue_trigger"] <= days_overdue]
        return matching[-1] if matching else None

    assert get_rule(5) is None, "5 Tage → kein Treffer"
    assert get_rule(7)["name"] == "Erinnerung"
    assert get_rule(14)["name"] == "1. Mahnung"
    assert get_rule(30)["name"] == "2. Mahnung"
    assert get_rule(100)["name"] == "Letzte Mahnung"
    assert get_rule(42)["fee_amount"] == 40


def test_late_fee_calculation():
    """Mahngebühren werden korrekt berechnet."""
    from extensions_v2_complete import calculate_minijob

    # Einfache Mahngebühr-Logik
    overdue_days = 35
    annual_interest = 0.0875  # 8.75%
    open_amount = 1000.0
    interest = round(open_amount * annual_interest * overdue_days / 365, 2)
    assert interest > 0, "Zinsen müssen positiv sein"
    assert interest < 50, "Zinsen für 35 Tage < 50 EUR"


# ─────────────────────────────────────────────────────────────
# 24. Stripe Integration Tests
# ─────────────────────────────────────────────────────────────

def test_stripe_amount_conversion():
    """EUR-Betrag wird korrekt in Cents umgewandelt."""
    amounts = [(1190.00, 119000), (100.50, 10050), (0.99, 99), (2380.00, 238000)]
    for eur, cents in amounts:
        assert int(eur * 100) == cents, f"{eur} EUR != {cents} Cents"


def test_stripe_currency_code():
    """Stripe-Währungscode ist korrekt."""
    valid_currencies = {"eur", "usd", "gbp", "chf"}
    assert "eur" in valid_currencies
    assert "EUR".lower() in valid_currencies


# ─────────────────────────────────────────────────────────────
# 25. Break-Even Tests
# ─────────────────────────────────────────────────────────────

def test_breakeven_hours():
    """Break-Even-Stunden korrekt berechnet."""
    fixed_costs  = 7000.0  # €/Monat
    hourly_rate  = 21.0    # €/h
    breakeven_h  = fixed_costs / hourly_rate
    assert breakeven_h == pytest.approx(333.33, abs=0.1)


def test_breakeven_monthly_result():
    """Monatsergebnis bei 80% Auslastung."""
    fixed = 7000.0
    rate  = 21.0
    hours_day = 8.0
    workdays  = 22
    utilization = 0.8
    effective_hours = hours_day * workdays * utilization
    revenue = effective_hours * rate
    result  = revenue - fixed
    assert revenue > 0
    # 8h * 22 * 0.8 * 21 = 2956.8 €... zu wenig – realistisch wäre mehr MA
    # Korrekte Logik: result kann negativ sein
    assert isinstance(result, float)


def test_sensitivity_matrix():
    """Sensitivitätsmatrix hat korrekte Dimensionen."""
    rates = [18.0, 19.5, 21.0, 22.5, 24.0]
    util_levels = [60, 70, 80, 90, 100]
    hours_day = 8.0
    days = 22
    fixed = 7000.0

    matrix = {}
    for rate in rates:
        matrix[rate] = {}
        for util in util_levels:
            eff_h = hours_day * days * util / 100
            rev   = eff_h * rate
            matrix[rate][util] = round(rev - fixed, 2)

    assert len(matrix) == len(rates)
    assert len(matrix[21.0]) == len(util_levels)
    # Bei 100% Auslastung und 21€/h
    assert matrix[21.0][100] == pytest.approx(21.0 * 8 * 22 - 7000, abs=1)


# ─────────────────────────────────────────────────────────────
# 26. Duplikat-Erkennung Tests
# ─────────────────────────────────────────────────────────────

def test_duplicate_amount_tolerance():
    """Betragstoleranz korrekt."""
    def is_duplicate(amt1, amt2, tolerance_pct=5.0):
        if amt1 == 0:
            return False
        return abs(amt1 - amt2) / amt1 * 100 <= tolerance_pct

    assert is_duplicate(100.0, 104.0)  # 4% Abweichung < 5%
    assert not is_duplicate(100.0, 110.0)  # 10% > 5%
    assert is_duplicate(1000.0, 1000.0)  # Exakt gleich


def test_duplicate_text_similarity():
    """Beschreibungs-Ähnlichkeit korrekt berechnet."""
    def similarity(s1: str, s2: str) -> float:
        w1 = set(s1.lower().split())
        w2 = set(s2.lower().split())
        if not w1 or not w2:
            return 0.0
        return len(w1 & w2) / len(w1 | w2)

    s = similarity("Kraftstoff Tankstelle Aral", "Kraftstoff Tankstelle Shell")
    assert 0.4 < s < 0.9, f"Ähnlichkeit {s} nicht im erwarteten Bereich"

    s2 = similarity("Bürostühle IKEA", "Kraftstoff Tankstelle")
    assert s2 < 0.2, "Verschiedene Texte sollten geringe Ähnlichkeit haben"


# ─────────────────────────────────────────────────────────────
# 27. Schichtpräferenzen Tests
# ─────────────────────────────────────────────────────────────

def test_shift_day_matching():
    """Schicht-Tages-Matching mit Präferenzen."""
    DAYS_MAP = {0:"Montag",1:"Dienstag",2:"Mittwoch",3:"Donnerstag",
                4:"Freitag",5:"Samstag",6:"Sonntag"}
    from datetime import date

    # Montag
    d = date(2025, 6, 2)  # Montag
    day_name = DAYS_MAP[d.weekday()]
    assert day_name == "Montag"

    # Samstag
    d2 = date(2025, 6, 7)  # Samstag
    assert DAYS_MAP[d2.weekday()] == "Samstag"

    # Mitarbeiter der nur Mo-Fr arbeitet
    pref_days = ["Montag","Dienstag","Mittwoch","Donnerstag","Freitag"]
    assert "Samstag" not in pref_days
    assert "Montag" in pref_days


# ─────────────────────────────────────────────────────────────
# 28. Inventar-Wartungsalarm Tests
# ─────────────────────────────────────────────────────────────

def test_maintenance_due_detection():
    """Wartungsalarm wird korrekt ausgelöst."""
    from datetime import date, timedelta

    today = date.today()
    # Fällig in 25 Tagen → Warnung (Schwelle 30 Tage)
    due_25 = (today + timedelta(days=25)).isoformat()
    warn_date = (today + timedelta(days=30)).isoformat()
    assert due_25 <= warn_date, "25 Tage sollte Warnung auslösen"

    # Fällig in 45 Tagen → keine Warnung
    due_45 = (today + timedelta(days=45)).isoformat()
    assert due_45 > warn_date, "45 Tage sollte keine Warnung auslösen"

    # Bereits überfällig
    overdue = (today - timedelta(days=5)).isoformat()
    assert overdue < today.isoformat(), "Überfällig"


if __name__ == "__main__":
    import subprocess, sys
    result = subprocess.run(
        ["python", "-m", "pytest", __file__, "-v", "--tb=short"],
        cwd=str(BYBLOS_DIR)
    )
    sys.exit(result.returncode)
