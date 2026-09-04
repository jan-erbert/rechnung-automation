import json
import os
from pathlib import Path

from time_utils import now

IS_WINDOWS = os.name == "nt"


class _LockUnavailableError(OSError):
    """Kennzeichnet eine bereits durch einen anderen Prozess gehaltene Sperre."""


class RunLock:
    """Verhindert parallele Rechnungsläufe mit einer Betriebssystem-Dateisperre."""

    def __init__(self, path: Path) -> None:
        """Initialisiert die Sperre fuer den angegebenen Pfad."""
        self.path = path
        self._descriptor: int | None = None

    def __enter__(self):
        """Oeffnet die Lockdatei und haelt sie bis zum Verlassen exklusiv gesperrt."""
        if self._descriptor is not None:
            raise RuntimeError("Diese Rechnungslauf-Sperre ist bereits aktiv.")

        self.path.parent.mkdir(parents=True, exist_ok=True)
        descriptor = os.open(self.path, os.O_RDWR | os.O_CREAT, 0o600)
        try:
            _ensure_lock_byte(descriptor)
            _lock_descriptor(descriptor)
        except _LockUnavailableError as err:
            os.close(descriptor)
            raise RuntimeError(
                "Ein weiterer Rechnungslauf ist bereits aktiv. "
                f"Sperrdatei: {self.path}"
            ) from err
        except BaseException:
            os.close(descriptor)
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
            raise

        self._descriptor = descriptor
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        """Gibt die Betriebssystem-Sperre frei und schliesst die Lockdatei."""
        descriptor = self._descriptor
        if descriptor is None:
            return
        self._descriptor = None
        try:
            _unlock_descriptor(descriptor)
        finally:
            os.close(descriptor)


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
