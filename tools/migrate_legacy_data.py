import argparse
import json
import sys
from pathlib import Path

import yaml

BASE_DIR = Path(__file__).resolve().parent.parent
SRC_DIR = BASE_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from configuration import load_invoice_config  # noqa: E402
from customer_files import (  # noqa: E402
    customer_to_yaml,
    load_customer_files,
    save_customer_file,
)
from legacy_migration import (  # noqa: E402
    convert_legacy_customers,
    convert_legacy_invoice_config,
)
from strict_yaml import load_yaml  # noqa: E402


def parse_args() -> argparse.Namespace:
    """Liest Pfade und explizite Aktionsschalter der Migration."""
    parser = argparse.ArgumentParser(
        description="Migriert alte JSON-Konfigurationen kontrolliert nach YAML."
    )
    parser.add_argument("--apply", action="store_true", help="Schreibt YAML-Dateien.")
    parser.add_argument(
        "--verify", action="store_true", help="Prueft vorhandene YAML-Dateien."
    )
    parser.add_argument(
        "--delete-legacy",
        action="store_true",
        help="Loescht JSON-Quellen erst nach erfolgreicher Pruefung.",
    )
    parser.add_argument(
        "--data-json", type=Path, default=BASE_DIR / "data" / "daten.json"
    )
    parser.add_argument(
        "--config-json",
        type=Path,
        default=BASE_DIR / "data" / "konfiguration.json",
    )
    parser.add_argument("--customers-dir", type=Path, default=BASE_DIR / "customers")
    parser.add_argument(
        "--invoice-yaml", type=Path, default=BASE_DIR / "config" / "invoice.yaml"
    )
    return parser.parse_args()


def load_json(path: Path, expected_type: type):
    """Laedt eine Legacy-JSON-Datei mit Typpruefung."""
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, expected_type):
        raise ValueError(f"{path} hat nicht den erwarteten Datentyp.")
    return value


def verify_migration(
    customers: list[dict],
    invoice_config: dict,
    customers_dir: Path,
    invoice_yaml: Path,
) -> None:
    """Vergleicht Migrationsergebnisse mit den JSON-Quellen."""
    if load_yaml(invoice_yaml) != invoice_config:
        raise ValueError(f"{invoice_yaml} weicht von der JSON-Quelle ab.")
    for customer in customers:
        path = customers_dir / f"{customer['id']}.yaml"
        if load_yaml(path) != customer_to_yaml(customer):
            raise ValueError(f"{path} weicht von der JSON-Quelle ab.")
    load_invoice_config(invoice_yaml)
    loaded = {customer["id"] for customer in load_customer_files(customers_dir)}
    if loaded != {customer["id"] for customer in customers}:
        raise ValueError("Geladene Kunden weichen von der JSON-Quelle ab.")


def delete_json_sources(data_json: Path, config_json: Path) -> None:
    """Loescht exakt die beiden verifizierten JSON-Quellen."""
    if data_json.resolve() == config_json.resolve():
        raise ValueError("Die beiden JSON-Quellpfade muessen verschieden sein.")
    if not data_json.is_file() or not config_json.is_file():
        raise FileNotFoundError("Mindestens eine JSON-Quelldatei fehlt.")
    data_json.unlink()
    config_json.unlink()


def main() -> int:
    """Migriert, prueft und loescht optional alte JSON-Konfigurationen."""
    args = parse_args()
    customers = convert_legacy_customers(load_json(args.data_json, list))
    invoice_config = convert_legacy_invoice_config(load_json(args.config_json, dict))
    if args.apply:
        if args.invoice_yaml.exists() or any(args.customers_dir.glob("*.y*ml")):
            raise FileExistsError(
                "Migration abgebrochen: YAML-Ziele existieren bereits."
            )
        args.customers_dir.mkdir(parents=True, exist_ok=True)
        for customer in customers:
            save_customer_file(customer, args.customers_dir / f"{customer['id']}.yaml")
        args.invoice_yaml.parent.mkdir(parents=True, exist_ok=True)
        with args.invoice_yaml.open("x", encoding="utf-8") as invoice_file:
            yaml.safe_dump(
                invoice_config, invoice_file, allow_unicode=True, sort_keys=False
            )
        print("YAML-Dateien wurden erzeugt.")
    elif not args.verify and not args.delete_legacy:
        print("Vorschau abgeschlossen. Mit --apply werden YAML-Dateien erzeugt.")
        return 0
    verify_migration(customers, invoice_config, args.customers_dir, args.invoice_yaml)
    print("Pruefung erfolgreich: Alle migrierten Daten stimmen ueberein.")
    if args.delete_legacy:
        delete_json_sources(args.data_json, args.config_json)
        print("Die alten JSON-Dateien wurden geloescht.")
    else:
        print("Die alten JSON-Dateien wurden nicht veraendert.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
