#src/main.py
import json
import smtplib
import os
import pdfkit
import base64
import locale
locale.setlocale(locale.LC_TIME, 'de_DE.UTF-8')
from jinja2 import Environment, FileSystemLoader
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from dotenv import load_dotenv
from datetime import datetime, timedelta
from io import BytesIO
from pathlib import Path
from dateutil.relativedelta import relativedelta

# 📦 Abhängigkeiten importieren
BASE_DIR = Path(__file__).resolve().parent.parent # .../rechnung-automation/
DATA_DIR = BASE_DIR / "data"
STUNDEN_DIR = BASE_DIR / "stunden"
VORLAGEN_DIR = BASE_DIR / "vorlagen"
IMG_DIR = BASE_DIR / "img"
BIN_DIR = BASE_DIR / "bin"
BACKUP_DIR = BASE_DIR / "backup"

# 🔐 Lade Konfiguration aus environment.env
load_dotenv(BASE_DIR / "data" / "environment.env")
with open(DATA_DIR / "daten.json", 'r', encoding='utf-8') as f:
    daten = json.load(f)

# 📧 E-Mail Konfiguration
MAIL_SERVER = os.getenv("MAIL_SERVER")
MAIL_PORT = int(os.getenv("MAIL_PORT"))
MAIL_USER = os.getenv("MAIL_USER")
MAIL_PASS = os.getenv("MAIL_PASS")

# 📄 Konfiguration JSON-Datei laden
def lade_konfiguration(pfad: Path = BASE_DIR / "data" / "konfiguration.json") -> dict:
    if not os.path.exists(pfad):
        raise FileNotFoundError(f"Konfigurationsdatei '{pfad}' nicht gefunden.")

    with open(pfad, "r", encoding="utf-8") as f:
        config = json.load(f)

    # Pflichtfelder prüfen
    pflichtfelder = [
        ("absender", "name"),
        ("absender", "firma"),
        ("absender", "email"),
        ("bank", "iban"),
        ("bank", "kontoinhaber"),
        ("finanzen", "kleinunternehmer")
    ]

    for bereich, feld in pflichtfelder:
        if feld not in config.get(bereich, {}):
            raise ValueError(f"Pflichtfeld fehlt: '{bereich}.{feld}'")

    # Prüfen: wenn kein Kleinunternehmer → Mehrwertsteuersatz muss gesetzt sein
    if not config["finanzen"].get("kleinunternehmer", False):
        if "mehrwertsteuer_prozent" not in config["finanzen"]:
            raise ValueError("Mehrwertsteuersatz fehlt bei Nicht-Kleinunternehmern.")

    return config

# 📥 Konfiguration laden
konfig = lade_konfiguration()

absender = konfig["absender"]
bank = konfig["bank"]
finanzen = konfig["finanzen"]

# 📁 Verlaufsdatei für das aktuelle Jahr laden oder neu anlegen (mit Fallback)
def lade_verlauf_datei(dateiname, jahr):
    if not os.path.exists(dateiname):
        print(f"ℹ️ Keine Verlaufsdatei vorhanden. Es wird eine neue Datei erstellt.")
        return []

    try:
        with open(dateiname, 'r', encoding='utf-8') as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        print(f"\n❌ Fehler beim Laden der Verlaufsdatei '{dateiname}':\n{e}")
        print("‼️ Die Datei scheint ungültiges JSON zu enthalten.")

        while True:
            entscheidung = input("Möchtest du die fehlerhafte Datei überschreiben? (y/n): ").strip().lower()
            if entscheidung == "y":
                backup_entscheidung = input("Willst du vorher eine Backup-Datei anlegen? (y/n): ").strip().lower()
                if backup_entscheidung == "y":
                    backup_path = BACKUP_DIR / f"verlauf-{jahr}_backup.json"
                    os.makedirs(backup_path.parent, exist_ok=True)
                    try:
                        os.rename(dateiname, backup_path)
                        print(f"🛡️ Sicherung gespeichert unter: {backup_path}")
                    except Exception as err:
                        print(f"⚠️ Backup konnte nicht erstellt werden: {err}")
                        print("🚫 Abbruch zur Sicherheit.")
                        exit(1)
                else:
                    print("⚠️ Kein Backup erstellt.")

                print("🆕 Leere Datei wird angelegt.")
                return []
            elif entscheidung == "n":
                print("🚫 Vorgang abgebrochen.")
                exit(1)
            else:
                print("Bitte y oder n eingeben.")


