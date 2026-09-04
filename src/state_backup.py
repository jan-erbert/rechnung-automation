import hashlib
import json
import os
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path, PurePosixPath

from paths import ProjectPaths
from time_utils import now

BACKUP_FORMAT_VERSION = 1
BACKUP_PATTERN = "state-backup-*.zip"


def validate_backup_config(config: dict) -> dict:
    """Prueft die Einstellungen fuer automatische Zustandsbackups."""
    if not isinstance(config, dict):
        raise ValueError("Der YAML-Bereich 'backup' muss eine Map sein.")
    enabled = config.get("enabled", True)
    if not isinstance(enabled, bool):
        raise ValueError("backup.enabled muss true oder false sein.")
    keep_last = config.get("keep_last", 30)
    if isinstance(keep_last, bool) or not isinstance(keep_last, int) or keep_last < 1:
        raise ValueError("backup.keep_last muss eine positive ganze Zahl sein.")
    return {"enabled": enabled, "keep_last": keep_last}


def create_state_backup(
    paths: ProjectPaths,
    keep_last: int = 30,
    timestamp: datetime | None = None,
) -> Path:
    """Sichert den lokalen Anwendungszustand in einem geprueften ZIP-Archiv."""
    keep_last = validate_backup_config({"keep_last": keep_last})["keep_last"]

    files = _collect_state_files(paths)
    if not files:
        raise ValueError("Es wurden keine sicherungsfaehigen Zustandsdateien gefunden.")

    paths.backup_dir.mkdir(parents=True, exist_ok=True)
    _set_private_directory_permissions(paths.backup_dir)
    created_at = timestamp or now()
    target = _next_backup_path(paths.backup_dir, created_at)
    temporary_path = None
    try:
        with tempfile.NamedTemporaryFile(
            "w+b",
            dir=paths.backup_dir,
            prefix=".state-backup-",
            suffix=".tmp",
            delete=False,
        ) as temporary_file:
            temporary_path = Path(temporary_file.name)

        manifest_files = []
        with zipfile.ZipFile(
            temporary_path,
            "w",
            compression=zipfile.ZIP_DEFLATED,
        ) as backup:
            for archive_name, source in files:
                content = source.read_bytes()
                backup.writestr(archive_name, content)
                manifest_files.append(
                    {
                        "path": archive_name,
                        "size": len(content),
                        "sha256": hashlib.sha256(content).hexdigest(),
                    }
                )
            manifest = {
                "format_version": BACKUP_FORMAT_VERSION,
                "created_at": created_at.isoformat(timespec="seconds"),
                "files": manifest_files,
            }
            backup.writestr(
                "manifest.json",
                json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
            )

        verify_state_backup(temporary_path)
        _set_private_file_permissions(temporary_path)
        os.replace(temporary_path, target)
    finally:
        if temporary_path and temporary_path.exists():
            temporary_path.unlink()

    _prune_backups(paths.backup_dir, keep_last)
    return target


def verify_state_backup(backup_path: Path) -> dict:
    """Prueft Manifest, Pfade, Groessen und Hashwerte eines Zustandsbackups."""
    try:
        with zipfile.ZipFile(backup_path, "r") as backup:
            names = backup.namelist()
            if len(names) != len(set(names)):
                raise ValueError("Backup enthaelt doppelte Dateipfade.")
            if "manifest.json" not in names:
                raise ValueError("Backup enthaelt kein manifest.json.")
            for name in names:
                _validate_archive_name(name)
            try:
                manifest = json.loads(backup.read("manifest.json"))
            except (KeyError, json.JSONDecodeError, UnicodeDecodeError) as err:
                raise ValueError("Backup-Manifest ist ungueltig.") from err
            _validate_manifest(manifest, names)
            for entry in manifest["files"]:
                content = backup.read(entry["path"])
                if len(content) != entry["size"]:
                    raise ValueError(
                        f"Backup-Datei '{entry['path']}' hat eine falsche Groesse."
                    )
                digest = hashlib.sha256(content).hexdigest()
                if digest != entry["sha256"]:
                    raise ValueError(
                        f"Backup-Datei '{entry['path']}' hat einen falschen Hashwert."
                    )
    except (OSError, zipfile.BadZipFile) as err:
        raise ValueError(
            f"Backup '{backup_path}' ist nicht lesbar oder beschaedigt."
        ) from err
    return manifest


def restore_state_backup(backup_path: Path, destination: Path) -> list[Path]:
    """Stellt ein geprueftes Backup ausschliesslich in ein leeres Ziel wieder her."""
    manifest = verify_state_backup(backup_path)
    if destination.exists():
        if not destination.is_dir():
            raise ValueError("Wiederherstellungsziel muss ein Verzeichnis sein.")
        if any(destination.iterdir()):
            raise ValueError("Wiederherstellungsziel muss leer sein.")
    destination.mkdir(parents=True, exist_ok=True)
    _set_private_directory_permissions(destination)

    restored = []
    with zipfile.ZipFile(backup_path, "r") as backup:
        for entry in manifest["files"]:
            relative_path = PurePosixPath(entry["path"])
            target = destination.joinpath(*relative_path.parts)
            target.parent.mkdir(parents=True, exist_ok=True)
            _set_private_directory_permissions(target.parent)
            with target.open("xb") as restored_file:
                restored_file.write(backup.read(entry["path"]))
            _set_private_file_permissions(target)
            restored.append(target)
    return restored


