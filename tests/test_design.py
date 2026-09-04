import pytest

from design import DEFAULT_DESIGN, validate_design_config


def test_design_defaults_preserve_current_colors():
    """Fehlende Designwerte behalten das bisherige Erscheinungsbild bei."""
    assert validate_design_config({}) == DEFAULT_DESIGN


def test_design_accepts_custom_hex_colors():
    """Gueltige benutzerdefinierte Hex-Farben werden uebernommen."""
    design = validate_design_config(
        {
            "pdf": {"accent_color": "#123456"},
            "mail": {"link_color": "#aBcDeF"},
        }
    )

    assert design["pdf"]["accent_color"] == "#123456"
    assert design["pdf"]["accent_text_color"] == "#ffffff"
    assert design["mail"]["link_color"] == "#aBcDeF"
    assert design["mail"]["accent_color"] == "#2f3c50"


@pytest.mark.parametrize("value", ["123456", "#12345", "#xyzxyz", "", None])
def test_design_rejects_invalid_hex_colors(value):
    """Ungueltige Farbangaben werden vor der Vorlagenverarbeitung abgelehnt."""
    with pytest.raises(ValueError, match="sechsstellige Hex-Farbe"):
        validate_design_config({"pdf": {"accent_color": value}})


def test_design_rejects_non_map_sections():
    """Designbereiche muessen als YAML-Maps konfiguriert sein."""
    with pytest.raises(ValueError, match="design.mail"):
        validate_design_config({"mail": "#123456"})


def test_design_rejects_unknown_fields():
    """Tippfehler in Design-Feldern werden nicht still ignoriert."""
    with pytest.raises(ValueError, match="Unbekannte Felder"):
        validate_design_config({"pdf": {"accent_colour": "#123456"}})
