from datetime import datetime
from decimal import Decimal

import pytest

from email_service import MailDeliveryError
from hours_files import write_hours_month
from workflow import (
    _send_email_with_status,
    _save_zero_hours_status,
    _save_pending_status,
    _process_customer_entry,
    _process_customer_in_run,
    RunContext,
    InvoiceProcessingError,
    process_invoices,
)


class DummyTemplates:
    """Stellt minimale Render-Methoden fuer Workflow-Tests bereit."""

    class Template:
        """Rendert einen festen HTML-Platzhalter."""

        def render(self, context):
            """Gibt testbares HTML ohne echte Vorlage zurueck."""
            return "<html></html>"

    email = Template()
    invoice = Template()


def _laufkontext(tmp_path, **aenderungen):
    """Erstellt einen minimalen gebuendelten Workflow-Kontext."""

    class DummyPaths:
        img_dir = tmp_path
        hours_dir = tmp_path

    werte = {
        "paths": DummyPaths(),
        "sender": {
            "name": "Max Mustermann",
            "company": "Musterfirma",
            "email": "kontakt@example.com",
        },
        "bank": {},
        "tax": {"small_business": True},
        "mail_bcc": [],
        "mail_from_name": None,
        "mail_config": {
            "server": "smtp.example.com",
            "port": 587,
            "user": "sender@example.com",
            "password": "test",
        },
        "pdf_config": {},
        "design_config": {},
        "branding_config": {
            "pdf_logo": None,
            "mail_logo": None,
            "pdf_logo_height": 40,
            "mail_logo_height": 60,
        },
        "file_naming_config": {
            "invoice_prefix": "Invoice",
            "preview_prefix": "PREVIEW",
        },
        "templates": DummyTemplates(),
        "history": [],
        "previous_history": [],
        "history_path": tmp_path / "invoice_history.json",
        "interactive": False,
    }
    werte.update(aenderungen)
    return RunContext(**werte)


def test_failed_mail_is_marked_for_retry(tmp_path, monkeypatch, caplog):
    """Ein SMTP-Fehler setzt failed und kuendigt den erneuten Versuch an."""
    invoice_history_pfad = tmp_path / "invoice_history.json"
    invoice_history = []
    versandeintrag = {
        "id": "rechnung-1",
        "customer_id": "kunde",
        "year": 2026,
        "month": 7,
        "status": "pending",
    }
    _save_pending_status(versandeintrag, invoice_history, invoice_history_pfad)

    def smtp_fehler(*args, **kwargs):
        raise MailDeliveryError("SMTP nicht erreichbar", retry_safe=True)

    monkeypatch.setattr("workflow.send_email", smtp_fehler)

    with pytest.raises(InvoiceProcessingError):
        _send_email_with_status(
            customer={
                "name": "Erika Beispiel",
                "email": "erika@example.com",
            },
            mail_config={
                "server": "smtp.example.com",
                "port": 587,
                "user": "sender@example.com",
                "password": "test",
            },
            msg=object(),
            recipients=["erika@example.com"],
            mail_bcc=None,
            invoice_id="rechnung-1",
            history=invoice_history,
            history_path=invoice_history_pfad,
        )

    assert invoice_history[0]["status"] == "failed"
    assert "beim naechsten Lauf erneut versucht" in caplog.text


def test_customer_cc_recipients_are_sent_with_invoice(tmp_path, monkeypatch):
    """Kundenbezogene CC-Adressen werden beim SMTP-Versand beruecksichtigt."""
    gesendete_empfaenger = []
    invoice_history_pfad = tmp_path / "invoice_history.json"

    monkeypatch.setattr("workflow.load_logo_asset", lambda *args: None)
    monkeypatch.setattr("workflow.generate_pdf_bytes", lambda *args: b"pdf")
    monkeypatch.setattr(
        "workflow.send_email",
        lambda *args, **kwargs: gesendete_empfaenger.extend(args[-1]),
    )

    _process_customer_entry(
        customers=[],
        customer={
            "id": "beispielfirma",
            "name": "Erika Beispiel",
            "company": "Beispielfirma",
            "email": "erika@example.com",
            "cc": ["buchhaltung@example.com", "team@example.com"],
            "street": "Beispielweg 1",
            "postal_code": "12345",
            "city": "Beispielstadt",
            "main_service": {
                "description": "Hosting",
                "unit": "month",
                "unit_price": "10,00",
            },
        },
        context=_laufkontext(
            tmp_path,
            mail_bcc=["bcc@example.com"],
            history_path=invoice_history_pfad,
        ),
    )

    assert gesendete_empfaenger == [
        "erika@example.com",
        "buchhaltung@example.com",
        "team@example.com",
        "bcc@example.com",
    ]


