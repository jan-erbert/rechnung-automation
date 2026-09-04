import smtplib
from datetime import datetime
from email import message_from_string

import pytest

from branding import LogoAsset
from email_service import (
    MailDeliveryError,
    build_error_report_email,
    build_mail_test_email,
    build_invoice_email,
    send_email,
)


class FakeSmtp:
    """Simuliert die fuer den Mailversand benoetigten SMTP-Methoden."""

    def __init__(self, send_error=None, refused=None, login_error=None):
        """Initialisiert einen optionalen Versandfehler."""
        self.send_error = send_error
        self.refused = refused or {}
        self.login_error = login_error

    def starttls(self):
        """Simuliert den TLS-Start."""

    def login(self, user, password):
        """Simuliert die SMTP-Anmeldung."""
        if self.login_error:
            raise self.login_error

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
    monkeypatch.setattr(
        "email_service.smtplib.SMTP", lambda server, port, timeout: smtp
    )

    with pytest.raises(MailDeliveryError) as exc_info:
        send_email("smtp.example.com", 587, "sender", "secret", object(), ["to"])

    assert exc_info.value.retry_safe is True


def test_smtp_authentication_error_gets_clear_hint(monkeypatch):
    """Falsche SMTP-Zugangsdaten erhalten einen klaren Nutzerhinweis."""
    smtp = FakeSmtp(
        login_error=smtplib.SMTPAuthenticationError(535, b"authentication failed")
    )
    monkeypatch.setattr(
        "email_service.smtplib.SMTP", lambda server, port, timeout: smtp
    )

    with pytest.raises(MailDeliveryError) as exc_info:
        send_email("smtp.example.com", 587, "sender", "secret", object(), ["to"])

    assert str(exc_info.value) == "SMTP-Anmeldung fehlgeschlagen."
    assert exc_info.value.retry_safe is True
    assert "MAIL_USER und MAIL_PASS" in exc_info.value.hint


def test_connection_loss_during_send_is_ambiguous(monkeypatch):
    """Ein Verbindungsabbruch waehrend der Uebergabe bleibt unklar."""
    smtp = FakeSmtp(ConnectionError("connection lost"))
    monkeypatch.setattr(
        "email_service.smtplib.SMTP", lambda server, port, timeout: smtp
    )

    with pytest.raises(MailDeliveryError) as exc_info:
        send_email("smtp.example.com", 587, "sender", "secret", object(), ["to"])

    assert exc_info.value.retry_safe is False


def test_partial_delivery_is_ambiguous(monkeypatch):
    """Ein Teilversand darf nicht automatisch wiederholt werden."""
    smtp = FakeSmtp(refused={"kunde@example.com": (550, b"rejected")})
    monkeypatch.setattr(
        "email_service.smtplib.SMTP", lambda server, port, timeout: smtp
    )

    with pytest.raises(MailDeliveryError) as exc_info:
        send_email(
            "smtp.example.com",
            587,
            "sender",
            "secret",
            object(),
            ["kunde@example.com", "bcc@example.com"],
        )

    assert exc_info.value.retry_safe is False


def test_implicit_tls_uses_smtp_ssl(monkeypatch):
    """Der Sicherheitsmodus ssl nutzt eine implizit verschluesselte Verbindung."""
    smtp = FakeSmtp()
    verbindungen = []
    monkeypatch.setattr(
        "email_service.smtplib.SMTP_SSL",
        lambda server, port, timeout: verbindungen.append((server, port, timeout))
        or smtp,
    )

    send_email(
        "smtp.example.com",
        465,
        "sender",
        "secret",
        object(),
        ["to"],
        security="ssl",
        timeout=15,
    )

    assert verbindungen == [("smtp.example.com", 465, 15)]


def test_error_report_mail_contains_escaped_errors():
    """Der Cron-Bericht enthaelt schwere Fehler ohne HTML-Injektion."""
    msg = build_error_report_email(
        "sender@example.com",
        "bcc@example.com",
        [
            {
                "timestamp": "2026-06-06 12:00:00",
                "level": "ERROR",
                "source": "workflow",
                "message": "Fehler bei <Firma>",
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
    msg = build_mail_test_email(
        "sender@example.com",
        "bcc@example.com",
        datetime(2026, 6, 6, 12, 5),
    )

    html = msg.get_payload()[0].get_payload(decode=True).decode()
    assert msg["To"] == "bcc@example.com"
    assert "Mailversand erfolgreich" in html
    assert "keine Rechnungen erzeugt" in html


def test_invoice_mail_embeds_configured_cid_logo():
    """Die Rechnungsmail bettet ein konfiguriertes Logo als CID-Bild ein."""
    msg = build_invoice_email(
        mail_user="sender@example.com",
        recipient="kunde@example.com",
        subject="Rechnung",
        mail_html='<img src="cid:invoice-logo">',
        pdf_bytes=b"pdf",
        attachment_name="rechnung.pdf",
        mail_logo=LogoAsset(data=b"image", subtype="png"),
    )

    related = msg.get_payload()[0]
    logo = related.get_payload()[1]
    assert related.get_content_subtype() == "related"
    assert logo["Content-ID"] == "<invoice-logo>"
    assert logo.get_content_subtype() == "png"


def test_invoice_mail_uses_optional_visible_sender_name():
    """Ein optionaler Absendername wird mit der SMTP-Adresse formatiert."""
    msg = build_invoice_email(
        mail_user="sender@example.com",
        recipient="kunde@example.com",
        subject="Rechnung",
        mail_html="Mail",
        pdf_bytes=b"pdf",
        attachment_name="rechnung.pdf",
        from_name="Musterfirma Rechnungen",
    )

    assert msg["From"] == "Musterfirma Rechnungen <sender@example.com>"


def test_invoice_mail_sets_optional_cc_header():
    """Optionale CC-Adressen werden als sichtbarer Mail-Header gesetzt."""
    msg = build_invoice_email(
        mail_user="sender@example.com",
        recipient="kunde@example.com",
        subject="Rechnung",
        mail_html="Mail",
        pdf_bytes=b"pdf",
        attachment_name="rechnung.pdf",
        mail_cc=["buchhaltung@example.com", "team@example.com"],
    )

    assert msg["To"] == "kunde@example.com"
    assert msg["Cc"] == "buchhaltung@example.com, team@example.com"


def test_invoice_mail_sets_multiple_bcc_recipients():
    """Globale BCC-Adressen werden als Liste in den Header uebernommen."""
    msg = build_invoice_email(
        mail_user="sender@example.com",
        recipient="kunde@example.com",
        subject="Rechnung",
        mail_html="Mail",
        pdf_bytes=b"pdf",
        attachment_name="rechnung.pdf",
        mail_bcc=["archiv@example.com", "backup@example.com"],
    )

    assert msg["Bcc"] == "archiv@example.com, backup@example.com"


def test_invoice_mail_from_header_uses_technical_smtp_address():
    """Der technische Mail-Absender kommt aus der SMTP-Adresse."""
    msg = build_invoice_email(
        mail_user="smtp-login@example.com",
        recipient="kunde@example.com",
        subject="Rechnung",
        mail_html="Kontakt: kontakt@example.com",
        pdf_bytes=b"pdf",
        attachment_name="rechnung.pdf",
        from_name="Musterfirma Rechnungen",
    )

    assert msg["From"] == "Musterfirma Rechnungen <smtp-login@example.com>"
