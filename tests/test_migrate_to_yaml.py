import json

import pytest
import yaml

from konfiguration import lade_konfiguration
from kundendateien import lade_kundendateien
from tools import migrate_to_yaml


def schreibe_json_quellen(tmp_path):
    """Erzeugt minimale alte JSON-Quellen fuer Migrationstests."""
    data_json = tmp_path / "daten.json"
    config_json = tmp_path / "konfiguration.json"
    kunden = [
        {
            "name": "Erika Beispiel",
            "firma": "Musterfirma",
            "email": "erika@example.com",
            "strasse": "Musterweg 1",
            "plz": "01234",
            "ort": "Musterstadt",
            "hauptleistung": {
                "beschreibung": "Hosting",
                "einheit": "monat",
                "betrag": "49.90",
            },
        }
    ]
    config = {
        "absender": {
            "name": "Max Mustermann",
            "firma": "Musterfirma",
            "straße": "Musterweg 1",
            "plz": "01234",
            "ort": "Musterstadt",
            "telefon": "+49 123",
            "email": "max@example.com",
        },
        "bank": {
            "bankname": "Musterbank",
            "kontoinhaber": "Max Mustermann",
            "iban": "DE123",
            "bic": "MUSTDE00XXX",
        },
        "finanzen": {
            "steuer_id_typ": "steuernummer",
            "steuernummer": "12/345/67890",
            "kleinunternehmer": True,
        },
    }
    data_json.write_text(json.dumps(kunden), encoding="utf-8")
    config_json.write_text(json.dumps(config), encoding="utf-8")
    return data_json, config_json


def setze_argumente(
    monkeypatch,
    data_json,
    config_json,
    customers_dir,
    invoice_yaml,
    *aktionen,
):
    """Setzt vollstaendige Kommandozeilenargumente fuer einen Testlauf."""
    monkeypatch.setattr(
        "sys.argv",
        [
            "migrate_to_yaml.py",
            *aktionen,
            "--data-json",
            str(data_json),
            "--config-json",
            str(config_json),
            "--customers-dir",
            str(customers_dir),
            "--invoice-yaml",
            str(invoice_yaml),
        ],
    )


def migriere_testdaten(tmp_path, monkeypatch):
    """Migriert Testdaten und gibt alle beteiligten Pfade zurueck."""
    data_json, config_json = schreibe_json_quellen(tmp_path)
    customers_dir = tmp_path / "customers"
    invoice_yaml = tmp_path / "invoice.yaml"
    setze_argumente(
        monkeypatch,
        data_json,
        config_json,
        customers_dir,
        invoice_yaml,
        "--apply",
    )
    assert migrate_to_yaml.main() == 0
    return data_json, config_json, customers_dir, invoice_yaml


def test_migration_writes_yaml_without_changing_json_sources(
    tmp_path, monkeypatch, capsys
):
    """Die explizite Migration schreibt, prueft und behaelt JSON-Quellen."""
    data_json, config_json = schreibe_json_quellen(tmp_path)
    customers_dir = tmp_path / "customers"
    invoice_yaml = tmp_path / "invoice.yaml"
    original_data = data_json.read_bytes()
    original_config = config_json.read_bytes()
    setze_argumente(
        monkeypatch,
        data_json,
        config_json,
        customers_dir,
        invoice_yaml,
        "--apply",
    )

    assert migrate_to_yaml.main() == 0

    assert data_json.read_bytes() == original_data
    assert config_json.read_bytes() == original_config
    assert lade_kundendateien(customers_dir)[0]["id"] == "musterfirma"
    assert lade_konfiguration(invoice_yaml)["absender"]["name"] == "Max Mustermann"
    assert "Pruefung erfolgreich" in capsys.readouterr().out


def test_verify_accepts_matching_existing_yaml(tmp_path, monkeypatch, capsys):
    """Eine bestehende unveraenderte Migration wird erfolgreich bestaetigt."""
    data_json, config_json, customers_dir, invoice_yaml = migriere_testdaten(
        tmp_path, monkeypatch
    )
    capsys.readouterr()
    setze_argumente(
        monkeypatch,
        data_json,
        config_json,
        customers_dir,
        invoice_yaml,
        "--verify",
    )

    assert migrate_to_yaml.main() == 0
    assert "Pruefung erfolgreich" in capsys.readouterr().out


def test_verify_rejects_changed_customer_yaml(tmp_path, monkeypatch):
    """Eine inhaltlich abweichende Kundendatei laesst die Pruefung scheitern."""
    data_json, config_json, customers_dir, invoice_yaml = migriere_testdaten(
        tmp_path, monkeypatch
    )
    customer_yaml = customers_dir / "musterfirma.yaml"
    customer = yaml.safe_load(customer_yaml.read_text(encoding="utf-8"))
    customer["company"] = "Veraenderte Firma"
    customer_yaml.write_text(
        yaml.safe_dump(customer, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )
    setze_argumente(
        monkeypatch,
        data_json,
        config_json,
        customers_dir,
        invoice_yaml,
        "--verify",
    )

    with pytest.raises(ValueError, match="weicht von der JSON-Quelle ab"):
        migrate_to_yaml.main()


def test_delete_legacy_removes_sources_after_verification(tmp_path, monkeypatch):
    """Der explizite Loeschschalter entfernt beide Quellen nach der Pruefung."""
    data_json, config_json, customers_dir, invoice_yaml = migriere_testdaten(
        tmp_path, monkeypatch
    )
    setze_argumente(
        monkeypatch,
        data_json,
        config_json,
        customers_dir,
        invoice_yaml,
        "--delete-legacy",
    )

    assert migrate_to_yaml.main() == 0

    assert not data_json.exists()
    assert not config_json.exists()
    assert invoice_yaml.is_file()
    assert (customers_dir / "musterfirma.yaml").is_file()


def test_delete_legacy_keeps_sources_when_verification_fails(tmp_path, monkeypatch):
    """Fehlerhafte YAML-Daten verhindern das Loeschen beider JSON-Quellen."""
    data_json, config_json, customers_dir, invoice_yaml = migriere_testdaten(
        tmp_path, monkeypatch
    )
    invoice = yaml.safe_load(invoice_yaml.read_text(encoding="utf-8"))
    invoice["sender"]["name"] = "Veraenderter Absender"
    invoice_yaml.write_text(
        yaml.safe_dump(invoice, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )
    setze_argumente(
        monkeypatch,
        data_json,
        config_json,
        customers_dir,
        invoice_yaml,
        "--delete-legacy",
    )

    with pytest.raises(ValueError, match="weicht von der JSON-Quelle ab"):
        migrate_to_yaml.main()

    assert data_json.is_file()
    assert config_json.is_file()
