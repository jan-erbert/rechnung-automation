from dataclasses import dataclass
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class ProjektPfade:
    """Buendelt die zentralen Projektpfade."""

    base_dir: Path
    data_dir: Path
    hours_dir: Path
    templates_dir: Path
    img_dir: Path
    backup_dir: Path


def _resolve_path(base_dir: Path, pfad_wert: str) -> Path:
    """Erzeugt absolute Pfade aus absoluten oder projekt-relativen Angaben."""
    pfad = Path(pfad_wert)
    return pfad if pfad.is_absolute() else base_dir / pfad


def erstelle_pfade(
    settings: dict | None = None, base_dir: Path = BASE_DIR
) -> ProjektPfade:
    """Erzeugt Projektpfade aus Einstellungen und sinnvollen Defaults."""
    settings = settings or {}
    paths_config = settings.get("paths", {})

    if not isinstance(paths_config, dict):
        raise ValueError("Der YAML-Bereich 'paths' muss eine Map sein.")

    return ProjektPfade(
        base_dir=base_dir,
        data_dir=_resolve_path(base_dir, paths_config.get("data_dir", "data")),
        hours_dir=_resolve_path(base_dir, paths_config.get("hours_dir", "hours")),
        templates_dir=_resolve_path(
            base_dir, paths_config.get("templates_dir", "templates")
        ),
        img_dir=_resolve_path(base_dir, paths_config.get("image_dir", "img")),
        backup_dir=_resolve_path(base_dir, paths_config.get("backup_dir", "backup")),
    )
