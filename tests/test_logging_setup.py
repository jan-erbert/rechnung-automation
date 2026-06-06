import logging

from logging_setup import LauffehlerSammler


def test_error_collector_ignores_warnings_and_collects_errors():
    """Der Cron-Sammler behaelt nur ERROR- und CRITICAL-Meldungen."""
    sammler = LauffehlerSammler()
    logger = logging.getLogger("test.lauffehler")
    logger.addHandler(sammler)
    logger.setLevel(logging.WARNING)
    logger.propagate = False

    try:
        logger.warning("Nur ein Hinweis")
        logger.error("Schwerer Fehler")
    finally:
        logger.removeHandler(sammler)
        logger.propagate = True

    assert len(sammler.fehler) == 1
    assert sammler.fehler[0]["level"] == "ERROR"
    assert sammler.fehler[0]["meldung"] == "Schwerer Fehler"
