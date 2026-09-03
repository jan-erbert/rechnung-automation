from branding import validiere_branding_config
from design import validiere_design_config
from pdf import validiere_pdf_config
from pfadpruefung import pruefe_lesbare_datei, pruefe_lesbares_verzeichnis


def pruefe_startvoraussetzungen(
    settings: dict,
    pfade,
    daten: list,
    mail_config: dict,
) -> None:
    """Prueft die wichtigsten Voraussetzungen vor einem Rechnungslauf."""
    validiere_pdf_config(settings.get("pdf", {}))
    validiere_design_config(settings.get("design", {}))
    validiere_branding_config(settings.get("branding", {}))
    _pruefe_mail_config(mail_config)
    if not isinstance(daten, list):
        raise ValueError("Kundendaten muessen als Liste geladen werden.")

    pruefe_lesbare_datei(
        pfade.base_dir / "config" / "settings.yaml",
        "config/settings.yaml",
    )
    pruefe_lesbare_datei(pfade.base_dir / ".env", ".env")
    pruefe_lesbares_verzeichnis(pfade.customers_dir, "Kundenverzeichnis")
    pruefe_lesbare_datei(pfade.invoice_config, "config/invoice.yaml")
    pruefe_lesbares_verzeichnis(pfade.templates_dir, "Template-Verzeichnis")
    pruefe_lesbare_datei(
        pfade.templates_dir / "mail_template.html",
        "Mailvorlage",
    )
    pruefe_lesbare_datei(
        pfade.templates_dir / "rechnung_template.html",
        "Rechnungsvorlage",
    )


def _pruefe_mail_config(mail_config: dict) -> None:
    """Prueft die bereits geladene Mail-Konfiguration."""
    if not isinstance(mail_config, dict):
        raise ValueError("Mail-Konfiguration muss eine Map sein.")
    for key in ("server", "port", "user", "passwort"):
        if mail_config.get(key) in (None, ""):
            raise ValueError(f"Mail-Konfiguration: {key} fehlt.")
