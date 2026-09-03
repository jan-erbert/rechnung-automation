import re
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
CUSTOMERS_DIR = BASE_DIR / "customers"
DEFAULT_DATEN_PATH = CUSTOMERS_DIR
SRC_DIR = BASE_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from validierung import (  # noqa: E402
    normalisiere_mail_liste,
    validiere_betrag,
    validiere_datum,
    validiere_einheit,
    validiere_kundeneintrag,
    validiere_monat,
    validiere_nichtnegative_ganzzahl,
    validiere_positive_ganzzahl,
)
from kundendateien import lade_kundendateien, speichere_kundendatei  # noqa: E402


def lade_kundendaten(dateiname: Path = DEFAULT_DATEN_PATH) -> list:
    """Laedt die bestehenden einzelnen YAML-Kundendateien."""
    if not dateiname.exists():
        return []
    return lade_kundendateien(dateiname)


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
    id_vorschlag = _erstelle_kunden_id(kunde["firma"])
    customer_id = frage(f"Kunden-ID (Standard: {id_vorschlag}): ") or id_vorschlag
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", customer_id):
        raise ValueError(
            "Kunden-ID darf nur Kleinbuchstaben, Zahlen und Bindestriche enthalten."
        )
    kunde["id"] = customer_id
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
    """Speichert einen neuen Kunden in einer eigenen YAML-Datei."""
    validiere_kundeneintrag(kunde)
    zielpfad = dateipfad / f"{kunde['id']}.yaml"
    if zielpfad.exists():
        raise FileExistsError(f"Kundendatei existiert bereits: {zielpfad}")
    speichere_kundendatei(kunde, zielpfad)
    print(f"\nKunde gespeichert in {zielpfad.resolve()}.")


def _erstelle_kunden_id(firma: str) -> str:
    """Erzeugt einen einfachen stabilen ID-Vorschlag aus dem Firmennamen."""
    text = firma.lower().replace("ä", "ae").replace("ö", "oe").replace("ü", "ue")
    text = text.replace("ß", "ss")
    return re.sub(r"[^a-z0-9]+", "-", text).strip("-") or "kunde"


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
