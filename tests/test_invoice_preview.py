from datetime import date, datetime
from pathlib import Path
from types import SimpleNamespace

import pytest

from design import validate_design_config
from invoice_preview import create_customer_invoice_preview


class CapturingTemplates:
    """Erfasst den Kontext der gerenderten Vorschau."""

    class InvoiceTemplate:
        """Rendert minimales PDF-HTML fuer den Test."""

        def __init__(self, contexts):
            """Speichert die gemeinsame Kontextliste."""
            self.contexts = contexts

        def render(self, context):
            """Erfasst den Kontext und gibt minimales HTML zurueck."""
            self.contexts.append(context)
            return "<html></html>"

    def __init__(self):
        """Initialisiert das Testtemplate mit Kontextspeicher."""
        self.contexts = []
        self.invoice = self.InvoiceTemplate(self.contexts)


def _customer(archive_directory: Path | None) -> dict:
    """Erstellt einen gueltigen Kunden fuer Vorschautests."""
    return {
        "id": "example",
        "active": True,
        "name": "Erika Beispiel",
        "company": "Example GmbH",
        "email": "erika@example.com",
        "cc": [],
        "street": "Beispielweg 1",
        "postal_code": "12345",
        "city": "Beispielstadt",
        "cycle_months": 1,
        "main_service": {
            "description": "Hosting",
            "unit": "month",
            "unit_price": "10.00",
        },
        "additional_services": [],
        "archive_directory": str(archive_directory) if archive_directory else None,
    }


def _invoice_config() -> dict:
    """Erstellt eine minimale Rechnungskonfiguration fuer Vorschautests."""
    return {
        "sender": {
            "name": "Max Mustermann",
            "company": "Musterfirma",
            "street": "Musterweg 1",
            "postal_code": "12345",
            "city": "Musterstadt",
            "phone": "0123",
            "email": "max@example.com",
            "website": "",
        },
        "bank": {
            "name": "Musterbank",
            "account_holder": "Max Mustermann",
            "iban": "DE00000000000000000000",
            "bic": "TESTDE00",
        },
        "tax": {
            "small_business": True,
            "identifier_type": "tax_number",
            "tax_number": "12/345",
            "tax_office": "Finanzamt Musterstadt",
        },
    }


def _branding() -> dict:
    """Erstellt eine Branding-Konfiguration ohne Bilddateien."""
    return {
        "pdf_logo": None,
        "mail_logo": None,
        "pdf_logo_height": 40,
        "mail_logo_height": 60,
        "header_title": None,
        "header_subtitle": None,
    }


def test_preview_writes_only_watermarked_pdf_to_customer_archive(tmp_path, monkeypatch):
    """Die Vorschau landet markiert und eindeutig benannt nur im Kundenarchiv."""
    archive_directory = tmp_path / "archive"
    archive_directory.mkdir()
    templates = CapturingTemplates()
    monkeypatch.setattr("invoice_preview.today", lambda: date(2026, 9, 4))
    monkeypatch.setattr("invoice_preview.generate_pdf_bytes", lambda *args: b"pdf")

    target = create_customer_invoice_preview(
        customer=_customer(archive_directory),
        paths=SimpleNamespace(
            base_dir=tmp_path,
            img_dir=tmp_path,
            hours_dir=tmp_path / "hours",
        ),
        invoice_config=_invoice_config(),
        pdf_config={"engine": "weasyprint"},
        design_config=validate_design_config({}),
        branding_config=_branding(),
        templates=templates,
        timestamp=datetime(2026, 9, 4, 14, 30, 0),
    )

    assert target.name == "PREVIEW_Invoice_example_09-2026_2026-09-04_14-30-00.pdf"
    assert target.read_bytes() == b"pdf"
    assert templates.contexts[0]["sample_text"] == "VORSCHAU"
    assert templates.contexts[0]["invoice_number"] == "09-2026"
    assert list(archive_directory.iterdir()) == [target]


def test_preview_requires_customer_archive(tmp_path):
    """Ohne Kundenarchiv wird keine Vorschau erzeugt."""
    with pytest.raises(ValueError, match="archive_directory"):
        create_customer_invoice_preview(
            customer=_customer(None),
            paths=SimpleNamespace(
                base_dir=tmp_path,
                img_dir=tmp_path,
                hours_dir=tmp_path / "hours",
            ),
            invoice_config=_invoice_config(),
            pdf_config={"engine": "weasyprint"},
            design_config=validate_design_config({}),
            branding_config=_branding(),
            templates=CapturingTemplates(),
        )


def test_preview_resolves_relative_archive_and_avoids_filename_collision(
    tmp_path, monkeypatch
):
    """Relative Archive und identische Zeitstempel bleiben sicher nutzbar."""
    archive_directory = tmp_path / "archive"
    archive_directory.mkdir()
    existing_path = archive_directory / (
        "PREVIEW_Invoice_example_09-2026_2026-09-04_14-30-00.pdf"
    )
    existing_path.write_bytes(b"existing")
    monkeypatch.setattr("invoice_preview.today", lambda: date(2026, 9, 4))
    monkeypatch.setattr("invoice_preview.generate_pdf_bytes", lambda *args: b"new")

    target = create_customer_invoice_preview(
        customer=_customer(Path("archive")),
        paths=SimpleNamespace(
            base_dir=tmp_path,
            img_dir=tmp_path,
            hours_dir=tmp_path / "hours",
        ),
        invoice_config=_invoice_config(),
        pdf_config={"engine": "weasyprint"},
        design_config=validate_design_config({}),
        branding_config=_branding(),
        templates=CapturingTemplates(),
        timestamp=datetime(2026, 9, 4, 14, 30, 0),
    )

    assert target.name.endswith("-02.pdf")
    assert existing_path.read_bytes() == b"existing"
    assert target.read_bytes() == b"new"
