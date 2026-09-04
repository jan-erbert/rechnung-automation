from pathlib import Path
from types import SimpleNamespace

import pytest

from startup_checks import check_start_requirements


def _erstelle_startpfade(tmp_path: Path):
    """Erstellt zentrale Dateien fuer einen erfolgreichen Mini-Check."""
    data_dir = tmp_path / "data"
    templates_dir = tmp_path / "templates"
    customers_dir = tmp_path / "customers"
    data_dir.mkdir()
    templates_dir.mkdir()
    customers_dir.mkdir()
    (tmp_path / "config").mkdir()
    (tmp_path / "config" / "settings.yaml").write_text("pdf: {}\n", encoding="utf-8")
    (tmp_path / ".env").write_text("MAIL_SERVER=test\n", encoding="utf-8")
    invoice_config = tmp_path / "config" / "invoice.yaml"
    invoice_config.write_text("sender: {}\n", encoding="utf-8")
    (templates_dir / "email_template.html").write_text("Mail", encoding="utf-8")
    (templates_dir / "invoice_template.html").write_text("PDF", encoding="utf-8")
    return SimpleNamespace(
        base_dir=tmp_path,
        data_dir=data_dir,
        customers_dir=customers_dir,
        invoice_config=invoice_config,
        templates_dir=templates_dir,
    )


def _mail_config() -> dict:
    """Erstellt eine vollstaendige Mail-Konfiguration."""
    return {
        "server": "smtp.example.com",
        "port": 587,
        "user": "sender@example.com",
        "password": "secret",
    }


def test_start_check_accepts_minimal_valid_setup(tmp_path):
    """Der Mini-Check akzeptiert die zentralen lesbaren Dateien."""
    paths = _erstelle_startpfade(tmp_path)

    check_start_requirements(
        {"runtime": {}, "pdf": {"engine": "weasyprint"}},
        paths,
        [],
        _mail_config(),
    )


def test_start_check_rejects_missing_template(tmp_path):
    """Eine fehlende zentrale Vorlage stoppt den Mini-Check."""
    paths = _erstelle_startpfade(tmp_path)
    (paths.templates_dir / "email_template.html").unlink()

    with pytest.raises(ValueError, match="Mailvorlage fehlt"):
        check_start_requirements(
            {"runtime": {}, "pdf": {"engine": "weasyprint"}},
            paths,
            [],
            _mail_config(),
        )


def test_start_check_rejects_non_list_customer_data(tmp_path):
    """Kundendaten muessen beim Start eine Liste sein."""
    paths = _erstelle_startpfade(tmp_path)

    with pytest.raises(ValueError, match="als Liste"):
        check_start_requirements(
            {"runtime": {}, "pdf": {"engine": "weasyprint"}},
            paths,
            {},
            _mail_config(),
        )


def test_start_check_rejects_invalid_design_color(tmp_path):
    """Eine ungueltige Designfarbe stoppt den Rechnungslauf fruehzeitig."""
    paths = _erstelle_startpfade(tmp_path)

    with pytest.raises(ValueError, match="sechsstellige Hex-Farbe"):
        check_start_requirements(
            {
                "runtime": {},
                "pdf": {"engine": "weasyprint"},
                "design": {"mail": {"link_color": "blau"}},
            },
            paths,
            [],
            _mail_config(),
        )


def test_start_check_rejects_unsupported_logo_format(tmp_path):
    """Ein nicht unterstuetztes Logoformat stoppt den Rechnungslauf fruehzeitig."""
    paths = _erstelle_startpfade(tmp_path)

    with pytest.raises(ValueError, match="Format"):
        check_start_requirements(
            {
                "runtime": {},
                "pdf": {"engine": "weasyprint"},
                "branding": {"mail_logo": "logo.svg"},
            },
            paths,
            [],
            _mail_config(),
        )


def test_start_check_rejects_unsafe_filename_prefix(tmp_path):
    """Ein unsicheres Dateipraefix stoppt den Rechnungslauf fruehzeitig."""
    paths = _erstelle_startpfade(tmp_path)

    with pytest.raises(ValueError, match="file_naming.invoice_prefix"):
        check_start_requirements(
            {
                "pdf": {"engine": "weasyprint"},
                "file_naming": {"invoice_prefix": "../Rechnung"},
            },
            paths,
            [],
            _mail_config(),
        )
