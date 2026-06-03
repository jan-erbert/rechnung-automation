from pathlib import Path

import yaml

DEFAULT_SETTINGS_PATH = (
    Path(__file__).resolve().parent.parent / "config" / "settings.yaml"
)


def lade_settings(pfad: Path = DEFAULT_SETTINGS_PATH) -> dict:
    """Laedt die nicht-sensitiven Projekteinstellungen aus YAML."""
    if not pfad.exists():
        raise FileNotFoundError(f"Einstellungsdatei '{pfad}' nicht gefunden.")

    with pfad.open("r", encoding="utf-8") as settings_file:
        settings = yaml.safe_load(settings_file) or {}

    if not isinstance(settings, dict):
        raise ValueError("Die Einstellungsdatei muss eine YAML-Map enthalten.")

    return settings
