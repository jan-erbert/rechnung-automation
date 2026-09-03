from datetime import date

from zeit import formatiere_monat_jahr


def test_month_name_does_not_depend_on_system_locale():
    """Deutsche Monatsnamen werden unabhaengig von System-Locales erzeugt."""
    assert formatiere_monat_jahr(date(2026, 3, 1)) == "März 2026"
