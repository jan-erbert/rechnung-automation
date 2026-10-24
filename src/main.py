import argparse
import logging
from pathlib import Path

from branding import validate_branding_config
from configuration import (
    load_invoice_config,
    load_mail_environment,
    validate_mail_config,
)
from customer_files import load_customer_files
from design import validate_design_config
from file_naming import validate_file_naming_config
from invoice_history import (
    close_expired_hours_waiting_entries,
    load_all_history,
)
from invoice_templates import load_templates
from legacy_migration import migrate_legacy_layout
from logging_setup import configure_logging
from notifications import (
    load_notification_config,
    run_reference,
    send_technical_report,
)
from paths import BASE_DIR, create_paths
from run_lock import RunLock
from recipient_policy import validate_recipient_policy
from settings_loader import load_settings
from state_backup import create_state_backup, validate_backup_config
from startup_checks import check_start_requirements
from terminal_banner import show_startup_banner
from time_utils import today
from workflow import process_invoices

logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    """Liest Kommandozeilenargumente fuer den Rechnungslauf."""
    parser = argparse.ArgumentParser(description="Rechnungen erzeugen und versenden.")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--non-interactive",
        action="store_true",
        help="Fuehrt den Lauf ohne Rueckfragen aus, z. B. fuer Cronjobs.",
    )
    mode.add_argument(
        "--dry-run",
        action="store_true",
        help=(
            "Prueft faellige Rechnungen inklusive PDF-Erzeugung, ohne Verlauf, "
            "Archive, Kundendateien oder Mailversand zu veraendern."
        ),
    )
    return parser.parse_args()


def main() -> int:
    """Startet den bestehenden CLI-Einstieg mit unveraenderten Betriebsmodi."""
    args = parse_args()
    if args.dry_run:
        mode = "dry-run"
    else:
        mode = "non-interactive" if args.non_interactive else "interactive"
    return run_application(mode)


