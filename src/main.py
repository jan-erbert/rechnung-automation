# src/main.py
import argparse
import logging
import os

from branding import validiere_branding_config
from design import validiere_design_config
from konfiguration import lade_konfiguration, lade_mail_umgebung
from kundendateien import lade_kundendateien
from logging_setup import (
    LauffehlerSammler,
    aktiviere_lauffehler_sammler,
    konfiguriere_logging,
)
from mail import baue_fehlerbericht_mail, sende_mail
from paths import erstelle_pfade
from settings_loader import lade_settings
from startpruefung import pruefe_startvoraussetzungen
from templates import lade_templates
from verlauf import lade_verlauf_datei, schliesse_abgelaufene_stundenwarteschlangen
from workflow import verarbeite_rechnungen
from zeit import heute

logger = logging.getLogger(__name__)


def parse_args():
    """Liest Kommandozeilenargumente fuer den Rechnungslauf."""
    parser = argparse.ArgumentParser(description="Rechnungen erzeugen und versenden.")
    parser.add_argument(
        "--non-interactive",
        action="store_true",
        help="Fuehrt den Lauf ohne Rueckfragen aus, z. B. fuer Cronjobs.",
    )
    return parser.parse_args()


def main():
    """Startet die Rechnungserstellung und den Mailversand."""
    args = parse_args()
    settings = lade_settings()
    pfade = erstelle_pfade(settings)
    log_file = konfiguriere_logging(settings.get("logging", {}), pfade.base_dir)
    fehler_sammler = aktiviere_lauffehler_sammler() if args.non_interactive else None
    logger.info("Starte Rechnungslauf.")
    if log_file:
        logger.info("Logdatei: %s", log_file)

    mail_config = None
    konfig = None
    try:
        # 📄 Kundendaten laden
        daten = lade_kundendateien(pfade.customers_dir, strict=False)

        # 📧 E-Mail Konfiguration
        mail_config = lade_mail_umgebung(
            pfade.base_dir / ".env", settings.get("mail", {})
        )

        # 📥 Konfiguration laden
        konfig = lade_konfiguration(pfade.invoice_config)

        pruefe_startvoraussetzungen(settings, pfade, daten, mail_config)
        design_config = validiere_design_config(settings.get("design", {}))
        branding_config = validiere_branding_config(settings.get("branding", {}))
        logger.info("Mini-Check vor dem Rechnungslauf erfolgreich.")

        # ⏳ Verlauf laden
        jahr = heute().year
        verlauf_dateiname = pfade.data_dir / f"verlauf-{jahr}.json"
        rechnungsverlauf = lade_verlauf_datei(
            verlauf_dateiname,
            jahr,
            pfade.backup_dir,
            interactive=not args.non_interactive,
        )
        vorjahr_dateiname = pfade.data_dir / f"verlauf-{jahr - 1}.json"
        rechnungsverlauf_vorjahr = (
            lade_verlauf_datei(
                vorjahr_dateiname,
                jahr - 1,
                pfade.backup_dir,
                interactive=not args.non_interactive,
            )
            if os.path.exists(vorjahr_dateiname)
            else []
        )
        _schliesse_abgelaufene_stundenwarteschlangen(
            verlauf_dateiname,
            rechnungsverlauf,
            vorjahr_dateiname,
            rechnungsverlauf_vorjahr,
        )

        # 📩 Jinja2-Templates laden
        templates = lade_templates(pfade.templates_dir)

        verarbeite_rechnungen(
            daten=daten,
            pfade=pfade,
            konfig=konfig,
            mail_config=mail_config,
            pdf_config=settings.get("pdf", {}),
            design_config=design_config,
            branding_config=branding_config,
            templates=templates,
            rechnungsverlauf=rechnungsverlauf,
            rechnungsverlauf_vorjahr=rechnungsverlauf_vorjahr,
            verlauf_dateiname=verlauf_dateiname,
            interactive=not args.non_interactive,
        )
        logger.info("Rechnungslauf beendet.")
    except Exception as err:
        logger.exception("Rechnungslauf wurde unerwartet abgebrochen: %s", err)
        raise
    finally:
        if fehler_sammler:
            _sende_cron_fehlerbericht(fehler_sammler, mail_config, konfig)


def _sende_cron_fehlerbericht(
    fehler_sammler: LauffehlerSammler,
    mail_config: dict | None,
    konfig: dict | None,
) -> None:
    """Sendet am Ende eines Cronlaufs eine Zusammenfassung schwerer Fehler."""
    fehler = list(fehler_sammler.fehler)
    if not fehler:
        return

    mail_bcc = (konfig or {}).get("mail", {}).get("bcc")
    if not mail_config or not mail_bcc:
        logger.critical(
            "Cron-Fehlerbericht kann nicht gesendet werden: "
            "Mail-Konfiguration oder BCC-Empfaenger fehlt."
        )
        return

    try:
        msg = baue_fehlerbericht_mail(
            mail_config["user"],
            mail_bcc[0],
            fehler,
            from_name=(konfig or {}).get("mail", {}).get("from_name"),
        )
        sende_mail(
            mail_config["server"],
            mail_config["port"],
            mail_config["user"],
            mail_config["passwort"],
            msg,
            mail_bcc,
            security=mail_config.get("security", "starttls"),
            timeout=mail_config.get("timeout", 30),
        )
        logger.info("Cron-Fehlerbericht wurde an den BCC-Empfaenger gesendet.")
    except Exception as err:
        logger.exception("Cron-Fehlerbericht konnte nicht gesendet werden: %s", err)


def _schliesse_abgelaufene_stundenwarteschlangen(
    verlauf_dateiname,
    rechnungsverlauf: list,
    vorjahr_dateiname,
    rechnungsverlauf_vorjahr: list,
) -> None:
    """Schliesst alte Nullstunden-Wartezustaende in geladenen Verlaeufen."""
    aktuelles_datum = heute()
    abgeschlossen = schliesse_abgelaufene_stundenwarteschlangen(
        verlauf_dateiname,
        rechnungsverlauf,
        aktuelles_datum,
    )
    if rechnungsverlauf_vorjahr:
        abgeschlossen += schliesse_abgelaufene_stundenwarteschlangen(
            vorjahr_dateiname,
            rechnungsverlauf_vorjahr,
            aktuelles_datum,
        )

    if abgeschlossen:
        logger.warning(
            "%s abgelaufene Nullstunden-Wartezustaende wurden ohne Rechnung "
            "als no_invoice abgeschlossen.",
            abgeschlossen,
        )


if __name__ == "__main__":
    main()
