import json
import logging
import os
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path

from dateutil.relativedelta import relativedelta

from validierung import validiere_betrag, validiere_einheit
from zeit import formatiere_monat_jahr, heute as aktuelles_datum

logger = logging.getLogger(__name__)


def berechne_stundenleistung(
    firma: str,
    zyklus: int,
    stundensatz: Decimal,
    hours_dir: Path,
    interactive: bool = True,
    heute: date | None = None,
):
    """Berechnet stundenbasierte Leistungen fuer den Abrechnungszeitraum."""
    heute = heute or aktuelles_datum()
    stunden_total = Decimal("0")
    monate = []
    fehlende_monate = []

    firma_key = firma.strip().lower()

    for i in range(zyklus):
        monat_dt = heute - relativedelta(months=i + 1)
        monat = monat_dt.month
        jahr = monat_dt.year
        dateiname = hours_dir / f"stunden_{jahr}_{monat:02d}.json"

        eintrag_gefunden = False

        if os.path.exists(dateiname):
            try:
                with open(dateiname, "r", encoding="utf-8") as f:
                    daten = json.load(f)
                    for eintrag in daten:
                        if eintrag.get("firma", "").strip().lower() == firma_key:
                            stunden = Decimal(str(eintrag.get("stunden", 0)))
                            if not stunden.is_finite() or stunden < 0:
                                raise ValueError(
                                    "Stunden muessen eine nichtnegative Zahl sein."
                                )
                            stunden_total += stunden
                            monate.append(formatiere_monat_jahr(monat_dt))
                            eintrag_gefunden = True
                            break
            except Exception as e:
                logger.warning("Fehler beim Lesen der Datei %s: %s", dateiname, e)

        if not eintrag_gefunden:
            logger.warning(
                "Keine Stunden fuer '%s' im Monat %s gefunden.",
                firma,
                formatiere_monat_jahr(monat_dt),
            )
            if not interactive:
                logger.info("Nicht-interaktiver Lauf: 0 Stunden angenommen.")
                fehlende_monate.append(monat_dt.strftime("%Y-%m"))
                continue

            eingabe = input(
                "Bitte Stundenanzahl manuell eingeben (Enter für 0): "
            ).strip()
            try:
                stunden = (
                    Decimal(eingabe.replace(",", ".")) if eingabe else Decimal("0")
                )
                if not stunden.is_finite() or stunden < 0:
                    raise InvalidOperation
                stunden_total += stunden
                if stunden > 0:
                    monate.append(formatiere_monat_jahr(monat_dt))
            except InvalidOperation:
                logger.warning("Ungueltige Eingabe - 0 Stunden angenommen.")

    betrag = stundensatz * stunden_total
    zeitraum = ", ".join(reversed(monate))

    return {
        "stunden": stunden_total,
        "stundensatz": stundensatz,
        "gesamtbetrag": betrag,
        "zeitraum": zeitraum,
        "vollstaendig": not fehlende_monate,
        "fehlende_monate": fehlende_monate,
    }


def baue_leistungspositionen(
    eintrag: dict,
    abrechnungszyklus: int,
    hours_dir: Path,
    interactive: bool = True,
    heute: date | None = None,
) -> dict:
    """Baut Leistungspositionen und Nettosumme fuer einen Kundeneintrag."""
    hauptleistung = eintrag.get("hauptleistung", {})
    leistungs_liste = []

    beschreibung = hauptleistung.get("beschreibung", "Leistung")
    einheit = validiere_einheit(hauptleistung.get("einheit", "Monat"))
    betrag = validiere_betrag(hauptleistung.get("betrag"), "Hauptleistung.betrag")

    stundeninfo = None
    if einheit == "stunde":
        stundeninfo = berechne_stundenleistung(
            eintrag.get("firma", ""),
            abrechnungszyklus,
            betrag,
            hours_dir,
            interactive=interactive,
            heute=heute,
        )

        if stundeninfo["stunden"] == 0 or not stundeninfo["vollstaendig"]:
            return {
                "leistungs_liste": leistungs_liste,
                "gesamtpreis": Decimal("0"),
                "stundeninfo": stundeninfo,
            }

        betrag = stundeninfo["gesamtbetrag"]
        gesamtpreis = betrag
        beschreibung = (
            f"{stundeninfo['stunden']:.1f} Stunden × "
            f"{stundeninfo['stundensatz']:.2f} EUR"
        )
        leistungs_liste.append(
            {
                "beschreibung": beschreibung,
                "preis": f"{betrag:.2f}".replace(".", ",") + " EUR",
            }
        )

    elif einheit == "pauschal":
        gesamtpreis = betrag
        leistungs_liste.append(
            {
                "beschreibung": f"{beschreibung} (pauschal)",
                "preis": f"{betrag:.2f}".replace(".", ",") + " EUR",
            }
        )

    else:
        gesamtpreis = betrag * abrechnungszyklus
        zeitraum_text = (
            "1 Monat" if abrechnungszyklus == 1 else f"{abrechnungszyklus} Monate"
        )
        beschreibung_mit_zeitraum = f"{beschreibung} für {zeitraum_text}"
        webseite = eintrag.get("webseite")
        if webseite:
            beschreibung_mit_zeitraum += f" ({webseite})"

        leistungs_liste.append(
            {
                "beschreibung": beschreibung_mit_zeitraum,
                "preis": f"{gesamtpreis:.2f}".replace(".", ",") + " EUR",
            }
        )

    for zusatz in eintrag.get("weitere_leistungen", []):
        beschreibung = zusatz.get("beschreibung", "Zusatzleistung")
        preis_str = str(zusatz.get("preis", "")).strip()
        preis_betrag = validiere_betrag(
            preis_str,
            "Preis der Zusatzleistung",
            inklusive_erlaubt=True,
        )

        if preis_betrag is not None:
            if zusatz.get("einheit") == "flat" or (
                "einheit" not in zusatz and einheit == "pauschal"
            ):
                preis_text = f"{preis_betrag:.2f}".replace(".", ",") + " EUR"
                zusatz_text = ""
                betrag_gesamt = preis_betrag
            else:
                betrag_gesamt = preis_betrag * abrechnungszyklus
                zusatz_text = (
                    f"({preis_betrag:.2f}".replace(".", ",")
                    + f" EUR × {abrechnungszyklus} Monate)"
                )
                preis_text = f"{betrag_gesamt:.2f}".replace(".", ",") + " EUR"
        else:
            zusatz_text = ""
            preis_text = preis_str
            betrag_gesamt = Decimal("0")

        leistungs_liste.append(
            {
                "beschreibung": beschreibung
                + (f"<br><small>{zusatz_text}</small>" if zusatz_text else ""),
                "preis": preis_text,
            }
        )

        if betrag_gesamt > 0:
            gesamtpreis += betrag_gesamt

    return {
        "leistungs_liste": leistungs_liste,
        "gesamtpreis": gesamtpreis,
        "stundeninfo": stundeninfo,
    }
