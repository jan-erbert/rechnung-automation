from datetime import datetime

import pytest

from mail import MailversandFehler
from workflow import (
    _sende_mail_mit_status,
    _speichere_nullstunden_status,
    _speichere_pending_status,
    _verarbeite_kundeneintrag,
    _verarbeite_kunden_im_lauf,
    verarbeite_rechnungen,
)


def test_failed_mail_is_marked_for_retry(tmp_path, monkeypatch, caplog):
    """Ein SMTP-Fehler setzt failed und kuendigt den erneuten Versuch an."""
    verlauf_pfad = tmp_path / "verlauf.json"
    verlauf = []
    versandeintrag = {
        "id": "rechnung-1",
        "versandstatus": "pending",
    }
    assert _speichere_pending_status(versandeintrag, verlauf, verlauf_pfad) is True

    def smtp_fehler(*args, **kwargs):
        raise MailversandFehler("SMTP nicht erreichbar", retry_sicher=True)

    monkeypatch.setattr("workflow.sende_mail", smtp_fehler)

    erfolgreich = _sende_mail_mit_status(
        eintrag={
            "name": "Erika Beispiel",
            "email": "erika@example.com",
        },
        mail_config={
            "server": "smtp.example.com",
            "port": 587,
            "user": "sender@example.com",
            "passwort": "test",
        },
        msg=object(),
        empfaenger_liste=["erika@example.com"],
        mail_bcc=None,
        rechnung_id="rechnung-1",
        rechnungsverlauf=verlauf,
        verlauf_dateiname=verlauf_pfad,
    )

    assert erfolgreich is False
    assert verlauf[0]["versandstatus"] == "failed"
    assert "beim naechsten Lauf erneut versucht" in caplog.text


def test_ambiguous_mail_failure_remains_pending(tmp_path, monkeypatch, caplog):
    """Ein unklarer SMTP-Abbruch blockiert automatische Wiederholungen."""
    verlauf_pfad = tmp_path / "verlauf.json"
    verlauf = []
    versandeintrag = {
        "id": "rechnung-1",
        "versandstatus": "pending",
    }
    assert _speichere_pending_status(versandeintrag, verlauf, verlauf_pfad) is True

    def smtp_fehler(*args, **kwargs):
        raise MailversandFehler("Verbindung abgebrochen", retry_sicher=False)

    monkeypatch.setattr("workflow.sende_mail", smtp_fehler)

    erfolgreich = _sende_mail_mit_status(
        eintrag={
            "name": "Erika Beispiel",
            "email": "erika@example.com",
        },
        mail_config={
            "server": "smtp.example.com",
            "port": 587,
            "user": "sender@example.com",
            "passwort": "test",
        },
        msg=object(),
        empfaenger_liste=["erika@example.com"],
        mail_bcc=None,
        rechnung_id="rechnung-1",
        rechnungsverlauf=verlauf,
        verlauf_dateiname=verlauf_pfad,
    )

    assert erfolgreich is False
    assert verlauf[0]["versandstatus"] == "pending"
    assert "Versandstatus ist unklar" in caplog.text


def test_successful_mail_is_marked_as_sent(tmp_path, monkeypatch):
    """Ein bestaetigter SMTP-Versand setzt den Status sent."""
    verlauf_pfad = tmp_path / "verlauf.json"
    verlauf = []
    versandeintrag = {
        "id": "rechnung-1",
        "versandstatus": "pending",
    }
    assert _speichere_pending_status(versandeintrag, verlauf, verlauf_pfad) is True
    monkeypatch.setattr("workflow.sende_mail", lambda *args, **kwargs: None)

    erfolgreich = _sende_mail_mit_status(
        eintrag={
            "name": "Erika Beispiel",
            "email": "erika@example.com",
        },
        mail_config={
            "server": "smtp.example.com",
            "port": 587,
            "user": "sender@example.com",
            "passwort": "test",
        },
        msg=object(),
        empfaenger_liste=["erika@example.com"],
        mail_bcc=None,
        rechnung_id="rechnung-1",
        rechnungsverlauf=verlauf,
        verlauf_dateiname=verlauf_pfad,
    )

    assert erfolgreich is True
    assert verlauf[0]["versandstatus"] == "sent"


def test_failed_sent_confirmation_remains_pending(tmp_path, monkeypatch, caplog):
    """Fehlt die lokale Versandbestaetigung, bleibt der Status pending."""
    verlauf_pfad = tmp_path / "verlauf.json"
    verlauf = []
    versandeintrag = {
        "id": "rechnung-1",
        "versandstatus": "pending",
    }
    assert _speichere_pending_status(versandeintrag, verlauf, verlauf_pfad) is True
    monkeypatch.setattr("workflow.sende_mail", lambda *args, **kwargs: None)

    def status_fehler(*args, **kwargs):
        raise OSError("Verlauf nicht schreibbar")

    monkeypatch.setattr("workflow.setze_versandstatus", status_fehler)

    erfolgreich = _sende_mail_mit_status(
        eintrag={
            "name": "Erika Beispiel",
            "email": "erika@example.com",
        },
        mail_config={
            "server": "smtp.example.com",
            "port": 587,
            "user": "sender@example.com",
            "passwort": "test",
        },
        msg=object(),
        empfaenger_liste=["erika@example.com"],
        mail_bcc=None,
        rechnung_id="rechnung-1",
        rechnungsverlauf=verlauf,
        verlauf_dateiname=verlauf_pfad,
    )

    assert erfolgreich is False
    assert verlauf[0]["versandstatus"] == "pending"
    assert "kein automatischer erneuter Versand" in caplog.text


