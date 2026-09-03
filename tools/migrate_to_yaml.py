import argparse
import json
import os
import re
import sys
import tempfile
from pathlib import Path

import yaml

BASE_DIR = Path(__file__).resolve().parent.parent
SRC_DIR = BASE_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from kundendateien import (  # noqa: E402
    kunde_als_yaml,
    lade_kundendateien,
    normalisiere_kunde,
    speichere_kundendatei,
)
from konfiguration import lade_konfiguration  # noqa: E402
from validierung import validiere_kundeneintrag  # noqa: E402


def parse_args() -> argparse.Namespace:
    """Liest Pfade und die expliziten Aktionsschalter der Migration."""
    parser = argparse.ArgumentParser(
        description="Migriert alte JSON-Konfigurationen kontrolliert nach YAML."
    )
    parser.add_argument(
        "--apply", action="store_true", help="Schreibt die YAML-Dateien."
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        help="Vergleicht vorhandene YAML-Dateien mit den JSON-Quellen.",
    )
    parser.add_argument(
        "--delete-legacy",
        action="store_true",
        help="Loescht beide JSON-Quellen erst nach erfolgreicher Pruefung.",
    )
    parser.add_argument(
        "--data-json", type=Path, default=BASE_DIR / "data" / "daten.json"
    )
    parser.add_argument(
        "--config-json",
        type=Path,
        default=BASE_DIR / "data" / "konfiguration.json",
    )
    parser.add_argument("--customers-dir", type=Path, default=BASE_DIR / "customers")
    parser.add_argument(
        "--invoice-yaml", type=Path, default=BASE_DIR / "config" / "invoice.yaml"
    )
    return parser.parse_args()


def lade_json(pfad: Path, erwarteter_typ: type):
    """Laedt eine alte JSON-Datei und prueft ihren obersten Datentyp."""
    with pfad.open("r", encoding="utf-8") as json_file:
        wert = json.load(json_file)
    if not isinstance(wert, erwarteter_typ):
        raise ValueError(f"{pfad} hat nicht den erwarteten Datentyp.")
    return wert


def erstelle_kunden_id(firma: str, verwendete_ids: set[str]) -> str:
    """Erzeugt eine eindeutige, dateisichere Kunden-ID."""
    basis = firma.lower().replace("ä", "ae").replace("ö", "oe").replace("ü", "ue")
    basis = basis.replace("ß", "ss")
    basis = re.sub(r"[^a-z0-9]+", "-", basis).strip("-") or "kunde"
    customer_id = basis
    nummer = 2
    while customer_id in verwendete_ids:
        customer_id = f"{basis}-{nummer}"
        nummer += 1
    verwendete_ids.add(customer_id)
    return customer_id


def normalisiere_alte_kunden(kunden: list[dict]) -> list[dict]:
    """Ergaenzt alte Kundeneintraege um IDs und eindeutige Zusatztypen."""
    ergebnis = []
    verwendete_ids: set[str] = set()
    for index, kunde in enumerate(kunden, start=1):
        if not isinstance(kunde, dict):
            raise ValueError(f"Kundeneintrag #{index} ist kein Objekt.")
        normalisiert = dict(kunde)
        normalisiert["id"] = erstelle_kunden_id(
            str(kunde.get("firma", "kunde")), verwendete_ids
        )
        normalisiert.setdefault("aktiv", True)
        normalisiert.setdefault("cc", [])
        normalisiert.setdefault("weitere_leistungen", [])
        hauptleistung = dict(normalisiert.get("hauptleistung", {}))
        hauptleistung["einheit"] = str(hauptleistung.get("einheit", "monat")).lower()
        normalisiert["hauptleistung"] = hauptleistung
        for leistung in normalisiert["weitere_leistungen"]:
            if str(leistung.get("preis", "")).strip().lower() == "inklusive":
                leistung["einheit"] = "included"
            elif hauptleistung.get("einheit") == "pauschal":
                leistung["einheit"] = "flat"
            else:
                leistung["einheit"] = "month"
        validiere_kundeneintrag(normalisiert)
        ergebnis.append(normalisiert)
    return ergebnis


def konvertiere_rechnungskonfiguration(config: dict) -> dict:
    """Uebersetzt die alte JSON-Rechnungskonfiguration ins neue YAML-Schema."""
    absender = config.get("absender", {})
    bank = config.get("bank", {})
    finanzen = config.get("finanzen", {})
    mail = config.get("mail", {})
    alter_typ = finanzen.get("steuer_id_typ")
    neuer_typ = {"steuernummer": "tax_number", "ust_id": "vat_id"}.get(alter_typ)
    if neuer_typ is None:
        raise ValueError("Unbekannter steuer_id_typ in der alten Konfiguration.")
    tax = {
        "identifier_type": neuer_typ,
        neuer_typ: finanzen.get(alter_typ),
        "tax_office": finanzen.get("finanzamt", ""),
        "small_business": finanzen.get("kleinunternehmer"),
    }
    if not tax["small_business"]:
        tax["vat_rate"] = str(finanzen.get("mehrwertsteuer_prozent"))
    bcc = mail.get("bcc")
    return {
        "sender": {
            "name": absender.get("name"),
            "company": absender.get("firma"),
            "street": absender.get("straße", absender.get("strasse", "")),
            "postal_code": str(absender.get("plz", "")),
            "city": absender.get("ort", ""),
            "phone": str(absender.get("telefon", "")),
            "email": absender.get("email"),
            "website": absender.get("website", ""),
        },
        "bank": {
            "name": bank.get("bankname", ""),
            "account_holder": bank.get("kontoinhaber"),
            "iban": bank.get("iban"),
            "bic": bank.get("bic", ""),
        },
        "tax": tax,
        "mail": {
            "bcc": [bcc] if isinstance(bcc, str) and bcc else bcc or [],
            "from_name": mail.get("from_name") or None,
        },
    }


