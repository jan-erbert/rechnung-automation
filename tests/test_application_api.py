"""Prueft gemeinsame Einstiege ohne PDF, Mail oder produktive Dateien."""

import contextlib
from types import SimpleNamespace

import pytest

import main as application
from configuration import load_mail_environment, validate_mail_config


def test_environment_only_smtp_without_env_file(monkeypatch, tmp_path):
    """Vollstaendige Prozesskonfiguration benoetigt keine .env-Datei."""
    environment = {
        "MAIL_SERVER": "smtp.example.invalid",
        "MAIL_PORT": "587",
        "MAIL_USER": "fixture",
        "MAIL_PASS": "fixture-password",
    }
    for key, value in environment.items():
        monkeypatch.setenv(key, value)
    result = load_mail_environment(tmp_path / ".env")
    assert result["port"] == 587
    assert result["user"] == "fixture"
    assert not (tmp_path / ".env").exists()


@pytest.mark.parametrize(
    "arguments,mode",
    [
        ([], "interactive"),
        (["--non-interactive"], "non-interactive"),
        (["--dry-run"], "dry-run"),
    ],
)
def test_cli_uses_shared_entry(monkeypatch, arguments, mode):
    """Alle bisherigen CLI-Modi rufen denselben Anwendungseinstieg auf."""
    calls = []
    monkeypatch.setattr("sys.argv", ["main.py", *arguments])
    monkeypatch.setattr(
        application, "run_application", lambda value: calls.append(value) or 0
    )
    assert application.main() == 0
    assert calls == [mode]


def test_injected_smtp_never_loads_dotenv_or_calls_real_workflow(monkeypatch, tmp_path):
    """Der API-Einstieg uebergibt SMTP direkt an die vorhandene Verarbeitung."""
    smtp = {
        "server": "smtp.example.invalid",
        "port": 587,
        "user": "fixture",
        "password": "fixture-password",
    }
    paths = SimpleNamespace(
        base_dir=tmp_path,
        data_dir=tmp_path,
        customers_dir=tmp_path,
        invoice_config=tmp_path / "invoice.yaml",
    )
    monkeypatch.setattr(application, "show_startup_banner", lambda **kw: None)
    monkeypatch.setattr(application, "load_settings", lambda: {})
    monkeypatch.setattr(application, "create_paths", lambda settings: paths)
    monkeypatch.setattr(application, "configure_logging", lambda *a, **kw: None)
    monkeypatch.setattr(application, "RunLock", lambda path: contextlib.nullcontext())
    monkeypatch.setattr(
        application, "load_customer_files", lambda *a, **kw: [{"id": "fixture"}]
    )
    monkeypatch.setattr(application, "load_invoice_config", lambda path: {})
    monkeypatch.setattr(application, "check_start_requirements", lambda *a: None)
    monkeypatch.setattr(application, "validate_design_config", lambda config: {})
    monkeypatch.setattr(application, "validate_branding_config", lambda config: {})
    monkeypatch.setattr(
        application, "validate_backup_config", lambda config: {"enabled": False}
    )

    def forbidden_dotenv(*args, **kwargs):
        """Verhindert jeden Rueckgriff auf lokale Zugangsdaten."""
        raise AssertionError("dotenv must not be read")

    def fake_workflow(*args, **kwargs):
        """Prueft nur die Eingaben ohne Projektverarbeitung."""
        assert args[4]["password"] == "fixture-password"
        kwargs["summary"]["prepared"] = 2
        return 0

    monkeypatch.setattr(application, "load_mail_environment", forbidden_dotenv)
    monkeypatch.setattr(application, "_run_invoices", fake_workflow)
    summary = {}
    assert (
        application.run_application("dry-run", mail_config=smtp, summary=summary) == 0
    )
    assert summary == {"mode": "dry-run", "customers": 1, "prepared": 2}
    assert list(tmp_path.iterdir()) == []


def test_invalid_injected_smtp_does_not_echo_secret():
    """Fehlertexte enthalten keine uebergebenen Zugangswerte."""
    with pytest.raises(ValueError) as error:
        validate_mail_config(
            {
                "server": "fixture",
                "user": "fixture",
                "password": "private-fixture",
                "port": -1,
            }
        )
    assert "private-fixture" not in str(error.value)
