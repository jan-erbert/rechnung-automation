import pytest

from pdf_service import archive_pdf, validate_pdf_config


def test_validiere_pdf_config_accepts_weasyprint():
    """WeasyPrint ist die einzige gueltige PDF-Engine."""
    assert validate_pdf_config({"engine": "weasyprint"}) == {"engine": "weasyprint"}


def test_validiere_pdf_config_rejects_unknown_engine():
    """Andere PDF-Engines werden bewusst abgelehnt."""
    with pytest.raises(ValueError):
        validate_pdf_config({"engine": "wkhtmltopdf"})


def test_archive_does_not_overwrite_different_existing_pdf(tmp_path):
    """Eine bestehende Archiv-PDF wird niemals still ersetzt."""
    target = tmp_path / "Invoice_customer_01-2026.pdf"
    target.write_bytes(b"existing")

    with pytest.raises(FileExistsError):
        archive_pdf(str(tmp_path), target.name, b"new")

    assert target.read_bytes() == b"existing"


def test_archive_falls_back_when_hardlinks_are_unavailable(tmp_path, monkeypatch):
    """Archive auf Dateisystemen ohne Hardlinks werden trotzdem geschrieben."""
    monkeypatch.setattr(
        "pdf_service.os.link",
        lambda *args: (_ for _ in ()).throw(OSError("not supported")),
    )

    archive_pdf(str(tmp_path), "Invoice_customer_01-2026.pdf", b"pdf")

    assert (tmp_path / "Invoice_customer_01-2026.pdf").read_bytes() == b"pdf"
