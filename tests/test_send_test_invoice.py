from datetime import datetime

import pytest
from decimal import Decimal

from design import validate_design_config
from tools.send_test_invoice import (
    build_sample_context,
    build_sample_service_data,
    ask_recipient,
    ask_sample_type,
)


def _configuration() -> dict:
    """Erstellt eigene Daten fuer Musterrechnungs-Tests."""
    return {
        "sender": {
            "name": "Max Mustermann",
            "company": "Musterfirma",
            "street": "Musterstraße 1",
            "postal_code": "12345",
            "city": "Musterstadt",
            "phone": "0123 456789",
            "email": "max@example.com",
            "website": "",
        },
        "bank": {
            "account_holder": "Max Mustermann",
            "name": "Musterbank",
            "iban": "DE00000000000000000000",
            "bic": "MUSTERBIC",
        },
        "tax": {
            "small_business": True,
            "identifier_type": "tax_number",
            "tax_number": "12/345/67890",
            "tax_office": "Finanzamt Musterstadt",
        },
    }


def test_recipient_question_uses_bcc_as_default(monkeypatch):
    """Eine leere Eingabe uebernimmt die konfigurierte BCC-Adresse."""
    monkeypatch.setattr("builtins.input", lambda prompt: "")

    assert ask_recipient("bcc@example.com") == "bcc@example.com"


def test_sample_type_question_repeats_after_invalid_input(monkeypatch, capsys):
    """Die Musterart wird nach einer ungueltigen Auswahl erneut abgefragt."""
    eingaben = iter(["falsch", "3"])
    monkeypatch.setattr("builtins.input", lambda prompt: next(eingaben))

    assert ask_sample_type() == "hours"
    assert "Ungueltige Auswahl" in capsys.readouterr().out


@pytest.mark.parametrize(
    ("sample_type", "total_amount"),
    [
        ("month", Decimal("89.00")),
        ("flat", Decimal("450.00")),
        ("hours", Decimal("487.50")),
    ],
)
def test_sample_service_types_have_fixed_synthetic_values(sample_type, total_amount):
    """Alle Musterarten verwenden feste synthetische Leistungsdaten."""
    assert build_sample_service_data(sample_type)["total_amount"] == total_amount


def test_sample_context_is_clearly_marked_and_uses_current_config(tmp_path):
    """Der Musterkontext nutzt eigene Daten und ist eindeutig gekennzeichnet."""
    context, mail_logo = build_sample_context(
        "month",
        _configuration(),
        validate_design_config({}),
        {
            "pdf_logo": None,
            "mail_logo": None,
            "pdf_logo_height": 40,
            "mail_logo_height": 60,
            "header_title": None,
            "header_subtitle": None,
        },
        tmp_path,
        datetime(2026, 6, 6),
    )

    assert mail_logo is None
    assert context["sample_text"] == "MUSTER"
    assert context["invoice_number"] == "MUSTER-06-2026"
    assert context["company"] == "Beispielfirma GmbH"
    assert context["sender"]["company"] == "Musterfirma"
    assert context["header_title"] == "Max Mustermann"
    assert context["header_subtitle"] == "Musterfirma"
