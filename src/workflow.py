import logging
from datetime import datetime

from branding import lade_logo_asset
from faelligkeit import rechnung_fällig
from kunden import (
    entferne_kunde_aus_daten,
    sollte_kunde_entfernt_werden,
    speichere_kundendaten,
)
from leistungen import baue_leistungspositionen
from mail import MailversandFehler, baue_rechnungsmail, sende_mail
from pfadpruefung import pruefe_archiv_pfad
from pdf import archiviere_pdf, erzeuge_pdf_bytes
from rechnungen import (
    baue_rechnungsdaten,
    berechne_abrechnungszeitraum,
    berechne_steuerwerte,
)
from templates import baue_template_context
from validierung import (
    normalisiere_mail_liste,
    validiere_kundeneintrag,
    validiere_positive_ganzzahl,
)
from verlauf import (
    VERSANDSTATUS_FAILED,
    VERSANDSTATUS_NO_INVOICE,
    VERSANDSTATUS_PENDING,
    VERSANDSTATUS_SENT,
    VERSANDSTATUS_WAITING_HOURS,
    baue_verlaufseintrag,
    setze_versandstatus,
    speichere_oder_ersetze_verlaufseintrag,
)

logger = logging.getLogger(__name__)


def verarbeite_rechnungen(
    daten: list,
    pfade,
    konfig: dict,
    mail_config: dict,
    pdf_config: dict,
    design_config: dict,
    branding_config: dict,
    templates,
    rechnungsverlauf: list,
    rechnungsverlauf_vorjahr: list,
    verlauf_dateiname,
    interactive: bool = True,
) -> None:
    """Verarbeitet alle faelligen Kundeneintraege fuer den Rechnungslauf."""
    absender = konfig["absender"]
    bank = konfig["bank"]
    finanzen = konfig["finanzen"]
    mail_bcc = konfig.get("mail", {}).get("bcc") or None
    mail_from_name = konfig.get("mail", {}).get("from_name") or None

    for eintrag in daten:
        try:
            _verarbeite_kunden_im_lauf(
                daten=daten,
                eintrag=eintrag,
                pfade=pfade,
                absender=absender,
                bank=bank,
                finanzen=finanzen,
                mail_bcc=mail_bcc,
                mail_from_name=mail_from_name,
                mail_config=mail_config,
                pdf_config=pdf_config,
                design_config=design_config,
                branding_config=branding_config,
                templates=templates,
                rechnungsverlauf=rechnungsverlauf,
                rechnungsverlauf_vorjahr=rechnungsverlauf_vorjahr,
                verlauf_dateiname=verlauf_dateiname,
                interactive=interactive,
            )
        except Exception as err:
            logger.exception(
                "%s: Unerwarteter Fehler bei der Verarbeitung. "
                "Der Rechnungslauf wird mit dem naechsten Kunden fortgesetzt: %s",
                eintrag.get("firma", "Unbekannter Kunde"),
                err,
            )

    logger.info("Alle Rechnungen wurden verarbeitet.")
    logger.info("Skript beendet.")


def _verarbeite_kunden_im_lauf(
    daten: list,
    eintrag: dict,
    pfade,
    absender: dict,
    bank: dict,
    finanzen: dict,
    mail_bcc: str | None,
    mail_from_name: str | None,
    mail_config: dict,
    pdf_config: dict,
    design_config: dict,
    branding_config: dict,
    templates,
    rechnungsverlauf: list,
    rechnungsverlauf_vorjahr: list,
    verlauf_dateiname,
    interactive: bool,
) -> None:
    """Prueft und verarbeitet einen Kunden innerhalb der sicheren Laufgrenze."""
    if eintrag.get("aktiv") is False:
        logger.info("%s: Kunde ist deaktiviert - keine Abrechnung.", eintrag["firma"])
        return

    try:
        validiere_kundeneintrag(eintrag)
    except ValueError as err:
        logger.error(
            "%s: Ungueltige Kundendaten - %s",
            eintrag.get("firma", "Unbekannter Kunde"),
            err,
        )
        return

    archiv_pfad = eintrag.get("archiv_pfad")
    if archiv_pfad:
        try:
            pruefe_archiv_pfad(archiv_pfad)
        except ValueError as err:
            logger.error(
                "%s: Archivpfad ist nicht erreichbar - keine Verarbeitung: %s",
                eintrag.get("firma", "Unbekannter Kunde"),
                err,
            )
            return

    if not rechnung_fällig(eintrag, rechnungsverlauf, rechnungsverlauf_vorjahr):
        logger.info("%s: Keine Abrechnung faellig.", eintrag["firma"])
        return

    _verarbeite_kundeneintrag(
        daten=daten,
        eintrag=eintrag,
        pfade=pfade,
        absender=absender,
        bank=bank,
        finanzen=finanzen,
        mail_bcc=mail_bcc,
        mail_from_name=mail_from_name,
        mail_config=mail_config,
        pdf_config=pdf_config,
        design_config=design_config,
        branding_config=branding_config,
        templates=templates,
        rechnungsverlauf=rechnungsverlauf,
        verlauf_dateiname=verlauf_dateiname,
        interactive=interactive,
    )


