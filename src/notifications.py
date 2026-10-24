"""Versendet ausschliesslich bereinigte technische Laufmeldungen."""

import logging
from pathlib import Path
from uuid import UUID, uuid4

from configuration import validate_mail_config
from email_service import build_error_report_email, send_email
from strict_yaml import load_yaml
from time_utils import now
from validation import normalize_email_list

logger = logging.getLogger(__name__)
DEFAULT_NOTIFICATIONS_PATH = (
    Path(__file__).resolve().parent.parent / "config" / "notifications.yaml"
)
STAGES = {
    "startup": ("INV-STARTUP", "Initialisierung fehlgeschlagen."),
    "configuration": ("INV-CONFIG", "Konfiguration konnte nicht geladen werden."),
    "smtp": ("INV-SMTP", "SMTP-Zugang konnte nicht bereitgestellt werden."),
    "validation": ("INV-VALIDATION", "Startpruefung fehlgeschlagen."),
    "processing": ("INV-PROCESSING", "Rechnungsverarbeitung fehlgeschlagen."),
    "windmill": ("INV-WINDMILL", "Automatisierter Flow fehlgeschlagen."),
}


def load_notification_config(path: Path = DEFAULT_NOTIFICATIONS_PATH) -> dict:
    """Laedt die private technische Zieladresse unabhaengig von Rechnungsdaten."""
    if not path.exists():
        return {"enabled": False, "recipient": None}
    try:
        config = load_yaml(path)
        if not isinstance(config, dict) or set(config) - {"enabled", "recipient"}:
            raise ValueError
        enabled = config.get("enabled", False)
        if not isinstance(enabled, bool):
            raise ValueError
        addresses = normalize_email_list(config.get("recipient"))
        if len(addresses) > 1 or (enabled and not addresses):
            raise ValueError
    except (ValueError, TypeError, OSError):
        raise ValueError(
            "Technische Benachrichtigungskonfiguration ungueltig."
        ) from None
    return {"enabled": enabled, "recipient": addresses[0] if addresses else None}


def run_reference(value: str | None = None) -> str:
    """Erlaubt nur UUID-Laufkennungen statt frei uebergebener Fehlertexte."""
    try:
        return str(UUID(value)) if value else str(uuid4())
    except (ValueError, TypeError, AttributeError):
        return str(uuid4())


def send_technical_report(
    config: dict,
    mail_config: dict | None,
    stage: str,
    reference: str,
    mail_loader=None,
) -> bool:
    """Sendet einen festen Fehlertext ohne Kundendaten, BCC oder Log-Anhang."""
    if not config.get("enabled"):
        return False
    try:
        smtp = validate_mail_config(mail_config or mail_loader())
        code, message = STAGES.get(stage, STAGES["startup"])
        error = {
            "timestamp": now().isoformat(timespec="seconds"),
            "level": "ERROR",
            "source": code,
            "message": (
                f"{message} Laufkennung: {run_reference(reference)}. "
                "Geschuetztes Laufprotokoll pruefen."
            ),
        }
        recipient = config["recipient"]
        message = build_error_report_email(smtp["user"], recipient, [error])
        send_email(
            smtp["server"],
            smtp["port"],
            smtp["user"],
            smtp["password"],
            message,
            [recipient],
            security=smtp.get("security", "starttls"),
            timeout=smtp.get("timeout", 30),
        )
        logger.info("Technischer Fehlerbericht wurde vom Mailserver angenommen.")
        return True
    except Exception:
        logger.error(
            "INV-NOTIFICATION: Technischer Fehlerbericht konnte nicht gesendet werden."
        )
        return False
