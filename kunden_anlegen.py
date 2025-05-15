import json
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent  # .../rechnung-automation/
DATA_DIR = BASE_DIR / "data"

def lade_kundendaten(dateiname=DATA_DIR / "daten.json"):
    if not os.path.exists(dateiname):
        print(f"📄 Datei '{dateiname}' nicht gefunden. Es wird eine neue erstellt.")
        return []

    try:
        with open(dateiname, 'r', encoding='utf-8') as f:
            daten = json.load(f)
            if not isinstance(daten, list):
                raise ValueError("daten.json ist kein Array.")
            return daten
    except (json.JSONDecodeError, ValueError) as e:
        print(f"\n❌ Fehler beim Laden von '{dateiname}': {e}")
        print("‼️ Die Datei scheint ungültig zu sein.")

        while True:
            entscheidung = input("Möchtest du die fehlerhafte Datei überschreiben? (y/n): ").strip().lower()
            if entscheidung == "y":
                backup_entscheidung = input("Willst du vorher ein Backup speichern? (y/n): ").strip().lower()
                if backup_entscheidung == "y":
                    os.makedirs("backup", exist_ok=True)
                    backup_pfad = BASE_DIR / "backup" / "daten_backup.json"
                    try:
                        os.rename(dateiname, backup_pfad)
                        print(f"🛡️ Backup gespeichert unter: {backup_pfad}")
                    except Exception as err:
                        print(f"⚠️ Backup fehlgeschlagen: {err}")
                        print("🚫 Abbruch zur Sicherheit.")
                        exit(1)
                else:
                    print("⚠️ Kein Backup erstellt.")

                print("🆕 Neue leere Datei wird erstellt.")
                with open(dateiname, 'w', encoding='utf-8') as f:
                    json.dump([], f, indent=2, ensure_ascii=False)
                return []
            elif entscheidung == "n":
                print("🚫 Vorgang abgebrochen.")
                exit(1)
            else:
                print("Bitte y oder n eingeben.")

def frage(prompt, optional=True):
    eingabe = input(prompt).strip()
    return eingabe if eingabe or not optional else None

def frage_mehrere_leistungen():
    leistungen = []
    while True:
        beschreibung = frage("📌 Zusätzliche Leistungen – Beschreibung (oder leer zum Abbrechen): ", optional=True)
        if not beschreibung:
            break
        preis = frage("💶 Preis (z. B. 9,99 oder Inklusive): ")
        leistungen.append({
            "beschreibung": beschreibung,
            "preis": preis
        })
        nochmal = input("➕ Weitere Leistung hinzufügen? (j/n): ").strip().lower()
        if nochmal != "j":
            break
    return leistungen if leistungen else None

def neuer_kunde():
    print("\n🧾 Neuen Kunden anlegen:\n")

    kunde = {
        "name": frage("👤 Name oder Ansprechpartner (z. B. Herr Müller): ", optional=False),
        "firma": frage("🏢 Firma: ", optional=False),
        "email": frage("📧 E-Mail: ", optional=False),
        "strasse": frage("📍 Straße und Hausnummer: ", optional=False),
        "plz": frage("📮 PLZ: ", optional=False),
        "ort": frage("🌆 Ort: ", optional=False),
        "webseite": frage("🔗 Webseite (optional, nur bei hosting relevant): ")
    }

    einmalig_input = input("🔁 Soll diese Rechnung nur einmalig erstellt werden? (y/n): ").strip().lower()
    einmalig = einmalig_input == "y"
    if einmalig:
        kunde["einmalig"] = True

    # 🔧 Hauptleistung
    print("\n💼 Hauptleistung eintragen:")
    beschreibung = frage("📝 Beschreibung der Hauptleistung (z. B. Hosting): ", optional=False)
    betrag = frage("💶 Betrag (z. B. 49,99): ", optional=False)
    if einmalig:
        einheit = "pauschal"
    else:
        einheit = frage("📏 Einheit der Abrechnung (Monat, Stunde, pauschal – Standard: Monat): ", optional=True)
        if not einheit:
            einheit = "Monat"

    kunde["hauptleistung"] = {
        "beschreibung": beschreibung,
        "einheit": einheit.strip().lower(),
        "betrag": betrag
    }

    if not einmalig:
        zyklus = frage("📆 Abrechnungszyklus in Monaten (z. B. 1 oder 6, Standard: 1): ")
        if zyklus:
            kunde["abrechnungszyklus"] = int(zyklus)

    # Optionalfelder
    optional_felder = {
        "rechnungsnummer": "📄 Rechnungsnummer-Präfix (optional): ",
        "rechnungsdatum": "📅 Rechnungsdatum (z. B. 01.05.2025, optional): ",
        "faelligkeit": "⏳ Fälligkeit in Tagen (z. B. 14, optional): ",
        "archiv_pfad": "📂 Archiv-Pfad für PDF (z. B. C:/Pfad/zum/Ordner): "
    }

    if not einmalig:
        optional_felder["letzte_rechnung"] = "📅 Letzte zu erstellende Rechnung (YYYY-MM, optional): "

    for key, prompt in optional_felder.items():
        wert = frage(prompt)
        if wert:
            kunde[key] = wert

    leistungen = frage_mehrere_leistungen()
    if leistungen:
        kunde["weitere_leistungen"] = leistungen

    aktiv_input = input("✅ Soll dieser Kunde ab jetzt aktiv sein? (y/n): ").strip().lower()
    if aktiv_input == "n":
        kunde["aktiv"] = False

    return kunde

def daten_speichern(kunde, dateipfad=DATA_DIR / "daten.json"):
    pfad = Path(dateipfad)
    if pfad.exists():
        try:
            daten = lade_kundendaten(dateipfad)
            if not isinstance(daten, list):
                raise ValueError
        except Exception:
            print("⚠️ Die bestehende daten.json ist ungültig oder kein Array. Erstelle neue Datei.")
            daten = []
    else:
        daten = []

    daten.append(kunde)

    with pfad.open("w", encoding="utf-8") as f:
        json.dump(daten, f, indent=2, ensure_ascii=False)
    print(f"\n✅ Kunde gespeichert in {pfad.resolve()}.")

if __name__ == "__main__":
    neuer = neuer_kunde()
    daten_speichern(neuer)
