import logging
from datetime import datetime

from logging_setup import RunErrorCollector, configure_logging


def test_error_collector_ignores_warnings_and_collects_errors():
    """Der Cron-Sammler behaelt nur ERROR- und CRITICAL-Meldungen."""
    collector = RunErrorCollector()
    logger = logging.getLogger("test.lauffehler")
    logger.addHandler(collector)
    logger.setLevel(logging.WARNING)
    logger.propagate = False

    try:
        logger.warning("Nur ein Hinweis")
        logger.error("Schwerer Fehler")
    finally:
        logger.removeHandler(collector)
        logger.propagate = True

    assert len(collector.errors) == 1
    assert collector.errors[0]["level"] == "ERROR"
    assert collector.errors[0]["message"] == "Schwerer Fehler"


def test_log_filename_is_readable_and_collision_safe(tmp_path, monkeypatch):
    """Logdateien tragen lesbares Datum und Uhrzeit sowie einen Kollisionssuffix."""
    monkeypatch.setattr(
        "logging_setup.now",
        lambda: datetime(2026, 9, 4, 10, 53, 25),
    )
    log_dir = tmp_path / "logs"
    erster_pfad = configure_logging(
        {"enabled": True, "directory": str(log_dir)},
        tmp_path,
    )
    zweiter_pfad = configure_logging(
        {"enabled": True, "directory": str(log_dir)},
        tmp_path,
    )

    assert erster_pfad.name == "invoice-2026-09-04_10-53-25.log"
    assert zweiter_pfad.name == "invoice-2026-09-04_10-53-25-02.log"

    for handler in logging.getLogger().handlers[:]:
        logging.getLogger().removeHandler(handler)
        handler.close()
