import pytest

from validierung import (
    normalisiere_mail_liste,
    validiere_betrag,
    validiere_datum,
    validiere_kundeneintrag,
    validiere_monat,
    validiere_nichtnegative_ganzzahl,
    validiere_positive_ganzzahl,
)


@pytest.mark.parametrize("wert", ["49,9O", "0", "-1", "NaN", ""])
def test_validiere_betrag_rejects_invalid_values(wert):
    """Fehlerhafte oder nichtpositive Betraege werden abgelehnt."""
    with pytest.raises(ValueError):
        validiere_betrag(wert)


def test_validiere_betrag_accepts_inklusive_for_additional_services():
    """Zusatzleistungen duerfen ausdruecklich inklusive sein."""
    assert validiere_betrag("Inklusive", inklusive_erlaubt=True) is None


@pytest.mark.parametrize("wert", ["monatlich", "1.5", "0", "-1"])
def test_validiere_positive_ganzzahl_rejects_invalid_values(wert):
    """Abrechnungszyklen muessen positive Ganzzahlen sein."""
    with pytest.raises(ValueError):
        validiere_positive_ganzzahl(wert, "Abrechnungszyklus")


def test_validiere_nichtnegative_ganzzahl_accepts_zero():
    """Eine sofortige Faelligkeit mit null Tagen bleibt erlaubt."""
    assert validiere_nichtnegative_ganzzahl("0", "Faelligkeit") == 0


@pytest.mark.parametrize("wert", ["1.6.2026", "31.02.2026", "2026-06-01"])
def test_validiere_datum_rejects_invalid_formats(wert):
    """Rechnungsdaten benoetigen das exakte und gueltige Format."""
    with pytest.raises(ValueError):
        validiere_datum(wert)


@pytest.mark.parametrize("wert", ["2026-6", "06-2026", "2026-13"])
def test_validiere_monat_rejects_invalid_formats(wert):
    """Endmonate benoetigen das exakte und gueltige Format."""
    with pytest.raises(ValueError):
        validiere_monat(wert)


def test_validiere_kundeneintrag_rejects_invalid_main_amount():
    """Ein fehlerhafter Hauptbetrag stoppt den Kundeneintrag."""
    eintrag = {
        "email": "kunde@example.com",
        "hauptleistung": {
            "beschreibung": "Hosting",
            "einheit": "Monat",
            "betrag": "49,9O",
        },
    }

    with pytest.raises(ValueError, match="Hauptleistung.betrag"):
        validiere_kundeneintrag(eintrag)


def test_validiere_kundeneintrag_accepts_inclusive_additional_service():
    """Eine inklusive Zusatzleistung bleibt ein gueltiger Hinweis."""
    eintrag = {
        "email": "kunde@example.com",
        "hauptleistung": {
            "beschreibung": "Hosting",
            "einheit": "Monat",
            "betrag": "49,90",
        },
        "weitere_leistungen": [
            {
                "beschreibung": "Support",
                "preis": "Inklusive",
            }
        ],
    }

    validiere_kundeneintrag(eintrag)


def test_normalisiere_mail_liste_accepts_single_and_multiple_addresses():
    """CC-Adressen duerfen als einzelne Adresse oder Liste gepflegt werden."""
    assert normalisiere_mail_liste("cc@example.com", "cc") == ["cc@example.com"]
    assert normalisiere_mail_liste(
        ["cc@example.com", "buchhaltung@example.com"],
        "cc",
    ) == ["cc@example.com", "buchhaltung@example.com"]


def test_normalisiere_mail_liste_rejects_invalid_address():
    """Ungueltige CC-Adressen werden vor dem Versand abgelehnt."""
    with pytest.raises(ValueError, match="cc"):
        normalisiere_mail_liste(["ungueltig"], "cc")


def test_validiere_kundeneintrag_rejects_multiple_main_recipients():
    """Die Hauptadresse bleibt eine einzelne To-Adresse."""
    eintrag = {
        "email": ["kunde@example.com", "team@example.com"],
        "hauptleistung": {
            "beschreibung": "Hosting",
            "einheit": "Monat",
            "betrag": "49,90",
        },
    }

    with pytest.raises(ValueError, match="email"):
        validiere_kundeneintrag(eintrag)
