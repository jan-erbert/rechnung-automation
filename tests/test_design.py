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


def test_table_colors_are_individually_configurable():
    """Eigene Tabellenfarben ergaenzen fehlende Werte mit sicheren Defaults."""
    design = validate_design_config({"tables": {"header_background": "#123456"}})
    assert design["tables"]["header_background"] == "#123456"
    assert design["tables"]["row_background"] == "#FFFFFF"


@pytest.mark.parametrize("value", ["blue", "#abc", "#000000;display:none", None, False])
def test_invalid_table_colors_are_rejected(value):
    """Ungueltige CSS-Werte gelangen nicht in die Rechnungsvorlagen."""
    with pytest.raises(ValueError, match="design.tables.header_background"):
        validate_design_config({"tables": {"header_background": value}})


def test_documented_color_presets_are_valid():
    """Alle veroeffentlichten Farbvorlagen verwenden die echte Konfigurationspruefung."""
    from pathlib import Path
    import yaml

    path = Path(__file__).resolve().parents[1] / "sample/design-presets.yaml"
    presets = yaml.safe_load(path.read_text())
    assert len(presets) == 4
    assert "neutral" in presets
    for preset in presets.values():
        assert validate_design_config(preset["design"])["tables"]
