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

logger = logging.getLogger(__name__)


class MailversandFehler(RuntimeError):
    """Beschreibt einen SMTP-Fehler mit sicherer Retry-Einordnung."""

    def __init__(self, message: str, retry_sicher: bool, hinweis: str = "") -> None:
        """Initialisiert einen klassifizierten Mailversandfehler."""
        super().__init__(message)
        self.retry_sicher = retry_sicher
        self.hinweis = hinweis


def baue_rechnungsmail(
    mail_user: str,
    empfaenger: str,
    betreff: str,
    mail_html: str,
    pdf_bytes: bytes,
    anhang_name: str,
    mail_bcc: str | None = None,
    mail_cc: list[str] | None = None,
    mail_logo: LogoAsset | None = None,
    from_name: str | None = None,
) -> MIMEMultipart:
    """Baut die MIME-Mail mit HTML-Inhalt und PDF-Anhang."""
    msg = MIMEMultipart()
    msg["From"] = _formatiere_absender(mail_user, from_name)
    msg["To"] = empfaenger
    msg["Subject"] = betreff
    if mail_cc:
        msg["Cc"] = ", ".join(mail_cc)
    if mail_bcc:
        msg["Bcc"] = mail_bcc

    if mail_logo:
        related = MIMEMultipart("related")
        related.attach(MIMEText(mail_html, "html"))
        logo_part = MIMEImage(mail_logo.data, _subtype=mail_logo.subtype)
        logo_part.add_header("Content-ID", "<rechnung-logo>")
        dateiendung = "jpg" if mail_logo.subtype == "jpeg" else mail_logo.subtype
        logo_part.add_header(
            "Content-Disposition",
            "inline",
            filename=f"logo.{dateiendung}",
        )
        related.attach(logo_part)
        msg.attach(related)
    else:
        msg.attach(MIMEText(mail_html, "html"))

    pdf_part = MIMEApplication(pdf_bytes, _subtype="pdf")
    pdf_part.add_header("Content-Disposition", "attachment", filename=anhang_name)
    msg.attach(pdf_part)

    return msg


def baue_fehlerbericht_mail(
    mail_user: str,
    empfaenger: str,
    fehler: list[dict[str, str]],
    zeitpunkt: datetime | None = None,
    from_name: str | None = None,
) -> MIMEMultipart:
    """Baut eine HTML-Mail mit schweren Fehlern eines Cronlaufs."""
    zeitpunkt = zeitpunkt or datetime.now()
    eintraege = "".join(
        (
            "<li style='margin-bottom: 14px;'>"
            f"<strong>{escape(eintrag['level'])}</strong> "
            f"({escape(eintrag['zeit'])}, {escape(eintrag['quelle'])})<br>"
            f"{escape(eintrag['meldung'])}"
            "</li>"
        )
        for eintrag in fehler
    )
    html = _baue_statusmail_html(
        titel="Rechnungslauf mit Fehlern beendet",
        einleitung=(
            f"Der automatische Rechnungslauf vom "
            f"{zeitpunkt:%d.%m.%Y um %H:%M Uhr} hat "
            f"{len(fehler)} schwere Fehler protokolliert."
        ),
        inhalt=f"<ul style='padding-left: 20px;'>{eintraege}</ul>",
        hinweis="Bitte pruefe die zugehoerige Logdatei und die betroffenen Eintraege.",
    )
    return baue_html_mail(
        mail_user,
        empfaenger,
        f"Fehlerbericht Rechnungslauf - {zeitpunkt:%d.%m.%Y %H:%M}",
        html,
        from_name=from_name,
    )


def baue_mailtest_mail(
    mail_user: str,
    empfaenger: str,
    zeitpunkt: datetime | None = None,
    from_name: str | None = None,
) -> MIMEMultipart:
    """Baut eine kurze Bestaetigungsmail fuer den SMTP-Test."""
    zeitpunkt = zeitpunkt or datetime.now()
    html = _baue_statusmail_html(
        titel="Mailversand erfolgreich",
        einleitung="Die Testmail der Rechnung-Automation wurde erfolgreich zugestellt.",
        inhalt=(
            "<p style='margin: 0;'>"
            f"Testzeitpunkt: <strong>{zeitpunkt:%d.%m.%Y um %H:%M Uhr}</strong>"
            "</p>"
        ),
        hinweis="Es wurden keine Rechnungen erzeugt oder Kundendaten verarbeitet.",
    )
    return baue_html_mail(
        mail_user,
        empfaenger,
        "Mailtest Rechnung-Automation erfolgreich",
        html,
        from_name=from_name,
    )


