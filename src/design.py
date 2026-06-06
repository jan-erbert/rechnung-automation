import re

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


def validiere_design_config(design_config: dict | None) -> dict:
    """Prueft Designfarben und ergaenzt die bisherigen Standardwerte."""
    if design_config is None:
        design_config = {}
    if not isinstance(design_config, dict):
        raise ValueError("Der YAML-Bereich 'design' muss eine Map sein.")

    validiert = {}
    for bereich, standardwerte in DEFAULT_DESIGN.items():
        werte = design_config.get(bereich, {})
        if not isinstance(werte, dict):
            raise ValueError(f"Der YAML-Bereich 'design.{bereich}' muss eine Map sein.")

        validiert[bereich] = {}
        for name, standardwert in standardwerte.items():
            wert = werte.get(name, standardwert)
            if not isinstance(wert, str) or not HEX_COLOR_PATTERN.fullmatch(wert):
                raise ValueError(
                    f"design.{bereich}.{name} muss eine sechsstellige "
                    "Hex-Farbe wie '#2f3c50' sein."
                )
            validiert[bereich][name] = wert

    return validiert
