import json
import os
import stat
import zipfile
from datetime import datetime

import pytest

from paths import create_paths
from state_backup import (
    create_state_backup,
    restore_state_backup,
    validate_backup_config,
    verify_state_backup,
)


def _paths(tmp_path):
    """Erzeugt vollstaendig isolierte Projektpfade fuer Backuptests."""
    return create_paths({}, tmp_path)


def _write_state(paths) -> None:
    """Schreibt einen kleinen, repraesentativen Anwendungszustand."""
    paths.invoice_config.parent.mkdir(parents=True)
    paths.invoice_config.write_text("sender: {}\n", encoding="utf-8")
    paths.customers_dir.mkdir()
    (paths.customers_dir / "example.yaml").write_text("id: example\n", encoding="utf-8")
    paths.hours_dir.mkdir()
    (paths.hours_dir / "2026-08.yaml").write_text(
        'period: "2026-08"\n', encoding="utf-8"
    )
    paths.data_dir.mkdir()
    (paths.data_dir / "invoice-history-2026.json").write_text("[]\n", encoding="utf-8")


def test_backup_is_verified_private_and_restorable(tmp_path):
    """Ein Zustandsbackup laesst sich geprueft in ein leeres Ziel entpacken."""
    paths = _paths(tmp_path)
    _write_state(paths)

    backup = create_state_backup(
        paths,
        timestamp=datetime(2026, 9, 4, 12, 0, 0),
    )
    manifest = verify_state_backup(backup)
    restored = restore_state_backup(backup, tmp_path / "restored")

    assert backup.name == "state-backup-2026-09-04_12-00-00.zip"
    assert len(manifest["files"]) == 4
    assert len(restored) == 4
    assert (tmp_path / "restored/customers/example.yaml").read_text(
        encoding="utf-8"
    ) == "id: example\n"
    if os.name == "posix":
        assert stat.S_IMODE(backup.stat().st_mode) == 0o600


def test_backup_retention_keeps_newest_archives(tmp_path):
    """Die Sicherungsaufbewahrung entfernt nur die aeltesten Backups."""
    paths = _paths(tmp_path)
    _write_state(paths)

    first = create_state_backup(
        paths,
        keep_last=2,
        timestamp=datetime(2026, 9, 4, 10, 0, 0),
    )
    second = create_state_backup(
        paths,
        keep_last=2,
        timestamp=datetime(2026, 9, 4, 11, 0, 0),
    )
    third = create_state_backup(
        paths,
        keep_last=2,
        timestamp=datetime(2026, 9, 4, 12, 0, 0),
    )

    assert not first.exists()
    assert second.exists()
    assert third.exists()


def test_restore_refuses_nonempty_destination(tmp_path):
    """Eine Wiederherstellung ueberschreibt keine vorhandenen Dateien."""
    paths = _paths(tmp_path)
    _write_state(paths)
    backup = create_state_backup(paths)
    destination = tmp_path / "restored"
    destination.mkdir()
    (destination / "keep.txt").write_text("behalten", encoding="utf-8")

    with pytest.raises(ValueError, match="muss leer sein"):
        restore_state_backup(backup, destination)


def test_verify_rejects_manifest_mismatch(tmp_path):
    """Zusaetzliche oder manipulierte Inhalte machen ein Backup ungueltig."""
    backup = tmp_path / "broken.zip"
    manifest = {
        "format_version": 1,
        "created_at": "2026-09-04T12:00:00",
        "files": [
            {
                "path": "data/invoice-history-2026.json",
                "size": 3,
                "sha256": "0" * 64,
            }
        ],
    }
    with zipfile.ZipFile(backup, "w") as archive:
        archive.writestr("manifest.json", json.dumps(manifest))
        archive.writestr("data/invoice-history-2026.json", "[]\n")

    with pytest.raises(ValueError, match="falschen Hashwert"):
        verify_state_backup(backup)


@pytest.mark.parametrize(
    "config",
    (
        {"enabled": "yes"},
        {"keep_last": 0},
        {"keep_last": True},
    ),
)
def test_backup_config_rejects_unsafe_values(config):
    """Fehlerhafte Backup-Schalter werden vor einem Rechnungslauf abgelehnt."""
    with pytest.raises(ValueError):
        validate_backup_config(config)
