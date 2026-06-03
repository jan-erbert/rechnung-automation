from datetime import datetime, timedelta

from dateutil.relativedelta import relativedelta


def baue_rechnungsdaten(eintrag: dict, heute: datetime) -> dict:
    """Ermittelt Datum, Nummer und Faelligkeit fuer eine Rechnung."""
    rechnungsdatum = eintrag.get("rechnungsdatum")
    if not rechnungsdatum:
        rechnungsdatum = heute.strftime("%d.%m.%Y")

    faelligkeit_tage = eintrag.get("faelligkeit", 14)
    try:
        faelligkeit_tage = int(faelligkeit_tage)
    except ValueError:
        faelligkeit_tage = 14

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
        "monat_jahr": heute.strftime("%B %Y"),
        "faelligkeit_datum": faelligkeit_datum,
        "rechnungsnummer": rechnungsnummer,
        "auto_rechnungsnummer": auto_rechnungsnummer,
    }


def berechne_steuerwerte(gesamtpreis: float, finanzen: dict) -> dict:
    """Berechnet Steuerhinweis und Bruttosumme fuer die Rechnung."""
    if finanzen["kleinunternehmer"]:
        steuerbetrag = 0
        mwst_hinweis = "Gemäß § 19 UStG wird keine Umsatzsteuer berechnet."
        gesamtpreis_mit_mwst = gesamtpreis
    else:
        steuerbetrag = round(gesamtpreis * finanzen["mehrwertsteuer_prozent"] / 100, 2)
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


def berechne_abrechnungszeitraum(heute: datetime, abrechnungszyklus: int) -> str:
    """Baut den Text fuer den abgerechneten Monatszeitraum."""
    if abrechnungszyklus < 1:
        return ""

    zeitraum_start = heute.strftime("%B %Y")
    zeitraum_ende_dt = heute + relativedelta(months=abrechnungszyklus - 1)
    zeitraum_ende = zeitraum_ende_dt.strftime("%B %Y")

    if abrechnungszyklus == 1:
        return zeitraum_start

    return f"{zeitraum_start} – {zeitraum_ende}"
