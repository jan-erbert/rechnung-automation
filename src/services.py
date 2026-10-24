import logging
from datetime import date
from decimal import Decimal
from pathlib import Path

from dateutil.relativedelta import relativedelta

from customer_changes import resolve_customer_for_period

from hours_files import (
    HoursFileError,
    load_hours_month,
    save_hours_value,
    hours_file_path,
    validate_hours_value,
    period_from_date,
)
from validation import validate_amount, validate_unit
from time_utils import format_month_year, today as current_date

logger = logging.getLogger(__name__)


def calculate_hourly_service(
    customer_id: str,
    cycle_months: int,
    hourly_rate: Decimal,
    hours_dir: Path,
    interactive: bool = True,
    today: date | None = None,
    monthly_rates: dict | None = None,
):
    """Berechnet stundenbasierte Leistungen fuer den Abrechnungszeitraum."""
    today = today or current_date()
    total_hours = Decimal("0")
    total_amount = Decimal("0")
    details = []
    months = []
    missing_months = []

    for i in range(cycle_months):
        month_date = today - relativedelta(months=i + 1)
        period = period_from_date(month_date)
        file_name = hours_file_path(hours_dir, period)
        months.append(format_month_year(month_date))
        hours_values = load_hours_month(file_name, period) if file_name.exists() else {}
        hours = hours_values.get(customer_id)

        if hours is None:
            logger.warning(
                "Keine Stunden fuer Kunden-ID '%s' im Monat %s gefunden.",
                customer_id,
                format_month_year(month_date),
            )
            if not interactive:
                logger.info("Nicht-interaktiver Lauf: 0 Stunden angenommen.")
                missing_months.append(month_date.strftime("%Y-%m"))
                continue

            hours = _ask_hours_value(period)
            saved_at = save_hours_value(
                hours_dir,
                period,
                customer_id,
                hours,
            )
            logger.info(
                "Manuelle Stundenangabe wurde in %s gespeichert.",
                saved_at,
            )

        total_hours += hours
        rate = (monthly_rates or {}).get(period, hourly_rate)
        total_amount += rate * hours
        details.append({"month": period, "hours": hours, "rate": rate})

    rates = {item["rate"] for item in details}
    amount = total_amount
    period = ", ".join(reversed(months))

    return {
        "hours": total_hours,
        "hourly_rate": next(iter(rates)) if len(rates) == 1 else hourly_rate,
        "monthly_details": list(reversed(details)),
        "mixed_rates": len(rates) > 1,
        "total_amount": amount,
        "period": period,
        "complete": not missing_months,
        "missing_months": missing_months,
    }


def _ask_hours_value(period: str) -> Decimal:
    """Fragt interaktiv einen gueltigen Stundenwert fuer einen Monat ab."""
    while True:
        input_value = input("Bitte Stundenanzahl manuell eingeben (Enter fuer 0): ")
        try:
            return validate_hours_value(
                input_value.strip() or "0",
                f"Manuelle Eingabe fuer {period}",
            )
        except HoursFileError as err:
            logger.warning("%s Bitte erneut eingeben.", err)


