import json
import os

import pytest

from run_lock import RunLock


def test_run_lock_blocks_parallel_run(tmp_path):
    """Eine aktive Sperre verhindert einen zweiten Rechnungslauf."""
    path = tmp_path / ".invoice-run.lock"
    with RunLock(path):
        with pytest.raises(RuntimeError, match="bereits aktiv"):
            with RunLock(path):
                pass
    assert not path.exists()


def test_run_lock_recovers_stale_process(tmp_path):
    """Eine eindeutig verwaiste PID-Sperre wird automatisch ersetzt."""
    path = tmp_path / ".invoice-run.lock"
    path.write_text(
        json.dumps({"pid": 99999999, "started_at": "2026-01-01T00:00:00"}),
        encoding="utf-8",
    )
    with RunLock(path):
        assert json.loads(path.read_text(encoding="utf-8"))["pid"] == os.getpid()
    assert not path.exists()


def test_run_lock_removes_incomplete_file_after_write_error(tmp_path, monkeypatch):
    """Ein Fehler beim Sperren hinterlaesst keine ungueltige Lockdatei."""
    path = tmp_path / ".invoice-run.lock"

    def fail_write(*args):
        """Simuliert einen Dateisystemfehler beim Schreiben der Sperre."""
        raise OSError("write failed")

    monkeypatch.setattr("run_lock.os.write", fail_write)

    with pytest.raises(OSError, match="write failed"):
        with RunLock(path):
            pass

    assert not path.exists()
