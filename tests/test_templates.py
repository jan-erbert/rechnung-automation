from pathlib import Path

from templates import lade_logo_base64, lade_templates

VORLAGEN_DIR = Path(__file__).resolve().parent.parent / "vorlagen"


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
    }


def test_lade_logo_base64_returns_empty_string_without_logo(tmp_path):
    """Ein fehlendes Logo liefert keine leere Data-URI."""
    assert lade_logo_base64(tmp_path) == ""


def test_templates_hide_empty_optional_website_and_logo():
    """Leere optionale Angaben erzeugen keine sichtbaren Platzhalter."""
    templates = lade_templates(VORLAGEN_DIR)
    context = _template_context()

    rechnung_html = templates.rechnung.render(context)
    mail_html = templates.mail.render(context)

    assert "Internet:" not in rechnung_html
    assert '<img src=""' not in rechnung_html
    assert "🌐" not in mail_html
    assert 'href=""' not in mail_html


def test_templates_render_available_website_and_logo():
    """Vorhandene optionale Angaben bleiben in den Vorlagen sichtbar."""
    templates = lade_templates(VORLAGEN_DIR)
    context = _template_context(
        website="https://example.com",
        logo_base64="data:image/png;base64,dGVzdA==",
    )

    rechnung_html = templates.rechnung.render(context)
    mail_html = templates.mail.render(context)

    assert "Internet: https://example.com" in rechnung_html
    assert 'src="data:image/png;base64,dGVzdA=="' in rechnung_html
    assert 'href="https://example.com"' in mail_html
