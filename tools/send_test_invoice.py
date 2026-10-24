import logging
import sys
from datetime import datetime, timedelta
from decimal import Decimal
from email.utils import parseaddr
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from branding import (  # noqa: E402
    LogoAsset,
    load_logo_asset,
    resolve_mail_branding,
    validate_branding_config,
)
from design import validate_design_config  # noqa: E402
from configuration import load_invoice_config, load_mail_environment  # noqa: E402
from logging_setup import configure_logging  # noqa: E402
from email_service import (  # noqa: E402
    MailDeliveryError,
    build_invoice_email,
    send_email,
)
from paths import create_paths  # noqa: E402
from pdf_service import generate_pdf_bytes  # noqa: E402
from invoices import calculate_tax_values  # noqa: E402
from settings_loader import load_settings  # noqa: E402
from invoice_templates import build_template_context, load_templates  # noqa: E402
from time_utils import format_month_year, now  # noqa: E402

logger = logging.getLogger(__name__)

SAMPLE_TYPES = {
    "1": "month",
    "monat": "month",
    "2": "flat",
    "flat": "flat",
    "3": "hours",
    "stunden": "hours",
}
SAMPLE_TYPE_LABELS = {"month": "Monat", "flat": "Pauschal", "hours": "Stunden"}


def main() -> int:
    """Startet die Musterrechnung mit kontrollierter Fehlerausgabe."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    try:
        _send_sample_invoice()
    except MailDeliveryError as err:
        logger.error("Musterrechnung konnte nicht versendet werden: %s", err)
        if err.hint:
            logger.error("Hinweis: %s", err.hint)
        return 1
    except (FileNotFoundError, OSError, RuntimeError, ValueError) as err:
        logger.error("Musterrechnung abgebrochen: %s", err)
        return 1
    return 0


def _send_sample_invoice() -> None:
    """Erzeugt und versendet eine deutlich markierte Musterrechnung."""
    settings = load_settings()
    paths = create_paths(settings)
    configure_logging(settings.get("logging", {}), paths.base_dir)
    invoice_config = load_invoice_config(paths.invoice_config)
    mail_config = load_mail_environment(
        paths.base_dir / ".env", settings.get("mail", {})
    )
    from pdf_service import resolve_pdf_config

    pdf_config = resolve_pdf_config(settings.get("pdf", {}), invoice_config)
    design = validate_design_config(settings.get("design", {}))
    branding = validate_branding_config(settings.get("branding", {}))
    templates = load_templates(paths.templates_dir)

    default_recipient = invoice_config.get("mail", {}).get("bcc")
    if not default_recipient:
        raise ValueError(
            "Testrechnung nicht moeglich: In config/invoice.yaml fehlt mail.bcc."
        )

    recipient = ask_recipient(default_recipient[0])
    sample_type = ask_sample_type()
    context, mail_logo = build_sample_context(
        sample_type,
        invoice_config,
        design,
        branding,
        paths.img_dir,
    )

    mail_html = templates.email.render(context)
    pdf_html = templates.invoice.render(context)
    if pdf_config["format"] == "zugferd":
        pdf_bytes = generate_pdf_bytes(
            pdf_html, pdf_config, context["invoice_snapshot"]
        )
    else:
        pdf_bytes = generate_pdf_bytes(pdf_html, pdf_config)
    msg = build_invoice_email(
        mail_user=mail_config["user"],
        recipient=recipient,
        subject=f"[MUSTER] Testrechnung {SAMPLE_TYPE_LABELS[sample_type]}",
        mail_html=mail_html,
        pdf_bytes=pdf_bytes,
        attachment_name=f"SAMPLE_Invoice_{sample_type}.pdf",
        mail_logo=mail_logo,
        from_name=invoice_config.get("mail", {}).get("from_name"),
    )

    logger.info("Versende Musterrechnung der Art '%s'.", sample_type)
    send_email(
        mail_config["server"],
        mail_config["port"],
        mail_config["user"],
        mail_config["password"],
        msg,
        [recipient],
        security=mail_config.get("security", "starttls"),
        timeout=mail_config.get("timeout", 30),
    )
    logger.info("Musterrechnung wurde erfolgreich versendet.")


def ask_recipient(default_recipient: str) -> str:
    """Fragt den Empfaenger ab und verwendet standardmaessig die BCC-Adresse."""
    while True:
        input_value = input(
            f"Empfaenger der Musterrechnung [{default_recipient}]: "
        ).strip()
        recipient = input_value or default_recipient
        if _is_valid_email(recipient):
            return recipient
        print("Ungueltige E-Mail-Adresse. Bitte erneut eingeben.")


def ask_sample_type() -> str:
    """Fragt nach einem Monats-, Pauschal- oder Stundenmuster."""
    while True:
        input_value = input(
            "Musterart waehlen: [1] Monat, [2] Pauschal, [3] Stunden: "
        ).strip()
        sample_type = SAMPLE_TYPES.get(input_value.lower())
        if sample_type:
            return sample_type
        print("Ungueltige Auswahl. Bitte 1, 2 oder 3 eingeben.")


def build_sample_context(
    sample_type: str,
    invoice_config: dict,
    design: dict,
    branding: dict,
    image_dir: Path,
    timestamp: datetime | None = None,
) -> tuple[dict, LogoAsset | None]:
    """Baut den Template-Kontext fuer eine synthetische Musterrechnung."""
    timestamp = timestamp or now()
    branding = resolve_mail_branding(branding, invoice_config.get("mail", {}))
    service_data = build_sample_service_data(sample_type)
    tax_data = calculate_tax_values(service_data["total_amount"], invoice_config["tax"])
    pdf_logo = load_logo_asset(image_dir, branding["pdf_logo"], "PDF-Logo")
    mail_logo = load_logo_asset(image_dir, branding["mail_logo"], "Mail-Logo")

    context = build_template_context(
        customer={
            "name": "Erika Beispiel",
            "company": "Beispielfirma GmbH",
            "email": "muster@example.com",
            "street": "Beispielweg 12",
            "postal_code": "12345",
            "city": "Musterstadt",
        },
        sender=invoice_config["sender"],
        bank=invoice_config["bank"],
        tax=invoice_config["tax"],
        items=service_data["items"],
        invoice_number=f"MUSTER-{timestamp:%m-%Y}",
        invoice_date=timestamp.strftime("%d.%m.%Y"),
        due_date=(timestamp + timedelta(days=14)).strftime("%d.%m.%Y"),
        billing_period=format_month_year(timestamp),
        month_year=format_month_year(timestamp),
        cycle_months=1,
        total_amount=service_data["total_amount"],
        formatted_total=tax_data["formatted_total"],
        gross_amount=tax_data["gross_amount"],
        tax_amount=tax_data["tax_amount"],
        vat_note=tax_data["vat_note"],
        logo_base64=pdf_logo.data_uri if pdf_logo else "",
        mail_logo_cid="invoice-logo" if mail_logo else "",
        design=design,
        branding=branding,
        hours_info=service_data["hours_info"],
        sample_text="MUSTER",
    )
    from zugferd import invoice_snapshot

    context["invoice_snapshot"] = invoice_snapshot(
        {
            "name": context["name"],
            "company": context["company"],
            "street": context["street"],
            "postal_code": context["postal_code"],
            "city": context["city"],
            "email": context["email"],
        },
        invoice_config["sender"],
        invoice_config["bank"],
        invoice_config["tax"],
        service_data,
        {
            "invoice_number": context["invoice_number"],
            "invoice_date": context["invoice_date"],
            "due_date": context["due_date"],
        },
        tax_data,
    )
    return context, mail_logo


def build_sample_service_data(sample_type: str) -> dict:
    """Erstellt feste, synthetische Leistungsdaten fuer die Musterarten."""
    if sample_type == "month":
        return {
            "items": [
                {
                    "description": "Monatliche Musterleistung fuer 1 Monat",
                    "price": "89,00 EUR",
                    "invoice_line": {
                        "name": "Musterleistung",
                        "quantity": Decimal("1"),
                        "unit_price": Decimal("89.00"),
                        "total": Decimal("1") * Decimal("89.00"),
                        "unit_code": "MON",
                    },
                }
            ],
            "total_amount": Decimal("89.00"),
            "hours_info": None,
        }
    if sample_type == "flat":
        return {
            "items": [
                {
                    "description": "Einmalige Musterleistung (pauschal)",
                    "price": "450,00 EUR",
                    "invoice_line": {
                        "name": "Musterleistung",
                        "quantity": Decimal("1"),
                        "unit_price": Decimal("450.00"),
                        "total": Decimal("1") * Decimal("450.00"),
                        "unit_code": "C62",
                    },
                }
            ],
            "total_amount": Decimal("450.00"),
            "hours_info": None,
        }
    if sample_type == "hours":
        return {
            "items": [
                {
                    "description": "6.5 Stunden x 75.00 EUR",
                    "price": "487,50 EUR",
                    "invoice_line": {
                        "name": "Musterleistung",
                        "quantity": Decimal("6.5"),
                        "unit_price": Decimal("75.00"),
                        "total": Decimal("6.5") * Decimal("75.00"),
                        "unit_code": "HUR",
                    },
                }
            ],
            "total_amount": Decimal("487.50"),
            "hours_info": {
                "hours": Decimal("6.5"),
                "hourly_rate": Decimal("75.00"),
            },
        }
    raise ValueError("Unbekannte Musterart.")


def _is_valid_email(value: str) -> bool:
    """Prueft eine einzelne einfache Empfaengeradresse."""
    name, address = parseaddr(value)
    domain = address.rsplit("@", 1)[-1]
    return not name and address == value and "@" in address and "." in domain


if __name__ == "__main__":
    raise SystemExit(main())
