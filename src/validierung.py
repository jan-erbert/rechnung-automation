from datetime import datetime
from email.utils import parseaddr
from math import isfinite

ERLAUBTE_EINHEITEN = ("monat", "stunde", "pauschal")


def validiere_betrag(
    wert,
    feld: str = "Betrag",
    inklusive_erlaubt: bool = False,
) -> float | None:
    """Prueft einen positiven Geldbetrag oder den Wert Inklusive."""
    text = str(wert).strip() if wert is not None else ""
    if inklusive_erlaubt and text.lower() == "inklusive":
        return None

    try:
        betrag = float(text.replace(",", "."))
    except ValueError as err:
        zusatz = " oder 'Inklusive'" if inklusive_erlaubt else ""
        raise ValueError(f"{feld} muss ein positiver Betrag{zusatz} sein.") from err

    if not isfinite(betrag) or betrag <= 0:
        raise ValueError(f"{feld} muss groesser als 0 sein.")

    return betrag


def validiere_positive_ganzzahl(wert, feld: str) -> int:
    """Prueft eine positive Ganzzahl."""
    zahl = _parse_ganzzahl(wert, feld)
    if zahl < 1:
        raise ValueError(f"{feld} muss mindestens 1 sein.")
    return zahl


def validiere_nichtnegative_ganzzahl(wert, feld: str) -> int:
    """Prueft eine nichtnegative Ganzzahl."""
    zahl = _parse_ganzzahl(wert, feld)
    if zahl < 0:
        raise ValueError(f"{feld} darf nicht negativ sein.")
    return zahl


def validiere_datum(wert, feld: str = "Rechnungsdatum") -> str:
    """Prueft ein Datum im Format TT.MM.JJJJ."""
    return _validiere_datumsformat(wert, "%d.%m.%Y", feld, "TT.MM.JJJJ")


def validiere_monat(wert, feld: str = "Letzte Rechnung") -> str:
    """Prueft einen Monat im Format JJJJ-MM."""
    return _validiere_datumsformat(wert, "%Y-%m", feld, "JJJJ-MM")


def validiere_einheit(wert) -> str:
    """Prueft die unterstuetzte Abrechnungseinheit."""
    einheit = str(wert).strip().lower() if wert is not None else ""
    if einheit not in ERLAUBTE_EINHEITEN:
        erlaubte_werte = ", ".join(ERLAUBTE_EINHEITEN)
        raise ValueError(
            "Hauptleistung.einheit muss einer dieser Werte sein: " f"{erlaubte_werte}."
        )
    return einheit


def normalisiere_mail_liste(wert, feld: str = "E-Mail") -> list[str]:
    """Prueft und normalisiert eine optionale Mailadresse oder Mailadressliste."""
    if wert in (None, ""):
        return []

    if isinstance(wert, str):
        adressen = [wert]
    elif isinstance(wert, list):
        adressen = wert
    else:
        raise ValueError(f"{feld} muss eine Mailadresse oder eine Liste sein.")

    normalisierte_adressen = []
    for index, adresse in enumerate(adressen, start=1):
        if not isinstance(adresse, str) or not adresse.strip():
            raise ValueError(f"{feld} #{index} muss eine Mailadresse sein.")
        normalisierte_adressen.append(_validiere_mailadresse(adresse.strip(), feld))

    return normalisierte_adressen


def validiere_kundeneintrag(eintrag: dict) -> None:
    """Prueft abrechnungsrelevante Werte eines Kundeneintrags."""
    if not isinstance(eintrag, dict):
        raise ValueError("Kundeneintrag muss ein Objekt sein.")

    hauptleistung = eintrag.get("hauptleistung")
    if not isinstance(hauptleistung, dict):
        raise ValueError("Hauptleistung fehlt oder ist ungueltig.")

    validiere_einheit(hauptleistung.get("einheit", "monat"))
    validiere_betrag(hauptleistung.get("betrag"), "Hauptleistung.betrag")
    validiere_positive_ganzzahl(
        eintrag.get("abrechnungszyklus", 1),
        "Abrechnungszyklus",
    )
    if not isinstance(eintrag.get("email"), str):
        raise ValueError("email muss eine Mailadresse sein.")
    normalisiere_mail_liste(eintrag.get("email"), "email")
    normalisiere_mail_liste(eintrag.get("cc"), "cc")

    if eintrag.get("faelligkeit") not in (None, ""):
        validiere_nichtnegative_ganzzahl(eintrag["faelligkeit"], "Faelligkeit")
    if eintrag.get("rechnungsdatum"):
        validiere_datum(eintrag["rechnungsdatum"])
    if eintrag.get("letzte_rechnung"):
        validiere_monat(eintrag["letzte_rechnung"])

    weitere_leistungen = eintrag.get("weitere_leistungen", [])
    if weitere_leistungen is None:
        weitere_leistungen = []
    if not isinstance(weitere_leistungen, list):
        raise ValueError("Weitere Leistungen muessen eine Liste sein.")

    for index, leistung in enumerate(weitere_leistungen, start=1):
        if not isinstance(leistung, dict):
            raise ValueError(f"Weitere Leistung #{index} muss ein Objekt sein.")
        validiere_betrag(
            leistung.get("preis"),
            f"Weitere Leistung #{index}.preis",
            inklusive_erlaubt=True,
        )


def _parse_ganzzahl(wert, feld: str) -> int:
    """Wandelt einen Wert kontrolliert in eine Ganzzahl um."""
    if isinstance(wert, bool):
        raise ValueError(f"{feld} muss eine ganze Zahl sein.")

    text = str(wert).strip() if wert is not None else ""
    if text.startswith("+"):
        text = text[1:]
    if not text or not text.lstrip("-").isdigit():
        raise ValueError(f"{feld} muss eine ganze Zahl sein.")
    return int(text)


def _validiere_mailadresse(adresse: str, feld: str) -> str:
    """Prueft eine einfache Mailadresse mit der Standardbibliothek."""
    name, parsed = parseaddr(adresse)
    if name or parsed != adresse or "@" not in parsed:
        raise ValueError(f"{feld} enthaelt eine ungueltige Mailadresse.")
    lokaler_teil, domain = parsed.rsplit("@", 1)
    if not lokaler_teil or "." not in domain or domain.startswith("."):
        raise ValueError(f"{feld} enthaelt eine ungueltige Mailadresse.")
    return parsed


def _validiere_datumsformat(
    wert,
    format_string: str,
    feld: str,
    format_name: str,
) -> str:
    """Prueft und normalisiert ein festes Datumsformat."""
    text = str(wert).strip() if wert is not None else ""
    try:
        datum = datetime.strptime(text, format_string)
    except ValueError as err:
        raise ValueError(f"{feld} muss dem Format {format_name} entsprechen.") from err

    if datum.strftime(format_string) != text:
        raise ValueError(f"{feld} muss dem Format {format_name} entsprechen.")
    return text
