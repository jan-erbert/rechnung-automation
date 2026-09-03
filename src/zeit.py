from datetime import date, datetime

MONATSNAMEN = (
    "Januar",
    "Februar",
    "März",
    "April",
    "Mai",
    "Juni",
    "Juli",
    "August",
    "September",
    "Oktober",
    "November",
    "Dezember",
)


def heute() -> date:
    """Liefert das aktuelle lokale Datum ueber eine zentrale Zeitquelle."""
    return date.today()


def jetzt() -> datetime:
    """Liefert den aktuellen lokalen Zeitpunkt ueber eine zentrale Zeitquelle."""
    return datetime.now()


def formatiere_monat_jahr(wert: date | datetime) -> str:
    """Formatiert Monat und Jahr ohne Abhaengigkeit von System-Locales."""
    return f"{MONATSNAMEN[wert.month - 1]} {wert.year}"
