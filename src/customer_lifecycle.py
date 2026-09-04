from datetime import date, datetime

from customer_files import save_customer_file


def should_deactivate_customer(entry: dict, today: date | datetime) -> bool:
    """Prueft, ob ein Kunde nach der aktuellen Rechnung entfernt werden kann."""
    if entry.get("one_time") is True:
        return True

    if entry.get("end_month"):
        try:
            letzte_erlaubte = datetime.strptime(entry["end_month"], "%Y-%m")
            return (today.year, today.month) >= (
                letzte_erlaubte.year,
                letzte_erlaubte.month,
            )
        except ValueError:
            return False

    return False


def remove_customer_from_data(data: list, entry: dict) -> list:
    """Entfernt einen Kunden anhand von Firma und Name aus der Datenliste."""
    return [
        customer
        for customer in data
        if not (
            customer.get("company", "").strip().lower()
            == entry["company"].strip().lower()
            and customer.get("name", "").strip().lower()
            == entry["name"].strip().lower()
        )
    ]


def save_customer_data(entry: dict) -> None:
    """Schreibt einen geladenen Kunden atomar in seine YAML-Datei."""
    file_path = entry.get("_file_path")
    if file_path is None:
        raise ValueError("Quellpfad der Kundendatei fehlt.")
    save_customer_file(entry, file_path)
