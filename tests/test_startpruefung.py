from pathlib import Path
from types import SimpleNamespace

import pytest

from startpruefung import pruefe_startvoraussetzungen


def _erstelle_startpfade(tmp_path: Path):
    """Erstellt zentrale Dateien fuer einen erfolgreichen Mini-Check."""
    data_dir = tmp_path / "data"
    templates_dir = tmp_path / "templates"
    data_dir.mkdir()
    templates_dir.mkdir()
    (tmp_path / "config").mkdir()
    (tmp_path / "config" / "settings.yaml").write_text("pdf: {}\n", encoding="utf-8")
    (tmp_path / ".env").write_text("MAIL_SERVER=test\n", encoding="utf-8")
    (data_dir / "daten.json").write_text("[]\n", encoding="utf-8")
    (data_dir / "konfiguration.json").write_text("{}\n", encoding="utf-8")
    (templates_dir / "mail_template.html").write_text("Mail", encoding="utf-8")
    (templates_dir / "rechnung_template.html").write_text("PDF", encoding="utf-8")
    return SimpleNamespace(
        base_dir=tmp_path,
        data_dir=data_dir,
        templates_dir=templates_dir,
    )


def _mail_config() -> dict:
    """Erstellt eine vollstaendige Mail-Konfiguration."""
    return {
        "server": "smtp.example.com",
        "port": 587,
        "user": "sender@example.com",
        "passwort": "secret",
    }


def test_start_check_accepts_minimal_valid_setup(tmp_path):
    """Der Mini-Check akzeptiert die zentralen lesbaren Dateien."""
    pfade = _erstelle_startpfade(tmp_path)

    pruefe_startvoraussetzungen(
        {"runtime": {}, "pdf": {"engine": "weasyprint"}},
        pfade,
        [],
        _mail_config(),
    )


def test_start_check_rejects_missing_template(tmp_path):
    """Eine fehlende zentrale Vorlage stoppt den Mini-Check."""
    pfade = _erstelle_startpfade(tmp_path)
    (pfade.templates_dir / "mail_template.html").unlink()

    with pytest.raises(ValueError, match="Mailvorlage fehlt"):
        pruefe_startvoraussetzungen(
            {"runtime": {}, "pdf": {"engine": "weasyprint"}},
            pfade,
            [],
            _mail_config(),
        )


def test_start_check_rejects_non_list_customer_data(tmp_path):
    """Kundendaten muessen beim Start eine Liste sein."""
    pfade = _erstelle_startpfade(tmp_path)

    with pytest.raises(ValueError, match="JSON-Liste"):
        pruefe_startvoraussetzungen(
            {"runtime": {}, "pdf": {"engine": "weasyprint"}},
            pfade,
            {},
            _mail_config(),
        )


def test_start_check_rejects_invalid_design_color(tmp_path):
    """Eine ungueltige Designfarbe stoppt den Rechnungslauf fruehzeitig."""
    pfade = _erstelle_startpfade(tmp_path)

    with pytest.raises(ValueError, match="sechsstellige Hex-Farbe"):
        pruefe_startvoraussetzungen(
            {
                "runtime": {},
                "pdf": {"engine": "weasyprint"},
                "design": {"mail": {"link_color": "blau"}},
            },
            pfade,
            [],
            _mail_config(),
        )


def test_start_check_rejects_unsupported_logo_format(tmp_path):
    """Ein nicht unterstuetztes Logoformat stoppt den Rechnungslauf fruehzeitig."""
    pfade = _erstelle_startpfade(tmp_path)

    with pytest.raises(ValueError, match="Format"):
        pruefe_startvoraussetzungen(
            {
                "runtime": {},
                "pdf": {"engine": "weasyprint"},
                "branding": {"mail_logo": "logo.svg"},
            },
            pfade,
            [],
            _mail_config(),
        )
