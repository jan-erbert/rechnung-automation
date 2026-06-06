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
    runtime_config = settings.get("runtime", {})
    if not isinstance(runtime_config, dict):
        raise ValueError("Der YAML-Bereich 'runtime' muss eine Map sein.")
    validiere_pdf_config(settings.get("pdf", {}))
    validiere_design_config(settings.get("design", {}))
    validiere_branding_config(settings.get("branding", {}))
    _pruefe_mail_config(mail_config)
    if not isinstance(daten, list):
        raise ValueError("data/daten.json muss eine JSON-Liste sein.")

    pruefe_lesbare_datei(
        pfade.base_dir / "config" / "settings.yaml",
        "config/settings.yaml",
    )
    pruefe_lesbare_datei(pfade.base_dir / ".env", ".env")
    pruefe_lesbare_datei(pfade.data_dir / "daten.json", "data/daten.json")
    pruefe_lesbare_datei(
        pfade.data_dir / "konfiguration.json",
        "data/konfiguration.json",
    )
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