def test_dry_run_renders_without_writes_or_mail(tmp_path, monkeypatch, caplog):
    """Der Dry-Run prueft die Rechnung ohne produktive Seiteneffekte."""
    actions = []
    caplog.set_level("INFO")
    monkeypatch.setattr("workflow.load_logo_asset", lambda *args: None)
    monkeypatch.setattr("workflow.generate_pdf_bytes", lambda *args: b"pdf")
    monkeypatch.setattr("workflow.archive_pdf", lambda *args: actions.append("archive"))
    monkeypatch.setattr("workflow.send_email", lambda *args: actions.append("mail"))
    monkeypatch.setattr(
        "workflow.save_or_replace_history_entry",
        lambda *args: actions.append("history"),
    )

    _process_customer_entry(
        customers=[],
        customer={
            "id": "beispielfirma",
            "name": "Erika Beispiel",
            "company": "Beispielfirma",
            "email": "erika@example.com",
            "cc": [],
            "street": "Beispielweg 1",
            "postal_code": "12345",
            "city": "Beispielstadt",
            "main_service": {
                "description": "Hosting",
                "unit": "month",
                "unit_price": "10.00",
            },
        },
        context=_laufkontext(tmp_path, dry_run=True),
    )

    assert actions == []
    assert "Dry-Run:" in caplog.text
    assert "keine Mail versendet" in caplog.text


def test_workflow_uses_configured_invoice_filename(tmp_path, monkeypatch):
    """Mailanhang und Archivierung erhalten denselben konfigurierten Namen."""
    captured_mail = {}
    captured_archive = {}
    monkeypatch.setattr("workflow.current_date", lambda: datetime(2026, 9, 4))
    monkeypatch.setattr("workflow.load_logo_asset", lambda *args: None)
    monkeypatch.setattr("workflow.generate_pdf_bytes", lambda *args: b"pdf")
    monkeypatch.setattr(
        "workflow.build_invoice_email",
        lambda **kwargs: captured_mail.update(kwargs) or object(),
    )
    monkeypatch.setattr(
        "workflow.archive_pdf",
        lambda archive, name, pdf: captured_archive.update(
            {"archive": archive, "name": name, "pdf": pdf}
        ),
    )
    monkeypatch.setattr("workflow.send_email", lambda *args, **kwargs: None)

    _process_customer_entry(
        customers=[],
        customer={
            "id": "tv-alzey",
            "name": "Erika Beispiel",
            "company": "Beispielfirma",
            "email": "erika@example.com",
            "cc": [],
            "street": "Beispielweg 1",
            "postal_code": "12345",
            "city": "Beispielstadt",
            "archive_directory": str(tmp_path),
            "main_service": {
                "description": "Hosting",
                "unit": "month",
                "unit_price": "10.00",
            },
        },
        context=_laufkontext(
            tmp_path,
            file_naming_config={
                "invoice_prefix": "Rechnung",
                "preview_prefix": "VORSCHAU",
            },
        ),
    )

    assert captured_mail["attachment_name"] == "Rechnung_tv-alzey_09-2026.pdf"
    assert captured_archive == {
        "archive": str(tmp_path),
        "name": "Rechnung_tv-alzey_09-2026.pdf",
        "pdf": b"pdf",
    }


def test_hourly_invoice_uses_service_period_and_records_hours(tmp_path, monkeypatch):
    """Stundenrechnung und Verlauf verwenden den geladenen Leistungsmonat."""
    write_hours_month(
        tmp_path / "2026-08.yaml",
        "2026-08",
        {"beispielfirma": Decimal("6.50")},
    )
    contexts = []
    monkeypatch.setattr("workflow.current_date", lambda: datetime(2026, 9, 4))
    monkeypatch.setattr("workflow.load_logo_asset", lambda *args: None)
    monkeypatch.setattr("workflow.generate_pdf_bytes", lambda *args: b"pdf")
    monkeypatch.setattr("workflow.send_email", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        "workflow.build_template_context",
        lambda **kwargs: contexts.append(kwargs) or {},
    )
    invoice_history = []

    _process_customer_entry(
        customers=[],
        customer={
            "id": "beispielfirma",
            "name": "Erika Beispiel",
            "company": "Beispielfirma",
            "email": "erika@example.com",
            "cc": [],
            "street": "Beispielweg 1",
            "postal_code": "12345",
            "city": "Beispielstadt",
            "main_service": {
                "description": "Beratung",
                "unit": "hour",
                "unit_price": "75.00",
            },
        },
        context=_laufkontext(
            tmp_path,
            history=invoice_history,
            history_path=tmp_path / "invoice_history.json",
        ),
    )

    assert contexts[0]["billing_period"] == "August 2026"
    assert invoice_history[0]["service_period"] == "August 2026"
    assert invoice_history[0]["hours"] == "6.50"
    assert invoice_history[0]["hourly_rate"] == "75.00"


