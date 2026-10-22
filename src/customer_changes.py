"""Loest geplante Kundenkonditionen fuer ihren jeweiligen Leistungsmonat auf."""

from copy import deepcopy
from datetime import date, datetime

from strict_yaml import reject_unknown_keys
from validation import validate_positive_integer

CONDITION_FIELDS = {"billing", "main_service", "additional_services"}
BILLING_FIELDS = {"cycle_months", "due_days", "end_month"}


def month_key(value: date | datetime | str) -> str:
    """Normalisiert einen Leistungsmonat im Format JJJJ-MM."""
    if isinstance(value, (date, datetime)):
        return value.strftime("%Y-%m")
    if not isinstance(value, str):
        raise ValueError("Leistungsmonat muss JJJJ-MM entsprechen.")
    try:
        parsed = datetime.strptime(value, "%Y-%m")
    except ValueError:
        raise ValueError("Leistungsmonat muss JJJJ-MM entsprechen.") from None
    if parsed.strftime("%Y-%m") != value:
        raise ValueError("Leistungsmonat muss JJJJ-MM entsprechen.")
    return value


def merge_document(document: dict, changes: dict) -> dict:
    """Verbindet Teilbereiche ohne die Ausgangsdaten zu veraendern."""
    result = deepcopy(document)
    for name, value in changes.items():
        if isinstance(value, dict) and isinstance(result.get(name), dict):
            result[name] = merge_document(result[name], value)
        else:
            result[name] = deepcopy(value)
    return result


def normalize_scheduled_changes(changes, base_document: dict) -> list[dict]:
    """Prueft geplante Konditionsaenderungen gegen das bestehende Kundenschema."""
    from customer_files import normalize_customer
    from validation import validate_customer_entry

    if not isinstance(changes, list):
        raise ValueError("scheduled_changes muss eine Liste sein.")
    result = []
    previous = None
    candidate = deepcopy(base_document)
    candidate.pop("scheduled_changes", None)
    candidate.pop("change_history", None)
    for item in changes:
        if not isinstance(item, dict):
            raise ValueError("scheduled_changes muss Objekte enthalten.")
        reject_unknown_keys(item, {"effective_from", "changes"}, "scheduled_changes")
        effective = month_key(item.get("effective_from"))
        if previous is not None and effective <= previous:
            raise ValueError("Geplante Aenderungen muessen eindeutig aufsteigend sein.")
        patch = item.get("changes")
        if not isinstance(patch, dict) or not patch:
            raise ValueError("Geplante Aenderung braucht mindestens eine Kondition.")
        reject_unknown_keys(patch, CONDITION_FIELDS, "scheduled_changes.changes")
        if "billing" in patch:
            if not isinstance(patch["billing"], dict):
                raise ValueError("Geplante billing-Aenderung muss ein Objekt sein.")
            reject_unknown_keys(
                patch["billing"], BILLING_FIELDS, "scheduled_changes.billing"
            )
        validate_hourly_cycle_change(candidate, patch)
        if "main_service" in patch and isinstance(patch["main_service"], dict):
            current_unit = candidate["main_service"].get("unit", "month")
            if patch["main_service"].get("unit", current_unit) != current_unit:
                raise ValueError(
                    "Wechsel der Abrechnungsart braucht eine eigene Freigabe."
                )
        candidate = merge_document(candidate, patch)
        validate_customer_entry(normalize_customer(candidate))
        result.append({"effective_from": effective, "changes": deepcopy(patch)})
        previous = effective
    return result


def validate_hourly_cycle_change(document: dict, changes: dict) -> None:
    """Verhindert ungeklaerte Periodenspruenge in der rueckwirkenden Stundenabrechnung."""
    billing = changes.get("billing", {})
    if not isinstance(billing, dict):
        raise ValueError("Geplante billing-Aenderung muss ein Objekt sein.")
    if document["main_service"].get("unit", "month") != "hour":
        return
    current_cycle = document.get("billing", {}).get("cycle_months", 1)
    changed_cycle = billing.get("cycle_months", current_cycle)
    if changed_cycle != current_cycle:
        raise ValueError(
            "Stunden-Abrechnungszyklus kann nicht automatisch geaendert werden; "
            "offene Leistungsmonate zuerst pruefen."
        )


