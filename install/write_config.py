import argparse
import os
import tempfile
from pathlib import Path

import yaml


def baue_konfiguration(values: dict[str, str]) -> dict:
    """Baut die Rechnungskonfiguration aus validierten Installer-Werten."""
    steuer_id_typ = values["SETUP_STEUER_ID_TYP"]
    if steuer_id_typ not in ("tax_number", "vat_id"):
        raise ValueError("SETUP_STEUER_ID_TYP ist ungueltig.")
    if values["SETUP_KLEINUNTERNEHMER"] not in ("true", "false"):
        raise ValueError("SETUP_KLEINUNTERNEHMER ist ungueltig.")

    tax = {
        "identifier_type": steuer_id_typ,
        steuer_id_typ: values["SETUP_STEUER_ID_WERT"],
        "tax_office": values["SETUP_FINANZAMT"],
        "small_business": values["SETUP_KLEINUNTERNEHMER"] == "true",
    }
    if not tax["small_business"]:
        mehrwertsteuer = int(values["SETUP_MWST"])
        if not 0 <= mehrwertsteuer <= 100:
            raise ValueError("SETUP_MWST muss zwischen 0 und 100 liegen.")
        tax["vat_rate"] = str(mehrwertsteuer)

    return {
        "sender": {
            "name": values["SETUP_NAME"],
            "company": values["SETUP_FIRMA"],
            "street": values["SETUP_STRASSE"],
            "postal_code": values["SETUP_PLZ"],
            "city": values["SETUP_ORT"],
            "phone": values["SETUP_TELEFON"],
            "email": values["SETUP_EMAIL"],
            "website": values.get("SETUP_WEBSITE", ""),
        },
        "bank": {
            "name": values["SETUP_BANKNAME"],
            "account_holder": values["SETUP_KONTOINHABER"],
            "iban": values["SETUP_IBAN"],
            "bic": values["SETUP_BIC"],
        },
        "tax": tax,
        "mail": {
            "bcc": [values["SETUP_BCC"]] if values.get("SETUP_BCC") else [],
            "from_name": values.get("SETUP_MAIL_FROM_NAME", ""),
        },
    }


def schreibe_konfiguration(pfad: Path, values: dict[str, str]) -> None:
    """Schreibt die Installer-Konfiguration atomar als geschuetztes YAML."""
    konfiguration = baue_konfiguration(values)
    pfad.parent.mkdir(parents=True, exist_ok=True)
    temp_pfad = None
    try:
        with tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-8",
            dir=pfad.parent,
            prefix=f".{pfad.name}.",
            suffix=".tmp",
            delete=False,
        ) as config_file:
            temp_pfad = Path(config_file.name)
            yaml.safe_dump(
                konfiguration,
                config_file,
                allow_unicode=True,
                sort_keys=False,
            )
            config_file.flush()
            os.fsync(config_file.fileno())
        os.replace(temp_pfad, pfad)
        os.chmod(pfad, 0o600)
    finally:
        if temp_pfad and temp_pfad.exists():
            temp_pfad.unlink()


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