def _verarbeite_kundeneintrag(
    daten: list,
    eintrag: dict,
    pfade,
    absender: dict,
    bank: dict,
    finanzen: dict,
    mail_bcc: str | None,
    mail_from_name: str | None,
    mail_config: dict,
    pdf_config: dict,
    design_config: dict,
    branding_config: dict,
    templates,
    rechnungsverlauf: list,
    verlauf_dateiname,
    interactive: bool,
) -> None:
    """Erzeugt und versendet eine Rechnung fuer einen Kundeneintrag."""
    heute = datetime.today()
    archiv_pfad = eintrag.get("archiv_pfad")
    if archiv_pfad:
        pruefe_archiv_pfad(archiv_pfad, schreibprobe=True)

    rechnungsdaten = baue_rechnungsdaten(eintrag, heute)
    rechnungsdatum = rechnungsdaten["rechnungsdatum"]
    monat_jahr = rechnungsdaten["monat_jahr"]
    faelligkeit_datum = rechnungsdaten["faelligkeit_datum"]
    rechnungsnummer = rechnungsdaten["rechnungsnummer"]
    auto_rechnungsnummer = rechnungsdaten["auto_rechnungsnummer"]

    abrechnungszyklus = validiere_positive_ganzzahl(
        eintrag.get("abrechnungszyklus", 1),
        "Abrechnungszyklus",
    )
    leistungsdaten = baue_leistungspositionen(
        eintrag,
        abrechnungszyklus,
        pfade.hours_dir,
        interactive=interactive,
    )
    leistungs_liste = leistungsdaten["leistungs_liste"]
    gesamtpreis = leistungsdaten["gesamtpreis"]
    stundeninfo = leistungsdaten["stundeninfo"]

    if stundeninfo and (stundeninfo["stunden"] == 0 or not stundeninfo["vollstaendig"]):
        _speichere_nullstunden_status(
            eintrag,
            heute,
            rechnungsnummer,
            rechnungsdatum,
            abrechnungszyklus,
            rechnungsverlauf,
            verlauf_dateiname,
            interactive,
            stundeninfo.get("fehlende_monate", []),
        )
        return

    steuerdaten = berechne_steuerwerte(gesamtpreis, finanzen)
    mail_cc = normalisiere_mail_liste(eintrag.get("cc"), "cc")
    pdf_logo = lade_logo_asset(
        pfade.img_dir,
        branding_config["pdf_logo"],
        "PDF-Logo",
    )
    mail_logo = lade_logo_asset(
        pfade.img_dir,
        branding_config["mail_logo"],
        "Mail-Logo",
    )
    abrechnungszeitraum = berechne_abrechnungszeitraum(heute, abrechnungszyklus)

    context = baue_template_context(
        eintrag=eintrag,
        absender=absender,
        bank=bank,
        finanzen=finanzen,
        leistungs_liste=leistungs_liste,
        rechnungsnummer=rechnungsnummer,
        rechnungsdatum=rechnungsdatum,
        faelligkeit_datum=faelligkeit_datum,
        abrechnungszeitraum=abrechnungszeitraum,
        monat_jahr=monat_jahr,
        abrechnungszyklus=abrechnungszyklus,
        gesamtpreis=gesamtpreis,
        gesamtpreis_str=steuerdaten["gesamtpreis_str"],
        gesamtpreis_mit_mwst=steuerdaten["gesamtpreis_mit_mwst"],
        steuerbetrag=steuerdaten["steuerbetrag"],
        mwst_hinweis=steuerdaten["mwst_hinweis"],
        logo_base64=pdf_logo.data_uri if pdf_logo else "",
        mail_logo_cid="rechnung-logo" if mail_logo else "",
        design=design_config,
        branding=branding_config,
        stundeninfo=stundeninfo,
    )

    mail_html = templates.mail.render(context)
    pdf_html = templates.rechnung.render(context)
    pdf_bytes = erzeuge_pdf_bytes(pdf_html, pdf_config)

    firma_slug = eintrag["firma"].lower().replace(" ", "_")
    anhang_name = f"Rechnung_{firma_slug}_{auto_rechnungsnummer}.pdf"
    msg = baue_rechnungsmail(
        mail_user=mail_config["user"],
        empfaenger=eintrag["email"],
        betreff=f"Ihre Rechnung Nr. {rechnungsnummer} – {eintrag['firma']}",
        mail_html=mail_html,
        pdf_bytes=pdf_bytes,
        anhang_name=anhang_name,
        mail_bcc=mail_bcc,
        mail_cc=mail_cc,
        mail_logo=mail_logo,
        from_name=mail_from_name,
    )

    versandeintrag = baue_verlaufseintrag(
        eintrag,
        heute,
        rechnungsnummer,
        rechnungsdatum,
        steuerdaten["gesamtpreis_str"].replace(",", "."),
        abrechnungszyklus,
        versandstatus=VERSANDSTATUS_PENDING,
    )
    if not _speichere_pending_status(
        versandeintrag,
        rechnungsverlauf,
        verlauf_dateiname,
    ):
        return

    empfaenger_liste = [eintrag["email"], *mail_cc]
    if mail_bcc:
        empfaenger_liste.append(mail_bcc)

    if not _sende_mail_mit_status(
        eintrag=eintrag,
        mail_config=mail_config,
        msg=msg,
        empfaenger_liste=empfaenger_liste,
        mail_bcc=mail_bcc,
        rechnung_id=versandeintrag["id"],
        rechnungsverlauf=rechnungsverlauf,
        verlauf_dateiname=verlauf_dateiname,
    ):
        return

    _archiviere_pdf_falls_noetig(eintrag, anhang_name, pdf_bytes)
    try:
        _entferne_kunden_falls_noetig(daten, eintrag, heute, pfade, interactive)
    except Exception as err:
        logger.exception(
            "Kunde %s konnte nach erfolgreichem Versand nicht entfernt werden: %s",
            eintrag["firma"],
            err,
        )


