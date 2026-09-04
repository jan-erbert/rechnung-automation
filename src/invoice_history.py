import json
import os
import tempfile
from datetime import date, datetime
from pathlib import Path

from time_utils import now

STATUS_PENDING = "pending"
STATUS_SENT = "sent"
STATUS_FAILED = "failed"
STATUS_WAITING_HOURS = "waiting_hours"
STATUS_NO_INVOICE = "no_invoice"
VALID_STATUSES = {
    STATUS_PENDING,
    STATUS_SENT,
    STATUS_FAILED,
    STATUS_WAITING_HOURS,
    STATUS_NO_INVOICE,
}


def load_history_file(path: Path, year: int | None = None) -> list[dict]:
    """Laedt und validiert eine Rechnungsverlaufsdatei."""
    if not path.exists():
        return []
    try:
        with path.open("r", encoding="utf-8") as history_file:
            history = json.load(history_file)
    except json.JSONDecodeError as err:
        raise ValueError(
            f"Verlaufsdatei '{path.name}' enthaelt ungueltiges JSON."
        ) from err
    validate_history(history, year=year, source=path.name)
    return history


def load_all_history(
    data_dir: Path,
) -> tuple[list[dict], dict[int, tuple[Path, list[dict]]]]:
    """Laedt alle vorhandenen englischen Verlaufsdateien."""
    combined = []
    by_year = {}
    for path in sorted(data_dir.glob("invoice-history-*.json")):
        suffix = path.stem.removeprefix("invoice-history-")
        if not suffix.isdigit() or len(suffix) != 4:
            raise ValueError(f"Ungueltiger Verlaufsdateiname: '{path.name}'.")
        year = int(suffix)
        entries = load_history_file(path, year)
        by_year[year] = (path, entries)
        combined.extend(entries)
    validate_history(combined, source="alle Verlaufsdateien")
    return combined, by_year


def validate_history(history, year: int | None = None, source: str = "Verlauf") -> None:
    """Prueft Struktur und eindeutige IDs eines Rechnungsverlaufs."""
    if not isinstance(history, list):
        raise ValueError(f"{source}: Oberste JSON-Struktur muss eine Liste sein.")
    seen_ids = set()
    for index, entry in enumerate(history, start=1):
        if not isinstance(entry, dict):
            raise ValueError(f"{source}: Eintrag #{index} muss ein Objekt sein.")
        entry_id = entry.get("id")
        if not isinstance(entry_id, str) or not entry_id.strip():
            raise ValueError(f"{source}: Eintrag #{index} hat keine gueltige id.")
        if entry_id in seen_ids:
            raise ValueError(f"{source}: Doppelte Verlaufs-ID '{entry_id}'.")
        seen_ids.add(entry_id)
        customer_id = entry.get("customer_id")
        if not isinstance(customer_id, str) or not customer_id.strip():
            raise ValueError(
                f"{source}: Eintrag '{entry_id}' hat keine gueltige customer_id."
            )
        entry_year = entry.get("year")
        month = entry.get("month")
        if not isinstance(entry_year, int) or year is not None and entry_year != year:
            raise ValueError(
                f"{source}: Eintrag '{entry_id}' hat ein ungueltiges year."
            )
        if not isinstance(month, int) or not 1 <= month <= 12:
            raise ValueError(
                f"{source}: Eintrag '{entry_id}' hat ein ungueltiges month."
            )
        status = entry.get("status", STATUS_SENT)
        if status not in VALID_STATUSES:
            raise ValueError(f"{source}: Eintrag '{entry_id}' hat Status '{status}'.")


def build_history_entry(
    customer: dict,
    current_date: date | datetime,
    invoice_number: str,
    invoice_date: str,
    amount: str,
    cycle_months: int | None = None,
    status: str | None = None,
    service_period: str | None = None,
    hours_info: dict | None = None,
) -> dict:
    """Baut einen Eintrag fuer den Rechnungsverlauf."""
    customer_id = customer["id"]
    entry = {
        "customer_id": customer_id,
        "company": customer["company"],
        "name": customer["name"],
        "month": current_date.month,
        "year": current_date.year,
        "invoice_number": invoice_number,
        "invoice_date": invoice_date,
        "amount": amount,
        "id": f"{customer_id}__{current_date:%Y-%m}",
    }
    if cycle_months is not None:
        entry["cycle_months"] = cycle_months
    if status is not None:
        entry["status"] = status
        entry["status_updated_at"] = now().isoformat(timespec="seconds")
    if service_period:
        entry["service_period"] = service_period
    if hours_info is not None:
        entry["hours"] = format(hours_info["hours"], "f")
        entry["hourly_rate"] = format(hours_info["hourly_rate"], "f")
    return entry


def save_history(path: Path, history: list[dict]) -> None:
    """Schreibt den Rechnungsverlauf atomar als JSON-Datei."""
    validate_history(history, source=path.name)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = None
    try:
        with tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as temporary_file:
            temporary_path = Path(temporary_file.name)
            json.dump(history, temporary_file, indent=2, ensure_ascii=False)
            temporary_file.write("\n")
            temporary_file.flush()
            os.fsync(temporary_file.fileno())
        os.replace(temporary_path, path)
    finally:
        if temporary_path and temporary_path.exists():
            temporary_path.unlink()


def save_or_replace_history_entry(path: Path, history: list[dict], entry: dict) -> None:
    """Speichert einen Verlaufseintrag anhand seiner ID atomar."""
    updated = [item for item in history if item.get("id") != entry["id"]]
    updated.append(entry)
    save_history(path, updated)
    history[:] = updated


def set_delivery_status(
    path: Path, history: list[dict], invoice_id: str, status: str
) -> None:
    """Aktualisiert den Versandstatus eines Verlaufseintrags atomar."""
    if status not in VALID_STATUSES:
        raise ValueError(f"Ungueltiger Versandstatus: '{status}'.")
    updated = [entry.copy() for entry in history]
    for entry in updated:
        if entry.get("id") == invoice_id:
            entry["status"] = status
            entry["status_updated_at"] = now().isoformat(timespec="seconds")
            save_history(path, updated)
            history[:] = updated
            return
    raise ValueError(f"Verlaufseintrag '{invoice_id}' wurde nicht gefunden.")


def is_successfully_sent(entry: dict) -> bool:
    """Prueft den Versandstatus mit Rueckwaertskompatibilitaet."""
    return entry.get("status", STATUS_SENT) == STATUS_SENT


def is_billing_complete(entry: dict) -> bool:
    """Prueft, ob ein Abrechnungszeitpunkt abschliessend verarbeitet wurde."""
    return entry.get("status", STATUS_SENT) in (STATUS_SENT, STATUS_NO_INVOICE)


def close_expired_hours_waiting_entries(
    path: Path, history: list[dict], current_date: date | datetime
) -> int:
    """Schliesst alte Nullstunden-Wartezustaende ohne Rechnung ab."""
    updated = [entry.copy() for entry in history]
    closed = 0
    for entry in updated:
        if entry.get("status") != STATUS_WAITING_HOURS:
            continue
        if (entry["year"], entry["month"]) >= (current_date.year, current_date.month):
            continue
        entry["status"] = STATUS_NO_INVOICE
        entry["status_updated_at"] = now().isoformat(timespec="seconds")
        closed += 1
    if closed:
        save_history(path, updated)
        history[:] = updated
    return closed
