import argparse
import os
import tempfile
from pathlib import Path

import yaml


def build_configuration(values: dict[str, str]) -> dict:
    """Baut die Rechnungskonfiguration aus validierten Installer-Werten."""
    identifier_type = values["SETUP_TAX_IDENTIFIER_TYPE"]
    if identifier_type not in ("tax_number", "vat_id"):
        raise ValueError("SETUP_TAX_IDENTIFIER_TYPE ist ungueltig.")
    if values["SETUP_SMALL_BUSINESS"] not in ("true", "false"):
        raise ValueError("SETUP_SMALL_BUSINESS ist ungueltig.")

    tax = {
        "identifier_type": identifier_type,
        identifier_type: values["SETUP_TAX_IDENTIFIER_VALUE"],
        "tax_office": values["SETUP_TAX_OFFICE"],
        "small_business": values["SETUP_SMALL_BUSINESS"] == "true",
    }
    if not tax["small_business"]:
        vat_rate = int(values["SETUP_VAT_RATE"])
        if not 0 <= vat_rate <= 100:
            raise ValueError("SETUP_VAT_RATE muss zwischen 0 und 100 liegen.")
        tax["vat_rate"] = str(vat_rate)

    return {
        "sender": {
            "name": values["SETUP_CONTACT_NAME"],
            "company": values["SETUP_COMPANY"],
            "street": values["SETUP_STREET"],
            "postal_code": values["SETUP_POSTAL_CODE"],
            "city": values["SETUP_CITY"],
            "phone": values["SETUP_PHONE"],
            "email": values["SETUP_EMAIL"],
            "website": values.get("SETUP_WEBSITE", ""),
        },
        "bank": {
            "name": values["SETUP_BANK_NAME"],
            "account_holder": values["SETUP_ACCOUNT_HOLDER"],
            "iban": values["SETUP_IBAN"],
            "bic": values["SETUP_BIC"],
        },
        "tax": tax,
        "mail": {
            "bcc": [values["SETUP_BCC"]] if values.get("SETUP_BCC") else [],
            "from_name": values.get("SETUP_MAIL_FROM_NAME", ""),
        },
    }


def write_configuration(path: Path, values: dict[str, str]) -> None:
    """Schreibt die Installer-Konfiguration atomar als geschuetztes YAML."""
    configuration = build_configuration(values)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = None
    try:
        with tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as config_file:
            temporary_path = Path(config_file.name)
            yaml.safe_dump(
                configuration,
                config_file,
                allow_unicode=True,
                sort_keys=False,
            )
            config_file.flush()
            os.fsync(config_file.fileno())
        os.replace(temporary_path, path)
        os.chmod(path, 0o600)
    finally:
        if temporary_path and temporary_path.exists():
            temporary_path.unlink()


def main() -> None:
    """Schreibt die Konfiguration aus den SETUP_-Umgebungsvariablen."""
    parser = argparse.ArgumentParser()
    parser.add_argument("config_path", type=Path)
    args = parser.parse_args()
    values = {
        key: value for key, value in os.environ.items() if key.startswith("SETUP_")
    }
    write_configuration(args.config_path, values)


if __name__ == "__main__":
    main()
