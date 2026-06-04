import json
import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)


def lade_verlauf_datei(dateiname, jahr, backup_dir: Path, interactive: bool = True):
    """Laedt eine Verlaufsdatei oder legt sie bei Bedarf neu an."""
    if not os.path.exists(dateiname):
        logger.info("Keine Verlaufsdatei vorhanden. Es wird eine neue Datei erstellt.")

        os.makedirs(Path(dateiname).parent, exist_ok=True)
        try:
            with open(dateiname, "w", encoding="utf-8") as f:
                json.dump([], f, indent=2, ensure_ascii=False)
        except Exception as err:
            logger.error("Konnte neue Verlaufsdatei nicht anlegen: %s", dateiname)
            raise SystemExit("Abbruch zur Sicherheit.") from err

        return []

    try:
        with open(dateiname, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        logger.error("Fehler beim Laden der Verlaufsdatei '%s': %s", dateiname, e)
        logger.error("Die Datei scheint ungueltiges JSON zu enthalten.")

        if not interactive:
            raise RuntimeError(f"Verlaufsdatei '{dateiname}' ist ungueltig.") from e

        while True:
            entscheidung = (
                input("Möchtest du die fehlerhafte Datei überschreiben? (y/n): ")
                .strip()
                .lower()
            )
            if entscheidung == "y":
                backup_entscheidung = (
                    input("Willst du vorher eine Backup-Datei anlegen? (y/n): ")
                    .strip()
                    .lower()
                )
                if backup_entscheidung == "y":
                    backup_path = backup_dir / f"verlauf-{jahr}_backup.json"
                    os.makedirs(backup_path.parent, exist_ok=True)
                    try:
                        os.rename(dateiname, backup_path)
                        logger.info("Sicherung gespeichert unter: %s", backup_path)
                    except Exception as err:
                        logger.warning("Backup konnte nicht erstellt werden: %s", err)
                        raise SystemExit("Abbruch zur Sicherheit.") from err
                else:
                    logger.warning("Kein Backup erstellt.")

                logger.info("Leere Datei wird angelegt.")
                return []
            if entscheidung == "n":
                raise SystemExit("Vorgang abgebrochen.")

            logger.info("Bitte y oder n eingeben.")


def baue_verlaufseintrag(
    eintrag: dict,
    heute,
    rechnungsnummer: str,
    rechnungsdatum: str,
    betrag: str,
    abrechnungszyklus: int | None = None,
) -> dict:
    """Baut einen Eintrag fuer den Rechnungsverlauf."""
    verlaufseintrag = {
        "firma": eintrag["firma"],
        "name": eintrag["name"],
        "monat": heute.month,
        "jahr": heute.year,
        "rechnungsnummer": rechnungsnummer,
        "rechnungsdatum": rechnungsdatum,
        "betrag": betrag,
        "id": (
            f"{eintrag['firma'].lower().strip()}__"
            f"{eintrag['name'].lower().strip()}__"
            f"{heute.strftime('%Y-%m')}"
        ),
    }

    if abrechnungszyklus is not None:
        verlaufseintrag["zyklus_monate"] = abrechnungszyklus

    return verlaufseintrag


def speichere_verlauf(verlauf_dateiname, rechnungsverlauf: list) -> None:
    """Schreibt den Rechnungsverlauf als JSON-Datei."""
    with open(verlauf_dateiname, "w", encoding="utf-8") as verlauf_file:
        json.dump(rechnungsverlauf, verlauf_file, indent=2, ensure_ascii=False)
