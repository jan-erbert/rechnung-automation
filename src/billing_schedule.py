import logging
from datetime import date, datetime

from invoice_history import (
    STATUS_FAILED,
    STATUS_NO_INVOICE,
    STATUS_PENDING,
    STATUS_SENT,
    STATUS_WAITING_HOURS,
    is_billing_complete,
)
from time_utils import today as current_date
from validation import validate_positive_integer

logger = logging.getLogger(__name__)


def is_invoice_due(
    customer: dict,
    history: list[dict],
    previous_history: list[dict] | None = None,
    today: date | datetime | None = None,
) -> bool:
    """Prueft, ob fuer diesen Kunden heute abgerechnet werden soll."""
    all_history = [*history, *(previous_history or [])]
    cycle_months = validate_positive_integer(
        customer.get("cycle_months", 1), "Abrechnungszyklus"
    )
    today = today or current_date()

    end_month = str(customer.get("end_month") or "").strip()
    past_end = False
    is_final_month = False
    if end_month:
        limit = datetime.strptime(end_month, "%Y-%m")
        past_end = (today.year, today.month) > (limit.year, limit.month)
        is_final_month = (today.year, today.month) == (limit.year, limit.month)

    customer_history = [
        entry for entry in all_history if _is_same_customer(customer, entry)
    ]
    for entry in customer_history:
        same_month = (entry["year"], entry["month"]) == (today.year, today.month)
        status = entry.get("status", STATUS_SENT)
        if status == STATUS_PENDING:
            logger.warning(
                "%s: Versandstatus pending ist unklar. Keine automatische Rechnung.",
                customer.get("company", "Unbekannter Kunde"),
            )
            return False
        if same_month and is_billing_complete(entry):
            return False
        if same_month and status == STATUS_WAITING_HOURS:
            logger.warning(
                "%s: Stunden fehlen weiterhin. Abrechnung wird erneut geprueft.",
                customer.get("company", "Unbekannter Kunde"),
            )
        elif status == STATUS_WAITING_HOURS:
            logger.warning(
                "%s: Alter Status waiting_hours muss zuerst abgeschlossen werden.",
                customer.get("company", "Unbekannter Kunde"),
            )
            return False
        if same_month and status == STATUS_FAILED:
            logger.warning(
                "%s: Vorheriger Mailversand ist fehlgeschlagen; erneuter Versuch.",
                customer.get("company", "Unbekannter Kunde"),
            )
        elif status == STATUS_FAILED:
            logger.warning(
                "%s: Alter fehlgeschlagener Versand muss manuell geprueft werden.",
                customer.get("company", "Unbekannter Kunde"),
            )
            return False
        if status not in {
            STATUS_FAILED,
            STATUS_NO_INVOICE,
            STATUS_PENDING,
            STATUS_SENT,
            STATUS_WAITING_HOURS,
        }:
            return False

    if past_end:
        return False
    if customer.get("one_time") is True:
        return not any(is_billing_complete(entry) for entry in customer_history)
    if is_final_month:
        return True

    completed = [entry for entry in customer_history if is_billing_complete(entry)]
    if not completed:
        return True
    latest = max(completed, key=lambda item: (item["year"], item["month"]))
    previous_cycle = latest.get("cycle_months")
    if (
        previous_cycle
        and validate_positive_integer(previous_cycle, "Vorheriger Abrechnungszyklus")
        != cycle_months
    ):
        logger.info(
            "Zykluswechsel erkannt (%s -> %s) - neue Rechnung wird erzeugt.",
            previous_cycle,
            cycle_months,
        )
        return True
    month_difference = (
        (today.year - latest["year"]) * 12 + today.month - latest["month"]
    )
    return month_difference >= cycle_months


def _is_same_customer(customer: dict, history_entry: dict) -> bool:
    """Vergleicht die stabile Kunden-ID."""
    customer_id = customer.get("id")
    history_customer_id = history_entry.get("customer_id")
    if customer_id and history_customer_id:
        return history_customer_id == customer_id
    return history_entry.get("company") == customer.get(
        "company"
    ) and history_entry.get("name") == customer.get("name")
