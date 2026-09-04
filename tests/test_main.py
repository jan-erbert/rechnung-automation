import main as main_module
from datetime import datetime
from types import SimpleNamespace

from logging_setup import RunErrorCollector
from main import _send_cron_error_report


def _mail_config() -> dict:
    """Erstellt eine minimale Mail-Konfiguration fuer Tests."""
    return {
        "server": "smtp.example.com",
        "port": 587,
        "user": "sender@example.com",
        "password": "secret",
    }


def test_cron_error_report_is_only_sent_when_errors_exist(monkeypatch):
    """Ein fehlerfreier Cronlauf versendet keinen Fehlerbericht."""
    versendet = []
    monkeypatch.setattr(
        "main.send_email", lambda *args, **kwargs: versendet.append((args, kwargs))
    )

    _send_cron_error_report(
        RunErrorCollector(),
        _mail_config(),
        {"mail": {"bcc": ["bcc@example.com"]}},
    )

    assert versendet == []


def test_cron_error_report_is_sent_only_to_bcc(monkeypatch):
    """Der Cron-Fehlerbericht wird ausschliesslich an BCC gesendet."""
    versendet = []
    collector = RunErrorCollector()
    collector.errors.append(
        {
            "timestamp": "2026-06-06 12:00:00",
            "level": "ERROR",
            "source": "workflow",
            "message": "Kundenverarbeitung fehlgeschlagen",
        }
    )
    monkeypatch.setattr(
        "main.send_email", lambda *args, **kwargs: versendet.append((args, kwargs))
    )

    _send_cron_error_report(
        collector,
        _mail_config(),
        {"mail": {"bcc": ["bcc@example.com"]}},
    )

    assert len(versendet) == 1
    assert versendet[0][0][-1] == ["bcc@example.com"]


def test_main_reports_configuration_error_without_traceback(monkeypatch, caplog):
    """Ein erwartbarer Startfehler endet kurz und mit Fehlercode."""
    monkeypatch.setattr("main.load_settings", lambda: _raise_value_error())
    monkeypatch.setattr("sys.argv", ["main.py"])

    assert main_module.main() == 1
    assert "Rechnungslauf abgebrochen: Einstellungen ungueltig" in caplog.text
    assert all(record.exc_info is None for record in caplog.records)


def _raise_value_error():
    """Loest einen kontrollierten Konfigurationsfehler aus."""
    raise ValueError("Einstellungen ungueltig")


def test_run_uses_closed_previous_history_state(monkeypatch, tmp_path):
    """Bereinigte alte Wartezustaende werden im selben Lauf weiterverwendet."""
    previous_history = [
        {
            "id": "customer__2025-08",
            "customer_id": "customer",
            "year": 2025,
            "month": 8,
            "status": "waiting_hours",
        }
    ]
    history_by_year = {2025: (tmp_path / "invoice-history-2025.json", previous_history)}
    captured = {}
    monkeypatch.setattr(main_module, "today", lambda: datetime(2026, 9, 4))
    monkeypatch.setattr(
        main_module,
        "load_all_history",
        lambda path: ([previous_history[0]], history_by_year),
    )

    def close_waiting(path, history, current_date):
        """Simuliert die atomare Ersetzung eines alten Wartezustands."""
        history[:] = [{**history[0], "status": "no_invoice"}]
        return 1

    def capture_process(**kwargs):
        """Erfasst den an den Workflow uebergebenen alten Verlauf."""
        captured["previous_history"] = kwargs["previous_history"]
        return 0

    monkeypatch.setattr(
        main_module, "close_expired_hours_waiting_entries", close_waiting
    )
    monkeypatch.setattr(main_module, "load_templates", lambda path: object())
    monkeypatch.setattr(main_module, "process_invoices", capture_process)

    result = main_module._run_invoices(
        SimpleNamespace(non_interactive=True),
        {},
        SimpleNamespace(data_dir=tmp_path, templates_dir=tmp_path),
        [],
        {},
        {},
        {},
        {},
    )

    assert result == 0
    assert captured["previous_history"][0]["status"] == "no_invoice"
