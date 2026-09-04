import json
import os
import threading
from pathlib import Path

from time_utils import now

IS_WINDOWS = os.name == "nt"
_ACTIVE_LOCKS: set[Path] = set()
_ACTIVE_LOCKS_GUARD = threading.Lock()


class _LockUnavailableError(OSError):
    """Kennzeichnet eine bereits durch einen anderen Prozess gehaltene Sperre."""


class RunLock:
    """Verhindert parallele Rechnungsläufe mit einer Betriebssystem-Dateisperre."""

    def __init__(self, path: Path) -> None:
        """Initialisiert die Sperre fuer den angegebenen Pfad."""
        self.path = path
        self._descriptor: int | None = None
        self._registry_path: Path | None = None

    def __enter__(self):
        """Oeffnet die Lockdatei und haelt sie bis zum Verlassen exklusiv gesperrt."""
        if self._descriptor is not None:
            raise RuntimeError("Diese Rechnungslauf-Sperre ist bereits aktiv.")

        registry_path = self.path.resolve()
        with _ACTIVE_LOCKS_GUARD:
            if registry_path in _ACTIVE_LOCKS:
                raise RuntimeError(
                    "Ein weiterer Rechnungslauf ist bereits aktiv. "
                    f"Sperrdatei: {self.path}"
                )
            _ACTIVE_LOCKS.add(registry_path)

        self.path.parent.mkdir(parents=True, exist_ok=True)
        try:
            descriptor = os.open(self.path, os.O_RDWR | os.O_CREAT, 0o600)
        except BaseException:
            _release_process_lock(registry_path)
            raise
        try:
            _ensure_lock_byte(descriptor)
            _lock_descriptor(descriptor)
        except _LockUnavailableError as err:
            os.close(descriptor)
            _release_process_lock(registry_path)
            raise RuntimeError(
                "Ein weiterer Rechnungslauf ist bereits aktiv. "
                f"Sperrdatei: {self.path}"
            ) from err
        except BaseException:
            os.close(descriptor)
            _release_process_lock(registry_path)
            raise

        try:
            payload = json.dumps(
                {"pid": os.getpid(), "started_at": now().isoformat(timespec="seconds")}
            ).encode("utf-8")
            os.lseek(descriptor, 0, os.SEEK_SET)
            os.ftruncate(descriptor, 0)
            os.write(descriptor, payload)
            os.fsync(descriptor)
        except BaseException:
            try:
                _unlock_descriptor(descriptor)
            finally:
                os.close(descriptor)
                _release_process_lock(registry_path)
            raise

        self._descriptor = descriptor
        self._registry_path = registry_path
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        """Gibt die Betriebssystem-Sperre frei und schliesst die Lockdatei."""
        descriptor = self._descriptor
        registry_path = self._registry_path
        if descriptor is None:
            return
        self._descriptor = None
        self._registry_path = None
        try:
            _unlock_descriptor(descriptor)
        finally:
            try:
                os.close(descriptor)
            finally:
                if registry_path is not None:
                    _release_process_lock(registry_path)


def _release_process_lock(path: Path) -> None:
    """Entfernt eine prozesslokale Sperrreservierung sicher."""
    with _ACTIVE_LOCKS_GUARD:
        _ACTIVE_LOCKS.discard(path)


def _ensure_lock_byte(descriptor: int) -> None:
    """Stellt fuer die bytebasierte Windows-Sperre einen sperrbaren Bereich bereit."""
    if os.fstat(descriptor).st_size == 0:
        os.write(descriptor, b"\0")
        os.fsync(descriptor)
    os.lseek(descriptor, 0, os.SEEK_SET)


def _lock_descriptor(descriptor: int) -> None:
    """Sperrt einen offenen Dateideskriptor ohne auf die Freigabe zu warten."""
    if IS_WINDOWS:
        import msvcrt

        try:
            msvcrt.locking(descriptor, msvcrt.LK_NBLCK, 1)
        except OSError as err:
            raise _LockUnavailableError from err
        return

    import fcntl

    try:
        fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError as err:
        raise _LockUnavailableError from err


def _unlock_descriptor(descriptor: int) -> None:
    """Gibt eine zuvor gesetzte Betriebssystem-Dateisperre frei."""
    os.lseek(descriptor, 0, os.SEEK_SET)
    if IS_WINDOWS:
        import msvcrt

        msvcrt.locking(descriptor, msvcrt.LK_UNLCK, 1)
        return

    import fcntl

    fcntl.flock(descriptor, fcntl.LOCK_UN)
