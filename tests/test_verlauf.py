import json
from datetime import datetime

import pytest

from verlauf import (
    VERSANDSTATUS_FAILED,
    VERSANDSTATUS_NO_INVOICE,
    VERSANDSTATUS_PENDING,
    VERSANDSTATUS_WAITING_HOURS,
    ist_abrechnung_abgeschlossen,
    ist_erfolgreich_versendet,
    schliesse_abgelaufene_stundenwarteschlangen,
    setze_versandstatus,
    speichere_oder_ersetze_verlaufseintrag,
    speichere_verlauf,
)


def test_legacy_history_entry_is_treated_as_sent():
    """Alte Verlaufseintraege bleiben als erfolgreich versendet gueltig."""
    assert ist_erfolgreich_versendet({"id": "alt"}) is True


def test_no_invoice_is_completed_but_not_sent():
    """Eine Nullabrechnung ist abgeschlossen, wurde aber nicht versendet."""
    eintrag = {"versandstatus": VERSANDSTATUS_NO_INVOICE}

    assert ist_abrechnung_abgeschlossen(eintrag) is True
    assert ist_erfolgreich_versendet(eintrag) is False


def test_status_entry_is_replaced_instead_of_duplicated(tmp_path):
    """Statuswechsel ersetzen denselben Rechnungseintrag atomar."""
    verlauf_pfad = tmp_path / "verlauf.json"
    verlauf = []
    pending = {"id": "rechnung-1", "versandstatus": VERSANDSTATUS_PENDING}

    speichere_oder_ersetze_verlaufseintrag(verlauf_pfad, verlauf, pending)
    setze_versandstatus(
        verlauf_pfad,
        verlauf,
        "rechnung-1",
        VERSANDSTATUS_FAILED,
    )

    gespeichert = json.loads(verlauf_pfad.read_text(encoding="utf-8"))
    assert len(gespeichert) == 1
    assert gespeichert[0]["versandstatus"] == VERSANDSTATUS_FAILED
    assert verlauf == gespeichert


def test_failed_atomic_write_does_not_replace_existing_history(tmp_path, monkeypatch):
    """Ein fehlgeschlagener atomarer Austausch erhaelt die bestehende Datei."""
    verlauf_pfad = tmp_path / "verlauf.json"
    bestehend = [{"id": "bestehend"}]
    speichere_verlauf(verlauf_pfad, bestehend)

    def fehler_beim_ersetzen(source, target):
        raise OSError("Austausch fehlgeschlagen")

    monkeypatch.setattr("verlauf.os.replace", fehler_beim_ersetzen)

    with pytest.raises(OSError):
        speichere_verlauf(verlauf_pfad, [{"id": "neu"}])

    assert json.loads(verlauf_pfad.read_text(encoding="utf-8")) == bestehend
    assert list(tmp_path.glob("*.tmp")) == []


def test_expired_waiting_hours_are_closed_without_invoice(tmp_path):
    """Ein alter Stunden-Wartezustand wird atomar als no_invoice abgeschlossen."""
    verlauf_pfad = tmp_path / "verlauf.json"
    verlauf = [
        {
            "id": "rechnung-1",
            "jahr": 2026,
            "monat": 6,
            "zyklus_monate": 3,
            "versandstatus": VERSANDSTATUS_WAITING_HOURS,
        }
    ]
    speichere_verlauf(verlauf_pfad, verlauf)

    abgeschlossen = schliesse_abgelaufene_stundenwarteschlangen(
        verlauf_pfad,
        verlauf,
        datetime(2026, 7, 1),
    )

    assert abgeschlossen == 1
    assert verlauf[0]["versandstatus"] == VERSANDSTATUS_NO_INVOICE
    assert verlauf[0]["zyklus_monate"] == 3


def test_current_waiting_hours_remain_open(tmp_path):
    """Der aktuelle Rechnungsmonat bleibt fuer nachgetragene Stunden offen."""
    verlauf_pfad = tmp_path / "verlauf.json"
    verlauf = [
        {
            "id": "rechnung-1",
            "jahr": 2026,
            "monat": 7,
            "versandstatus": VERSANDSTATUS_WAITING_HOURS,
        }
    ]
    speichere_verlauf(verlauf_pfad, verlauf)

    abgeschlossen = schliesse_abgelaufene_stundenwarteschlangen(
        verlauf_pfad,
        verlauf,
        datetime(2026, 7, 31),
    )

    assert abgeschlossen == 0
    assert verlauf[0]["versandstatus"] == VERSANDSTATUS_WAITING_HOURS
