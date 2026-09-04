import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from legacy_migration import migrate_legacy_layout  # noqa: E402
from paths import create_paths  # noqa: E402
from settings_loader import load_settings  # noqa: E402


def main() -> int:
    """Migriert beim Setup erkannte Legacy-Dateien ohne Quellen zu loeschen."""
    try:
        settings = load_settings(PROJECT_ROOT / "config" / "settings.yaml")
        paths = create_paths(settings, PROJECT_ROOT)
        actions = migrate_legacy_layout(PROJECT_ROOT, paths)
    except (FileNotFoundError, OSError, ValueError) as err:
        print(f"Legacy-Migration fehlgeschlagen: {err}", file=sys.stderr)
        print(
            "Die alten Quelldateien wurden nicht geloescht. "
            "Bitte den genannten Konflikt korrigieren und erneut starten.",
            file=sys.stderr,
        )
        return 1
    if actions:
        print("Legacy-Struktur wurde erfolgreich migriert:")
        for action in actions:
            print(f"- {action}")
    else:
        print("Keine ausstehende Legacy-Migration gefunden.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
