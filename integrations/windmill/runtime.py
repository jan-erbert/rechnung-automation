"""Optionale Windmill-Einstiege fuer die gemeinsame Python-Anwendung."""

from pathlib import Path
import sys

PROJECT = Path(__file__).resolve().parents[2]
if str(PROJECT / "src") not in sys.path:
    sys.path.insert(0, str(PROJECT / "src"))

from customer_files import load_customer_files, normalize_customer  # noqa: E402
from customer_changes import resolve_customer_for_period  # noqa: E402
from time_utils import today  # noqa: E402
from customer_management import (  # noqa: E402
    create_customer,
    get_customer,
    list_customers,
    update_customer,
)
from main import run_application  # noqa: E402
from paths import create_paths  # noqa: E402
from settings_loader import load_settings  # noqa: E402
from integrations.windmill.configuration import load_smtp_resource  # noqa: E402


def project_paths():
    """Verwendet dieselben Einstellungen und Datenpfade wie der lokale Einstieg."""
    return create_paths(load_settings(), base_dir=PROJECT)


def validate_project() -> dict:
    """Prueft Kundenstruktur ohne SMTP-Abruf oder Rechnungserzeugung."""
    paths = project_paths()
    customers = load_customer_files(paths.customers_dir)
    return {"customers": len(customers), "validated": True}


def run(
    mode: str = "dry-run",
    smtp_resource: str = "f/rechnung/smtp",
    resource_loader=None,
    allowed_domains: list[str] | None = None,
) -> dict:
    """Fuehrt die gemeinsame Anwendung aus und gibt nur Laufzaehler zurueck."""
    if mode not in {"dry-run", "send"}:
        raise ValueError("Erlaubte Modi: dry-run und send.")
    smtp = (
        {
            "server": "localhost",
            "port": 1,
            "user": "dry-run@example.invalid",
            "password": "not-a-real-secret",
        }
        if mode == "dry-run"
        else load_smtp_resource(smtp_resource, resource_loader=resource_loader)
    )
    summary = {}
    code = run_application(
        "dry-run" if mode == "dry-run" else "non-interactive",
        mail_config=smtp,
        summary=summary,
        allowed_domains=allowed_domains,
    )
    if code:
        raise RuntimeError("Rechnungslauf fehlgeschlagen; Status und Log pruefen.")
    return {**summary, "exit_code": code}


def customers() -> list[dict]:
    """Liefert die private Kundenliste fuer berechtigte Verwaltungsformulare."""
    rows = []
    for record in list_customers(project_paths().customers_dir):
        customer = resolve_customer_for_period(
            normalize_customer(record["customer"]), today()
        )
        rows.append(
            {
                "id": customer["id"],
                "company": customer["company"],
                "email": customer["email"],
                "active": customer["active"],
                "unit_price": customer["main_service"]["unit_price"],
                "cycle_months": customer["cycle_months"],
                "revision": record["revision"],
            }
        )
    return rows


def new_customer(
    customer_id: str,
    company: str,
    contact_name: str,
    email: str,
    street: str,
    postal_code: str,
    city: str,
    description: str,
    unit_price: str,
    cycle_months: int = 1,
    unit: str = "month",
    cc: list[str] | None = None,
    apply: bool = False,
    allowed_domains: list[str] | None = None,
    archive_directory: str | None = None,
) -> dict:
    """Prueft oder speichert einen Kunden ohne Rechnungs- oder Mailausloesung."""
    paths = project_paths()
    document = {
        "id": customer_id,
        "active": True,
        "contact": {
            "name": contact_name,
            "company": company,
            "email": email,
            "cc": cc or [],
            "street": street,
            "postal_code": postal_code,
            "city": city,
        },
        "billing": {"cycle_months": cycle_months, "due_days": 14},
        "main_service": {
            "description": description,
            "unit": unit,
            "unit_price": unit_price,
        },
    }
    if archive_directory is not None:
        document["archive"] = {"directory": archive_directory}
    return create_customer(
        paths.customers_dir,
        paths.data_dir,
        document,
        allowed_domains=allowed_domains,
        apply=apply,
    )


def edit_customer(
    customer_id: str,
    expected_revision: str = "",
    email: str | None = None,
    unit_price: str | None = None,
    description: str | None = None,
    cycle_months: int | None = None,
    effective_from: str | None = None,
    cc: list[str] | None = None,
    active: bool | None = None,
    apply: bool = False,
    allowed_domains: list[str] | None = None,
    company: str | None = None,
    contact_name: str | None = None,
    street: str | None = None,
    postal_code: str | None = None,
    city: str | None = None,
) -> dict:
    """Plant Konditionen und aendert Kontakte mit Schutz gegen veraltete Formulare."""
    paths = project_paths()
    current = get_customer(paths.customers_dir, customer_id)
    if apply and not expected_revision:
        raise ValueError("Zuerst Vorschau ausfuehren und deren revision uebernehmen.")
    changes = {}
    contact = {
        "name": contact_name,
        "company": company,
        "email": email,
        "cc": cc,
        "street": street,
        "postal_code": postal_code,
        "city": city,
    }
    contact = {key: value for key, value in contact.items() if value is not None}
    if contact:
        changes["contact"] = contact
    if unit_price is not None or description is not None:
        changes["main_service"] = {}
        if unit_price is not None:
            changes["main_service"]["unit_price"] = unit_price
        if description is not None:
            changes["main_service"]["description"] = description
    if cycle_months is not None:
        changes["billing"] = {"cycle_months": cycle_months}
    if active is not None:
        changes["active"] = active
    return update_customer(
        paths.customers_dir,
        paths.data_dir,
        customer_id,
        changes,
        expected_revision=expected_revision or current["revision"],
        effective_from=effective_from,
        allowed_domains=allowed_domains,
        apply=apply,
    )
