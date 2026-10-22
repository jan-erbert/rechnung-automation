"""Prueft den optionalen Windmill-Adapter mit erfundenen Ressourcen."""

from unittest.mock import Mock

import pytest

from integrations.windmill import configuration as adapter
from openbao_secrets import OpenBaoError


@pytest.fixture
def smtp():
    """Liefert einen generischen SMTP-Ressourcendatensatz ohne echte Zugangsdaten."""
    return {
        "server": "smtp.example.invalid",
        "port": 587,
        "security": "starttls",
        "timeout": 30,
        "secret_provider": "windmill",
        "user": "fixture-user",
        "password": "fixture-password",
    }


def test_native_resource_matches_shared_mail_contract(smtp):
    """Uebersetzt eine Windmill-Ressource ohne eine lokale Env-Datei."""
    loader = Mock(return_value=smtp)

    result = adapter.load_smtp_resource("f/invoices/smtp", loader)

    keys = ["server", "port", "security", "timeout", "user", "password"]
    assert result == {key: smtp[key] for key in keys}
    loader.assert_called_once_with("f/invoices/smtp")


def test_openbao_resource_is_resolved_only_in_process(monkeypatch, smtp):
    """Laedt die begrenzte AppRole-Konfiguration und gibt nur die Mailconfig weiter."""
    smtp.update(secret_provider="openbao", openbao_resource="f/invoices/openbao")
    smtp.pop("user")
    smtp.pop("password")
    vault = {"secret_id": "fixture-login-secret"}
    loader = Mock(side_effect=[smtp, vault])
    read = Mock(return_value={"user": "fixture-user", "password": "fixture-password"})
    monkeypatch.setattr(adapter, "read_kv2_secret", read)

    result = adapter.load_smtp_resource("f/invoices/smtp", loader)

    read.assert_called_once_with(vault)
    assert result["user"] == "fixture-user"
    assert result["password"] == "fixture-password"
    assert "secret_id" not in result
    assert "openbao_resource" not in result


def test_failed_openbao_read_never_falls_back_to_inline_credentials(monkeypatch, smtp):
    """Verhindert die stille Wiederverwendung veralteter Zugangsdaten."""
    smtp.update(secret_provider="openbao", openbao_resource="f/invoices/openbao")
    loader = Mock(side_effect=[smtp, {}])
    monkeypatch.setattr(
        adapter, "read_kv2_secret", Mock(side_effect=OpenBaoError("unavailable"))
    )

    with pytest.raises(OpenBaoError, match="unavailable"):
        adapter.load_smtp_resource("f/invoices/smtp", loader)


@pytest.mark.parametrize("port", [0, 65536, True, 1.5, "fixture-password"])
def test_rejects_invalid_port_without_revealing_value(smtp, port):
    """Prueft Portwerte ohne rohe Konfigurationsinhalte in Fehlermeldungen."""
    smtp["port"] = port

    with pytest.raises(ValueError) as caught:
        adapter.load_smtp_resource("f/invoices/smtp", Mock(return_value=smtp))

    assert "fixture-password" not in str(caught.value)


def test_rejects_unknown_secret_provider(smtp):
    """Eine falsch geschriebene Quelle darf keinen lokalen Ersatz laden."""
    smtp["secret_provider"] = "typo"

    with pytest.raises(ValueError, match="Secret-Provider"):
        adapter.load_smtp_resource("f/invoices/smtp", Mock(return_value=smtp))
