"""Optionale ZUGFeRD-Ausgabe mit lokal geprueften EN-16931-Rechnungsdaten."""

from datetime import datetime
from decimal import Decimal
from io import BytesIO
from xml.etree import ElementTree as ET

CENT = Decimal("0.01")
PROFILE = "urn:cen.eu:en16931:2017"
XML_NAME = "factur-x.xml"
FX = "urn:factur-x:pdfa:CrossIndustryDocument:invoice:1p0#"
RDF = "http://www.w3.org/1999/02/22-rdf-syntax-ns#"


def invoice_snapshot(customer, sender, bank, tax, services, dates, totals) -> dict:
    """Uebernimmt berechnete Originalwerte statt formatierter Anzeigetexte."""
    lines = [item.get("invoice_line") for item in services["items"]]
    if not lines or any(line is None for line in lines):
        raise ValueError("ZF_DATA: Strukturierte Rechnungspositionen fehlen.")
    # Null-Stunden-Monate bleiben im Sichtteil, sind aber keine Rechnungsposten.
    lines = [line for line in lines if line["quantity"] != 0 or line["total"] != 0]
    if not lines:
        raise ValueError("ZF_DATA: Keine abrechenbaren Positionen vorhanden.")
    return {
        "customer": customer,
        "sender": sender,
        "bank": bank,
        "tax": tax,
        "lines": lines,
        "dates": dates,
        "net": services["total_amount"],
        "tax_amount": totals["tax_amount"],
        "gross": totals["gross_amount"],
    }


def _money(value) -> Decimal:
    """Prueft Geldwerte ohne Ruecklesen von lokalisierten Anzeigeformaten."""
    amount = Decimal(str(value))
    if not amount.is_finite() or amount < 0:
        raise ValueError("ZF_AMOUNT: Geldwert ist ungueltig.")
    return amount.quantize(CENT)


def _check_snapshot(snapshot: dict) -> None:
    """Prueft die Uebereinstimmung sichtbarer und strukturierter Summen."""
    total = Decimal("0")
    for line in snapshot["lines"]:
        quantity = Decimal(str(line["quantity"]))
        price = Decimal(str(line["unit_price"]))
        if not quantity.is_finite() or quantity <= 0:
            raise ValueError("ZF_QUANTITY: Menge muss positiv sein.")
        if not price.is_finite() or price < 0:
            raise ValueError("ZF_PRICE: Einzelpreis ist ungueltig.")
        if _money(quantity * price) != _money(line["total"]):
            raise ValueError("ZF_LINE_TOTAL: Positionssumme stimmt nicht ueberein.")
        total += _money(line["total"])
    if total != _money(snapshot["net"]):
        raise ValueError("ZF_NET_TOTAL: Gerundete Positionssummen weichen ab.")
    if total + _money(snapshot["tax_amount"]) != _money(snapshot["gross"]):
        raise ValueError("ZF_GROSS_TOTAL: Gesamtsumme stimmt nicht ueberein.")


def _fill_party(party, data: dict) -> None:
    """Uebertraegt Anschrift und elektronische Kontaktadresse."""
    party.name = data.get("company") or data["name"]
    party.address.line_one = data["street"]
    party.address.postcode = data["postal_code"]
    party.address.city_name = data["city"]
    party.address.country_id = data.get("country_code", "DE")
    if data.get("email"):
        party.electronic_address.uri_ID = ("EM", data["email"])


