from pathlib import Path

from design import validiere_design_config
from templates import lade_templates

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"


def _template_context(website: str = "", logo_base64: str = "") -> dict:
    """Erstellt einen minimalen Kontext fuer Rendering-Tests."""
    return {
        "absender": {
            "name": "Max Mustermann",
            "firma": "Musterfirma",
            "straße": "Musterstraße 1",
            "plz": "12345",
            "ort": "Musterstadt",
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
        "finanzen": {
            "kleinunternehmer": True,
            "steuer_id_typ": "steuernummer",
            "steuernummer": "12/345/67890",
        },
        "name": "Erika Beispiel",
        "firma": "Beispielfirma",
        "email": "erika@example.com",
        "strasse": "Beispielweg 2",
        "plz": "54321",
        "ort": "Beispielstadt",
        "rechnungsnummer": "TEST-01-2026",
        "rechnungsdatum": "01.01.2026",
        "faelligkeit": "15.01.2026",
        "abrechnungszeitraum": "",
        "abrechnungszyklus": 1,
        "monat_jahr": "Januar 2026",
        "leistungen": [],
        "gesamtpreis": "100,00",
        "netto_betrag": "100,00",
        "steuerbetrag": "0,00",
        "mwst_prozent": 0,
        "mwst_hinweis": "",
        "brutto_betrag": "100,00",
        "logo_base64": logo_base64,
        "mail_logo_cid": "",
        "design": validiere_design_config({}),
        "header_title": "Max Mustermann",
        "header_subtitle": "Musterfirma",
        "pdf_logo_height": 40,
        "mail_logo_height": 60,
    }


def test_templates_hide_empty_optional_website_and_logo():
    """Leere optionale Angaben erzeugen keine sichtbaren Platzhalter."""
    templates = lade_templates(TEMPLATES_DIR)
    context = _template_context()

    rechnung_html = templates.rechnung.render(context)
    mail_html = templates.mail.render(context)

    assert "Internet:" not in rechnung_html
    assert '<img src=""' not in rechnung_html
    assert '<div class="watermark">' not in rechnung_html
    assert "🌐" not in mail_html
    assert 'href=""' not in mail_html
    assert "nicht zur Zahlung bestimmt" not in mail_html


def test_templates_render_available_website_and_logo():
    """Vorhandene optionale Angaben bleiben in den Vorlagen sichtbar."""
    templates = lade_templates(TEMPLATES_DIR)
    context = _template_context(
        website="https://example.com",
        logo_base64="data:image/png;base64,dGVzdA==",
    )

    rechnung_html = templates.rechnung.render(context)
    mail_html = templates.mail.render(context)

    assert "Internet: https://example.com" in rechnung_html
    assert 'src="data:image/png;base64,dGVzdA=="' in rechnung_html
    assert 'href="https://example.com"' in mail_html


def test_mail_template_renders_configured_cid_logo():
    """Ein konfiguriertes Mail-Logo wird als CID-Bild im Kopf angezeigt."""
    templates = lade_templates(TEMPLATES_DIR)
    context = _template_context()
    context["mail_logo_cid"] = "rechnung-logo"

    mail_html = templates.mail.render(context)

    assert 'src="cid:rechnung-logo"' in mail_html
    assert "max-height: 60px" in mail_html


def test_templates_render_independent_branding_header_texts():
    """Eigene Headertexte aendern nur die Branding-Koepfe der Vorlagen."""
    templates = lade_templates(TEMPLATES_DIR)
    context = _template_context()
    context["header_title"] = "Musteragentur"
    context["header_subtitle"] = "Design und Beratung"

    rechnung_html = templates.rechnung.render(context)
    mail_html = templates.mail.render(context)

    assert "Musteragentur" in rechnung_html
    assert "Design und Beratung" in rechnung_html
    assert "Musteragentur" in mail_html
    assert "Design und Beratung" in mail_html


def test_templates_render_sample_notice_and_pdf_watermark():
    """Musterrechnungen sind in Mail und PDF eindeutig gekennzeichnet."""
    templates = lade_templates(TEMPLATES_DIR)
    context = _template_context()
    context["muster_text"] = "MUSTER"

    rechnung_html = templates.rechnung.render(context)
    mail_html = templates.mail.render(context)

    assert '<div class="watermark">MUSTER</div>' in rechnung_html
    assert "nicht zur Zahlung bestimmt" in mail_html


def test_templates_render_configured_accent_colors():
    """PDF und Rechnungsmail verwenden die konfigurierten Akzentfarben."""
    templates = lade_templates(TEMPLATES_DIR)
    context = _template_context()
    context["design"] = validiere_design_config(
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

    rechnung_html = templates.rechnung.render(context)
    mail_html = templates.mail.render(context)

    for farbe in ("#112233", "#445566", "#778899"):
        assert farbe in rechnung_html
    for farbe in ("#abcdef", "#fedcba"):
        assert farbe in mail_html
    assert "background-color: #abcdef" in mail_html
