# src/main.py
import argparse
import json
import locale
import logging
import os
from datetime import datetime

from konfiguration import lade_konfiguration, lade_mail_umgebung
from logging_setup import konfiguriere_logging
from paths import erstelle_pfade
from settings_loader import lade_settings
from templates import lade_templates
from verlauf import lade_verlauf_datei
from workflow import verarbeite_rechnungen

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
    logger.info("Starte Rechnungslauf.")
    if log_file:
        logger.info("Logdatei: %s", log_file)

    runtime_config = settings.get("runtime", {})
    if not isinstance(runtime_config, dict):
        raise ValueError("Der YAML-Bereich 'runtime' muss eine Map sein.")

    locale.setlocale(locale.LC_TIME, runtime_config.get("locale", "de_DE.UTF-8"))

    # 📄 Kundendaten laden
    with open(pfade.data_dir / "daten.json", "r", encoding="utf-8") as f:
        daten = json.load(f)

    # 📧 E-Mail Konfiguration
    mail_config = lade_mail_umgebung(pfade.base_dir / ".env")

    # 📥 Konfiguration laden
    konfig = lade_konfiguration(pfade.data_dir / "konfiguration.json")

    # ⏳ Verlauf laden
    jahr = datetime.today().year
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

    # 📩 Jinja2-Templates laden
    templates = lade_templates(pfade.vorlagen_dir)

    verarbeite_rechnungen(
        daten=daten,
        pfade=pfade,
        konfig=konfig,
        mail_config=mail_config,
        pdf_config=settings.get("pdf", {}),
        templates=templates,
        rechnungsverlauf=rechnungsverlauf,
        rechnungsverlauf_vorjahr=rechnungsverlauf_vorjahr,
        verlauf_dateiname=verlauf_dateiname,
        interactive=not args.non_interactive,
    )
    logger.info("Rechnungslauf beendet.")


if __name__ == "__main__":
    main()
