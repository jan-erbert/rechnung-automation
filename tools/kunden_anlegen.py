import json
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DEFAULT_DATEN_PATH = DATA_DIR / "daten.json"
SRC_DIR = BASE_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from validierung import (  # noqa: E402
    normalisiere_mail_liste,
    validiere_betrag,
    validiere_datum,
    validiere_einheit,
    validiere_monat,
    validiere_nichtnegative_ganzzahl,
    validiere_positive_ganzzahl,
)


def lade_kundendaten(dateiname: Path = DEFAULT_DATEN_PATH) -> list:
    """Laedt die bestehende Kundenliste oder erstellt eine neue Liste."""
    if not dateiname.exists():
        print(f"Datei '{dateiname}' nicht gefunden. Es wird eine neue erstellt.")
        return []

    try:
        with dateiname.open("r", encoding="utf-8") as daten_file:
            daten = json.load(daten_file)
    except json.JSONDecodeError as err:
        return _behandle_ungueltige_kundendatei(dateiname, err)

    if not isinstance(daten, list):
        return _behandle_ungueltige_kundendatei(
            dateiname,
            ValueError("daten.json ist kein Array."),
        )

    return daten


def _behandle_ungueltige_kundendatei(dateiname: Path, fehler: Exception) -> list:
    """Fragt nach dem Umgang mit einer ungueltigen Kundendatei."""
    print(f"\nFehler beim Laden von '{dateiname}': {fehler}")
    print("Die Datei scheint ungueltig zu sein.")

    while True:
        entscheidung = (
            input("Moechtest du die fehlerhafte Datei ueberschreiben? (y/n): ")
            .strip()
            .lower()
        )
        if entscheidung == "y":
            _sichere_kundendatei_falls_gewuenscht(dateiname)
            _schreibe_kundendaten(dateiname, [])
            print("Neue leere Datei wurde erstellt.")
            return []
        if entscheidung == "n":
            raise SystemExit("Vorgang abgebrochen.")
        print("Bitte y oder n eingeben.")


def _sichere_kundendatei_falls_gewuenscht(dateiname: Path) -> None:
    """Erstellt optional ein Backup der ungueltigen Kundendatei."""
    entscheidung = input("Willst du vorher ein Backup speichern? (y/n): ").strip()
    if entscheidung.lower() != "y":
        print("Kein Backup erstellt.")
        return

    backup_dir = BASE_DIR / "backup"
    backup_dir.mkdir(parents=True, exist_ok=True)
    backup_pfad = backup_dir / "daten_backup.json"
    try:
        dateiname.replace(backup_pfad)
        print(f"Backup gespeichert unter: {backup_pfad}")
    except OSError as err:
        print(f"Backup fehlgeschlagen: {err}")
        raise SystemExit("Abbruch zur Sicherheit.") from err


def frage(prompt: str, optional: bool = True) -> str | None:
    """Fragt einen Textwert ab und validiert Pflichtfelder."""
    while True:
        eingabe = input(prompt).strip()
        if eingabe:
            return eingabe
        if optional:
            return None
        print("Dieses Feld darf nicht leer sein.")


def frage_validiert(prompt: str, validierung, optional: bool = False):
    """Fragt einen Wert ab, bis die uebergebene Validierung erfolgreich ist."""
    while True:
        wert = frage(prompt, optional=optional)
        if wert is None:
            return None
        try:
            validierung(wert)
            return wert
        except ValueError as err:
            print(f"Ungueltige Eingabe: {err}")


def frage_mehrere_leistungen() -> list | None:
    """Fragt optionale Zusatzleistungen fuer einen Kunden ab."""
    leistungen = []
    while True:
        beschreibung = frage(
            "Zusaetzliche Leistung - Beschreibung (leer zum Beenden): "
        )
        if not beschreibung:
            break

        preis = frage_validiert(
            "Preis (z. B. 9,99 oder Inklusive): ",
            lambda wert: validiere_betrag(
                wert,
                "Preis",
                inklusive_erlaubt=True,
            ),
        )
        leistungen.append({"beschreibung": beschreibung, "preis": preis})

        nochmal = input("Weitere Leistung hinzufuegen? (j/n): ").strip().lower()
        if nochmal != "j":
            break

    return leistungen or None


