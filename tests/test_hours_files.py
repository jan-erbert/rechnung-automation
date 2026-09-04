from decimal import Decimal

import pytest

from hours_files import (
    HoursFileError,
    load_hours_month,
    save_hours_value,
    write_hours_month,
)


def test_hours_yaml_roundtrip_uses_decimal_and_restrictive_permissions(tmp_path):
    """Stundenwerte bleiben als Decimal erhalten und lokal geschuetzt."""
    file_path = tmp_path / "2026-08.yaml"

    write_hours_month(
        file_path,
        "2026-08",
        {"musterfirma": Decimal("8.50")},
    )

    assert load_hours_month(file_path, "2026-08") == {"musterfirma": Decimal("8.50")}
    assert file_path.stat().st_mode & 0o777 == 0o600
    assert "hours: 8.50" in file_path.read_text(encoding="utf-8")


def test_hours_yaml_accepts_unquoted_number(tmp_path):
    """Stunden duerfen komfortabel als unquotierte YAML-Zahl gepflegt werden."""
    file_path = tmp_path / "2026-08.yaml"
    file_path.write_text(
        "period: '2026-08'\ncustomers:\n  musterfirma:\n    hours: 8.5\n",
        encoding="utf-8",
    )

    assert load_hours_month(file_path, "2026-08") == {"musterfirma": Decimal("8.5")}


def test_hours_yaml_rejects_boolean_value(tmp_path):
    """YAML-Boolesche Werte werden nicht versehentlich als Zahl akzeptiert."""
    file_path = tmp_path / "2026-08.yaml"
    file_path.write_text(
        "period: '2026-08'\ncustomers:\n  musterfirma:\n    hours: true\n",
        encoding="utf-8",
    )

    with pytest.raises(HoursFileError, match="muss eine Zahl sein"):
        load_hours_month(file_path, "2026-08")


def test_hours_yaml_rejects_mismatching_period(tmp_path):
    """Dateiname und deklarierter Zeitraum duerfen nicht widersprechen."""
    file_path = tmp_path / "2026-08.yaml"
    file_path.write_text(
        "period: '2026-07'\ncustomers: {}\n",
        encoding="utf-8",
    )

    with pytest.raises(HoursFileError, match="period muss '2026-08' sein"):
        load_hours_month(file_path, "2026-08")


def test_hours_yaml_rejects_duplicate_customer_id(tmp_path):
    """Doppelte Kunden-IDs werden nicht still mit dem letzten Wert ersetzt."""
    file_path = tmp_path / "2026-08.yaml"
    file_path.write_text(
        "period: '2026-08'\n"
        "customers:\n"
        "  musterfirma:\n"
        "    hours: '1.00'\n"
        "  musterfirma:\n"
        "    hours: '2.00'\n",
        encoding="utf-8",
    )

    with pytest.raises(HoursFileError, match="ungueltiges YAML"):
        load_hours_month(file_path, "2026-08")


def test_manual_hour_write_preserves_other_customers(tmp_path):
    """Neue manuelle Werte ersetzen keine anderen Monatswerte."""
    file_path = tmp_path / "2026-08.yaml"
    write_hours_month(
        file_path,
        "2026-08",
        {"kunde-eins": Decimal("2.00")},
    )

    save_hours_value(
        tmp_path,
        "2026-08",
        "kunde-zwei",
        Decimal("3.50"),
    )

    assert load_hours_month(file_path, "2026-08") == {
        "kunde-eins": Decimal("2.00"),
        "kunde-zwei": Decimal("3.50"),
    }
