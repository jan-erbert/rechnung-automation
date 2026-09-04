import logging
from dataclasses import dataclass
from datetime import date

from branding import load_logo_asset
from billing_schedule import is_invoice_due
from customer_lifecycle import should_deactivate_customer, save_customer_data
from services import build_service_items
from email_service import MailDeliveryError, build_invoice_email, send_email
from path_checks import check_archive_path
from pdf_service import archive_pdf, generate_pdf_bytes
from invoices import (
    build_invoice_data,
    calculate_billing_period,
    calculate_tax_values,
)
from hours_files import HoursFileError
from invoice_templates import build_template_context
from invoice_templates import InvoiceTemplates
from paths import ProjectPaths
from validation import (
    normalize_email_list,
    validate_customer_entry,
    validate_positive_integer,
)
from invoice_history import (
    STATUS_FAILED,
    STATUS_NO_INVOICE,
    STATUS_PENDING,
    STATUS_SENT,
    STATUS_WAITING_HOURS,
    build_history_entry,
    set_delivery_status,
    save_or_replace_history_entry,
)
from time_utils import today as current_date

logger = logging.getLogger(__name__)


class InvoiceProcessingError(RuntimeError):
    """Kennzeichnet einen kontrolliert fehlgeschlagenen Rechnungsvorgang."""


@dataclass(frozen=True)
class RunContext:
    """Buendelt unveraenderliche Abhaengigkeiten eines Rechnungslaufs."""

    paths: ProjectPaths
    sender: dict
    bank: dict
    tax: dict
    mail_bcc: list[str]
    mail_from_name: str | None
    mail_config: dict
    pdf_config: dict
    design_config: dict
    branding_config: dict
    templates: InvoiceTemplates
    history: list
    previous_history: list
    history_path: object
    interactive: bool


def process_invoices(
    customers: list,
    paths,
    invoice_config: dict,
    mail_config: dict,
    pdf_config: dict,
    design_config: dict,
    branding_config: dict,
    templates,
    history: list,
    previous_history: list,
    history_path,
    interactive: bool = True,
) -> int:
    """Verarbeitet alle faelligen Kundeneintraege fuer den Rechnungslauf."""
    context = RunContext(
        paths=paths,
        sender=invoice_config["sender"],
        bank=invoice_config["bank"],
        tax=invoice_config["tax"],
        mail_bcc=invoice_config.get("mail", {}).get("bcc") or [],
        mail_from_name=invoice_config.get("mail", {}).get("from_name") or None,
        mail_config=mail_config,
        pdf_config=pdf_config,
        design_config=design_config,
        branding_config=branding_config,
        templates=templates,
        history=history,
        previous_history=previous_history,
        history_path=history_path,
        interactive=interactive,
    )

    customer_errors = 0
    for customer in customers:
        try:
            _process_customer_in_run(
                customers=customers,
                customer=customer,
                context=context,
            )
        except HoursFileError as err:
            customer_errors += 1
            logger.error(
                "%s: Stundenabrechnung abgebrochen - %s Keine Rechnung wurde "
                "erstellt oder versendet. Weitere Kunden werden verarbeitet.",
                customer.get("company", "Unbekannter Kunde"),
                err,
            )
        except Exception as err:
            customer_errors += 1
            logger.error(
                "%s: Verarbeitung wegen eines internen Fehlers abgebrochen. "
                "Bitte Konfiguration und Versandstatus pruefen, bevor der Lauf "
                "wiederholt wird. Weitere Kunden werden verarbeitet.",
                customer.get("company", "Unbekannter Kunde"),
            )
            logger.debug(
                "%s: Technische Fehlerdetails: %s",
                customer.get("company", "Unbekannter Kunde"),
                err,
                exc_info=True,
            )

    if customer_errors:
        logger.error(
            "Rechnungslauf mit %s Fehlern bei der Kundenverarbeitung abgeschlossen.",
            customer_errors,
        )
    else:
        logger.info("Rechnungslauf ohne unerwartete Kundenfehler abgeschlossen.")
    return customer_errors


