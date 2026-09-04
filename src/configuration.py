import os
from decimal import Decimal
from pathlib import Path

from dotenv import dotenv_values

from strict_yaml import load_yaml, reject_unknown_keys

from validation import (
    normalize_email_list,
    validate_percentage,
    validate_positive_integer,
)


def load_invoice_config(path: Path) -> dict:
    """Laedt die fachliche Rechnungskonfiguration aus YAML."""
    if not path.exists():
        raise FileNotFoundError(f"Konfigurationsdatei '{path}' nicht gefunden.")

    config = load_yaml(path) or {}
    if not isinstance(config, dict):
        raise ValueError("Die Rechnungskonfiguration muss eine YAML-Map sein.")

    sender = _require_map(config, "sender")
    bank = _require_map(config, "bank")
    tax = _require_map(config, "tax")
    mail = config.get("mail", {})
    if not isinstance(mail, dict):
        raise ValueError("Der Bereich 'mail' muss eine Map sein.")
    reject_unknown_keys(config, {"sender", "bank", "tax", "mail"}, "invoice")
    reject_unknown_keys(
        sender,
        {
            "name",
            "company",
            "street",
            "postal_code",
            "city",
            "phone",
            "email",
            "website",
        },
        "sender",
    )
    reject_unknown_keys(bank, {"name", "iban", "bic", "account_holder"}, "bank")
    reject_unknown_keys(
        tax,
        {
            "identifier_type",
            "tax_number",
            "vat_id",
            "tax_office",
            "small_business",
            "vat_rate",
        },
        "tax",
    )
    reject_unknown_keys(mail, {"bcc", "from_name"}, "mail")

    _require_fields(
        sender,
        "sender",
        ("name", "company", "street", "postal_code", "city", "phone", "email"),
    )
    _require_fields(bank, "bank", ("name", "iban", "bic", "account_holder"))
    _validate_tax_identifier(tax)
    _validate_mail_options(mail)
    normalize_email_list(sender["email"], "sender.email")
    for field in ("name", "company", "street", "postal_code", "city", "phone", "email"):
        if not isinstance(sender[field], str):
            raise ValueError(f"sender.{field} muss ein Text sein.")
    for field in ("name", "account_holder", "iban", "bic"):
        if not isinstance(bank[field], str):
            raise ValueError(f"bank.{field} muss ein Text sein.")

    small_business = tax.get("small_business")
    if not isinstance(small_business, bool):
        raise ValueError("tax.small_business muss true oder false sein.")

    vat_rate = Decimal("0")
    if not small_business:
        if "vat_rate" not in tax:
            raise ValueError("tax.vat_rate fehlt bei Nicht-Kleinunternehmern.")
        if not isinstance(tax["vat_rate"], str):
            raise ValueError("tax.vat_rate muss als Text in Anfuehrungszeichen stehen.")
        vat_rate = validate_percentage(tax["vat_rate"], "tax.vat_rate")

    return {
        "sender": {
            "name": sender["name"],
            "company": sender["company"],
            "street": sender.get("street", ""),
            "postal_code": str(sender.get("postal_code", "")),
            "city": sender.get("city", ""),
            "phone": str(sender.get("phone", "")),
            "email": sender["email"],
            "website": sender.get("website", ""),
        },
        "bank": {
            "name": bank.get("name", ""),
            "account_holder": bank["account_holder"],
            "iban": bank["iban"],
            "bic": bank.get("bic", ""),
        },
        "tax": {
            "identifier_type": tax["identifier_type"],
            tax["identifier_type"]: tax[tax["identifier_type"]],
            "tax_office": tax.get("tax_office", ""),
            "small_business": small_business,
            "vat_rate": vat_rate,
        },
        "mail": {
            "bcc": _normalize_address_list(mail.get("bcc")),
            "from_name": mail.get("from_name") or None,
        },
    }


def _require_map(config: dict, name: str) -> dict:
    """Liefert einen erforderlichen YAML-Bereich als Map."""
    value = config.get(name)
    if not isinstance(value, dict):
        raise ValueError(f"Der Bereich '{name}' muss eine Map sein.")
    return value


def _require_fields(config: dict, section: str, fields: tuple[str, ...]) -> None:
    """Prueft erforderliche, nicht leere Konfigurationsfelder."""
    for field in fields:
        if config.get(field) in (None, ""):
            raise ValueError(f"Pflichtfeld fehlt: '{section}.{field}'")


def _validate_mail_options(mail_config: dict) -> None:
    """Prueft optionale Einstellungen fuer erzeugte E-Mails."""
    from_name = mail_config.get("from_name")
    if from_name not in (None, "") and (
        not isinstance(from_name, str) or not from_name.strip()
    ):
        raise ValueError("mail.from_name muss ein Text sein oder leer bleiben.")
    _normalize_address_list(mail_config.get("bcc"))


def _normalize_address_list(value) -> list[str]:
    """Normalisiert optionale Konfigurations-Empfaenger als Liste."""
    if value in (None, ""):
        return []
    if not isinstance(value, list):
        raise ValueError("mail.bcc muss eine Liste von Mailadressen sein.")
    return normalize_email_list(value, "mail.bcc")


def _validate_tax_identifier(tax: dict) -> None:
    """Prueft die ausgewaehlte Steuernummer oder USt-IdNr."""
    identifier_type = tax.get("identifier_type")
    if identifier_type not in ("tax_number", "vat_id"):
        raise ValueError("tax.identifier_type muss 'tax_number' oder 'vat_id' sein.")
    if not tax.get(identifier_type):
        raise ValueError(f"Pflichtfeld fehlt: 'tax.{identifier_type}'")
    if not isinstance(tax[identifier_type], str):
        raise ValueError(f"tax.{identifier_type} muss ein Text sein.")


def load_mail_environment(path: Path, mail_settings: dict | None = None) -> dict:
    """Laedt Mail-Zugangsdaten ohne globale Umgebungsvariablen zu veraendern."""
    if not path.exists():
        raise FileNotFoundError(f"Env-Datei '{path}' nicht gefunden.")

    env = {**dotenv_values(path), **os.environ}
    required_fields = ("MAIL_SERVER", "MAIL_PORT", "MAIL_USER", "MAIL_PASS")
    missing_fields = [field for field in required_fields if not env.get(field)]
    if missing_fields:
        raise ValueError(
            "Pflichtfelder fehlen in der Env-Datei: " + ", ".join(missing_fields)
        )

    mail_settings = mail_settings or {}
    if not isinstance(mail_settings, dict):
        raise ValueError("Der YAML-Bereich 'mail' muss eine Map sein.")
    security = str(mail_settings.get("security", "starttls")).lower()
    if security not in ("starttls", "ssl"):
        raise ValueError("mail.security muss 'starttls' oder 'ssl' sein.")
    timeout = validate_positive_integer(
        mail_settings.get("timeout_seconds", 30), "mail.timeout_seconds"
    )

    mail_port = validate_positive_integer(env["MAIL_PORT"], "MAIL_PORT")
    if mail_port > 65535:
        raise ValueError("MAIL_PORT darf hoechstens 65535 sein.")
    return {
        "server": env["MAIL_SERVER"],
        "port": mail_port,
        "user": env["MAIL_USER"],
        "password": env["MAIL_PASS"],
        "security": security,
        "timeout": timeout,
    }
