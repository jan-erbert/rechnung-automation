import logging
import smtplib
from datetime import datetime
from email.mime.image import MIMEImage
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr
from html import escape

from branding import LogoAsset
from time_utils import now

logger = logging.getLogger(__name__)


class MailDeliveryError(RuntimeError):
    """Beschreibt einen SMTP-Fehler mit sicherer Retry-Einordnung."""

    def __init__(self, message: str, retry_safe: bool, hint: str = "") -> None:
        """Initialisiert einen klassifizierten Mailversandfehler."""
        super().__init__(message)
        self.retry_safe = retry_safe
        self.hint = hint


def build_invoice_email(
    mail_user: str,
    recipient: str,
    subject: str,
    mail_html: str,
    pdf_bytes: bytes,
    attachment_name: str,
    mail_bcc: list[str] | None = None,
    mail_cc: list[str] | None = None,
    mail_logo: LogoAsset | None = None,
    from_name: str | None = None,
) -> MIMEMultipart:
    """Baut die MIME-Mail mit HTML-Inhalt und PDF-Anhang."""
    msg = MIMEMultipart()
    msg["From"] = _format_sender(mail_user, from_name)
    msg["To"] = recipient
    msg["Subject"] = subject
    if mail_cc:
        msg["Cc"] = ", ".join(mail_cc)
    if mail_bcc:
        msg["Bcc"] = ", ".join(mail_bcc)

    if mail_logo:
        related = MIMEMultipart("related")
        related.attach(MIMEText(mail_html, "html"))
        logo_part = MIMEImage(mail_logo.data, _subtype=mail_logo.subtype)
        logo_part.add_header("Content-ID", "<invoice-logo>")
        extension = "jpg" if mail_logo.subtype == "jpeg" else mail_logo.subtype
        logo_part.add_header(
            "Content-Disposition",
            "inline",
            filename=f"logo.{extension}",
        )
        related.attach(logo_part)
        msg.attach(related)
    else:
        msg.attach(MIMEText(mail_html, "html"))

    pdf_part = MIMEApplication(pdf_bytes, _subtype="pdf")
    pdf_part.add_header("Content-Disposition", "attachment", filename=attachment_name)
    msg.attach(pdf_part)

    return msg


def build_error_report_email(
    mail_user: str,
    recipient: str,
    errors: list[dict[str, str]],
    timestamp: datetime | None = None,
    from_name: str | None = None,
) -> MIMEMultipart:
    """Baut eine HTML-Mail mit schweren Fehlern eines Cronlaufs."""
    timestamp = timestamp or now()
    entries = "".join(
        (
            "<li style='margin-bottom: 14px;'>"
            f"<strong>{escape(entry['level'])}</strong> "
            f"({escape(entry['timestamp'])}, {escape(entry['source'])})<br>"
            f"{escape(entry['message'])}"
            "</li>"
        )
        for entry in errors
    )
    html = _build_status_email_html(
        title="Rechnungslauf mit Fehlern beendet",
        introduction=(
            f"Der automatische Rechnungslauf vom "
            f"{timestamp:%d.%m.%Y um %H:%M Uhr} hat "
            f"{len(errors)} schwere Fehler protokolliert."
        ),
        content=f"<ul style='padding-left: 20px;'>{entries}</ul>",
        hint="Bitte pruefe die zugehoerige Logdatei und die betroffenen Eintraege.",
    )
    return build_html_email(
        mail_user,
        recipient,
        f"Fehlerbericht Rechnungslauf - {timestamp:%d.%m.%Y %H:%M}",
        html,
        from_name=from_name,
    )


def build_mail_test_email(
    mail_user: str,
    recipient: str,
    timestamp: datetime | None = None,
    from_name: str | None = None,
) -> MIMEMultipart:
    """Baut eine kurze Bestaetigungsmail fuer den SMTP-Test."""
    timestamp = timestamp or now()
    html = _build_status_email_html(
        title="Mailversand erfolgreich",
        introduction="Die Testmail der Rechnung-Automation wurde erfolgreich zugestellt.",
        content=(
            "<p style='margin: 0;'>"
            f"Testzeitpunkt: <strong>{timestamp:%d.%m.%Y um %H:%M Uhr}</strong>"
            "</p>"
        ),
        hint="Es wurden keine Rechnungen erzeugt oder Kundendaten verarbeitet.",
    )
    return build_html_email(
        mail_user,
        recipient,
        "Mailtest Rechnung-Automation erfolgreich",
        html,
        from_name=from_name,
    )


