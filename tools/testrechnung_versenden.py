import logging
import sys
from datetime import datetime, timedelta
from decimal import Decimal
from email.utils import parseaddr
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from branding import LogoAsset, lade_logo_asset, validiere_branding_config  # noqa: E402
from design import validiere_design_config  # noqa: E402
from konfiguration import lade_konfiguration, lade_mail_umgebung  # noqa: E402
from logging_setup import konfiguriere_logging  # noqa: E402
from mail import baue_rechnungsmail, sende_mail  # noqa: E402
from paths import erstelle_pfade  # noqa: E402
from pdf import erzeuge_pdf_bytes, validiere_pdf_config  # noqa: E402
from rechnungen import berechne_steuerwerte  # noqa: E402
from settings_loader import lade_settings  # noqa: E402
from templates import baue_template_context, lade_templates  # noqa: E402
from zeit import formatiere_monat_jahr, jetzt  # noqa: E402

logger = logging.getLogger(__name__)

MUSTERARTEN = {
    "1": "monat",
    "monat": "monat",
    "2": "pauschal",
    "pauschal": "pauschal",
    "3": "stunden",
    "stunden": "stunden",
}


def main() -> None:
    """Erzeugt und versendet eine deutlich markierte Musterrechnung."""
    settings = lade_settings()
    pfade = erstelle_pfade(settings)
    konfiguriere_logging(settings.get("logging", {}), pfade.base_dir)
    konfig = lade_konfiguration(pfade.invoice_config)
    mail_config = lade_mail_umgebung(pfade.base_dir / ".env", settings.get("mail", {}))
    pdf_config = validiere_pdf_config(settings.get("pdf", {}))
    design = validiere_design_config(settings.get("design", {}))
    branding = validiere_branding_config(settings.get("branding", {}))
    templates = lade_templates(pfade.templates_dir)

    standard_empfaenger = konfig.get("mail", {}).get("bcc")
    if not standard_empfaenger:
        raise ValueError(
            "Testrechnung nicht moeglich: In config/invoice.yaml fehlt mail.bcc."
        )

    empfaenger = frage_empfaenger(standard_empfaenger[0])
    musterart = frage_musterart()
    context, mail_logo = baue_muster_context(
        musterart,
        konfig,
        design,
        branding,
        pfade.img_dir,
    )

    mail_html = templates.mail.render(context)
    pdf_html = templates.rechnung.render(context)
    pdf_bytes = erzeuge_pdf_bytes(pdf_html, pdf_config)
    msg = baue_rechnungsmail(
        mail_user=mail_config["user"],
        empfaenger=empfaenger,
        betreff=f"[MUSTER] Testrechnung {musterart.capitalize()}",
        mail_html=mail_html,
        pdf_bytes=pdf_bytes,
        anhang_name=f"MUSTER_Testrechnung_{musterart}.pdf",
        mail_logo=mail_logo,
        from_name=konfig.get("mail", {}).get("from_name"),
    )

    logger.info("Versende Musterrechnung der Art '%s'.", musterart)
    sende_mail(
        mail_config["server"],
        mail_config["port"],
        mail_config["user"],
        mail_config["passwort"],
        msg,
        [empfaenger],
        security=mail_config.get("security", "starttls"),
        timeout=mail_config.get("timeout", 30),
    )
    logger.info("Musterrechnung wurde erfolgreich versendet.")


def frage_empfaenger(standard_empfaenger: str) -> str:
    """Fragt den Empfaenger ab und verwendet standardmaessig die BCC-Adresse."""
    while True:
        eingabe = input(
            f"Empfaenger der Musterrechnung [{standard_empfaenger}]: "
        ).strip()
        empfaenger = eingabe or standard_empfaenger
        if _ist_gueltige_mailadresse(empfaenger):
            return empfaenger
        print("Ungueltige E-Mail-Adresse. Bitte erneut eingeben.")


def frage_musterart() -> str:
    """Fragt nach einem Monats-, Pauschal- oder Stundenmuster."""
    while True:
        eingabe = input(
            "Musterart waehlen: [1] Monat, [2] Pauschal, [3] Stunden: "
        ).strip()
        musterart = MUSTERARTEN.get(eingabe.lower())
        if musterart:
            return musterart
        print("Ungueltige Auswahl. Bitte 1, 2 oder 3 eingeben.")


