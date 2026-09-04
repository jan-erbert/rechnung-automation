import json

from customer_files import load_customer_files, save_customer_file
from invoice_history import load_history_file
from legacy_migration import convert_legacy_customers, migrate_legacy_layout


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
    assert (data_dir / "daten.json").is_file()
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
