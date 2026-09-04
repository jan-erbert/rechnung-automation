import re

from strict_yaml import reject_unknown_keys

DEFAULT_DESIGN = {
    "pdf": {
        "accent_color": "#2f3c50",
        "accent_text_color": "#ffffff",
        "accent_muted_text_color": "#dbe2ea",
    },
    "mail": {
        "accent_color": "#2f3c50",
        "link_color": "#007BFF",
    },
}

HEX_COLOR_PATTERN = re.compile(r"^#[0-9A-Fa-f]{6}$")


def validate_design_config(design_config: dict | None) -> dict:
    """Prueft Designfarben und ergaenzt die bisherigen Standardwerte."""
    if design_config is None:
        design_config = {}
    if not isinstance(design_config, dict):
        raise ValueError("Der YAML-Bereich 'design' muss eine Map sein.")

    reject_unknown_keys(design_config, set(DEFAULT_DESIGN), "design")
    validated = {}
    for section, defaults in DEFAULT_DESIGN.items():
        values = design_config.get(section, {})
        if not isinstance(values, dict):
            raise ValueError(f"Der YAML-Bereich 'design.{section}' muss eine Map sein.")

        reject_unknown_keys(values, set(defaults), f"design.{section}")
        validated[section] = {}
        for name, default in defaults.items():
            value = values.get(name, default)
            if not isinstance(value, str) or not HEX_COLOR_PATTERN.fullmatch(value):
                raise ValueError(
                    f"design.{section}.{name} muss eine sechsstellige "
                    "Hex-Farbe wie '#2f3c50' sein."
                )
            validated[section][name] = value

    return validated
