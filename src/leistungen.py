import json
import os
from datetime import datetime
from pathlib import Path

from dateutil.relativedelta import relativedelta


def berechne_stundenleistung(
    firma: str,
    zyklus: int,
    stundensatz: float,
    stunden_dir: Path,
):
    """Berechnet stundenbasierte Leistungen fuer den Abrechnungszeitraum."""
    heute = datetime.today()
    stunden_total = 0.0
    monate = []

    firma_key = firma.strip().lower()

    for i in range(zyklus):
        monat_dt = heute - relativedelta(months=i + 1)
        monat = monat_dt.month
        jahr = monat_dt.year
        dateiname = stunden_dir / f"stunden_{jahr}_{monat:02d}.json"

        eintrag_gefunden = False

        if os.path.exists(dateiname):
            try:
                with open(dateiname, "r", encoding="utf-8") as f:
                    daten = json.load(f)
                    for eintrag in daten:
                        if eintrag.get("firma", "").strip().lower() == firma_key:
                            stunden = float(eintrag.get("stunden", 0))
                            stunden_total += stunden
                            monate.append(monat_dt.strftime("%B %Y"))
                            eintrag_gefunden = True
                            break
            except Exception as e:
                print(f"⚠️ Fehler beim Lesen der Datei {dateiname}: {e}")

        if not eintrag_gefunden:
            print(
                f"❓ Keine Stunden für '{firma}' im Monat {monat_dt.strftime('%B %Y')} gefunden."
            )
            eingabe = input(
                "Bitte Stundenanzahl manuell eingeben (Enter für 0): "
            ).strip()
            try:
                stunden = float(eingabe.replace(",", ".")) if eingabe else 0.0
                stunden_total += stunden
                if stunden > 0:
                    monate.append(monat_dt.strftime("%B %Y"))
            except ValueError:
                print("⚠️ Ungültige Eingabe – 0 Stunden angenommen.")

    betrag = stundensatz * stunden_total
    zeitraum = ", ".join(reversed(monate))

    return {
        "stunden": stunden_total,
        "stundensatz": stundensatz,
        "gesamtbetrag": betrag,
        "zeitraum": zeitraum,
    }


def baue_leistungspositionen(
    eintrag: dict,
    abrechnungszyklus: int,
    stunden_dir: Path,
) -> dict:
    """Baut Leistungspositionen und Nettosumme fuer einen Kundeneintrag."""
    hauptleistung = eintrag.get("hauptleistung", {})
    leistungs_liste = []

    beschreibung = hauptleistung.get("beschreibung", "Leistung")
    einheit = hauptleistung.get("einheit", "Monat").strip().lower()
    betrag_str = hauptleistung.get("betrag", "0").replace(",", ".").strip()

    try:
        betrag = float(betrag_str)
    except ValueError:
        betrag = 0.0

    stundeninfo = None
    if einheit == "stunde":
        stundeninfo = berechne_stundenleistung(
            eintrag.get("firma", ""),
            abrechnungszyklus,
            betrag,
            stunden_dir,
        )

        if stundeninfo["stunden"] == 0:
            return {
                "leistungs_liste": leistungs_liste,
                "gesamtpreis": 0.0,
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
        leistungs_liste.append(
            {
                "beschreibung": (
                    f"{beschreibung} für {zeitraum_text} "
                    f"({eintrag.get('webseite', '')})"
                ),
                "preis": f"{gesamtpreis:.2f}".replace(".", ",") + " EUR",
            }
        )

    for zusatz in eintrag.get("weitere_leistungen", []):
        beschreibung = zusatz.get("beschreibung", "Zusatzleistung")
        preis_str = zusatz.get("preis", "").strip()

        try:
            preis_float = float(preis_str.replace(",", "."))
            if einheit == "pauschal":
                preis_text = f"{preis_float:.2f}".replace(".", ",") + " EUR"
                zusatz_text = ""
                betrag_gesamt = preis_float
            else:
                betrag_gesamt = preis_float * abrechnungszyklus
                zusatz_text = (
                    f"({preis_float:.2f}".replace(".", ",")
                    + f" EUR × {abrechnungszyklus} Monate)"
                )
                preis_text = f"{betrag_gesamt:.2f}".replace(".", ",") + " EUR"
        except ValueError:
            zusatz_text = ""
            preis_text = preis_str
            betrag_gesamt = 0.0

        leistungs_liste.append(
            {
                "beschreibung": beschreibung
                + (f"<br><small>{zusatz_text}</small>" if zusatz_text else ""),
                "preis": preis_text,
            }
        )

        if isinstance(betrag_gesamt, float) and betrag_gesamt > 0:
            betrag_gesamt = preis_float * abrechnungszyklus
            gesamtpreis += betrag_gesamt

    return {
        "leistungs_liste": leistungs_liste,
        "gesamtpreis": gesamtpreis,
        "stundeninfo": stundeninfo,
    }
