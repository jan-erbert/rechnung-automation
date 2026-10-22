"""Prueft Kundenpflege ausschliesslich mit erfundenen temporaeren Dateien."""

from datetime import date
import json

import pytest

from customer_changes import next_billing_month, resolve_customer_for_period
from customer_files import customer_to_yaml, load_customer_files, normalize_customer
from customer_management import create_customer, get_customer, update_customer
from run_lock import RunLock


def document():
    """Erstellt einen erfundenen Kunden ohne produktive Daten."""
    return {
        "id": "fixture",
        "contact": {
            "name": "Fixture",
            "company": "Fixture Company",
            "email": "invoice@example.invalid",
            "cc": [],
            "street": "Fixture Road 1",
            "postal_code": "12345",
            "city": "Fixture",
        },
        "billing": {"cycle_months": 1, "due_days": 14},
        "main_service": {
            "description": "Hosting",
            "unit": "month",
            "unit_price": "50.00",
        },
        "additional_services": [],
    }


def create(tmp_path):
    """Legt nur einen temporaeren Verwaltungskunden an."""
    return create_customer(tmp_path / "customers", tmp_path / "state", document())


def update(tmp_path, revision, changes, **kwargs):
    """Speichert nur eine temporaere Kundenaenderung."""
    return update_customer(
        tmp_path / "customers",
        tmp_path / "state",
        "fixture",
        changes,
        revision,
        today=date(2026, 10, 22),
        **kwargs,
    )


def completed_history(tmp_path, cycle=1):
    """Schreibt ausschliesslich eine erfundene abgeschlossene Periode."""
    path = tmp_path / "state/invoice-history-2026.json"
    path.write_text(
        json.dumps(
            [
                {
                    "id": "fixture__2026-10",
                    "customer_id": "fixture",
                    "year": 2026,
                    "month": 10,
                    "cycle_months": cycle,
                    "status": "sent",
                    "amount": "50.00",
                }
            ]
        )
    )
    return path


def rate(customer, period):
    """Liest nur den aufgeloesten Stundensatz oder Monatspreis."""
    return resolve_customer_for_period(customer, period)["main_service"]["unit_price"]


def test_future_price_preserves_current_price_and_old_history(tmp_path):
    """Neue Preise greifen kuenftig, vorhandene Rechnungsdaten bleiben gleich."""
    created = create(tmp_path)
    history = completed_history(tmp_path)
    before = history.read_bytes()
    updated = update(
        tmp_path, created["revision"], {"main_service": {"unit_price": "60.00"}}
    )
    assert history.read_bytes() == before
    customer = load_customer_files(tmp_path / "customers")[0]
    assert rate(customer, "2026-10") == "50.00"
    assert rate(customer, "2026-11") == "60.00"
    planned = updated["customer"]["scheduled_changes"][0]
    assert planned["effective_from"] == "2026-11"
    assert updated["customer"]["main_service"]["unit_price"] == "50.00"


def test_completed_quarter_cannot_be_changed_mid_period(tmp_path):
    """Eine vorausbezahlte Quartalsperiode endet vor der neuen Kondition."""
    raw = document()
    raw["billing"]["cycle_months"] = 3
    created = create_customer(tmp_path / "customers", tmp_path / "state", raw)
    completed_history(tmp_path, cycle=3)
    with pytest.raises(ValueError, match="2027-01"):
        update(
            tmp_path,
            created["revision"],
            {"billing": {"cycle_months": 1}},
            effective_from="2026-11",
        )
    updated = update(tmp_path, created["revision"], {"billing": {"cycle_months": 1}})
    assert updated["customer"]["scheduled_changes"][0]["effective_from"] == "2027-01"


