from datetime import datetime

from customer_lifecycle import should_deactivate_customer


def test_kunde_can_be_removed_after_invoice_in_last_month():
    """Nach der letzten Rechnung kann der beendete Kunde entfernt werden."""
    entry = {"end_month": "2026-12"}

    assert should_deactivate_customer(entry, datetime(2026, 12, 1)) is True


def test_kunde_is_not_removed_before_last_invoice_month():
    """Vor dem Endmonat bleibt der Kunde in den Kundendaten."""
    entry = {"end_month": "2026-12"}

    assert should_deactivate_customer(entry, datetime(2026, 11, 30)) is False
