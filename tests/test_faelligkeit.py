from datetime import datetime

from faelligkeit import rechnung_fällig


def test_rechnung_is_due_until_end_of_last_invoice_month():
    """Der konfigurierte Endmonat bleibt bis zum Monatsende abrechenbar."""
    eintrag = {
        "firma": "Beispielfirma",
        "name": "Erika Beispiel",
        "letzte_rechnung": "2026-12",
    }

    assert rechnung_fällig(eintrag, [], heute=datetime(2026, 12, 31)) is True


def test_rechnung_is_not_due_after_last_invoice_month():
    """Nach dem konfigurierten Endmonat wird keine Rechnung mehr erstellt."""
    eintrag = {
        "firma": "Beispielfirma",
        "name": "Erika Beispiel",
        "letzte_rechnung": "2026-12",
    }

    assert rechnung_fällig(eintrag, [], heute=datetime(2027, 1, 1)) is False


def test_last_invoice_month_is_due_independent_of_regular_cycle():
    """Im Endmonat wird die letzte reguläre Rechnung sicher faellig."""
    eintrag = {
        "firma": "Beispielfirma",
        "name": "Erika Beispiel",
        "abrechnungszyklus": 12,
        "letzte_rechnung": "2026-12",
    }
    verlauf = [
        {
            "firma": "Beispielfirma",
            "name": "Erika Beispiel",
            "jahr": 2026,
            "monat": 11,
            "zyklus_monate": 12,
        }
    ]

    assert rechnung_fällig(eintrag, verlauf, heute=datetime(2026, 12, 15)) is True


def test_last_invoice_month_is_not_billed_twice():
    """Eine bereits versendete letzte Rechnung wird nicht erneut erstellt."""
    eintrag = {
        "firma": "Beispielfirma",
        "name": "Erika Beispiel",
        "letzte_rechnung": "2026-12",
    }
    verlauf = [
        {
            "id": "beispielfirma__erika beispiel__2026-12",
            "firma": "Beispielfirma",
            "name": "Erika Beispiel",
            "jahr": 2026,
            "monat": 12,
        }
    ]

    assert rechnung_fällig(eintrag, verlauf, heute=datetime(2026, 12, 31)) is False


def test_failed_mail_is_retried():
    """Ein eindeutig fehlgeschlagener Versand wird erneut versucht."""
    eintrag = {
        "firma": "Beispielfirma",
        "name": "Erika Beispiel",
    }
    verlauf = [
        {
            "id": "beispielfirma__erika beispiel__2026-12",
            "firma": "Beispielfirma",
            "name": "Erika Beispiel",
            "jahr": 2026,
            "monat": 12,
            "versandstatus": "failed",
        }
    ]

    assert rechnung_fällig(eintrag, verlauf, heute=datetime(2026, 12, 15)) is True


def test_failed_mail_from_previous_month_blocks_new_invoice():
    """Ein alter fehlgeschlagener Versand wird nicht als neue Rechnung gebaut."""
    eintrag = {
        "firma": "Beispielfirma",
        "name": "Erika Beispiel",
    }
    verlauf = [
        {
            "id": "beispielfirma__erika beispiel__2026-11",
            "firma": "Beispielfirma",
            "name": "Erika Beispiel",
            "jahr": 2026,
            "monat": 11,
            "versandstatus": "failed",
        }
    ]

    assert rechnung_fällig(eintrag, verlauf, heute=datetime(2026, 12, 15)) is False


def test_pending_mail_blocks_automatic_retry():
    """Ein unklarer pending-Status verhindert automatischen Doppelversand."""
    eintrag = {
        "firma": "Beispielfirma",
        "name": "Erika Beispiel",
    }
    verlauf = [
        {
            "id": "beispielfirma__erika beispiel__2026-11",
            "firma": "Beispielfirma",
            "name": "Erika Beispiel",
            "jahr": 2026,
            "monat": 11,
            "versandstatus": "pending",
        }
    ]

    assert rechnung_fällig(eintrag, verlauf, heute=datetime(2026, 12, 15)) is False


def test_unknown_mail_status_blocks_automatic_retry():
    """Ein unbekannter Versandstatus wird vorsichtshalber blockiert."""
    eintrag = {
        "firma": "Beispielfirma",
        "name": "Erika Beispiel",
    }
    verlauf = [
        {
            "id": "beispielfirma__erika beispiel__2026-11",
            "firma": "Beispielfirma",
            "name": "Erika Beispiel",
            "jahr": 2026,
            "monat": 11,
            "versandstatus": "unbekannt",
        }
    ]

    assert rechnung_fällig(eintrag, verlauf, heute=datetime(2026, 12, 15)) is False


def test_waiting_hours_is_retried_in_same_invoice_month():
    """Fehlende Stunden werden im selben Rechnungsmonat erneut geprueft."""
    eintrag = {
        "firma": "Beispielfirma",
        "name": "Erika Beispiel",
        "abrechnungszyklus": 3,
    }
    verlauf = [
        {
            "id": "beispielfirma__erika beispiel__2026-12",
            "firma": "Beispielfirma",
            "name": "Erika Beispiel",
            "jahr": 2026,
            "monat": 12,
            "zyklus_monate": 3,
            "versandstatus": "waiting_hours",
        }
    ]

    assert rechnung_fällig(eintrag, verlauf, heute=datetime(2026, 12, 20)) is True


def test_old_waiting_hours_blocks_new_invoice():
    """Ein alter Wartezustand darf nicht in eine neue Rechnung umschlagen."""
    eintrag = {
        "firma": "Beispielfirma",
        "name": "Erika Beispiel",
    }
    verlauf = [
        {
            "id": "beispielfirma__erika beispiel__2026-11",
            "firma": "Beispielfirma",
            "name": "Erika Beispiel",
            "jahr": 2026,
            "monat": 11,
            "versandstatus": "waiting_hours",
        }
    ]

    assert rechnung_fällig(eintrag, verlauf, heute=datetime(2026, 12, 1)) is False


def test_no_invoice_preserves_multi_month_cycle():
    """Eine Nullabrechnung bleibt Teil des konfigurierten Zyklus."""
    eintrag = {
        "firma": "Beispielfirma",
        "name": "Erika Beispiel",
        "abrechnungszyklus": 3,
    }
    verlauf = [
        {
            "id": "beispielfirma__erika beispiel__2026-11",
            "firma": "Beispielfirma",
            "name": "Erika Beispiel",
            "jahr": 2026,
            "monat": 11,
            "zyklus_monate": 3,
            "versandstatus": "no_invoice",
        }
    ]

    assert rechnung_fällig(eintrag, verlauf, heute=datetime(2026, 12, 1)) is False
    assert rechnung_fällig(eintrag, verlauf, heute=datetime(2027, 2, 1)) is True
