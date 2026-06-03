from datetime import datetime


def rechnung_fällig(eintrag, verlauf_liste, verlauf_vorjahr=None):
    """Prueft, ob fuer diesen Eintrag heute abgerechnet werden soll."""
    if verlauf_vorjahr is None:
        verlauf_vorjahr = []
    abrechnungszyklus = int(eintrag.get("abrechnungszyklus", 1))
    heute = datetime.today()
    aktueller_schlüssel = heute.strftime("%Y-%m")

    # 1. Laufzeit-Ende prüfen
    letzte_rechnung_grenze = eintrag.get("letzte_rechnung", "").strip()
    if letzte_rechnung_grenze:
        try:
            grenze = datetime.strptime(letzte_rechnung_grenze, "%Y-%m")
            if heute > grenze:
                return False  # Laufzeit überschritten
        except ValueError:
            pass  # Ignoriere ungültiges Format

    # 2. Wurde bereits abgerechnet?
    firma = eintrag.get("firma", "").strip().lower()
    name = eintrag.get("name", "").strip().lower()
    empfaenger_id = f"{firma}__{name}__{aktueller_schlüssel}"

    for liste in (verlauf_liste, verlauf_vorjahr):
        for eintrag_verlauf in liste:
            if eintrag_verlauf.get("id") == empfaenger_id:
                return False  # Schon abgerechnet

    # 3. Einmalige Rechnung?
    if eintrag.get("einmalig") is True:
        for liste in (verlauf_liste, verlauf_vorjahr):
            for eintrag_verlauf in liste:
                if (
                    eintrag_verlauf.get("firma", "").strip().lower() == firma
                    and eintrag_verlauf.get("name", "").strip().lower() == name
                ):
                    return False
        return (
            True  # Einmalige Rechnung war noch nie im Verlauf (auch nicht im Vorjahr)
        )

    # 4. Letzte reguläre Abrechnung bestimmen
    letzte_abrechnung = None
    letzter_eintrag = None

    # Erst im aktuellen Jahr suchen, dann (falls nötig) im Vorjahr
    suchlisten = [verlauf_liste]
    if abrechnungszyklus > 1 and verlauf_vorjahr:
        suchlisten.append(verlauf_vorjahr)

    for liste in suchlisten:
        for ev in reversed(liste):
            if (
                ev.get("firma", "").strip().lower() == firma
                and ev.get("name", "").strip().lower() == name
            ):
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
        if vorheriger_zyklus and int(vorheriger_zyklus) != abrechnungszyklus:
            print(
                f"🔁 Zykluswechsel erkannt ({vorheriger_zyklus} → {abrechnungszyklus}) – "
                "neue Rechnung wird erzeugt."
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
