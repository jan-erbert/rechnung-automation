from datetime import datetime
from decimal import Decimal

import pytest

from invoices import build_invoice_data, calculate_tax_values


def test_baue_rechnungsdaten_uses_prefix_and_due_date():
    """Rechnungsnummer und Faelligkeit werden aus Kundendaten berechnet."""
    today = datetime(2026, 6, 4)
    entry = {
        "invoice_prefix": "TEST",
        "invoice_date": "01.06.2026",
        "due_days": "14",
    }

    data = build_invoice_data(entry, today)

    assert data["invoice_date"] == "01.06.2026"
    assert data["due_date"] == "15.06.2026"
    assert data["invoice_number"] == "TEST-06-2026"


def test_null_invoice_prefix_uses_automatic_number():
    """Ein YAML-null beim optionalen Praefix nutzt die automatische Nummer."""
    data = build_invoice_data(
        {"invoice_prefix": None, "due_days": 14},
        datetime(2026, 6, 4),
    )

    assert data["invoice_number"] == "06-2026"


def test_berechne_steuerwerte_for_kleinunternehmer():
    """Kleinunternehmer-Rechnungen bleiben ohne Umsatzsteuer."""
    steuerdaten = calculate_tax_values(
        Decimal("100.00"),
        {"small_business": True},
    )

    assert steuerdaten["tax_amount"] == Decimal("0.00")
    assert steuerdaten["gross_amount"] == Decimal("100.00")
    assert steuerdaten["formatted_total"] == "100,00"


def test_berechne_steuerwerte_with_mwst():
    """Regulaere Rechnungen berechnen Steuerbetrag und Bruttosumme."""
    steuerdaten = calculate_tax_values(
        Decimal("100.00"),
        {"small_business": False, "vat_rate": 19},
    )

    assert steuerdaten["tax_amount"] == Decimal("19.00")
    assert steuerdaten["gross_amount"] == Decimal("119.00")
    assert steuerdaten["formatted_total"] == "119,00"


def test_baue_rechnungsdaten_rejects_invalid_due_days():
    """Eine fehlerhafte Faelligkeit wird nicht still ersetzt."""
    with pytest.raises(ValueError, match="Faelligkeit"):
        build_invoice_data({"due_days": "vierzehn"}, datetime(2026, 6, 4))


def test_baue_rechnungsdaten_rejects_invalid_invoice_date():
    """Ein ungueltiges Rechnungsdatum wird verstaendlich abgelehnt."""
    with pytest.raises(ValueError, match="Rechnungsdatum"):
        build_invoice_data(
            {"invoice_date": "31.02.2026"},
            datetime(2026, 6, 4),
        )
