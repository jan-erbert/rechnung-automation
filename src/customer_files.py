import os
import re
import tempfile
import logging
from datetime import date, datetime
from pathlib import Path

import yaml

from strict_yaml import load_yaml, reject_unknown_keys
from validation import validate_customer_entry

CUSTOMER_ID_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
SUPPORTED_UNITS = {"month", "hour", "flat"}
logger = logging.getLogger(__name__)


def load_customer_files(customers_dir: Path, strict: bool = True) -> list[dict]:
    """Laedt und validiert alle YAML-Kundendateien eines Verzeichnisses."""
    if not customers_dir.exists():
        raise FileNotFoundError(f"Kundenverzeichnis '{customers_dir}' fehlt.")
    if not customers_dir.is_dir():
        raise ValueError(f"Kundenpfad '{customers_dir}' ist kein Verzeichnis.")

    customers = []
    known_ids = set()
    files = sorted((*customers_dir.glob("*.yaml"), *customers_dir.glob("*.yml")))
    for file_path in files:
        try:
            raw_value = load_yaml(file_path) or {}
            customer = normalize_customer(raw_value, file_path)
            validate_customer_entry(customer)
            if customer["id"] in known_ids:
                raise ValueError(f"Doppelte Kunden-ID: '{customer['id']}'.")
        except (OSError, ValueError, yaml.YAMLError) as err:
            error = ValueError(f"{file_path.name}: {err}")
            if strict:
                raise error from err
            logger.error("Kundendatei wird uebersprungen: %s", error)
            continue
        known_ids.add(customer["id"])
        customers.append(customer)
    return customers


def normalize_customer(raw_value: dict, file_path: Path | None = None) -> dict:
    """Uebersetzt das editierbare YAML-Schema in das interne Kundenmodell."""
    if not isinstance(raw_value, dict):
        raise ValueError("Kundendatei muss eine YAML-Map enthalten.")
    customer_id = raw_value.get("id")
    if not isinstance(customer_id, str) or not CUSTOMER_ID_PATTERN.fullmatch(
        customer_id
    ):
        raise ValueError(
            "id muss ein kleingeschriebener Bezeichner wie 'musterfirma' sein."
        )

    contact = _map(raw_value, "contact")
    billing = _map(raw_value, "billing", optional=True)
    main_service = _map(raw_value, "main_service")
    archive = _map(raw_value, "archive", optional=True)
    reject_unknown_keys(
        raw_value,
        {
            "id",
            "active",
            "contact",
            "billing",
            "main_service",
            "additional_services",
            "archive",
        },
        "customer",
    )
    reject_unknown_keys(
        contact,
        {
            "name",
            "company",
            "email",
            "cc",
            "street",
            "postal_code",
            "city",
            "website",
        },
        "contact",
    )
    reject_unknown_keys(
        billing,
        {
            "invoice_prefix",
            "cycle_months",
            "due_days",
            "end_month",
            "invoice_date",
            "one_time",
        },
        "billing",
    )
    reject_unknown_keys(
        main_service,
        {"description", "unit", "unit_price"},
        "main_service",
    )
    reject_unknown_keys(archive, {"directory"}, "archive")
    unit = main_service.get("unit", "month")
    if unit not in SUPPORTED_UNITS:
        raise ValueError("main_service.unit muss month, hour oder flat sein.")
    if not isinstance(main_service.get("unit_price"), str):
        raise ValueError(
            "main_service.unit_price muss als Text in Anfuehrungszeichen stehen."
        )
    for field in ("name", "company", "email", "street", "postal_code", "city"):
        if not isinstance(contact.get(field), str) or not contact[field].strip():
            raise ValueError(f"contact.{field} muss ein nicht leerer Text sein.")
    if not isinstance(contact.get("cc", []), list):
        raise ValueError("contact.cc muss eine Liste sein.")
    if contact.get("website") is not None and not isinstance(
        contact.get("website"), str
    ):
        raise ValueError("contact.website muss ein Text oder null sein.")
    if archive.get("directory") is not None and not isinstance(
        archive.get("directory"), str
    ):
        raise ValueError("archive.directory muss ein Text oder null sein.")
    if (
        not isinstance(main_service.get("description"), str)
        or not main_service["description"].strip()
    ):
        raise ValueError("main_service.description muss ein nicht leerer Text sein.")

    customer = {
        "id": customer_id,
        "active": raw_value.get("active", True),
        "name": contact.get("name"),
        "company": contact.get("company"),
        "email": contact.get("email"),
        "cc": contact.get("cc", []),
        "street": contact.get("street"),
        "postal_code": str(contact.get("postal_code", "")),
        "city": contact.get("city"),
        "website": contact.get("website"),
        "invoice_prefix": billing.get("invoice_prefix", ""),
        "cycle_months": billing.get("cycle_months", 1),
        "due_days": billing.get("due_days", 14),
        "end_month": _normalize_month(billing.get("end_month")),
        "invoice_date": _normalize_invoice_date(billing.get("invoice_date")),
        "one_time": billing.get("one_time", False),
        "main_service": {
            "description": main_service.get("description"),
            "unit": unit,
            "unit_price": main_service.get("unit_price"),
        },
        "additional_services": _normalize_additional_services(
            raw_value.get("additional_services", [])
        ),
        "archive_directory": archive.get("directory"),
    }
    if file_path is not None:
        customer["_file_path"] = file_path
    return customer