def neuer_kunde() -> dict:
    """Fragt interaktiv einen neuen Kundeneintrag ab."""
    print("\nNeuen Kunden anlegen:\n")

    kunde = {
        "name": frage("Name oder Ansprechpartner: ", optional=False),
        "firma": frage("Firma: ", optional=False),
        "email": frage("E-Mail: ", optional=False),
        "strasse": frage("Strasse und Hausnummer: ", optional=False),
        "plz": frage("PLZ: ", optional=False),
        "ort": frage("Ort: ", optional=False),
        "webseite": frage("Webseite (optional, nur bei Hosting relevant): "),
    }
    cc_adressen = frage_mail_cc()
    if cc_adressen:
        kunde["cc"] = cc_adressen

    einmalig = (
        input(
            "Soll diese Rechnung nur einmalig erstellt werden? Standard: nein (y/n): "
        )
        .strip()
        .lower()
        == "y"
    )
    if einmalig:
        kunde["einmalig"] = True

    kunde["hauptleistung"] = _frage_hauptleistung(einmalig)
    _frage_optionale_felder(kunde, einmalig)

    leistungen = frage_mehrere_leistungen()
    if leistungen:
        kunde["weitere_leistungen"] = leistungen

    aktiv_input = input("Soll dieser Kunde ab jetzt aktiv sein? (y/n): ")
    if aktiv_input.strip().lower() == "n":
        kunde["aktiv"] = False

    return kunde


def frage_mail_cc() -> list[str]:
    """Fragt optionale CC-Empfaenger fuer einen Kundeneintrag ab."""
    cc_adressen = []
    while True:
        cc = frage("CC-E-Mail (optional, leer zum Fortfahren): ")
        if not cc:
            return cc_adressen
        try:
            cc_adressen.extend(normalisiere_mail_liste(cc, "CC-E-Mail"))
        except ValueError as err:
            print(f"Ungueltige Eingabe: {err}")


def _frage_hauptleistung(einmalig: bool) -> dict:
    """Fragt die Hauptleistung fuer einen Kundeneintrag ab."""
    print("\nHauptleistung eintragen:")
    beschreibung = frage("Beschreibung der Hauptleistung: ", optional=False)
    betrag = frage_validiert(
        "Betrag (z. B. 49,99): ",
        lambda wert: validiere_betrag(wert, "Betrag"),
    )

    if einmalig:
        einheit = "pauschal"
    else:
        einheit = frage_validiert(
            "Einheit der Abrechnung (Monat, Stunde, pauschal - Standard: Monat): ",
            validiere_einheit,
            optional=True,
        )
        einheit = einheit or "Monat"

    return {
        "beschreibung": beschreibung,
        "einheit": einheit.strip().lower(),
        "betrag": betrag,
    }


def _frage_optionale_felder(kunde: dict, einmalig: bool) -> None:
    """Ergaenzt optionale Kundenfelder."""
    if not einmalig:
        zyklus = frage_validiert(
            "Abrechnungszyklus in Monaten (Standard: 1): ",
            lambda wert: validiere_positive_ganzzahl(wert, "Abrechnungszyklus"),
            optional=True,
        )
        if zyklus:
            kunde["abrechnungszyklus"] = int(zyklus)

    optionale_felder = {
        "rechnungsnummer": ("Rechnungsnummer-Praefix (optional): ", None),
        "rechnungsdatum": (
            "Rechnungsdatum (z. B. 01.05.2026, optional): ",
            validiere_datum,
        ),
        "faelligkeit": (
            "Faelligkeit in Tagen (z. B. 14, optional): ",
            lambda wert: validiere_nichtnegative_ganzzahl(wert, "Faelligkeit"),
        ),
        "archiv_pfad": ("Archiv-Pfad fuer PDF: ", None),
    }

    if not einmalig:
        optionale_felder["letzte_rechnung"] = (
            "Letzte zu erstellende Rechnung (YYYY-MM, optional): ",
            validiere_monat,
        )

    for key, (prompt, validierung) in optionale_felder.items():
        if validierung:
            wert = frage_validiert(prompt, validierung, optional=True)
        else:
            wert = frage(prompt)
        if wert:
            kunde[key] = wert


def daten_speichern(kunde: dict, dateipfad: Path = DEFAULT_DATEN_PATH) -> None:
    """Speichert einen neuen Kundeneintrag in daten.json."""
    daten = lade_kundendaten(dateipfad) if dateipfad.exists() else []
    daten.append(kunde)
    _schreibe_kundendaten(dateipfad, daten)
    print(f"\nKunde gespeichert in {dateipfad.resolve()}.")


def _schreibe_kundendaten(dateipfad: Path, daten: list) -> None:
    """Schreibt Kundendaten formatiert als JSON."""
    dateipfad.parent.mkdir(parents=True, exist_ok=True)
    with dateipfad.open("w", encoding="utf-8") as daten_file:
        json.dump(daten, daten_file, indent=2, ensure_ascii=False)


def main() -> None:
    """Startet die interaktive Kundenerfassung."""
    while True:
        daten_speichern(neuer_kunde())
        nochmal = input("\nWeitere Kunden anlegen? (y/n): ").strip().lower()
        if nochmal != "y":
            print("\nVorgang beendet.")
            break


if __name__ == "__main__":
    main()