def _process_customer_in_run(
    customers: list,
    customer: dict,
    context: RunContext,
) -> None:
    """Prueft und verarbeitet einen Kunden innerhalb der sicheren Laufgrenze."""
    if customer.get("active") is False:
        logger.info(
            "%s: Kunde ist deaktiviert - keine Abrechnung.", customer["company"]
        )
        return

    validate_customer_entry(customer)

    archive_directory = customer.get("archive_directory")
    if archive_directory:
        check_archive_path(archive_directory)

    if not is_invoice_due(customer, context.history, context.previous_history):
        logger.info("%s: Keine Abrechnung faellig.", customer["company"])
        return

    _process_customer_entry(
        customers=customers,
        customer=customer,
        context=context,
    )


def _process_customer_entry(
    customers: list,
    customer: dict,
    context: RunContext,
) -> None:
    """Erzeugt und versendet eine Rechnung fuer einen Kundeneintrag."""
    today = current_date()
    paths = context.paths
    archive_directory = customer.get("archive_directory")
    if archive_directory:
        check_archive_path(archive_directory, write_probe=True)

    invoice_data = build_invoice_data(customer, today)
    invoice_date = invoice_data["invoice_date"]
    month_year = invoice_data["month_year"]
    due_date = invoice_data["due_date"]
    invoice_number = invoice_data["invoice_number"]
    automatic_invoice_number = invoice_data["automatic_invoice_number"]

    cycle_months = validate_positive_integer(
        customer.get("cycle_months", 1),
        "Abrechnungszyklus",
    )
    service_data = build_service_items(
        customer,
        cycle_months,
        paths.hours_dir,
        interactive=context.interactive,
        today=today,
    )
    items = service_data["items"]
    total_amount = service_data["total_amount"]
    hours_info = service_data["hours_info"]
    billing_period = (
        hours_info["period"]
        if hours_info
        else calculate_billing_period(today, cycle_months)
    )

    if hours_info and (hours_info["hours"] == 0 or not hours_info["complete"]):
        _save_zero_hours_status(
            customer,
            today,
            invoice_number,
            invoice_date,
            cycle_months,
            context.history,
            context.history_path,
            context.interactive,
            service_period=billing_period,
            hours_info=hours_info,
            missing_months=hours_info.get("missing_months", []),
        )
        return

    tax_data = calculate_tax_values(total_amount, context.tax)
    mail_cc = normalize_email_list(customer.get("cc"), "cc")
    pdf_logo = load_logo_asset(
        paths.img_dir,
        context.branding_config["pdf_logo"],
        "PDF-Logo",
    )
    mail_logo = load_logo_asset(
        paths.img_dir,
        context.branding_config["mail_logo"],
        "Mail-Logo",
    )
    template_context = build_template_context(
        customer=customer,
        sender=context.sender,
        bank=context.bank,
        tax=context.tax,
        items=items,
        invoice_number=invoice_number,
        invoice_date=invoice_date,
        due_date=due_date,
        billing_period=billing_period,
        month_year=month_year,
        cycle_months=cycle_months,
        total_amount=total_amount,
        formatted_total=tax_data["formatted_total"],
        gross_amount=tax_data["gross_amount"],
        tax_amount=tax_data["tax_amount"],
        vat_note=tax_data["vat_note"],
        logo_base64=pdf_logo.data_uri if pdf_logo else "",
        mail_logo_cid="invoice-logo" if mail_logo else "",
        design=context.design_config,
        branding=context.branding_config,
        hours_info=hours_info,
    )

    mail_html = context.templates.email.render(template_context)
    pdf_html = context.templates.invoice.render(template_context)
    pdf_bytes = generate_pdf_bytes(pdf_html, context.pdf_config)

    attachment_name = f"Invoice_{customer['id']}_{automatic_invoice_number}.pdf"
    msg = build_invoice_email(
        mail_user=context.mail_config["user"],
        recipient=customer["email"],
        subject=f"Ihre Rechnung Nr. {invoice_number} – {customer['company']}",
        mail_html=mail_html,
        pdf_bytes=pdf_bytes,
        attachment_name=attachment_name,
        mail_bcc=context.mail_bcc,
        mail_cc=mail_cc,
        mail_logo=mail_logo,
        from_name=context.mail_from_name,
    )

    delivery_entry = build_history_entry(
        customer,
        today,
        invoice_number,
        invoice_date,
        tax_data["formatted_total"].replace(",", "."),
        cycle_months,
        status=STATUS_PENDING,
        service_period=billing_period,
        hours_info=hours_info,
    )
    _archive_pdf_if_needed(customer, attachment_name, pdf_bytes)
    _save_pending_status(delivery_entry, context.history, context.history_path)

    recipients = [customer["email"], *mail_cc, *context.mail_bcc]

    _send_email_with_status(
        customer=customer,
        mail_config=context.mail_config,
        msg=msg,
        recipients=recipients,
        mail_bcc=context.mail_bcc,
        invoice_id=delivery_entry["id"],
        history=context.history,
        history_path=context.history_path,
    )
    _deactivate_customer_if_needed(
        customers, customer, today, paths, context.interactive
    )


