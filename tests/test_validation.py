from decimal import Decimal

import pytest

from validation import (
    normalize_email_list,
    validate_amount,
    validate_date,
    validate_customer_entry,
    validate_month,
    validate_nonnegative_integer,
    validate_positive_integer,
    validate_percentage,
)


@pytest.mark.parametrize("value", ["49,9O", "0", "-1", "NaN", ""])
def test_validiere_betrag_rejects_invalid_values(value):
    """Fehlerhafte oder nichtpositive Betraege werden abgelehnt."""
    with pytest.raises(ValueError):
        validate_amount(value)


def test_validiere_betrag_accepts_inklusive_for_additional_services():
    """Zusatzservices duerfen ausdruecklich inklusive sein."""
    assert validate_amount("Inklusive", included_allowed=True) is None


@pytest.mark.parametrize("value", ["monatlich", "1.5", "0", "-1"])
def test_validiere_positive_ganzzahl_rejects_invalid_values(value):
    """Abrechnungszyklen muessen positive Ganzzahlen sein."""
    with pytest.raises(ValueError):
        validate_positive_integer(value, "Abrechnungszyklus")


def test_validiere_nichtnegative_ganzzahl_accepts_zero():
    """Eine sofortige Faelligkeit mit null Tagen bleibt erlaubt."""
    assert validate_nonnegative_integer("0", "Faelligkeit") == 0


@pytest.mark.parametrize("value", ["1.6.2026", "31.02.2026", "2026-06-01"])
def test_validiere_datum_rejects_invalid_formats(value):
    """Rechnungsdaten benoetigen das exakte und gueltige Format."""
    with pytest.raises(ValueError):
        validate_date(value)


@pytest.mark.parametrize("value", ["2026-6", "06-2026", "2026-13"])
def test_validiere_monat_rejects_invalid_formats(value):
    """Endmonate benoetigen das exakte und gueltige Format."""
    with pytest.raises(ValueError):
        validate_month(value)


def test_validiere_kundeneintrag_rejects_invalid_main_amount():
    """Ein fehlerhafter Hauptbetrag stoppt den Kundeneintrag."""
    entry = {
        "email": "kunde@example.com",
        "main_service": {
            "description": "Hosting",
            "unit": "month",
            "unit_price": "49,9O",
        },
    }

    with pytest.raises(ValueError, match="main_service.unit_price"):
        validate_customer_entry(entry)


def test_validiere_kundeneintrag_accepts_inclusive_additional_service():
    """Eine inklusive Zusatzleistung bleibt ein gueltiger Hinweis."""
    entry = {
        "email": "kunde@example.com",
        "main_service": {
            "description": "Hosting",
            "unit": "month",
            "unit_price": "49,90",
        },
        "additional_services": [
            {
                "description": "Support",
                "unit": "included",
                "unit_price": None,
            }
        ],
    }

    validate_customer_entry(entry)


def test_normalisiere_mail_liste_accepts_single_and_multiple_addresses():
    """CC-Adressen duerfen als einzelne Adresse oder Liste gepflegt werden."""
    assert normalize_email_list("cc@example.com", "cc") == ["cc@example.com"]
    assert normalize_email_list(
        ["cc@example.com", "buchhaltung@example.com"],
        "cc",
    ) == ["cc@example.com", "buchhaltung@example.com"]


def test_normalisiere_mail_liste_rejects_invalid_address():
    """Ungueltige CC-Adressen werden vor dem Versand abgelehnt."""
    with pytest.raises(ValueError, match="cc"):
        normalize_email_list(["ungueltig"], "cc")


def test_validiere_kundeneintrag_rejects_multiple_main_recipients():
    """Die Hauptadresse bleibt eine einzelne To-Adresse."""
    entry = {
        "email": ["kunde@example.com", "team@example.com"],
        "main_service": {
            "description": "Hosting",
            "unit": "month",
            "unit_price": "49,90",
        },
    }

    with pytest.raises(ValueError, match="email"):
        validate_customer_entry(entry)


def test_money_rejects_more_than_two_decimal_places():
    """Geldwerte duerfen keine Bruchteile eines Cents enthalten."""
    with pytest.raises(ValueError, match="zwei Nachkommastellen"):
        validate_amount("10.001")


@pytest.mark.parametrize("value", ["0", "19.5", "100"])
def test_percentage_accepts_decimal_range(value):
    """Prozentsaetze akzeptieren Dezimalwerte einschliesslich Grenzen."""
    assert validate_percentage(value) == Decimal(value)
