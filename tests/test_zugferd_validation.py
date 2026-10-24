"""Isolierte XML-Pruefungen ohne PDFs, Versand oder produktive Dateien."""

import json
from datetime import date
from decimal import Decimal
from types import SimpleNamespace

import pytest

import zugferd_validation as validation


def _valid_xml():
    """Erstellt ausschliesslich fiktive strukturierte XML-Testdaten."""
    pytest.importorskip("drafthorse")
    from drafthorse.models.document import Document
    from drafthorse.models.party import TaxRegistration
    from drafthorse.models.trade import ApplicableTradeTax
    from drafthorse.models.tradelines import LineItem

    document = Document()
    document.context.guideline_parameter.id = validation.PROFILE_ID
    document.header.id = "TEST-2026-001"
    document.header.type_code = "380"
    document.header.issue_date_time = date(2026, 10, 24)
    for party in (document.trade.agreement.seller, document.trade.agreement.buyer):
        party.name = "Musterfirma"
        party.address.line_one = "Musterweg 1"
        party.address.postcode = "12345"
        party.address.city_name = "Musterstadt"
        party.address.country_id = "DE"
    registration = TaxRegistration()
    registration.id = ("VA", "DE123456789")
    document.trade.agreement.seller.tax_registrations.add(registration)
    item = LineItem()
    item.document.line_id = "1"
    item.product.name = "Testleistung"
    item.agreement.net.amount = "100.00"
    item.delivery.billed_quantity = ("1", "C62")
    item.settlement.trade_tax.type_code = "VAT"
    item.settlement.trade_tax.category_code = "S"
    item.settlement.trade_tax.rate_applicable_percent = "19"
    item.settlement.monetary_summation.total_amount = "100.00"
    document.trade.items.add(item)
    document.trade.settlement.currency_code = "EUR"
    tax = ApplicableTradeTax()
    tax.calculated_amount = "19.00"
    tax.type_code = "VAT"
    tax.basis_amount = "100.00"
    tax.category_code = "S"
    tax.rate_applicable_percent = "19"
    document.trade.settlement.trade_tax.add(tax)
    document.trade.settlement.terms.description = "Zahlbar innerhalb von 14 Tagen."
    total = document.trade.settlement.monetary_summation
    total.line_total = "100.00"
    total.tax_basis_total = Decimal("100.00")
    total.tax_total = ("19.00", "EUR")
    total.grand_total = Decimal("119.00")
    total.due_amount = Decimal("119.00")
    return document.serialize(schema="FACTUR-X_EN16931")


@pytest.fixture
def optional_dependencies():
    """Ueberspringt echte Standardpruefungen ohne die optionale Erweiterung."""
    pytest.importorskip("drafthorse")
    pytest.importorskip("lxml")
    pytest.importorskip("saxonche")


def test_valid_invoice_passes_real_local_rules(optional_dependencies):
    """Fiktive EN-16931-Daten bestehen XSD und echte CEN-Regeln."""
    validation.validate_invoice_xml(_valid_xml())


def test_wrong_total_is_rejected_by_business_rules(optional_dependencies):
    """Ein XSD-gueltiger falscher Gesamtbetrag scheitert an Geschaeftsregeln."""
    xml = _valid_xml().replace(
        b"<ram:GrandTotalAmount>119.00</ram:GrandTotalAmount>",
        b"<ram:GrandTotalAmount>120.00</ram:GrandTotalAmount>",
    )
    with pytest.raises(ValueError, match="ZUGFERD_EN16931.*BR-CO-15"):
        validation.validate_invoice_xml(xml)


def test_invalid_structure_has_safe_error(optional_dependencies):
    """Unguelle XML-Struktur meldet keine Rechnungsinhalte."""
    xml = _valid_xml().replace(b"<ram:TypeCode>380</ram:TypeCode>", b"")
    with pytest.raises(ValueError, match="ZUGFERD_XSD") as error:
        validation.validate_invoice_xml(xml)
    assert "Musterfirma" not in str(error.value)


@pytest.mark.parametrize("payload", [b"<", b"<!DOCTYPE x><x/>"])
def test_malformed_xml_or_dtd_rejected(payload, optional_dependencies):
    """DTD und defekte Dokumente gelangen nicht zur Regelpruefung."""
    with pytest.raises(ValueError, match="ZUGFERD_XML"):
        validation.validate_invoice_xml(payload)


def test_external_entity_rejected_without_reading_file(tmp_path, optional_dependencies):
    """Eine externe Entitaet wird auch mit lokaler Datei nicht verarbeitet."""
    private = tmp_path / "private.txt"
    private.write_text("PRIVATE_SENTINEL")
    xml = (
        '<!DOCTYPE x [<!ENTITY leak SYSTEM "'
        + private.as_uri()
        + '">]><x>&leak;</x>'
    ).encode()
    with pytest.raises(ValueError, match="ZUGFERD_XML") as error:
        validation.validate_invoice_xml(xml)
    assert "PRIVATE_SENTINEL" not in str(error.value)


def test_profile_must_be_exact_en16931(optional_dependencies):
    """Ein anderes Profil wird nicht versehentlich als EN 16931 akzeptiert."""
    xml = _valid_xml().replace(validation.PROFILE_ID.encode(), b"other-profile")
    with pytest.raises(ValueError, match="ZUGFERD_PROFILE"):
        validation.validate_invoice_xml(xml)


def test_missing_rules_fail_closed(tmp_path):
    """Fehlende Standardregeln werden nicht still uebersprungen."""
    with pytest.raises(RuntimeError, match="ZUGFERD_RULES"):
        validation._trusted_stylesheet(tmp_path)


def test_changed_rulepack_is_rejected(tmp_path):
    """Eine veraenderte Regeldatei besteht die Integritaetspruefung nicht."""
    manifest = {"files": {"EN16931-CII-validation.xslt": "0" * 64}}
    (tmp_path / "manifest.json").write_text(json.dumps(manifest))
    (tmp_path / "EN16931-CII-validation.xslt").write_text("changed")
    with pytest.raises(RuntimeError, match="ZUGFERD_RULES"):
        validation._trusted_stylesheet(tmp_path)


def test_vendored_rules_match_manifest():
    """Das unveraenderte offizielle Regelpaket entspricht dem Manifest."""
    path = validation._trusted_stylesheet(validation.RULES_DIRECTORY)
    assert path.name == "EN16931-CII-validation.xslt"


def test_schema_import_cannot_leave_package(tmp_path, optional_dependencies):
    """Ein Schemaimport ausserhalb des Paketverzeichnisses wird gesperrt."""
    from lxml import etree

    package = tmp_path / "package"
    schemas = package / "schema"
    schemas.mkdir(parents=True)
    (schemas / "Factur-X_1.0.07_EN16931.xsd").write_text(
        '<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema">'
        '<xs:include schemaLocation="../../outside.xsd"/></xs:schema>'
    )
    fake = SimpleNamespace(__file__=str(package / "__init__.py"))
    with pytest.raises(RuntimeError, match="ZUGFERD_SCHEMA"):
        validation._validate_schema(etree.fromstring(b"<test/>"), fake, etree)


def test_setup_check_without_invoice(optional_dependencies):
    """Die Installation laesst sich ohne Rechnung oder Netzwerk pruefen."""
    validation.check_validation_setup()
