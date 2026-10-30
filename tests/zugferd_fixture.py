"""Ausschliesslich fiktive Daten fuer isolierte ZUGFeRD-Tests."""

from decimal import Decimal


def invoice_snapshot() -> dict:
    """Liefert eine neue fiktive Rechnung ohne Zugriff auf Projektkonfiguration."""
    return {
        "customer": {
            "company": "Musterkunde GmbH",
            "name": "Erika Beispiel",
            "first_name": "Erika",
            "last_name": "Beispiel",
            "salutation": "frau",
            "street": "Testweg 1",
            "postal_code": "12345",
            "city": "Musterstadt",
            "country_code": "DE",
            "email": "customer@example.org",
        },
        "sender": {
            "company": "Musteranbieter GmbH",
            "name": "Max Mustermann",
            "street": "Beispielweg 2",
            "postal_code": "54321",
            "city": "Beispielstadt",
            "country_code": "DE",
            "email": "sender@example.org",
            "phone": "+49 123 456789",
        },
        "bank": {
            "iban": "DE89370400440532013000",
            "account_holder": "Musterfirma",
            "name": "Musterbank",
            "bic": "TESTDEFFXXX",
        },
        "tax": {
            "identifier_type": "vat_id",
            "vat_id": "DE123456789",
            "small_business": False,
            "vat_rate": Decimal("19"),
            "tax_office": "Musterstadt",
        },
        "lines": [
            {
                "name": "Hosting",
                "quantity": Decimal("1"),
                "unit_price": Decimal("100"),
                "total": Decimal("100"),
                "unit_code": "C62",
            }
        ],
        "dates": {
            "invoice_number": "MUSTER-01",
            "invoice_date": "24.10.2026",
            "due_date": "07.11.2026",
        },
        "net": Decimal("100"),
        "tax_amount": Decimal("19"),
        "gross": Decimal("119"),
    }
