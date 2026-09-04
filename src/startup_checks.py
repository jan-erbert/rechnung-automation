from branding import validate_branding_config
from design import validate_design_config
from file_naming import validate_file_naming_config
from pdf_service import validate_pdf_config
from path_checks import check_readable_file, check_readable_directory


def check_start_requirements(
    settings: dict,
    paths,
    data: list,
    mail_config: dict,
) -> None:
    """Prueft die wichtigsten Voraussetzungen vor einem Rechnungslauf."""
    validate_pdf_config(settings.get("pdf", {}))
    validate_design_config(settings.get("design", {}))
    validate_branding_config(settings.get("branding", {}))
    validate_file_naming_config(settings.get("file_naming", {}))
    _check_mail_config(mail_config)
    if not isinstance(data, list):
        raise ValueError("Kundendaten muessen als Liste geladen werden.")

    check_readable_file(
        paths.base_dir / "config" / "settings.yaml",
        "config/settings.yaml",
    )
    check_readable_file(paths.base_dir / ".env", ".env")
    check_readable_directory(paths.customers_dir, "Kundenverzeichnis")
    check_readable_file(paths.invoice_config, "config/invoice.yaml")
    check_readable_directory(paths.templates_dir, "Template-Verzeichnis")
    check_readable_file(
        paths.templates_dir / "email_template.html",
        "Mailvorlage",
    )
    check_readable_file(
        paths.templates_dir / "invoice_template.html",
        "Rechnungsvorlage",
    )


def _check_mail_config(mail_config: dict) -> None:
    """Prueft die bereits geladene Mail-Konfiguration."""
    if not isinstance(mail_config, dict):
        raise ValueError("Mail-Konfiguration muss eine Map sein.")
    for key in ("server", "port", "user", "password"):
        if mail_config.get(key) in (None, ""):
            raise ValueError(f"Mail-Konfiguration: {key} fehlt.")
