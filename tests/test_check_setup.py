from tools import check_setup


def _erstelle_pfade(tmp_path):
    """Erstellt die fuer den vollstaendigen Pfadcheck benoetigten Pfade."""
    data_dir = tmp_path / "data"
    templates_dir = tmp_path / "templates"
    hours_dir = tmp_path / "hours"
    customers_dir = tmp_path / "customers"
    archive_dir = tmp_path / "archiv"
    for path in (data_dir, templates_dir, hours_dir, customers_dir, archive_dir):
        path.mkdir()

    (tmp_path / ".env").write_text("MAIL_SERVER=test\n", encoding="utf-8")
    (tmp_path / "invoice.yaml").write_text("sender: {}\n", encoding="utf-8")
    (templates_dir / "email_template.html").write_text("Mail", encoding="utf-8")
    (templates_dir / "invoice_template.html").write_text("PDF", encoding="utf-8")

    settings = {
        "paths": {
            "data_dir": str(data_dir),
            "customers_dir": str(customers_dir),
            "invoice_config": str(tmp_path / "invoice.yaml"),
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
        [{"archive_directory": str(archive_dir)}],
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
        [{"archive_directory": str(tmp_path / "fehlt")}],
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


def test_hours_check_reports_invalid_yaml(tmp_path, monkeypatch):
    """Der Setup-Check meldet eine widerspruechliche Stunden-Monatsdatei."""
    settings, _ = _erstelle_pfade(tmp_path)
    monkeypatch.setattr(check_setup, "PROJECT_ROOT", tmp_path)
    (tmp_path / "hours" / "2026-08.yaml").write_text(
        "period: '2026-07'\ncustomers: {}\n",
        encoding="utf-8",
    )
    report = check_setup.CheckReport()

    check_setup._check_hours_files(report, settings)

    assert any("period muss '2026-08' sein" in error for error in report.errors)


def test_hours_check_warns_about_legacy_json(tmp_path, monkeypatch):
    """Alte Stunden-JSONs erhalten einen konkreten Migrationshinweis."""
    settings, _ = _erstelle_pfade(tmp_path)
    monkeypatch.setattr(check_setup, "PROJECT_ROOT", tmp_path)
    (tmp_path / "hours" / "stunden_2026_08.json").write_text(
        "[]",
        encoding="utf-8",
    )
    report = check_setup.CheckReport()

    check_setup._check_hours_files(report, settings)

    assert any("migrate_legacy_hours.py" in warning for warning in report.warnings)
