import pytest

from pdf import validiere_pdf_config


def test_validiere_pdf_config_accepts_weasyprint():
    """WeasyPrint ist die einzige gueltige PDF-Engine."""
    assert validiere_pdf_config({"engine": "weasyprint"}) == {"engine": "weasyprint"}


def test_validiere_pdf_config_rejects_unknown_engine():
    """Andere PDF-Engines werden bewusst abgelehnt."""
    with pytest.raises(ValueError):
        validiere_pdf_config({"engine": "wkhtmltopdf"})
