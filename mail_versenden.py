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

# 🔐 Lade Konfiguration aus environment.env
load_dotenv("environment.env")

MAIL_SERVER = os.getenv("MAIL_SERVER")
MAIL_PORT = int(os.getenv("MAIL_PORT"))
MAIL_USER = os.getenv("MAIL_USER")
MAIL_PASS = os.getenv("MAIL_PASS")
MAIL_BCC = os.getenv("MAIL_BCC")

# 📄 JSON-Datei laden
with open('daten.json', 'r', encoding='utf-8') as f:
    daten = json.load(f)

# 📩 Jinja2-Umgebung und Template laden
env = Environment(loader=FileSystemLoader('vorlagen'))
template = env.get_template('mail_template.html')
template_pdf = env.get_template('rechnung_template.html')

# ✉ Mail vorbereiten und versenden
for eintrag in daten:
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

    # Rechnungsnummer automatisch zusammenbauen
    prefix = eintrag.get('rechnungsnummer', '').strip()
    auto_rechnungsnummer = heute.strftime('%m-%Y')
    if prefix:
        rechnungsnummer = f"{prefix}-{auto_rechnungsnummer}"
    else:
        rechnungsnummer = auto_rechnungsnummer

    # Gesamtpreis berechnen
    grundbetrag = eintrag.get("betrag", "0").replace(",", ".")
    try:
        gesamtpreis = float(grundbetrag)
    except ValueError:
        gesamtpreis = 0.0

    leistungs_liste = [{
        "beschreibung": f"Monatliches Hosting für {eintrag['webseite']}",
        "preis": f"{eintrag['betrag']} EUR"
    }]

    for leistung in eintrag.get("weitere_leistungen", []):
        preis_raw = leistung.get("preis", "").replace(",", ".").replace(" EUR", "").strip()

        try:
            preis_float = float(preis_raw)
            gesamtpreis += preis_float
            preis_formatiert = f"{preis_raw.replace('.', ',')} EUR"
        except ValueError:
            preis_formatiert = preis_raw  # z. B. "Inklusive"

        leistungs_liste.append({
            "beschreibung": leistung.get("beschreibung", ""),
            "preis": preis_formatiert
        })

    gesamtpreis_str = f"{gesamtpreis:.2f}".replace(".", ",")

    with open("img/logo.png", "rb") as img_file:
        logo_base64 = base64.b64encode(img_file.read()).decode("utf-8")

    # von daten.json übergeben
    context = {
        'name': eintrag['name'],
        'firma': eintrag['firma'],
        'email': eintrag['email'],
        'strasse': eintrag['strasse'],
        'plz': eintrag['plz'],
        'ort': eintrag['ort'],
        'rechnungsnummer': rechnungsnummer,
        'rechnungsdatum': rechnungsdatum,
        'faelligkeit': faelligkeit_datum,
        'betrag': eintrag['betrag'],
        'monat_jahr': monat_jahr,
        'leistungen': leistungs_liste,
        'gesamtpreis': gesamtpreis_str,
        'logo_base64': f"data:image/png;base64,{logo_base64}"
    }

    mail_html = template.render(context)

    # PDF-Rechnung generieren mit pdfkit
    pdf_html = template_pdf.render(context)

    # Konfiguration mit Pfad zur wkhtmltopdf.exe (falls nicht im Systempfad)
    config = pdfkit.configuration(wkhtmltopdf='bin/wkhtmltopdf.exe')

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
            # PDF zusätzlich archivieren, wenn Pfad vorhanden
            archiv_pfad = eintrag.get('archiv_pfad')
            if archiv_pfad:
                try:
                    os.makedirs(archiv_pfad, exist_ok=True)
                    archiv_datei = os.path.join(archiv_pfad, anhang_name)
                    with open(archiv_datei, "wb") as f:
                        f.write(pdf_bytes)
                    print(f"🗂️ Archiviert unter: {archiv_datei}")
                except Exception as e:
                    print(f"⚠️ Fehler beim Archivieren der PDF: {e}")
        
    except Exception as e:
        print(f"❌ Fehler beim Senden an {eintrag['email']}: {e}")