def build_html_email(
    mail_user: str,
    recipient: str,
    subject: str,
    html: str,
    from_name: str | None = None,
) -> MIMEMultipart:
    """Baut eine einfache HTML-Mail ohne Anhang."""
    msg = MIMEMultipart()
    msg["From"] = _format_sender(mail_user, from_name)
    msg["To"] = recipient
    msg["Subject"] = subject
    msg.attach(MIMEText(html, "html"))
    return msg


def _format_sender(mail_user: str, from_name: str | None) -> str:
    """Formatiert die SMTP-Adresse mit einem optionalen sichtbaren Namen."""
    return formataddr((from_name, mail_user)) if from_name else mail_user


def _build_status_email_html(
    title: str,
    introduction: str,
    content: str,
    hint: str,
) -> str:
    """Baut das gemeinsame schlichte Layout fuer Statusmails."""
    return f"""
<!doctype html>
<html lang="de">
  <body style="margin: 0; background: #f4f6f8; font-family: Arial, sans-serif; color: #20252b;">
    <div style="max-width: 680px; margin: 24px auto; background: #ffffff; border: 1px solid #dfe3e8;">
      <div style="padding: 20px 24px; background: #243447; color: #ffffff;">
        <h1 style="margin: 0; font-size: 20px;">{escape(title)}</h1>
      </div>
      <div style="padding: 24px;">
        <p style="margin-top: 0;">{escape(introduction)}</p>
        {content}
        <p style="margin: 24px 0 0; color: #59636e; font-size: 13px;">{escape(hint)}</p>
      </div>
    </div>
  </body>
</html>
""".strip()


def send_email(
    mail_server: str,
    mail_port: int,
    mail_user: str,
    mail_pass: str,
    msg: MIMEMultipart,
    recipients: list[str],
    security: str = "starttls",
    timeout: int = 30,
) -> None:
    """Sendet eine vorbereitete MIME-Mail per SMTP."""
    server = None
    try:
        if security == "ssl":
            server = smtplib.SMTP_SSL(mail_server, mail_port, timeout=timeout)
        elif security == "starttls":
            server = smtplib.SMTP(mail_server, mail_port, timeout=timeout)
            server.starttls()
        else:
            raise ValueError("SMTP-Sicherheitsmodus muss starttls oder ssl sein.")
        server.login(mail_user, mail_pass)
    except smtplib.SMTPAuthenticationError as err:
        _close_smtp_connection(server)
        raise MailDeliveryError(
            "SMTP-Anmeldung fehlgeschlagen.",
            retry_safe=True,
            hint=(
                "Bitte MAIL_USER und MAIL_PASS in .env sowie die SMTP-Freigabe "
                "beim Mailanbieter pruefen."
            ),
        ) from err
    except (
        OSError,
        smtplib.SMTPConnectError,
        smtplib.SMTPHeloError,
        smtplib.SMTPNotSupportedError,
        smtplib.SMTPServerDisconnected,
    ) as err:
        _close_smtp_connection(server)
        raise MailDeliveryError(
            "SMTP-Verbindung oder TLS-Start ist fehlgeschlagen.",
            retry_safe=True,
            hint=(
                "Bitte MAIL_SERVER, MAIL_PORT und die geforderte "
                "Verschluesselungsart des Mailanbieters pruefen."
            ),
        ) from err
    except Exception as err:
        _close_smtp_connection(server)
        raise MailDeliveryError(
            "SMTP-Verbindung oder Anmeldung ist fehlgeschlagen.",
            retry_safe=True,
            hint="Bitte die SMTP-Zugangsdaten und Servereinstellungen pruefen.",
        ) from err

    try:
        refused_recipients = server.send_message(
            msg,
            from_addr=mail_user,
            to_addrs=recipients,
        )
        if refused_recipients:
            raise MailDeliveryError(
                "SMTP hat nur einen Teil der Empfaenger akzeptiert.",
                retry_safe=False,
            )
    except MailDeliveryError:
        raise
    except (
        smtplib.SMTPRecipientsRefused,
        smtplib.SMTPSenderRefused,
        smtplib.SMTPDataError,
    ) as err:
        raise MailDeliveryError(
            "Der SMTP-Server hat den Versand eindeutig abgelehnt.",
            retry_safe=True,
        ) from err
    except Exception as err:
        raise MailDeliveryError(
            "Die SMTP-Verbindung wurde waehrend des Versands unterbrochen.",
            retry_safe=False,
        ) from err
    finally:
        try:
            server.quit()
        except Exception as err:
            logger.warning(
                "SMTP-Verbindung konnte nicht sauber beendet werden: %s", err
            )


def _close_smtp_connection(server) -> None:
    """Schliesst eine teilweise geoeffnete SMTP-Verbindung bestmoeglich."""
    if server is None:
        return
    try:
        server.close()
    except Exception:
        pass
