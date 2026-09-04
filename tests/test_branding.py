import pytest

from branding import load_logo_asset, resolve_logo_path, validate_branding_config


def test_branding_defaults_keep_pdf_logo_and_disable_mail_logo():
    """Branding-Defaults behalten das PDF-Logo und deaktivieren das Mail-Logo."""
    assert validate_branding_config({}) == {
        "pdf_logo": "logo.png",
        "mail_logo": None,
        "pdf_logo_height": 40,
        "mail_logo_height": 60,
        "header_title": None,
        "header_subtitle": None,
    }


def test_branding_accepts_relative_and_absolute_logo_paths(tmp_path):
    """Relative und absolute PNG- oder JPEG-Pfade sind zulaessig."""
    absolute = tmp_path / "mail.jpg"

    branding = validate_branding_config(
        {
            "pdf_logo": "branding/rechnung.png",
            "mail_logo": str(absolute),
        }
    )

    assert branding["pdf_logo"] == "branding/rechnung.png"
    assert branding["mail_logo"] == str(absolute)


def test_branding_accepts_optional_header_texts():
    """Eigene Branding-Texte koennen unabhaengig konfiguriert werden."""
    branding = validate_branding_config(
        {
            "header_title": "Musteragentur",
            "header_subtitle": "Design und Beratung",
        }
    )

    assert branding["header_title"] == "Musteragentur"
    assert branding["header_subtitle"] == "Design und Beratung"


def test_branding_rejects_empty_header_text():
    """Leere Branding-Texte werden als Konfigurationsfehler erkannt."""
    with pytest.raises(ValueError, match="header_title"):
        validate_branding_config({"header_title": ""})


def test_branding_rejects_unknown_fields():
    """Tippfehler in Branding-Feldern werden nicht still ignoriert."""
    with pytest.raises(ValueError, match="Unbekannte Felder"):
        validate_branding_config({"mail_logo_heigth": 60})


def test_branding_accepts_bounded_logo_heights():
    """Logo-Hoehen koennen innerhalb sicherer Grenzen angepasst werden."""
    branding = validate_branding_config({"pdf_logo_height": 55, "mail_logo_height": 80})

    assert branding["pdf_logo_height"] == 55
    assert branding["mail_logo_height"] == 80


@pytest.mark.parametrize("value", [True, 9, 201, "60"])
def test_branding_rejects_invalid_logo_height(value):
    """Ungueltige Logo-Hoehen werden vor dem Rendering abgelehnt."""
    with pytest.raises(ValueError, match="10 bis 200"):
        validate_branding_config({"mail_logo_height": value})


def test_branding_rejects_unsupported_logo_format():
    """Nicht unterstuetzte Logoformate werden fruehzeitig abgelehnt."""
    with pytest.raises(ValueError, match="Format"):
        validate_branding_config({"mail_logo": "logo.svg"})


def test_relative_logo_path_must_stay_in_image_directory(tmp_path):
    """Relative Logo-Pfade duerfen den Bildordner nicht verlassen."""
    with pytest.raises(ValueError, match="innerhalb"):
        resolve_logo_path(tmp_path / "img", "../logo.png")


def test_logo_asset_loads_png_as_data_uri(tmp_path):
    """Ein PNG-Logo wird fuer PDF und Mail passend geladen."""
    image_dir = tmp_path / "img"
    image_dir.mkdir()
    (image_dir / "logo.png").write_bytes(b"png-data")

    logo = load_logo_asset(image_dir, "logo.png", "Testlogo")

    assert logo is not None
    assert logo.subtype == "png"
    assert logo.data == b"png-data"
    assert logo.data_uri == "data:image/png;base64,cG5nLWRhdGE="


def test_missing_configured_logo_is_ignored_with_warning(tmp_path, caplog):
    """Ein fehlendes konfiguriertes Logo blockiert die Verarbeitung nicht."""
    logo = load_logo_asset(tmp_path, "logo.png", "Testlogo")

    assert logo is None
    assert "Testlogo nicht gefunden" in caplog.text
