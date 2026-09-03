import yaml
import pytest

from konfiguration import lade_konfiguration


def _write_config(tmp_path, tax: dict):
    """Schreibt eine minimale YAML-Rechnungskonfiguration fuer Tests."""
    config_path = tmp_path / "invoice.yaml"
    config = {
        "sender": {
            "name": "Test",
            "company": "Testfirma",
            "street": "Testweg 1",
            "postal_code": "01234",
            "city": "Teststadt",
            "phone": "+49 123",
            "email": "test@example.com",
        },
        "bank": {
            "iban": "DE00000000000000000000",
            "name": "Testbank",
            "bic": "TESTDE00XXX",
            "account_holder": "Test",
        },
        "tax": tax,
    }
    config_path.write_text(
        yaml.safe_dump(config, allow_unicode=True, sort_keys=False), encoding="utf-8"
    )
    return config_path


@pytest.mark.parametrize(
    ("identifier_type", "yaml_feld", "internes_feld", "wert"),
    [
        ("tax_number", "tax_number", "steuernummer", "12/345/67890"),
        ("vat_id", "vat_id", "ust_id", "DE123456789"),
    ],
)
def test_lade_konfiguration_accepts_tax_id_types(
    tmp_path, identifier_type, yaml_feld, internes_feld, wert
):
    """Steuernummer und USt-IdNr. sind gueltige Alternativen."""
    config_path = _write_config(
        tmp_path,
        {
            "identifier_type": identifier_type,
            yaml_feld: wert,
            "small_business": True,
        },
    )

    config = lade_konfiguration(config_path)

    assert config["finanzen"][internes_feld] == wert


def test_lade_konfiguration_rejects_missing_selected_tax_id(tmp_path):
    """Der ausgewaehlte Nummerntyp benoetigt den passenden Wert."""
    config_path = _write_config(
        tmp_path,
        {"identifier_type": "vat_id", "small_business": True},
    )

    with pytest.raises(ValueError, match="tax.vat_id"):
        lade_konfiguration(config_path)


def test_lade_konfiguration_rejects_whitespace_mail_sender_name(tmp_path):
    """Ein gesetzter Mail-Absendername darf nicht nur Leerzeichen enthalten."""
    config_path = _write_config(
        tmp_path,
        {
            "identifier_type": "tax_number",
            "tax_number": "12/345/67890",
            "small_business": True,
        },
    )
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    config["mail"] = {"from_name": "   "}
    config_path.write_text(yaml.safe_dump(config), encoding="utf-8")

    with pytest.raises(ValueError, match="mail.from_name"):
        lade_konfiguration(config_path)
