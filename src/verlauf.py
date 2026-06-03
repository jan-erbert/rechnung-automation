import json
import os
from pathlib import Path


def lade_verlauf_datei(dateiname, jahr, backup_dir: Path):
    """Laedt eine Verlaufsdatei oder legt sie bei Bedarf neu an."""
    if not os.path.exists(dateiname):
        print("ℹ️ Keine Verlaufsdatei vorhanden. Es wird eine neue Datei erstellt.")

        os.makedirs(Path(dateiname).parent, exist_ok=True)
        try:
            with open(dateiname, "w", encoding="utf-8") as f:
                json.dump([], f, indent=2, ensure_ascii=False)
        except Exception as err:
            print(f"❌ Konnte neue Verlaufsdatei nicht anlegen: {dateiname}\n{err}")
            print("🚫 Abbruch zur Sicherheit.")
            exit(1)

        return []

    try:
        with open(dateiname, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        print(f"\n❌ Fehler beim Laden der Verlaufsdatei '{dateiname}':\n{e}")
        print("‼️ Die Datei scheint ungültiges JSON zu enthalten.")

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
                        print(f"🛡️ Sicherung gespeichert unter: {backup_path}")
                    except Exception as err:
                        print(f"⚠️ Backup konnte nicht erstellt werden: {err}")
                        print("🚫 Abbruch zur Sicherheit.")
                        exit(1)
                else:
                    print("⚠️ Kein Backup erstellt.")

                print("🆕 Leere Datei wird angelegt.")
                return []
            if entscheidung == "n":
                print("🚫 Vorgang abgebrochen.")
                exit(1)

            print("Bitte y oder n eingeben.")


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
