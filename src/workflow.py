from datetime import datetime

from faelligkeit import rechnung_fällig
from kunden import (
    entferne_kunde_aus_daten,
    sollte_kunde_entfernt_werden,
    speichere_kundendaten,
)
from leistungen import baue_leistungspositionen
from mail import baue_rechnungsmail, sende_mail
from pdf import archiviere_pdf, erzeuge_pdf_bytes
from rechnungen import (
    baue_rechnungsdaten,
    berechne_abrechnungszeitraum,
    berechne_steuerwerte,
)
from templates import baue_template_context, lade_logo_base64
from verlauf import baue_verlaufseintrag, speichere_verlauf


def verarbeite_rechnungen(
    daten: list,
    pfade,
    konfig: dict,
    mail_config: dict,
    templates,
    rechnungsverlauf: list,
    rechnungsverlauf_vorjahr: list,
    verlauf_dateiname,
) -> None:
    """Verarbeitet alle faelligen Kundeneintraege fuer den Rechnungslauf."""
    absender = konfig["absender"]
    bank = konfig["bank"]
    finanzen = konfig["finanzen"]
    mail_bcc = konfig.get("mail", {}).get("bcc") or None

    for eintrag in daten:
        if eintrag.get("aktiv") is False:
            print(f"⏭️  {eintrag['firma']}: Kunde ist deaktiviert – keine Abrechnung.")
            continue

        if not rechnung_fällig(eintrag, rechnungsverlauf, rechnungsverlauf_vorjahr):
            print(f"⏭️  {eintrag['firma']}: Keine Abrechnung fällig.")
            continue

        _verarbeite_kundeneintrag(
            daten=daten,
            eintrag=eintrag,
            pfade=pfade,
            absender=absender,
            bank=bank,
            finanzen=finanzen,
            mail_bcc=mail_bcc,
            mail_config=mail_config,
            templates=templates,
            rechnungsverlauf=rechnungsverlauf,
            verlauf_dateiname=verlauf_dateiname,
        )

    print("🏁 Alle Rechnungen wurden verarbeitet.")
    print("🔚 Skript beendet...")


def _verarbeite_kundeneintrag(
    daten: list,
    eintrag: dict,
    pfade,
    absender: dict,
    bank: dict,
    finanzen: dict,
    mail_bcc: str | None,
    mail_config: dict,
    templates,
    rechnungsverlauf: list,
    verlauf_dateiname,
) -> None:
    """Erzeugt und versendet eine Rechnung fuer einen Kundeneintrag."""
    heute = datetime.today()

    rechnungsdaten = baue_rechnungsdaten(eintrag, heute)
    rechnungsdatum = rechnungsdaten["rechnungsdatum"]
    monat_jahr = rechnungsdaten["monat_jahr"]
    faelligkeit_datum = rechnungsdaten["faelligkeit_datum"]
    rechnungsnummer = rechnungsdaten["rechnungsnummer"]
    auto_rechnungsnummer = rechnungsdaten["auto_rechnungsnummer"]

    abrechnungszyklus = int(eintrag.get("abrechnungszyklus", 1))
    leistungsdaten = baue_leistungspositionen(
        eintrag,
        abrechnungszyklus,
        pfade.stunden_dir,
    )
    leistungs_liste = leistungsdaten["leistungs_liste"]
    gesamtpreis = leistungsdaten["gesamtpreis"]
    stundeninfo = leistungsdaten["stundeninfo"]

    if stundeninfo and stundeninfo["stunden"] == 0:
        _speichere_nullstunden_verlauf(
            eintrag,
            heute,
            rechnungsnummer,
            rechnungsdatum,
            rechnungsverlauf,
            verlauf_dateiname,
        )
        return

    steuerdaten = berechne_steuerwerte(gesamtpreis, finanzen)
    logo_base64 = lade_logo_base64(pfade.img_dir)
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
        logo_base64=logo_base64,
        stundeninfo=stundeninfo,
    )

    mail_html = templates.mail.render(context)
    pdf_html = templates.rechnung.render(context)
    pdf_bytes = erzeuge_pdf_bytes(pdf_html, pfade.bin_dir)

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
    )

    try:
        empfaenger_liste = [eintrag["email"]]
        if mail_bcc:
            empfaenger_liste.append(mail_bcc)

        sende_mail(
            mail_config["server"],
            mail_config["port"],
            mail_config["user"],
            mail_config["passwort"],
            msg,
            empfaenger_liste,
        )
        print(f"✅ Mail an {eintrag['name']} ({eintrag['email']}) gesendet.")
        print("BCC:", mail_bcc)

        _speichere_erfolgreichen_verlauf(
            eintrag,
            heute,
            rechnungsnummer,
            rechnungsdatum,
            steuerdaten["gesamtpreis_str"],
            abrechnungszyklus,
            rechnungsverlauf,
            verlauf_dateiname,
        )
        _archiviere_pdf_falls_noetig(eintrag, anhang_name, pdf_bytes)
        _entferne_kunden_falls_noetig(daten, eintrag, heute, pfade)

    except Exception as e:
        print(f"❌ Fehler beim Senden an {eintrag['email']}: {e}")