def test_contact_change_is_immediate_and_does_not_add_invoice_state(tmp_path):
    """Eine neue Mailadresse betrifft den naechsten Versand ohne Rechnungsstart."""
    created = create(tmp_path)
    updated = update(
        tmp_path, created["revision"], {"contact": {"email": "new@example.invalid"}}
    )
    assert updated["customer"]["contact"]["email"] == "new@example.invalid"
    assert "scheduled_changes" not in updated["customer"]
    assert sorted(p.name for p in (tmp_path / "state").iterdir()) == [
        ".invoice-run.lock",
    ]


def test_stale_form_is_rejected(tmp_path):
    """Zwei Browserformulare koennen einander nicht still ueberschreiben."""
    created = create(tmp_path)
    update(tmp_path, created["revision"], {"contact": {"city": "New City"}})
    with pytest.raises(ValueError, match="inzwischen"):
        update(tmp_path, created["revision"], {"contact": {"city": "Lost Update"}})


def test_duplicate_and_outside_domain_are_rejected(tmp_path):
    """Anlage ueberschreibt keine Kunden und beachtet optionale Mailgrenzen."""
    create(tmp_path)
    with pytest.raises(ValueError, match="bereits"):
        create_customer(tmp_path / "customers", tmp_path / "state", document())
    with pytest.raises(ValueError, match="Maildomains"):
        create_customer(
            tmp_path / "customers", tmp_path / "state", document(), ["allowed.invalid"]
        )


def test_invalid_or_past_conditions_do_not_change_file(tmp_path):
    """Ungueltige Preise und rueckwirkende Aenderungen werden vor Speicherung erkannt."""
    created = create(tmp_path)
    path = tmp_path / "customers/fixture.yaml"
    before = path.read_bytes()
    cases = [
        ({"main_service": {"unit_price": "-1"}}, None),
        ({"main_service": {"unit_price": "60"}}, "2026-10"),
    ]
    for changes, effective in cases:
        with pytest.raises(ValueError):
            update(tmp_path, created["revision"], changes, effective_from=effective)
        assert path.read_bytes() == before


def test_same_lock_prevents_management_during_invoice_run(tmp_path):
    """Kundenpflege und Rechnungslauf verwenden dieselbe exklusive Sperre."""
    created = create(tmp_path)
    with RunLock(tmp_path / "state/.invoice-run.lock"):
        with pytest.raises(RuntimeError, match="weiterer Rechnungslauf"):
            update(tmp_path, created["revision"], {"active": False})


def test_lifecycle_save_preserves_baseline_and_future_changes(tmp_path):
    """Ein aufgeloester und deaktivierter Kunde behaelt seine alten Konditionen."""
    created = create(tmp_path)
    update(tmp_path, created["revision"], {"main_service": {"unit_price": "60.00"}})
    customer = load_customer_files(tmp_path / "customers")[0]
    future = resolve_customer_for_period(customer, "2026-11")
    future["active"] = False
    exported = customer_to_yaml(future)
    assert exported["active"] is False
    assert exported["main_service"]["unit_price"] == "50.00"
    restored = normalize_customer(exported)
    assert rate(restored, "2026-10") == "50.00"
    assert rate(future, "2026-10") == "50.00"


def test_changed_billing_kind_requires_separate_migration(tmp_path):
    """Ein Wechsel zwischen Stunden- und Vorausabrechnung wird nicht still geplant."""
    created = create(tmp_path)
    with pytest.raises(ValueError, match="Abrechnungsart"):
        update(tmp_path, created["revision"], {"main_service": {"unit": "hour"}})


def test_versioned_input_rejects_duplicate_or_unsorted_months():
    """Ein manipuliertes YAML kann keine widerspruechlichen Konditionen einschleusen."""
    raw = document()
    raw["scheduled_changes"] = [
        {
            "effective_from": "2026-12",
            "changes": {"main_service": {"unit_price": "60"}},
        },
        {
            "effective_from": "2026-11",
            "changes": {"main_service": {"unit_price": "70"}},
        },
    ]
    with pytest.raises(ValueError, match="aufsteigend"):
        normalize_customer(raw)