def baue_muster_context(
    musterart: str,
    konfig: dict,
    design: dict,
    branding: dict,
    image_dir: Path,
    zeitpunkt: datetime | None = None,
) -> tuple[dict, LogoAsset | None]:
    """Baut den Template-Kontext fuer eine synthetische Musterrechnung."""
    zeitpunkt = zeitpunkt or jetzt()
    leistungsdaten = baue_muster_leistungsdaten(musterart)
    steuerdaten = berechne_steuerwerte(
        leistungsdaten["gesamtpreis"], konfig["finanzen"]
    )
    pdf_logo = lade_logo_asset(image_dir, branding["pdf_logo"], "PDF-Logo")
    mail_logo = lade_logo_asset(image_dir, branding["mail_logo"], "Mail-Logo")

    context = baue_template_context(
        eintrag={
            "name": "Erika Beispiel",
            "firma": "Beispielfirma GmbH",
            "email": "muster@example.com",
            "strasse": "Beispielweg 12",
            "plz": "12345",
            "ort": "Musterstadt",
        },
        absender=konfig["absender"],
        bank=konfig["bank"],
        finanzen=konfig["finanzen"],
        leistungs_liste=leistungsdaten["leistungen"],
        rechnungsnummer=f"MUSTER-{zeitpunkt:%m-%Y}",
        rechnungsdatum=zeitpunkt.strftime("%d.%m.%Y"),
        faelligkeit_datum=(zeitpunkt + timedelta(days=14)).strftime("%d.%m.%Y"),
        abrechnungszeitraum=formatiere_monat_jahr(zeitpunkt),
        monat_jahr=formatiere_monat_jahr(zeitpunkt),
        abrechnungszyklus=1,
        gesamtpreis=leistungsdaten["gesamtpreis"],
        gesamtpreis_str=steuerdaten["gesamtpreis_str"],
        gesamtpreis_mit_mwst=steuerdaten["gesamtpreis_mit_mwst"],
        steuerbetrag=steuerdaten["steuerbetrag"],
        mwst_hinweis=steuerdaten["mwst_hinweis"],
        logo_base64=pdf_logo.data_uri if pdf_logo else "",
        mail_logo_cid="rechnung-logo" if mail_logo else "",
        design=design,
        branding=branding,
        stundeninfo=leistungsdaten["stundeninfo"],
        muster_text="MUSTER",
    )
    return context, mail_logo


def baue_muster_leistungsdaten(musterart: str) -> dict:
    """Erstellt feste, synthetische Leistungsdaten fuer die Musterarten."""
    if musterart == "monat":
        return {
            "leistungen": [
                {
                    "beschreibung": "Monatliche Musterleistung fuer 1 Monat",
                    "preis": "89,00 EUR",
                }
            ],
            "gesamtpreis": Decimal("89.00"),
            "stundeninfo": None,
        }
    if musterart == "pauschal":
        return {
            "leistungen": [
                {
                    "beschreibung": "Einmalige Musterleistung (pauschal)",
                    "preis": "450,00 EUR",
                }
            ],
            "gesamtpreis": Decimal("450.00"),
            "stundeninfo": None,
        }
    if musterart == "stunden":
        return {
            "leistungen": [
                {
                    "beschreibung": "6.5 Stunden x 75.00 EUR",
                    "preis": "487,50 EUR",
                }
            ],
            "gesamtpreis": Decimal("487.50"),
            "stundeninfo": {
                "stunden": Decimal("6.5"),
                "stundensatz": Decimal("75.00"),
            },
        }
    raise ValueError("Unbekannte Musterart.")


def _ist_gueltige_mailadresse(wert: str) -> bool:
    """Prueft eine einzelne einfache Empfaengeradresse."""
    name, adresse = parseaddr(wert)
    domain = adresse.rsplit("@", 1)[-1]
    return not name and adresse == wert and "@" in adresse and "." in domain


if __name__ == "__main__":
    main()
