import argparse
import logging
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from branding import validate_branding_config  # noqa: E402
from configuration import load_invoice_config  # noqa: E402
from customer_files import load_customer_files  # noqa: E402
from design import validate_design_config  # noqa: E402
from file_naming import validate_file_naming_config  # noqa: E402
from invoice_preview import create_customer_invoice_preview  # noqa: E402
from invoice_templates import load_templates  # noqa: E402
from logging_setup import configure_logging  # noqa: E402
from paths import create_paths  # noqa: E402
from settings_loader import load_settings  # noqa: E402

logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    """Liest die stabile Kunden-ID fuer die Rechnungsvorschau."""
    parser = argparse.ArgumentParser(
        description=("Erzeugt eine markierte Rechnungsvorschau nur im Kunden-Archiv.")
    )
    parser.add_argument("customer_id", help="Stabile ID aus der Kunden-YAML-Datei.")
    return parser.parse_args()


def main() -> int:
    """Erzeugt eine Kunden-Vorschau mit kontrollierter Fehlerausgabe."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    try:
        args = parse_args()
        settings = load_settings()
        paths = create_paths(settings)
        configure_logging(
            settings.get("logging", {}),
            paths.base_dir,
            run_mode="preview",
        )
        customers = load_customer_files(paths.customers_dir, strict=True)
        customer = _find_customer(customers, args.customer_id)
        invoice_config = load_invoice_config(paths.invoice_config)
        preview_path = create_customer_invoice_preview(
            customer=customer,
            paths=paths,
            invoice_config=invoice_config,
            pdf_config=settings.get("pdf", {}),
            design_config=validate_design_config(settings.get("design", {})),
            branding_config=validate_branding_config(settings.get("branding", {})),
            file_naming_config=validate_file_naming_config(
                settings.get("file_naming", {})
            ),
            templates=load_templates(paths.templates_dir),
        )
        logger.info("Rechnungsvorschau gespeichert: %s", preview_path)
        logger.info(
            "Kein Versand und keine Aenderung an Rechnungsstatus oder Kundendaten."
        )
        return 0
    except (FileNotFoundError, OSError, RuntimeError, ValueError) as err:
        logger.error("Rechnungsvorschau abgebrochen: %s", err)
        return 1


def _find_customer(customers: list[dict], customer_id: str) -> dict:
    """Findet genau einen Kunden anhand seiner stabilen ID."""
    matches = [customer for customer in customers if customer.get("id") == customer_id]
    if not matches:
        raise ValueError(f"Keine Kundendatei fuer ID '{customer_id}' gefunden.")
    if len(matches) > 1:
        raise ValueError(f"Kunden-ID '{customer_id}' ist nicht eindeutig.")
    return matches[0]


if __name__ == "__main__":
    raise SystemExit(main())
