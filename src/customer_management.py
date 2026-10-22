"""Verwaltet Kunden ohne Rechnungserzeugung und mit gemeinsamer Lauf-Sperre."""

from contextlib import nullcontext
from copy import deepcopy
from datetime import date
import hashlib
from pathlib import Path

from customer_changes import (
    CONDITION_FIELDS,
    merge_document,
    month_key,
    next_change_month,
    normalize_scheduled_changes,
    validate_change_boundary,
    validate_hourly_cycle_change,
)
from customer_files import (
    CUSTOMER_ID_PATTERN,
    customer_to_yaml,
    load_customer_files,
    normalize_customer,
    save_customer_file,
)
from invoice_history import load_all_history
from run_lock import RunLock
from strict_yaml import reject_unknown_keys
from time_utils import now, today as current_date
from validation import normalize_email_list, validate_customer_entry


def customer_revision(path: Path) -> str:
    """Erkennt konkurrierende Bearbeitungen anhand der Dateipruefsumme."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_managed_customers(customers_dir: Path) -> list[dict]:
    """Schliesst fremde Symlinkziele vor dem Lesen von Verwaltungsdaten aus."""
    for pattern in ("*.yaml", "*.yml"):
        for path in customers_dir.glob(pattern):
            if not path.resolve().is_relative_to(customers_dir.resolve()):
                raise ValueError("Kundendatei verlaesst das Kundenverzeichnis.")
    return load_customer_files(customers_dir)


def _find_customer(customers_dir: Path, customer_id: str) -> dict:
    """Findet einen Kunden ausschliesslich innerhalb des freigegebenen Ordners."""
    if not isinstance(customer_id, str) or not CUSTOMER_ID_PATTERN.fullmatch(
        customer_id
    ):
        raise ValueError("Ungueltige Kunden-ID.")
    for customer in _load_managed_customers(customers_dir):
        if customer["id"] == customer_id:
            if not customer["_file_path"].resolve().is_relative_to(
                customers_dir.resolve()
            ):
                raise ValueError("Kundendatei verlaesst das Kundenverzeichnis.")
            return customer
    raise ValueError("Kunden-ID wurde nicht gefunden.")


def _check_recipients(customer: dict, allowed_domains: list[str] | None) -> None:
    """Prueft optionale Empfaengergrenzen vor dem Speichern."""
    if allowed_domains is None:
        return
    domains = {value.lower() for value in allowed_domains}
    recipients = normalize_email_list(customer["email"], "email")
    recipients += normalize_email_list(customer.get("cc", []), "cc")
    if any(address.rsplit("@", 1)[1].lower() not in domains for address in recipients):
        raise ValueError("Empfaenger liegt ausserhalb der freigegebenen Maildomains.")


def _result(customer: dict) -> dict:
    """Liefert editierbare Daten mit einer Versionskennung fuer das Formular."""
    return {
        "customer": customer_to_yaml(customer),
        "revision": customer_revision(customer["_file_path"]),
    }


def list_customers(customers_dir: Path) -> list[dict]:
    """Liest Kunden fuer die Verwaltung, ohne einen Rechnungslauf zu starten."""
    return [_result(customer) for customer in _load_managed_customers(customers_dir)]


def get_customer(customers_dir: Path, customer_id: str) -> dict:
    """Liest genau einen Kunden und dessen aktuelle Formularversion."""
    return _result(_find_customer(customers_dir, customer_id))


def create_customer(
    customers_dir: Path,
    data_dir: Path,
    document: dict,
    allowed_domains: list[str] | None = None,
    apply: bool = True,
) -> dict:
    """Validiert oder speichert einen Kunden ohne Rechnung oder Versand."""
    customer = normalize_customer(document)
    validate_customer_entry(customer)
    _check_recipients(customer, allowed_domains)
    if document.get("scheduled_changes") or document.get("change_history"):
        raise ValueError("Neue Kunden brauchen keine vorgegebene Aenderungshistorie.")
    if apply:
        customers_dir.mkdir(parents=True, exist_ok=True)
    lock = RunLock(data_dir / ".invoice-run.lock") if apply else nullcontext()
    with lock:
        existing = (
            _load_managed_customers(customers_dir) if customers_dir.exists() else []
        )
        if any(item["id"] == customer["id"] for item in existing):
            raise ValueError("Kunden-ID ist bereits vorhanden.")
        path = customers_dir / f"{customer['id']}.yaml"
        if path.exists() or path.is_symlink():
            raise ValueError("Zieldatei ist bereits vorhanden.")
        if not apply:
            return {"customer": customer_to_yaml(customer), "revision": None, "saved": False}
        customer["_change_history"] = [
            {
                "at": now().isoformat(timespec="seconds"),
                "action": "create",
            }
        ]
        save_customer_file(customer, path)
        customer["_file_path"] = path
        return {**_result(customer), "saved": True}


def update_customer(
    customers_dir: Path,
    data_dir: Path,
    customer_id: str,
    changes: dict,
    expected_revision: str,
    effective_from: str | None = None,
    today: date | None = None,
    allowed_domains: list[str] | None = None,
    apply: bool = True,
) -> dict:
    """Prueft oder speichert Kontakt und kuenftige Konditionen ohne Rechnungsstart."""
    if not isinstance(changes, dict) or not changes:
        raise ValueError("Mindestens eine Kundenaenderung ist erforderlich.")
    reject_unknown_keys(
        changes, {"contact", "active", *CONDITION_FIELDS}, "Kundenaenderung"
    )
    today = today or current_date()
    lock = RunLock(data_dir / ".invoice-run.lock") if apply else nullcontext()
    with lock:
        customer = _find_customer(customers_dir, customer_id)
        path = customer["_file_path"]
        if customer_revision(path) != expected_revision:
            raise ValueError("Kunde wurde inzwischen geaendert; Formular neu laden.")
        before = customer_to_yaml(customer)
        document = deepcopy(before)
        immediate = {
            key: value for key, value in changes.items() if key not in CONDITION_FIELDS
        }
        document = merge_document(document, immediate)
        conditions = {
            key: value for key, value in changes.items() if key in CONDITION_FIELDS
        }
        effective = None
        if conditions:
            validate_hourly_cycle_change(document, conditions)
            history, _ = load_all_history(data_dir)
            minimum = next_change_month(customer, history, today, conditions)
            effective = month_key(effective_from) if effective_from else minimum
            if effective < minimum:
                raise ValueError(
                    "Konditionsaenderungen sind erst ab dem naechsten "
                    f"Abrechnungszeitraum {minimum} erlaubt."
                )
            validate_change_boundary(customer, history, effective, today, conditions)
            scheduled = deepcopy(document.get("scheduled_changes", []))
            same_month = next(
                (item for item in scheduled if item["effective_from"] == effective),
                None,
            )
            if same_month:
                same_month["changes"] = merge_document(same_month["changes"], conditions)
            else:
                scheduled.append({"effective_from": effective, "changes": conditions})
                scheduled.sort(key=lambda item: item["effective_from"])
            document["scheduled_changes"] = normalize_scheduled_changes(
                scheduled, document
            )
        elif effective_from is not None:
            raise ValueError("Kontaktpflege hat keinen Konditionsmonat.")
        updated = normalize_customer(document, path)
        validate_customer_entry(updated)
        _check_recipients(updated, allowed_domains)
        if not apply:
            return {**_result(updated), "saved": False}
        updated.setdefault("_change_history", []).append(
            {
                "at": now().isoformat(timespec="seconds"),
                "action": "update",
                "effective_from": effective,
                "changes": deepcopy(changes),
            }
        )
        save_customer_file(updated, path)
        return {**_result(updated), "saved": True}
