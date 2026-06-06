from tools import check_setup


def _erstelle_pfade(tmp_path):
    """Erstellt die fuer den vollstaendigen Pfadcheck benoetigten Pfade."""
    data_dir = tmp_path / "data"
    templates_dir = tmp_path / "templates"
    hours_dir = tmp_path / "hours"
    archive_dir = tmp_path / "archiv"
    for pfad in (data_dir, templates_dir, hours_dir, archive_dir):
        pfad.mkdir()

    (tmp_path / ".env").write_text("MAIL_SERVER=test\n", encoding="utf-8")
    (data_dir / "daten.json").write_text("[]\n", encoding="utf-8")
    (data_dir / "konfiguration.json").write_text("{}\n", encoding="utf-8")
    (templates_dir / "mail_template.html").write_text("Mail", encoding="utf-8")
    (templates_dir / "rechnung_template.html").write_text("PDF", encoding="utf-8")

    settings = {
        "paths": {
            "data_dir": str(data_dir),
            "templates_dir": str(templates_dir),
            "hours_dir": str(hours_dir),
            "backup_dir": str(tmp_path / "backup"),
            "image_dir": str(tmp_path / "img"),
        },
        "logging": {
            "enabled": True,
            "directory": str(tmp_path / "logs"),
        },
    }
    return settings, archive_dir


def test_full_path_check_accepts_accessible_paths(tmp_path, monkeypatch):
    """Der volle Check akzeptiert erreichbare Lese- und Schreibziele."""
    settings, archive_dir = _erstelle_pfade(tmp_path)
    monkeypatch.setattr(check_setup, "PROJECT_ROOT", tmp_path)
    report = check_setup.CheckReport()

    check_setup._check_paths(
        report,
        settings,
        [{"archiv_pfad": str(archive_dir)}],
    )

    assert report.errors == []
    assert list(archive_dir.iterdir()) == []


def test_full_path_check_reports_missing_archive(tmp_path, monkeypatch):
    """Ein fehlendes Kundenarchiv wird als Setup-Fehler gemeldet."""
    settings, _ = _erstelle_pfade(tmp_path)
    monkeypatch.setattr(check_setup, "PROJECT_ROOT", tmp_path)
    report = check_setup.CheckReport()

    check_setup._check_paths(
        report,
        settings,
        [{"archiv_pfad": str(tmp_path / "fehlt")}],
    )

    assert any("Archivpfad existiert nicht" in error for error in report.errors)


def test_design_check_reports_invalid_color():
    """Der Setup-Check meldet ungueltige Designfarben."""
    report = check_setup.CheckReport()

    check_setup._check_design_settings(
        report,
        {"design": {"pdf": {"accent_color": "dunkelblau"}}},
    )

    assert any("Design-Konfiguration ist ungueltig" in error for error in report.errors)


def test_branding_check_warns_about_missing_configured_logo(tmp_path, monkeypatch):
    """Der Setup-Check warnt bei einem fehlenden konfigurierten Logo."""
    monkeypatch.setattr(check_setup, "PROJECT_ROOT", tmp_path)
    report = check_setup.CheckReport()

    check_setup._check_branding_settings(
        report,
        {
            "paths": {"image_dir": "img"},
            "branding": {"pdf_logo": None, "mail_logo": "mail-logo.png"},
        },
    )

    assert report.errors == []
    assert any("Mail-Logo fehlt" in warning for warning in report.warnings)
