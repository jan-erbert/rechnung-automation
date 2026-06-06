import json
import os
from pathlib import Path

from dotenv import load_dotenv


def lade_konfiguration(pfad: Path) -> dict:
    """Laedt und prueft die zentrale Rechnungs-Konfiguration."""
    if not os.path.exists(pfad):
        raise FileNotFoundError(f"Konfigurationsdatei '{pfad}' nicht gefunden.")

    with open(pfad, "r", encoding="utf-8") as f:
        config = json.load(f)

    pflichtfelder = [
        ("absender", "name"),
        ("absender", "firma"),
        ("absender", "email"),
        ("bank", "iban"),
        ("bank", "kontoinhaber"),
        ("finanzen", "kleinunternehmer"),
    ]

    for bereich, feld in pflichtfelder:
        if feld not in config.get(bereich, {}):
            raise ValueError(f"Pflichtfeld fehlt: '{bereich}.{feld}'")

    _validiere_steuer_id(config["finanzen"])

    if not config["finanzen"].get("kleinunternehmer", False):
        if "mehrwertsteuer_prozent" not in config["finanzen"]:
            raise ValueError("Mehrwertsteuersatz fehlt bei Nicht-Kleinunternehmern.")

    return config


def _validiere_steuer_id(finanzen: dict) -> None:
    """Prueft die ausgewaehlte Steuernummer oder USt-IdNr."""
    steuer_id_typ = finanzen.get("steuer_id_typ")
    if steuer_id_typ not in ("steuernummer", "ust_id"):
        raise ValueError(
            "Pflichtfeld 'finanzen.steuer_id_typ' muss "
            "'steuernummer' oder 'ust_id' sein."
        )

    if not finanzen.get(steuer_id_typ):
        raise ValueError(f"Pflichtfeld fehlt: 'finanzen.{steuer_id_typ}'")


def lade_mail_umgebung(pfad: Path) -> dict:
    """Laedt die Mail-Zugangsdaten aus der lokalen Umgebung."""
    if not pfad.exists():
        raise FileNotFoundError(f"Env-Datei '{pfad}' nicht gefunden.")

    load_dotenv(pfad)

    pflichtfelder = ["MAIL_SERVER", "MAIL_PORT", "MAIL_USER", "MAIL_PASS"]
    fehlende_felder = [feld for feld in pflichtfelder if not os.getenv(feld)]
    if fehlende_felder:
        felder = ", ".join(fehlende_felder)
        raise ValueError(f"Pflichtfelder fehlen in der Env-Datei: {felder}")

    try:
        mail_port = int(os.getenv("MAIL_PORT"))
    except ValueError as err:
        raise ValueError("MAIL_PORT muss eine Zahl sein.") from err

    return {
        "server": os.getenv("MAIL_SERVER"),
        "port": mail_port,
        "user": os.getenv("MAIL_USER"),
        "passwort": os.getenv("MAIL_PASS"),
    }
