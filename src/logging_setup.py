import logging
from datetime import datetime
from pathlib import Path

from zeit import jetzt


class LauffehlerSammler(logging.Handler):
    """Sammelt schwere Laufmeldungen fuer den Cron-Fehlerbericht."""

    def __init__(self) -> None:
        """Initialisiert einen leeren ERROR-/CRITICAL-Sammler."""
        super().__init__(level=logging.ERROR)
        self.fehler: list[dict[str, str]] = []

    def emit(self, record: logging.LogRecord) -> None:
        """Speichert eine bereinigte schwere Logmeldung."""
        self.fehler.append(
            {
                "zeit": datetime.fromtimestamp(record.created).strftime(
                    "%Y-%m-%d %H:%M:%S"
                ),
                "level": record.levelname,
                "quelle": record.name,
                "meldung": record.getMessage(),
            }
        )


def konfiguriere_logging(logging_config: dict, base_dir: Path) -> Path | None:
    """Konfiguriert Konsolen- und optional Datei-Logging."""
    if not isinstance(logging_config, dict):
        raise ValueError("Der YAML-Bereich 'logging' muss eine Map sein.")

    logger = logging.getLogger()
    logger.handlers.clear()

    level_name = str(logging_config.get("level", "INFO")).upper()
    level = getattr(logging, level_name, logging.INFO)
    logger.setLevel(level)

    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(level)
    logger.addHandler(console_handler)

    if logging_config.get("enabled", True) is False:
        return None

    log_dir = _resolve_log_dir(base_dir, logging_config.get("directory", "logs"))
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / f"rechnung-{jetzt():%Y%m%d-%H%M%S}.log"

    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setFormatter(formatter)
    file_handler.setLevel(level)
    logger.addHandler(file_handler)

    return log_file


def aktiviere_lauffehler_sammler() -> LauffehlerSammler:
    """Haengt einen Sammler fuer ERROR- und CRITICAL-Meldungen ein."""
    sammler = LauffehlerSammler()
    logging.getLogger().addHandler(sammler)
    return sammler


def _resolve_log_dir(base_dir: Path, log_dir_value: str) -> Path:
    """Erzeugt den absoluten Log-Pfad aus Projektroot und Einstellung."""
    log_dir = Path(log_dir_value)
    return log_dir if log_dir.is_absolute() else base_dir / log_dir
