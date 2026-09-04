import pytest

from path_checks import (
    check_archive_path,
    check_readable_file,
    check_writable_target_directory,
)


def test_readable_file_rejects_directory(tmp_path):
    """Ein Verzeichnis wird nicht als erwartete Datei akzeptiert."""
    with pytest.raises(ValueError, match="keine regulaere Datei"):
        check_readable_file(tmp_path, "Testdatei")


def test_write_probe_leaves_no_file(tmp_path):
    """Die Schreibprobe entfernt ihre temporaere Datei sofort wieder."""
    ziel = tmp_path / "noch-nicht-vorhanden"

    check_writable_target_directory(ziel, "Zielverzeichnis")

    assert list(tmp_path.iterdir()) == []


def test_archive_path_requires_existing_directory(tmp_path):
    """Ein Kundenarchiv muss als erreichbares Verzeichnis existieren."""
    archive_path = tmp_path / "archiv"

    with pytest.raises(ValueError, match="existiert nicht"):
        check_archive_path(str(archive_path))


def test_archive_write_probe_accepts_directory(tmp_path):
    """Ein beschreibbares Archiv besteht die echte Schreibprobe."""
    archive_path = tmp_path / "archiv"
    archive_path.mkdir()

    check_archive_path(str(archive_path), write_probe=True)

    assert list(archive_path.iterdir()) == []
