from pathlib import Path

from strict_yaml import load_yaml, reject_unknown_keys

DEFAULT_SETTINGS_PATH = (
    Path(__file__).resolve().parent.parent / "config" / "settings.yaml"
)


def load_settings(path: Path = DEFAULT_SETTINGS_PATH) -> dict:
    """Laedt die nicht-sensitiven Projekteinstellungen aus YAML."""
    if not path.exists():
        raise FileNotFoundError(f"Einstellungsdatei '{path}' nicht gefunden.")

    settings = load_yaml(path) or {}

    if not isinstance(settings, dict):
        raise ValueError("Die Einstellungsdatei muss eine YAML-Map enthalten.")

    reject_unknown_keys(
        settings,
        {"paths", "pdf", "design", "branding", "logging", "mail"},
        "settings",
    )
    sections = {
        "paths": {
            "data_dir",
            "customers_dir",
            "invoice_config",
            "templates_dir",
            "image_dir",
            "hours_dir",
            "backup_dir",
        },
        "pdf": {"engine"},
        "logging": {"enabled", "directory", "level"},
        "mail": {"security", "timeout_seconds"},
    }
    for section, allowed in sections.items():
        values = settings.get(section, {})
        if not isinstance(values, dict):
            raise ValueError(f"Der Bereich '{section}' muss eine Map sein.")
        reject_unknown_keys(values, allowed, section)
    return settings
