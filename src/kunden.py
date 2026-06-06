import json
from datetime import datetime


def sollte_kunde_entfernt_werden(eintrag: dict, heute: datetime) -> bool:
    """Prueft, ob ein Kunde nach der aktuellen Rechnung entfernt werden kann."""
    if eintrag.get("einmalig") is True:
        return True

    if eintrag.get("letzte_rechnung"):
        try:
            letzte_erlaubte = datetime.strptime(eintrag["letzte_rechnung"], "%Y-%m")
            return (heute.year, heute.month) >= (
                letzte_erlaubte.year,
                letzte_erlaubte.month,
            )
        except ValueError:
            return False

    return False


def entferne_kunde_aus_daten(daten: list, eintrag: dict) -> list:
    """Entfernt einen Kunden anhand von Firma und Name aus der Datenliste."""
    return [
        kunde
        for kunde in daten
        if not (
            kunde.get("firma", "").strip().lower() == eintrag["firma"].strip().lower()
            and kunde.get("name", "").strip().lower() == eintrag["name"].strip().lower()
        )
    ]


def speichere_kundendaten(pfad, daten: list) -> None:
    """Schreibt die Kundendaten als JSON-Datei."""
    with open(pfad, "w", encoding="utf-8") as daten_file:
        json.dump(daten, daten_file, indent=2, ensure_ascii=False)
