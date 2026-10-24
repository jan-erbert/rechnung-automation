"""Prueft technische Benachrichtigungen ohne Netzwerk und echte Projektdateien."""

import logging
from uuid import UUID
from unittest.mock import Mock

import pytest

import main as application
import notifications
from logging_setup import RunErrorCollector

SMTP = {
    "server": "smtp.example.invalid",
    "port": 587,
    "user": "sender@example.invalid",
    "password": "fixture-secret",
}
TARGET = {"enabled": True, "recipient": "operator@example.invalid"}


def test_absent_configuration_disables_notifications(tmp_path):
    """Ein bestehendes Projekt bekommt ohne ausdrueckliche Aktivierung keine Mail."""
    result = notifications.load_notification_config(tmp_path / "absent.yaml")
    assert result == {"enabled": False, "recipient": None}


@pytest.mark.parametrize(
    "content",
    [
        "enabled: true\nrecipient: null",
        "enabled: yesplease\nrecipient: operator@example.invalid",
        "enabled: true\nrecipient: [one@example.invalid, two@example.invalid]",
        "enabled: true\nrecipient: invalid-secret",
        "enabled: true\nrecipient: broken\n  syntax: fixture-secret",
        "enabled: false\nunknown-secret: fixture-secret",
        "- fixture-secret",
        "enabled: false\nenabled: true",
    ],
)
def test_invalid_configuration_never_echoes_private_values(tmp_path, content):
    """Falsche YAML-Werte geben weder Adressen noch YAML-Inhalte preis."""
    path = tmp_path / "notifications.yaml"
    path.write_text(content, encoding="utf-8")
    with pytest.raises(ValueError) as failure:
        notifications.load_notification_config(path)
    assert str(failure.value) == "Technische Benachrichtigungskonfiguration ungueltig."


def test_single_technical_recipient_is_loaded(tmp_path):
    """Die private Adresse wird unabhaengig von Rechnung und Kundendaten gelesen."""
    path = tmp_path / "notifications.yaml"
    path.write_text(
        "enabled: true\nrecipient: operator@example.invalid", encoding="utf-8"
    )
    assert notifications.load_notification_config(path) == TARGET


def test_report_contains_only_fixed_metadata_without_bcc_or_attachments(monkeypatch):
    """Technische Berichte enthalten keine Rohlogs, Rechnungsdaten oder Anhaenge."""
    send = Mock()
    monkeypatch.setattr(notifications, "send_email", send)
    reference = "01a163fd-e909-0151-5f4e-2708654ec904"
    assert notifications.send_technical_report(TARGET, SMTP, "processing", reference)
    args, kwargs = send.call_args
    message = args[4]
    assert args[5] == [TARGET["recipient"]]
    assert message["To"] == TARGET["recipient"]
    assert message["Bcc"] is None
    assert message["Cc"] is None
    assert all(
        part.get_content_disposition() != "attachment" for part in message.walk()
    )
    payload = message.get_payload()[0].get_payload(decode=True).decode("utf-8")
    assert "INV-PROCESSING" in payload
    assert reference in payload
    assert "fixture-secret" not in message.as_string()
    assert kwargs["security"] == "starttls"


def test_disabled_report_never_loads_credentials(monkeypatch):
    """Ohne Aktivierung werden auch keine Secrets nachgeladen."""
    loader = Mock(side_effect=AssertionError("must not read secrets"))
    assert not notifications.send_technical_report({}, None, "startup", "", loader)
    loader.assert_not_called()


def test_notification_smtp_failure_is_logged_without_secret(monkeypatch, caplog):
    """SMTP-Ausfaelle verlassen den Meldeweg kontrolliert und ohne Fehlerspiegelung."""
    monkeypatch.setattr(
        notifications, "send_email", Mock(side_effect=RuntimeError("fixture-secret"))
    )
    assert not notifications.send_technical_report(TARGET, SMTP, "smtp", "")
    assert "INV-NOTIFICATION" in caplog.text
    assert "fixture-secret" not in caplog.text


