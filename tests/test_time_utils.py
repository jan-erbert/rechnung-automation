from datetime import date

from time_utils import format_month_year


def test_month_name_does_not_depend_on_system_locale():
    """Deutsche Monatsnamen werden unabhaengig von System-Locales erzeugt."""
    assert format_month_year(date(2026, 3, 1)) == "März 2026"
