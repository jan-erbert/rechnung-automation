from datetime import datetime

import pytest

from rechnungen import baue_rechnungsdaten, berechne_steuerwerte


def test_baue_rechnungsdaten_uses_prefix_and_due_date():
    """Rechnungsnummer und Faelligkeit werden aus Kundendaten berechnet."""
    heute = datetime(2026, 6, 4)
    eintrag = {
        "rechnungsnummer": "TEST",
        "rechnungsdatum": "01.06.2026",
        "faelligkeit": "14",
    }

    daten = baue_rechnungsdaten(eintrag, heute)

    assert daten["rechnungsdatum"] == "01.06.2026"
    assert daten["faelligkeit_datum"] == "15.06.2026"
    assert daten["rechnungsnummer"] == "TEST-06-2026"


def test_berechne_steuerwerte_for_kleinunternehmer():
    """Kleinunternehmer-Rechnungen bleiben ohne Umsatzsteuer."""
    steuerdaten = berechne_steuerwerte(
        100.0,
        {"kleinunternehmer": True},
    )

    assert steuerdaten["steuerbetrag"] == 0
    assert steuerdaten["gesamtpreis_mit_mwst"] == 100.0
    assert steuerdaten["gesamtpreis_str"] == "100,00"


def test_berechne_steuerwerte_with_mwst():
    """Regulaere Rechnungen berechnen Steuerbetrag und Bruttosumme."""
    steuerdaten = berechne_steuerwerte(
        100.0,
        {"kleinunternehmer": False, "mehrwertsteuer_prozent": 19},
    )

    assert steuerdaten["steuerbetrag"] == 19.0
    assert steuerdaten["gesamtpreis_mit_mwst"] == 119.0
    assert steuerdaten["gesamtpreis_str"] == "119,00"


def test_baue_rechnungsdaten_rejects_invalid_due_days():
    """Eine fehlerhafte Faelligkeit wird nicht still ersetzt."""
    with pytest.raises(ValueError, match="Faelligkeit"):
        baue_rechnungsdaten({"faelligkeit": "vierzehn"}, datetime(2026, 6, 4))


def test_baue_rechnungsdaten_rejects_invalid_invoice_date():
    """Ein ungueltiges Rechnungsdatum wird verstaendlich abgelehnt."""
    with pytest.raises(ValueError, match="Rechnungsdatum"):
        baue_rechnungsdaten(
            {"rechnungsdatum": "31.02.2026"},
            datetime(2026, 6, 4),
        )
