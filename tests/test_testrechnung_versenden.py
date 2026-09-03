from datetime import datetime

import pytest
from decimal import Decimal

from design import validiere_design_config
from tools.testrechnung_versenden import (
    baue_muster_context,
    baue_muster_leistungsdaten,
    frage_empfaenger,
    frage_musterart,
)


def _konfiguration() -> dict:
    """Erstellt eigene Daten fuer Musterrechnungs-Tests."""
    return {
        "absender": {
            "name": "Max Mustermann",
            "firma": "Musterfirma",
            "straße": "Musterstraße 1",
            "plz": "12345",
            "ort": "Musterstadt",
            "telefon": "0123 456789",
            "email": "max@example.com",
            "website": "",
        },
        "bank": {
            "kontoinhaber": "Max Mustermann",
            "bankname": "Musterbank",
            "iban": "DE00000000000000000000",
            "bic": "MUSTERBIC",
        },
        "finanzen": {
            "kleinunternehmer": True,
            "steuer_id_typ": "steuernummer",
            "steuernummer": "12/345/67890",
            "finanzamt": "Finanzamt Musterstadt",
        },
    }


def test_recipient_question_uses_bcc_as_default(monkeypatch):
    """Eine leere Eingabe uebernimmt die konfigurierte BCC-Adresse."""
    monkeypatch.setattr("builtins.input", lambda prompt: "")

    assert frage_empfaenger("bcc@example.com") == "bcc@example.com"


def test_sample_type_question_repeats_after_invalid_input(monkeypatch, capsys):
    """Die Musterart wird nach einer ungueltigen Auswahl erneut abgefragt."""
    eingaben = iter(["falsch", "3"])
    monkeypatch.setattr("builtins.input", lambda prompt: next(eingaben))

    assert frage_musterart() == "stunden"
    assert "Ungueltige Auswahl" in capsys.readouterr().out


@pytest.mark.parametrize(
    ("musterart", "gesamtpreis"),
    [
        ("monat", Decimal("89.00")),
        ("pauschal", Decimal("450.00")),
        ("stunden", Decimal("487.50")),
    ],
)
def test_sample_service_types_have_fixed_synthetic_values(musterart, gesamtpreis):
    """Alle Musterarten verwenden feste synthetische Leistungsdaten."""
    assert baue_muster_leistungsdaten(musterart)["gesamtpreis"] == gesamtpreis


def test_sample_context_is_clearly_marked_and_uses_current_config(tmp_path):
    """Der Musterkontext nutzt eigene Daten und ist eindeutig gekennzeichnet."""
    context, mail_logo = baue_muster_context(
        "monat",
        _konfiguration(),
        validiere_design_config({}),
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
    assert context["muster_text"] == "MUSTER"
    assert context["rechnungsnummer"] == "MUSTER-06-2026"
    assert context["firma"] == "Beispielfirma GmbH"
    assert context["absender"]["firma"] == "Musterfirma"
    assert context["header_title"] == "Max Mustermann"
    assert context["header_subtitle"] == "Musterfirma"
