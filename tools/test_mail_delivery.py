import logging
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from configuration import load_invoice_config, load_mail_environment  # noqa: E402
from logging_setup import configure_logging  # noqa: E402
from email_service import (  # noqa: E402
    MailDeliveryError,
    build_mail_test_email,
    send_email,
)
from paths import create_paths  # noqa: E402
from settings_loader import load_settings  # noqa: E402

logger = logging.getLogger(__name__)


def main() -> int:
    """Sendet eine reine SMTP-Testmail an den konfigurierten BCC-Empfaenger."""
    try:
        settings = load_settings()
        paths = create_paths(settings)
        configure_logging(settings.get("logging", {}), paths.base_dir)
        invoice_config = load_invoice_config(paths.invoice_config)
        mail_config = load_mail_environment(
            paths.base_dir / ".env", settings.get("mail", {})
        )
        mail_bcc = invoice_config.get("mail", {}).get("bcc")
        if not mail_bcc:
            raise ValueError(
                "Mailtest nicht moeglich: In config/invoice.yaml fehlt mail.bcc."
            )
        msg = build_mail_test_email(
            mail_config["user"],
            mail_bcc[0],
            from_name=invoice_config.get("mail", {}).get("from_name"),
        )
        send_email(
            mail_config["server"],
            mail_config["port"],
            mail_config["user"],
            mail_config["password"],
            msg,
            mail_bcc,
            security=mail_config.get("security", "starttls"),
            timeout=mail_config.get("timeout", 30),
        )
    except MailDeliveryError as err:
        logger.error("SMTP-Test fehlgeschlagen: %s", err)
        if err.hint:
            logger.error("Hinweis: %s", err.hint)
        return 1
    except (FileNotFoundError, OSError, ValueError) as err:
        logger.error("SMTP-Test abgebrochen: %s", err)
        return 1

    logger.info("SMTP-Testmail wurde erfolgreich an den BCC-Empfaenger gesendet.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
