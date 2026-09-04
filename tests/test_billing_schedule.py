from datetime import datetime

from billing_schedule import is_invoice_due


def test_rechnung_is_due_until_end_of_last_invoice_month():
    """Der konfigurierte Endmonat bleibt bis zum Monatsende abrechenbar."""
    entry = {
        "company": "Beispielfirma",
        "name": "Erika Beispiel",
        "end_month": "2026-12",
    }

    assert is_invoice_due(entry, [], today=datetime(2026, 12, 31)) is True


def test_rechnung_is_not_due_after_last_invoice_month():
    """Nach dem konfigurierten Endmonat wird keine Rechnung mehr erstellt."""
    entry = {
        "company": "Beispielfirma",
        "name": "Erika Beispiel",
        "end_month": "2026-12",
    }

    assert is_invoice_due(entry, [], today=datetime(2027, 1, 1)) is False


def test_null_last_invoice_month_has_no_end_limit():
    """Ein YAML-null beim optionalen Endmonat begrenzt die Laufzeit nicht."""
    entry = {
        "company": "Beispielfirma",
        "name": "Erika Beispiel",
        "end_month": None,
    }

    assert is_invoice_due(entry, [], today=datetime(2026, 12, 15)) is True


def test_last_invoice_month_is_due_independent_of_regular_cycle():
    """Im Endmonat wird die letzte reguläre Rechnung sicher faellig."""
    entry = {
        "company": "Beispielfirma",
        "name": "Erika Beispiel",
        "cycle_months": 12,
        "end_month": "2026-12",
    }
    invoice_history = [
        {
            "company": "Beispielfirma",
            "name": "Erika Beispiel",
            "year": 2026,
            "month": 11,
            "cycle_months": 12,
        }
    ]

    assert is_invoice_due(entry, invoice_history, today=datetime(2026, 12, 15)) is True


def test_last_invoice_month_is_not_billed_twice():
    """Eine bereits versendete letzte Rechnung wird nicht erneut erstellt."""
    entry = {
        "company": "Beispielfirma",
        "name": "Erika Beispiel",
        "end_month": "2026-12",
    }
    invoice_history = [
        {
            "id": "beispielfirma__erika beispiel__2026-12",
            "company": "Beispielfirma",
            "name": "Erika Beispiel",
            "year": 2026,
            "month": 12,
        }
    ]

    assert is_invoice_due(entry, invoice_history, today=datetime(2026, 12, 31)) is False


def test_failed_mail_is_retried():
    """Ein eindeutig fehlgeschlagener Versand wird erneut versucht."""
    entry = {
        "company": "Beispielfirma",
        "name": "Erika Beispiel",
    }
    invoice_history = [
        {
            "id": "beispielfirma__erika beispiel__2026-12",
            "company": "Beispielfirma",
            "name": "Erika Beispiel",
            "year": 2026,
            "month": 12,
            "status": "failed",
        }
    ]

    assert is_invoice_due(entry, invoice_history, today=datetime(2026, 12, 15)) is True


def test_failed_mail_from_previous_month_blocks_new_invoice():
    """Ein alter fehlgeschlagener Versand wird nicht als neue Rechnung gebaut."""
    entry = {
        "company": "Beispielfirma",
        "name": "Erika Beispiel",
    }
    invoice_history = [
        {
            "id": "beispielfirma__erika beispiel__2026-11",
            "company": "Beispielfirma",
            "name": "Erika Beispiel",
            "year": 2026,
            "month": 11,
            "status": "failed",
        }
    ]

    assert is_invoice_due(entry, invoice_history, today=datetime(2026, 12, 15)) is False


def test_pending_mail_blocks_automatic_retry():
    """Ein unklarer pending-Status verhindert automatischen Doppelversand."""
    entry = {
        "company": "Beispielfirma",
        "name": "Erika Beispiel",
    }
    invoice_history = [
        {
            "id": "beispielfirma__erika beispiel__2026-11",
            "company": "Beispielfirma",
            "name": "Erika Beispiel",
            "year": 2026,
            "month": 11,
            "status": "pending",
        }
    ]

    assert is_invoice_due(entry, invoice_history, today=datetime(2026, 12, 15)) is False


def test_unknown_mail_status_blocks_automatic_retry():
    """Ein unbekannter Versandstatus wird vorsichtshalber blockiert."""
    entry = {
        "company": "Beispielfirma",
        "name": "Erika Beispiel",
    }
    invoice_history = [
        {
            "id": "beispielfirma__erika beispiel__2026-11",
            "company": "Beispielfirma",
            "name": "Erika Beispiel",
            "year": 2026,
            "month": 11,
            "status": "unbekannt",
        }
    ]

    assert is_invoice_due(entry, invoice_history, today=datetime(2026, 12, 15)) is False


def test_waiting_hours_is_retried_in_same_invoice_month():
    """Fehlende Stunden werden im selben Rechnungsmonat erneut geprueft."""
    entry = {
        "company": "Beispielfirma",
        "name": "Erika Beispiel",
        "cycle_months": 3,
    }
    invoice_history = [
        {
            "id": "beispielfirma__erika beispiel__2026-12",
            "company": "Beispielfirma",
            "name": "Erika Beispiel",
            "year": 2026,
            "month": 12,
            "cycle_months": 3,
            "status": "waiting_hours",
        }
    ]

    assert is_invoice_due(entry, invoice_history, today=datetime(2026, 12, 20)) is True


def test_old_waiting_hours_blocks_new_invoice():
    """Ein alter Wartezustand darf nicht in eine neue Rechnung umschlagen."""
    entry = {
        "company": "Beispielfirma",
        "name": "Erika Beispiel",
    }
    invoice_history = [
        {
            "id": "beispielfirma__erika beispiel__2026-11",
            "company": "Beispielfirma",
            "name": "Erika Beispiel",
            "year": 2026,
            "month": 11,
            "status": "waiting_hours",
        }
    ]

    assert is_invoice_due(entry, invoice_history, today=datetime(2026, 12, 1)) is False


def test_no_invoice_preserves_multi_month_cycle():
    """Eine Nullabrechnung bleibt Teil des konfigurierten Zyklus."""
    entry = {
        "company": "Beispielfirma",
        "name": "Erika Beispiel",
        "cycle_months": 3,
    }
    invoice_history = [
        {
            "id": "beispielfirma__erika beispiel__2026-11",
            "company": "Beispielfirma",
            "name": "Erika Beispiel",
            "year": 2026,
            "month": 11,
            "cycle_months": 3,
            "status": "no_invoice",
        }
    ]

    assert is_invoice_due(entry, invoice_history, today=datetime(2026, 12, 1)) is False
    assert is_invoice_due(entry, invoice_history, today=datetime(2027, 2, 1)) is True


def test_one_time_invoice_from_older_year_remains_blocked():
    """Ein Einmalkunde bleibt auch nach mehr als zwei Jahren abgeschlossen."""
    customer = {
        "id": "beispielfirma",
        "company": "Beispielfirma",
        "name": "Erika Beispiel",
        "one_time": True,
    }
    history = [
        {
            "id": "beispielfirma__2023-01",
            "customer_id": "beispielfirma",
            "year": 2023,
            "month": 1,
            "status": "sent",
        }
    ]

    assert is_invoice_due(customer, history, today=datetime(2026, 6, 4)) is False
