import os
from decimal import Decimal
from pathlib import Path

import yaml
from dotenv import dotenv_values

from validierung import (
    normalisiere_mail_liste,
    validiere_prozentsatz,
    validiere_positive_ganzzahl,
)


def lade_konfiguration(pfad: Path) -> dict:
    """Laedt die fachliche Rechnungskonfiguration aus YAML."""
    if not pfad.exists():
        raise FileNotFoundError(f"Konfigurationsdatei '{pfad}' nicht gefunden.")

    try:
        with pfad.open("r", encoding="utf-8") as config_file:
            config = yaml.safe_load(config_file) or {}
    except yaml.YAMLError as err:
        raise ValueError(f"Ungueltiges YAML in '{pfad.name}': {err}") from err
    if not isinstance(config, dict):
        raise ValueError("Die Rechnungskonfiguration muss eine YAML-Map sein.")

    sender = _erwarte_map(config, "sender")
    bank = _erwarte_map(config, "bank")
    tax = _erwarte_map(config, "tax")
    mail = config.get("mail", {})
    if not isinstance(mail, dict):
        raise ValueError("Der Bereich 'mail' muss eine Map sein.")

    _erwarte_felder(
        sender,
        "sender",
        ("name", "company", "street", "postal_code", "city", "phone", "email"),
    )
    _erwarte_felder(bank, "bank", ("name", "iban", "bic", "account_holder"))
    _validiere_steuer_id(tax)
    _validiere_mail_optionen(mail)
    normalisiere_mail_liste(sender["email"], "sender.email")
    for feld in ("name", "company", "street", "postal_code", "city", "phone", "email"):
        if not isinstance(sender[feld], str):
            raise ValueError(f"sender.{feld} muss ein Text sein.")
    for feld in ("name", "account_holder", "iban", "bic"):
        if not isinstance(bank[feld], str):
            raise ValueError(f"bank.{feld} muss ein Text sein.")

    kleinunternehmer = tax.get("small_business")
    if not isinstance(kleinunternehmer, bool):
        raise ValueError("tax.small_business muss true oder false sein.")

    mehrwertsteuer = Decimal("0")
    if not kleinunternehmer:
        if "vat_rate" not in tax:
            raise ValueError("tax.vat_rate fehlt bei Nicht-Kleinunternehmern.")
        if not isinstance(tax["vat_rate"], str):
            raise ValueError("tax.vat_rate muss als Text in Anfuehrungszeichen stehen.")
        mehrwertsteuer = validiere_prozentsatz(tax["vat_rate"], "tax.vat_rate")

    steuer_id_typ = {
        "tax_number": "steuernummer",
        "vat_id": "ust_id",
    }[tax["identifier_type"]]
    return {
        "absender": {
            "name": sender["name"],
            "firma": sender["company"],
            "straße": sender.get("street", ""),
            "plz": str(sender.get("postal_code", "")),
            "ort": sender.get("city", ""),
            "telefon": str(sender.get("phone", "")),
            "email": sender["email"],
            "website": sender.get("website", ""),
        },
        "bank": {
            "bankname": bank.get("name", ""),
            "kontoinhaber": bank["account_holder"],
            "iban": bank["iban"],
            "bic": bank.get("bic", ""),
        },
        "finanzen": {
            "steuer_id_typ": steuer_id_typ,
            steuer_id_typ: tax[tax["identifier_type"]],
            "finanzamt": tax.get("tax_office", ""),
            "kleinunternehmer": kleinunternehmer,
            "mehrwertsteuer_prozent": mehrwertsteuer,
        },
        "mail": {
            "bcc": _normalisiere_adressliste(mail.get("bcc")),
            "from_name": mail.get("from_name") or None,
        },
    }


def _erwarte_map(config: dict, name: str) -> dict:
    """Liefert einen erforderlichen YAML-Bereich als Map."""
    wert = config.get(name)
    if not isinstance(wert, dict):
        raise ValueError(f"Der Bereich '{name}' muss eine Map sein.")
    return wert


def _erwarte_felder(config: dict, bereich: str, felder: tuple[str, ...]) -> None:
    """Prueft erforderliche, nicht leere Konfigurationsfelder."""
    for feld in felder:
        if config.get(feld) in (None, ""):
            raise ValueError(f"Pflichtfeld fehlt: '{bereich}.{feld}'")


def _validiere_mail_optionen(mail_config: dict) -> None:
    """Prueft optionale Einstellungen fuer erzeugte E-Mails."""
    from_name = mail_config.get("from_name")
    if from_name not in (None, "") and (
        not isinstance(from_name, str) or not from_name.strip()
    ):
        raise ValueError("mail.from_name muss ein Text sein oder leer bleiben.")
    _normalisiere_adressliste(mail_config.get("bcc"))


def _normalisiere_adressliste(wert) -> list[str]:
    """Normalisiert optionale Konfigurations-Empfaenger als Liste."""
    if wert in (None, ""):
        return []
    if not isinstance(wert, list):
        raise ValueError("mail.bcc muss eine Liste von Mailadressen sein.")
    return normalisiere_mail_liste(wert, "mail.bcc")


def _validiere_steuer_id(tax: dict) -> None:
    """Prueft die ausgewaehlte Steuernummer oder USt-IdNr."""
    identifier_type = tax.get("identifier_type")
    if identifier_type not in ("tax_number", "vat_id"):
        raise ValueError("tax.identifier_type muss 'tax_number' oder 'vat_id' sein.")
    if not tax.get(identifier_type):
        raise ValueError(f"Pflichtfeld fehlt: 'tax.{identifier_type}'")
    if not isinstance(tax[identifier_type], str):
        raise ValueError(f"tax.{identifier_type} muss ein Text sein.")


def lade_mail_umgebung(pfad: Path, mail_settings: dict | None = None) -> dict:
    """Laedt Mail-Zugangsdaten ohne globale Umgebungsvariablen zu veraendern."""
    if not pfad.exists():
        raise FileNotFoundError(f"Env-Datei '{pfad}' nicht gefunden.")

    env = {**dotenv_values(pfad), **os.environ}
    pflichtfelder = ("MAIL_SERVER", "MAIL_PORT", "MAIL_USER", "MAIL_PASS")
    fehlende_felder = [feld for feld in pflichtfelder if not env.get(feld)]
    if fehlende_felder:
        raise ValueError(
            "Pflichtfelder fehlen in der Env-Datei: " + ", ".join(fehlende_felder)
        )

    mail_settings = mail_settings or {}
    if not isinstance(mail_settings, dict):
        raise ValueError("Der YAML-Bereich 'mail' muss eine Map sein.")
    security = str(mail_settings.get("security", "starttls")).lower()
    if security not in ("starttls", "ssl"):
        raise ValueError("mail.security muss 'starttls' oder 'ssl' sein.")
    timeout = validiere_positive_ganzzahl(
        mail_settings.get("timeout_seconds", 30), "mail.timeout_seconds"
    )

    mail_port = validiere_positive_ganzzahl(env["MAIL_PORT"], "MAIL_PORT")
    if mail_port > 65535:
        raise ValueError("MAIL_PORT darf hoechstens 65535 sein.")
    return {
        "server": env["MAIL_SERVER"],
        "port": mail_port,
        "user": env["MAIL_USER"],
        "passwort": env["MAIL_PASS"],
        "security": security,
        "timeout": timeout,
    }
