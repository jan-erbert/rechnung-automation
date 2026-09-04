import argparse
import logging

from branding import validate_branding_config
from configuration import load_invoice_config, load_mail_environment
from customer_files import load_customer_files
from design import validate_design_config
from email_service import build_error_report_email, send_email
from invoice_history import (
    close_expired_hours_waiting_entries,
    load_all_history,
)
from invoice_templates import load_templates
from legacy_migration import migrate_legacy_layout
from logging_setup import (
    RunErrorCollector,
    activate_run_error_collector,
    configure_logging,
)
from paths import create_paths
from run_lock import RunLock
from settings_loader import load_settings
from startup_checks import check_start_requirements
from time_utils import today
from workflow import process_invoices

logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    """Liest Kommandozeilenargumente fuer den Rechnungslauf."""
    parser = argparse.ArgumentParser(description="Rechnungen erzeugen und versenden.")
    parser.add_argument(
        "--non-interactive",
        action="store_true",
        help="Fuehrt den Lauf ohne Rueckfragen aus, z. B. fuer Cronjobs.",
    )
    return parser.parse_args()


def main() -> int:
    """Startet den Rechnungslauf mit kontrollierter Fehlerausgabe."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    mail_config = None
    invoice_config = None
    error_collector = None
    try:
        args = parse_args()
        settings = load_settings()
        paths = create_paths(settings)
        log_file = configure_logging(settings.get("logging", {}), paths.base_dir)
        error_collector = (
            activate_run_error_collector() if args.non_interactive else None
        )
        logger.info("Starte Rechnungslauf.")
        if log_file:
            logger.info("Logdatei: %s", log_file)
        with RunLock(paths.data_dir / ".invoice-run.lock"):
            migrate_legacy_layout(paths.base_dir)
            customers = load_customer_files(paths.customers_dir, strict=True)
            if not customers:
                raise ValueError(
                    "Keine Kundendateien im Verzeichnis customers gefunden."
                )
            mail_config = load_mail_environment(
                paths.base_dir / ".env", settings.get("mail", {})
            )
            invoice_config = load_invoice_config(paths.invoice_config)
            check_start_requirements(settings, paths, customers, mail_config)
            design_config = validate_design_config(settings.get("design", {}))
            branding_config = validate_branding_config(settings.get("branding", {}))
            logger.info("Startpruefung erfolgreich.")
            errors = _run_invoices(
                args,
                settings,
                paths,
                customers,
                mail_config,
                invoice_config,
                design_config,
                branding_config,
            )
        if errors:
            return 1
        logger.info("Rechnungslauf beendet.")
        return 0
    except (FileNotFoundError, OSError, RuntimeError, ValueError) as err:
        logger.error("Rechnungslauf abgebrochen: %s", err)
        return 1
    except Exception as err:
        logger.error(
            "Rechnungslauf wegen eines internen Fehlers abgebrochen. "
            "Konfiguration und Log pruefen."
        )
        logger.debug("Technische Fehlerdetails: %s", err, exc_info=True)
        return 1
    finally:
        if error_collector:
            _send_cron_error_report(error_collector, mail_config, invoice_config)


def _run_invoices(
    args: argparse.Namespace,
    settings: dict,
    paths,
    customers: list[dict],
    mail_config: dict,
    invoice_config: dict,
    design_config: dict,
    branding_config: dict,
) -> int:
    """Laedt Verlaeufe und verarbeitet alle faelligen Rechnungen."""
    current_year = today().year
    _, history_by_year = load_all_history(paths.data_dir)
    current_path = paths.data_dir / f"invoice-history-{current_year}.json"
    current_history = history_by_year.get(current_year, (current_path, []))[1]
    closed = 0
    for _, (history_path, history) in history_by_year.items():
        closed += close_expired_hours_waiting_entries(history_path, history, today())
    if closed:
        logger.warning(
            "%s abgelaufene Nullstunden-Wartezustaende wurden als no_invoice "
            "abgeschlossen.",
            closed,
        )
    previous_history = [
        entry
        for year, (_, history) in history_by_year.items()
        if year != current_year
        for entry in history
    ]
    templates = load_templates(paths.templates_dir)
    return process_invoices(
        customers=customers,
        paths=paths,
        invoice_config=invoice_config,
        mail_config=mail_config,
        pdf_config=settings.get("pdf", {}),
        design_config=design_config,
        branding_config=branding_config,
        templates=templates,
        history=current_history,
        previous_history=previous_history,
        history_path=current_path,
        interactive=not args.non_interactive,
    )


def _send_cron_error_report(
    error_collector: RunErrorCollector,
    mail_config: dict | None,
    invoice_config: dict | None,
) -> None:
    """Sendet am Ende eines Cronlaufs eine Zusammenfassung schwerer Fehler."""
    errors = list(error_collector.errors)
    if not errors:
        return
    mail_bcc = (invoice_config or {}).get("mail", {}).get("bcc")
    if not mail_config or not mail_bcc:
        logger.critical(
            "Cron-Fehlerbericht kann nicht gesendet werden: "
            "Mail-Konfiguration oder BCC-Empfaenger fehlt."
        )
        return
    try:
        message = build_error_report_email(
            mail_config["user"],
            mail_bcc[0],
            errors,
            from_name=(invoice_config or {}).get("mail", {}).get("from_name"),
        )
        send_email(
            mail_config["server"],
            mail_config["port"],
            mail_config["user"],
            mail_config["password"],
            message,
            mail_bcc,
            security=mail_config.get("security", "starttls"),
            timeout=mail_config.get("timeout", 30),
        )
        logger.info("Cron-Fehlerbericht wurde an den BCC-Empfaenger gesendet.")
    except Exception as err:
        logger.error("Cron-Fehlerbericht konnte nicht gesendet werden: %s", err)
        logger.debug("Technische Fehlerdetails: %s", err, exc_info=True)


if __name__ == "__main__":
    raise SystemExit(main())