def _speichere_nullstunden_verlauf(
    eintrag: dict,
    heute: datetime,
    rechnungsnummer: str,
    rechnungsdatum: str,
    rechnungsverlauf: list,
    verlauf_dateiname,
) -> None:
    """Speichert einen Verlaufseintrag fuer stundenbasierte Nullabrechnungen."""
    print(
        f"⏭️ Keine Stunden für {eintrag['firma']} – "
        "es wird keine Rechnung verschickt, aber der Verlauf wird aktualisiert."
    )
    rechnungsverlauf.append(
        baue_verlaufseintrag(
            eintrag,
            heute,
            rechnungsnummer,
            rechnungsdatum,
            "0.00",
        )
    )
    speichere_verlauf(verlauf_dateiname, rechnungsverlauf)
    print("📝 Verlauf aktualisiert.")


def _speichere_erfolgreichen_verlauf(
    eintrag: dict,
    heute: datetime,
    rechnungsnummer: str,
    rechnungsdatum: str,
    gesamtpreis_str: str,
    abrechnungszyklus: int,
    rechnungsverlauf: list,
    verlauf_dateiname,
) -> None:
    """Speichert den Verlaufseintrag fuer eine versendete Rechnung."""
    rechnungsverlauf.append(
        baue_verlaufseintrag(
            eintrag,
            heute,
            rechnungsnummer,
            rechnungsdatum,
            gesamtpreis_str.replace(",", "."),
            abrechnungszyklus,
        )
    )
    speichere_verlauf(verlauf_dateiname, rechnungsverlauf)
    print("📝 Verlauf aktualisiert.")


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
        print(f"⚠️ Fehler beim Archivieren der PDF: {e}")


def _entferne_kunden_falls_noetig(
    daten: list,
    eintrag: dict,
    heute: datetime,
    pfade,
) -> None:
    """Fragt nach dem Entfernen abgeschlossener Kundeneintraege."""
    if not sollte_kunde_entfernt_werden(eintrag, heute):
        return

    print(
        f"\n🛑 Kunde '{eintrag['firma']}' "
        f"({eintrag['name']}) hat die letzte Rechnung erhalten."
    )
    entscheidung = (
        input("❓ Möchtest du diesen Kunden jetzt aus daten.json löschen? (y/n): ")
        .strip()
        .lower()
    )
    if entscheidung == "y":
        daten[:] = entferne_kunde_aus_daten(daten, eintrag)
        speichere_kundendaten(pfade.data_dir / "daten.json", daten)
        print("🗑️ Kunde wurde aus daten.json entfernt.")
    else:
        print("⚠️ Kunde bleibt weiterhin in der Kundendatei, wird jedoch übersprungen")
