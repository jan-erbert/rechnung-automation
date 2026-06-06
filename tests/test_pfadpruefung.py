import pytest

from pfadpruefung import (
    pruefe_archiv_pfad,
    pruefe_lesbare_datei,
    pruefe_schreibbares_zielverzeichnis,
)


def test_readable_file_rejects_directory(tmp_path):
    """Ein Verzeichnis wird nicht als erwartete Datei akzeptiert."""
    with pytest.raises(ValueError, match="keine regulaere Datei"):
        pruefe_lesbare_datei(tmp_path, "Testdatei")


def test_write_probe_leaves_no_file(tmp_path):
    """Die Schreibprobe entfernt ihre temporaere Datei sofort wieder."""
    ziel = tmp_path / "noch-nicht-vorhanden"

    pruefe_schreibbares_zielverzeichnis(ziel, "Zielverzeichnis")

    assert list(tmp_path.iterdir()) == []


def test_archive_path_requires_existing_directory(tmp_path):
    """Ein Kundenarchiv muss als erreichbares Verzeichnis existieren."""
    archiv_pfad = tmp_path / "archiv"

    with pytest.raises(ValueError, match="existiert nicht"):
        pruefe_archiv_pfad(str(archiv_pfad))


def test_archive_write_probe_accepts_directory(tmp_path):
    """Ein beschreibbares Archiv besteht die echte Schreibprobe."""
    archiv_pfad = tmp_path / "archiv"
    archiv_pfad.mkdir()

    pruefe_archiv_pfad(str(archiv_pfad), schreibprobe=True)

    assert list(archiv_pfad.iterdir()) == []
