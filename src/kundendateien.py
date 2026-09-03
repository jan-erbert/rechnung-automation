import os
import re
import tempfile
import logging
from datetime import date, datetime
from pathlib import Path

import yaml

from validierung import validiere_kundeneintrag

CUSTOMER_ID_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
UNIT_TO_INTERNAL = {"month": "monat", "hour": "stunde", "flat": "pauschal"}
UNIT_TO_YAML = {wert: key for key, wert in UNIT_TO_INTERNAL.items()}
logger = logging.getLogger(__name__)


def lade_kundendateien(customers_dir: Path, strict: bool = True) -> list[dict]:
    """Laedt und validiert alle YAML-Kundendateien eines Verzeichnisses."""
    if not customers_dir.exists():
        raise FileNotFoundError(f"Kundenverzeichnis '{customers_dir}' fehlt.")
    if not customers_dir.is_dir():
        raise ValueError(f"Kundenpfad '{customers_dir}' ist kein Verzeichnis.")

    kunden = []
    bekannte_ids = set()
    dateien = sorted((*customers_dir.glob("*.yaml"), *customers_dir.glob("*.yml")))
    for dateipfad in dateien:
        try:
            with dateipfad.open("r", encoding="utf-8") as customer_file:
                rohwert = yaml.safe_load(customer_file) or {}
            kunde = normalisiere_kunde(rohwert, dateipfad)
            validiere_kundeneintrag(kunde)
            if kunde["id"] in bekannte_ids:
                raise ValueError(f"Doppelte Kunden-ID: '{kunde['id']}'.")
        except (OSError, ValueError, yaml.YAMLError) as err:
            fehler = ValueError(f"{dateipfad.name}: {err}")
            if strict:
                raise fehler from err
            logger.error("Kundendatei wird uebersprungen: %s", fehler)
            continue
        bekannte_ids.add(kunde["id"])
        kunden.append(kunde)
    return kunden


def normalisiere_kunde(rohwert: dict, dateipfad: Path | None = None) -> dict:
    """Uebersetzt das editierbare YAML-Schema in das interne Kundenmodell."""
    if not isinstance(rohwert, dict):
        raise ValueError("Kundendatei muss eine YAML-Map enthalten.")
    customer_id = rohwert.get("id")
    if not isinstance(customer_id, str) or not CUSTOMER_ID_PATTERN.fullmatch(
        customer_id
    ):
        raise ValueError(
            "id muss ein kleingeschriebener Bezeichner wie 'musterfirma' sein."
        )

    contact = _map(rohwert, "contact")
    billing = _map(rohwert, "billing", optional=True)
    main_service = _map(rohwert, "main_service")
    unit = main_service.get("unit", "month")
    if unit not in UNIT_TO_INTERNAL:
        raise ValueError("main_service.unit muss month, hour oder flat sein.")
    if not isinstance(main_service.get("unit_price"), str):
        raise ValueError(
            "main_service.unit_price muss als Text in Anfuehrungszeichen stehen."
        )
    for feld in ("name", "company", "email", "street", "postal_code", "city"):
        if not isinstance(contact.get(feld), str) or not contact[feld].strip():
            raise ValueError(f"contact.{feld} muss ein nicht leerer Text sein.")
    if not isinstance(contact.get("cc", []), list):
        raise ValueError("contact.cc muss eine Liste sein.")
    if contact.get("website") is not None and not isinstance(
        contact.get("website"), str
    ):
        raise ValueError("contact.website muss ein Text oder null sein.")
    archive = _map(rohwert, "archive", optional=True)
    if archive.get("directory") is not None and not isinstance(
        archive.get("directory"), str
    ):
        raise ValueError("archive.directory muss ein Text oder null sein.")
    if (
        not isinstance(main_service.get("description"), str)
        or not main_service["description"].strip()
    ):
        raise ValueError("main_service.description muss ein nicht leerer Text sein.")

    kunde = {
        "id": customer_id,
        "aktiv": rohwert.get("active", True),
        "name": contact.get("name"),
        "firma": contact.get("company"),
        "email": contact.get("email"),
        "cc": contact.get("cc", []),
        "strasse": contact.get("street"),
        "plz": str(contact.get("postal_code", "")),
        "ort": contact.get("city"),
        "webseite": contact.get("website"),
        "rechnungsnummer": billing.get("invoice_prefix", ""),
        "abrechnungszyklus": billing.get("cycle_months", 1),
        "faelligkeit": billing.get("due_days", 14),
        "letzte_rechnung": _normalisiere_monat(billing.get("end_month")),
        "rechnungsdatum": _normalisiere_rechnungsdatum(billing.get("invoice_date")),
        "einmalig": billing.get("one_time", False),
        "hauptleistung": {
            "beschreibung": main_service.get("description"),
            "einheit": UNIT_TO_INTERNAL[unit],
            "betrag": main_service.get("unit_price"),
        },
        "weitere_leistungen": _normalisiere_zusatzleistungen(
            rohwert.get("additional_services", [])
        ),
        "archiv_pfad": archive.get("directory"),
    }
    if dateipfad is not None:
        kunde["_dateipfad"] = dateipfad
    return kunde