def _normalize_additional_services(services) -> list[dict]:
    """Uebersetzt Zusatzservices in das interne Format."""
    if not isinstance(services, list):
        raise ValueError("additional_services muss eine Liste sein.")
    result = []
    for index, service in enumerate(services, start=1):
        if not isinstance(service, dict):
            raise ValueError(f"additional_services #{index} muss eine Map sein.")
        reject_unknown_keys(
            service,
            {"description", "unit", "unit_price"},
            f"additional_services[{index}]",
        )
        unit = service.get("unit", "flat")
        if unit not in ("flat", "month", "included"):
            raise ValueError(
                f"additional_services #{index}.unit muss flat, month oder included sein."
            )
        price = None if unit == "included" else service.get("unit_price")
        if unit != "included" and not isinstance(price, str):
            raise ValueError(
                f"additional_services #{index}.unit_price muss als Text "
                "in Anfuehrungszeichen stehen."
            )
        result.append(
            {
                "description": service.get("description"),
                "unit_price": price,
                "unit": unit,
            }
        )
    return result


def _map(config: dict, name: str, optional: bool = False) -> dict:
    """Liefert einen YAML-Unterbereich als Map."""
    value = config.get(name, {}) if optional else config.get(name)
    if not isinstance(value, dict):
        raise ValueError(f"{name} muss eine Map sein.")
    return value


def _normalize_month(value) -> str | None:
    """Normalisiert einen optionalen Abrechnungs-Endmonat."""
    return None if value in (None, "") else str(value)


def _normalize_invoice_date(value) -> str | None:
    """Uebersetzt ein optionales ISO-Datum ins interne deutsche Format."""
    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        value = value.date()
    if isinstance(value, date):
        return value.strftime("%d.%m.%Y")
    text = str(value)
    for format_string in ("%Y-%m-%d", "%d.%m.%Y"):
        try:
            return datetime.strptime(text, format_string).strftime("%d.%m.%Y")
        except ValueError:
            continue
    raise ValueError("billing.invoice_date muss dem Format JJJJ-MM-TT entsprechen.")


def customer_to_yaml(customer: dict) -> dict:
    """Uebersetzt das interne Kundenmodell in das editierbare YAML-Schema."""
    additional_services = []
    for service in customer.get("additional_services", []):
        included = service.get("unit") == "included"
        entry = {
            "description": service.get("description"),
            "unit": "included" if included else service.get("unit", "flat"),
        }
        if not included:
            entry["unit_price"] = str(service.get("unit_price"))
        additional_services.append(entry)

    return {
        "id": customer["id"],
        "active": customer.get("active", True),
        "contact": {
            "name": customer.get("name"),
            "company": customer.get("company"),
            "email": customer.get("email"),
            "cc": customer.get("cc", []),
            "street": customer.get("street"),
            "postal_code": str(customer.get("postal_code", "")),
            "city": customer.get("city"),
            "website": customer.get("website"),
        },
        "billing": {
            "invoice_prefix": customer.get("invoice_prefix") or None,
            "cycle_months": customer.get("cycle_months", 1),
            "due_days": customer.get("due_days", 14),
            "end_month": customer.get("end_month") or None,
            "invoice_date": _invoice_date_to_iso(customer.get("invoice_date")),
            "one_time": customer.get("one_time", False),
        },
        "main_service": {
            "description": customer["main_service"].get("description"),
            "unit": customer["main_service"].get("unit", "month"),
            "unit_price": str(customer["main_service"].get("unit_price")),
        },
        "additional_services": additional_services,
        "archive": {"directory": customer.get("archive_directory") or None},
    }


def _invoice_date_to_iso(value) -> str | None:
    """Uebersetzt ein internes Rechnungsdatum ins YAML-ISO-Format."""
    if not value:
        return None
    return datetime.strptime(str(value), "%d.%m.%Y").strftime("%Y-%m-%d")


def save_customer_file(customer: dict, file_path: Path) -> None:
    """Schreibt eine einzelne Kundendatei atomar als YAML."""
    yaml_data = customer_to_yaml(customer)
    validate_customer_entry(normalize_customer(yaml_data))
    file_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = None
    try:
        with tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-8",
            dir=file_path.parent,
            prefix=f".{file_path.name}.",
            suffix=".tmp",
            delete=False,
        ) as temporary_file:
            temporary_path = Path(temporary_file.name)
            yaml.safe_dump(
                yaml_data,
                temporary_file,
                allow_unicode=True,
                sort_keys=False,
            )
            temporary_file.flush()
            os.fsync(temporary_file.fileno())
        os.replace(temporary_path, file_path)
    finally:
        if temporary_path and temporary_path.exists():
            temporary_path.unlink()
