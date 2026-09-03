import json
import logging
import os
import tempfile
from datetime import date, datetime
from pathlib import Path

from zeit import jetzt

logger = logging.getLogger(__name__)

VERSANDSTATUS_PENDING = "pending"
VERSANDSTATUS_SENT = "sent"
VERSANDSTATUS_FAILED = "failed"
VERSANDSTATUS_WAITING_HOURS = "waiting_hours"
VERSANDSTATUS_NO_INVOICE = "no_invoice"


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
    versandstatus: str | None = None,
) -> dict:
    """Baut einen Eintrag fuer den Rechnungsverlauf."""
    kunden_id = eintrag.get("id") or (
        f"{eintrag['firma'].lower().strip()}__{eintrag['name'].lower().strip()}"
    )
    verlaufseintrag = {
        "kunden_id": kunden_id,
        "firma": eintrag["firma"],
        "name": eintrag["name"],
        "monat": heute.month,
        "jahr": heute.year,
        "rechnungsnummer": rechnungsnummer,
        "rechnungsdatum": rechnungsdatum,
        "betrag": betrag,
        "id": f"{kunden_id}__{heute.strftime('%Y-%m')}",
    }

    if abrechnungszyklus is not None:
        verlaufseintrag["zyklus_monate"] = abrechnungszyklus
    if versandstatus is not None:
        verlaufseintrag["versandstatus"] = versandstatus
        verlaufseintrag["versandstatus_zeitpunkt"] = jetzt().isoformat(
            timespec="seconds"
        )

    return verlaufseintrag


def speichere_verlauf(verlauf_dateiname, rechnungsverlauf: list) -> None:
    """Schreibt den Rechnungsverlauf atomar als JSON-Datei."""
    verlauf_pfad = Path(verlauf_dateiname)
    verlauf_pfad.parent.mkdir(parents=True, exist_ok=True)
    temp_pfad = None

    try:
        with tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-8",
            dir=verlauf_pfad.parent,
            prefix=f".{verlauf_pfad.name}.",
            suffix=".tmp",
            delete=False,
        ) as temp_file:
            temp_pfad = Path(temp_file.name)
            json.dump(rechnungsverlauf, temp_file, indent=2, ensure_ascii=False)
            temp_file.flush()
            os.fsync(temp_file.fileno())

        os.replace(temp_pfad, verlauf_pfad)
    finally:
        if temp_pfad and temp_pfad.exists():
            temp_pfad.unlink()


def speichere_oder_ersetze_verlaufseintrag(
    verlauf_dateiname,
    rechnungsverlauf: list,
    verlaufseintrag: dict,
) -> None:
    """Speichert einen Verlaufseintrag anhand seiner ID atomar."""
    neuer_verlauf = [
        vorhandener
        for vorhandener in rechnungsverlauf
        if vorhandener.get("id") != verlaufseintrag["id"]
    ]
    neuer_verlauf.append(verlaufseintrag)
    speichere_verlauf(verlauf_dateiname, neuer_verlauf)
    rechnungsverlauf[:] = neuer_verlauf


def setze_versandstatus(
    verlauf_dateiname,
    rechnungsverlauf: list,
    rechnung_id: str,
    versandstatus: str,
) -> None:
    """Aktualisiert den Versandstatus eines Verlaufseintrags atomar."""
    neuer_verlauf = [eintrag.copy() for eintrag in rechnungsverlauf]
    for eintrag in neuer_verlauf:
        if eintrag.get("id") == rechnung_id:
            eintrag["versandstatus"] = versandstatus
            eintrag["versandstatus_zeitpunkt"] = jetzt().isoformat(timespec="seconds")
            speichere_verlauf(verlauf_dateiname, neuer_verlauf)
            rechnungsverlauf[:] = neuer_verlauf
            return

    raise ValueError(f"Verlaufseintrag '{rechnung_id}' wurde nicht gefunden.")


def ist_erfolgreich_versendet(verlaufseintrag: dict) -> bool:
    """Prueft den Versandstatus mit Rueckwaertskompatibilitaet."""
    return (
        verlaufseintrag.get("versandstatus", VERSANDSTATUS_SENT) == VERSANDSTATUS_SENT
    )


def ist_abrechnung_abgeschlossen(verlaufseintrag: dict) -> bool:
    """Prueft, ob ein Abrechnungszeitpunkt abschliessend verarbeitet wurde."""
    status = verlaufseintrag.get("versandstatus", VERSANDSTATUS_SENT)
    return status in (VERSANDSTATUS_SENT, VERSANDSTATUS_NO_INVOICE)


def schliesse_abgelaufene_stundenwarteschlangen(
    verlauf_dateiname,
    rechnungsverlauf: list,
    heute: date | datetime,
) -> int:
    """Schliesst alte Nullstunden-Wartezustaende ohne Rechnung ab."""
    neuer_verlauf = [eintrag.copy() for eintrag in rechnungsverlauf]
    abgeschlossen = 0

    for eintrag in neuer_verlauf:
        if eintrag.get("versandstatus") != VERSANDSTATUS_WAITING_HOURS:
            continue

        jahr = eintrag.get("jahr")
        monat = eintrag.get("monat")
        if not isinstance(jahr, int) or not isinstance(monat, int):
            continue
        if (jahr, monat) >= (heute.year, heute.month):
            continue

        eintrag["versandstatus"] = VERSANDSTATUS_NO_INVOICE
        eintrag["versandstatus_zeitpunkt"] = jetzt().isoformat(timespec="seconds")
        abgeschlossen += 1

    if abgeschlossen:
        speichere_verlauf(verlauf_dateiname, neuer_verlauf)
        rechnungsverlauf[:] = neuer_verlauf

    return abgeschlossen
