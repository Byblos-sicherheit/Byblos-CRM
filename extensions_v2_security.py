"""Teilweise Wiederherstellung von extensions_v2_security: ZUGFeRD-/CII-XML (Profil EN 16931).

Die Seiten dieses Moduls fehlen weiterhin und werden ausgeblendet (crm_stage8.PAGE_SOURCES).
shortcut: XML ist nicht gegen einen EN-16931-/ZUGFeRD-Validator geprüft – vor Versand an Kunden validieren.
"""
import xml.etree.ElementTree as ET

NS = {
    "rsm": "urn:un:unece:uncefact:data:standard:CrossIndustryInvoice:100",
    "ram": "urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100",
    "udt": "urn:un:unece:uncefact:data:standard:UnqualifiedDataType:100",
}
for _prefix, _uri in NS.items():
    ET.register_namespace(_prefix, _uri)


def _el(parent, tag, text=None, **attrs):
    prefix, name = tag.split(":")
    node = ET.SubElement(parent, f"{{{NS[prefix]}}}{name}", attrs)
    if text is not None:
        node.text = str(text)
    return node


def _money(value):
    return f"{float(value or 0):.2f}"


def _date(parent, tag, iso):
    if iso:
        wrapper = _el(parent, tag)
        _el(wrapper, "udt:DateTimeString", str(iso)[:10].replace("-", ""), format="102")


def _party(parent, tag, name, street="", vat_id=""):
    party = _el(parent, tag)
    _el(party, "ram:Name", name or "")
    address = _el(party, "ram:PostalTradeAddress")
    if street:
        _el(address, "ram:LineOne", street)
    _el(address, "ram:CountryID", "DE")
    if vat_id:
        _el(_el(party, "ram:SpecifiedTaxRegistration"), "ram:ID", vat_id, schemeID="VA")


def generate_zugferd_xml(invoice, customer, items, seller):
    """CII-XML zu Rechnung (dict), Kunde, Positionen und Verkäufer; Beträge aus der Rechnung, nicht neu gerechnet."""
    root = ET.Element(f"{{{NS['rsm']}}}CrossIndustryInvoice")
    ctx = _el(root, "rsm:ExchangedDocumentContext")
    _el(_el(ctx, "ram:GuidelineSpecifiedDocumentContextParameter"), "ram:ID", "urn:cen.eu:en16931:2017")
    doc = _el(root, "rsm:ExchangedDocument")
    _el(doc, "ram:ID", invoice.get("invoice_no", ""))
    _el(doc, "ram:TypeCode", "380")
    _date(doc, "ram:IssueDateTime", invoice.get("invoice_date"))
    tx = _el(root, "rsm:SupplyChainTradeTransaction")
    for pos, item in enumerate(items or [], 1):
        line = _el(tx, "ram:IncludedSupplyChainTradeLineItem")
        _el(_el(line, "ram:AssociatedDocumentLineDocument"), "ram:LineID", pos)
        _el(_el(line, "ram:SpecifiedTradeProduct"), "ram:Name", item.get("description", ""))
        _el(_el(_el(line, "ram:SpecifiedLineTradeAgreement"), "ram:NetPriceProductTradePrice"), "ram:ChargeAmount",
            _money(item.get("unit_price")))
        _el(_el(line, "ram:SpecifiedLineTradeDelivery"), "ram:BilledQuantity", item.get("quantity", 1),
            unitCode=item.get("unit") or "C62")
        settle = _el(line, "ram:SpecifiedLineTradeSettlement")
        tax = _el(settle, "ram:ApplicableTradeTax")
        _el(tax, "ram:TypeCode", "VAT")
        _el(tax, "ram:CategoryCode", "S")
        _el(tax, "ram:RateApplicablePercent", _money(invoice.get("vat_rate")))
        _el(_el(settle, "ram:SpecifiedTradeSettlementLineMonetarySummation"), "ram:LineTotalAmount", _money(item.get("total")))
    agreement = _el(tx, "ram:ApplicableHeaderTradeAgreement")
    _party(agreement, "ram:SellerTradeParty", seller.get("name"), seller.get("street", ""), seller.get("ust_id", ""))
    _party(agreement, "ram:BuyerTradeParty", customer.get("company"), customer.get("street", ""), customer.get("vat_id", ""))
    _el(tx, "ram:ApplicableHeaderTradeDelivery")
    settlement = _el(tx, "ram:ApplicableHeaderTradeSettlement")
    _el(settlement, "ram:InvoiceCurrencyCode", "EUR")
    if seller.get("iban"):
        means = _el(settlement, "ram:SpecifiedTradeSettlementPaymentMeans")
        _el(means, "ram:TypeCode", "58")
        _el(_el(means, "ram:PayeePartyCreditorFinancialAccount"), "ram:IBANID", seller["iban"].replace(" ", ""))
    tax = _el(settlement, "ram:ApplicableTradeTax")
    _el(tax, "ram:CalculatedAmount", _money(invoice.get("vat_total")))
    _el(tax, "ram:TypeCode", "VAT")
    _el(tax, "ram:BasisAmount", _money(invoice.get("net_total")))
    _el(tax, "ram:CategoryCode", "S")
    _el(tax, "ram:RateApplicablePercent", _money(invoice.get("vat_rate")))
    if invoice.get("due_date"):
        _date(_el(settlement, "ram:SpecifiedTradePaymentTerms"), "ram:DueDateDateTime", invoice["due_date"])
    total = _el(settlement, "ram:SpecifiedTradeSettlementHeaderMonetarySummation")
    _el(total, "ram:LineTotalAmount", _money(invoice.get("net_total")))
    _el(total, "ram:TaxBasisTotalAmount", _money(invoice.get("net_total")))
    _el(total, "ram:TaxTotalAmount", _money(invoice.get("vat_total")), currencyID="EUR")
    _el(total, "ram:GrandTotalAmount", _money(invoice.get("gross_total")))
    _el(total, "ram:DuePayableAmount", _money(invoice.get("gross_total")))
    return ET.tostring(root, encoding="unicode", xml_declaration=True)
