import json

import pytest

from konfiguration import lade_konfiguration


def _write_config(tmp_path, finanzen: dict):
    """Schreibt eine minimale Rechnungskonfiguration fuer Tests."""
    config_path = tmp_path / "konfiguration.json"
    config = {
        "absender": {
            "name": "Test",
            "firma": "Testfirma",
            "email": "test@example.com",
        },
        "bank": {
            "iban": "DE00000000000000000000",
            "kontoinhaber": "Test",
        },
        "finanzen": finanzen,
    }
    config_path.write_text(json.dumps(config), encoding="utf-8")
    return config_path


@pytest.mark.parametrize(
    ("steuer_id_typ", "feld", "wert"),
    [
        ("steuernummer", "steuernummer", "12/345/67890"),
        ("ust_id", "ust_id", "DE123456789"),
    ],
)
def test_lade_konfiguration_accepts_tax_id_types(
    tmp_path,
    steuer_id_typ,
    feld,
    wert,
):
    """Steuernummer und USt-IdNr. sind gueltige Alternativen."""
    config_path = _write_config(
        tmp_path,
        {
            "steuer_id_typ": steuer_id_typ,
            feld: wert,
            "kleinunternehmer": True,
        },
    )

    config = lade_konfiguration(config_path)

    assert config["finanzen"][feld] == wert


def test_lade_konfiguration_rejects_missing_selected_tax_id(tmp_path):
    """Der ausgewaehlte Nummerntyp benoetigt den passenden Wert."""
    config_path = _write_config(
        tmp_path,
        {
            "steuer_id_typ": "ust_id",
            "kleinunternehmer": True,
        },
    )

    with pytest.raises(ValueError, match="finanzen.ust_id"):
        lade_konfiguration(config_path)


def test_lade_konfiguration_rejects_whitespace_mail_sender_name(tmp_path):
    """Ein gesetzter Mail-Absendername darf nicht nur Leerzeichen enthalten."""
    config_path = _write_config(
        tmp_path,
        {
            "steuer_id_typ": "steuernummer",
            "steuernummer": "12/345/67890",
            "kleinunternehmer": True,
        },
    )
    config = json.loads(config_path.read_text(encoding="utf-8"))
    config["mail"] = {"from_name": "   "}
    config_path.write_text(json.dumps(config), encoding="utf-8")

    with pytest.raises(ValueError, match="mail.from_name"):
        lade_konfiguration(config_path)
