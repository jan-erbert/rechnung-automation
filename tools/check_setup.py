import importlib.util
import sys
from pathlib import Path

from dotenv import dotenv_values

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from branding import loese_logo_pfad_auf, validiere_branding_config  # noqa: E402
from design import validiere_design_config  # noqa: E402
from konfiguration import lade_konfiguration, lade_mail_umgebung  # noqa: E402
from kundendateien import lade_kundendateien  # noqa: E402
from paths import erstelle_pfade  # noqa: E402
from pdf import validiere_pdf_config  # noqa: E402
from pfadpruefung import (  # noqa: E402
    pruefe_archiv_pfad,
    pruefe_lesbare_datei,
    pruefe_lesbares_verzeichnis,
    pruefe_schreibbares_zielverzeichnis,
)
from settings_loader import lade_settings  # noqa: E402

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
    _check_konfiguration(report, settings)
    daten = _check_daten(report, settings)
    if settings:
        _check_pdf_settings(report, settings)
        _check_design_settings(report, settings)
        _check_branding_settings(report, settings)
        _check_paths(report, settings, daten)
    report.print_summary()
    return 1 if report.errors else 0


def _check_settings(report: CheckReport) -> dict | None:
    """Prueft die YAML-Einstellungen."""
    try:
        settings = lade_settings(PROJECT_ROOT / "config" / "settings.yaml")
        erstelle_pfade(settings, PROJECT_ROOT)
    except Exception as err:
        report.error(f"config/settings.yaml ist nicht gueltig: {err}")
        return None
    if not isinstance(settings.get("logging", {}), dict):
        report.error("Der YAML-Bereich 'logging' muss eine Map sein.")
    return settings


def _check_pdf_settings(report: CheckReport, settings: dict) -> None:
    """Prueft die konfigurierte PDF-Engine."""
    try:
        validiere_pdf_config(settings.get("pdf", {}))
    except Exception as err:
        report.error(f"PDF-Konfiguration ist ungueltig: {err}")


def _check_design_settings(report: CheckReport, settings: dict) -> None:
    """Prueft die konfigurierten Designfarben."""
    try:
        validiere_design_config(settings.get("design", {}))
    except Exception as err:
        report.error(f"Design-Konfiguration ist ungueltig: {err}")


def _check_branding_settings(report: CheckReport, settings: dict) -> None:
    """Prueft Branding-Konfiguration und konfigurierte Logo-Dateien."""
    try:
        branding = validiere_branding_config(settings.get("branding", {}))
        pfade = erstelle_pfade(settings, PROJECT_ROOT)
    except Exception as err:
        report.error(f"Branding-Konfiguration ist ungueltig: {err}")
        return
    for name, bezeichnung in (("pdf_logo", "PDF-Logo"), ("mail_logo", "Mail-Logo")):
        if branding[name] is None:
            continue
        try:
            pruefe_lesbare_datei(
                loese_logo_pfad_auf(pfade.img_dir, branding[name]), bezeichnung
            )
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
        lade_mail_umgebung(env_path, (settings or {}).get("mail", {}))
    except Exception as err:
        report.error(f"Mail-Konfiguration ist ungueltig: {err}")


def _check_weasyprint(report: CheckReport) -> None:
    """Prueft, ob WeasyPrint importierbar ist."""
    if importlib.util.find_spec("weasyprint") is None:
        report.error("WeasyPrint ist nicht installiert oder nicht importierbar.")


def _check_konfiguration(
    report: CheckReport, settings: dict | None = None
) -> dict | None:
    """Prueft die eigene YAML-Rechnungskonfiguration."""
    try:
        pfade = erstelle_pfade(settings or {}, PROJECT_ROOT)
        return lade_konfiguration(pfade.invoice_config)
    except Exception as err:
        report.error(f"config/invoice.yaml ist ungueltig: {err}")
        return None