def _normalisiere_zusatzleistungen(leistungen) -> list[dict]:
    """Uebersetzt Zusatzleistungen in das interne Format."""
    if not isinstance(leistungen, list):
        raise ValueError("additional_services muss eine Liste sein.")
    ergebnis = []
    for index, leistung in enumerate(leistungen, start=1):
        if not isinstance(leistung, dict):
            raise ValueError(f"additional_services #{index} muss eine Map sein.")
        unit = leistung.get("unit", "flat")
        if unit not in ("flat", "month", "included"):
            raise ValueError(
                f"additional_services #{index}.unit muss flat, month oder included sein."
            )
        preis = "Inklusive" if unit == "included" else leistung.get("unit_price")
        if unit != "included" and not isinstance(preis, str):
            raise ValueError(
                f"additional_services #{index}.unit_price muss als Text "
                "in Anfuehrungszeichen stehen."
            )
        ergebnis.append(
            {
                "beschreibung": leistung.get("description"),
                "preis": preis,
                "einheit": unit,
            }
        )
    return ergebnis


def _map(config: dict, name: str, optional: bool = False) -> dict:
    """Liefert einen YAML-Unterbereich als Map."""
    wert = config.get(name, {}) if optional else config.get(name)
    if not isinstance(wert, dict):
        raise ValueError(f"{name} muss eine Map sein.")
    return wert


def _normalisiere_monat(wert) -> str | None:
    """Normalisiert einen optionalen Abrechnungs-Endmonat."""
    return None if wert in (None, "") else str(wert)


def _normalisiere_rechnungsdatum(wert) -> str | None:
    """Uebersetzt ein optionales ISO-Datum ins interne deutsche Format."""
    if wert in (None, ""):
        return None
    if isinstance(wert, datetime):
        wert = wert.date()
    if isinstance(wert, date):
        return wert.strftime("%d.%m.%Y")
    text = str(wert)
    for format_string in ("%Y-%m-%d", "%d.%m.%Y"):
        try:
            return datetime.strptime(text, format_string).strftime("%d.%m.%Y")
        except ValueError:
            continue
    raise ValueError("billing.invoice_date muss dem Format JJJJ-MM-TT entsprechen.")


def kunde_als_yaml(kunde: dict) -> dict:
    """Uebersetzt das interne Kundenmodell in das editierbare YAML-Schema."""
    zusatzleistungen = []
    for leistung in kunde.get("weitere_leistungen", []):
        inklusive = str(leistung.get("preis", "")).lower() == "inklusive"
        eintrag = {
            "description": leistung.get("beschreibung"),
            "unit": "included" if inklusive else leistung.get("einheit", "flat"),
        }
        if not inklusive:
            eintrag["unit_price"] = str(leistung.get("preis"))
        zusatzleistungen.append(eintrag)

    return {
        "id": kunde["id"],
        "active": kunde.get("aktiv", True),
        "contact": {
            "name": kunde.get("name"),
            "company": kunde.get("firma"),
            "email": kunde.get("email"),
            "cc": kunde.get("cc", []),
            "street": kunde.get("strasse"),
            "postal_code": str(kunde.get("plz", "")),
            "city": kunde.get("ort"),
            "website": kunde.get("webseite"),
        },
        "billing": {
            "invoice_prefix": kunde.get("rechnungsnummer") or None,
            "cycle_months": kunde.get("abrechnungszyklus", 1),
            "due_days": kunde.get("faelligkeit", 14),
            "end_month": kunde.get("letzte_rechnung") or None,
            "invoice_date": _rechnungsdatum_als_iso(kunde.get("rechnungsdatum")),
            "one_time": kunde.get("einmalig", False),
        },
        "main_service": {
            "description": kunde["hauptleistung"].get("beschreibung"),
            "unit": UNIT_TO_YAML[kunde["hauptleistung"].get("einheit", "monat")],
            "unit_price": str(kunde["hauptleistung"].get("betrag")),
        },
        "additional_services": zusatzleistungen,
        "archive": {"directory": kunde.get("archiv_pfad") or None},
    }


def _rechnungsdatum_als_iso(wert) -> str | None:
    """Uebersetzt ein internes Rechnungsdatum ins YAML-ISO-Format."""
    if not wert:
        return None
    return datetime.strptime(str(wert), "%d.%m.%Y").strftime("%Y-%m-%d")


def speichere_kundendatei(kunde: dict, dateipfad: Path) -> None:
    """Schreibt eine einzelne Kundendatei atomar als YAML."""
    yaml_daten = kunde_als_yaml(kunde)
    validiere_kundeneintrag(normalisiere_kunde(yaml_daten))
    dateipfad.parent.mkdir(parents=True, exist_ok=True)
    temp_pfad = None
    try:
        with tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-8",
            dir=dateipfad.parent,
            prefix=f".{dateipfad.name}.",
            suffix=".tmp",
            delete=False,
        ) as temp_file:
            temp_pfad = Path(temp_file.name)
            yaml.safe_dump(
                yaml_daten,
                temp_file,
                allow_unicode=True,
                sort_keys=False,
            )
            temp_file.flush()
            os.fsync(temp_file.fileno())
        os.replace(temp_pfad, dateipfad)
    finally:
        if temp_pfad and temp_pfad.exists():
            temp_pfad.unlink()
