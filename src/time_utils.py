from datetime import date, datetime

MONTH_NAMES = (
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


def today() -> date:
    """Liefert das aktuelle lokale Datum ueber eine zentrale Zeitquelle."""
    return date.today()


def now() -> datetime:
    """Liefert den aktuellen lokalen Zeitpunkt ueber eine zentrale Zeitquelle."""
    return datetime.now()


def format_month_year(value: date | datetime) -> str:
    """Formatiert Monat und Jahr ohne Abhaengigkeit von System-Locales."""
    return f"{MONTH_NAMES[value.month - 1]} {value.year}"