def _speichere_pending_status(
    versandeintrag: dict,
    rechnungsverlauf: list,
    verlauf_dateiname,
) -> bool:
    """Speichert den unbestaetigten Versandstatus vor dem SMTP-Aufruf."""
    try:
        speichere_oder_ersetze_verlaufseintrag(
            verlauf_dateiname,
            rechnungsverlauf,
            versandeintrag,
        )
    except Exception as err:
        logger.exception(
            "Versand wird nicht gestartet: Status pending konnte nicht "
            "gespeichert werden: %s",
            err,
        )
        return False

    logger.info("Versandstatus pending gespeichert. Mailversand wird gestartet.")
    return True


def _sende_mail_mit_status(
    eintrag: dict,
    mail_config: dict,
    msg,
    empfaenger_liste: list[str],
    mail_bcc: str | None,
    rechnung_id: str,
    rechnungsverlauf: list,
    verlauf_dateiname,
) -> bool:
    """Sendet eine Mail und aktualisiert ihren Versandstatus."""
    try:
        sende_mail(
            mail_config["server"],
            mail_config["port"],
            mail_config["user"],
            mail_config["passwort"],
            msg,
            empfaenger_liste,
        )
    except MailversandFehler as err:
        logger.error(
            "Mailversand an %s ist fehlgeschlagen: %s",
            eintrag["email"],
            err,
        )
        if err.hinweis:
            logger.warning("Hinweis zum Mailversand: %s", err.hinweis)
        if not err.retry_sicher:
            logger.critical(
                "Der Versandstatus ist unklar. Pending bleibt bestehen und "
                "blockiert automatische Wiederholungen."
            )
            return False

        try:
            setze_versandstatus(
                verlauf_dateiname,
                rechnungsverlauf,
                rechnung_id,
                VERSANDSTATUS_FAILED,
            )
            logger.warning(
                "Versandstatus failed gespeichert. "
                "Der Versand wird beim naechsten Lauf erneut versucht."
            )
        except Exception as status_err:
            logger.critical(
                "Mailversand ist fehlgeschlagen, aber der Status konnte nicht "
                "auf failed gesetzt werden. Pending bleibt bestehen und muss "
                "manuell geprueft werden: %s",
                status_err,
                exc_info=True,
            )
        return False
    except Exception as err:
        logger.exception(
            "Unerwarteter Fehler waehrend des Mailversands. Pending bleibt "
            "bestehen und blockiert automatische Wiederholungen: %s",
            err,
        )
        return False

    logger.info("Mail an %s (%s) gesendet.", eintrag["name"], eintrag["email"])
    if mail_bcc:
        logger.info("BCC-Empfaenger ist konfiguriert.")

    try:
        setze_versandstatus(
            verlauf_dateiname,
            rechnungsverlauf,
            rechnung_id,
            VERSANDSTATUS_SENT,
        )
    except Exception as err:
        logger.critical(
            "Mail wurde versendet, aber der Status sent konnte nicht gespeichert "
            "werden. Pending bleibt bestehen; kein automatischer erneuter Versand: %s",
            err,
            exc_info=True,
        )
        return False

    logger.info("Versandstatus sent gespeichert.")
    return True


