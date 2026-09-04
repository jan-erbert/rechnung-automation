import tempfile
from pathlib import Path


def check_readable_file(path: Path, label: str) -> None:
    """Prueft, ob eine erwartete Datei vorhanden und lesbar ist."""
    if not path.exists():
        raise ValueError(f"{label} fehlt.")
    if not path.is_file():
        raise ValueError(f"{label} ist keine regulaere Datei.")
    try:
        with path.open("rb") as datei:
            datei.read(1)
    except OSError as err:
        raise ValueError(f"{label} ist nicht lesbar: {err}") from err


def check_readable_directory(path: Path, label: str) -> None:
    """Prueft, ob ein erwartetes Verzeichnis vorhanden und lesbar ist."""
    if not path.exists():
        raise ValueError(f"{label} fehlt.")
    if not path.is_dir():
        raise ValueError(f"{label} ist kein Verzeichnis.")
    try:
        next(path.iterdir(), None)
    except OSError as err:
        raise ValueError(f"{label} ist nicht lesbar: {err}") from err


def check_writable_target_directory(path: Path, label: str) -> None:
    """Prueft ein Zielverzeichnis oder seinen naechsten vorhandenen Elternpfad."""
    probe_path = path if path.exists() else _nearest_existing_parent(path)
    if not probe_path.is_dir():
        raise ValueError(f"{label}: '{probe_path}' ist kein Verzeichnis.")

    try:
        with tempfile.NamedTemporaryFile(
            prefix=".invoice-write-test-",
            dir=probe_path,
        ) as testdatei:
            testdatei.write(b"test")
            testdatei.flush()
    except OSError as err:
        raise ValueError(f"{label} ist nicht beschreibbar: {err}") from err


def check_archive_path(path_value: str, write_probe: bool = False) -> None:
    """Prueft einen konfigurierten Kunden-Archivpfad."""
    try:
        archive_path = Path(path_value).expanduser()
    except (TypeError, ValueError, RuntimeError) as err:
        raise ValueError("Archivpfad ist ungueltig.") from err
    if not archive_path.exists():
        raise ValueError("Archivpfad existiert nicht.")
    if not archive_path.is_dir():
        raise ValueError("Archivpfad ist kein Verzeichnis.")
    check_readable_directory(archive_path, "Archivpfad")
    if write_probe:
        check_writable_target_directory(archive_path, "Archivpfad")


def _nearest_existing_parent(path: Path) -> Path:
    """Ermittelt den naechsten vorhandenen Elternpfad."""
    current_path = path
    while not current_path.exists():
        if current_path.parent == current_path:
            raise ValueError(f"Kein vorhandener Elternpfad fuer '{path}' gefunden.")
        current_path = current_path.parent
    return current_path