def test_ambiguous_mail_failure_remains_pending(tmp_path, monkeypatch, caplog):
    """Ein unklarer SMTP-Abbruch blockiert automatische Wiederholungen."""
    invoice_history_pfad = tmp_path / "invoice_history.json"
    invoice_history = []
    versandeintrag = {
        "id": "rechnung-1",
        "customer_id": "kunde",
        "year": 2026,
        "month": 7,
        "status": "pending",
    }
    _save_pending_status(versandeintrag, invoice_history, invoice_history_pfad)

    def smtp_fehler(*args, **kwargs):
        raise MailDeliveryError("Verbindung abgebrochen", retry_safe=False)

    monkeypatch.setattr("workflow.send_email", smtp_fehler)

    with pytest.raises(InvoiceProcessingError):
        _send_email_with_status(
            customer={
                "name": "Erika Beispiel",
                "email": "erika@example.com",
            },
            mail_config={
                "server": "smtp.example.com",
                "port": 587,
                "user": "sender@example.com",
                "password": "test",
            },
            msg=object(),
            recipients=["erika@example.com"],
            mail_bcc=None,
            invoice_id="rechnung-1",
            history=invoice_history,
            history_path=invoice_history_pfad,
        )

    assert invoice_history[0]["status"] == "pending"
    assert "Versandstatus ist unklar" in caplog.text


def test_successful_mail_is_marked_as_sent(tmp_path, monkeypatch):
    """Ein bestaetigter SMTP-Versand setzt den Status sent."""
    invoice_history_pfad = tmp_path / "invoice_history.json"
    invoice_history = []
    versandeintrag = {
        "id": "rechnung-1",
        "customer_id": "kunde",
        "year": 2026,
        "month": 7,
        "status": "pending",
    }
    _save_pending_status(versandeintrag, invoice_history, invoice_history_pfad)
    monkeypatch.setattr("workflow.send_email", lambda *args, **kwargs: None)

    _send_email_with_status(
        customer={
            "name": "Erika Beispiel",
            "email": "erika@example.com",
        },
        mail_config={
            "server": "smtp.example.com",
            "port": 587,
            "user": "sender@example.com",
            "password": "test",
        },
        msg=object(),
        recipients=["erika@example.com"],
        mail_bcc=None,
        invoice_id="rechnung-1",
        history=invoice_history,
        history_path=invoice_history_pfad,
    )

    assert invoice_history[0]["status"] == "sent"


def test_failed_sent_confirmation_remains_pending(tmp_path, monkeypatch, caplog):
    """Fehlt die lokale Versandbestaetigung, bleibt der Status pending."""
    invoice_history_pfad = tmp_path / "invoice_history.json"
    invoice_history = []
    versandeintrag = {
        "id": "rechnung-1",
        "customer_id": "kunde",
        "year": 2026,
        "month": 7,
        "status": "pending",
    }
    _save_pending_status(versandeintrag, invoice_history, invoice_history_pfad)
    monkeypatch.setattr("workflow.send_email", lambda *args, **kwargs: None)

    def status_fehler(*args, **kwargs):
        raise OSError("Verlauf nicht schreibbar")

    monkeypatch.setattr("workflow.set_delivery_status", status_fehler)

    with pytest.raises(InvoiceProcessingError):
        _send_email_with_status(
            customer={
                "name": "Erika Beispiel",
                "email": "erika@example.com",
            },
            mail_config={
                "server": "smtp.example.com",
                "port": 587,
                "user": "sender@example.com",
                "password": "test",
            },
            msg=object(),
            recipients=["erika@example.com"],
            mail_bcc=None,
            invoice_id="rechnung-1",
            history=invoice_history,
            history_path=invoice_history_pfad,
        )

    assert invoice_history[0]["status"] == "pending"
    assert "kein automatischer erneuter Versand" in caplog.text


