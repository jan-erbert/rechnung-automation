import json
import logging
import os
import re
import tempfile
from pathlib import Path

import yaml
from jinja2 import Environment, TemplateSyntaxError

from configuration import load_invoice_config
from customer_files import load_customer_files, save_customer_file
from hours_files import (
    hours_file_path,
    load_hours_month,
    validate_hours_value,
    write_hours_month,
)
from invoice_history import load_history_file, save_history
from paths import ProjectPaths, create_paths

logger = logging.getLogger(__name__)

LEGACY_HISTORY_FIELDS = {
    "kunden_id": "customer_id",
    "firma": "company",
    "monat": "month",
    "jahr": "year",
    "rechnungsnummer": "invoice_number",
    "rechnungsdatum": "invoice_date",
    "betrag": "amount",
    "zyklus_monate": "cycle_months",
    "versandstatus": "status",
    "versandstatus_zeitpunkt": "status_updated_at",
    "leistungszeitraum": "service_period",
    "stunden": "hours",
    "stundensatz": "hourly_rate",
}
LEGACY_TEMPLATE_REPLACEMENTS = {
    "leistungen": "items",
    "leistung": "item",
    "eintrag": "item",
    "beschreibung": "description",
    "preis": "price",
    "abrechnungszeitraum": "billing_period",
    "abrechnungszyklus": "cycle_months",
    "absender": "sender",
    "finanzen": "tax",
    "kleinunternehmer": "small_business",
    "steuer_id_typ": "identifier_type",
    "ust_id": "vat_id",
    "steuernummer": "tax_number",
    "finanzamt": "tax_office",
    "firma": "company",
    "strasse": "street",
    "straße": "street",
    "plz": "postal_code",
    "ort": "city",
    "telefon": "phone",
    "bankname": "name",
    "kontoinhaber": "account_holder",
    "faelligkeit": "due_date",
    "betrag": "net_amount",
    "gesamtpreis": "formatted_total",
    "monat_jahr": "month_year",
    "mwst_hinweis": "vat_note",
    "mwst_prozent": "vat_rate",
    "brutto_betrag": "gross_amount",
    "netto_betrag": "net_amount",
    "rechnungsdatum": "invoice_date",
    "rechnungsnummer": "invoice_number",
    "steuerbetrag": "tax_amount",
    "muster_text": "sample_text",
    "stundensatz_hinweis": "hourly_rate_note",
    "gesamtprice": "formatted_total",
}


def migrate_legacy_layout(
    base_dir: Path, project_paths: ProjectPaths | None = None
) -> list[str]:
    """Migriert erkannte alte Dateistrukturen idempotent auf englische Ziele."""
    project_paths = project_paths or create_paths(base_dir=base_dir)
    actions = []
    data_dir = project_paths.data_dir
    customers_dir = project_paths.customers_dir
    invoice_path = project_paths.invoice_config
    legacy_customers = data_dir / "daten.json"
    legacy_config = data_dir / "konfiguration.json"

    if legacy_config.exists():
        config = convert_legacy_invoice_config(_load_json(legacy_config, dict))
        if invoice_path.exists():
            load_invoice_config(invoice_path)
        else:
            _write_yaml_exclusive(invoice_path, config)
            load_invoice_config(invoice_path)
            actions.append(
                f"{legacy_config.name} -> {_display_path(invoice_path, base_dir)}"
            )

    if legacy_customers.exists():
        customers = convert_legacy_customers(_load_json(legacy_customers, list))
        _create_company_index(customers, "Legacy-Kundendaten")
        expected_paths = {
            customers_dir / f"{customer['id']}.yaml": customer for customer in customers
        }
        missing_paths = [path for path in expected_paths if not path.exists()]
        for path, customer in expected_paths.items():
            if path.exists():
                continue
            save_customer_file(customer, path)
        if missing_paths:
            load_customer_files(customers_dir, strict=True)
            actions.append(f"{legacy_customers.name} -> customers/*.yaml")

    legacy_relations_exist = any(data_dir.glob("verlauf-*.json")) or any(
        project_paths.hours_dir.glob("stunden_*.json")
    )
    customer_index = (
        _create_company_index(load_customer_files(customers_dir), "Kundendateien")
        if legacy_relations_exist
        else {}
    )
    actions.extend(_migrate_history(data_dir, customer_index))
    actions.extend(_migrate_hours(project_paths.hours_dir, customers_dir))
    actions.extend(_migrate_templates(project_paths.templates_dir))
    for action in actions:
        logger.info("Legacy-Migration: %s", action)
    return actions


