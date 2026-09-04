import logging
import os
from datetime import datetime
from pathlib import Path

from time_utils import now

VALID_LOG_LEVELS = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
VALID_RUN_MODES = {"interactive", "cron", "dry-run", "preview", "tool"}


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


def configure_logging(
    logging_config: dict,
    base_dir: Path,
    run_mode: str = "tool",
) -> Path | None:
    """Konfiguriert Konsolen- und optional Datei-Logging."""
    if not isinstance(logging_config, dict):
        raise ValueError("Der YAML-Bereich 'logging' muss eine Map sein.")

    logger = logging.getLogger()
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
        handler.close()

    level_name = str(logging_config.get("level", "INFO")).upper()
    if level_name not in VALID_LOG_LEVELS:
        raise ValueError(
            "logging.level muss DEBUG, INFO, WARNING, ERROR oder CRITICAL sein."
        )
    if run_mode not in VALID_RUN_MODES:
        raise ValueError(
            "run_mode muss interactive, cron, dry-run, preview oder tool sein."
        )
    level = getattr(logging, level_name)
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
    retention_files = validate_log_retention(logging_config.get("retention_files", 100))
    while True:
        log_file = _create_log_path(log_dir, run_mode)
        try:
            file_handler = logging.FileHandler(log_file, mode="x", encoding="utf-8")
            break
        except FileExistsError:
            continue
    file_handler.setFormatter(formatter)
    file_handler.setLevel(level)
    logger.addHandler(file_handler)
    try:
        os.chmod(log_file, 0o600)
    except OSError:
        pass
    _prune_log_files(log_dir, retention_files)

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


def _create_log_path(log_dir: Path, run_mode: str) -> Path:
    """Erzeugt einen lesbaren und kollisionsfreien Dateinamen fuer den Lauf."""
    base = f"invoice-{run_mode}-{now():%Y-%m-%d_%H-%M-%S}"
    log_file = log_dir / f"{base}.log"
    number = 2
    while log_file.exists():
        log_file = log_dir / f"{base}-{number:02d}.log"
        number += 1
    return log_file


def validate_log_retention(value) -> int:
    """Prueft die maximale Anzahl aufzubewahrender Laufprotokolle."""
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ValueError("logging.retention_files muss eine positive ganze Zahl sein.")
    return value


def _prune_log_files(log_dir: Path, retention_files: int) -> None:
    """Entfernt ausschliesslich ueberzaehlige eigene Laufprotokolle."""
    log_files = sorted(
        (
            path
            for path in log_dir.glob("invoice-*.log")
            if path.is_file() and not path.is_symlink()
        ),
        key=lambda path: (path.stat().st_mtime_ns, path.name),
        reverse=True,
    )
    for log_file in log_files:
        try:
            os.chmod(log_file, 0o600)
        except OSError:
            pass
    for log_file in log_files[retention_files:]:
        try:
            log_file.unlink()
        except OSError as err:
            logging.getLogger(__name__).warning(
                "Alte Logdatei konnte nicht entfernt werden: %s", err
            )
