import logging
from pathlib import Path

PDF_ENGINE = "weasyprint"
logger = logging.getLogger(__name__)


def validiere_pdf_config(pdf_config: dict) -> dict:
    """Prueft die PDF-Konfiguration und setzt Defaults."""
    if not isinstance(pdf_config, dict):
        raise ValueError("Der YAML-Bereich 'pdf' muss eine Map sein.")

    engine = pdf_config.get("engine", PDF_ENGINE)
    if engine != PDF_ENGINE:
        raise ValueError("Als PDF-Engine wird nur noch 'weasyprint' unterstuetzt.")

    return {"engine": engine}


def erzeuge_pdf_bytes(pdf_html: str, pdf_config: dict) -> bytes:
    """Erzeugt PDF-Bytes mit der konfigurierten PDF-Engine."""
    validiere_pdf_config(pdf_config)
    return _erzeuge_mit_weasyprint(pdf_html)


def _erzeuge_mit_weasyprint(pdf_html: str) -> bytes:
    """Erzeugt PDF-Bytes mit WeasyPrint."""
    try:
        from weasyprint import HTML
    except ImportError as err:
        raise RuntimeError("PDF-Engine 'weasyprint' ist nicht installiert.") from err

    return HTML(string=pdf_html).write_pdf()


def archiviere_pdf(archiv_pfad: str, anhang_name: str, pdf_bytes: bytes) -> None:
    """Speichert eine erzeugte PDF optional im Kundenarchiv."""
    archiv_pfad_path = Path(archiv_pfad)
    archiv_datei = archiv_pfad_path / anhang_name
    archiv_pfad_path.mkdir(parents=True, exist_ok=True)
    with open(archiv_datei, "wb") as f:
        f.write(pdf_bytes)
    logger.info("PDF archiviert unter: %s", archiv_datei)
