import logging
from datetime import datetime

from validierung import validiere_positive_ganzzahl
from verlauf import (
    VERSANDSTATUS_FAILED,
    VERSANDSTATUS_NO_INVOICE,
    VERSANDSTATUS_PENDING,
    VERSANDSTATUS_SENT,
    VERSANDSTATUS_WAITING_HOURS,
    ist_abrechnung_abgeschlossen,
)
from zeit import heute as aktuelles_datum

logger = logging.getLogger(__name__)


def rechnung_fällig(eintrag, verlauf_liste, verlauf_vorjahr=None, heute=None):
    """Prueft, ob fuer diesen Eintrag heute abgerechnet werden soll."""
    if verlauf_vorjahr is None:
        verlauf_vorjahr = []
    abrechnungszyklus = validiere_positive_ganzzahl(
        eintrag.get("abrechnungszyklus", 1),
        "Abrechnungszyklus",
    )
    heute = heute or aktuelles_datum()

    # 1. Laufzeit-Ende prüfen
    laufzeit_ueberschritten = False
    ist_letzter_rechnungsmonat = False
    letzte_rechnung_grenze = eintrag.get("letzte_rechnung", "").strip()
    if letzte_rechnung_grenze:
        try:
            grenze = datetime.strptime(letzte_rechnung_grenze, "%Y-%m")
            if (heute.year, heute.month) > (grenze.year, grenze.month):
                laufzeit_ueberschritten = True
            ist_letzter_rechnungsmonat = (heute.year, heute.month) == (
                grenze.year,
                grenze.month,
            )
        except ValueError:
            pass  # Ignoriere ungültiges Format

    # 2. Wurde bereits abgerechnet?
    for liste in (verlauf_liste, verlauf_vorjahr):
        for eintrag_verlauf in liste:
            gleicher_kunde = _ist_gleicher_kunde(eintrag, eintrag_verlauf)
            gleicher_zeitraum = gleicher_kunde and (
                eintrag_verlauf.get("jahr"),
                eintrag_verlauf.get("monat"),
            ) == (heute.year, heute.month)
            status = eintrag_verlauf.get("versandstatus")
            status_unklar = status not in (
                None,
                VERSANDSTATUS_FAILED,
                VERSANDSTATUS_NO_INVOICE,
                VERSANDSTATUS_PENDING,
                VERSANDSTATUS_SENT,
                VERSANDSTATUS_WAITING_HOURS,
            )
            if gleicher_kunde and (status == VERSANDSTATUS_PENDING or status_unklar):
                logger.warning(
                    "%s: Versandstatus %s ist unklar. "
                    "Keine automatische Rechnungserstellung.",
                    eintrag.get("firma", "Unbekannter Kunde"),
                    status,
                )
                return False
            if gleicher_zeitraum and ist_abrechnung_abgeschlossen(eintrag_verlauf):
                return False  # Schon abgerechnet
            if gleicher_zeitraum and status == VERSANDSTATUS_WAITING_HOURS:
                logger.warning(
                    "%s: Stunden fehlen weiterhin. Abrechnung wird erneut geprueft.",
                    eintrag.get("firma", "Unbekannter Kunde"),
                )
            elif gleicher_kunde and status == VERSANDSTATUS_WAITING_HOURS:
                logger.warning(
                    "%s: Alter Status waiting_hours muss als no_invoice "
                    "abgeschlossen werden. Keine automatische Rechnungserstellung.",
                    eintrag.get("firma", "Unbekannter Kunde"),
                )
                return False
            if gleicher_zeitraum and status == VERSANDSTATUS_FAILED:
                logger.warning(
                    "%s: Vorheriger Mailversand ist fehlgeschlagen. "
                    "Versand wird erneut versucht.",
                    eintrag.get("firma", "Unbekannter Kunde"),
                )
            elif gleicher_kunde and status == VERSANDSTATUS_FAILED:
                logger.warning(
                    "%s: Fehlgeschlagener Versand aus einem frueheren "
                    "Rechnungsmonat muss manuell geprueft werden. "
                    "Keine automatische Rechnungserstellung.",
                    eintrag.get("firma", "Unbekannter Kunde"),
                )
                return False

    if laufzeit_ueberschritten:
        return False

    # 3. Einmalige Rechnung?
    if eintrag.get("einmalig") is True:
        for liste in (verlauf_liste, verlauf_vorjahr):
            for eintrag_verlauf in liste:
                if _ist_gleicher_kunde(
                    eintrag, eintrag_verlauf
                ) and ist_abrechnung_abgeschlossen(eintrag_verlauf):
                    return False
        return (
            True  # Einmalige Rechnung war noch nie im Verlauf (auch nicht im Vorjahr)
        )

    if ist_letzter_rechnungsmonat:
        return True

    # 4. Letzte reguläre Abrechnung bestimmen
    letzte_abrechnung = None
    letzter_eintrag = None

    # Erst im aktuellen Jahr suchen, dann (falls nötig) im Vorjahr
    suchlisten = [verlauf_liste]
    if abrechnungszyklus > 1 and verlauf_vorjahr:
        suchlisten.append(verlauf_vorjahr)

    for liste in suchlisten:
        for ev in reversed(liste):
            if _ist_gleicher_kunde(eintrag, ev) and ist_abrechnung_abgeschlossen(ev):
                letzter_eintrag = ev
                jahr_v = ev.get("jahr")
                monat_v = ev.get("monat")
                if isinstance(jahr_v, int) and isinstance(monat_v, int):
                    letzte_abrechnung = f"{jahr_v}-{monat_v:02d}"
                break
        if letzter_eintrag:
            break

    # 5. Prüfe Zyklus-Wechsel
    if letzter_eintrag:
        vorheriger_zyklus = letzter_eintrag.get("zyklus_monate")
        if vorheriger_zyklus and (
            validiere_positive_ganzzahl(
                vorheriger_zyklus,
                "Vorheriger Abrechnungszyklus",
            )
            != abrechnungszyklus
        ):
            logger.info(
                "Zykluswechsel erkannt (%s -> %s) - neue Rechnung wird erzeugt.",
                vorheriger_zyklus,
                abrechnungszyklus,
            )
            return True

    # 6. Prüfe Differenz in Monaten
    if letzte_abrechnung:
        try:
            letzte_dt = datetime.strptime(letzte_abrechnung, "%Y-%m")
            diff_monate = (
                (heute.year - letzte_dt.year) * 12 + heute.month - letzte_dt.month
            )
            return diff_monate >= abrechnungszyklus
        except ValueError:
            return True  # Vorsichtshalber trotzdem abrechnen

    return True  # Noch nie abgerechnet


def _ist_gleicher_kunde(kunde: dict, verlaufseintrag: dict) -> bool:
    """Vergleicht Kunden-ID und rueckwaertskompatibel Firma sowie Name."""
    kunden_id = verlaufseintrag.get("kunden_id")
    if kunden_id:
        return kunden_id == kunde.get("id")
    return (
        verlaufseintrag.get("firma", "").strip().lower()
        == kunde.get("firma", "").strip().lower()
        and verlaufseintrag.get("name", "").strip().lower()
        == kunde.get("name", "").strip().lower()
    )