def _speichere_nullstunden_status(
    eintrag: dict,
    heute: datetime,
    rechnungsnummer: str,
    rechnungsdatum: str,
    abrechnungszyklus: int,
    rechnungsverlauf: list,
    verlauf_dateiname,
    interactive: bool,
    fehlende_monate: list[str] | None = None,
) -> None:
    """Speichert den Status einer stundenbasierten Nullabrechnung."""
    status = VERSANDSTATUS_NO_INVOICE if interactive else VERSANDSTATUS_WAITING_HOURS
    verlaufseintrag = baue_verlaufseintrag(
        eintrag,
        heute,
        rechnungsnummer,
        rechnungsdatum,
        "0.00",
        abrechnungszyklus,
        versandstatus=status,
    )
    speichere_oder_ersetze_verlaufseintrag(
        verlauf_dateiname,
        rechnungsverlauf,
        verlaufseintrag,
    )

    if interactive:
        logger.info(
            "Keine Stunden fuer %s. Keine Rechnung erstellt oder versendet; "
            "Abrechnung wurde als no_invoice abgeschlossen.",
            eintrag["firma"],
        )
    else:
        fehlende_monate = fehlende_monate or []
        fehlende_hinweis = (
            f" Fehlende Monatsdaten: {', '.join(fehlende_monate)}."
            if fehlende_monate
            else ""
        )
        logger.warning(
            "Keine abrechenbaren oder unvollstaendige Stunden fuer %s. "
            "Keine Rechnung erstellt oder versendet; "
            "Status waiting_hours wird innerhalb dieses Rechnungsmonats erneut "
            "geprueft.%s",
            eintrag["firma"],
            fehlende_hinweis,
        )


def _archiviere_pdf_falls_noetig(
    eintrag: dict,
    anhang_name: str,
    pdf_bytes: bytes,
) -> None:
    """Archiviert eine PDF, wenn der Kundeneintrag einen Archivpfad enthaelt."""
    archiv_pfad = eintrag.get("archiv_pfad")
    if not archiv_pfad:
        return

    try:
        archiviere_pdf(archiv_pfad, anhang_name, pdf_bytes)
    except Exception as e:
        logger.error(
            "%s: PDF konnte nach erfolgreichem Versand nicht archiviert werden: %s",
            eintrag.get("firma", "Unbekannter Kunde"),
            e,
            exc_info=True,
        )


def _entferne_kunden_falls_noetig(
    daten: list,
    eintrag: dict,
    heute: datetime,
    pfade,
    interactive: bool,
) -> None:
    """Fragt nach dem Entfernen abgeschlossener Kundeneintraege."""
    if not sollte_kunde_entfernt_werden(eintrag, heute):
        return

    logger.info(
        "Kunde '%s' (%s) hat die letzte Rechnung erhalten.",
        eintrag["firma"],
        eintrag["name"],
    )
    if not interactive:
        logger.info("Nicht-interaktiver Lauf: Kunde bleibt in daten.json.")
        return

    entscheidung = (
        input("❓ Möchtest du diesen Kunden jetzt aus daten.json löschen? (y/n): ")
        .strip()
        .lower()
    )
    if entscheidung == "y":
        daten[:] = entferne_kunde_aus_daten(daten, eintrag)
        speichere_kundendaten(pfade.data_dir / "daten.json", daten)
        logger.info("Kunde wurde aus daten.json entfernt.")
    else:
        logger.info("Kunde bleibt weiterhin in der Kundendatei.")