def _save_pending_status(
    delivery_entry: dict,
    history: list,
    history_path,
) -> None:
    """Speichert den unbestaetigten Versandstatus vor dem SMTP-Aufruf."""
    try:
        save_or_replace_history_entry(
            history_path,
            history,
            delivery_entry,
        )
    except Exception as err:
        logger.error(
            "Versand wird nicht gestartet: Status pending konnte nicht "
            "gespeichert werden: %s",
            err,
        )
        logger.debug("Technische Fehlerdetails: %s", err, exc_info=True)
        raise InvoiceProcessingError(
            "Status pending konnte nicht gespeichert werden."
        ) from err

    logger.info("Versandstatus pending gespeichert. Mailversand wird gestartet.")


def _send_email_with_status(
    customer: dict,
    mail_config: dict,
    msg,
    recipients: list[str],
    mail_bcc: list[str],
    invoice_id: str,
    history: list,
    history_path,
) -> None:
    """Sendet eine Mail und aktualisiert ihren Versandstatus."""
    try:
        send_email(
            mail_config["server"],
            mail_config["port"],
            mail_config["user"],
            mail_config["password"],
            msg,
            recipients,
            security=mail_config.get("security", "starttls"),
            timeout=mail_config.get("timeout", 30),
        )
    except MailDeliveryError as err:
        logger.error(
            "Mailversand an %s ist fehlgeschlagen: %s",
            customer["email"],
            err,
        )
        if err.hint:
            logger.warning("Hinweis zum Mailversand: %s", err.hint)
        if not err.retry_safe:
            logger.critical(
                "Der Versandstatus ist unklar. Pending bleibt bestehen und "
                "blockiert automatische Wiederholungen."
            )
            raise InvoiceProcessingError("SMTP-Status ist unklar.") from err

        try:
            set_delivery_status(
                history_path,
                history,
                invoice_id,
                STATUS_FAILED,
            )
            logger.warning(
                "Versandstatus failed gespeichert. "
                "Der Versand wird beim naechsten Lauf erneut versucht."
            )
        except Exception as status_err:
            logger.critical(
                "Mailversand ist fehlgeschlagen, aber der Status konnte nicht "
                "auf failed gesetzt werden. Pending bleibt bestehen und muss "
                "manuell geprueft werden: %s",
                status_err,
            )
            logger.debug("Technische Fehlerdetails: %s", status_err, exc_info=True)
        raise InvoiceProcessingError("Mailversand ist fehlgeschlagen.") from err
    except Exception as err:
        logger.error(
            "Unerwarteter Fehler waehrend des Mailversands. Pending bleibt "
            "bestehen und blockiert automatische Wiederholungen: %s",
            err,
        )
        logger.debug("Technische Fehlerdetails: %s", err, exc_info=True)
        raise InvoiceProcessingError("Unerwarteter Mailfehler.") from err

    logger.info("Mail an %s (%s) gesendet.", customer["name"], customer["email"])
    if mail_bcc:
        logger.info("BCC-Empfaenger ist konfiguriert.")

    try:
        set_delivery_status(
            history_path,
            history,
            invoice_id,
            STATUS_SENT,
        )
    except Exception as err:
        logger.critical(
            "Mail wurde versendet, aber der Status sent konnte nicht gespeichert "
            "werden. Pending bleibt bestehen; kein automatischer erneuter Versand: %s",
            err,
        )
        logger.debug("Technische Fehlerdetails: %s", err, exc_info=True)
        raise InvoiceProcessingError(
            "Status sent konnte nicht gespeichert werden."
        ) from err

    logger.info("Versandstatus sent gespeichert.")


