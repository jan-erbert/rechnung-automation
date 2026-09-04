import pytest

from configuration import load_invoice_config
from customer_files import load_customer_files
from settings_loader import load_settings


def test_settings_reject_duplicate_keys(tmp_path):
    """Doppelte YAML-Schluessel werden nicht still ueberschrieben."""
    path = tmp_path / "settings.yaml"
    path.write_text("mail:\n  security: ssl\n  security: starttls\n", encoding="utf-8")

    with pytest.raises(ValueError, match="duplicate key"):
        load_settings(path)


def test_settings_reject_unknown_keys(tmp_path):
    """Tippfehler in Settings werden konkret gemeldet."""
    path = tmp_path / "settings.yaml"
    path.write_text("mail:\n  securty: starttls\n", encoding="utf-8")

    with pytest.raises(ValueError, match="mail.securty"):
        load_settings(path)


def test_settings_accept_file_naming_section(tmp_path):
    """Die Dateibenennung kann zentral in den Settings gepflegt werden."""
    path = tmp_path / "settings.yaml"
    path.write_text(
        "file_naming:\n  invoice_prefix: Rechnung\n  preview_prefix: VORSCHAU\n",
        encoding="utf-8",
    )

    assert load_settings(path)["file_naming"]["invoice_prefix"] == "Rechnung"


def test_customer_rejects_unknown_active_field(tmp_path):
    """Ein Tippfehler bei active kann keinen Default aktivieren."""
    (tmp_path / "customer.yaml").write_text(
        """id: customer
activee: false
contact:
  name: Erika Beispiel
  company: Beispiel GmbH
  email: erika@example.com
  street: Beispielweg 1
  postal_code: "12345"
  city: Beispielstadt
main_service:
  description: Hosting
  unit: month
  unit_price: "10.00"
""",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="customer.activee"):
        load_customer_files(tmp_path)


def test_invoice_config_rejects_unknown_field(tmp_path):
    """Unbekannte Rechnungsfelder brechen die Konfigurationspruefung ab."""
    path = tmp_path / "invoice.yaml"
    path.write_text(
        """sender:
  name: Max Beispiel
  company: Beispiel GmbH
  street: Beispielweg 1
  postal_code: "12345"
  city: Beispielstadt
  phone: "0123"
  email: max@example.com
bank:
  name: Beispielbank
  iban: DE123
  bic: TESTDE00
  account_holder: Max Beispiel
tax:
  identifier_type: tax_number
  tax_number: 12/345
  small_business: true
  vat_raet: "19"
""",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="tax.vat_raet"):
        load_invoice_config(path)
