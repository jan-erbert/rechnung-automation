import yaml
import pytest

from configuration import load_invoice_config


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
    ("identifier_type", "yaml_field", "internal_field", "value"),
    [
        ("tax_number", "tax_number", "tax_number", "12/345/67890"),
        ("vat_id", "vat_id", "vat_id", "DE123456789"),
    ],
)
def test_lade_configuration_accepts_tax_id_types(
    tmp_path, identifier_type, yaml_field, internal_field, value
):
    """Steuernummer und USt-IdNr. sind gueltige Alternativen."""
    config_path = _write_config(
        tmp_path,
        {
            "identifier_type": identifier_type,
            yaml_field: value,
            "small_business": True,
        },
    )

    config = load_invoice_config(config_path)

    assert config["tax"][internal_field] == value


def test_lade_configuration_rejects_missing_selected_tax_id(tmp_path):
    """Der ausgewaehlte Nummerntyp benoetigt den passenden Wert."""
    config_path = _write_config(
        tmp_path,
        {"identifier_type": "vat_id", "small_business": True},
    )

    with pytest.raises(ValueError, match="tax.vat_id"):
        load_invoice_config(config_path)


def test_lade_configuration_rejects_whitespace_mail_sender_name(tmp_path):
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
        load_invoice_config(config_path)


@pytest.mark.parametrize("option", ["icons_enabled", "automation_notice_enabled"])
@pytest.mark.parametrize("value", [False, True, "false", 0, None])
def test_private_mail_option_is_strict_boolean(tmp_path, option, value):
    """Der private Mail-Schalter akzeptiert nur true und false."""
    path = _write_config(
        tmp_path,
        {
            "identifier_type": "tax_number",
            "tax_number": "12/345/67890",
            "small_business": True,
            "vat_rate": 0,
        },
    )
    config = yaml.safe_load(path.read_text())
    config["mail"] = {option: value}
    path.write_text(yaml.safe_dump(config))
    if isinstance(value, bool):
        assert load_invoice_config(path)["mail"][option] is value
    else:
        with pytest.raises(ValueError, match=f"mail.{option}"):
            load_invoice_config(path)


@pytest.mark.parametrize("output_format", ["pdf", "zugferd", "invalid"])
def test_private_pdf_format_is_validated(tmp_path, output_format):
    """Private Formatwahl akzeptiert nur die ausdruecklich unterstuetzten Formate."""
    path = _write_config(
        tmp_path,
        {
            "identifier_type": "tax_number",
            "tax_number": "12/345",
            "small_business": True,
        },
    )
    config = yaml.safe_load(path.read_text())
    config["pdf"] = {"format": output_format}
    path.write_text(yaml.safe_dump(config))
    if output_format == "invalid":
        with pytest.raises(ValueError, match="pdf.format"):
            load_invoice_config(path)
    else:
        assert load_invoice_config(path)["pdf"]["format"] == output_format
