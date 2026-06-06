import importlib.util
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from pdf import validiere_pdf_config  # noqa: E402
from paths import erstelle_pfade  # noqa: E402
from pfadpruefung import (  # noqa: E402
    pruefe_archiv_pfad,
    pruefe_lesbare_datei,
    pruefe_lesbares_verzeichnis,
    pruefe_schreibbares_zielverzeichnis,
)
from settings_loader import lade_settings  # noqa: E402
from validierung import (  # noqa: E402
    validiere_kundeneintrag,
    validiere_nichtnegative_ganzzahl,
    validiere_positive_ganzzahl,
)

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
    _check_env(report)
    _check_weasyprint(report)
    _check_konfiguration(report)
    daten = _check_daten(report)

    if settings:
        _check_pdf_settings(report, settings)
        _check_paths(report, settings, daten)

    report.print_summary()
    return 1 if report.errors else 0


def _check_settings(report: CheckReport) -> dict | None:
    """Prueft die YAML-Einstellungen."""
    try:
        settings = lade_settings(PROJECT_ROOT / "config" / "settings.yaml")
    except Exception as err:
        report.error(f"config/settings.yaml ist nicht gueltig: {err}")
        return None

    logging_config = settings.get("logging", {})
    if not isinstance(logging_config, dict):
        report.error("Der YAML-Bereich 'logging' muss eine Map sein.")

    return settings


def _check_pdf_settings(report: CheckReport, settings: dict) -> None:
    """Prueft die konfigurierte PDF-Engine."""
    try:
        validiere_pdf_config(settings.get("pdf", {}))
    except Exception as err:
        report.error(f"PDF-Konfiguration ist ungueltig: {err}")


def _check_env(report: CheckReport) -> None:
    """Prueft die lokale .env-Datei ohne Werte auszugeben."""
    env_path = PROJECT_ROOT / ".env"
    if not env_path.exists():
        report.error(".env fehlt.")
        return

    try:
        env_values = _read_env_keys(env_path)
    except OSError as err:
        report.error(f".env ist nicht lesbar: {err}")
        return
    for key in REQUIRED_ENV_KEYS:
        if not env_values.get(key):
            report.error(f".env: {key} fehlt oder ist leer.")

    port_value = env_values.get("MAIL_PORT")
    if port_value:
        try:
            validiere_positive_ganzzahl(port_value, "MAIL_PORT")
        except ValueError as err:
            report.error(f".env: {err}")


def _read_env_keys(env_path: Path) -> dict[str, str]:
    """Liest nur Schluessel und Rohwerte aus einer Env-Datei."""
    values = {}
    with env_path.open("r", encoding="utf-8") as env_file:
        for line in env_file:
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or "=" not in stripped:
                continue
            key, value = stripped.split("=", 1)
            values[key.strip()] = value.strip()
    return values


def _check_weasyprint(report: CheckReport) -> None:
    """Prueft, ob WeasyPrint importierbar ist."""
    if importlib.util.find_spec("weasyprint") is None:
        report.error("WeasyPrint ist nicht installiert oder nicht importierbar.")


def _check_konfiguration(report: CheckReport) -> None:
    """Prueft die eigene Rechnungskonfiguration."""
    config_path = PROJECT_ROOT / "data" / "konfiguration.json"
    config = _load_json(config_path, report, "data/konfiguration.json")
    if config is None:
        return

    if not isinstance(config, dict):
        report.error("data/konfiguration.json muss ein JSON-Objekt sein.")
        return

    _require_object_keys(
        report,
        config,
        "absender",
        ("name", "firma", "straße", "plz", "ort", "telefon", "email"),
    )
    _require_object_keys(
        report,
        config,
        "bank",
        ("bankname", "kontoinhaber", "iban", "bic"),
    )
    _require_object_keys(
        report,
        config,
        "finanzen",
        ("steuer_id_typ", "finanzamt", "kleinunternehmer"),
    )
    _check_steuer_id(report, config.get("finanzen", {}))
    finanzen = config.get("finanzen", {})
    if isinstance(finanzen, dict) and finanzen.get("kleinunternehmer") is False:
        try:
            validiere_nichtnegative_ganzzahl(
                finanzen.get("mehrwertsteuer_prozent"),
                "finanzen.mehrwertsteuer_prozent",
            )
        except ValueError as err:
            report.error(f"data/konfiguration.json: {err}")


def _check_daten(report: CheckReport) -> list | None:
    """Prueft die Kundendaten strukturell ohne Werte auszugeben."""
    daten_path = PROJECT_ROOT / "data" / "daten.json"
    daten = _load_json(daten_path, report, "data/daten.json")
    if daten is None:
        return None

    if not isinstance(daten, list):
        report.error("data/daten.json muss eine JSON-Liste sein.")
        return None

    for index, kunde in enumerate(daten, start=1):
        if not isinstance(kunde, dict):
            report.error(f"data/daten.json: Eintrag #{index} muss ein Objekt sein.")
            continue
        _check_kundeneintrag(report, kunde, index)
    return daten


def _check_kundeneintrag(report: CheckReport, kunde: dict, index: int) -> None:
    """Prueft einen Kundeneintrag ohne Kundendaten auszugeben."""
    for key in ("name", "firma", "email", "strasse", "plz", "ort"):
        if not kunde.get(key):
            report.error(f"data/daten.json: Eintrag #{index}: {key} fehlt.")

    hauptleistung = kunde.get("hauptleistung")
    if not isinstance(hauptleistung, dict):
        report.error(
            f"data/daten.json: Eintrag #{index}: hauptleistung fehlt oder ist ungueltig."
        )
    else:
        for key in ("beschreibung", "einheit", "betrag"):
            if not hauptleistung.get(key):
                report.error(
                    f"data/daten.json: Eintrag #{index}: hauptleistung.{key} fehlt."
                )

    try:
        validiere_kundeneintrag(kunde)
    except ValueError as err:
        report.error(f"data/daten.json: Eintrag #{index}: {err}")


