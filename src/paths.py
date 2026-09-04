from dataclasses import dataclass
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class ProjectPaths:
    """Buendelt die zentralen Projektpfade."""

    base_dir: Path
    data_dir: Path
    customers_dir: Path
    invoice_config: Path
    hours_dir: Path
    templates_dir: Path
    img_dir: Path
    backup_dir: Path


def _resolve_path(base_dir: Path, path_value: str) -> Path:
    """Erzeugt absolute Pfade aus absoluten oder projekt-relativen Angaben."""
    path = Path(path_value)
    return path if path.is_absolute() else base_dir / path


def create_paths(
    settings: dict | None = None, base_dir: Path = BASE_DIR
) -> ProjectPaths:
    """Erzeugt Projektpfade aus Einstellungen und sinnvollen Defaults."""
    settings = settings or {}
    paths_config = settings.get("paths", {})

    if not isinstance(paths_config, dict):
        raise ValueError("Der YAML-Bereich 'paths' muss eine Map sein.")

    return ProjectPaths(
        base_dir=base_dir,
        data_dir=_resolve_path(base_dir, paths_config.get("data_dir", "data")),
        customers_dir=_resolve_path(
            base_dir, paths_config.get("customers_dir", "customers")
        ),
        invoice_config=_resolve_path(
            base_dir, paths_config.get("invoice_config", "config/invoice.yaml")
        ),
        hours_dir=_resolve_path(base_dir, paths_config.get("hours_dir", "hours")),
        templates_dir=_resolve_path(
            base_dir, paths_config.get("templates_dir", "templates")
        ),
        img_dir=_resolve_path(base_dir, paths_config.get("image_dir", "img")),
        backup_dir=_resolve_path(base_dir, paths_config.get("backup_dir", "backup")),
    )
