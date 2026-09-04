from datetime import datetime
from decimal import Decimal, InvalidOperation
from email.utils import parseaddr

SUPPORTED_UNITS = ("month", "hour", "flat")
CENT = Decimal("0.01")


def validate_amount(
    value,
    field: str = "Betrag",
    included_allowed: bool = False,
) -> Decimal | None:
    """Prueft einen positiven Geldbetrag oder den Wert Inklusive."""
    text = str(value).strip() if value is not None else ""
    if included_allowed and (value is None or text.lower() == "inklusive"):
        return None

    try:
        amount = Decimal(text.replace(",", "."))
    except InvalidOperation as err:
        suffix = " oder 'Inklusive'" if included_allowed else ""
        raise ValueError(f"{field} muss ein positiver Betrag{suffix} sein.") from err

    if not amount.is_finite() or amount <= 0:
        raise ValueError(f"{field} muss groesser als 0 sein.")
    if amount.quantize(CENT) != amount:
        raise ValueError(f"{field} darf hoechstens zwei Nachkommastellen haben.")

    return amount.quantize(CENT)


def validate_percentage(value, field: str = "Prozentsatz") -> Decimal:
    """Prueft einen Dezimal-Prozentsatz zwischen 0 und 100."""
    text = str(value).strip() if value is not None else ""
    try:
        percentage = Decimal(text.replace(",", "."))
    except InvalidOperation as err:
        raise ValueError(f"{field} muss eine Dezimalzahl sein.") from err
    if not percentage.is_finite() or not Decimal("0") <= percentage <= Decimal("100"):
        raise ValueError(f"{field} muss zwischen 0 und 100 liegen.")
    return percentage


def validate_positive_integer(value, field: str) -> int:
    """Prueft eine positive Ganzzahl."""
    number = _parse_integer(value, field)
    if number < 1:
        raise ValueError(f"{field} muss mindestens 1 sein.")
    return number


def validate_nonnegative_integer(value, field: str) -> int:
    """Prueft eine nichtnegative Ganzzahl."""
    number = _parse_integer(value, field)
    if number < 0:
        raise ValueError(f"{field} darf nicht negativ sein.")
    return number


def validate_date(value, field: str = "Rechnungsdatum") -> str:
    """Prueft ein Datum im Format TT.MM.JJJJ."""
    return _validate_date_format(value, "%d.%m.%Y", field, "TT.MM.JJJJ")


def validate_month(value, field: str = "Letzte Rechnung") -> str:
    """Prueft einen Monat im Format JJJJ-MM."""
    return _validate_date_format(value, "%Y-%m", field, "JJJJ-MM")


def validate_unit(value) -> str:
    """Prueft die unterstuetzte Abrechnungseinheit."""
    unit = str(value).strip().lower() if value is not None else ""
    if unit not in SUPPORTED_UNITS:
        allowed_values = ", ".join(SUPPORTED_UNITS)
        raise ValueError(
            "main_service.unit muss einer dieser Werte sein: " f"{allowed_values}."
        )
    return unit


def normalize_email_list(value, field: str = "E-Mail") -> list[str]:
    """Prueft und normalisiert eine optionale Mailadresse oder Mailadressliste."""
    if value in (None, ""):
        return []

    if isinstance(value, str):
        addresses = [value]
    elif isinstance(value, list):
        addresses = value
    else:
        raise ValueError(f"{field} muss eine Mailadresse oder eine Liste sein.")

    normalized_addresses = []
    for index, address in enumerate(addresses, start=1):
        if not isinstance(address, str) or not address.strip():
            raise ValueError(f"{field} #{index} muss eine Mailadresse sein.")
        normalized_addresses.append(_validate_email_address(address.strip(), field))

    return normalized_addresses


def validate_customer_entry(entry: dict) -> None:
    """Prueft abrechnungsrelevante Werte eines Kundeneintrags."""
    if not isinstance(entry, dict):
        raise ValueError("Kundeneintrag muss ein Objekt sein.")

    if not isinstance(entry.get("active", True), bool):
        raise ValueError("active muss true oder false sein.")
    if not isinstance(entry.get("one_time", False), bool):
        raise ValueError("billing.one_time muss true oder false sein.")

    main_service = entry.get("main_service")
    if not isinstance(main_service, dict):
        raise ValueError("Hauptleistung fehlt oder ist ungueltig.")

    validate_unit(main_service.get("unit", "month"))
    validate_amount(main_service.get("unit_price"), "main_service.unit_price")
    validate_positive_integer(
        entry.get("cycle_months", 1),
        "Abrechnungszyklus",
    )
    if not isinstance(entry.get("email"), str):
        raise ValueError("email muss eine Mailadresse sein.")
    normalize_email_list(entry.get("email"), "email")
    normalize_email_list(entry.get("cc"), "cc")

    if entry.get("due_days") not in (None, ""):
        validate_nonnegative_integer(entry["due_days"], "Faelligkeit")
    if entry.get("invoice_date"):
        validate_date(entry["invoice_date"])
    if entry.get("end_month"):
        validate_month(entry["end_month"])

    additional_services = entry.get("additional_services", [])
    if additional_services is None:
        additional_services = []
    if not isinstance(additional_services, list):
        raise ValueError("Weitere Leistungen muessen eine Liste sein.")

    for index, service in enumerate(additional_services, start=1):
        if not isinstance(service, dict):
            raise ValueError(f"Weitere Leistung #{index} muss ein Objekt sein.")
        if (
            not isinstance(service.get("description"), str)
            or not service["description"].strip()
        ):
            raise ValueError(f"Weitere Leistung #{index}.description fehlt.")
        validate_amount(
            service.get("unit_price"),
            f"additional_services #{index}.unit_price",
            included_allowed=service.get("unit") == "included",
        )


def _parse_integer(value, field: str) -> int:
    """Wandelt einen Wert kontrolliert in eine Ganzzahl um."""
    if isinstance(value, bool):
        raise ValueError(f"{field} muss eine ganze Zahl sein.")

    text = str(value).strip() if value is not None else ""
    if text.startswith("+"):
        text = text[1:]
    if not text or not text.lstrip("-").isdigit():
        raise ValueError(f"{field} muss eine ganze Zahl sein.")
    return int(text)


def _validate_email_address(address: str, field: str) -> str:
    """Prueft eine einfache Mailadresse mit der Standardbibliothek."""
    name, parsed = parseaddr(address)
    if name or parsed != address or "@" not in parsed:
        raise ValueError(f"{field} enthaelt eine ungueltige Mailadresse.")
    local_part, domain = parsed.rsplit("@", 1)
    if not local_part or "." not in domain or domain.startswith("."):
        raise ValueError(f"{field} enthaelt eine ungueltige Mailadresse.")
    return parsed


def _validate_date_format(
    value,
    format_string: str,
    field: str,
    format_name: str,
) -> str:
    """Prueft und normalisiert ein festes Datumsformat."""
    text = str(value).strip() if value is not None else ""
    try:
        parsed_date = datetime.strptime(text, format_string)
    except ValueError as err:
        raise ValueError(f"{field} muss dem Format {format_name} entsprechen.") from err

    if parsed_date.strftime(format_string) != text:
        raise ValueError(f"{field} muss dem Format {format_name} entsprechen.")
    return text