MAIL_BCC = konfig.get("mail", {}).get("bcc") or None

def berechne_stundenleistung(firma: str, zyklus: int, stundensatz: float):
    heute = datetime.today()
    stunden_total = 0.0
    monate = []

    firma_key = firma.strip().lower()

    for i in range(zyklus):
        monat_dt = heute - relativedelta(months=i+1)
        monat = monat_dt.month
        jahr = monat_dt.year
        dateiname = STUNDEN_DIR / f"stunden_{jahr}_{monat:02d}.json"

        eintrag_gefunden = False

        if os.path.exists(dateiname):
            try:
                with open(dateiname, 'r', encoding='utf-8') as f:
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
            print(f"❓ Keine Stunden für '{firma}' im Monat {monat_dt.strftime('%B %Y')} gefunden.")
            eingabe = input(f"Bitte Stundenanzahl manuell eingeben (Enter für 0): ").strip()
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
        "zeitraum": zeitraum
    }

# ⏳ Verlauf laden
jahr = datetime.today().year
verlauf_dateiname = BASE_DIR / "data" / f"verlauf-{jahr}.json"
rechnungsverlauf = lade_verlauf_datei(verlauf_dateiname, jahr)


def rechnung_fällig(eintrag, verlauf_liste):
    """Prüft, ob für diesen Eintrag heute abgerechnet werden soll."""
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

    for eintrag_verlauf in rechnungsverlauf:
        if eintrag_verlauf.get("id") == empfaenger_id:
            return False  # Schon abgerechnet

    # 3. Einmalige Rechnung?
    if eintrag.get("einmalig") is True:
        # Wurde schon abgerechnet?
        for eintrag_verlauf in verlauf_liste:
            if eintrag_verlauf.get("firma", "").strip().lower() == firma and \
            eintrag_verlauf.get("name", "").strip().lower() == name:
                return False  # Einmalige Rechnung wurde bereits gestellt
        return True  # Noch nie gestellt → jetzt abrechnen

    # 4. Prüfe, ob das aktuelle Datum auf den Zyklus passt
    letzte_abrechnung = None
    for eintrag_verlauf in sorted(verlauf_liste, key=lambda e: (e.get("jahr", 0), e.get("monat", 0))):
        if eintrag_verlauf.get("firma", "").strip().lower() == firma and \
        eintrag_verlauf.get("name", "").strip().lower() == name:
            # Kombiniere Jahr und Monat zu einem "YYYY-MM"-String
            jahr_v = eintrag_verlauf.get("jahr")
            monat_v = eintrag_verlauf.get("monat")
            if isinstance(jahr_v, int) and isinstance(monat_v, int):
                letzte_abrechnung = f"{jahr_v}-{monat_v:02d}"

    if letzte_abrechnung:
        try:
            letzte_dt = datetime.strptime(letzte_abrechnung, "%Y-%m")
            diff_monate = (heute.year - letzte_dt.year) * 12 + heute.month - letzte_dt.month
            return diff_monate >= abrechnungszyklus
        except ValueError:
            return True  # Fehlerhafte Daten => lieber abrechnen
    else:
        return True  # Noch nie abgerechnet

# 📩 Jinja2-Umgebung und Template laden
env = Environment(loader=FileSystemLoader(VORLAGEN_DIR))
template = env.get_template('mail_template.html')
template_pdf = env.get_template('rechnung_template.html')

