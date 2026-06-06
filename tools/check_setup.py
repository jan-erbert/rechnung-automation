import importlib.util
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from pdf import validiere_pdf_config  # noqa: E402
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
    _check_env(report)
    _check_templates(report)
    _check_weasyprint(report)
    _check_konfiguration(report)
    _check_daten(report)

    if settings:
        _check_pdf_settings(report, settings)

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

    env_values = _read_env_keys(env_path)
    for key in REQUIRED_ENV_KEYS:
        if not env_values.get(key):
            report.error(f".env: {key} fehlt oder ist leer.")

    port_value = env_values.get("MAIL_PORT")
    if port_value:
        try:
            int(port_value)
        except ValueError:
            report.error(".env: MAIL_PORT muss eine ganze Zahl sein.")


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


def _check_templates(report: CheckReport) -> None:
    """Prueft die erwarteten Template-Dateien."""
    for rel_path in (
        "vorlagen/mail_template.html",
        "vorlagen/rechnung_template.html",
    ):
        if not (PROJECT_ROOT / rel_path).exists():
            report.error(f"{rel_path} fehlt.")


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


def _check_daten(report: CheckReport) -> None:
    """Prueft die Kundendaten strukturell ohne Werte auszugeben."""
    daten_path = PROJECT_ROOT / "data" / "daten.json"
    daten = _load_json(daten_path, report, "data/daten.json")
    if daten is None:
        return

    if not isinstance(daten, list):
        report.error("data/daten.json muss eine JSON-Liste sein.")
        return

    for index, kunde in enumerate(daten, start=1):
        if not isinstance(kunde, dict):
            report.error(f"data/daten.json: Eintrag #{index} muss ein Objekt sein.")
            continue
        _check_kundeneintrag(report, kunde, index)


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

    archiv_pfad = kunde.get("archiv_pfad")
    if archiv_pfad and not Path(archiv_pfad).exists():
        report.warning(
            f"data/daten.json: Eintrag #{index}: Archivpfad existiert noch nicht."
        )


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


if __name__ == "__main__":
    raise SystemExit(main())