def _display_path(path: Path, base_dir: Path) -> str:
    """Formatiert Projektpfade und externe Pfade fuer Statusmeldungen."""
    try:
        return str(path.relative_to(base_dir))
    except ValueError:
        return str(path)


def _create_company_index(customers: list[dict], source: str) -> dict[str, str]:
    """Erzeugt einen eindeutigen Firmenindex fuer Legacy-Zuordnungen."""
    company_index = {}
    for index, customer in enumerate(customers, start=1):
        company = str(customer.get("company", "")).strip().casefold()
        customer_id = customer.get("id")
        if not company:
            raise ValueError(f"{source}: Firma in Eintrag #{index} fehlt.")
        if company in company_index:
            raise ValueError(
                f"{source}: Firma '{customer.get('company')}' ist nicht eindeutig."
            )
        company_index[company] = customer_id
    return company_index


def _load_json(path: Path, expected_type: type):
    """Laedt eine alte JSON-Datei mit Typpruefung."""
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as err:
        raise ValueError(f"Legacy-Datei '{path}' enthaelt ungueltiges JSON.") from err
    if not isinstance(value, expected_type):
        raise ValueError(f"Legacy-Datei '{path}' hat einen ungueltigen Datentyp.")
    return value


def _create_customer_id(company: str, used: set[str]) -> str:
    """Erzeugt eine eindeutige, dateisichere Kunden-ID."""
    base = company.lower().translate(
        str.maketrans({"ä": "ae", "ö": "oe", "ü": "ue", "ß": "ss"})
    )
    base = re.sub(r"[^a-z0-9]+", "-", base).strip("-") or "customer"
    candidate = base
    number = 2
    while candidate in used:
        candidate = f"{base}-{number}"
        number += 1
    used.add(candidate)
    return candidate


def convert_legacy_customers(values: list[dict]) -> list[dict]:
    """Uebersetzt alte deutsche Kundeneintraege ins englische interne Modell."""
    customers = []
    used = set()
    unit_map = {"monat": "month", "stunde": "hour", "pauschal": "flat"}
    for index, value in enumerate(values, start=1):
        if not isinstance(value, dict):
            raise ValueError(f"Legacy-Kunde #{index} ist kein Objekt.")
        main = value.get("hauptleistung") or {}
        additional = []
        for item in (
            value.get("weitere_leistungen", value.get("weitere_services", [])) or []
        ):
            included = str(item.get("preis", "")).strip().lower() == "inklusive"
            additional.append(
                {
                    "description": item.get("beschreibung"),
                    "unit": (
                        "included"
                        if included
                        else unit_map.get(item.get("einheit"), "month")
                    ),
                    "unit_price": None if included else str(item.get("preis")),
                }
            )
        company = str(value.get("firma", ""))
        customers.append(
            {
                "id": _create_customer_id(company, used),
                "active": value.get("aktiv", True),
                "name": value.get("name"),
                "company": company,
                "email": value.get("email"),
                "cc": value.get("cc", []),
                "street": value.get("strasse", value.get("straße")),
                "postal_code": str(value.get("plz", "")),
                "city": value.get("ort"),
                "website": value.get("webseite"),
                "invoice_prefix": value.get("rechnungsnummer", ""),
                "cycle_months": value.get("abrechnungszyklus", 1),
                "due_days": value.get("faelligkeit", 14),
                "end_month": value.get("letzte_rechnung"),
                "invoice_date": value.get("rechnungsdatum"),
                "one_time": value.get("einmalig", False),
                "main_service": {
                    "description": main.get("beschreibung"),
                    "unit": unit_map.get(
                        str(main.get("einheit", "monat")).lower(), "month"
                    ),
                    "unit_price": str(main.get("betrag")),
                },
                "additional_services": additional,
                "archive_directory": value.get("archiv_pfad"),
            }
        )
    return customers


