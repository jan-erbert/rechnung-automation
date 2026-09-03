from decimal import Decimal

import pytest
import yaml

from kundendateien import lade_kundendateien, speichere_kundendatei


def _customer(customer_id: str = "musterfirma") -> dict:
    """Erstellt einen minimalen gueltigen YAML-Kunden."""
    return {
        "id": customer_id,
        "active": True,
        "contact": {
            "name": "Erika Beispiel",
            "company": "Musterfirma",
            "email": "erika@example.com",
            "cc": [],
            "street": "Musterweg 1",
            "postal_code": "01234",
            "city": "Musterstadt",
        },
        "billing": {"cycle_months": 1, "due_days": 14},
        "main_service": {
            "description": "Hosting",
            "unit": "month",
            "unit_price": "49.90",
        },
        "additional_services": [{"description": "Support", "unit": "included"}],
    }


def test_loads_one_customer_per_yaml_file(tmp_path):
    """Jede YAML-Datei wird als eigener Kunde geladen und normalisiert."""
    (tmp_path / "musterfirma.yaml").write_text(
        yaml.safe_dump(_customer(), sort_keys=False), encoding="utf-8"
    )

    kunden = lade_kundendateien(tmp_path)

    assert len(kunden) == 1
    assert kunden[0]["id"] == "musterfirma"
    assert kunden[0]["plz"] == "01234"
    assert kunden[0]["hauptleistung"]["betrag"] == "49.90"
    assert kunden[0]["weitere_leistungen"][0]["preis"] == "Inklusive"


def test_rejects_duplicate_customer_ids(tmp_path):
    """Doppelte stabile IDs werden verzeichnisweit abgelehnt."""
    for name in ("eins.yaml", "zwei.yaml"):
        (tmp_path / name).write_text(
            yaml.safe_dump(_customer(), sort_keys=False), encoding="utf-8"
        )

    with pytest.raises(ValueError, match="Doppelte Kunden-ID"):
        lade_kundendateien(tmp_path)


def test_non_strict_loading_skips_only_invalid_customer(tmp_path, caplog):
    """Ein ungueltiger Kunde blockiert im Rechnungslauf keine gueltigen Dateien."""
    (tmp_path / "gueltig.yaml").write_text(
        yaml.safe_dump(_customer(), sort_keys=False), encoding="utf-8"
    )
    (tmp_path / "ungueltig.yaml").write_text("contact: [", encoding="utf-8")

    kunden = lade_kundendateien(tmp_path, strict=False)

    assert [kunde["id"] for kunde in kunden] == ["musterfirma"]
    assert "wird uebersprungen" in caplog.text


def test_rejects_unquoted_money_value(tmp_path):
    """YAML-Gleitkommazahlen werden fuer Geldwerte bewusst abgelehnt."""
    customer = _customer()
    customer["main_service"]["unit_price"] = 49.9
    (tmp_path / "musterfirma.yaml").write_text(
        yaml.safe_dump(customer, sort_keys=False), encoding="utf-8"
    )

    with pytest.raises(ValueError, match="Anfuehrungszeichen"):
        lade_kundendateien(tmp_path)


def test_customer_write_is_roundtrip_safe(tmp_path):
    """Atomar gespeicherte Kundendaten lassen sich verlustfrei neu laden."""
    internal = {
        "id": "musterfirma",
        "aktiv": True,
        "name": "Erika Beispiel",
        "firma": "Musterfirma",
        "email": "erika@example.com",
        "cc": [],
        "strasse": "Musterweg 1",
        "plz": "01234",
        "ort": "Musterstadt",
        "webseite": None,
        "rechnungsnummer": "MF",
        "abrechnungszyklus": 1,
        "faelligkeit": 14,
        "letzte_rechnung": None,
        "rechnungsdatum": None,
        "einmalig": False,
        "hauptleistung": {
            "beschreibung": "Hosting",
            "einheit": "monat",
            "betrag": Decimal("49.90"),
        },
        "weitere_leistungen": [],
        "archiv_pfad": None,
    }
    target = tmp_path / "musterfirma.yaml"

    speichere_kundendatei(internal, target)
    loaded = lade_kundendateien(tmp_path)[0]

    assert loaded["id"] == internal["id"]
    assert loaded["plz"] == "01234"
    assert loaded["hauptleistung"]["betrag"] == "49.90"