def _check_steuer_id(report: CheckReport, finanzen: dict) -> None:
    """Prueft die ausgewaehlte steuerliche Identifikationsnummer."""
    steuer_id_typ = finanzen.get("steuer_id_typ")
    if steuer_id_typ not in ("steuernummer", "ust_id"):
        report.error(
            "data/konfiguration.json: finanzen.steuer_id_typ muss "
            "'steuernummer' oder 'ust_id' sein."
        )
        return

    if not finanzen.get(steuer_id_typ):
        report.error(f"data/konfiguration.json: finanzen.{steuer_id_typ} fehlt.")


def _load_json(path: Path, report: CheckReport, label: str):
    """Laedt JSON-Dateien fuer die Setup-Pruefung."""
    if not path.exists():
        report.error(f"{label} fehlt.")
        return None

    try:
        with path.open("r", encoding="utf-8") as json_file:
            return json.load(json_file)
    except json.JSONDecodeError as err:
        report.error(f"{label} ist kein gueltiges JSON: {err}")
        return None
    except OSError as err:
        report.error(f"{label} ist nicht lesbar: {err}")
        return None


def _require_object_keys(
    report: CheckReport,
    parent: dict,
    section: str,
    keys: tuple[str, ...],
) -> None:
    """Prueft Pflichtfelder in einem JSON-Objektabschnitt."""
    value = parent.get(section)
    if not isinstance(value, dict):
        report.error(f"data/konfiguration.json: {section} fehlt oder ist ungueltig.")
        return

    for key in keys:
        if value.get(key) in (None, ""):
            report.error(f"data/konfiguration.json: {section}.{key} fehlt.")


def _check_paths(report: CheckReport, settings: dict, daten: list | None) -> None:
    """Prueft zentrale Lese- und Schreibpfade mit echten Schreibproben."""
    try:
        pfade = erstelle_pfade(settings, PROJECT_ROOT)
    except Exception as err:
        report.error(f"Pfadkonfiguration ist ungueltig: {err}")
        return

    lese_pruefungen = (
        (pruefe_lesbare_datei, PROJECT_ROOT / ".env", ".env"),
        (pruefe_lesbares_verzeichnis, pfade.data_dir, "Datenverzeichnis"),
        (pruefe_lesbare_datei, pfade.data_dir / "daten.json", "data/daten.json"),
        (
            pruefe_lesbare_datei,
            pfade.data_dir / "konfiguration.json",
            "data/konfiguration.json",
        ),
        (
            pruefe_lesbares_verzeichnis,
            pfade.vorlagen_dir,
            "Vorlagenverzeichnis",
        ),
        (
            pruefe_lesbare_datei,
            pfade.vorlagen_dir / "mail_template.html",
            "Mailvorlage",
        ),
        (
            pruefe_lesbare_datei,
            pfade.vorlagen_dir / "rechnung_template.html",
            "Rechnungsvorlage",
        ),
    )
    for pruefung, pfad, bezeichnung in lese_pruefungen:
        _melde_pfadfehler(report, pruefung, pfad, bezeichnung)

    for pfad, bezeichnung in (
        (pfade.data_dir, "Datenverzeichnis"),
        (pfade.backup_dir, "Backupverzeichnis"),
    ):
        _melde_pfadfehler(
            report,
            pruefe_schreibbares_zielverzeichnis,
            pfad,
            bezeichnung,
        )

    logging_config = settings.get("logging", {})
    if isinstance(logging_config, dict) and logging_config.get("enabled", True):
        try:
            log_dir = Path(logging_config.get("directory", "logs"))
        except (TypeError, ValueError) as err:
            report.error(f"Logverzeichnis ist ungueltig: {err}")
            log_dir = None
        if log_dir is not None:
            if not log_dir.is_absolute():
                log_dir = PROJECT_ROOT / log_dir
            _melde_pfadfehler(
                report,
                pruefe_schreibbares_zielverzeichnis,
                log_dir,
                "Logverzeichnis",
            )

    if pfade.stunden_dir.exists():
        _melde_pfadfehler(
            report,
            pruefe_lesbares_verzeichnis,
            pfade.stunden_dir,
            "Stundenverzeichnis",
        )
    elif _hat_stundenkunden(daten):
        report.error(
            "Stundenverzeichnis fehlt, obwohl Stundenkunden konfiguriert sind."
        )
    else:
        report.warning("Optionales Stundenverzeichnis fehlt.")

    if pfade.img_dir.exists():
        _melde_pfadfehler(
            report,
            pruefe_lesbares_verzeichnis,
            pfade.img_dir,
            "Bildverzeichnis",
        )
        logo_pfad = pfade.img_dir / "logo.png"
        if logo_pfad.exists():
            _melde_pfadfehler(report, pruefe_lesbare_datei, logo_pfad, "Logo")

    for index, kunde in enumerate(daten or [], start=1):
        archiv_pfad = kunde.get("archiv_pfad") if isinstance(kunde, dict) else None
        if not archiv_pfad:
            continue
        try:
            pruefe_archiv_pfad(archiv_pfad, schreibprobe=True)
        except ValueError as err:
            report.error(f"data/daten.json: Eintrag #{index}: {err}")


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
