import importlib.util
import re
import sys
from pathlib import Path

from dotenv import dotenv_values

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from branding import resolve_logo_path, validate_branding_config  # noqa: E402
from design import validate_design_config  # noqa: E402
from configuration import load_invoice_config, load_mail_environment  # noqa: E402
from customer_files import load_customer_files  # noqa: E402
from paths import create_paths  # noqa: E402
from pdf_service import validate_pdf_config  # noqa: E402
from path_checks import (  # noqa: E402
    check_archive_path,
    check_readable_file,
    check_readable_directory,
    check_writable_target_directory,
)
from settings_loader import load_settings  # noqa: E402
from hours_files import load_hours_month  # noqa: E402
from logging_setup import validate_log_retention  # noqa: E402
from state_backup import validate_backup_config  # noqa: E402

REQUIRED_ENV_KEYS = ("MAIL_SERVER", "MAIL_PORT", "MAIL_USER", "MAIL_PASS")


class CheckReport:
    """Sammelt Ergebnisse fuer die Setup-Pruefung."""

    def __init__(self) -> None:
        """Initialisiert leere Fehler- und Warnlisten."""
        self.errors: list[str] = []
        self.warnings: list[str] = []

    def error(self, message: str) -> None:
        """Fuegt eine Fehlermeldung hinzu."""
        self.errors.append(message)

    def warning(self, message: str) -> None:
        """Fuegt eine Warnmeldung hinzu."""
        self.warnings.append(message)

    def print_summary(self) -> None:
        """Gibt die Pruefergebnisse ohne sensible Werte aus."""
        if self.errors:
            print("Fehler:")
            for message in self.errors:
                print(f"- {message}")
        if self.warnings:
            print("Warnungen:")
            for message in self.warnings:
                print(f"- {message}")
        if not self.errors and not self.warnings:
            print("Setup-Check erfolgreich: keine Probleme gefunden.")
        elif not self.errors:
            print("Setup-Check abgeschlossen: keine Fehler, aber Warnungen.")
        else:
            print("Setup-Check fehlgeschlagen.")


def main() -> int:
    """Prueft die lokale Einrichtung ohne produktive Aktionen."""
    report = CheckReport()
    settings = _check_settings(report)
    _check_env(report, settings)
    _check_weasyprint(report)
    _check_configuration(report, settings)
    data = _check_customers(report, settings)
    if settings:
        _check_pdf_settings(report, settings)
        _check_design_settings(report, settings)
        _check_branding_settings(report, settings)
        _check_hours_files(report, settings)
        _check_paths(report, settings, data)
    report.print_summary()
    return 1 if report.errors else 0


def _check_settings(report: CheckReport) -> dict | None:
    """Prueft die YAML-Einstellungen."""
    try:
        settings = load_settings(PROJECT_ROOT / "config" / "settings.yaml")
        create_paths(settings, PROJECT_ROOT)
    except Exception as err:
        report.error(f"config/settings.yaml ist nicht gueltig: {err}")
        return None
    if not isinstance(settings.get("logging", {}), dict):
        report.error("Der YAML-Bereich 'logging' muss eine Map sein.")
    else:
        try:
            validate_log_retention(
                settings.get("logging", {}).get("retention_files", 100)
            )
        except ValueError as err:
            report.error(f"Logging-Konfiguration ist ungueltig: {err}")
    try:
        validate_backup_config(settings.get("backup", {}))
    except ValueError as err:
        report.error(f"Backup-Konfiguration ist ungueltig: {err}")
    return settings


def _check_pdf_settings(report: CheckReport, settings: dict) -> None:
    """Prueft die konfigurierte PDF-Engine."""
    try:
        validate_pdf_config(settings.get("pdf", {}))
    except Exception as err:
        report.error(f"PDF-Konfiguration ist ungueltig: {err}")


def _check_design_settings(report: CheckReport, settings: dict) -> None:
    """Prueft die konfigurierten Designfarben."""
    try:
        validate_design_config(settings.get("design", {}))
    except Exception as err:
        report.error(f"Design-Konfiguration ist ungueltig: {err}")


def _check_branding_settings(report: CheckReport, settings: dict) -> None:
    """Prueft Branding-Konfiguration und konfigurierte Logo-Dateien."""
    try:
        branding = validate_branding_config(settings.get("branding", {}))
        paths = create_paths(settings, PROJECT_ROOT)
    except Exception as err:
        report.error(f"Branding-Konfiguration ist ungueltig: {err}")
        return
    for name, label in (("pdf_logo", "PDF-Logo"), ("mail_logo", "Mail-Logo")):
        if branding[name] is None:
            continue
        try:
            check_readable_file(resolve_logo_path(paths.img_dir, branding[name]), label)
        except ValueError as err:
            report.warning(str(err))


def _check_env(report: CheckReport, settings: dict | None = None) -> None:
    """Prueft die lokale .env-Datei ohne Werte auszugeben."""
    env_path = PROJECT_ROOT / ".env"
    if not env_path.exists():
        report.error(".env fehlt.")
        return
    values = dotenv_values(env_path)
    for key in REQUIRED_ENV_KEYS:
        if not values.get(key):
            report.error(f".env: {key} fehlt oder ist leer.")
    try:
        load_mail_environment(env_path, (settings or {}).get("mail", {}))
    except Exception as err:
        report.error(f"Mail-Konfiguration ist ungueltig: {err}")


def _check_weasyprint(report: CheckReport) -> None:
    """Prueft, ob WeasyPrint importierbar ist."""
    if importlib.util.find_spec("weasyprint") is None:
        report.error("WeasyPrint ist nicht installiert oder nicht importierbar.")


