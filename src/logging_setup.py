import logging
from datetime import datetime
from pathlib import Path

from time_utils import now


class RunErrorCollector(logging.Handler):
    """Sammelt schwere Laufmeldungen fuer den Cron-Fehlerbericht."""

    def __init__(self) -> None:
        """Initialisiert einen leeren ERROR-/CRITICAL-Sammler."""
        super().__init__(level=logging.ERROR)
        self.errors: list[dict[str, str]] = []

    def emit(self, record: logging.LogRecord) -> None:
        """Speichert eine bereinigte schwere Logmeldung."""
        self.errors.append(
            {
                "timestamp": datetime.fromtimestamp(record.created).strftime(
                    "%Y-%m-%d %H:%M:%S"
                ),
                "level": record.levelname,
                "source": record.name,
                "message": record.getMessage(),
            }
        )


def configure_logging(logging_config: dict, base_dir: Path) -> Path | None:
    """Konfiguriert Konsolen- und optional Datei-Logging."""
    if not isinstance(logging_config, dict):
        raise ValueError("Der YAML-Bereich 'logging' muss eine Map sein.")

    logger = logging.getLogger()
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
        handler.close()

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
    while True:
        log_file = _create_log_path(log_dir)
        try:
            file_handler = logging.FileHandler(log_file, mode="x", encoding="utf-8")
            break
        except FileExistsError:
            continue
    file_handler.setFormatter(formatter)
    file_handler.setLevel(level)
    logger.addHandler(file_handler)

    return log_file


def activate_run_error_collector() -> RunErrorCollector:
    """Haengt einen Sammler fuer ERROR- und CRITICAL-Meldungen ein."""
    collector = RunErrorCollector()
    logging.getLogger().addHandler(collector)
    return collector


def _resolve_log_dir(base_dir: Path, log_dir_value: str) -> Path:
    """Erzeugt den absoluten Log-Pfad aus Projektroot und Einstellung."""
    log_dir = Path(log_dir_value)
    return log_dir if log_dir.is_absolute() else base_dir / log_dir


def _create_log_path(log_dir: Path) -> Path:
    """Erzeugt einen lesbaren und kollisionsfreien Dateinamen fuer den Lauf."""
    base = f"invoice-{now():%Y-%m-%d_%H-%M-%S}"
    log_file = log_dir / f"{base}.log"
    number = 2
    while log_file.exists():
        log_file = log_dir / f"{base}-{number:02d}.log"
        number += 1
    return log_file
