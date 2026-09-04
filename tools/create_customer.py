import re
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
CUSTOMERS_DIR = BASE_DIR / "customers"
DEFAULT_CUSTOMERS_PATH = CUSTOMERS_DIR
SRC_DIR = BASE_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from validation import (  # noqa: E402
    normalize_email_list,
    validate_amount,
    validate_date,
    validate_unit,
    validate_customer_entry,
    validate_month,
    validate_nonnegative_integer,
    validate_positive_integer,
)
from customer_files import load_customer_files, save_customer_file  # noqa: E402


def load_customer_data(file_name: Path = DEFAULT_CUSTOMERS_PATH) -> list:
    """Laedt die bestehenden einzelnen YAML-Kundendateien."""
    if not file_name.exists():
        return []
    return load_customer_files(file_name)


def ask_value(prompt: str, optional: bool = True) -> str | None:
    """Fragt einen Textwert ab und validiert Pflichtfelder."""
    while True:
        input_value = input(prompt).strip()
        if input_value:
            return input_value
        if optional:
            return None
        print("Dieses Feld darf nicht leer sein.")


def ask_validated(prompt: str, validator, optional: bool = False):
    """Fragt einen Wert ab, bis die uebergebene Validierung erfolgreich ist."""
    while True:
        value = ask_value(prompt, optional=optional)
        if value is None:
            return None
        try:
            validator(value)
            return value
        except ValueError as err:
            print(f"Ungueltige Eingabe: {err}")


def ask_additional_services(default_unit: str = "month") -> list | None:
    """Fragt optionale Zusatzservices fuer einen Kunden ab."""
    services = []
    while True:
        description = ask_value(
            "Zusaetzliche Leistung - Beschreibung (leer zum Beenden): "
        )
        if not description:
            break

        price = ask_validated(
            "Preis (z. B. 9,99 oder Inklusive): ",
            lambda value: validate_amount(
                value,
                "Preis",
                included_allowed=True,
            ),
        )
        included = str(price).strip().lower() == "inklusive"
        services.append(
            {
                "description": description,
                "unit": "included" if included else default_unit,
                "unit_price": None if included else price,
            }
        )

        again = input("Weitere Leistung hinzufuegen? (j/n): ").strip().lower()
        if again != "j":
            break

    return services or None


def new_customer() -> dict:
    """Fragt interaktiv einen neuen Kundeneintrag ab."""
    print("\nNeuen Kunden anlegen:\n")

    customer = {
        "name": ask_value("Name oder Ansprechpartner: ", optional=False),
        "company": ask_value("Firma: ", optional=False),
        "email": ask_value("E-Mail: ", optional=False),
        "street": ask_value("Strasse und Hausnummer: ", optional=False),
        "postal_code": ask_value("PLZ: ", optional=False),
        "city": ask_value("Ort: ", optional=False),
        "website": ask_value("Webseite (optional, nur bei Hosting relevant): "),
    }
    suggested_id = _create_customer_id(customer["company"])
    customer_id = ask_value(f"Kunden-ID (Standard: {suggested_id}): ") or suggested_id
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", customer_id):
        raise ValueError(
            "Kunden-ID darf nur Kleinbuchstaben, Zahlen und Bindestriche enthalten."
        )
    customer["id"] = customer_id
    cc_addresses = ask_email_cc()
    if cc_addresses:
        customer["cc"] = cc_addresses

    one_time = (
        input(
            "Soll diese Rechnung nur einmalig erstellt werden? Standard: nein (y/n): "
        )
        .strip()
        .lower()
        == "y"
    )
    if one_time:
        customer["one_time"] = True

    customer["main_service"] = _ask_main_service(one_time)
    _ask_optional_fields(customer, one_time)

    services = ask_additional_services(customer["main_service"]["unit"])
    if services:
        customer["additional_services"] = services

    active_input = input("Soll dieser Kunde ab jetzt aktiv sein? (y/n): ")
    if active_input.strip().lower() == "n":
        customer["active"] = False

    return customer


def ask_email_cc() -> list[str]:
    """Fragt optionale CC-Empfaenger fuer einen Kundeneintrag ab."""
    cc_addresses = []
    while True:
        cc = ask_value("CC-E-Mail (optional, leer zum Fortfahren): ")
        if not cc:
            return cc_addresses
        try:
            cc_addresses.extend(normalize_email_list(cc, "CC-E-Mail"))
        except ValueError as err:
            print(f"Ungueltige Eingabe: {err}")


def _ask_main_service(one_time: bool) -> dict:
    """Fragt die Hauptleistung fuer einen Kundeneintrag ab."""
    print("\nHauptleistung eintragen:")
    description = ask_value("Beschreibung der Hauptleistung: ", optional=False)
    amount = ask_validated(
        "Betrag (z. B. 49,99): ",
        lambda value: validate_amount(value, "Betrag"),
    )

    if one_time:
        unit = "flat"
    else:
        unit = ask_validated(
            "Einheit der Abrechnung (month, hour, flat - Standard: month): ",
            validate_unit,
            optional=True,
        )
        unit = unit or "month"

    return {
        "description": description,
        "unit": unit.strip().lower(),
        "unit_price": amount,
    }


def _ask_optional_fields(customer: dict, one_time: bool) -> None:
    """Ergaenzt optionale Kundenfelder."""
    if not one_time:
        cycle = ask_validated(
            "Abrechnungszyklus in Monaten (Standard: 1): ",
            lambda value: validate_positive_integer(value, "Abrechnungszyklus"),
            optional=True,
        )
        if cycle:
            customer["cycle_months"] = int(cycle)

    optional_fields = {
        "invoice_prefix": ("Rechnungsnummer-Praefix (optional): ", None),
        "invoice_date": (
            "Rechnungsdatum (z. B. 01.05.2026, optional): ",
            validate_date,
        ),
        "due_days": (
            "Faelligkeit in Tagen (z. B. 14, optional): ",
            lambda value: validate_nonnegative_integer(value, "Faelligkeit"),
        ),
        "archive_directory": ("Archiv-Pfad fuer PDF: ", None),
    }

    if not one_time:
        optional_fields["end_month"] = (
            "Letzte zu erstellende Rechnung (YYYY-MM, optional): ",
            validate_month,
        )

    for key, (prompt, validator) in optional_fields.items():
        if validator:
            value = ask_validated(prompt, validator, optional=True)
        else:
            value = ask_value(prompt)
        if value:
            customer[key] = value


def save_data(customer: dict, file_path: Path = DEFAULT_CUSTOMERS_PATH) -> None:
    """Speichert einen neuen Kunden in einer eigenen YAML-Datei."""
    validate_customer_entry(customer)
    target_path = file_path / f"{customer['id']}.yaml"
    if target_path.exists():
        raise FileExistsError(f"Kundendatei existiert bereits: {target_path}")
    save_customer_file(customer, target_path)
    print(f"\nKunde gespeichert in {target_path.resolve()}.")


def _create_customer_id(company: str) -> str:
    """Erzeugt einen einfachen stabilen ID-Vorschlag aus dem Firmennamen."""
    text = company.lower().replace("ä", "ae").replace("ö", "oe").replace("ü", "ue")
    text = text.replace("ß", "ss")
    return re.sub(r"[^a-z0-9]+", "-", text).strip("-") or "customer"


def main() -> None:
    """Startet die interaktive Kundenerfassung."""
    while True:
        save_data(new_customer())
        again = input("\nWeitere Kunden anlegen? (y/n): ").strip().lower()
        if again != "y":
            print("\nVorgang beendet.")
            break


if __name__ == "__main__":
    main()
