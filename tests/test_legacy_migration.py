import json
from decimal import Decimal

import pytest

from customer_files import load_customer_files, save_customer_file
from hours_files import write_hours_month
from invoice_history import load_history_file, save_history
from legacy_migration import convert_legacy_customers, migrate_legacy_layout
from paths import create_paths


def _customer(customer_id: str, company: str) -> dict:
    """Erstellt einen minimalen gueltigen Kunden fuer Migrationstests."""
    return {
        "id": customer_id,
        "active": True,
        "name": "Erika Beispiel",
        "company": company,
        "email": "erika@example.com",
        "cc": [],
        "street": "Beispielweg 1",
        "postal_code": "01234",
        "city": "Beispielstadt",
        "website": None,
        "invoice_prefix": "",
        "cycle_months": 1,
        "due_days": 14,
        "end_month": None,
        "invoice_date": None,
        "one_time": False,
        "main_service": {
            "description": "Hosting",
            "unit": "month",
            "unit_price": "10.00",
        },
        "additional_services": [],
        "archive_directory": None,
    }


def test_startup_migration_is_complete_and_idempotent(tmp_path):
    """Der Start migriert alte Daten einmalig und behaelt die Quellen."""
    data_dir = tmp_path / "data"
    hours_dir = tmp_path / "hours"
    templates_dir = tmp_path / "templates"
    data_dir.mkdir()
    hours_dir.mkdir()
    templates_dir.mkdir()
    legacy_customer = {
        "name": "Erika Beispiel",
        "firma": "Beispiel GmbH",
        "email": "erika@example.com",
        "strasse": "Beispielweg 1",
        "plz": "01234",
        "ort": "Beispielstadt",
        "hauptleistung": {
            "beschreibung": "Hosting",
            "einheit": "monat",
            "betrag": "10.00",
        },
    }
    legacy_invoice = {
        "absender": {
            "name": "Max Beispiel",
            "firma": "Beispiel GmbH",
            "strasse": "Beispielweg 2",
            "plz": "01234",
            "ort": "Beispielstadt",
            "telefon": "0123",
            "email": "max@example.com",
        },
        "bank": {
            "bankname": "Beispielbank",
            "kontoinhaber": "Max Beispiel",
            "iban": "DE123",
            "bic": "TESTDE00",
        },
        "finanzen": {
            "steuer_id_typ": "steuernummer",
            "steuernummer": "12/345",
            "kleinunternehmer": True,
        },
    }
    (data_dir / "daten.json").write_text(
        json.dumps([legacy_customer]), encoding="utf-8"
    )
    (data_dir / "konfiguration.json").write_text(
        json.dumps(legacy_invoice), encoding="utf-8"
    )
    (data_dir / "verlauf-2024.json").write_text(
        json.dumps(
            [
                {
                    "id": "beispiel-gmbh__2024-01",
                    "firma": "Beispiel GmbH",
                    "name": "Erika Beispiel",
                    "jahr": 2024,
                    "monat": 1,
                    "rechnungsnummer": "01-2024",
                    "rechnungsdatum": "01.01.2024",
                    "betrag": "10.00",
                }
            ]
        ),
        encoding="utf-8",
    )
    (hours_dir / "stunden_2026_01.json").write_text(
        json.dumps([{"firma": "Beispiel GmbH", "stunden": 2.5}]),
        encoding="utf-8",
    )
    (templates_dir / "mail_template.html").write_text(
        "{{ absender.firma }} {{ rechnungsnummer }}", encoding="utf-8"
    )
    (templates_dir / "rechnung_template.html").write_text(
        "{% for eintrag in leistungen %}{{ eintrag.beschreibung }}{% endfor %}",
        encoding="utf-8",
    )

    actions = migrate_legacy_layout(tmp_path)

    assert actions
    customer = load_customer_files(tmp_path / "customers")[0]
    assert customer["id"] == "beispiel-gmbh"
    history = load_history_file(data_dir / "invoice-history-2024.json", 2024)
    assert history[0]["customer_id"] == customer["id"]
    assert history[0]["invoice_number"] == "01-2024"
    assert (hours_dir / "2026-01.yaml").is_file()
    assert "sender.company" in (templates_dir / "email_template.html").read_text(
        encoding="utf-8"
    )
    assert "item.description" in (templates_dir / "invoice_template.html").read_text(
        encoding="utf-8"
    )
    assert (data_dir / "daten.json").is_file()

    customer["active"] = False
    save_customer_file(customer, tmp_path / "customers/beispiel-gmbh.yaml")
    history[0]["status"] = "sent"
    save_history(data_dir / "invoice-history-2024.json", history)
    write_hours_month(
        hours_dir / "2026-01.yaml",
        "2026-01",
        {"beispiel-gmbh": Decimal("3.00")},
        replace_existing=True,
    )
    (templates_dir / "email_template.html").write_text(
        "{{ sender.company }} - angepasst", encoding="utf-8"
    )

    assert migrate_legacy_layout(tmp_path) == []


