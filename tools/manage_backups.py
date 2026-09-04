import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from paths import create_paths  # noqa: E402
from settings_loader import load_settings  # noqa: E402
from state_backup import (  # noqa: E402
    create_state_backup,
    restore_state_backup,
    validate_backup_config,
    verify_state_backup,
)


def parse_args() -> argparse.Namespace:
    """Liest Aktion und Pfade fuer die Backup-Verwaltung."""
    parser = argparse.ArgumentParser(description="Lokale Zustandsbackups verwalten.")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("create", help="Erstellt ein neues Zustandsbackup.")
    verify = subparsers.add_parser("verify", help="Prueft ein vorhandenes Backup.")
    verify.add_argument("backup", type=Path)
    restore = subparsers.add_parser(
        "restore",
        help="Stellt ein Backup in einem neuen oder leeren Zielverzeichnis wieder her.",
    )
    restore.add_argument("backup", type=Path)
    restore.add_argument("destination", type=Path)
    return parser.parse_args()


def main() -> int:
    """Fuehrt die angeforderte sichere Backup-Aktion aus."""
    args = parse_args()
    try:
        if args.command == "create":
            settings = load_settings()
            paths = create_paths(settings)
            backup_config = validate_backup_config(settings.get("backup", {}))
            backup = create_state_backup(
                paths,
                keep_last=backup_config.get("keep_last", 30),
            )
            print(f"Backup erstellt und verifiziert: {backup}")
        elif args.command == "verify":
            manifest = verify_state_backup(args.backup)
            print(
                "Backup erfolgreich verifiziert: " f"{len(manifest['files'])} Dateien."
            )
        else:
            restored = restore_state_backup(args.backup, args.destination)
            print(
                "Backup sicher wiederhergestellt: "
                f"{len(restored)} Dateien unter {args.destination}"
            )
    except (OSError, ValueError) as err:
        print(f"Backup-Aktion fehlgeschlagen: {err}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
