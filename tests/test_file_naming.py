from datetime import datetime

import pytest

from file_naming import (
    build_invoice_filename,
    build_preview_filename,
    validate_file_naming_config,
)


def test_file_naming_defaults_preserve_previous_names():
    """Fehlende Einstellungen behalten die bisherigen englischen Praefixe."""
    assert validate_file_naming_config({}) == {
        "invoice_prefix": "Invoice",
        "preview_prefix": "PREVIEW",
    }


def test_configured_invoice_and_preview_names_are_consistent():
    """Rechnung und Vorschau verwenden dieselbe konfigurierte Grundbenennung."""
    config = {
        "invoice_prefix": "Rechnung",
        "preview_prefix": "VORSCHAU",
    }

    assert (
        build_invoice_filename("tv-alzey", "09-2026", config)
        == "Rechnung_tv-alzey_09-2026.pdf"
    )
    assert (
        build_preview_filename(
            "tv-alzey",
            "09-2026",
            datetime(2026, 9, 4, 15, 30, 0),
            config,
        )
        == "VORSCHAU_Rechnung_tv-alzey_09-2026_2026-09-04_15-30-00.pdf"
    )


@pytest.mark.parametrize(
    "prefix",
    ["", " Rechnung", "Rechnung ", "../Rechnung", "Rechnung/2026", "Rechnung.pdf"],
)
def test_file_naming_rejects_unsafe_prefixes(prefix):
    """Unsichere oder missverstaendliche Praefixe werden frueh abgelehnt."""
    with pytest.raises(ValueError, match="file_naming.invoice_prefix"):
        validate_file_naming_config({"invoice_prefix": prefix})


def test_file_naming_rejects_unknown_option():
    """Tippfehler in der Benennungskonfiguration bleiben nicht unbemerkt."""
    with pytest.raises(ValueError, match="file_naming.invoice_preffix"):
        validate_file_naming_config({"invoice_preffix": "Rechnung"})