def baue_html_mail(
    mail_user: str,
    empfaenger: str,
    betreff: str,
    html: str,
    from_name: str | None = None,
) -> MIMEMultipart:
    """Baut eine einfache HTML-Mail ohne Anhang."""
    msg = MIMEMultipart()
    msg["From"] = _formatiere_absender(mail_user, from_name)
    msg["To"] = empfaenger
    msg["Subject"] = betreff
    msg.attach(MIMEText(html, "html"))
    return msg


def _formatiere_absender(mail_user: str, from_name: str | None) -> str:
    """Formatiert die SMTP-Adresse mit einem optionalen sichtbaren Namen."""
    return formataddr((from_name, mail_user)) if from_name else mail_user


def _baue_statusmail_html(
    titel: str,
    einleitung: str,
    inhalt: str,
    hinweis: str,
) -> str:
    """Baut das gemeinsame schlichte Layout fuer Statusmails."""
    return f"""
<!doctype html>
<html lang="de">
  <body style="margin: 0; background: #f4f6f8; font-family: Arial, sans-serif; color: #20252b;">
    <div style="max-width: 680px; margin: 24px auto; background: #ffffff; border: 1px solid #dfe3e8;">
      <div style="padding: 20px 24px; background: #243447; color: #ffffff;">
        <h1 style="margin: 0; font-size: 20px;">{escape(titel)}</h1>
      </div>
      <div style="padding: 24px;">
        <p style="margin-top: 0;">{escape(einleitung)}</p>
        {inhalt}
        <p style="margin: 24px 0 0; color: #59636e; font-size: 13px;">{escape(hinweis)}</p>
      </div>
    </div>
  </body>
</html>
""".strip()


def sende_mail(
    mail_server: str,
    mail_port: int,
    mail_user: str,
    mail_pass: str,
    msg: MIMEMultipart,
    empfaenger_liste: list[str],
) -> None:
    """Sendet eine vorbereitete MIME-Mail per SMTP."""
    server = None
    try:
        server = smtplib.SMTP(mail_server, mail_port)
        server.starttls()
        server.login(mail_user, mail_pass)
    except smtplib.SMTPAuthenticationError as err:
        _schliesse_smtp_verbindung(server)
        raise MailversandFehler(
            "SMTP-Anmeldung fehlgeschlagen.",
            retry_sicher=True,
            hinweis=(
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
        _schliesse_smtp_verbindung(server)
        raise MailversandFehler(
            "SMTP-Verbindung oder TLS-Start ist fehlgeschlagen.",
            retry_sicher=True,
            hinweis=(
                "Bitte MAIL_SERVER, MAIL_PORT und die geforderte "
                "Verschluesselungsart des Mailanbieters pruefen."
            ),
        ) from err
    except Exception as err:
        _schliesse_smtp_verbindung(server)
        raise MailversandFehler(
            "SMTP-Verbindung oder Anmeldung ist fehlgeschlagen.",
            retry_sicher=True,
            hinweis="Bitte die SMTP-Zugangsdaten und Servereinstellungen pruefen.",
        ) from err

    try:
        abgelehnte_empfaenger = server.send_message(
            msg,
            from_addr=mail_user,
            to_addrs=empfaenger_liste,
        )
        if abgelehnte_empfaenger:
            raise MailversandFehler(
                "SMTP hat nur einen Teil der Empfaenger akzeptiert.",
                retry_sicher=False,
            )
    except MailversandFehler:
        raise
    except (
        smtplib.SMTPRecipientsRefused,
        smtplib.SMTPSenderRefused,
        smtplib.SMTPDataError,
    ) as err:
        raise MailversandFehler(
            "Der SMTP-Server hat den Versand eindeutig abgelehnt.",
            retry_sicher=True,
        ) from err
    except Exception as err:
        raise MailversandFehler(
            "Die SMTP-Verbindung wurde waehrend des Versands unterbrochen.",
            retry_sicher=False,
        ) from err
    finally:
        try:
            server.quit()
        except Exception as err:
            logger.warning(
                "SMTP-Verbindung konnte nicht sauber beendet werden: %s", err
            )


def _schliesse_smtp_verbindung(server) -> None:
    """Schliesst eine teilweise geoeffnete SMTP-Verbindung bestmoeglich."""
    if server is None:
        return
    try:
        server.close()
    except Exception:
        pass