def test_new_year_without_history_chooses_next_month():
    """Der Standardwechsel nach Dezember ist der Januar des Folgejahres."""
    next_month = next_billing_month(
        normalize_customer(document()), [], date(2026, 12, 31)
    )
    assert next_month == "2027-01"


def test_read_customer_returns_current_revision(tmp_path):
    """Der Verwaltungsabruf liefert die unveraenderte Dateiversion."""
    created = create(tmp_path)
    loaded = get_customer(tmp_path / "customers", "fixture")
    assert loaded["revision"] == created["revision"]


def test_explicit_month_must_fit_existing_quarter(tmp_path):
    """Ein Februar darf keine neue Januar-Quartalsrechnung unterbrechen."""
    raw = document()
    raw["billing"]["cycle_months"] = 3
    created = create_customer(tmp_path / "customers", tmp_path / "state", raw)
    completed_history(tmp_path, cycle=3)
    with pytest.raises(ValueError, match="Zyklusgrenze"):
        update(
            tmp_path,
            created["revision"],
            {"billing": {"cycle_months": 1}},
            effective_from="2027-02",
        )


def test_quarter_without_history_uses_next_full_boundary(tmp_path):
    """Auch ohne Historie wird eine begonnene Vorausperiode nicht aufgeteilt."""
    raw = document()
    raw["billing"]["cycle_months"] = 3
    created = create_customer(tmp_path / "customers", tmp_path / "state", raw)
    updated = update(
        tmp_path, created["revision"], {"main_service": {"unit_price": "60.00"}}
    )
    assert updated["customer"]["scheduled_changes"][0]["effective_from"] == "2027-01"


def test_hourly_future_price_uses_service_month_before_next_invoice(tmp_path):
    """Ein neuer November-Stundensatz darf erst Novemberleistungen betreffen."""
    raw = document()
    raw["main_service"]["unit"] = "hour"
    raw["billing"]["cycle_months"] = 3
    created = create_customer(tmp_path / "customers", tmp_path / "state", raw)
    completed_history(tmp_path, cycle=3)
    updated = update(
        tmp_path, created["revision"], {"main_service": {"unit_price": "60.00"}}
    )
    assert updated["customer"]["scheduled_changes"][0]["effective_from"] == "2026-11"
    customer = load_customer_files(tmp_path / "customers")[0]
    assert rate(customer, "2026-10") == "50.00"


def test_create_preview_does_not_create_any_directory(tmp_path):
    """Eine Anlagevorschau validiert ohne Lock-, Kunden- oder Zustandsdateien."""
    result = create_customer(
        tmp_path / "customers", tmp_path / "state", document(), apply=False
    )
    assert result["saved"] is False
    assert result["revision"] is None
    assert list(tmp_path.iterdir()) == []


def test_update_preview_preserves_original_file_and_revision(tmp_path):
    """Die Vorschau verwendet dieselben Pruefungen ohne Speicherung."""
    created = create(tmp_path)
    original = (tmp_path / "customers/fixture.yaml").read_bytes()
    result = update(
        tmp_path,
        created["revision"],
        {"main_service": {"unit_price": "60.00"}},
        apply=False,
    )
    assert result["saved"] is False
    assert result["revision"] == created["revision"]
    assert result["customer"]["scheduled_changes"][0]["effective_from"] == "2026-11"
    assert (tmp_path / "customers/fixture.yaml").read_bytes() == original


def test_hourly_cycle_change_is_rejected_before_storage(tmp_path):
    """Die Verwaltung verlangt bei Stunden-Zykluswechsel eine eigene Periodenpruefung."""
    raw = document()
    raw["main_service"]["unit"] = "hour"
    created = create_customer(tmp_path / "customers", tmp_path / "state", raw)
    original = (tmp_path / "customers/fixture.yaml").read_bytes()
    with pytest.raises(ValueError, match="Stunden-Abrechnungszyklus"):
        update(tmp_path, created["revision"], {"billing": {"cycle_months": 3}})
    assert (tmp_path / "customers/fixture.yaml").read_bytes() == original