def build_service_items(
    entry: dict,
    cycle_months: int,
    hours_dir: Path,
    interactive: bool = True,
    today: date | None = None,
) -> dict:
    """Baut Leistungspositionen und Nettosumme fuer einen Kundeneintrag."""
    invoice_day = today or current_date()
    monthly_rates = None
    if entry.get("main_service", {}).get("unit") == "hour" and entry.get(
        "_scheduled_changes"
    ):
        preceding = resolve_customer_for_period(
            entry, invoice_day - relativedelta(months=1)
        )
        cycle_months = int(preceding.get("cycle_months", cycle_months))
        snapshots = [
            resolve_customer_for_period(
                entry, invoice_day - relativedelta(months=index + 1)
            )
            for index in range(cycle_months)
        ]
        if any(
            item.get("additional_services") != snapshots[0].get("additional_services")
            for item in snapshots
        ):
            raise HoursFileError(
                "Zusatzleistungen wechseln im Stundenzeitraum; getrennte Abrechnung pruefen."
            )
        monthly_rates = {
            (invoice_day - relativedelta(months=index + 1)).strftime(
                "%Y-%m"
            ): validate_amount(item["main_service"]["unit_price"], "Stundensatz")
            for index, item in enumerate(snapshots)
        }
        entry = snapshots[0]
    main_service = entry.get("main_service", {})
    items = []

    description = main_service.get("description", "Leistung")
    unit = validate_unit(main_service.get("unit", "month"))
    amount = validate_amount(main_service.get("unit_price"), "main_service.unit_price")

    hours_info = None
    if unit == "hour":
        hours_info = calculate_hourly_service(
            entry.get("id", ""),
            cycle_months,
            amount,
            hours_dir,
            interactive=interactive,
            today=today,
            **({"monthly_rates": monthly_rates} if monthly_rates is not None else {}),
        )

        if hours_info["hours"] == 0 or not hours_info["complete"]:
            return {
                "items": items,
                "total_amount": Decimal("0"),
                "hours_info": hours_info,
            }

        amount = hours_info["total_amount"]
        total_amount = amount
        description = (
            f"{hours_info['hours']:.1f} Stunden × "
            f"{hours_info['hourly_rate']:.2f} EUR"
        )
        if hours_info.get("mixed_rates"):
            for detail in hours_info["monthly_details"]:
                value = detail["hours"] * detail["rate"]
                items.append(
                    {
                        "description": (
                            f"{detail['month']}: {detail['hours']:.1f} Stunden "
                            f"× {detail['rate']:.2f} EUR"
                        ),
                        "price": f"{value:.2f}".replace(".", ",") + " EUR",
                        "invoice_line": _invoice_line(
                            detail["month"]
                            + ": "
                            + main_service.get("description", "Leistung"),
                            detail["hours"],
                            detail["rate"],
                            value,
                            "HUR",
                        ),
                    }
                )
        else:
            items.append(
                {
                    "description": description,
                    "price": f"{amount:.2f}".replace(".", ",") + " EUR",
                    "invoice_line": _invoice_line(
                        main_service.get("description", "Leistung"),
                        hours_info["hours"],
                        hours_info["hourly_rate"],
                        amount,
                        "HUR",
                    ),
                }
            )

    elif unit == "flat":
        total_amount = amount
        items.append(
            {
                "description": f"{description} (pauschal)",
                "price": f"{amount:.2f}".replace(".", ",") + " EUR",
                "invoice_line": _invoice_line(description, 1, amount, amount, "C62"),
            }
        )

    else:
        total_amount = amount * cycle_months
        period_text = "1 Monat" if cycle_months == 1 else f"{cycle_months} Monate"
        description_with_period = f"{description} für {period_text}"
        website = entry.get("website")
        if website:
            description_with_period += f" ({website})"

        items.append(
            {
                "description": description_with_period,
                "price": f"{total_amount:.2f}".replace(".", ",") + " EUR",
                "invoice_line": _invoice_line(
                    description_with_period, cycle_months, amount, total_amount, "MON"
                ),
            }
        )

    for additional_service in entry.get("additional_services", []):
        description = additional_service.get("description", "Zusatzleistung")
        price_text = (
            "Inklusive"
            if additional_service.get("unit") == "included"
            else str(additional_service.get("unit_price", "")).strip()
        )
        price_amount = validate_amount(
            price_text,
            "Preis der Zusatzleistung",
            included_allowed=True,
        )

        if price_amount is not None:
            if additional_service.get("unit") == "flat" or (
                "unit" not in additional_service and unit == "flat"
            ):
                formatted_price = f"{price_amount:.2f}".replace(".", ",") + " EUR"
                additional_text = ""
                item_total = price_amount
            else:
                item_total = price_amount * cycle_months
                additional_text = (
                    f"({price_amount:.2f}".replace(".", ",")
                    + f" EUR × {cycle_months} Monate)"
                )
                formatted_price = f"{item_total:.2f}".replace(".", ",") + " EUR"
        else:
            additional_text = ""
            formatted_price = price_text
            item_total = Decimal("0")

        items.append(
            {
                "description": description
                + (f"<br><small>{additional_text}</small>" if additional_text else ""),
                "price": formatted_price,
                "invoice_line": _invoice_line(
                    description, 1, item_total, item_total, "C62"
                ),
            }
        )

        if item_total > 0:
            total_amount += item_total

    return {
        "items": items,
        "total_amount": total_amount,
        "hours_info": hours_info,
    }


def _invoice_line(name, quantity, unit_price, total, unit_code) -> dict:
    """Behaelt berechnete Positionswerte fuer den optionalen XML-Export."""
    return {
        "name": name,
        "quantity": Decimal(str(quantity)),
        "unit_price": Decimal(str(unit_price)),
        "total": Decimal(str(total)),
        "unit_code": unit_code,
    }
