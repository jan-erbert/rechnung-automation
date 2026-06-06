import smtplib
from datetime import datetime
from email import message_from_string

import pytest

from mail import (
    MailversandFehler,
    baue_fehlerbericht_mail,
    baue_mailtest_mail,
    sende_mail,
)


class FakeSmtp:
    """Simuliert die fuer den Mailversand benoetigten SMTP-Methoden."""

    def __init__(self, send_error=None, refused=None):
        """Initialisiert einen optionalen Versandfehler."""
        self.send_error = send_error
        self.refused = refused or {}

    def starttls(self):
        """Simuliert den TLS-Start."""

    def login(self, user, password):
        """Simuliert die SMTP-Anmeldung."""

    def send_message(self, msg, from_addr, to_addrs):
        """Simuliert die Mailuebergabe."""
        if self.send_error:
            raise self.send_error
        return self.refused

    def quit(self):
        """Simuliert das saubere Verbindungsende."""


def test_explicit_smtp_rejection_is_safe_to_retry(monkeypatch):
    """Eine eindeutige SMTP-Ablehnung darf erneut versucht werden."""
    smtp = FakeSmtp(smtplib.SMTPDataError(550, b"rejected"))
    monkeypatch.setattr("mail.smtplib.SMTP", lambda server, port: smtp)

    with pytest.raises(MailversandFehler) as exc_info:
        sende_mail("smtp.example.com", 587, "sender", "secret", object(), ["to"])

    assert exc_info.value.retry_sicher is True


def test_connection_loss_during_send_is_ambiguous(monkeypatch):
    """Ein Verbindungsabbruch waehrend der Uebergabe bleibt unklar."""
    smtp = FakeSmtp(ConnectionError("connection lost"))
    monkeypatch.setattr("mail.smtplib.SMTP", lambda server, port: smtp)

    with pytest.raises(MailversandFehler) as exc_info:
        sende_mail("smtp.example.com", 587, "sender", "secret", object(), ["to"])

    assert exc_info.value.retry_sicher is False


def test_partial_delivery_is_ambiguous(monkeypatch):
    """Ein Teilversand darf nicht automatisch wiederholt werden."""
    smtp = FakeSmtp(refused={"kunde@example.com": (550, b"rejected")})
    monkeypatch.setattr("mail.smtplib.SMTP", lambda server, port: smtp)

    with pytest.raises(MailversandFehler) as exc_info:
        sende_mail(
            "smtp.example.com",
            587,
            "sender",
            "secret",
            object(),
            ["kunde@example.com", "bcc@example.com"],
        )

    assert exc_info.value.retry_sicher is False


def test_error_report_mail_contains_escaped_errors():
    """Der Cron-Bericht enthaelt schwere Fehler ohne HTML-Injektion."""
    msg = baue_fehlerbericht_mail(
        "sender@example.com",
        "bcc@example.com",
        [
            {
                "zeit": "2026-06-06 12:00:00",
                "level": "ERROR",
                "quelle": "workflow",
                "meldung": "Fehler bei <Firma>",
            }
        ],
        datetime(2026, 6, 6, 12, 5),
    )

    parsed = message_from_string(msg.as_string())
    html = parsed.get_payload()[0].get_payload(decode=True).decode()
    assert parsed["To"] == "bcc@example.com"
    assert "Fehler bei &lt;Firma&gt;" in html
    assert "1 schwere Fehler" in html


def test_mail_test_confirms_without_invoice_content():
    """Die SMTP-Testmail bestaetigt nur den Mailversand."""
    msg = baue_mailtest_mail(
        "sender@example.com",
        "bcc@example.com",
        datetime(2026, 6, 6, 12, 5),
    )

    html = msg.get_payload()[0].get_payload(decode=True).decode()
    assert msg["To"] == "bcc@example.com"
    assert "Mailversand erfolgreich" in html
    assert "keine Rechnungen erzeugt" in html