def resolve_customer_for_period(customer: dict, period: date | str) -> dict:
    """Waehlt Konditionen nach Leistungsmonat statt nach Ausfuehrungsdatum."""
    from customer_files import customer_to_yaml, normalize_customer

    document = customer_to_yaml(customer)
    scheduled = document.pop("scheduled_changes", [])
    history = document.pop("change_history", [])
    target = month_key(period)
    applied = None
    for item in scheduled:
        if item["effective_from"] > target:
            break
        document = merge_document(document, item["changes"])
        applied = item["effective_from"]
    result = normalize_customer(document, customer.get("_file_path"))
    if scheduled:
        result["_scheduled_changes"] = deepcopy(scheduled)
    if history:
        result["_change_history"] = deepcopy(history)
    result["_base_customer_document"] = customer.get("_base_customer_document") or {
        key: deepcopy(value)
        for key, value in customer_to_yaml(customer).items()
        if key not in {"scheduled_changes", "change_history"}
    }
    result["_conditions_effective_from"] = applied
    return result


def next_billing_month(customer: dict, history: list[dict], today: date) -> str:
    """Ermittelt den naechsten zulaessigen Aenderungsmonat nach bestehendem Zyklus."""
    from invoice_history import is_billing_complete

    minimum = today.year * 12 + today.month
    completed = [
        item
        for item in history
        if item.get("customer_id") == customer["id"] and is_billing_complete(item)
    ]
    if completed:
        latest = max(completed, key=lambda item: (item["year"], item["month"]))
        cycle = validate_positive_integer(
            latest.get("cycle_months", customer.get("cycle_months", 1)),
            "Vorheriger Abrechnungszyklus",
        )
        next_index = latest["year"] * 12 + latest["month"] - 1 + cycle
        minimum = max(minimum, next_index)
    year, month = divmod(minimum, 12)
    return f"{year:04d}-{month + 1:02d}"


def _change_cycle(
    customer: dict, history: list[dict], effective: str, today: date, changes: dict
) -> tuple[int, int] | None:
    """Ermittelt den Anker einer vorgegebenen Abrechnungsgrenze."""
    from invoice_history import is_billing_complete

    is_hourly = customer["main_service"].get("unit") == "hour"
    cycle_change = "cycle_months" in changes.get("billing", {})
    if is_hourly and not cycle_change:
        return
    completed = [
        item
        for item in history
        if item.get("customer_id") == customer["id"] and is_billing_complete(item)
    ]
    latest = max(completed, key=lambda item: (item["year"], item["month"]), default=None)
    anchor = (
        latest["year"] * 12 + latest["month"] - 1
        if latest
        else today.year * 12 + today.month - 1
    )
    cycle = validate_positive_integer(
        (latest or {}).get("cycle_months", customer.get("cycle_months", 1)),
        "Vorheriger Abrechnungszyklus",
    )
    year, month = map(int, effective.split("-"))
    target = year * 12 + month - 1
    for item in customer.get("_scheduled_changes", []):
        item_year, item_month = map(int, item["effective_from"].split("-"))
        boundary = item_year * 12 + item_month - 1
        if anchor < boundary < target:
            new_cycle = item["changes"].get("billing", {}).get("cycle_months")
            if new_cycle:
                anchor = boundary
                cycle = int(new_cycle)
    return anchor, cycle


def validate_change_boundary(
    customer: dict, history: list[dict], effective: str, today: date, changes: dict
) -> None:
    """Verhindert Konditionswechsel innerhalb bereits begonnener Vorausperioden."""
    boundary = _change_cycle(customer, history, effective, today, changes)
    if boundary:
        anchor, cycle = boundary
        year, month = map(int, effective.split("-"))
        if (year * 12 + month - 1 - anchor) % cycle:
            raise ValueError("Konditionsmonat muss zur bestehenden Zyklusgrenze passen.")


def next_change_month(
    customer: dict, history: list[dict], today: date, changes: dict
) -> str:
    """Waehlt die naechste passende Grenze fuer zukuenftige Konditionen."""
    is_hourly = customer["main_service"].get("unit") == "hour"
    cycle_change = "cycle_months" in changes.get("billing", {})
    minimum = next_billing_month(
        customer, [] if is_hourly and not cycle_change else history, today
    )
    boundary = _change_cycle(customer, history, minimum, today, changes)
    if boundary is None:
        return minimum
    anchor, cycle = boundary
    year, month = map(int, minimum.split("-"))
    candidate = year * 12 + month - 1
    candidate += (-(candidate - anchor)) % cycle
    year, month = divmod(candidate, 12)
    return f"{year:04d}-{month + 1:02d}"