def convert_legacy_invoice_config(config: dict) -> dict:
    """Uebersetzt die alte deutsche Rechnungskonfiguration nach YAML."""
    sender = config.get("absender", {})
    bank = config.get("bank", {})
    tax = config.get("finanzen", {})
    identifier = {"steuernummer": "tax_number", "ust_id": "vat_id"}.get(
        tax.get("steuer_id_typ")
    )
    if not identifier:
        raise ValueError("Unbekannter steuer_id_typ in der Legacy-Konfiguration.")
    new_tax = {
        "identifier_type": identifier,
        identifier: tax.get(tax.get("steuer_id_typ")),
        "tax_office": tax.get("finanzamt", ""),
        "small_business": tax.get("kleinunternehmer"),
    }
    if not new_tax["small_business"]:
        new_tax["vat_rate"] = str(tax.get("mehrwertsteuer_prozent"))
    bcc = config.get("mail", {}).get("bcc")
    return {
        "sender": {
            "name": sender.get("name"),
            "company": sender.get("firma"),
            "street": sender.get("straße", sender.get("strasse", "")),
            "postal_code": str(sender.get("plz", "")),
            "city": sender.get("ort", ""),
            "phone": str(sender.get("telefon", "")),
            "email": sender.get("email"),
            "website": sender.get("website", ""),
        },
        "bank": {
            "name": bank.get("bankname", ""),
            "account_holder": bank.get("kontoinhaber"),
            "iban": bank.get("iban"),
            "bic": bank.get("bic", ""),
        },
        "tax": new_tax,
        "mail": {
            "bcc": [bcc] if isinstance(bcc, str) and bcc else bcc or [],
            "from_name": config.get("mail", {}).get("from_name") or None,
        },
    }


def _write_yaml_exclusive(path: Path, value: dict) -> None:
    """Schreibt eine neue YAML-Datei ohne bestehende Ziele zu ersetzen."""
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
        ) as yaml_file:
            temporary_path = Path(yaml_file.name)
            yaml.safe_dump(value, yaml_file, allow_unicode=True, sort_keys=False)
            yaml_file.flush()
            os.fsync(yaml_file.fileno())
        _publish_exclusive(temporary_path, path)
    finally:
        if temporary_path and temporary_path.exists():
            temporary_path.unlink()


def _migrate_history(data_dir: Path, customer_index: dict[str, str]) -> list[str]:
    """Migriert alte Verlaufsdateinamen und Felder nach Englisch."""
    actions = []
    for source in sorted(data_dir.glob("verlauf-*.json")):
        match = re.fullmatch(r"verlauf-(\d{4})\.json", source.name)
        if not match:
            continue
        target = data_dir / f"invoice-history-{match.group(1)}.json"
        converted = []
        known_customer_ids = set(customer_index.values())
        seen_entry_ids = set()
        for index, entry in enumerate(_load_json(source, list), start=1):
            if not isinstance(entry, dict):
                raise ValueError(f"{source.name}: Eintrag #{index} ist kein Objekt.")
            converted_entry = {
                LEGACY_HISTORY_FIELDS.get(key, key): item for key, item in entry.items()
            }
            entry_id = converted_entry.get("id")
            if entry_id in seen_entry_ids:
                raise ValueError(f"{source.name}: Doppelte Verlaufs-ID '{entry_id}'.")
            seen_entry_ids.add(entry_id)
            company = str(converted_entry.get("company", "")).strip().casefold()
            customer_id = converted_entry.get("customer_id")
            if customer_id not in known_customer_ids:
                resolved_id = customer_index.get(company)
                if not resolved_id:
                    raise ValueError(
                        f"{source.name}: customer_id in Eintrag #{index} kann "
                        "keinem Kunden zugeordnet werden."
                    )
                converted_entry["customer_id"] = resolved_id
            converted.append(converted_entry)
        if target.exists():
            existing = load_history_file(target, int(match.group(1)))
            _require_entry_keys(
                converted,
                existing,
                "id",
                f"Legacy-Verlauf '{source.name}'",
            )
            continue
        save_history(target, converted)
        load_history_file(target, int(match.group(1)))
        actions.append(f"{source.name} -> {target.name}")
    return actions


