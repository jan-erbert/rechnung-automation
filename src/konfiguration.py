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

    if not config["finanzen"].get("kleinunternehmer", False):
        if "mehrwertsteuer_prozent" not in config["finanzen"]:
            raise ValueError("Mehrwertsteuersatz fehlt bei Nicht-Kleinunternehmern.")

    return config


def lade_mail_umgebung(pfad: Path) -> dict:
    """Laedt die Mail-Zugangsdaten aus der lokalen Umgebung."""
    load_dotenv(pfad)
    return {
        "server": os.getenv("MAIL_SERVER"),
        "port": int(os.getenv("MAIL_PORT")),
        "user": os.getenv("MAIL_USER"),
        "passwort": os.getenv("MAIL_PASS"),
    }
