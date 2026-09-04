from datetime import datetime
from pathlib import Path

from branding import load_logo_asset
from file_naming import build_preview_filename
from invoice_templates import InvoiceTemplates, build_template_context
from invoices import build_invoice_data, calculate_billing_period, calculate_tax_values
from path_checks import check_archive_path
from paths import ProjectPaths
from pdf_service import archive_pdf, generate_pdf_bytes
from services import build_service_items
from time_utils import now, today
from validation import validate_customer_entry, validate_positive_integer

PREVIEW_WATERMARK = "VORSCHAU"


def create_customer_invoice_preview(
    customer: dict,
    paths: ProjectPaths,
    invoice_config: dict,
    pdf_config: dict,
    design_config: dict,
    branding_config: dict,
    file_naming_config: dict,
    templates: InvoiceTemplates,
    timestamp: datetime | None = None,
) -> Path:
    """Erzeugt eine markierte Kunden-Vorschau ohne Versand oder Statusaenderung."""
    validate_customer_entry(customer)
    if customer.get("active") is False:
        raise ValueError("Fuer einen deaktivierten Kunden wird keine Vorschau erzeugt.")

    archive_value = customer.get("archive_directory")
    if not archive_value:
        raise ValueError(
            "Kundenvorschau nicht moeglich: archive_directory ist nicht gesetzt."
        )
    archive_directory = Path(archive_value).expanduser()
    if not archive_directory.is_absolute():
        archive_directory = paths.base_dir / archive_directory
    check_archive_path(str(archive_directory), write_probe=True)

    preview_date = today()
    preview_timestamp = timestamp or now()
    invoice_data = build_invoice_data(customer, preview_date)
    cycle_months = validate_positive_integer(
        customer.get("cycle_months", 1),
        "Abrechnungszyklus",
    )
    service_data = build_service_items(
        customer,
        cycle_months,
        paths.hours_dir,
        interactive=False,
        today=preview_date,
    )
    hours_info = service_data["hours_info"]
    if hours_info and (hours_info["hours"] == 0 or not hours_info["complete"]):
        raise ValueError(
            "Kundenvorschau nicht moeglich: Es fehlen vollstaendige abrechenbare "
            "Stundenwerte."
        )

    tax_data = calculate_tax_values(service_data["total_amount"], invoice_config["tax"])
    pdf_logo = load_logo_asset(
        paths.img_dir,
        branding_config["pdf_logo"],
        "PDF-Logo",
    )
    billing_period = (
        hours_info["period"]
        if hours_info
        else calculate_billing_period(preview_date, cycle_months)
    )
    template_context = build_template_context(
        customer=customer,
        sender=invoice_config["sender"],
        bank=invoice_config["bank"],
        tax=invoice_config["tax"],
        items=service_data["items"],
        invoice_number=invoice_data["invoice_number"],
        invoice_date=invoice_data["invoice_date"],
        due_date=invoice_data["due_date"],
        billing_period=billing_period,
        month_year=invoice_data["month_year"],
        cycle_months=cycle_months,
        total_amount=service_data["total_amount"],
        formatted_total=tax_data["formatted_total"],
        gross_amount=tax_data["gross_amount"],
        tax_amount=tax_data["tax_amount"],
        vat_note=tax_data["vat_note"],
        logo_base64=pdf_logo.data_uri if pdf_logo else "",
        mail_logo_cid="",
        design=design_config,
        branding=branding_config,
        hours_info=hours_info,
        sample_text=PREVIEW_WATERMARK,
    )
    pdf_html = templates.invoice.render(template_context)
    pdf_bytes = generate_pdf_bytes(pdf_html, pdf_config)

    target = _next_preview_path(
        archive_directory,
        customer["id"],
        invoice_data["automatic_invoice_number"],
        preview_timestamp,
        file_naming_config,
    )
    archive_pdf(str(archive_directory), target.name, pdf_bytes)
    return target


def _next_preview_path(
    archive_directory: Path,
    customer_id: str,
    invoice_number: str,
    timestamp: datetime,
    file_naming_config: dict,
) -> Path:
    """Ermittelt einen kollisionsfreien und gut erkennbaren Vorschaupfad."""
    file_name = build_preview_filename(
        customer_id,
        invoice_number,
        timestamp,
        file_naming_config,
    )
    base_name = file_name.removesuffix(".pdf")
    target = archive_directory / file_name
    number = 2
    while target.exists():
        target = archive_directory / f"{base_name}-{number:02d}.pdf"
        number += 1
    return target
