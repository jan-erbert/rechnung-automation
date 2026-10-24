"""Echte optionale PDF/XML-Pruefung mit ausschliesslich fiktiven Rechnungen."""

import os
from decimal import Decimal
from io import BytesIO
from pathlib import Path

import pytest

pytestmark = pytest.mark.skipif(
    os.environ.get("RUN_ZUGFERD_INTEGRATION") != "1",
    reason="Optionale native Integration ausdruecklich aktivieren.",
)


def _snapshot(case):
    """Baut Standard-, Kleinunternehmer- und Stundenbeispiele ohne private Daten."""
    from zugferd_fixture import invoice_snapshot

    snapshot = invoice_snapshot()
    if case == "small_business":
        snapshot["tax"] = {
            "identifier_type": "tax_number",
            "tax_number": "12/345/67890",
            "small_business": True,
            "vat_rate": Decimal("0"),
        }
        snapshot["tax_amount"] = Decimal("0")
        snapshot["gross"] = snapshot["net"]
    elif case == "hours":
        snapshot["lines"][0].update(
            quantity=Decimal("2.5"),
            unit_price=Decimal("40"),
            unit_code="HUR",
        )
    elif case == "quarter":
        snapshot["lines"][0].update(
            quantity=Decimal("3"),
            unit_price=Decimal("19.99"),
            total=Decimal("59.97"),
            unit_code="MON",
        )
        snapshot.update(
            net=Decimal("59.97"), tax_amount=Decimal("11.39"), gross=Decimal("71.36")
        )
    return snapshot


def _html(snapshot):
    """Rendert die tatsaechliche Rechnungsvorlage aus demselben Datensatz."""
    from branding import validate_branding_config
    from design import validate_design_config
    from invoice_templates import build_template_context, load_templates

    items = [
        {"description": line["name"], "price": f"{line['total']:.2f}".replace(".", ",") + " EUR"}
        for line in snapshot["lines"]
    ]
    context = build_template_context(
        customer=snapshot["customer"],
        sender=snapshot["sender"],
        bank=snapshot["bank"],
        tax=snapshot["tax"],
        items=items,
        invoice_number=snapshot["dates"]["invoice_number"],
        invoice_date=snapshot["dates"]["invoice_date"],
        due_date=snapshot["dates"]["due_date"],
        billing_period="Oktober 2026",
        month_year="Oktober 2026",
        cycle_months=1,
        total_amount=snapshot["net"],
        formatted_total=f"{snapshot['gross']:.2f}".replace(".", ","),
        gross_amount=snapshot["gross"],
        tax_amount=snapshot["tax_amount"],
        vat_note="Musterrechnung",
        logo_base64="",
        mail_logo_cid="",
        design=validate_design_config({}),
        branding=validate_branding_config({}),
        sample_text="MUSTER",
    )
    templates = Path(__file__).resolve().parents[1] / "templates"
    return load_templates(templates).invoice.render(context)


@pytest.mark.parametrize("case", ["standard", "small_business", "hours", "quarter"])
def test_real_zugferd_contains_valid_matching_xml(case):
    """Echte PDF/A-3-Ausgabe behaelt Darstellung und gepruefte XML zusammen."""
    from pypdf import PdfReader
    from pdf_service import generate_pdf_bytes
    from zugferd_validation import validate_invoice_xml

    snapshot = _snapshot(case)
    pdf = generate_pdf_bytes(_html(snapshot), {"format": "zugferd"}, snapshot)
    reader = PdfReader(BytesIO(pdf), strict=True)
    assert len(reader.pages) == 1
    assert snapshot["dates"]["invoice_number"] in reader.pages[0].extract_text()
    xml = reader.attachments["factur-x.xml"][0]
    validate_invoice_xml(xml)
    assert b"%PDF-1.7" in pdf[:20]


def test_changed_xml_is_rejected_after_embedding():
    """Ein abweichender Datenteil besteht die Roundtrip-Pruefung nicht."""
    from pdf_service import generate_pdf_bytes
    from zugferd import verify_embedded_invoice

    snapshot = _snapshot("standard")
    pdf = generate_pdf_bytes(_html(snapshot), {"format": "zugferd"}, snapshot)
    with pytest.raises(ValueError, match="ZF_EMBEDDING"):
        verify_embedded_invoice(pdf, b"different XML")