def _save_zero_hours_status(
    customer: dict,
    today: date,
    invoice_number: str,
    invoice_date: str,
    cycle_months: int,
    history: list,
    history_path,
    interactive: bool,
    service_period: str = "",
    hours_info: dict | None = None,
    missing_months: list[str] | None = None,
) -> None:
    """Speichert den Status einer stundenbasierten Nullabrechnung."""
    status = STATUS_NO_INVOICE if interactive else STATUS_WAITING_HOURS
    history_entry = build_history_entry(
        customer,
        today,
        invoice_number,
        invoice_date,
        "0.00",
        cycle_months,
        status=status,
        service_period=service_period,
        hours_info=hours_info,
    )
    save_or_replace_history_entry(
        history_path,
        history,
        history_entry,
    )

    if interactive:
        logger.info(
            "Keine Stunden fuer %s. Keine Rechnung erstellt oder versendet; "
            "Abrechnung wurde als no_invoice abgeschlossen.",
            customer["company"],
        )
    else:
        missing_months = missing_months or []
        fehlende_hinweis = (
            f" Fehlende Monatsdaten: {', '.join(missing_months)}."
            if missing_months
            else ""
        )
        logger.warning(
            "Keine abrechenbaren oder unvollstaendige Stunden fuer %s. "
            "Keine Rechnung erstellt oder versendet; "
            "Status waiting_hours wird innerhalb dieses Rechnungsmonats erneut "
            "geprueft.%s",
            customer["company"],
            fehlende_hinweis,
        )


def _archive_pdf_if_needed(
    customer: dict,
    attachment_name: str,
    pdf_bytes: bytes,
) -> None:
    """Archiviert eine PDF, wenn der Kundeneintrag einen Archivpfad enthaelt."""
    archive_directory = customer.get("archive_directory")
    if not archive_directory:
        return

    archive_pdf(archive_directory, attachment_name, pdf_bytes)


def _deactivate_customer_if_needed(
    customers: list,
    customer: dict,
    today: date,
    paths,
    interactive: bool,
) -> None:
    """Fragt nach dem Entfernen abgeschlossener Kundeneintraege."""
    if not should_deactivate_customer(customer, today):
        return

    logger.info(
        "Kunde '%s' (%s) hat die letzte Rechnung erhalten.",
        customer["company"],
        customer["name"],
    )
    if not interactive:
        logger.info("Nicht-interaktiver Lauf: Kunde bleibt aktiv.")
        return

    decision = (
        input("❓ Moechtest du diesen Kunden jetzt deaktivieren? (y/n): ")
        .strip()
        .lower()
    )
    if decision == "y":
        customer["active"] = False
        save_customer_data(customer)
        logger.info("Kunde wurde in seiner YAML-Datei deaktiviert.")
    else:
        logger.info("Kunde bleibt weiterhin in der Kundendatei.")
