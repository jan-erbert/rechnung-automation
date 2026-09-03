import pytest
from decimal import Decimal

from leistungen import baue_leistungspositionen, berechne_stundenleistung


@pytest.mark.parametrize("webseite", ["", None])
def test_leistungsposition_hides_empty_optional_website(tmp_path, webseite):
    """Leere Webseiten erzeugen keine leeren Klammern in Positionen."""
    eintrag = {
        "firma": "Beispielfirma",
        "webseite": webseite,
        "hauptleistung": {
            "beschreibung": "Hosting",
            "einheit": "Monat",
            "betrag": "10,00",
        },
    }

    ergebnis = baue_leistungspositionen(eintrag, 1, tmp_path)

    assert ergebnis["leistungs_liste"][0]["beschreibung"] == "Hosting für 1 Monat"


def test_leistungsposition_renders_available_website(tmp_path):
    """Eine vorhandene Webseite bleibt in der Leistungsposition sichtbar."""
    eintrag = {
        "firma": "Beispielfirma",
        "webseite": "example.com",
        "hauptleistung": {
            "beschreibung": "Hosting",
            "einheit": "Monat",
            "betrag": "10,00",
        },
    }

    ergebnis = baue_leistungspositionen(eintrag, 1, tmp_path)

    assert (
        ergebnis["leistungs_liste"][0]["beschreibung"]
        == "Hosting für 1 Monat (example.com)"
    )


def test_leistungsposition_rejects_invalid_main_amount(tmp_path):
    """Ein fehlerhafter Hauptbetrag wird nicht als Nullbetrag verarbeitet."""
    eintrag = {
        "firma": "Beispielfirma",
        "hauptleistung": {
            "beschreibung": "Hosting",
            "einheit": "Monat",
            "betrag": "49,9O",
        },
    }

    with pytest.raises(ValueError, match="Hauptleistung.betrag"):
        baue_leistungspositionen(eintrag, 1, tmp_path)


def test_pauschale_zusatzleistung_is_added_once(tmp_path):
    """Pauschale Zusatzleistungen werden unabhaengig vom Zyklus einmal addiert."""
    eintrag = {
        "firma": "Beispielfirma",
        "abrechnungszyklus": 3,
        "hauptleistung": {
            "beschreibung": "Projekt",
            "einheit": "pauschal",
            "betrag": "100,00",
        },
        "weitere_leistungen": [
            {
                "beschreibung": "Einrichtung",
                "preis": "20,00",
            }
        ],
    }

    ergebnis = baue_leistungspositionen(eintrag, 3, tmp_path)

    assert ergebnis["leistungs_liste"][1]["preis"] == "20,00 EUR"
    assert ergebnis["gesamtpreis"] == Decimal("120.00")


def test_monatliche_zusatzleistung_uses_billing_cycle(tmp_path):
    """Monatliche Zusatzleistungen bleiben an den Zyklus gekoppelt."""
    eintrag = {
        "firma": "Beispielfirma",
        "hauptleistung": {
            "beschreibung": "Hosting",
            "einheit": "Monat",
            "betrag": "10,00",
        },
        "weitere_leistungen": [
            {
                "beschreibung": "Support",
                "preis": "5,00",
            }
        ],
    }

    ergebnis = baue_leistungspositionen(eintrag, 3, tmp_path)

    assert ergebnis["leistungs_liste"][1]["preis"] == "15,00 EUR"
    assert ergebnis["gesamtpreis"] == Decimal("45.00")


def test_inklusive_zusatzleistung_does_not_change_total(tmp_path):
    """Eine inklusive Zusatzleistung veraendert die Rechnungssumme nicht."""
    eintrag = {
        "firma": "Beispielfirma",
        "hauptleistung": {
            "beschreibung": "Hosting",
            "einheit": "Monat",
            "betrag": "10,00",
        },
        "weitere_leistungen": [
            {
                "beschreibung": "Support",
                "preis": "Inklusive",
            }
        ],
    }

    ergebnis = baue_leistungspositionen(eintrag, 3, tmp_path)

    assert ergebnis["leistungs_liste"][1]["preis"] == "Inklusive"
    assert ergebnis["gesamtpreis"] == Decimal("30.00")


def test_incomplete_multi_month_hours_do_not_create_partial_invoice(
    tmp_path,
    monkeypatch,
):
    """Fehlende Monatsdaten verhindern eine unvollstaendige Cronrechnung."""
    (tmp_path / "stunden_2026_06.json").write_text(
        '[{"firma": "Beispielfirma", "stunden": 5}]',
        encoding="utf-8",
    )

    ergebnis = baue_leistungspositionen(
        {
            "firma": "Beispielfirma",
            "hauptleistung": {
                "beschreibung": "Beratung",
                "einheit": "Stunde",
                "betrag": "100,00",
            },
        },
        3,
        tmp_path,
        interactive=False,
        heute=FixedDatetime.today().date(),
    )

    assert ergebnis["stundeninfo"]["stunden"] == 5
    assert ergebnis["stundeninfo"]["vollstaendig"] is False
    assert ergebnis["leistungs_liste"] == []
    assert ergebnis["gesamtpreis"] == Decimal("0")


def test_complete_multi_month_hours_can_be_billed(tmp_path, monkeypatch):
    """Vollstaendige Monatsdaten bleiben bei Mehrmonatszyklen abrechenbar."""
    for monat in (4, 5, 6):
        (tmp_path / f"stunden_2026_{monat:02d}.json").write_text(
            '[{"firma": "Beispielfirma", "stunden": 1}]',
            encoding="utf-8",
        )

    ergebnis = berechne_stundenleistung(
        "Beispielfirma",
        3,
        Decimal("100.00"),
        tmp_path,
        interactive=False,
        heute=FixedDatetime.today().date(),
    )

    assert ergebnis["stunden"] == 3
    assert ergebnis["vollstaendig"] is True
    assert ergebnis["fehlende_monate"] == []


class FixedDatetime:
    """Stellt fuer Stundenlogiktests ein festes heutiges Datum bereit."""

    @classmethod
    def today(cls):
        """Liefert den festen Testzeitpunkt."""
        from datetime import datetime

        return datetime(2026, 7, 15)
