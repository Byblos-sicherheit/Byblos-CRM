"""Teilweise Wiederherstellung von extensions_v2_prod1: Belegtext-Erkennung und TOTP.

Die Seiten dieses Moduls (Intelligenter Import, Angebots-PDF, …) fehlen weiterhin und werden ausgeblendet
(crm_stage8.PAGE_SOURCES). TOTP liegt in crm_stage8; hier nur die Namen, die Altcode und Tests erwarten.
"""
import re

import crm_stage8

_AMOUNT = r"(\d{1,3}(?:[.\s]\d{3})+(?:,\d{1,2})?|\d+(?:[.,]\d{1,2})?)"
_INVOICE_NO = re.compile(r"(?:Rechnungs?\s*-?\s*(?:nummer|nr\.?)|Invoice\s*No\.?)\s*:?\s*([A-Z0-9][A-Z0-9\-/]*)", re.I)
_DATE = re.compile(r"(\d{1,2})\.(\d{1,2})\.(\d{4})")
_GROSS = re.compile(r"(?:Gesamtbetrag|Rechnungsbetrag|Bruttobetrag|Brutto|Gesamtsumme|Endbetrag|Zu zahlen)\s*:?\s*" + _AMOUNT, re.I)
_NET = re.compile(r"(?:Nettobetrag|Netto|Zwischensumme)\s*:?\s*" + _AMOUNT, re.I)
_VAT = re.compile(r"(\d{1,2}(?:[.,]\d)?)\s*%\s*(?:MwSt|USt|Umsatzsteuer|Mehrwertsteuer)|(?:MwSt|USt)\.?\s*(\d{1,2}(?:[.,]\d)?)\s*%", re.I)
_IBAN = re.compile(r"\b([A-Z]{2}\d{2}(?:\s?[A-Z0-9]{4}){3,7}(?:\s?[A-Z0-9]{1,3})?)\b")


def parse_de_amount(text):
    """Betrag aus '1.234,56', '1234,56', '1234.56', '2.380,50 €' oder '1 234,56'."""
    s = str(text).replace("€", "").replace("EUR", "").replace(" ", "").replace(" ", "").strip()
    if "," in s and "." in s:
        s = s.replace(".", "").replace(",", ".") if s.rfind(",") > s.rfind(".") else s.replace(",", "")
    elif "," in s:
        s = s.replace(",", ".")
    elif s.count(".") > 1 or (s.count(".") == 1 and len(s.split(".")[1]) == 3):
        s = s.replace(".", "")  # nur Tausenderpunkte, z. B. 1.190
    return float(s)


def _date_iso(match):
    d, m, y = (int(x) for x in match.groups())
    return f"{y:04d}-{m:02d}-{d:02d}"


def extract_invoice_data_from_text(text):
    """Rechnungsnummer, Datum, Beträge, Steuersatz und IBAN aus Belegtext. Nur gefundene Felder im Ergebnis."""
    text = text or ""
    result = {}
    if m := _INVOICE_NO.search(text):
        result["invoice_no"] = m.group(1)
    dated = re.search(r"(?:Rechnungsdatum|Datum|Date)\s*:?\s*" + _DATE.pattern, text, re.I)
    if dated or (dated := _DATE.search(text)):
        result["invoice_date"] = _date_iso(re.search(_DATE, dated.group(0)))
    if m := _GROSS.search(text):
        result["gross_total"] = parse_de_amount(m.group(1))
    if m := _NET.search(text):
        result["net_total"] = parse_de_amount(m.group(1))
    if m := _VAT.search(text):
        result["vat_rate"] = float((m.group(1) or m.group(2)).replace(",", "."))
    if m := _IBAN.search(text):
        result["sender_iban"] = m.group(1).replace(" ", "")
    return result


def generate_totp_secret():
    return crm_stage8.new_secret()


def get_totp_uri(secret, username, issuer="Byblos CRM"):
    return crm_stage8.provisioning_uri(username, secret, issuer)


verify_totp = crm_stage8.verify_totp
