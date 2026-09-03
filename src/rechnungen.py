from datetime import date, datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP

from dateutil.relativedelta import relativedelta

from validierung import validiere_datum, validiere_nichtnegative_ganzzahl
from zeit import formatiere_monat_jahr

CENT = Decimal("0.01")


def baue_rechnungsdaten(eintrag: dict, heute: date | datetime) -> dict:
    """Ermittelt Datum, Nummer und Faelligkeit fuer eine Rechnung."""
    rechnungsdatum = eintrag.get("rechnungsdatum")
    if not rechnungsdatum:
        rechnungsdatum = heute.strftime("%d.%m.%Y")
    else:
        rechnungsdatum = validiere_datum(rechnungsdatum)

    faelligkeit_tage = validiere_nichtnegative_ganzzahl(
        eintrag.get("faelligkeit", 14),
        "Faelligkeit",
    )

    rechnungsdatum_obj = datetime.strptime(rechnungsdatum, "%d.%m.%Y")
    faelligkeit_datum = (
        rechnungsdatum_obj + timedelta(days=faelligkeit_tage)
    ).strftime("%d.%m.%Y")

    prefix = eintrag.get("rechnungsnummer", "").strip()
    auto_rechnungsnummer = heute.strftime("%m-%Y")
    rechnungsnummer = (
        f"{prefix}-{auto_rechnungsnummer}" if prefix else auto_rechnungsnummer
    )

    return {
        "rechnungsdatum": rechnungsdatum,
        "monat_jahr": formatiere_monat_jahr(heute),
        "faelligkeit_datum": faelligkeit_datum,
        "rechnungsnummer": rechnungsnummer,
        "auto_rechnungsnummer": auto_rechnungsnummer,
    }


def berechne_steuerwerte(gesamtpreis: Decimal, finanzen: dict) -> dict:
    """Berechnet Steuerhinweis und Bruttosumme fuer die Rechnung."""
    gesamtpreis = Decimal(str(gesamtpreis))
    if finanzen["kleinunternehmer"]:
        steuerbetrag = Decimal("0.00")
        mwst_hinweis = "Gemäß § 19 UStG wird keine Umsatzsteuer berechnet."
        gesamtpreis_mit_mwst = gesamtpreis
    else:
        steuersatz = Decimal(str(finanzen["mehrwertsteuer_prozent"]))
        steuerbetrag = (gesamtpreis * steuersatz / Decimal("100")).quantize(
            CENT, rounding=ROUND_HALF_UP
        )
        mwst_hinweis = (
            f"zzgl. {finanzen['mehrwertsteuer_prozent']}% MwSt "
            f"({steuerbetrag:.2f} EUR)"
        )
        gesamtpreis_mit_mwst = gesamtpreis + steuerbetrag

    return {
        "steuerbetrag": steuerbetrag,
        "mwst_hinweis": mwst_hinweis,
        "gesamtpreis_mit_mwst": gesamtpreis_mit_mwst,
        "gesamtpreis_str": f"{gesamtpreis_mit_mwst:.2f}".replace(".", ","),
    }


def berechne_abrechnungszeitraum(heute: date | datetime, abrechnungszyklus: int) -> str:
    """Baut den Text fuer den abgerechneten Monatszeitraum."""
    if abrechnungszyklus < 1:
        return ""

    zeitraum_start = formatiere_monat_jahr(heute)
    zeitraum_ende_dt = heute + relativedelta(months=abrechnungszyklus - 1)
    zeitraum_ende = formatiere_monat_jahr(zeitraum_ende_dt)

    if abrechnungszyklus == 1:
        return zeitraum_start

    return f"{zeitraum_start} – {zeitraum_ende}"