def test_startup_migration_resumes_partial_customer_conversion(tmp_path):
    """Eine unterbrochene Kundenmigration erzeugt sicher die fehlenden Dateien."""
    data_dir = tmp_path / "data"
    customers_dir = tmp_path / "customers"
    data_dir.mkdir()
    customers_dir.mkdir()
    legacy_customers = [
        {
            "name": "Erika Beispiel",
            "firma": "Erste Firma",
            "email": "erika@example.com",
            "strasse": "Beispielweg 1",
            "plz": "01234",
            "ort": "Beispielstadt",
            "hauptleistung": {
                "beschreibung": "Hosting",
                "einheit": "monat",
                "betrag": "10.00",
            },
        },
        {
            "name": "Max Beispiel",
            "firma": "Zweite Firma",
            "email": "max@example.com",
            "strasse": "Beispielweg 2",
            "plz": "01234",
            "ort": "Beispielstadt",
            "hauptleistung": {
                "beschreibung": "Wartung",
                "einheit": "monat",
                "betrag": "20.00",
            },
        },
    ]
    (data_dir / "daten.json").write_text(json.dumps(legacy_customers), encoding="utf-8")
    converted = convert_legacy_customers(legacy_customers)
    first = converted[0]
    save_customer_file(first, customers_dir / f"{first['id']}.yaml")

    actions = migrate_legacy_layout(tmp_path)

    assert actions == ["daten.json -> customers/*.yaml"]
    assert {customer["id"] for customer in load_customer_files(customers_dir)} == {
        "erste-firma",
        "zweite-firma",
    }


def test_migration_uses_resolved_project_paths(tmp_path):
    """Legacy-Daten werden in konfigurierten Verzeichnissen gesucht und migriert."""
    custom_data = tmp_path / "state"
    custom_customers = tmp_path / "accounts"
    custom_hours = tmp_path / "worklogs"
    custom_templates = tmp_path / "views"
    custom_config = tmp_path / "private" / "billing.yaml"
    for directory in (custom_data, custom_customers, custom_hours, custom_templates):
        directory.mkdir(parents=True)
    save_customer_file(
        _customer("example", "Example GmbH"), custom_customers / "example.yaml"
    )
    (custom_data / "verlauf-2025.json").write_text(
        json.dumps(
            [
                {
                    "id": "example__2025-01",
                    "firma": "Example GmbH",
                    "name": "Erika Beispiel",
                    "jahr": 2025,
                    "monat": 1,
                }
            ]
        ),
        encoding="utf-8",
    )
    paths = create_paths(
        {
            "paths": {
                "data_dir": str(custom_data),
                "customers_dir": str(custom_customers),
                "invoice_config": str(custom_config),
                "hours_dir": str(custom_hours),
                "templates_dir": str(custom_templates),
            }
        },
        tmp_path,
    )

    actions = migrate_legacy_layout(tmp_path, paths)

    assert "verlauf-2025.json -> invoice-history-2025.json" in actions
    assert (custom_data / "invoice-history-2025.json").is_file()
    assert not (tmp_path / "data" / "invoice-history-2025.json").exists()


def test_retained_history_and_hours_may_be_unchanged_subsets(tmp_path):
    """Neue und fachlich aktualisierte Zielwerte duerfen bestehen bleiben."""
    data_dir = tmp_path / "data"
    customers_dir = tmp_path / "customers"
    hours_dir = tmp_path / "hours"
    templates_dir = tmp_path / "templates"
    for directory in (data_dir, customers_dir, hours_dir, templates_dir):
        directory.mkdir()
    save_customer_file(
        _customer("legacy", "Legacy GmbH"), customers_dir / "legacy.yaml"
    )
    save_customer_file(_customer("new", "Neue GmbH"), customers_dir / "new.yaml")
    legacy_history = {
        "id": "legacy__2025-01",
        "kunden_id": "legacy",
        "firma": "Legacy GmbH",
        "name": "Erika Beispiel",
        "jahr": 2025,
        "monat": 1,
    }
    (data_dir / "verlauf-2025.json").write_text(
        json.dumps([legacy_history]), encoding="utf-8"
    )
    (data_dir / "invoice-history-2025.json").write_text(
        json.dumps(
            [
                {
                    "id": "legacy__2025-01",
                    "customer_id": "legacy",
                    "company": "Legacy GmbH",
                    "name": "Erika Beispiel",
                    "year": 2025,
                    "month": 1,
                    "status": "sent",
                },
                {
                    "id": "new__2025-02",
                    "customer_id": "new",
                    "company": "Neue GmbH",
                    "name": "Erika Beispiel",
                    "year": 2025,
                    "month": 2,
                },
            ]
        ),
        encoding="utf-8",
    )
    (hours_dir / "stunden_2025_01.json").write_text(
        json.dumps([{"firma": "Legacy GmbH", "stunden": 2.5}]), encoding="utf-8"
    )
    write_hours_month(
        hours_dir / "2025-01.yaml",
        "2025-01",
        {"legacy": Decimal("4.00"), "new": Decimal("3.00")},
    )

    assert migrate_legacy_layout(tmp_path) == []


