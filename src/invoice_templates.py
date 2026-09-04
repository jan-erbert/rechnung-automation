from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, Template


@dataclass(frozen=True)
class InvoiceTemplates:
    """Buendelt die geladenen E-Mail- und Rechnungstemplates."""

    email: Template
    invoice: Template


def load_templates(templates_dir: Path) -> InvoiceTemplates:
    """Laedt die HTML-Templates fuer E-Mail und Rechnung."""
    environment = Environment(loader=FileSystemLoader(templates_dir), autoescape=True)
    return InvoiceTemplates(
        email=environment.get_template("email_template.html"),
        invoice=environment.get_template("invoice_template.html"),
    )


def build_template_context(
    customer: dict,
    sender: dict,
    bank: dict,
    tax: dict,
    items: list,
    invoice_number: str,
    invoice_date: str,
    due_date: str,
    billing_period: str,
    month_year: str,
    cycle_months: int,
    total_amount: Decimal,
    formatted_total: str,
    gross_amount: Decimal,
    tax_amount: Decimal,
    vat_note: str,
    logo_base64: str,
    mail_logo_cid: str,
    design: dict,
    branding: dict,
    hours_info: dict | None = None,
    sample_text: str = "",
) -> dict:
    """Baut den gemeinsamen Kontext fuer E-Mail- und PDF-Templates."""
    context = {
        "name": customer["name"],
        "company": customer["company"],
        "email": customer["email"],
        "street": customer["street"],
        "postal_code": customer["postal_code"],
        "city": customer["city"],
        "invoice_number": invoice_number,
        "invoice_date": invoice_date,
        "due_date": due_date,
        "billing_period": billing_period or "",
        "month_year": month_year,
        "items": items,
        "formatted_total": formatted_total,
        "logo_base64": logo_base64,
        "mail_logo_cid": mail_logo_cid,
        "sample_text": sample_text,
        "design": design,
        "header_title": branding.get("header_title") or sender["name"],
        "header_subtitle": branding.get("header_subtitle") or sender["company"],
        "pdf_logo_height": branding["pdf_logo_height"],
        "mail_logo_height": branding["mail_logo_height"],
        "cycle_months": cycle_months,
        "sender": sender,
        "bank": bank,
        "tax": tax,
        "vat_note": vat_note,
        "tax_amount": f"{tax_amount:.2f}".replace(".", ","),
        "vat_rate": _format_percentage(tax.get("vat_rate", Decimal("0"))),
        "gross_amount": f"{gross_amount:.2f}".replace(".", ","),
        "net_amount": f"{total_amount:.2f}".replace(".", ","),
    }
    if hours_info:
        context["hourly_rate_note"] = (
            f"(Stundensatz: {hours_info['hourly_rate']:.2f} EUR pro Stunde)"
        )
    return context


def _format_percentage(value) -> str:
    """Formatiert einen Dezimal-Prozentsatz ohne unnoetige Nullen."""
    return format(Decimal(str(value)), "f").rstrip("0").rstrip(".") or "0"