def _migrate_hours(hours_dir: Path, customers_dir: Path) -> list[str]:
    """Migriert alte Stunden-JSONs nach kunden-ID-basiertem YAML."""
    sources = sorted(hours_dir.glob("stunden_*.json"))
    if not sources:
        return []
    company_index = _create_company_index(
        load_customer_files(customers_dir), "Kundendateien"
    )
    actions = []
    for source in sources:
        match = re.fullmatch(r"stunden_(\d{4})_(\d{2})\.json", source.name)
        if not match:
            continue
        period = f"{match.group(1)}-{match.group(2)}"
        values = {}
        for index, entry in enumerate(_load_json(source, list), start=1):
            company = str(entry.get("firma", "")).strip().casefold()
            if company not in company_index:
                raise ValueError(
                    f"{source.name}: Firma in Eintrag #{index} ist unbekannt."
                )
            customer_id = company_index[company]
            if customer_id in values:
                raise ValueError(
                    f"{source.name}: Doppelte Stunden fuer Firma in Eintrag #{index}."
                )
            legacy_hours = entry.get("stunden")
            values[customer_id] = validate_hours_value(str(legacy_hours), "hours")
        target = hours_file_path(hours_dir, period)
        if target.exists():
            existing = load_hours_month(target, period)
            missing_ids = set(values) - set(existing)
            if missing_ids:
                raise ValueError(
                    f"Legacy-Stunden fehlen in '{target.name}' fuer: "
                    + ", ".join(sorted(missing_ids))
                )
            continue
        write_hours_month(target, period, values, replace_existing=False)
        actions.append(f"{source.name} -> {target.name}")
    return actions


def _migrate_templates(templates_dir: Path) -> list[str]:
    """Migriert alte technische Templatenamen und Jinja-Felder."""
    actions = []
    for old_name, new_name in (
        ("mail_template.html", "email_template.html"),
        ("rechnung_template.html", "invoice_template.html"),
    ):
        source = templates_dir / old_name
        target = templates_dir / new_name
        if not source.exists():
            continue
        content = source.read_text(encoding="utf-8")
        _validate_jinja_template(content, source.name)
        content = _replace_legacy_jinja_names(content)
        _validate_jinja_template(content, source.name)
        if target.exists():
            _validate_jinja_template(target.read_text(encoding="utf-8"), target.name)
            continue
        _write_text_exclusive(target, content)
        actions.append(f"{old_name} -> {new_name}")
    return actions


def _require_entry_keys(
    expected: list[dict], existing: list[dict], key: str, source: str
) -> None:
    """Prueft, ob alle Legacy-Identitaeten im aktuellen Ziel enthalten sind."""
    existing_keys = {entry.get(key) for entry in existing}
    for entry in expected:
        entry_key = entry.get(key)
        if entry_key not in existing_keys:
            raise ValueError(f"{source}: Eintrag '{entry_key}' fehlt im Ziel.")


def _replace_legacy_jinja_names(content: str) -> str:
    """Ersetzt alte Bezeichner ausschliesslich innerhalb von Jinja-Bloecken."""
    tokens = Environment().lex(content)
    return "".join(
        (
            LEGACY_TEMPLATE_REPLACEMENTS.get(value, value)
            if token_type == "name"
            else value
        )
        for _, token_type, value in tokens
    )


def _validate_jinja_template(content: str, source_name: str) -> None:
    """Prueft die Syntax eines migrierten Jinja-Templates."""
    try:
        Environment().parse(content)
    except TemplateSyntaxError as err:
        raise ValueError(
            f"Migriertes Legacy-Template '{source_name}' ist ungueltig: {err}"
        ) from err


def _write_text_exclusive(path: Path, content: str) -> None:
    """Schreibt eine Textdatei atomar, ohne vorhandene Ziele zu ersetzen."""
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
        ) as template_file:
            temporary_path = Path(template_file.name)
            template_file.write(content)
            template_file.flush()
            os.fsync(template_file.fileno())
        _publish_exclusive(temporary_path, path)
    finally:
        if temporary_path and temporary_path.exists():
            temporary_path.unlink()


def _publish_exclusive(temporary_path: Path, target: Path) -> None:
    """Veroeffentlicht eine Datei exklusiv mit portablem Hardlink-Fallback."""
    try:
        os.link(temporary_path, target)
        return
    except FileExistsError:
        raise
    except OSError:
        pass

    created = False
    try:
        descriptor = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        created = True
        with os.fdopen(descriptor, "wb") as target_file:
            target_file.write(temporary_path.read_bytes())
            target_file.flush()
            os.fsync(target_file.fileno())
    except Exception:
        if created:
            target.unlink(missing_ok=True)
        raise
