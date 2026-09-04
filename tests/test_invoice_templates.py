from pathlib import Path

from design import validate_design_config
from invoice_templates import load_templates

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"


def _template_context(website: str = "", logo_base64: str = "") -> dict:
    """Erstellt einen minimalen Kontext fuer Rendering-Tests."""
    return {
        "sender": {
            "name": "Max Mustermann",
            "company": "Musterfirma",
            "street": "Musterstraße 1",
            "postal_code": "12345",
            "city": "Musterstadt",
            "telefon": "0123 456789",
            "email": "max@example.com",
            "website": website,
        },
        "bank": {
            "kontoinhaber": "Max Mustermann",
            "bankname": "Musterbank",
            "iban": "DE00000000000000000000",
            "bic": "MUSTERBIC",
        },
        "tax": {
            "small_business": True,
            "steuer_id_typ": "steuernummer",
            "steuernummer": "12/345/67890",
        },
        "name": "Erika Beispiel",
        "company": "Beispielfirma",
        "email": "erika@example.com",
        "street": "Beispielweg 2",
        "postal_code": "54321",
        "city": "Beispielstadt",
        "invoice_number": "TEST-01-2026",
        "invoice_date": "01.01.2026",
        "due_days": "15.01.2026",
        "abrechnungszeitraum": "",
        "cycle_months": 1,
        "month_year": "Januar 2026",
        "services": [],
        "total_amount": "100,00",
        "netto_betrag": "100,00",
        "tax_amount": "0,00",
        "mwst_prozent": 0,
        "vat_note": "",
        "brutto_betrag": "100,00",
        "logo_base64": logo_base64,
        "mail_logo_cid": "",
        "design": validate_design_config({}),
        "header_title": "Max Mustermann",
        "header_subtitle": "Musterfirma",
        "pdf_logo_height": 40,
        "mail_logo_height": 60,
    }


def test_templates_hide_empty_optional_website_and_logo():
    """Leere optionale Angaben erzeugen keine sichtbaren Platzhalter."""
    templates = load_templates(TEMPLATES_DIR)
    context = _template_context()

    rechnung_html = templates.invoice.render(context)
    mail_html = templates.email.render(context)

    assert "Internet:" not in rechnung_html
    assert '<img src=""' not in rechnung_html
    assert '<div class="watermark">' not in rechnung_html
    assert "🌐" not in mail_html
    assert 'href=""' not in mail_html
    assert "nicht zur Zahlung bestimmt" not in mail_html


def test_templates_render_available_website_and_logo():
    """Vorhandene optionale Angaben bleiben in den Vorlagen sichtbar."""
    templates = load_templates(TEMPLATES_DIR)
    context = _template_context(
        website="https://example.com",
        logo_base64="data:image/png;base64,dGVzdA==",
    )

    rechnung_html = templates.invoice.render(context)
    mail_html = templates.email.render(context)

    assert "Internet: https://example.com" in rechnung_html
    assert 'src="data:image/png;base64,dGVzdA=="' in rechnung_html
    assert 'href="https://example.com"' in mail_html


def test_mail_template_renders_configured_cid_logo():
    """Ein konfiguriertes Mail-Logo wird als CID-Bild im Kopf angezeigt."""
    templates = load_templates(TEMPLATES_DIR)
    context = _template_context()
    context["mail_logo_cid"] = "invoice-logo"

    mail_html = templates.email.render(context)

    assert 'src="cid:invoice-logo"' in mail_html
    assert "max-height: 60px" in mail_html


def test_templates_render_independent_branding_header_texts():
    """Eigene Headertexte aendern nur die Branding-Koepfe der Vorlagen."""
    templates = load_templates(TEMPLATES_DIR)
    context = _template_context()
    context["header_title"] = "Musteragentur"
    context["header_subtitle"] = "Design und Beratung"

    rechnung_html = templates.invoice.render(context)
    mail_html = templates.email.render(context)

    assert "Musteragentur" in rechnung_html
    assert "Design und Beratung" in rechnung_html
    assert "Musteragentur" in mail_html
    assert "Design und Beratung" in mail_html


def test_templates_render_sample_notice_and_pdf_watermark():
    """Musterinvoices sind in Mail und PDF eindeutig gekennzeichnet."""
    templates = load_templates(TEMPLATES_DIR)
    context = _template_context()
    context["sample_text"] = "MUSTER"

    rechnung_html = templates.invoice.render(context)
    mail_html = templates.email.render(context)

    assert '<div class="watermark">MUSTER</div>' in rechnung_html
    assert "nicht zur Zahlung bestimmt" in mail_html


def test_templates_render_configured_accent_colors():
    """PDF und Rechnungsmail verwenden die konfigurierten Akzentfarben."""
    templates = load_templates(TEMPLATES_DIR)
    context = _template_context()
    context["design"] = validate_design_config(
        {
            "pdf": {
                "accent_color": "#112233",
                "accent_text_color": "#445566",
                "accent_muted_text_color": "#778899",
            },
            "mail": {
                "accent_color": "#abcdef",
                "link_color": "#fedcba",
            },
        }
    )

    rechnung_html = templates.invoice.render(context)
    mail_html = templates.email.render(context)

    for farbe in ("#112233", "#445566", "#778899"):
        assert farbe in rechnung_html
    for farbe in ("#abcdef", "#fedcba"):
        assert farbe in mail_html
    assert "background-color: #abcdef" in mail_html
