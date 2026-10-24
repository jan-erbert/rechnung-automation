"""Prueft Konfigurationswahl und sichere Verarbeitung vor dem Versand."""

from decimal import Decimal

import pytest

from pdf_service import generate_pdf_bytes, validate_pdf_config
from services import build_service_items
from zugferd import _check_snapshot
from zugferd_fixture import invoice_snapshot as fixture_snapshot


@pytest.mark.parametrize("value", ["xml", "", None, True, []])
def test_unknown_output_format_is_rejected(value):
    """Unbekannte Ausgabeoptionen fuehren nicht zu einem stillen PDF-Fallback."""
    with pytest.raises(ValueError, match="pdf.format"):
        validate_pdf_config({"format": value})


def test_pdf_mode_does_not_load_optional_packages(monkeypatch):
    """Normale PDF-Ausgabe verwendet ausschliesslich die bisherige Engine."""
    monkeypatch.setattr("pdf_service._generate_with_weasyprint", lambda html: b"pdf")
    assert generate_pdf_bytes("test", {}) == b"pdf"


def test_zugferd_requires_structured_data():
    """Ohne Originalwerte wird keine scheinbare ZUGFeRD-Rechnung erzeugt."""
    with pytest.raises(ValueError, match="ZF_DATA"):
        generate_pdf_bytes("test", {"format": "zugferd"})


def test_mismatched_line_totals_are_rejected():
    """Abweichende Mengen oder Positionssummen werden vor dem Export erkannt."""
    snapshot = fixture_snapshot()
    snapshot["lines"][0]["quantity"] = Decimal("2")
    with pytest.raises(ValueError, match="ZF_LINE_TOTAL"):
        _check_snapshot(snapshot)


def test_mismatched_invoice_total_is_rejected():
    """Ein anderer Gesamtbetrag kann nicht neben der PDF exportiert werden."""
    snapshot = fixture_snapshot()
    snapshot["gross"] = Decimal("120")
    with pytest.raises(ValueError, match="ZF_GROSS_TOTAL"):
        _check_snapshot(snapshot)


def test_services_keep_numeric_values_for_export(tmp_path):
    """XML-Export nutzt berechnete Zahlen statt lokalisierter Preisstrings."""
    services = build_service_items(
        {
            "main_service": {
                "description": "Betreuung",
                "unit": "month",
                "unit_price": "19,99",
            },
            "additional_services": [
                {"description": "Inklusive", "unit": "included", "unit_price": None}
            ],
        },
        3,
        tmp_path,
    )
    line = services["items"][0]["invoice_line"]
    assert line["quantity"] == Decimal("3")
    assert line["unit_price"] == Decimal("19.99")
    assert line["total"] == Decimal("59.97")
    assert services["items"][1]["invoice_line"]["total"] == 0


def test_validation_failure_blocks_mail_archive_and_history(tmp_path, monkeypatch):
    """Bei ungueltiger XML wird weder versendet noch als gesendet gespeichert."""
    from test_workflow import _laufkontext
    from workflow import _process_customer_entry

    events = []

    def reject(*args):
        """Simuliert einen fehlgeschlagenen Standardvalidator vor SMTP."""
        raise ValueError("ZUGFERD_EN16931: invalid")

    monkeypatch.setattr("workflow.generate_pdf_bytes", reject)
    monkeypatch.setattr("workflow.load_logo_asset", lambda *args: None)
    monkeypatch.setattr("workflow.archive_pdf", lambda *args: events.append("archive"))
    monkeypatch.setattr("workflow.send_email", lambda *args: events.append("mail"))
    customer = {
        "id": "muster",
        "name": "Test",
        "company": "Testfirma",
        "email": "test@example.org",
        "street": "Testweg 1",
        "postal_code": "12345",
        "city": "Teststadt",
        "main_service": {"description": "Hosting", "unit": "month", "unit_price": "10"},
    }
    context = _laufkontext(tmp_path, pdf_config={"format": "zugferd"})
    with pytest.raises(ValueError, match="ZUGFERD_EN16931"):
        _process_customer_entry([], customer, context)
    assert events == []
    assert context.history == []
    assert not context.history_path.exists()


def test_zero_hour_month_does_not_block_mixed_rate_invoice(tmp_path):
    """Ein Nullmonat blockiert andere abrechenbare Stunden nicht."""
    from datetime import date
    from test_customer_billing_changes import customer
    from hours_files import write_hours_month
    from invoices import calculate_tax_values
    from zugferd import invoice_snapshot

    entry = customer(unit="hour", cycle=2)
    write_hours_month(tmp_path / "2026-10.yaml", "2026-10", {"fixture": Decimal("0")})
    write_hours_month(tmp_path / "2026-11.yaml", "2026-11", {"fixture": Decimal("1")})
    services = build_service_items(
        entry, 2, tmp_path, interactive=False, today=date(2026, 12, 1)
    )
    original = fixture_snapshot()
    snapshot = invoice_snapshot(
        original["customer"],
        original["sender"],
        original["bank"],
        original["tax"],
        services,
        original["dates"],
        calculate_tax_values(services["total_amount"], original["tax"]),
    )
    assert len(services["items"]) == 2
    assert len(snapshot["lines"]) == 1
    assert snapshot["lines"][0]["quantity"] == 1
    _check_snapshot(snapshot)