def build_invoice_xml(snapshot: dict) -> bytes:
    """Erzeugt CII-XML und prueft Schema sowie EN-16931-Geschaeftsregeln."""
    try:
        from drafthorse.models.accounting import ApplicableTradeTax
        from drafthorse.models.document import Document
        from drafthorse.models.party import TaxRegistration
        from drafthorse.models.payment import PaymentMeans, PaymentTerms
        from drafthorse.models.tradelines import LineItem
    except ImportError:
        raise RuntimeError(
            "ZF_DEPENDENCY: Optionale ZUGFeRD-Pakete installieren."
        ) from None
    from zugferd_validation import validate_invoice_xml

    _check_snapshot(snapshot)
    doc = Document()
    doc.context.guideline_parameter.id = PROFILE
    dates = snapshot["dates"]
    doc.header.id = dates["invoice_number"]
    doc.header.type_code = "380"
    doc.header.issue_date_time = datetime.strptime(
        dates["invoice_date"], "%d.%m.%Y"
    ).date()
    _fill_party(doc.trade.agreement.seller, snapshot["sender"])
    _fill_party(doc.trade.agreement.buyer, snapshot["customer"])
    tax = snapshot["tax"]
    scheme = "VA" if tax["identifier_type"] == "vat_id" else "FC"
    # Die vorhandene Steuerkennung dient zugleich als interne Verkaeuferkennung.
    doc.trade.agreement.seller.id = tax[tax["identifier_type"]]
    doc.trade.agreement.seller.tax_registrations.add(
        TaxRegistration(id=(scheme, tax[tax["identifier_type"]]))
    )
    exempt = tax["small_business"] or Decimal(str(tax["vat_rate"])) == 0
    category = "E" if exempt else "S"
    rate = Decimal("0") if exempt else Decimal(str(tax["vat_rate"]))
    if exempt and not tax["small_business"]:
        raise ValueError("ZF_TAX: Steuerbefreiungsgrund fehlt fuer diesen Steuerfall.")
    for index, line in enumerate(snapshot["lines"], 1):
        item = LineItem()
        item.document.line_id = str(index)
        item.product.name = line["name"]
        item.agreement.net.amount = line["unit_price"]
        item.agreement.net.basis_quantity = (Decimal("1"), line["unit_code"])
        item.delivery.billed_quantity = (line["quantity"], line["unit_code"])
        item.settlement.trade_tax.type_code = "VAT"
        item.settlement.trade_tax.category_code = category
        item.settlement.trade_tax.rate_applicable_percent = rate
        item.settlement.monetary_summation.total_amount = _money(line["total"])
        doc.trade.items.add(item)
    settlement = doc.trade.settlement
    settlement.currency_code = "EUR"
    settlement.payment_reference = dates["invoice_number"]
    payment = PaymentMeans(type_code="58")
    payment.payee_account.iban = snapshot["bank"]["iban"].replace(" ", "")
    payment.payee_account.account_name = snapshot["bank"]["account_holder"]
    settlement.payment_means.add(payment)
    breakdown = ApplicableTradeTax()
    breakdown.type_code = "VAT"
    breakdown.category_code = category
    breakdown.rate_applicable_percent = rate
    breakdown.calculated_amount = _money(snapshot["tax_amount"])
    breakdown.basis_amount = _money(snapshot["net"])
    if exempt:
        breakdown.exemption_reason = (
            "Gemaess § 19 UStG wird keine Umsatzsteuer berechnet."
        )
    settlement.trade_tax.add(breakdown)
    sums = settlement.monetary_summation
    sums.line_total = _money(snapshot["net"])
    sums.tax_basis_total = _money(snapshot["net"])
    sums.tax_total = (_money(snapshot["tax_amount"]), "EUR")
    sums.grand_total = _money(snapshot["gross"])
    sums.due_amount = _money(snapshot["gross"])
    terms = PaymentTerms()
    terms.due = datetime.strptime(dates["due_date"], "%d.%m.%Y").date()
    settlement.terms.add(terms)
    try:
        xml = doc.serialize(schema="FACTUR-X_EN16931")
    except Exception:
        raise ValueError(
            "ZF_SCHEMA: Rechnungsdaten entsprechen nicht dem Profil."
        ) from None
    validate_invoice_xml(xml)
    return xml


