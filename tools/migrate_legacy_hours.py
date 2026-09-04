import argparse
import json
import re
import sys
from decimal import Decimal
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
SRC_DIR = BASE_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from customer_files import load_customer_files  # noqa: E402
from hours_files import (  # noqa: E402
    load_hours_month,
    write_hours_month,
    hours_file_path,
    validate_hours_value,
)

LEGACY_NAME_PATTERN = re.compile(r"^stunden_(\d{4})_(\d{2})\.json$")


def parse_args() -> argparse.Namespace:
    """Liest Aktionsschalter und Verzeichnisse der Stundenmigration."""
    parser = argparse.ArgumentParser(
        description="Migriert alte monatliche Stunden-JSONs kontrolliert nach YAML."
    )
    parser.add_argument("--apply", action="store_true", help="Schreibt YAML-Dateien.")
    parser.add_argument(
        "--verify",
        action="store_true",
        help="Vergleicht vorhandene YAML-Dateien mit den JSON-Quellen.",
    )
    parser.add_argument(
        "--delete-legacy",
        action="store_true",
        help="Loescht alte Stunden-JSONs erst nach erfolgreicher Pruefung.",
    )
    parser.add_argument("--hours-dir", type=Path, default=BASE_DIR / "hours")
    parser.add_argument("--customers-dir", type=Path, default=BASE_DIR / "customers")
    return parser.parse_args()


def find_legacy_files(hours_dir: Path) -> list[Path]:
    """Findet alte Stunden-JSONs mit gueltigem Monatsdateinamen."""
    return sorted(
        path
        for path in hours_dir.glob("stunden_*.json")
        if LEGACY_NAME_PATTERN.fullmatch(path.name)
    )


def create_company_index(customers: list[dict]) -> dict[str, str]:
    """Ordnet eindeutige alte Firmennamen stabilen Kunden-IDs zu."""
    index = {}
    for customer in customers:
        company = str(customer.get("company", "")).strip().casefold()
        if company in index:
            raise ValueError(
                "Stundenmigration nicht eindeutig: Mehrere Kunden verwenden "
                "denselben Firmennamen."
            )
        index[company] = customer["id"]
    return index


def convert_legacy_file(
    file_path: Path, company_index: dict[str, str]
) -> tuple[str, dict[str, Decimal]]:
    """Konvertiert eine alte Monatsdatei in Zeitraum und ID-basierte Werte."""
    match = LEGACY_NAME_PATTERN.fullmatch(file_path.name)
    if not match:
        raise ValueError(f"Unbekannter Stunden-Dateiname: {file_path.name}")
    period = f"{match.group(1)}-{match.group(2)}"
    try:
        with file_path.open("r", encoding="utf-8") as json_file:
            data = json.load(json_file)
    except (OSError, json.JSONDecodeError) as err:
        raise ValueError(
            f"{file_path.name} konnte nicht gelesen werden: {err}"
        ) from err
    if not isinstance(data, list):
        raise ValueError(f"{file_path.name} muss eine JSON-Liste enthalten.")

    hours_values = {}
    for number, entry in enumerate(data, start=1):
        if not isinstance(entry, dict):
            raise ValueError(f"{file_path.name}: Eintrag #{number} ist kein Objekt.")
        company = str(entry.get("firma", "")).strip().casefold()
        customer_id = company_index.get(company)
        if not customer_id:
            raise ValueError(
                f"{file_path.name}: Firma aus Eintrag #{number} ist keinem "
                "Kunden zugeordnet."
            )
        if customer_id in hours_values:
            raise ValueError(
                f"{file_path.name}: Kunden-ID '{customer_id}' kommt mehrfach vor."
            )
        hours_values[customer_id] = validate_hours_value(
            str(entry.get("stunden", "")),
            f"{file_path.name}, Eintrag #{number}",
        )
    return period, hours_values


def load_expected_months(
    legacy_files: list[Path], company_index: dict[str, str]
) -> dict[Path, tuple[str, dict[str, Decimal]]]:
    """Bereitet alle Quellen vor, bevor eine Zieldatei geschrieben wird."""
    return {
        file_path: convert_legacy_file(file_path, company_index)
        for file_path in legacy_files
    }


def verify_migration(
    hours_dir: Path,
    expected_months: dict[Path, tuple[str, dict[str, Decimal]]],
) -> None:
    """Vergleicht alle Stunden-YAMLs semantisch mit ihren JSON-Quellen."""
    for period, expected_values in expected_months.values():
        target = hours_dir / f"{period}.yaml"
        loaded_values = load_hours_month(target, period)
        if loaded_values != expected_values:
            raise ValueError(
                f"Pruefung fehlgeschlagen: {target.name} weicht von der JSON-Quelle ab."
            )


def main() -> int:
    """Migriert und prueft alte Stundenwerte mit expliziten Schaltern."""
    args = parse_args()
    legacy_files = find_legacy_files(args.hours_dir)
    if not legacy_files:
        print("Keine alten Stunden-JSONs gefunden.")
        return 0

    customers = load_customer_files(args.customers_dir)
    expected_months = load_expected_months(
        legacy_files,
        create_company_index(customers),
    )
    targets = [
        hours_file_path(args.hours_dir, period)
        for period, _ in expected_months.values()
    ]
    print(f"Geprueft: {len(legacy_files)} alte Stunden-Monatsdateien.")

    if args.apply:
        existing = [target for target in targets if target.exists()]
        if existing:
            raise FileExistsError(
                "Migration abgebrochen; Zieldateien existieren bereits: "
                + ", ".join(str(path) for path in existing)
            )
        for period, hours_values in expected_months.values():
            target = hours_file_path(args.hours_dir, period)
            write_hours_month(
                target,
                period,
                hours_values,
                replace_existing=False,
            )
        print("Stunden-YAMLs wurden erzeugt.")
    elif not args.verify and not args.delete_legacy:
        print("Vorschau abgeschlossen. Mit --apply werden die YAML-Dateien erzeugt.")
        return 0

    verify_migration(args.hours_dir, expected_months)
    print("Pruefung erfolgreich: Alle Stundenwerte stimmen ueberein.")
    if args.delete_legacy:
        for file_path in legacy_files:
            file_path.unlink()
        print("Die alten Stunden-JSONs wurden geloescht.")
    else:
        print("Die alten Stunden-JSONs wurden nicht veraendert.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
