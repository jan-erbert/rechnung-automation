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


def test_mail_has_left_aligned_wordmark_header_and_no_emojis():
    """Der Mailkopf zeigt nur die linke Wortmarke und keine Dokumenttitel."""
    context = _template_context()
    context.update(
        mail_header_title="Rechnung",
        mail_header_subtitle="Oktober 2026",
        mail_logo_cid="invoice-logo",
    )
    html = load_templates(TEMPLATES_DIR).email.render(context)
    header = html.split("</table>", 1)[0]
    assert "text-align: left" in header
    assert 'width="300"' in header
    assert "padding: 22px 26px" in header
    assert "<h1" not in header and "<h2" not in header
    assert "Oktober 2026" not in header
    assert "cid:invoice-document-icon" in html
    assert "<svg" not in html
    assert not any(ord(character) >= 0x1F000 for character in html)
    assert (TEMPLATES_DIR.parent / "sample/email_template.sample.html").read_text() == (
        TEMPLATES_DIR / "email_template.html"
    ).read_text()


def test_mail_icons_switch_preserves_text_and_logo():
    """Abschalten entfernt alle Symbol-CIDs, aber keine Kontaktdaten oder Logos."""
    context = _template_context()
    context.update(mail_logo_cid="invoice-logo", mail_icons_enabled=False)
    html = load_templates(TEMPLATES_DIR).email.render(context)
    assert "-icon" not in html
    assert "cid:invoice-logo" in html
    for text in (
        "Leistungsübersicht",
        "Bankverbindung",
        "Musterstraße 1",
        "max@example.com",
    ):
        assert text in html


def test_pdf_and_mail_share_configured_table_colors():
    """Dieselben Tabellenfarben erscheinen in beiden Rechnungsvorlagen."""
    context = _template_context()
    colors = {
        "header_background": "#102030",
        "total_background": "#405060",
        "border_color": "#708090",
        "header_text_color": "#A0B0C0",
        "body_text_color": "#D0E0F0",
        "row_background": "#F0E0D0",
    }
    context["design"] = validate_design_config({"tables": colors})
    context["items"] = [{"description": "Test", "price": "10,00 EUR"}]
    templates = load_templates(TEMPLATES_DIR)
    for html in (templates.invoice.render(context), templates.email.render(context)):
        assert all(value in html for value in colors.values())


def test_automation_notice_is_optional_and_does_not_change_pdf():
    """Der dezente Hinweis erscheint nur aktiviert in der Mail, nie im PDF."""
    templates = load_templates(TEMPLATES_DIR)
    context = _template_context()
    notice = "Diese E-Mail wurde automatisch erstellt und versendet."
    original_pdf = templates.invoice.render(context)
    assert notice not in templates.email.render(context)
    for enabled in (True, False):
        context["mail_automation_notice_enabled"] = enabled
        html = templates.email.render(context)
        assert (notice in html) is enabled
        assert "max@example.com" in html
        assert templates.invoice.render(context) == original_pdf


def test_pdf_uses_configured_page_and_footer_margins():
    """PDF-Inhalt und Fussbereich richten sich nach denselben Seitenraendern."""
    context = _template_context()
    context["design"] = validate_design_config(
        {"pdf_layout": {"margin_left_mm": 20, "margin_right_mm": 10}}
    )
    templates = load_templates(TEMPLATES_DIR)
    html = templates.invoice.render(context)
    assert "padding: 15mm 10mm 40mm 20mm;" in html
    assert "bottom: 15mm;" in html
    assert "left: 20mm;" in html
    assert "width: calc(100% - 30mm);" in html
