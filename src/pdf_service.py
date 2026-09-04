import logging
import os
import tempfile
from pathlib import Path

PDF_ENGINE = "weasyprint"
logger = logging.getLogger(__name__)


def validate_pdf_config(pdf_config: dict) -> dict:
    """Prueft die PDF-Konfiguration und setzt Defaults."""
    if not isinstance(pdf_config, dict):
        raise ValueError("Der YAML-Bereich 'pdf' muss eine Map sein.")

    engine = pdf_config.get("engine", PDF_ENGINE)
    if engine != PDF_ENGINE:
        raise ValueError("Als PDF-Engine wird nur noch 'weasyprint' unterstuetzt.")

    return {"engine": engine}


def generate_pdf_bytes(pdf_html: str, pdf_config: dict) -> bytes:
    """Erzeugt PDF-Bytes mit der konfigurierten PDF-Engine."""
    validate_pdf_config(pdf_config)
    return _generate_with_weasyprint(pdf_html)


def _generate_with_weasyprint(pdf_html: str) -> bytes:
    """Erzeugt PDF-Bytes mit WeasyPrint."""
    try:
        from weasyprint import HTML
    except ImportError as err:
        raise RuntimeError("PDF-Engine 'weasyprint' ist nicht installiert.") from err

    return HTML(string=pdf_html).write_pdf()


def archive_pdf(archive_directory: str, attachment_name: str, pdf_bytes: bytes) -> None:
    """Speichert eine erzeugte PDF optional im Kundenarchiv."""
    archive_path = Path(archive_directory).expanduser()
    target = archive_path / attachment_name
    archive_path.mkdir(parents=True, exist_ok=True)
    if target.exists():
        if target.read_bytes() == pdf_bytes:
            logger.info("Identische PDF ist bereits archiviert: %s", target)
            return
        raise FileExistsError(f"Archivdatei '{target}' existiert bereits.")

    temporary_path = None
    try:
        with tempfile.NamedTemporaryFile(
            "wb",
            dir=archive_path,
            prefix=f".{target.name}.",
            suffix=".tmp",
            delete=False,
        ) as temporary_file:
            temporary_path = Path(temporary_file.name)
            temporary_file.write(pdf_bytes)
            temporary_file.flush()
            os.fsync(temporary_file.fileno())
        os.link(temporary_path, target)
    finally:
        if temporary_path and temporary_path.exists():
            temporary_path.unlink()
    logger.info("PDF archiviert unter: %s", target)
