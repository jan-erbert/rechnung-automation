from decimal import Decimal

import pytest
import yaml

from customer_files import load_customer_files, save_customer_file


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

    customers = load_customer_files(tmp_path)

    assert len(customers) == 1
    assert customers[0]["id"] == "musterfirma"
    assert customers[0]["postal_code"] == "01234"
    assert customers[0]["main_service"]["unit_price"] == "49.90"
    assert customers[0]["additional_services"][0]["unit_price"] is None


def test_rejects_duplicate_customer_ids(tmp_path):
    """Doppelte stabile IDs werden verzeichnisweit abgelehnt."""
    for name in ("eins.yaml", "zwei.yaml"):
        (tmp_path / name).write_text(
            yaml.safe_dump(_customer(), sort_keys=False), encoding="utf-8"
        )

    with pytest.raises(ValueError, match="Doppelte Kunden-ID"):
        load_customer_files(tmp_path)


def test_non_strict_loading_skips_only_invalid_customer(tmp_path, caplog):
    """Ein ungueltiger Kunde blockiert im Rechnungslauf keine gueltigen Dateien."""
    (tmp_path / "gueltig.yaml").write_text(
        yaml.safe_dump(_customer(), sort_keys=False), encoding="utf-8"
    )
    (tmp_path / "ungueltig.yaml").write_text("contact: [", encoding="utf-8")

    customers = load_customer_files(tmp_path, strict=False)

    assert [customer["id"] for customer in customers] == ["musterfirma"]
    assert "wird uebersprungen" in caplog.text


def test_rejects_unquoted_money_value(tmp_path):
    """YAML-Gleitkommazahlen werden fuer Geldwerte bewusst abgelehnt."""
    customer = _customer()
    customer["main_service"]["unit_price"] = 49.9
    (tmp_path / "musterfirma.yaml").write_text(
        yaml.safe_dump(customer, sort_keys=False), encoding="utf-8"
    )

    with pytest.raises(ValueError, match="Anfuehrungszeichen"):
        load_customer_files(tmp_path)


def test_customer_write_is_roundtrip_safe(tmp_path):
    """Atomar gespeicherte Kundendaten lassen sich verlustfrei neu laden."""
    internal = {
        "id": "musterfirma",
        "active": True,
        "name": "Erika Beispiel",
        "company": "Musterfirma",
        "email": "erika@example.com",
        "cc": [],
        "street": "Musterweg 1",
        "postal_code": "01234",
        "city": "Musterstadt",
        "website": None,
        "invoice_prefix": "MF",
        "cycle_months": 1,
        "due_days": 14,
        "end_month": None,
        "invoice_date": None,
        "one_time": False,
        "main_service": {
            "description": "Hosting",
            "unit": "month",
            "unit_price": Decimal("49.90"),
        },
        "additional_services": [],
        "archive_directory": None,
    }
    target = tmp_path / "musterfirma.yaml"

    save_customer_file(internal, target)
    loaded = load_customer_files(tmp_path)[0]

    assert loaded["id"] == internal["id"]
    assert loaded["postal_code"] == "01234"
    assert loaded["main_service"]["unit_price"] == "49.90"
