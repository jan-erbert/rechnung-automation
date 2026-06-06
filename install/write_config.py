import argparse
import json
import os
from pathlib import Path


def baue_konfiguration(values: dict[str, str]) -> dict:
    """Baut die Rechnungskonfiguration aus validierten Installer-Werten."""
    steuer_id_typ = values["SETUP_STEUER_ID_TYP"]
    if steuer_id_typ not in ("steuernummer", "ust_id"):
        raise ValueError("SETUP_STEUER_ID_TYP ist ungueltig.")
    if values["SETUP_KLEINUNTERNEHMER"] not in ("true", "false"):
        raise ValueError("SETUP_KLEINUNTERNEHMER ist ungueltig.")

    finanzen = {
        "steuer_id_typ": steuer_id_typ,
        steuer_id_typ: values["SETUP_STEUER_ID_WERT"],
        "finanzamt": values["SETUP_FINANZAMT"],
        "kleinunternehmer": values["SETUP_KLEINUNTERNEHMER"] == "true",
    }
    if not finanzen["kleinunternehmer"]:
        mehrwertsteuer = int(values["SETUP_MWST"])
        if not 0 <= mehrwertsteuer <= 100:
            raise ValueError("SETUP_MWST muss zwischen 0 und 100 liegen.")
        finanzen["mehrwertsteuer_prozent"] = mehrwertsteuer

    return {
        "absender": {
            "name": values["SETUP_NAME"],
            "firma": values["SETUP_FIRMA"],
            "straße": values["SETUP_STRASSE"],
            "plz": values["SETUP_PLZ"],
            "ort": values["SETUP_ORT"],
            "telefon": values["SETUP_TELEFON"],
            "email": values["SETUP_EMAIL"],
            "website": values.get("SETUP_WEBSITE", ""),
        },
        "bank": {
            "bankname": values["SETUP_BANKNAME"],
            "kontoinhaber": values["SETUP_KONTOINHABER"],
            "iban": values["SETUP_IBAN"],
            "bic": values["SETUP_BIC"],
        },
        "finanzen": finanzen,
        "mail": {
            "bcc": values.get("SETUP_BCC", ""),
            "from_name": values.get("SETUP_MAIL_FROM_NAME", ""),
        },
    }


def schreibe_konfiguration(pfad: Path, values: dict[str, str]) -> None:
    """Schreibt die Installer-Konfiguration als gueltiges UTF-8-JSON."""
    konfiguration = baue_konfiguration(values)
    pfad.parent.mkdir(parents=True, exist_ok=True)
    with pfad.open("w", encoding="utf-8") as config_file:
        json.dump(konfiguration, config_file, indent=2, ensure_ascii=False)
        config_file.write("\n")


def main() -> None:
    """Schreibt die Konfiguration aus den SETUP_-Umgebungsvariablen."""
    parser = argparse.ArgumentParser()
    parser.add_argument("config_path", type=Path)
    args = parser.parse_args()
    values = {
        key: value for key, value in os.environ.items() if key.startswith("SETUP_")
    }
    schreibe_konfiguration(args.config_path, values)


if __name__ == "__main__":
    main()
