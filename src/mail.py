import smtplib
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


def baue_rechnungsmail(
    mail_user: str,
    empfaenger: str,
    betreff: str,
    mail_html: str,
    pdf_bytes: bytes,
    anhang_name: str,
    mail_bcc: str | None = None,
) -> MIMEMultipart:
    """Baut die MIME-Mail mit HTML-Inhalt und PDF-Anhang."""
    msg = MIMEMultipart()
    msg["From"] = mail_user
    msg["To"] = empfaenger
    msg["Subject"] = betreff
    if mail_bcc:
        msg["Bcc"] = mail_bcc

    msg.attach(MIMEText(mail_html, "html"))

    pdf_part = MIMEApplication(pdf_bytes, _subtype="pdf")
    pdf_part.add_header("Content-Disposition", "attachment", filename=anhang_name)
    msg.attach(pdf_part)

    return msg


def sende_mail(
    mail_server: str,
    mail_port: int,
    mail_user: str,
    mail_pass: str,
    msg: MIMEMultipart,
    empfaenger_liste: list[str],
) -> None:
    """Sendet eine vorbereitete MIME-Mail per SMTP."""
    with smtplib.SMTP(mail_server, mail_port) as server:
        server.starttls()
        server.login(mail_user, mail_pass)
        server.send_message(msg, from_addr=mail_user, to_addrs=empfaenger_liste)