def schreibe_yaml_atomar(pfad: Path, inhalt: dict) -> None:
    """Schreibt eine YAML-Datei atomar und ohne bestehende Datei zu ersetzen."""
    if pfad.exists():
        raise FileExistsError(f"Zieldatei existiert bereits: {pfad}")
    pfad.parent.mkdir(parents=True, exist_ok=True)
    temp_pfad = None
    try:
        with tempfile.NamedTemporaryFile(
            "w", encoding="utf-8", dir=pfad.parent, delete=False, suffix=".tmp"
        ) as temp_file:
            temp_pfad = Path(temp_file.name)
            yaml.safe_dump(inhalt, temp_file, allow_unicode=True, sort_keys=False)
            temp_file.flush()
            os.fsync(temp_file.fileno())
        os.replace(temp_pfad, pfad)
    finally:
        if temp_pfad and temp_pfad.exists():
            temp_pfad.unlink()


def lade_yaml_objekt(pfad: Path) -> dict:
    """Laedt fuer den Vergleich ein YAML-Objekt aus einer Datei."""
    if not pfad.is_file():
        raise FileNotFoundError(f"Erwartete YAML-Datei fehlt: {pfad}")
    with pfad.open("r", encoding="utf-8") as yaml_file:
        inhalt = yaml.safe_load(yaml_file)
    if not isinstance(inhalt, dict):
        raise ValueError(f"Pruefung fehlgeschlagen: {pfad} ist kein YAML-Objekt.")
    return inhalt


def pruefe_migration(
    kunden: list[dict],
    invoice_config: dict,
    customers_dir: Path,
    invoice_yaml: Path,
) -> None:
    """Vergleicht alle Migrationsergebnisse und validiert sie per Produktiv-Loader."""
    if lade_yaml_objekt(invoice_yaml) != invoice_config:
        raise ValueError(
            f"Pruefung fehlgeschlagen: {invoice_yaml} weicht von der JSON-Quelle ab."
        )

    for kunde in kunden:
        kunden_pfad = customers_dir / f"{kunde['id']}.yaml"
        if lade_yaml_objekt(kunden_pfad) != kunde_als_yaml(kunde):
            raise ValueError(
                "Pruefung fehlgeschlagen: "
                f"Kundendatei fuer '{kunde['id']}' weicht von der JSON-Quelle ab."
            )

    lade_konfiguration(invoice_yaml)
    geladene_kunden = {
        kunde["id"]: kunde for kunde in lade_kundendateien(customers_dir)
    }
    fehlende_ids = [
        kunde["id"] for kunde in kunden if kunde["id"] not in geladene_kunden
    ]
    if fehlende_ids:
        raise ValueError(
            "Pruefung fehlgeschlagen: Kunden fehlen nach dem Laden: "
            + ", ".join(fehlende_ids)
        )


def loesche_json_quellen(data_json: Path, config_json: Path) -> None:
    """Loescht exakt die beiden angegebenen JSON-Quellen."""
    quellpfade = (data_json, config_json)
    if data_json.resolve() == config_json.resolve():
        raise ValueError("Die beiden JSON-Quellpfade muessen verschieden sein.")
    for pfad in quellpfade:
        if not pfad.is_file():
            raise FileNotFoundError(f"JSON-Quelldatei fehlt: {pfad}")
    for pfad in quellpfade:
        pfad.unlink()


def main() -> int:
    """Migriert, prueft und entfernt Altdateien nur mit expliziten Schaltern."""
    args = parse_args()
    alte_kunden = lade_json(args.data_json, list)
    alte_config = lade_json(args.config_json, dict)
    kunden = normalisiere_alte_kunden(alte_kunden)
    invoice_config = konvertiere_rechnungskonfiguration(alte_config)
    for kunde in kunden:
        validiere_kundeneintrag(normalisiere_kunde(kunde_als_yaml(kunde)))

    ziele = [
        args.invoice_yaml,
        *[args.customers_dir / f"{k['id']}.yaml" for k in kunden],
    ]
    print(f"Geprueft: 1 Rechnungskonfiguration und {len(kunden)} Kunden.")
    if args.apply:
        vorhandene = [pfad for pfad in ziele if pfad.exists()]
        if vorhandene:
            raise FileExistsError(
                "Migration abgebrochen; Zieldateien existieren bereits: "
                + ", ".join(str(pfad) for pfad in vorhandene)
            )
        schreibe_yaml_atomar(args.invoice_yaml, invoice_config)
        for kunde in kunden:
            speichere_kundendatei(kunde, args.customers_dir / f"{kunde['id']}.yaml")
        print("YAML-Dateien wurden erzeugt.")
    elif not args.verify and not args.delete_legacy:
        vorhandene = [pfad for pfad in ziele if pfad.exists()]
        if vorhandene:
            raise FileExistsError(
                "Vorschau abgebrochen; Zieldateien existieren bereits: "
                + ", ".join(str(pfad) for pfad in vorhandene)
            )
        print("Vorschau abgeschlossen. Mit --apply werden die YAML-Dateien erzeugt.")
        return 0

    pruefe_migration(kunden, invoice_config, args.customers_dir, args.invoice_yaml)
    print("Pruefung erfolgreich: Alle migrierten YAML-Daten stimmen ueberein.")

    if args.delete_legacy:
        loesche_json_quellen(args.data_json, args.config_json)
        print("Die beiden alten JSON-Konfigurationsdateien wurden geloescht.")
    else:
        print("Die JSON-Quelldateien wurden nicht veraendert.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
