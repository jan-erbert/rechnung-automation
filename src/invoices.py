from datetime import date, datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP

from dateutil.relativedelta import relativedelta

from validation import validate_date, validate_nonnegative_integer
from time_utils import format_month_year

CENT = Decimal("0.01")


def build_invoice_data(entry: dict, today: date | datetime) -> dict:
    """Ermittelt Datum, Nummer und Faelligkeit fuer eine Rechnung."""
    invoice_date = entry.get("invoice_date")
    if not invoice_date:
        invoice_date = today.strftime("%d.%m.%Y")
    else:
        invoice_date = validate_date(invoice_date)

    due_days = validate_nonnegative_integer(
        entry.get("due_days", 14),
        "Faelligkeit",
    )

    invoice_date_value = datetime.strptime(invoice_date, "%d.%m.%Y")
    due_date = (invoice_date_value + timedelta(days=due_days)).strftime("%d.%m.%Y")

    prefix = str(entry.get("invoice_prefix") or "").strip()
    automatic_invoice_number = today.strftime("%m-%Y")
    invoice_number = (
        f"{prefix}-{automatic_invoice_number}" if prefix else automatic_invoice_number
    )

    return {
        "invoice_date": invoice_date,
        "month_year": format_month_year(today),
        "due_date": due_date,
        "invoice_number": invoice_number,
        "automatic_invoice_number": automatic_invoice_number,
    }


def calculate_tax_values(total_amount: Decimal, tax: dict) -> dict:
    """Berechnet Steuerhinweis und Bruttosumme fuer die Rechnung."""
    total_amount = Decimal(str(total_amount))
    if tax["small_business"]:
        tax_amount = Decimal("0.00")
        vat_note = "Gemäß § 19 UStG wird keine Umsatzsteuer berechnet."
        gross_amount = total_amount
    else:
        tax_rate = Decimal(str(tax["vat_rate"]))
        tax_amount = (total_amount * tax_rate / Decimal("100")).quantize(
            CENT, rounding=ROUND_HALF_UP
        )
        vat_note = f"zzgl. {tax['vat_rate']}% MwSt " f"({tax_amount:.2f} EUR)"
        gross_amount = total_amount + tax_amount

    return {
        "tax_amount": tax_amount,
        "vat_note": vat_note,
        "gross_amount": gross_amount,
        "formatted_total": f"{gross_amount:.2f}".replace(".", ","),
    }


def calculate_billing_period(today: date | datetime, cycle_months: int) -> str:
    """Baut den Text fuer den abgerechneten Monatszeitraum."""
    if cycle_months < 1:
        return ""

    zeitraum_start = format_month_year(today)
    zeitraum_ende_dt = today + relativedelta(months=cycle_months - 1)
    zeitraum_ende = format_month_year(zeitraum_ende_dt)

    if cycle_months == 1:
        return zeitraum_start

    return f"{zeitraum_start} – {zeitraum_ende}"
