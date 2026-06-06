import tempfile
from pathlib import Path


def pruefe_lesbare_datei(pfad: Path, bezeichnung: str) -> None:
    """Prueft, ob eine erwartete Datei vorhanden und lesbar ist."""
    if not pfad.exists():
        raise ValueError(f"{bezeichnung} fehlt.")
    if not pfad.is_file():
        raise ValueError(f"{bezeichnung} ist keine regulaere Datei.")
    try:
        with pfad.open("rb") as datei:
            datei.read(1)
    except OSError as err:
        raise ValueError(f"{bezeichnung} ist nicht lesbar: {err}") from err


def pruefe_lesbares_verzeichnis(pfad: Path, bezeichnung: str) -> None:
    """Prueft, ob ein erwartetes Verzeichnis vorhanden und lesbar ist."""
    if not pfad.exists():
        raise ValueError(f"{bezeichnung} fehlt.")
    if not pfad.is_dir():
        raise ValueError(f"{bezeichnung} ist kein Verzeichnis.")
    try:
        next(pfad.iterdir(), None)
    except OSError as err:
        raise ValueError(f"{bezeichnung} ist nicht lesbar: {err}") from err


def pruefe_schreibbares_zielverzeichnis(pfad: Path, bezeichnung: str) -> None:
    """Prueft ein Zielverzeichnis oder seinen naechsten vorhandenen Elternpfad."""
    pruefpfad = pfad if pfad.exists() else _naechster_vorhandener_elternpfad(pfad)
    if not pruefpfad.is_dir():
        raise ValueError(f"{bezeichnung}: '{pruefpfad}' ist kein Verzeichnis.")

    try:
        with tempfile.NamedTemporaryFile(
            prefix=".rechnung-schreibtest-",
            dir=pruefpfad,
        ) as testdatei:
            testdatei.write(b"test")
            testdatei.flush()
    except OSError as err:
        raise ValueError(f"{bezeichnung} ist nicht beschreibbar: {err}") from err


def pruefe_archiv_pfad(pfad_wert: str, schreibprobe: bool = False) -> None:
    """Prueft einen konfigurierten Kunden-Archivpfad."""
    try:
        archiv_pfad = Path(pfad_wert).expanduser()
    except (TypeError, ValueError, RuntimeError) as err:
        raise ValueError("Archivpfad ist ungueltig.") from err
    if not archiv_pfad.exists():
        raise ValueError("Archivpfad existiert nicht.")
    if not archiv_pfad.is_dir():
        raise ValueError("Archivpfad ist kein Verzeichnis.")
    pruefe_lesbares_verzeichnis(archiv_pfad, "Archivpfad")
    if schreibprobe:
        pruefe_schreibbares_zielverzeichnis(archiv_pfad, "Archivpfad")


def _naechster_vorhandener_elternpfad(pfad: Path) -> Path:
    """Ermittelt den naechsten vorhandenen Elternpfad."""
    aktueller_pfad = pfad
    while not aktueller_pfad.exists():
        if aktueller_pfad.parent == aktueller_pfad:
            raise ValueError(f"Kein vorhandener Elternpfad fuer '{pfad}' gefunden.")
        aktueller_pfad = aktueller_pfad.parent
    return aktueller_pfad
