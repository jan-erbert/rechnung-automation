import json
import os
import sys
from types import SimpleNamespace

import pytest

import run_lock
from run_lock import RunLock


def test_run_lock_blocks_parallel_run(tmp_path):
    """Eine aktive Sperre verhindert einen zweiten Rechnungslauf."""
    path = tmp_path / ".invoice-run.lock"
    with RunLock(path):
        with pytest.raises(RuntimeError, match="bereits aktiv"):
            with RunLock(path):
                pass
    assert path.exists()


def test_run_lock_reuses_unlocked_file_without_process_probe(tmp_path, monkeypatch):
    """Eine alte Lockdatei wird ohne Eingriff in den genannten Prozess genutzt."""
    path = tmp_path / ".invoice-run.lock"
    path.write_text(
        json.dumps({"pid": os.getpid(), "started_at": "2026-01-01T00:00:00"}),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        os,
        "kill",
        lambda *args: pytest.fail("RunLock darf keine Prozesssignale verwenden."),
    )

    with RunLock(path):
        assert json.loads(path.read_text(encoding="utf-8"))["pid"] == os.getpid()
    assert path.exists()


def test_run_lock_releases_file_after_write_error(tmp_path, monkeypatch):
    """Ein Schreibfehler gibt die Sperre fuer einen spaeteren Lauf wieder frei."""
    path = tmp_path / ".invoice-run.lock"
    path.write_bytes(b"\0")

    def fail_write(*args):
        """Simuliert einen Dateisystemfehler beim Schreiben der Sperre."""
        raise OSError("write failed")

    monkeypatch.setattr("run_lock.os.write", fail_write)

    with pytest.raises(OSError, match="write failed"):
        with RunLock(path):
            pass

    monkeypatch.undo()
    with RunLock(path):
        assert json.loads(path.read_text(encoding="utf-8"))["pid"] == os.getpid()


def test_windows_lock_uses_msvcrt_without_process_signal(monkeypatch):
    """Der Windows-Pfad sperrt und entsperrt ausschliesslich per msvcrt."""
    calls = []
    fake_msvcrt = SimpleNamespace(
        LK_NBLCK=1,
        LK_UNLCK=2,
        locking=lambda descriptor, mode, length: calls.append(
            (descriptor, mode, length)
        ),
    )
    monkeypatch.setitem(sys.modules, "msvcrt", fake_msvcrt)
    monkeypatch.setattr(run_lock, "IS_WINDOWS", True)
    monkeypatch.setattr(run_lock.os, "lseek", lambda *args: 0)
    monkeypatch.setattr(
        os,
        "kill",
        lambda *args: pytest.fail("RunLock darf keine Prozesssignale verwenden."),
    )

    run_lock._lock_descriptor(7)
    run_lock._unlock_descriptor(7)

    assert calls == [(7, fake_msvcrt.LK_NBLCK, 1), (7, fake_msvcrt.LK_UNLCK, 1)]


def test_windows_lock_contention_is_reported(monkeypatch):
    """Ein belegter Windows-Lock wird als nicht verfuegbar eingeordnet."""

    def fail_lock(descriptor, mode, length):
        """Simuliert eine bereits gesperrte Datei unter Windows."""
        raise OSError("locked")

    fake_msvcrt = SimpleNamespace(LK_NBLCK=1, locking=fail_lock)
    monkeypatch.setitem(sys.modules, "msvcrt", fake_msvcrt)
    monkeypatch.setattr(run_lock, "IS_WINDOWS", True)

    with pytest.raises(run_lock._LockUnavailableError):
        run_lock._lock_descriptor(7)
