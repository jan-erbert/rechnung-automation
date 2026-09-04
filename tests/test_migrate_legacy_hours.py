import json
from decimal import Decimal

import pytest
import yaml

from hours_files import load_hours_month
from tools import migrate_legacy_hours


def _schreibe_kunde(customers_dir):
    """Schreibt einen minimalen Stundenkunden fuer Migrationstests."""
    customers_dir.mkdir()
    customer = {
        "id": "musterfirma",
        "active": True,
        "contact": {
            "name": "Erika Beispiel",
            "company": "Musterfirma",
            "email": "erika@example.com",
            "street": "Musterweg 1",
            "postal_code": "01234",
            "city": "Musterstadt",
        },
        "billing": {"cycle_months": 1, "due_days": 14},
        "main_service": {
            "description": "Beratung",
            "unit": "hour",
            "unit_price": "75.00",
        },
    }
    (customers_dir / "musterfirma.yaml").write_text(
        yaml.safe_dump(customer, sort_keys=False),
        encoding="utf-8",
    )


def _setze_argumente(monkeypatch, hours_dir, customers_dir, *aktionen):
    """Setzt vollstaendige Argumente fuer die Stundenmigration."""
    monkeypatch.setattr(
        "sys.argv",
        [
            "migrate_legacy_hours.py",
            *aktionen,
            "--hours-dir",
            str(hours_dir),
            "--customers-dir",
            str(customers_dir),
        ],
    )


def _write_legacy_file(hours_dir, company="Musterfirma"):
    """Schreibt eine alte monatliche Stunden-JSON."""
    hours_dir.mkdir()
    altdatei = hours_dir / "stunden_2026_08.json"
    altdatei.write_text(
        json.dumps([{"firma": company, "stunden": 8.5}]),
        encoding="utf-8",
    )
    return altdatei


def test_hours_migration_writes_verified_yaml_and_keeps_source(
    tmp_path, monkeypatch, capsys
):
    """Die Migration erzeugt geprueftes YAML und behaelt standardmaessig JSON."""
    hours_dir = tmp_path / "hours"
    customers_dir = tmp_path / "customers"
    altdatei = _write_legacy_file(hours_dir)
    _schreibe_kunde(customers_dir)
    _setze_argumente(monkeypatch, hours_dir, customers_dir, "--apply")

    assert migrate_legacy_hours.main() == 0

    assert altdatei.is_file()
    assert load_hours_month(hours_dir / "2026-08.yaml", "2026-08") == {
        "musterfirma": Decimal("8.5")
    }
    assert "Pruefung erfolgreich" in capsys.readouterr().out


def test_hours_migration_can_delete_verified_legacy_source(tmp_path, monkeypatch):
    """Der explizite Schalter loescht JSON erst nach erfolgreicher Pruefung."""
    hours_dir = tmp_path / "hours"
    customers_dir = tmp_path / "customers"
    altdatei = _write_legacy_file(hours_dir)
    _schreibe_kunde(customers_dir)
    _setze_argumente(
        monkeypatch,
        hours_dir,
        customers_dir,
        "--apply",
        "--delete-legacy",
    )

    assert migrate_legacy_hours.main() == 0
    assert not altdatei.exists()


def test_hours_migration_rejects_unknown_company(tmp_path, monkeypatch):
    """Nicht zuordenbare Firmennamen werden nicht still uebergangen."""
    hours_dir = tmp_path / "hours"
    customers_dir = tmp_path / "customers"
    altdatei = _write_legacy_file(hours_dir, company="Unbekannt")
    _schreibe_kunde(customers_dir)
    _setze_argumente(monkeypatch, hours_dir, customers_dir, "--apply")

    with pytest.raises(ValueError, match="keinem Kunden zugeordnet"):
        migrate_legacy_hours.main()

    assert altdatei.is_file()
    assert not (hours_dir / "2026-08.yaml").exists()
