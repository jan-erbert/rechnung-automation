import logging
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from konfiguration import lade_konfiguration, lade_mail_umgebung  # noqa: E402
from logging_setup import konfiguriere_logging  # noqa: E402
from mail import MailversandFehler, baue_mailtest_mail, sende_mail  # noqa: E402
from paths import erstelle_pfade  # noqa: E402
from settings_loader import lade_settings  # noqa: E402

logger = logging.getLogger(__name__)


def main() -> None:
    """Sendet eine reine SMTP-Testmail an den konfigurierten BCC-Empfaenger."""
    settings = lade_settings()
    pfade = erstelle_pfade(settings)
    konfiguriere_logging(settings.get("logging", {}), pfade.base_dir)
    konfig = lade_konfiguration(pfade.data_dir / "konfiguration.json")
    mail_config = lade_mail_umgebung(pfade.base_dir / ".env")
    mail_bcc = konfig.get("mail", {}).get("bcc")
    if not mail_bcc:
        raise ValueError(
            "Mailtest nicht moeglich: In data/konfiguration.json fehlt mail.bcc."
        )

    msg = baue_mailtest_mail(
        mail_config["user"],
        mail_bcc,
        from_name=konfig.get("mail", {}).get("from_name"),
    )
    try:
        sende_mail(
            mail_config["server"],
            mail_config["port"],
            mail_config["user"],
            mail_config["passwort"],
            msg,
            [mail_bcc],
        )
    except MailversandFehler as err:
        logger.error("SMTP-Test fehlgeschlagen: %s", err)
        if err.hinweis:
            logger.error("Hinweis: %s", err.hinweis)
        sys.exit(1)

    logger.info("SMTP-Testmail wurde erfolgreich an den BCC-Empfaenger gesendet.")


if __name__ == "__main__":
    main()
