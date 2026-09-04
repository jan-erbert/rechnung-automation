import json
import os
from pathlib import Path

from time_utils import now


class RunLock:
    """Verhindert parallele Rechnungsläufe ueber eine exklusive Lockdatei."""

    def __init__(self, path: Path) -> None:
        """Initialisiert die Sperre fuer den angegebenen Pfad."""
        self.path = path
        self._acquired = False

    def __enter__(self):
        """Legt die Lockdatei exklusiv an."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._remove_stale_lock()
        try:
            descriptor = os.open(self.path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        except FileExistsError as err:
            raise RuntimeError(
                "Ein weiterer Rechnungslauf ist bereits aktiv. "
                f"Sperrdatei: {self.path}"
            ) from err
        try:
            payload = json.dumps(
                {"pid": os.getpid(), "started_at": now().isoformat(timespec="seconds")}
            ).encode("utf-8")
            os.write(descriptor, payload)
            os.fsync(descriptor)
            self._acquired = True
        except BaseException:
            self.path.unlink(missing_ok=True)
            raise
        finally:
            os.close(descriptor)
        return self

    def _remove_stale_lock(self) -> None:
        """Entfernt eine eindeutig verwaiste Sperre nach einem Prozessabbruch."""
        if not self.path.exists():
            return
        try:
            lock_data = json.loads(self.path.read_text(encoding="utf-8"))
            process_id = int(lock_data["pid"])
            os.kill(process_id, 0)
        except ProcessLookupError:
            self.path.unlink(missing_ok=True)
        except FileNotFoundError:
            return
        except (KeyError, TypeError, ValueError, json.JSONDecodeError):
            raise RuntimeError(
                f"Sperrdatei '{self.path}' ist ungueltig und muss geprueft werden."
            )
        except PermissionError:
            return

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        """Gibt eine erfolgreich erworbene Sperre wieder frei."""
        if self._acquired:
            self.path.unlink(missing_ok=True)
            self._acquired = False
