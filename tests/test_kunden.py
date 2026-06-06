from datetime import datetime

from kunden import sollte_kunde_entfernt_werden


def test_kunde_can_be_removed_after_invoice_in_last_month():
    """Nach der letzten Rechnung kann der beendete Kunde entfernt werden."""
    eintrag = {"letzte_rechnung": "2026-12"}

    assert sollte_kunde_entfernt_werden(eintrag, datetime(2026, 12, 1)) is True


def test_kunde_is_not_removed_before_last_invoice_month():
    """Vor dem Endmonat bleibt der Kunde in den Kundendaten."""
    eintrag = {"letzte_rechnung": "2026-12"}

    assert sollte_kunde_entfernt_werden(eintrag, datetime(2026, 11, 30)) is False
