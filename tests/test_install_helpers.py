import json

import pytest
from dotenv import dotenv_values

from install.write_config import baue_konfiguration, schreibe_konfiguration
from install.write_env import schreibe_mail_env


def _config_values() -> dict[str, str]:
    """Erstellt vollstaendige Installer-Werte fuer Tests."""
    return {
        "SETUP_NAME": 'Jan "Test"',
        "SETUP_FIRMA": "Firma\\Nord",
        "SETUP_STRASSE": "Teststraße 1",
        "SETUP_PLZ": "12345",
        "SETUP_ORT": "Teststadt",
        "SETUP_TELEFON": "0123 456",
        "SETUP_EMAIL": "jan@example.com",
        "SETUP_WEBSITE": "https://example.com?a=1&b=2",
        "SETUP_BANKNAME": "Testbank",
        "SETUP_KONTOINHABER": "Jan Test",
        "SETUP_IBAN": "DE00000000000000000000",
        "SETUP_BIC": "TESTBIC",
        "SETUP_STEUER_ID_TYP": "steuernummer",
        "SETUP_STEUER_ID_WERT": "12/345/67890",
        "SETUP_FINANZAMT": "Finanzamt Teststadt",
        "SETUP_KLEINUNTERNEHMER": "false",
        "SETUP_MWST": "19",
        "SETUP_BCC": "archiv@example.com",
    }


def test_write_config_preserves_json_special_characters(tmp_path):
    """Installer-Werte mit Sonderzeichen bleiben gueltiges JSON."""
    config_path = tmp_path / "konfiguration.json"

    schreibe_konfiguration(config_path, _config_values())

    config = json.loads(config_path.read_text(encoding="utf-8"))
    assert config["absender"]["name"] == 'Jan "Test"'
    assert config["absender"]["firma"] == "Firma\\Nord"
    assert config["finanzen"]["mehrwertsteuer_prozent"] == 19


def test_small_business_config_omits_vat_rate():
    """Kleinunternehmer-Konfigurationen enthalten keinen Steuersatz."""
    values = _config_values()
    values["SETUP_KLEINUNTERNEHMER"] = "true"
    values["SETUP_MWST"] = ""

    config = baue_konfiguration(values)

    assert "mehrwertsteuer_prozent" not in config["finanzen"]


def test_config_rejects_invalid_vat_rate():
    """Mehrwertsteuersaetze ausserhalb des Prozentbereichs werden abgelehnt."""
    values = _config_values()
    values["SETUP_MWST"] = "101"

    with pytest.raises(ValueError, match="zwischen 0 und 100"):
        baue_konfiguration(values)


def test_write_env_preserves_special_characters(tmp_path):
    """SMTP-Werte mit Sonderzeichen bleiben ueber dotenv lesbar."""
    env_path = tmp_path / ".env"
    values = {
        "MAIL_SERVER": "smtp.example.com",
        "MAIL_PORT": "587",
        "MAIL_USER": "jan+rechnung@example.com",
        "MAIL_PASS": "pass wort#mit'zeichen",
    }

    schreibe_mail_env(env_path, values)

    assert dict(dotenv_values(env_path)) == values
    assert env_path.stat().st_mode & 0o777 == 0o600
