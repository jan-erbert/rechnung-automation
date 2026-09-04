import json
from datetime import datetime

import pytest

from invoice_history import (
    STATUS_FAILED,
    STATUS_NO_INVOICE,
    STATUS_PENDING,
    STATUS_WAITING_HOURS,
    is_billing_complete,
    is_successfully_sent,
    close_expired_hours_waiting_entries,
    set_delivery_status,
    save_or_replace_history_entry,
    save_history,
    load_history_file,
)


def test_legacy_history_entry_is_treated_as_sent():
    """Alte Verlaufseintraege bleiben als erfolgreich versendet gueltig."""
    assert is_successfully_sent({"id": "alt"}) is True


def test_no_invoice_is_completed_but_not_sent():
    """Eine Nullabrechnung ist abgeschlossen, wurde aber nicht versendet."""
    entry = {"status": STATUS_NO_INVOICE}

    assert is_billing_complete(entry) is True
    assert is_successfully_sent(entry) is False


def test_status_entry_is_replaced_instead_of_duplicated(tmp_path):
    """Statuswechsel ersetzen denselben Rechnungseintrag atomar."""
    invoice_history_pfad = tmp_path / "invoice_history.json"
    invoice_history = []
    pending = {
        "id": "rechnung-1",
        "customer_id": "kunde",
        "year": 2026,
        "month": 7,
        "status": STATUS_PENDING,
    }

    save_or_replace_history_entry(invoice_history_pfad, invoice_history, pending)
    set_delivery_status(
        invoice_history_pfad,
        invoice_history,
        "rechnung-1",
        STATUS_FAILED,
    )

    gespeichert = json.loads(invoice_history_pfad.read_text(encoding="utf-8"))
    assert len(gespeichert) == 1
    assert gespeichert[0]["status"] == STATUS_FAILED
    assert invoice_history == gespeichert


def test_failed_atomic_write_does_not_replace_existing_history(tmp_path, monkeypatch):
    """Ein fehlgeschlagener atomarer Austausch erhaelt die bestehende Datei."""
    invoice_history_pfad = tmp_path / "invoice_history.json"
    bestehend = [{"id": "bestehend", "customer_id": "kunde", "year": 2026, "month": 7}]
    save_history(invoice_history_pfad, bestehend)

    def fehler_beim_ersetzen(source, target):
        raise OSError("Austausch fehlgeschlagen")

    monkeypatch.setattr("invoice_history.os.replace", fehler_beim_ersetzen)

    with pytest.raises(OSError):
        save_history(
            invoice_history_pfad,
            [{"id": "neu", "customer_id": "kunde", "year": 2026, "month": 7}],
        )

    assert json.loads(invoice_history_pfad.read_text(encoding="utf-8")) == bestehend
    assert list(tmp_path.glob("*.tmp")) == []


def test_expired_waiting_hours_are_closed_without_invoice(tmp_path):
    """Ein alter Stunden-Wartezustand wird atomar als no_invoice abgeschlossen."""
    invoice_history_pfad = tmp_path / "invoice_history.json"
    invoice_history = [
        {
            "id": "rechnung-1",
            "customer_id": "kunde",
            "year": 2026,
            "month": 6,
            "cycle_months": 3,
            "status": STATUS_WAITING_HOURS,
        }
    ]
    save_history(invoice_history_pfad, invoice_history)

    closed = close_expired_hours_waiting_entries(
        invoice_history_pfad,
        invoice_history,
        datetime(2026, 7, 1),
    )

    assert closed == 1
    assert invoice_history[0]["status"] == STATUS_NO_INVOICE
    assert invoice_history[0]["cycle_months"] == 3


def test_current_waiting_hours_remain_open(tmp_path):
    """Der aktuelle Rechnungsmonat bleibt fuer nachgetragene Stunden offen."""
    invoice_history_pfad = tmp_path / "invoice_history.json"
    invoice_history = [
        {
            "id": "rechnung-1",
            "customer_id": "kunde",
            "year": 2026,
            "month": 7,
            "status": STATUS_WAITING_HOURS,
        }
    ]
    save_history(invoice_history_pfad, invoice_history)

    closed = close_expired_hours_waiting_entries(
        invoice_history_pfad,
        invoice_history,
        datetime(2026, 7, 31),
    )

    assert closed == 0
    assert invoice_history[0]["status"] == STATUS_WAITING_HOURS


def test_history_loader_rejects_duplicate_ids(tmp_path):
    """Doppelte IDs koennen Abrechnungen nicht unbemerkt beeinflussen."""
    path = tmp_path / "invoice-history-2026.json"
    entry = {
        "id": "customer__2026-01",
        "customer_id": "customer",
        "year": 2026,
        "month": 1,
    }
    path.write_text(json.dumps([entry, entry]), encoding="utf-8")

    with pytest.raises(ValueError, match="Doppelte Verlaufs-ID"):
        load_history_file(path, 2026)