def test_untrusted_reference_and_stage_never_enter_mail(monkeypatch):
    """Freie Fehlereingaben werden durch feste Kategorien und UUID ersetzt."""
    send = Mock()
    monkeypatch.setattr(notifications, "send_email", send)
    notifications.send_technical_report(
        TARGET, SMTP, "fixture-secret", "fixture-secret"
    )
    message = send.call_args.args[4]
    payload = message.get_payload()[0].get_payload(decode=True).decode("utf-8")
    assert "fixture-secret" not in payload
    UUID(notifications.run_reference("invalid"))


@pytest.mark.parametrize("mode", ["dry-run", "interactive", "non-interactive"])
def test_early_application_failure_notifies_only_noninteractive(monkeypatch, mode):
    """Auch vor dem Settings-Laden sind nur Cron-Fehler zur Meldung freigegeben."""
    monkeypatch.setattr(
        application, "load_notification_config", Mock(return_value=TARGET)
    )
    monkeypatch.setattr(application, "show_startup_banner", lambda **kw: None)
    monkeypatch.setattr(
        application, "load_settings", Mock(side_effect=ValueError("private-config"))
    )
    report = Mock(return_value=True)
    monkeypatch.setattr(application, "send_technical_report", report)
    before = list(logging.getLogger().handlers)
    assert application.run_application(mode, mail_config=SMTP) == 1
    assert report.call_count == (1 if mode == "non-interactive" else 0)
    if report.called:
        assert report.call_args.args[0] == TARGET
        assert report.call_args.args[2] == "configuration"
        assert report.call_args.kwargs["mail_loader"]()["password"] == SMTP["password"]
    assert not any(
        isinstance(handler, RunErrorCollector) and handler not in before
        for handler in logging.getLogger().handlers
    )


def test_notification_delivery_failure_cannot_turn_failed_run_successful(monkeypatch):
    """Ein fehlerhafter SMTP-Bericht maskiert den urspruenglichen Fehler nicht."""
    monkeypatch.setattr(
        application, "load_notification_config", Mock(return_value=TARGET)
    )
    monkeypatch.setattr(application, "show_startup_banner", lambda **kw: None)
    monkeypatch.setattr(
        application, "load_settings", Mock(side_effect=ValueError("private-config"))
    )
    monkeypatch.setattr(application, "send_technical_report", Mock(return_value=False))
    assert application.run_application("non-interactive", mail_config=SMTP) == 1


def test_flow_owned_reporting_disables_duplicate_application_report(monkeypatch):
    """Ein Flow-Fehlerhandler ersetzt genau diesen einen App-Meldeweg."""
    monkeypatch.setattr(
        application, "load_notification_config", Mock(return_value=TARGET)
    )
    monkeypatch.setattr(application, "show_startup_banner", lambda **kw: None)
    monkeypatch.setattr(application, "load_settings", Mock(side_effect=ValueError()))
    report = Mock()
    monkeypatch.setattr(application, "send_technical_report", report)
    assert application.run_application("non-interactive", notify_errors=False) == 1
    report.assert_not_called()


def test_malformed_notification_file_stops_without_bcc_fallback(monkeypatch, tmp_path):
    """Eine ungueltige Wartungsadresse wird nicht durch Rechnungs-BCC ersetzt."""
    path = tmp_path / "notifications.yaml"
    path.write_text("enabled: true\nrecipient: [broken", encoding="utf-8")
    invoice = Mock(
        side_effect=AssertionError("invoice configuration must not be loaded")
    )
    monkeypatch.setattr(application, "load_invoice_config", invoice)
    send = Mock()
    monkeypatch.setattr(notifications, "send_email", send)
    assert (
        application.run_application(
            "non-interactive", mail_config=SMTP, notifications_path=path
        )
        == 1
    )
    invoice.assert_not_called()
    send.assert_not_called()


def test_early_failure_never_logs_raw_exception(monkeypatch, caplog):
    """Ein Parserfehler mit privatem Inhalt wird nur als sichere Kategorie geloggt."""
    monkeypatch.setattr(application, "load_notification_config", Mock(return_value={}))
    monkeypatch.setattr(application, "show_startup_banner", lambda **kw: None)
    monkeypatch.setattr(
        application, "load_settings", Mock(side_effect=ValueError("private-secret"))
    )
    with caplog.at_level(logging.DEBUG):
        assert application.run_application("non-interactive", mail_config=SMTP) == 1
    assert "private-secret" not in caplog.text
    assert "Laufkennung" in caplog.text