def test_duplicate_customer_companies_are_rejected(tmp_path):
    """Mehrdeutige Firmenzuordnungen stoppen die Migration."""
    customers_dir = tmp_path / "customers"
    hours_dir = tmp_path / "hours"
    customers_dir.mkdir()
    hours_dir.mkdir()
    save_customer_file(_customer("first", "Gleiche GmbH"), customers_dir / "first.yaml")
    save_customer_file(
        _customer("second", "Gleiche GmbH"), customers_dir / "second.yaml"
    )
    (hours_dir / "stunden_2025_01.json").write_text("[]", encoding="utf-8")

    with pytest.raises(ValueError, match="nicht eindeutig"):
        migrate_legacy_layout(tmp_path)


def test_duplicate_companies_without_legacy_mapping_are_allowed(tmp_path):
    """Normale Kundendaten duerfen dieselbe Firma mit stabilen IDs verwenden."""
    customers_dir = tmp_path / "customers"
    customers_dir.mkdir()
    save_customer_file(_customer("first", "Gleiche GmbH"), customers_dir / "first.yaml")
    save_customer_file(
        _customer("second", "Gleiche GmbH"), customers_dir / "second.yaml"
    )

    assert migrate_legacy_layout(tmp_path) == []


def test_duplicate_legacy_hours_are_rejected(tmp_path):
    """Doppelte Stunden derselben Firma werden nicht still ueberschrieben."""
    customers_dir = tmp_path / "customers"
    hours_dir = tmp_path / "hours"
    customers_dir.mkdir()
    hours_dir.mkdir()
    save_customer_file(
        _customer("example", "Example GmbH"), customers_dir / "example.yaml"
    )
    (hours_dir / "stunden_2025_01.json").write_text(
        json.dumps(
            [
                {"firma": "Example GmbH", "stunden": 1},
                {"firma": "Example GmbH", "stunden": 2},
            ]
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="Doppelte Stunden"):
        migrate_legacy_layout(tmp_path)

    assert not (hours_dir / "2025-01.yaml").exists()


def test_unknown_legacy_customer_id_is_resolved_by_unique_company(tmp_path):
    """Eine alte ID wird kontrolliert ueber die eindeutige Firma ersetzt."""
    data_dir = tmp_path / "data"
    customers_dir = tmp_path / "customers"
    data_dir.mkdir()
    customers_dir.mkdir()
    save_customer_file(
        _customer("example", "Example GmbH"), customers_dir / "example.yaml"
    )
    (data_dir / "verlauf-2025.json").write_text(
        json.dumps(
            [
                {
                    "id": "alte-id__2025-01",
                    "kunden_id": "alte-id",
                    "firma": "Example GmbH",
                    "name": "Erika Beispiel",
                    "jahr": 2025,
                    "monat": 1,
                }
            ]
        ),
        encoding="utf-8",
    )

    migrate_legacy_layout(tmp_path)

    history = load_history_file(data_dir / "invoice-history-2025.json", 2025)
    assert history[0]["customer_id"] == "example"


def test_unknown_legacy_customer_id_without_match_is_rejected(tmp_path):
    """Nicht zuordenbare alte IDs erzeugen einen kontrollierten Fehler."""
    data_dir = tmp_path / "data"
    customers_dir = tmp_path / "customers"
    data_dir.mkdir()
    customers_dir.mkdir()
    save_customer_file(
        _customer("example", "Example GmbH"), customers_dir / "example.yaml"
    )
    (data_dir / "verlauf-2025.json").write_text(
        json.dumps(
            [
                {
                    "id": "unknown__2025-01",
                    "kunden_id": "unknown",
                    "firma": "Unbekannt GmbH",
                    "name": "Erika Beispiel",
                    "jahr": 2025,
                    "monat": 1,
                }
            ]
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="keinem Kunden zugeordnet"):
        migrate_legacy_layout(tmp_path)


def test_template_migration_changes_only_jinja_and_validates_syntax(tmp_path):
    """Sichtbarer Text bleibt erhalten und nur Jinja-Namen werden migriert."""
    customers_dir = tmp_path / "customers"
    templates_dir = tmp_path / "templates"
    customers_dir.mkdir()
    templates_dir.mkdir()
    save_customer_file(
        _customer("example", "Example GmbH"), customers_dir / "example.yaml"
    )
    visible_text = 'firma ort preis betrag und "firma" bleiben sichtbarer Inhalt'
    (templates_dir / "mail_template.html").write_text(
        visible_text + ' {{ absender.firma }} {{ betrag }} {{ "firma" }}',
        encoding="utf-8",
    )

    migrate_legacy_layout(tmp_path)

    migrated = (templates_dir / "email_template.html").read_text(encoding="utf-8")
    assert visible_text in migrated
    assert "{{ sender.company }}" in migrated
    assert "{{ net_amount }}" in migrated
    assert '{{ "firma" }}' in migrated

    (templates_dir / "rechnung_template.html").write_text(
        "{% if firma %}", encoding="utf-8"
    )
    with pytest.raises(ValueError, match="ungueltig"):
        migrate_legacy_layout(tmp_path)
    assert not (templates_dir / "invoice_template.html").exists()