def _check_daten(report: CheckReport, settings: dict | None = None) -> list | None:
    """Prueft alle einzelnen YAML-Kundendateien ohne Werte auszugeben."""
    try:
        pfade = erstelle_pfade(settings or {}, PROJECT_ROOT)
        return lade_kundendateien(pfade.customers_dir)
    except Exception as err:
        report.error(f"Kundendateien sind ungueltig: {err}")
        return None


def _check_paths(report: CheckReport, settings: dict, daten: list | None) -> None:
    """Prueft zentrale Lese- und Schreibpfade mit echten Schreibproben."""
    try:
        pfade = erstelle_pfade(settings, PROJECT_ROOT)
    except ValueError as err:
        report.error(f"Pfadkonfiguration ist ungueltig: {err}")
        return

    pruefungen = (
        (pruefe_lesbare_datei, PROJECT_ROOT / ".env", ".env"),
        (pruefe_lesbares_verzeichnis, pfade.data_dir, "Datenverzeichnis"),
        (pruefe_lesbares_verzeichnis, pfade.customers_dir, "Kundenverzeichnis"),
        (pruefe_lesbare_datei, pfade.invoice_config, "config/invoice.yaml"),
        (pruefe_lesbares_verzeichnis, pfade.templates_dir, "Template-Verzeichnis"),
        (
            pruefe_lesbare_datei,
            pfade.templates_dir / "mail_template.html",
            "Mailvorlage",
        ),
        (
            pruefe_lesbare_datei,
            pfade.templates_dir / "rechnung_template.html",
            "Rechnungsvorlage",
        ),
    )
    for pruefung, pfad, bezeichnung in pruefungen:
        _melde_pfadfehler(report, pruefung, pfad, bezeichnung)
    for pfad, bezeichnung in (
        (pfade.data_dir, "Datenverzeichnis"),
        (pfade.backup_dir, "Backupverzeichnis"),
    ):
        _melde_pfadfehler(
            report, pruefe_schreibbares_zielverzeichnis, pfad, bezeichnung
        )

    logging_config = settings.get("logging", {})
    if isinstance(logging_config, dict) and logging_config.get("enabled", True):
        log_dir = Path(logging_config.get("directory", "logs"))
        if not log_dir.is_absolute():
            log_dir = PROJECT_ROOT / log_dir
        _melde_pfadfehler(
            report, pruefe_schreibbares_zielverzeichnis, log_dir, "Logverzeichnis"
        )

    if pfade.hours_dir.exists():
        _melde_pfadfehler(
            report, pruefe_lesbares_verzeichnis, pfade.hours_dir, "Stundenverzeichnis"
        )
    elif _hat_stundenkunden(daten):
        report.error(
            "Stundenverzeichnis fehlt, obwohl Stundenkunden konfiguriert sind."
        )
    else:
        report.warning("Optionales Stundenverzeichnis fehlt.")

    for kunde in daten or []:
        archiv_pfad = kunde.get("archiv_pfad") if isinstance(kunde, dict) else None
        if not archiv_pfad:
            continue
        try:
            pruefe_archiv_pfad(archiv_pfad, schreibprobe=True)
        except ValueError as err:
            report.error(f"Kunde {kunde.get('id', 'unbekannt')}: {err}")


def _melde_pfadfehler(
    report: CheckReport, pruefung, pfad: Path, bezeichnung: str
) -> None:
    """Fuehrt eine Pfadpruefung aus und uebernimmt Fehler in den Bericht."""
    try:
        pruefung(pfad, bezeichnung)
    except ValueError as err:
        report.error(str(err))


def _hat_stundenkunden(daten: list | None) -> bool:
    """Prueft, ob mindestens ein aktiver Stundenkunde konfiguriert ist."""
    return any(
        isinstance(kunde, dict)
        and kunde.get("aktiv") is not False
        and isinstance(kunde.get("hauptleistung"), dict)
        and str(kunde["hauptleistung"].get("einheit", "")).lower() == "stunde"
        for kunde in (daten or [])
    )


if __name__ == "__main__":
    raise SystemExit(main())