def _check_configuration(
    report: CheckReport, settings: dict | None = None
) -> dict | None:
    """Prueft die eigene YAML-Rechnungskonfiguration."""
    try:
        paths = create_paths(settings or {}, PROJECT_ROOT)
        return load_invoice_config(paths.invoice_config)
    except Exception as err:
        report.error(f"config/invoice.yaml ist ungueltig: {err}")
        return None


def _check_customers(report: CheckReport, settings: dict | None = None) -> list | None:
    """Prueft alle einzelnen YAML-Kundendateien ohne Werte auszugeben."""
    try:
        paths = create_paths(settings or {}, PROJECT_ROOT)
        customers = load_customer_files(paths.customers_dir)
        if not customers:
            report.warning("Keine Kundendateien im Verzeichnis customers gefunden.")
        return customers
    except Exception as err:
        report.error(f"Kundendateien sind ungueltig: {err}")
        return None


def _check_hours_files(report: CheckReport, settings: dict) -> None:
    """Validiert vorhandene Stunden-YAMLs und meldet alte JSON-Quellen."""
    try:
        hours_dir = create_paths(settings, PROJECT_ROOT).hours_dir
    except ValueError:
        return
    if not hours_dir.is_dir():
        return

    for file_path in sorted(hours_dir.glob("*.yaml")):
        try:
            load_hours_month(file_path, file_path.stem)
        except ValueError as err:
            report.error(str(err))
    for file_path in sorted(hours_dir.glob("*.yml")):
        report.error(
            f"Stundendatei '{file_path.name}' muss die Endung .yaml verwenden."
        )
    unmigrated_legacy_files = []
    for legacy_file in hours_dir.glob("stunden_*.json"):
        match = re.fullmatch(r"stunden_(\d{4})_(\d{2})\.json", legacy_file.name)
        if (
            match
            and not (hours_dir / f"{match.group(1)}-{match.group(2)}.yaml").exists()
        ):
            unmigrated_legacy_files.append(legacy_file)
    if unmigrated_legacy_files:
        report.warning(
            "Noch nicht migrierte Stunden-JSONs gefunden. Migration mit "
            "tools/migrate_legacy_hours.py pruefen."
        )


def _check_paths(report: CheckReport, settings: dict, data: list | None) -> None:
    """Prueft zentrale Lese- und Schreibpfade mit echten Schreibproben."""
    try:
        paths = create_paths(settings, PROJECT_ROOT)
    except ValueError as err:
        report.error(f"Pfadkonfiguration ist ungueltig: {err}")
        return

    checks = (
        (check_readable_file, PROJECT_ROOT / ".env", ".env"),
        (check_readable_directory, paths.data_dir, "Datenverzeichnis"),
        (check_readable_directory, paths.customers_dir, "Kundenverzeichnis"),
        (check_readable_file, paths.invoice_config, "config/invoice.yaml"),
        (check_readable_directory, paths.templates_dir, "Template-Verzeichnis"),
        (
            check_readable_file,
            paths.templates_dir / "email_template.html",
            "Mailvorlage",
        ),
        (
            check_readable_file,
            paths.templates_dir / "invoice_template.html",
            "Rechnungsvorlage",
        ),
    )
    for check, path, label in checks:
        _report_path_error(report, check, path, label)
    writable_targets = [(paths.data_dir, "Datenverzeichnis")]
    try:
        backup_config = validate_backup_config(settings.get("backup", {}))
    except ValueError:
        backup_config = {"enabled": False}
    if backup_config["enabled"]:
        writable_targets.append((paths.backup_dir, "Backupverzeichnis"))
    for path, label in writable_targets:
        _report_path_error(report, check_writable_target_directory, path, label)

    logging_config = settings.get("logging", {})
    if isinstance(logging_config, dict) and logging_config.get("enabled", True):
        log_dir = Path(logging_config.get("directory", "logs"))
        if not log_dir.is_absolute():
            log_dir = PROJECT_ROOT / log_dir
        _report_path_error(
            report, check_writable_target_directory, log_dir, "Logverzeichnis"
        )

    if paths.hours_dir.exists():
        _report_path_error(
            report, check_readable_directory, paths.hours_dir, "Stundenverzeichnis"
        )
    elif _has_hourly_customers(data):
        report.error(
            "Stundenverzeichnis fehlt, obwohl Stundenkunden konfiguriert sind."
        )
    else:
        report.warning("Optionales Stundenverzeichnis fehlt.")

    for customer in data or []:
        archive_path = (
            customer.get("archive_directory") if isinstance(customer, dict) else None
        )
        if not archive_path:
            continue
        try:
            check_archive_path(archive_path, write_probe=True)
        except ValueError as err:
            report.error(f"Kunde {customer.get('id', 'unbekannt')}: {err}")


def _report_path_error(report: CheckReport, check, path: Path, label: str) -> None:
    """Fuehrt eine Pfadpruefung aus und uebernimmt Fehler in den Bericht."""
    try:
        check(path, label)
    except ValueError as err:
        report.error(str(err))


def _has_hourly_customers(data: list | None) -> bool:
    """Prueft, ob mindestens ein aktiver Stundenkunde konfiguriert ist."""
    return any(
        isinstance(customer, dict)
        and customer.get("active") is not False
        and isinstance(customer.get("main_service"), dict)
        and str(customer["main_service"].get("unit", "")).lower() == "hour"
        for customer in (data or [])
    )


if __name__ == "__main__":
    raise SystemExit(main())