def _xmp_extension() -> bytes:
    """Beschreibt die eingebettete Rechnung im ZUGFeRD-XMP-Schema."""
    extension = "http://www.aiim.org/pdfa/ns/extension/"
    schema = "http://www.aiim.org/pdfa/ns/schema#"
    prop = "http://www.aiim.org/pdfa/ns/property#"
    for prefix, namespace in {
        "rdf": RDF,
        "fx": FX,
        "pdfaExtension": extension,
        "pdfaSchema": schema,
        "pdfaProperty": prop,
    }.items():
        ET.register_namespace(prefix, namespace)
    root = ET.Element(f"{{{RDF}}}RDF")
    description = ET.SubElement(root, f"{{{RDF}}}Description", {f"{{{RDF}}}about": ""})
    values = {
        "DocumentType": "INVOICE",
        "DocumentFileName": XML_NAME,
        "Version": "1.0",
        "ConformanceLevel": "EN 16931",
    }
    for name, value in values.items():
        ET.SubElement(description, f"{{{FX}}}{name}").text = value
    schemas = ET.SubElement(description, f"{{{extension}}}schemas")
    bag = ET.SubElement(schemas, f"{{{RDF}}}Bag")
    entry = ET.SubElement(bag, f"{{{RDF}}}li", {f"{{{RDF}}}parseType": "Resource"})
    for name, value in {
        "schema": "Factur-X PDF/A Extension Schema",
        "namespaceURI": FX,
        "prefix": "fx",
    }.items():
        ET.SubElement(entry, f"{{{schema}}}{name}").text = value
    properties = ET.SubElement(entry, f"{{{schema}}}property")
    sequence = ET.SubElement(properties, f"{{{RDF}}}Seq")
    for name in values:
        item = ET.SubElement(
            sequence, f"{{{RDF}}}li", {f"{{{RDF}}}parseType": "Resource"}
        )
        for key, value in {
            "name": name,
            "valueType": "Text",
            "category": "external",
            "description": f"Factur-X {name}",
        }.items():
            ET.SubElement(item, f"{{{prop}}}{key}").text = value
    return ET.tostring(root, encoding="utf-8")


def generate_zugferd_pdf(pdf_html: str, snapshot: dict) -> bytes:
    """Erzeugt PDF/A-3 mit identischer, validierter XML ohne Java-Komponente."""
    xml = build_invoice_xml(snapshot)
    from weasyprint import Attachment, HTML

    document = HTML(string=pdf_html).render()
    document.metadata.xmp_metadata.append(_xmp_extension())
    attachment = Attachment(
        file_obj=BytesIO(xml), name=XML_NAME, relationship="Alternative"
    )
    result = document.write_pdf(
        pdf_variant="pdf/a-3u",
        attachments=[attachment],
        finisher=_unique_associated_files,
    )
    verify_embedded_invoice(result, xml)
    return result


def _unique_associated_files(document, pdf) -> None:
    """Entfernt doppelte AF-Referenzen der verwendeten WeasyPrint-Version 69."""
    references = pdf.catalog.get("AF")
    if references is not None:
        references[:] = list(dict.fromkeys(references))


def verify_embedded_invoice(pdf_bytes: bytes, expected_xml: bytes) -> None:
    """Prueft XML-Roundtrip, Dateizuordnung und deklarierte PDF-Metadaten."""
    try:
        from pypdf import PdfReader

        reader = PdfReader(BytesIO(pdf_bytes), strict=True)
        attachments = reader.attachments
        if set(attachments) != {XML_NAME} or attachments[XML_NAME] != [expected_xml]:
            raise ValueError("XML-Roundtrip")
        root = reader.trailer["/Root"]
        associated = root["/AF"]
        if len(associated) != 1:
            raise ValueError("Dateizuordnung")
        spec = associated[0].get_object()
        if spec["/AFRelationship"] != "/Alternative" or spec["/F"] != XML_NAME:
            raise ValueError("Dateizuordnung")
        metadata = ET.fromstring(root["/Metadata"].get_data())
        descriptions = metadata.findall(f".//{{{RDF}}}Description")
        if not any(
            element.get("{http://www.aiim.org/pdfa/ns/id/}part") == "3"
            for element in descriptions
        ):
            raise ValueError("PDF/A-Deklaration")
        for name, value in {
            "DocumentFileName": XML_NAME,
            "DocumentType": "INVOICE",
            "Version": "1.0",
            "ConformanceLevel": "EN 16931",
        }.items():
            if metadata.findtext(f".//{{{FX}}}{name}") != value:
                raise ValueError("ZUGFeRD-Metadaten")
    except Exception:
        raise ValueError(
            "ZF_EMBEDDING: Eingebettete Rechnung konnte nicht bestaetigt werden."
        ) from None
