import os
from pathlib import Path

import pytest
import yaml
from dotenv import dotenv_values

from install.write_config import build_configuration, write_configuration
from install.write_env import write_mail_env

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _config_values() -> dict[str, str]:
    """Erstellt vollstaendige Installer-Werte fuer Tests."""
    return {
        "SETUP_CONTACT_NAME": 'Jan "Test"',
        "SETUP_COMPANY": "Firma\\Nord",
        "SETUP_STREET": "Teststraße 1",
        "SETUP_POSTAL_CODE": "12345",
        "SETUP_CITY": "Teststadt",
        "SETUP_PHONE": "0123 456",
        "SETUP_EMAIL": "jan@example.com",
        "SETUP_WEBSITE": "https://example.com?a=1&b=2",
        "SETUP_BANK_NAME": "Testbank",
        "SETUP_ACCOUNT_HOLDER": "Jan Test",
        "SETUP_IBAN": "DE00000000000000000000",
        "SETUP_BIC": "TESTBIC",
        "SETUP_TAX_IDENTIFIER_TYPE": "tax_number",
        "SETUP_TAX_IDENTIFIER_VALUE": "12/345/67890",
        "SETUP_TAX_OFFICE": "Finanzamt Teststadt",
        "SETUP_SMALL_BUSINESS": "false",
        "SETUP_VAT_RATE": "19",
        "SETUP_BCC": "archiv@example.com",
        "SETUP_MAIL_FROM_NAME": "Testfirma Rechnungen",
    }


def test_write_config_preserves_yaml_special_characters(tmp_path):
    """Installer-Werte mit Sonderzeichen bleiben gueltiges YAML."""
    config_path = tmp_path / "invoice.yaml"

    write_configuration(config_path, _config_values())

    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    assert config["sender"]["name"] == 'Jan "Test"'
    assert config["sender"]["company"] == "Firma\\Nord"
    assert config["tax"]["vat_rate"] == "19"
    assert config["mail"]["from_name"] == "Testfirma Rechnungen"
    if os.name == "posix":
        assert config_path.stat().st_mode & 0o777 == 0o600


def test_small_business_config_omits_vat_rate():
    """Kleinunternehmer-Konfigurationen enthalten keinen Steuersatz."""
    values = _config_values()
    values["SETUP_SMALL_BUSINESS"] = "true"
    values["SETUP_VAT_RATE"] = ""

    config = build_configuration(values)

    assert "vat_rate" not in config["tax"]


def test_config_rejects_invalid_vat_rate():
    """Mehrwertsteuersaetze ausserhalb des Prozentbereichs werden abgelehnt."""
    values = _config_values()
    values["SETUP_VAT_RATE"] = "101"

    with pytest.raises(ValueError, match="zwischen 0 und 100"):
        build_configuration(values)


def test_write_env_preserves_special_characters(tmp_path):
    """SMTP-Werte mit Sonderzeichen bleiben ueber dotenv lesbar."""
    env_path = tmp_path / ".env"
    values = {
        "MAIL_SERVER": "smtp.example.com",
        "MAIL_PORT": "587",
        "MAIL_USER": "jan+rechnung@example.com",
        "MAIL_PASS": "pass wort#mit'zeichen",
    }

    write_mail_env(env_path, values)

    assert dict(dotenv_values(env_path)) == values
    if os.name == "posix":
        assert env_path.stat().st_mode & 0o777 == 0o600


@pytest.mark.parametrize(
    ("script_name", "expected_text"),
    [
        ("install.sh", "mkdir -p customers data hours"),
        ("install.ps1", 'Join-Path $ProjectRoot "hours"'),
    ],
)
def test_installer_create_hours_directory(script_name, expected_text):
    """Beide Erstinstaller legen das Verzeichnis fuer Stunden-YAMLs an."""
    content = (PROJECT_ROOT / "install" / script_name).read_text(encoding="utf-8")

    assert expected_text in content
