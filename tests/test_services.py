import pytest
from decimal import Decimal

from services import build_service_items, calculate_hourly_service
from hours_files import write_hours_month


@pytest.mark.parametrize("website", ["", None])
def test_leistungsposition_hides_empty_optional_website(tmp_path, website):
    """Leere Webseiten erzeugen keine leeren Klammern in Positionen."""
    entry = {
        "company": "Beispielfirma",
        "website": website,
        "main_service": {
            "description": "Hosting",
            "unit": "month",
            "unit_price": "10,00",
        },
    }

    result = build_service_items(entry, 1, tmp_path)

    assert result["items"][0]["description"] == "Hosting für 1 Monat"


def test_leistungsposition_renders_available_website(tmp_path):
    """Eine vorhandene Webseite bleibt in der Leistungsposition sichtbar."""
    entry = {
        "company": "Beispielfirma",
        "website": "example.com",
        "main_service": {
            "description": "Hosting",
            "unit": "month",
            "unit_price": "10,00",
        },
    }

    result = build_service_items(entry, 1, tmp_path)

    assert result["items"][0]["description"] == "Hosting für 1 Monat (example.com)"


def test_leistungsposition_rejects_invalid_main_amount(tmp_path):
    """Ein fehlerhafter Hauptbetrag wird nicht als Nullbetrag verarbeitet."""
    entry = {
        "company": "Beispielfirma",
        "main_service": {
            "description": "Hosting",
            "unit": "month",
            "unit_price": "49,9O",
        },
    }

    with pytest.raises(ValueError, match="main_service.unit_price"):
        build_service_items(entry, 1, tmp_path)


def test_pauschale_zusatzleistung_is_added_once(tmp_path):
    """Pauschale Zusatzservices werden unabhaengig vom Zyklus einmal addiert."""
    entry = {
        "company": "Beispielfirma",
        "cycle_months": 3,
        "main_service": {
            "description": "Projekt",
            "unit": "flat",
            "unit_price": "100,00",
        },
        "additional_services": [
            {
                "description": "Einrichtung",
                "unit_price": "20,00",
            }
        ],
    }

    result = build_service_items(entry, 3, tmp_path)

    assert result["items"][1]["price"] == "20,00 EUR"
    assert result["total_amount"] == Decimal("120.00")


def test_monatliche_zusatzleistung_uses_billing_cycle(tmp_path):
    """Monatliche Zusatzservices bleiben an den Zyklus gekoppelt."""
    entry = {
        "company": "Beispielfirma",
        "main_service": {
            "description": "Hosting",
            "unit": "month",
            "unit_price": "10,00",
        },
        "additional_services": [
            {
                "description": "Support",
                "unit_price": "5,00",
            }
        ],
    }

    result = build_service_items(entry, 3, tmp_path)

    assert result["items"][1]["price"] == "15,00 EUR"
    assert result["total_amount"] == Decimal("45.00")


def test_inklusive_zusatzleistung_does_not_change_total(tmp_path):
    """Eine inklusive Zusatzleistung veraendert die Rechnungssumme nicht."""
    entry = {
        "company": "Beispielfirma",
        "main_service": {
            "description": "Hosting",
            "unit": "month",
            "unit_price": "10,00",
        },
        "additional_services": [
            {
                "description": "Support",
                "unit": "included",
                "unit_price": None,
            }
        ],
    }

    result = build_service_items(entry, 3, tmp_path)

    assert result["items"][1]["price"] == "Inklusive"
    assert result["total_amount"] == Decimal("30.00")


def test_incomplete_multi_month_hours_do_not_create_partial_invoice(
    tmp_path,
    monkeypatch,
):
    """Fehlende Monatsdaten verhindern eine unvollstaendige Cronrechnung."""
    write_hours_month(
        tmp_path / "2026-06.yaml",
        "2026-06",
        {"beispielfirma": Decimal("5.00")},
    )

    result = build_service_items(
        {
            "id": "beispielfirma",
            "company": "Beispielfirma",
            "main_service": {
                "description": "Beratung",
                "unit": "hour",
                "unit_price": "100,00",
            },
        },
        3,
        tmp_path,
        interactive=False,
        today=FixedDatetime.today().date(),
    )

    assert result["hours_info"]["hours"] == 5
    assert result["hours_info"]["complete"] is False
    assert result["items"] == []
    assert result["total_amount"] == Decimal("0")


def test_complete_multi_month_hours_can_be_billed(tmp_path, monkeypatch):
    """Vollstaendige Monatsdaten bleiben bei Mehrmonatszyklen abrechenbar."""
    for monat in (4, 5, 6):
        period = f"2026-{monat:02d}"
        write_hours_month(
            tmp_path / f"{period}.yaml",
            period,
            {"beispielfirma": Decimal("1.00")},
        )

    result = calculate_hourly_service(
        "beispielfirma",
        3,
        Decimal("100.00"),
        tmp_path,
        interactive=False,
        today=FixedDatetime.today().date(),
    )

    assert result["hours"] == 3
    assert result["complete"] is True
    assert result["missing_months"] == []
    assert result["period"] == "April 2026, Mai 2026, Juni 2026"


def test_manual_hours_are_persisted_as_yaml(tmp_path, monkeypatch):
    """Eine manuelle Stundenangabe bleibt reproduzierbar im Monats-YAML."""
    monkeypatch.setattr("builtins.input", lambda *args: "6,5")

    result = calculate_hourly_service(
        "beispielfirma",
        1,
        Decimal("100.00"),
        tmp_path,
        interactive=True,
        today=FixedDatetime.today().date(),
    )

    assert result["hours"] == Decimal("6.5")
    assert result["period"] == "Juni 2026"
    assert (tmp_path / "2026-06.yaml").is_file()


def test_invalid_manual_hours_are_requested_again(tmp_path, monkeypatch, caplog):
    """Eine fehlerhafte Stundenangabe wird nicht still als null uebernommen."""
    eingaben = iter(("ungueltig", "2.25"))
    monkeypatch.setattr("builtins.input", lambda *args: next(eingaben))

    result = calculate_hourly_service(
        "beispielfirma",
        1,
        Decimal("100.00"),
        tmp_path,
        interactive=True,
        today=FixedDatetime.today().date(),
    )

    assert result["hours"] == Decimal("2.25")
    assert "Bitte erneut eingeben" in caplog.text


class FixedDatetime:
    """Stellt fuer Stundenlogiktests ein festes heutiges Datum bereit."""

    @classmethod
    def today(cls):
        """Liefert den festen Testzeitpunkt."""
        from datetime import datetime

        return datetime(2026, 7, 15)
