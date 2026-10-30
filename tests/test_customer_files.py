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
            "first_name": "Erika",
            "last_name": "Beispiel",
            "salutation": "frau",
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
    assert customers[0]["name"] == "Erika Beispiel"
    assert customers[0]["mail_salutation"] == "Sehr geehrte Frau Beispiel,"
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
        "first_name": "Erika",
        "last_name": "Beispiel",
        "salutation": "frau",
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
    contact = yaml.safe_load(target.read_text())["contact"]
    assert contact["first_name"] == "Erika"
    assert contact["last_name"] == "Beispiel"
    assert contact["salutation"] == "frau"
    assert "name" not in contact


@pytest.mark.parametrize("keep_structured_fields", [False, True])
def test_rejects_old_combined_contact_name(tmp_path, keep_structured_fields):
    """Das alte Namensfeld wird weder allein noch neben neuen Feldern akzeptiert."""
    customer = _customer()
    if not keep_structured_fields:
        for field in ("first_name", "last_name", "salutation"):
            customer["contact"].pop(field)
    customer["contact"]["name"] = "Frau Erika Beispiel"
    path = tmp_path / "customer.yaml"
    path.write_text(yaml.safe_dump(customer), encoding="utf-8")
    before = path.read_bytes()

    with pytest.raises(ValueError, match="contact.name"):
        load_customer_files(tmp_path)

    assert path.read_bytes() == before


def test_organisation_without_personal_name_roundtrips(tmp_path):
    """Eine Organisation braucht keinen erfundenen Ansprechpartner."""
    customer = _customer()
    customer["contact"].update(first_name="", last_name="", salutation="organisation")
    path = tmp_path / "customer.yaml"
    path.write_text(yaml.safe_dump(customer), encoding="utf-8")

    loaded = load_customer_files(tmp_path)[0]
    assert loaded["name"] == ""
    assert loaded["mail_salutation"] == "Sehr geehrte Damen und Herren,"
    save_customer_file(loaded, path)

    assert load_customer_files(tmp_path)[0]["salutation"] == "organisation"