def _collect_state_files(paths: ProjectPaths) -> list[tuple[str, Path]]:
    """Sammelt die fuer einen sicheren Wiederanlauf erforderlichen Dateien."""
    candidates = []
    if paths.invoice_config.is_file():
        candidates.append(("config/invoice.yaml", paths.invoice_config))
    candidates.extend(
        (f"customers/{path.name}", path)
        for path in _regular_files(paths.customers_dir, ("*.yaml", "*.yml"))
    )
    candidates.extend(
        (f"hours/{path.name}", path)
        for path in _regular_files(paths.hours_dir, ("*.yaml",))
    )
    candidates.extend(
        (f"data/{path.name}", path)
        for path in _regular_files(paths.data_dir, ("invoice-history-*.json",))
    )
    return sorted(candidates, key=lambda item: item[0])


def _regular_files(directory: Path, patterns: tuple[str, ...]) -> list[Path]:
    """Liefert regulaere, nicht symbolische Dateien aus einem Verzeichnis."""
    if not directory.is_dir():
        return []
    files = []
    for pattern in patterns:
        files.extend(
            path
            for path in directory.glob(pattern)
            if path.is_file() and not path.is_symlink()
        )
    return sorted(set(files))


def _next_backup_path(backup_dir: Path, timestamp: datetime) -> Path:
    """Erzeugt einen kollisionsfreien Namen fuer ein Zustandsbackup."""
    base = f"state-backup-{timestamp:%Y-%m-%d_%H-%M-%S}"
    target = backup_dir / f"{base}.zip"
    number = 2
    while target.exists():
        target = backup_dir / f"{base}-{number:02d}.zip"
        number += 1
    return target


def _prune_backups(backup_dir: Path, keep_last: int) -> None:
    """Entfernt ausschliesslich ueberzaehlige eigene Zustandsbackups."""
    backups = sorted(backup_dir.glob(BACKUP_PATTERN), key=lambda path: path.name)
    for obsolete in backups[:-keep_last]:
        if obsolete.is_file() and not obsolete.is_symlink():
            obsolete.unlink()


def _validate_archive_name(name: str) -> None:
    """Verwirft absolute Pfade und Traversal-Sequenzen in Backups."""
    if not isinstance(name, str) or not name:
        raise ValueError("Backup enthaelt einen ungueltigen Dateipfad.")
    path = PurePosixPath(name)
    if path.is_absolute() or ".." in path.parts or not path.parts:
        raise ValueError(f"Unsicherer Pfad im Backup: '{name}'.")


def _validate_manifest(manifest, names: list[str]) -> None:
    """Prueft die erwartete Manifeststruktur eines Backups."""
    if not isinstance(manifest, dict) or manifest.get("format_version") != 1:
        raise ValueError("Backup-Manifest verwendet ein unbekanntes Format.")
    entries = manifest.get("files")
    if not isinstance(entries, list) or not entries:
        raise ValueError("Backup-Manifest enthaelt keine Dateien.")
    paths = []
    for entry in entries:
        if not isinstance(entry, dict):
            raise ValueError("Backup-Manifest enthaelt einen ungueltigen Eintrag.")
        if set(entry) != {"path", "size", "sha256"}:
            raise ValueError("Backup-Manifest enthaelt unbekannte Felder.")
        _validate_archive_name(entry["path"])
        if not isinstance(entry["size"], int) or entry["size"] < 0:
            raise ValueError("Backup-Manifest enthaelt eine ungueltige Dateigroesse.")
        if not isinstance(entry["sha256"], str) or len(entry["sha256"]) != 64:
            raise ValueError("Backup-Manifest enthaelt einen ungueltigen Hashwert.")
        paths.append(entry["path"])
    if len(paths) != len(set(paths)):
        raise ValueError("Backup-Manifest enthaelt doppelte Dateipfade.")
    if set(names) != {"manifest.json", *paths}:
        raise ValueError("Backup-Inhalt stimmt nicht mit dem Manifest ueberein.")


def _set_private_directory_permissions(path: Path) -> None:
    """Setzt unterstuetzte lokale Verzeichnisrechte auf nur den Besitzer."""
    try:
        os.chmod(path, 0o700)
    except OSError:
        return


def _set_private_file_permissions(path: Path) -> None:
    """Setzt unterstuetzte lokale Dateirechte auf nur den Besitzer."""
    try:
        os.chmod(path, 0o600)
    except OSError:
        return
