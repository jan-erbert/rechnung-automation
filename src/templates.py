import base64
import logging
from dataclasses import dataclass
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RechnungsTemplates:
    """Buendelt die geladenen Mail- und Rechnungstemplates."""

    mail: object
    rechnung: object


def lade_templates(vorlagen_dir: Path) -> RechnungsTemplates:
    """Laedt die HTML-Templates fuer Mail und Rechnung."""
    env = Environment(loader=FileSystemLoader(vorlagen_dir))
    return RechnungsTemplates(
        mail=env.get_template("mail_template.html"),
        rechnung=env.get_template("rechnung_template.html"),
    )


def lade_logo_base64(img_dir: Path) -> str:
    """Laedt das optionale Logo als Base64-Data-URI."""
    try:
        with open(img_dir / "logo.png", "rb") as img_file:
            logo_base64 = base64.b64encode(img_file.read()).decode("utf-8")
    except FileNotFoundError:
        logger.warning(
            "Logo-Datei nicht gefunden. Logo wird in der Rechnung nicht angezeigt."
        )
        return ""

    return f"data:image/png;base64,{logo_base64}"


def baue_template_context(
    eintrag: dict,
    absender: dict,
    bank: dict,
    finanzen: dict,
    leistungs_liste: list,
    rechnungsnummer: str,
    rechnungsdatum: str,
    faelligkeit_datum: str,
    abrechnungszeitraum: str,
    monat_jahr: str,
    abrechnungszyklus: int,
    gesamtpreis: float,
    gesamtpreis_str: str,
    gesamtpreis_mit_mwst: float,
    steuerbetrag: float,
    mwst_hinweis: str,
    logo_base64: str,
    stundeninfo: dict | None = None,
) -> dict:
    """Baut den gemeinsamen Kontext fuer Mail- und PDF-Templates."""
    context = {
        "name": eintrag["name"],
        "firma": eintrag["firma"],
        "email": eintrag["email"],
        "strasse": eintrag["strasse"],
        "betrag": f"{gesamtpreis:.2f}".replace(".", ","),
        "plz": eintrag["plz"],
        "ort": eintrag["ort"],
        "rechnungsnummer": rechnungsnummer,
        "rechnungsdatum": rechnungsdatum,
        "faelligkeit": faelligkeit_datum,
        "abrechnungszeitraum": abrechnungszeitraum if abrechnungszeitraum else "",
        "monat_jahr": monat_jahr,
        "leistungen": leistungs_liste,
        "gesamtpreis": gesamtpreis_str,
        "logo_base64": logo_base64,
        "abrechnungszyklus": abrechnungszyklus,
        "absender": absender,
        "bank": bank,
        "finanzen": finanzen,
        "mwst_hinweis": mwst_hinweis,
        "steuerbetrag": f"{steuerbetrag:.2f}".replace(".", ","),
        "mwst_prozent": finanzen.get("mehrwertsteuer_prozent", 0),
        "brutto_betrag": f"{gesamtpreis_mit_mwst:.2f}".replace(".", ","),
        "netto_betrag": f"{gesamtpreis:.2f}".replace(".", ","),
    }

    if stundeninfo:
        context["stundensatz_hinweis"] = (
            f"(Stundensatz: {stundeninfo['stundensatz']:.2f} EUR pro Stunde)"
        )

    return context
