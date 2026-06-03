from pathlib import Path

import pdfkit


def erzeuge_pdf_bytes(pdf_html: str, bin_dir: Path) -> bytes:
    """Erzeugt PDF-Bytes mit der bestehenden wkhtmltopdf/pdfkit-Logik."""
    config = pdfkit.configuration(wkhtmltopdf=str(bin_dir / "wkhtmltopdf.exe"))
    return pdfkit.from_string(pdf_html, False, configuration=config)


def archiviere_pdf(archiv_pfad: str, anhang_name: str, pdf_bytes: bytes) -> None:
    """Speichert eine erzeugte PDF optional im Kundenarchiv."""
    archiv_pfad_path = Path(archiv_pfad)
    archiv_datei = archiv_pfad_path / anhang_name
    archiv_pfad_path.mkdir(parents=True, exist_ok=True)
    with open(archiv_datei, "wb") as f:
        f.write(pdf_bytes)
    print(f"🗂️ Archiviert unter: {archiv_datei}")
