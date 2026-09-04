from datetime import datetime

from strict_yaml import reject_unknown_keys

DEFAULT_FILE_NAMING = {
    "invoice_prefix": "Invoice",
    "preview_prefix": "PREVIEW",
}
MAX_PREFIX_LENGTH = 50


def validate_file_naming_config(file_naming_config: dict | None) -> dict:
    """Prueft sichere, plattformuebergreifende Praefixe fuer PDF-Dateinamen."""
    if file_naming_config is None:
        file_naming_config = {}
    if not isinstance(file_naming_config, dict):
        raise ValueError("Der YAML-Bereich 'file_naming' muss eine Map sein.")

    reject_unknown_keys(
        file_naming_config,
        set(DEFAULT_FILE_NAMING),
        "file_naming",
    )
    return {
        name: _validate_prefix(file_naming_config.get(name, default), name)
        for name, default in DEFAULT_FILE_NAMING.items()
    }


def build_invoice_filename(
    customer_id: str,
    invoice_number: str,
    file_naming_config: dict | None,
) -> str:
    """Baut den konfigurierten Dateinamen fuer Rechnung und Mailanhang."""
    naming = validate_file_naming_config(file_naming_config)
    return f"{naming['invoice_prefix']}_{customer_id}_{invoice_number}.pdf"


def build_preview_filename(
    customer_id: str,
    invoice_number: str,
    timestamp: datetime,
    file_naming_config: dict | None,
) -> str:
    """Baut einen klar markierten und zeitgestempelten Vorschaudateinamen."""
    naming = validate_file_naming_config(file_naming_config)
    return (
        f"{naming['preview_prefix']}_{naming['invoice_prefix']}_{customer_id}_"
        f"{invoice_number}_{timestamp:%Y-%m-%d_%H-%M-%S}.pdf"
    )


def _validate_prefix(value, name: str) -> str:
    """Validiert einen einzelnen sicheren Dateinamenbestandteil."""
    if not isinstance(value, str) or not value:
        raise ValueError(f"file_naming.{name} muss ein nicht leerer Text sein.")
    if value != value.strip():
        raise ValueError(f"file_naming.{name} darf keine Rand-Leerzeichen enthalten.")
    if len(value) > MAX_PREFIX_LENGTH:
        raise ValueError(
            f"file_naming.{name} darf hoechstens {MAX_PREFIX_LENGTH} Zeichen haben."
        )
    if not all(character.isalnum() or character in "-_" for character in value):
        raise ValueError(
            f"file_naming.{name} darf nur Buchstaben, Zahlen, Bindestriche und "
            "Unterstriche enthalten."
        )
    return value