def test_cron_null_hours_wait_for_later_hours(tmp_path, caplog):
    """Cron-Nullstunden bleiben im aktuellen Rechnungsmonat offen."""
    invoice_history_pfad = tmp_path / "invoice_history.json"
    invoice_history = []

    _save_zero_hours_status(
        customer={
            "id": "beispielfirma",
            "company": "Beispielfirma",
            "name": "Erika Beispiel",
        },
        today=datetime(2026, 7, 1),
        invoice_number="07-2026",
        invoice_date="01.07.2026",
        cycle_months=3,
        history=invoice_history,
        history_path=invoice_history_pfad,
        interactive=False,
    )

    assert invoice_history[0]["status"] == "waiting_hours"
    assert invoice_history[0]["cycle_months"] == 3
    assert "Keine Rechnung erstellt oder versendet" in caplog.text


def test_interactive_null_hours_are_closed_without_invoice(tmp_path, caplog):
    """Bewusst bestaetigte Nullstunden werden direkt abgeschlossen."""
    caplog.set_level("INFO")
    invoice_history_pfad = tmp_path / "invoice_history.json"
    invoice_history = []

    _save_zero_hours_status(
        customer={
            "id": "beispielfirma",
            "company": "Beispielfirma",
            "name": "Erika Beispiel",
        },
        today=datetime(2026, 7, 1),
        invoice_number="07-2026",
        invoice_date="01.07.2026",
        cycle_months=1,
        history=invoice_history,
        history_path=invoice_history_pfad,
        interactive=True,
    )

    assert invoice_history[0]["status"] == "no_invoice"
    assert "no_invoice abgeschlossen" in caplog.text


def test_unexpected_customer_error_does_not_stop_following_customer(
    monkeypatch,
    caplog,
):
    """Ein unerwarteter Kundenfehler blockiert folgende Kunden nicht."""
    verarbeitet = []

    def verarbeite_kunde(**kwargs):
        firma = kwargs["customer"]["company"]
        verarbeitet.append(firma)
        if firma == "Fehlerfirma":
            raise RuntimeError("Template defekt")

    monkeypatch.setattr("workflow._process_customer_in_run", verarbeite_kunde)

    fehleranzahl = process_invoices(
        customers=[{"company": "Fehlerfirma"}, {"company": "Folgefirma"}],
        paths=object(),
        invoice_config={"sender": {}, "bank": {}, "tax": {}},
        mail_config={},
        pdf_config={},
        design_config={},
        branding_config={},
        file_naming_config={},
        templates=object(),
        history=[],
        previous_history=[],
        history_path=object(),
    )

    assert verarbeitet == ["Fehlerfirma", "Folgefirma"]
    assert fehleranzahl == 1
    assert "Weitere Kunden werden verarbeitet" in caplog.text
    assert "mit 1 Fehlern bei der Kundenverarbeitung abgeschlossen" in caplog.text
    assert all(record.exc_info is None for record in caplog.records)


def test_unreachable_archive_skips_customer_before_due_check(
    tmp_path,
    monkeypatch,
    caplog,
):
    """Ein unerreichbares Archiv stoppt nur den betroffenen Kunden."""
    billing_schedule_geprueft = []
    monkeypatch.setattr(
        "workflow.is_invoice_due",
        lambda *args: billing_schedule_geprueft.append(True),
    )

    with pytest.raises(ValueError, match="Archivpfad existiert nicht"):
        _process_customer_in_run(
            customers=[],
            customer={
                "company": "Beispielfirma",
                "email": "kunde@example.com",
                "archive_directory": str(tmp_path / "fehlt"),
                "main_service": {
                    "description": "Hosting",
                    "unit": "month",
                    "unit_price": "10,00",
                },
            },
            context=_laufkontext(tmp_path),
        )

    assert billing_schedule_geprueft == []


def test_archive_write_probe_stops_before_invoice_creation(monkeypatch, tmp_path):
    """Eine fehlgeschlagene Archiv-Schreibprobe stoppt vor der Rechnung."""
    rechnungsdaten_gebaut = []

    def schreibfehler(*args, **kwargs):
        raise ValueError("Archivpfad ist nicht beschreibbar.")

    monkeypatch.setattr("workflow.check_archive_path", schreibfehler)
    monkeypatch.setattr(
        "workflow.build_invoice_data",
        lambda *args: rechnungsdaten_gebaut.append(True),
    )

    with pytest.raises(ValueError, match="nicht beschreibbar"):
        _process_customer_entry(
            customers=[],
            customer={"archive_directory": "/archiv"},
            context=_laufkontext(tmp_path),
        )

    assert rechnungsdaten_gebaut == []