# ✉ Mail vorbereiten und versenden
for eintrag in daten:
    # 🔁 Kunden überspringen, wenn "aktiv": false gesetzt ist
    if eintrag.get("aktiv") is False:
        print(f"⏭️  {eintrag['firma']}: Kunde ist deaktiviert – keine Abrechnung.")
        continue
    if not rechnung_fällig(eintrag, rechnungsverlauf):
        print(f"⏭️  {eintrag['firma']}: Keine Abrechnung fällig.")
        continue

    heute = datetime.today()

    # Rechnungsdatum automatisch setzen, wenn nicht vorhanden
    rechnungsdatum = eintrag.get('rechnungsdatum')
    if not rechnungsdatum:
        rechnungsdatum = heute.strftime('%d.%m.%Y')

    # Monat und Jahr für Text wie "April 2025"
    monat_jahr = heute.strftime('%B %Y')  # auf Deutsch ggf. locale setzen

    # Fälligkeitsdatum berechnen
    faelligkeit_stage = eintrag.get('faelligkeit', 14)
    try:
        faelligkeit_stage = int(faelligkeit_stage)
    except ValueError:
        faelligkeit_stage = 14

    rechnungsdatum_obj = datetime.strptime(rechnungsdatum, '%d.%m.%Y')
    faelligkeit_datum = (rechnungsdatum_obj + timedelta(days=faelligkeit_stage)).strftime('%d.%m.%Y')
    hauptleistung = eintrag.get("hauptleistung", {})

    # Rechnungsnummer automatisch zusammenbauen
    prefix = eintrag.get('rechnungsnummer', '').strip()
    auto_rechnungsnummer = heute.strftime('%m-%Y')
    if prefix:
        rechnungsnummer = f"{prefix}-{auto_rechnungsnummer}"
    else:
        rechnungsnummer = auto_rechnungsnummer

    abrechnungszyklus = int(eintrag.get("abrechnungszyklus", 1))
    try:
        grundbetrag = float(eintrag.get("betrag", "0").replace(",", "."))
    except ValueError:
        grundbetrag = 0.0

    # 💼 Hauptleistung zur Liste hinzufügen
    leistungs_liste = []

    
    beschreibung = hauptleistung.get("beschreibung", "Leistung")
    einheit = hauptleistung.get("einheit", "Monat").strip().lower()
    betrag_str = hauptleistung.get("betrag", "0").replace(",", ".").strip()

    try:
        betrag = float(betrag_str)
    except ValueError:
        betrag = 0.0

    if einheit == "stunde":
        # 🕒 Stundenbasiert: Stunden einlesen + multiplizieren
        stundeninfo = berechne_stundenleistung(eintrag.get("firma", ""), abrechnungszyklus, betrag)
        
        if stundeninfo["stunden"] == 0:
            print(f"⏭️ Keine Stunden für {eintrag['firma']} – es wird keine Rechnung verschickt, aber der Verlauf wird aktualisiert.")
            rechnungsverlauf.append({
                "firma": eintrag["firma"],
                "name": eintrag["name"],
                "monat": heute.month,
                "jahr": heute.year,
                "rechnungsnummer": rechnungsnummer,
                "rechnungsdatum": rechnungsdatum,
                "betrag": "0.00",
                "id": f"{eintrag['firma'].lower().strip()}__{eintrag['name'].lower().strip()}__{heute.strftime('%Y-%m')}"
            })
            with open(verlauf_dateiname, 'w', encoding='utf-8') as verlauf_file:
                json.dump(rechnungsverlauf, verlauf_file, indent=2, ensure_ascii=False)
            print("📝 Verlauf aktualisiert.")
            continue

        betrag = stundeninfo["gesamtbetrag"]
        gesamtpreis = betrag  # Direkt setzen, da es keine Multiplikation durch Zyklus gibt

        beschreibung = f"{stundeninfo['stunden']:.1f} Stunden × {stundeninfo['stundensatz']:.2f} EUR"
        leistungs_liste.append({
            "beschreibung": beschreibung,
            "preis": f"{betrag:.2f}".replace(".", ",") + " EUR"
        })

    elif einheit == "pauschal":
        # 💰 Pauschalbetrag → kein Multiplizieren
        gesamtpreis = betrag
        leistungs_liste.append({
            "beschreibung": f"{beschreibung} (pauschal)",
            "preis": f"{betrag:.2f}".replace(".", ",") + " EUR"
        })
        
    else:
        # 📆 Standard: monatlich, multiplizieren mit Zyklus
        gesamtpreis = betrag * abrechnungszyklus
        zeitraum_text = "1 Monat" if abrechnungszyklus == 1 else f"{abrechnungszyklus} Monate"
        leistungs_liste.append({
            "beschreibung": f"{beschreibung} für {zeitraum_text} ({eintrag.get('webseite', '')})",
            "preis": f"{gesamtpreis:.2f}".replace(".", ",") + " EUR"
        })
    # ➕ Zusätzliche Leistungen ergänzen (für alle Einheiten)
    weitere = eintrag.get("weitere_leistungen", [])
    for zusatz in weitere:
        beschreibung = zusatz.get("beschreibung", "Zusatzleistung")
        preis_str = zusatz.get("preis", "").strip()

        try:
            preis_float = float(preis_str.replace(",", "."))
            if einheit == "pauschal":
                # Keine Multiplikation, keine Zusatzzeile
                preis_text = f"{preis_float:.2f}".replace(".", ",") + " EUR"
                zusatz_text = ""
                betrag_gesamt = preis_float
            else:
                betrag_gesamt = preis_float * abrechnungszyklus
                zusatz_text = f"({preis_float:.2f}".replace(".", ",") + f" EUR × {abrechnungszyklus} Monate)"
                preis_text = f"{betrag_gesamt:.2f}".replace(".", ",") + " EUR"
        except ValueError:
            zusatz_text = ""
            preis_text = preis_str  # z. B. „Inklusive“
            betrag_gesamt = 0.0

        leistungs_liste.append({
            "beschreibung": beschreibung + (f"<br><small>{zusatz_text}</small>" if zusatz_text else ""),
            "preis": preis_text
        })

        # Summe aufrechnen, nur wenn numerisch
        if isinstance(betrag_gesamt, float) and betrag_gesamt > 0:
            betrag_gesamt = preis_float * abrechnungszyklus
            gesamtpreis += betrag_gesamt

    # Berechnung von Steuerbetrag, MwSt-Hinweis und Gesamtpreis
    if finanzen["kleinunternehmer"]:
        steuerbetrag = 0
        mwst_hinweis = "Gemäß § 19 UStG wird keine Umsatzsteuer berechnet."
        gesamtpreis_mit_mwst = gesamtpreis  # Nettopreis = Bruttopreis
    else:
        steuerbetrag = round(gesamtpreis * finanzen["mehrwertsteuer_prozent"] / 100, 2)
        mwst_hinweis = f"zzgl. {finanzen['mehrwertsteuer_prozent']}% MwSt ({steuerbetrag:.2f} EUR)"
        gesamtpreis_mit_mwst = gesamtpreis + steuerbetrag

    gesamtpreis_str = f"{gesamtpreis_mit_mwst:.2f}".replace(".", ",")

    try:
        with open(IMG_DIR / "logo.png", "rb") as img_file:
            logo_base64 = base64.b64encode(img_file.read()).decode("utf-8")
    except FileNotFoundError:
        print("⚠️ Logo-Datei nicht gefunden. Logo wird in der Rechnung nicht angezeigt.")
        logo_base64 = ""

    # 📆 Abrechnungszeitraum (für alle Einheiten mit monatlichem Zyklus)
    abrechnungszeitraum = ""
    if abrechnungszyklus >= 1:
        zeitraum_start = heute.strftime("%B %Y")
        zeitraum_ende_dt = heute + relativedelta(months=abrechnungszyklus - 1)
        zeitraum_ende = zeitraum_ende_dt.strftime("%B %Y")
        abrechnungszeitraum = zeitraum_start if abrechnungszyklus == 1 else f"{zeitraum_start} – {zeitraum_ende}"


    # Kontextdaten vorbereiten
    context = {
        'name': eintrag['name'],
        'firma': eintrag['firma'],
        'email': eintrag['email'],
        'strasse': eintrag['strasse'],
        'betrag': f"{gesamtpreis:.2f}".replace(".", ","),
        'plz': eintrag['plz'],
        'ort': eintrag['ort'],
        'rechnungsnummer': rechnungsnummer,
        'rechnungsdatum': rechnungsdatum,
        'faelligkeit': faelligkeit_datum,
        'abrechnungszeitraum': abrechnungszeitraum if abrechnungszeitraum else "",
        'monat_jahr': monat_jahr,
        'leistungen': leistungs_liste,
        'gesamtpreis': gesamtpreis_str,
        'logo_base64': f"data:image/png;base64,{logo_base64}",
        'abrechnungszyklus': abrechnungszyklus,
        'absender': absender,
        'bank': bank,
        'finanzen': finanzen,
        'mwst_hinweis': mwst_hinweis,
        'steuerbetrag': f"{steuerbetrag:.2f}".replace(".", ","),
        'mwst_prozent': finanzen.get("mehrwertsteuer_prozent", 0),
        'brutto_betrag': f"{gesamtpreis_mit_mwst:.2f}".replace(".", ","),
        'netto_betrag': f"{gesamtpreis:.2f}".replace(".", ",")
    }

    # Ergänzung: Stundensatzhinweis unten anzeigen
    if einheit == "stunde":
        context["stundensatz_hinweis"] = f"(Stundensatz: {stundeninfo['stundensatz']:.2f} EUR pro Stunde)"

    mail_html = template.render(context)

    # PDF-Rechnung generieren mit pdfkit
    pdf_html = template_pdf.render(context)

    # Konfiguration mit Pfad zur wkhtmltopdf.exe (falls nicht im Systempfad)
    config = pdfkit.configuration(wkhtmltopdf=str(BIN_DIR / "wkhtmltopdf.exe"))

    # Optionen zur Qualitäts- und Formatkontrolle
    options = {
        'dpi': 300,
        'page-size': 'A4',
        'margin-top': '0mm',
        'margin-right': '0mm',
        'margin-bottom': '0mm',
        'margin-left': '0mm',
        'encoding': 'UTF-8',
        'enable-local-file-access': ''
    }

    # PDF erzeugen als Bytes
    pdf_bytes = pdfkit.from_string(pdf_html, False, configuration=config)

    # In BytesIO verpacken, damit wir es an die Mail anhängen können
    pdf_file = BytesIO(pdf_bytes)


    msg = MIMEMultipart()
    msg['From'] = MAIL_USER
    msg['To'] = eintrag['email']
    msg['Subject'] = f"Ihre Rechnung Nr. {rechnungsnummer} – {eintrag['firma']}"
    if MAIL_BCC:
        msg['Bcc'] = MAIL_BCC

    msg.attach(MIMEText(mail_html, 'html'))

    # PDF an E-Mail anhängen
    from email.mime.application import MIMEApplication
    # PDF-Dateiname aus Firmennamen erzeugen (klein, Leerzeichen zu "_")
    firma_slug = eintrag['firma'].lower().replace(" ", "_")
    anhang_name = f"Rechnung_{firma_slug}_{auto_rechnungsnummer}.pdf"
    pdf_part = MIMEApplication(pdf_file.read(), _subtype='pdf')
    pdf_part.add_header('Content-Disposition', 'attachment', filename=anhang_name)
    msg.attach(pdf_part)


    try:
        with smtplib.SMTP(MAIL_SERVER, MAIL_PORT) as server:
            server.starttls()
            server.login(MAIL_USER, MAIL_PASS)
            empfaenger_liste = [eintrag['email']]
            if MAIL_BCC:
                empfaenger_liste.append(MAIL_BCC)
            server.send_message(msg, from_addr=MAIL_USER, to_addrs=empfaenger_liste)
            print(f"✅ Mail an {eintrag['name']} ({eintrag['email']}) gesendet.")
            print("BCC:", MAIL_BCC)
            
            # ⏺️ Eintrag zum Rechnungsverlauf hinzufügen
            rechnungsverlauf.append({
                "firma": eintrag["firma"],
                "name": eintrag["name"],
                "monat": heute.month,
                "jahr": heute.year,
                "rechnungsnummer": rechnungsnummer,
                "rechnungsdatum": rechnungsdatum,
                "betrag": gesamtpreis_str.replace(",", "."),
                "id": f"{eintrag['firma'].lower().strip()}__{eintrag['name'].lower().strip()}__{heute.strftime('%Y-%m')}"
            })

            # Verlaufsdatei aktualisieren
            with open(verlauf_dateiname, 'w', encoding='utf-8') as verlauf_file:
                json.dump(rechnungsverlauf, verlauf_file, indent=2, ensure_ascii=False)
            print("📝 Verlauf aktualisiert.")

            # PDF zusätzlich archivieren, wenn Pfad vorhanden
            archiv_pfad = eintrag.get('archiv_pfad')
            if archiv_pfad:
                try:
                    archiv_pfad_path = Path(archiv_pfad)
                    archiv_datei = archiv_pfad_path / anhang_name
                    archiv_pfad_path.mkdir(parents=True, exist_ok=True)
                    with open(archiv_datei, "wb") as f:
                        f.write(pdf_bytes)
                    print(f"🗂️ Archiviert unter: {archiv_datei}")
                except Exception as e:
                    print(f"⚠️ Fehler beim Archivieren der PDF: {e}")

            # 🧹 Prüfen, ob der Kunde gelöscht werden soll
            loeschen_nach_letzter = False

            if eintrag.get("einmalig") is True:
                loeschen_nach_letzter = True
            elif eintrag.get("letzte_rechnung"):
                try:
                    letzte_erlaubte = datetime.strptime(eintrag["letzte_rechnung"], "%Y-%m")
                    if heute > letzte_erlaubte + relativedelta(months=1):
                        loeschen_nach_letzter = True
                except ValueError:
                    pass

            if loeschen_nach_letzter:
                print(f"\n🛑 Kunde '{eintrag['firma']}' ({eintrag['name']}) hat die letzte Rechnung erhalten.")
                entscheidung = input("❓ Möchtest du diesen Kunden jetzt aus daten.json löschen? (y/n): ").strip().lower()
                if entscheidung == "y":
                    daten = [k for k in daten if not (
                        k.get("firma", "").strip().lower() == eintrag["firma"].strip().lower() and
                        k.get("name", "").strip().lower() == eintrag["name"].strip().lower()
                    )]
                    with open(BASE_DIR / "data" / "daten.json", 'w', encoding='utf-8') as f:
                        json.dump(daten, f, indent=2, ensure_ascii=False)
                    print("🗑️ Kunde wurde aus daten.json entfernt.")
                else:
                    print("⚠️ Kunde bleibt weiterhin in der Kundendatei, wird jedoch übersprungen")
    
    except Exception as e:
        print(f"❌ Fehler beim Senden an {eintrag['email']}: {e}")

print("🏁 Alle Rechnungen wurden verarbeitet.")
print("🔚 Skript beendet...")