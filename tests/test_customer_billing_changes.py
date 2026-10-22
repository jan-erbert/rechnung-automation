"""Prueft Konditionsgrenzen mit fiktiven Stunden und ohne PDF oder Mailversand."""

from datetime import date
from decimal import Decimal
from types import SimpleNamespace

import pytest

from customer_changes import resolve_customer_for_period
from customer_files import normalize_customer
from hours_files import HoursFileError, write_hours_month
from invoice_history import build_history_entry
from services import build_service_items
import invoice_preview
import workflow


def customer(unit="month", cycle=1, effective="2026-11"):
    """Erstellt einen erfundenen Kunden mit einer geplanten Preiserhoehung."""
    return normalize_customer(
        {
            "id": "fixture",
            "contact": {
                "name": "Fixture",
                "company": "Fixture Company",
                "email": "fixture@example.invalid",
                "street": "Fixture Road 1",
                "postal_code": "12345",
                "city": "Fixture",
            },
            "billing": {"cycle_months": cycle, "due_days": 14},
            "main_service": {
                "description": "Fixture Service",
                "unit": unit,
                "unit_price": "50.00",
            },
            "scheduled_changes": [
                {
                    "effective_from": effective,
                    "changes": {"main_service": {"unit_price": "60.00"}},
                }
            ],
        }
    )


def write_hours(tmp_path, *periods):
    """Schreibt nur erfundene Stunden in temporaere Testdateien."""
    for period in periods:
        write_hours_month(
            tmp_path / f"{period}.yaml", period, {"fixture": Decimal("1.00")}
        )


def test_monthly_forward_price_changes_only_at_effective_month(tmp_path):
    """Oktober bleibt beim alten Preis, November nutzt die neue Vorausleistung."""
    entry = customer()
    october = build_service_items(
        resolve_customer_for_period(entry, "2026-10"),
        1,
        tmp_path,
        interactive=False,
        today=date(2026, 10, 22),
    )
    november = build_service_items(
        resolve_customer_for_period(entry, "2026-11"),
        1,
        tmp_path,
        interactive=False,
        today=date(2026, 11, 1),
    )
    assert october["total_amount"] == Decimal("50.00")
    assert november["total_amount"] == Decimal("60.00")


def test_hourly_price_uses_service_month_not_invoice_month(tmp_path):
    """Der Novemberlauf rechnet Oktober alt, der Dezemberlauf November neu ab."""
    entry = customer(unit="hour")
    write_hours(tmp_path, "2026-10", "2026-11")
    november = build_service_items(
        resolve_customer_for_period(entry, "2026-11"),
        1,
        tmp_path,
        interactive=False,
        today=date(2026, 11, 1),
    )
    december = build_service_items(
        resolve_customer_for_period(entry, "2026-12"),
        1,
        tmp_path,
        interactive=False,
        today=date(2026, 12, 1),
    )
    assert november["total_amount"] == Decimal("50.00")
    assert december["total_amount"] == Decimal("60.00")


def test_hourly_quarter_keeps_each_months_rate_in_items_and_history(tmp_path):
    """Ein Quartal mit Tarifwechsel summiert und dokumentiert jeden Leistungsmonat."""
    entry = customer(unit="hour", cycle=3)
    write_hours(tmp_path, "2026-10", "2026-11", "2026-12")
    effective = resolve_customer_for_period(entry, "2027-01")
    result = build_service_items(
        effective, 3, tmp_path, interactive=False, today=date(2027, 1, 1)
    )
    assert result["total_amount"] == Decimal("170.00")
    assert [item["price"] for item in result["items"]] == [
        "50,00 EUR",
        "60,00 EUR",
        "60,00 EUR",
    ]
    history = build_history_entry(
        effective,
        date(2027, 1, 1),
        "fixture-01-2027",
        "01.01.2027",
        "170.00",
        cycle_months=3,
        hours_info=result["hours_info"],
    )
    assert [item["rate"] for item in history["hourly_rates"]] == [
        "50.00",
        "60.00",
        "60.00",
    ]
    assert "hourly_rate" not in history


def test_monthly_quarter_does_not_trigger_new_invoice_before_boundary(
    tmp_path, monkeypatch
):
    """Ein geplanter Januarwechsel zieht keine neue Novemberrechnung vor."""
    entry = customer(cycle=3, effective="2027-01")
    entry["_scheduled_changes"][0]["changes"]["billing"] = {"cycle_months": 1}
    context = SimpleNamespace(
        history=[
            {
                "customer_id": "fixture",
                "year": 2026,
                "month": 10,
                "cycle_months": 3,
                "status": "sent",
            }
        ],
        previous_history=[],
    )
    monkeypatch.setattr("workflow.current_date", lambda: date(2026, 11, 1))
    monkeypatch.setattr("billing_schedule.current_date", lambda: date(2026, 11, 1))

    def unexpected_invoice(*args, **kwargs):
        """Verhindert jede Rechnungserzeugung im Test."""
        raise AssertionError("Keine neue Rechnung vor der Zyklusgrenze")

    monkeypatch.setattr("workflow._process_customer_entry", unexpected_invoice)
    assert workflow._process_customer_in_run([], entry, context) == "skipped"


def test_hourly_additional_service_change_stops_ambiguous_period(tmp_path):
    """Nicht unterstuetzte Zusatzleistungsmischungen werden nie still abgerechnet."""
    entry = customer(unit="hour", cycle=3)
    entry["_scheduled_changes"][0]["changes"]["additional_services"] = [
        {"description": "Support", "unit": "month", "unit_price": "5.00"}
    ]
    write_hours(tmp_path, "2026-10", "2026-11", "2026-12")
    with pytest.raises(HoursFileError, match="Zusatzleistungen"):
        build_service_items(
            entry, 3, tmp_path, interactive=False, today=date(2027, 1, 1)
        )


class StopBeforeRender(Exception):
    """Beendet einen geprueften Test vor allen PDF- und Versandoperationen."""


def test_invoice_preview_uses_same_effective_month_as_workflow(tmp_path, monkeypatch):
    """Die Vorschau muss vor der Leistungsermittlung dieselben Konditionen waehlen."""
    entry = customer()
    entry["archive_directory"] = str(tmp_path)
    seen = []

    def record_service(customer, *args, **kwargs):
        """Prueft nur die Kondition und stoppt vor jedem Renderaufruf."""
        seen.append(customer["main_service"]["unit_price"])
        raise StopBeforeRender

    monkeypatch.setattr(invoice_preview, "today", lambda: date(2026, 11, 1))
    monkeypatch.setattr(invoice_preview, "check_archive_path", lambda *a, **k: None)
    monkeypatch.setattr(invoice_preview, "build_service_items", record_service)
    with pytest.raises(StopBeforeRender):
        invoice_preview.create_customer_invoice_preview(
            entry,
            SimpleNamespace(base_dir=tmp_path, hours_dir=tmp_path),
            {},
            {},
            {},
            {},
            {},
            None,
        )
    assert seen == ["60.00"]


@pytest.mark.parametrize("old_cycle,new_cycle", [(3, 1), (1, 3)])
def test_hourly_cycle_change_is_rejected_even_in_direct_yaml(old_cycle, new_cycle):
    """Ein verspaeteter Uebergang darf keine Leistungsmonate verlieren oder duplizieren."""
    from customer_files import customer_to_yaml

    document = customer_to_yaml(customer(unit="hour", cycle=old_cycle))
    document["scheduled_changes"][0]["changes"]["billing"] = {
        "cycle_months": new_cycle
    }
    with pytest.raises(ValueError, match="Stunden-Abrechnungszyklus"):
        normalize_customer(document)