def test_cron_null_hours_wait_for_later_hours(tmp_path, caplog):
    """Cron-Nullstunden bleiben im aktuellen Rechnungsmonat offen."""
    verlauf_pfad = tmp_path / "verlauf.json"
    verlauf = []

    _speichere_nullstunden_status(
        eintrag={"firma": "Beispielfirma", "name": "Erika Beispiel"},
        heute=datetime(2026, 7, 1),
        rechnungsnummer="07-2026",
        rechnungsdatum="01.07.2026",
        abrechnungszyklus=3,
        rechnungsverlauf=verlauf,
        verlauf_dateiname=verlauf_pfad,
        interactive=False,
    )

    assert verlauf[0]["versandstatus"] == "waiting_hours"
    assert verlauf[0]["zyklus_monate"] == 3
    assert "Keine Rechnung erstellt oder versendet" in caplog.text


def test_interactive_null_hours_are_closed_without_invoice(tmp_path, caplog):
    """Bewusst bestaetigte Nullstunden werden direkt abgeschlossen."""
    caplog.set_level("INFO")
    verlauf_pfad = tmp_path / "verlauf.json"
    verlauf = []

    _speichere_nullstunden_status(
        eintrag={"firma": "Beispielfirma", "name": "Erika Beispiel"},
        heute=datetime(2026, 7, 1),
        rechnungsnummer="07-2026",
        rechnungsdatum="01.07.2026",
        abrechnungszyklus=1,
        rechnungsverlauf=verlauf,
        verlauf_dateiname=verlauf_pfad,
        interactive=True,
    )

    assert verlauf[0]["versandstatus"] == "no_invoice"
    assert "no_invoice abgeschlossen" in caplog.text


def test_unexpected_customer_error_does_not_stop_following_customer(
    monkeypatch,
    caplog,
):
    """Ein unerwarteter Kundenfehler blockiert folgende Kunden nicht."""
    verarbeitet = []

    def verarbeite_kunde(**kwargs):
        firma = kwargs["eintrag"]["firma"]
        verarbeitet.append(firma)
        if firma == "Fehlerfirma":
            raise RuntimeError("Template defekt")

    monkeypatch.setattr("workflow._verarbeite_kunden_im_lauf", verarbeite_kunde)

    verarbeite_rechnungen(
        daten=[{"firma": "Fehlerfirma"}, {"firma": "Folgefirma"}],
        pfade=object(),
        konfig={"absender": {}, "bank": {}, "finanzen": {}},
        mail_config={},
        pdf_config={},
        design_config={},
        branding_config={},
        templates=object(),
        rechnungsverlauf=[],
        rechnungsverlauf_vorjahr=[],
        verlauf_dateiname=object(),
    )

    assert verarbeitet == ["Fehlerfirma", "Folgefirma"]
    assert "wird mit dem naechsten Kunden fortgesetzt" in caplog.text


def test_unreachable_archive_skips_customer_before_due_check(
    tmp_path,
    monkeypatch,
    caplog,
):
    """Ein unerreichbares Archiv stoppt nur den betroffenen Kunden."""
    faelligkeit_geprueft = []
    monkeypatch.setattr(
        "workflow.rechnung_fällig",
        lambda *args: faelligkeit_geprueft.append(True),
    )

    _verarbeite_kunden_im_lauf(
        daten=[],
        eintrag={
            "firma": "Beispielfirma",
            "archiv_pfad": str(tmp_path / "fehlt"),
            "hauptleistung": {
                "beschreibung": "Hosting",
                "einheit": "Monat",
                "betrag": "10,00",
            },
        },
        pfade=object(),
        absender={},
        bank={},
        finanzen={},
        mail_bcc=None,
        mail_from_name=None,
        mail_config={},
        pdf_config={},
        design_config={},
        branding_config={},
        templates=object(),
        rechnungsverlauf=[],
        rechnungsverlauf_vorjahr=[],
        verlauf_dateiname=object(),
        interactive=False,
    )

    assert faelligkeit_geprueft == []
    assert "Archivpfad ist nicht erreichbar" in caplog.text


def test_archive_write_probe_stops_before_invoice_creation(monkeypatch):
    """Eine fehlgeschlagene Archiv-Schreibprobe stoppt vor der Rechnung."""
    rechnungsdaten_gebaut = []

    def schreibfehler(*args, **kwargs):
        raise ValueError("Archivpfad ist nicht beschreibbar.")

    monkeypatch.setattr("workflow.pruefe_archiv_pfad", schreibfehler)
    monkeypatch.setattr(
        "workflow.baue_rechnungsdaten",
        lambda *args: rechnungsdaten_gebaut.append(True),
    )

    with pytest.raises(ValueError, match="nicht beschreibbar"):
        _verarbeite_kundeneintrag(
            daten=[],
            eintrag={"archiv_pfad": "/archiv"},
            pfade=object(),
            absender={},
            bank={},
            finanzen={},
            mail_bcc=None,
            mail_from_name=None,
            mail_config={},
            pdf_config={},
            design_config={},
            branding_config={},
            templates=object(),
            rechnungsverlauf=[],
            verlauf_dateiname=object(),
            interactive=False,
        )

    assert rechnungsdaten_gebaut == []
