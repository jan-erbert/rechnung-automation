from logging_setup import LauffehlerSammler
from main import _sende_cron_fehlerbericht


def _mail_config() -> dict:
    """Erstellt eine minimale Mail-Konfiguration fuer Tests."""
    return {
        "server": "smtp.example.com",
        "port": 587,
        "user": "sender@example.com",
        "passwort": "secret",
    }


def test_cron_error_report_is_only_sent_when_errors_exist(monkeypatch):
    """Ein fehlerfreier Cronlauf versendet keinen Fehlerbericht."""
    versendet = []
    monkeypatch.setattr("main.sende_mail", lambda *args: versendet.append(args))

    _sende_cron_fehlerbericht(
        LauffehlerSammler(),
        _mail_config(),
        {"mail": {"bcc": "bcc@example.com"}},
    )

    assert versendet == []


def test_cron_error_report_is_sent_only_to_bcc(monkeypatch):
    """Der Cron-Fehlerbericht wird ausschliesslich an BCC gesendet."""
    versendet = []
    sammler = LauffehlerSammler()
    sammler.fehler.append(
        {
            "zeit": "2026-06-06 12:00:00",
            "level": "ERROR",
            "quelle": "workflow",
            "meldung": "Kundenverarbeitung fehlgeschlagen",
        }
    )
    monkeypatch.setattr("main.sende_mail", lambda *args: versendet.append(args))

    _sende_cron_fehlerbericht(
        sammler,
        _mail_config(),
        {"mail": {"bcc": "bcc@example.com"}},
    )

    assert len(versendet) == 1
    assert versendet[0][-1] == ["bcc@example.com"]