def run_application(
    mode: str = "dry-run",
    mail_config: dict | None = None,
    settings_path: Path | None = None,
    summary: dict | None = None,
    allowed_domains: list[str] | None = None,
    notifications_path: Path | None = None,
    notify_errors: bool = True,
    reference: str | None = None,
) -> int:
    """Fuehrt dieselbe Rechnungslogik fuer CLI und optionale Orchestratoren aus."""
    if mode not in {"interactive", "non-interactive", "dry-run"}:
        raise ValueError("Unbekannter Betriebsmodus.")
    supplied_mail = mail_config
    args = argparse.Namespace(
        non_interactive=mode == "non-interactive", dry_run=mode == "dry-run"
    )
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    mail_config = None
    invoice_config = None
    notification_config = {"enabled": False, "recipient": None}
    stage = "startup"
    failed = True
    reference = run_reference(reference)
    settings = {}
    base_dir = BASE_DIR
    try:
        notification_config = load_notification_config(
            notifications_path or BASE_DIR / "config" / "notifications.yaml"
        )
        stage = "configuration"
        show_startup_banner(non_interactive=args.non_interactive)
        settings = (
            load_settings() if settings_path is None else load_settings(settings_path)
        )
        paths = create_paths(settings)
        base_dir = paths.base_dir
        if args.dry_run:
            run_mode = "dry-run"
        elif args.non_interactive:
            run_mode = "cron"
        else:
            run_mode = "interactive"
        log_file = configure_logging(
            settings.get("logging", {}), paths.base_dir, run_mode=run_mode
        )
        logger.info("Starte Rechnungslauf (Modus: %s).", run_mode)
        if log_file:
            logger.info("Logdatei: %s", log_file)
        with RunLock(paths.data_dir / ".invoice-run.lock"):
            if not args.dry_run:
                migrate_legacy_layout(paths.base_dir, paths)
            customers = load_customer_files(paths.customers_dir, strict=True)
            if not customers:
                raise ValueError(
                    "Keine Kundendateien im Verzeichnis customers gefunden."
                )
            stage = "smtp"
            mail_config = (
                load_mail_environment(paths.base_dir / ".env", settings.get("mail", {}))
                if supplied_mail is None
                else validate_mail_config(supplied_mail)
            )
            if summary is not None:
                summary.update(mode=mode, customers=len(customers))
            stage = "validation"
            candidate_invoice = load_invoice_config(paths.invoice_config)
            validate_recipient_policy(customers, candidate_invoice, allowed_domains)
            invoice_config = candidate_invoice
            from pdf_service import resolve_pdf_config

            settings = {
                **settings,
                "pdf": resolve_pdf_config(settings.get("pdf", {}), invoice_config),
            }
            check_start_requirements(settings, paths, customers, mail_config)
            design_config = validate_design_config(settings.get("design", {}))
            branding_config = validate_branding_config(settings.get("branding", {}))
            logger.info("Startpruefung erfolgreich.")
            backup_config = validate_backup_config(settings.get("backup", {}))
            if not args.dry_run and backup_config["enabled"]:
                backup_path = create_state_backup(
                    paths,
                    keep_last=backup_config["keep_last"],
                )
                logger.info("Zustandsbackup erstellt: %s", backup_path)
            stage = "processing"
            errors = _run_invoices(
                args,
                settings,
                paths,
                customers,
                mail_config,
                invoice_config,
                design_config,
                branding_config,
                summary=summary,
            )
        if errors:
            logger.error("Rechnungslauf fehlgeschlagen; Laufkennung: %s.", reference)
            return 1
        logger.info("Rechnungslauf beendet.")
        failed = False
        return 0
    except (FileNotFoundError, OSError, RuntimeError, ValueError) as err:
        logger.error(
            "Rechnungslauf abgebrochen (Schritt: %s, Laufkennung: %s).",
            stage,
            reference,
        )
        logger.debug("Technische Fehlerklasse: %s", type(err).__name__)
        return 1
    except Exception as err:
        logger.error(
            "Rechnungslauf wegen eines internen Fehlers abgebrochen. "
            "Konfiguration und Log pruefen. Laufkennung: %s.",
            reference,
        )
        logger.debug("Technische Fehlerklasse: %s", type(err).__name__)
        return 1
    finally:
        if failed and args.non_interactive and notify_errors:
            send_technical_report(
                notification_config,
                mail_config,
                stage,
                reference,
                mail_loader=lambda: (
                    validate_mail_config(supplied_mail)
                    if supplied_mail is not None
                    else load_mail_environment(
                        base_dir / ".env", settings.get("mail", {})
                    )
                ),
            )


def _run_invoices(
    args: argparse.Namespace,
    settings: dict,
    paths,
    customers: list[dict],
    mail_config: dict,
    invoice_config: dict,
    design_config: dict,
    branding_config: dict,
    summary: dict | None = None,
) -> int:
    """Laedt Verlaeufe und verarbeitet alle faelligen Rechnungen."""
    current_year = today().year
    _, history_by_year = load_all_history(paths.data_dir)
    current_path = paths.data_dir / f"invoice-history-{current_year}.json"
    current_history = history_by_year.get(current_year, (current_path, []))[1]
    closed = 0
    if not args.dry_run:
        for _, (history_path, history) in history_by_year.items():
            closed += close_expired_hours_waiting_entries(
                history_path, history, today()
            )
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
    file_naming_config = validate_file_naming_config(settings.get("file_naming", {}))
    return process_invoices(
        customers=customers,
        paths=paths,
        invoice_config=invoice_config,
        mail_config=mail_config,
        pdf_config=settings.get("pdf", {}),
        design_config=design_config,
        branding_config=branding_config,
        file_naming_config=file_naming_config,
        templates=templates,
        history=current_history,
        previous_history=previous_history,
        history_path=current_path,
        interactive=not args.non_interactive and not args.dry_run,
        dry_run=args.dry_run,
        summary=summary,
    )


if __name__ == "__main__":
    raise SystemExit(main())
