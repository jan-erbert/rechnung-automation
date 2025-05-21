# 🧾 Rechnung-Automation

Ein flexibles Python-Tool zur automatisierten Erstellung und Versendung von PDF-Rechnungen per E-Mail – ideal für Freelancer und Kleinunternehmer.

## ✅ Funktionen

- 📄 Erstellung von PDF-Rechnungen aus HTML-Vorlagen
- 📧 Versand der Rechnungen per E-Mail mit BCC-Unterstützung
- 📁 Automatische Archivierung der PDFs an frei definierbare Pfade
- 🧠 Automatische Generierung von Rechnungsnummer, Abrechnungszeitraum, Fälligkeitsdatum
- 🕒 Unterstützung stundenbasierter Abrechnung (mit Monatsdateien)
- 🔁 Zyklische oder einmalige Abrechnung, je nach Kundeneinstellung
- 💡 Rückfrage bei fehlenden Daten, z. B. Stunden oder fehlerhaften Dateien
- 🖼 Anpassbares HTML/CSS-Design (Logo, Farben, Templates)
- ⚙️ Interaktive Einrichtung über install.ps1/install.sh/install.bat
- 🖱 Desktop-Verknüpfung für Windows-Nutzer wird automatisch erstellt

---

## 🚀 Schnellstart

### 1. Voraussetzungen

- Python 3.10 oder neuer
- wkhtmltopdf (liegt im Ordner `bin/` oder muss installiert sein)
- Internetzugang für den Mailversand (SMTP)

### 2. Einrichtung (abhängig vom Betriebssystem)

```powershell
# Windows PowerShell
./install.ps1

# Linux/macOS Terminal
./install.sh

# Windows CMD (Alternativ)
install.bat
```

> Erstellt `.venv`, installiert Abhängigkeiten, fragt zentrale Konfigurationsdaten ab und erstellt Startskripte + Desktop-Verknüpfung.

---

## ⚙️ Konfiguration

### `environment.env`

```env
MAIL_SERVER=smtp.example.com
MAIL_PORT=587
MAIL_USER=deine@email.de
MAIL_PASS=dein_passwort
MAIL_BCC=optional@email.de
```

### `daten.json`

Beinhaltet die Kunden-, Leistungs- und Abrechnungsdaten. Kann interaktiv über `tools/kunden_anlegen.py` erweitert werden.

```jsonc
[
  {
    "name": "Herr Mustermann",
    "firma": "Musterfirma GmbH",
    "email": "kunde@example.com",
    "strasse": "Musterstraße 1",
    "plz": "12345",
    "ort": "Musterstadt",
    "webseite": "www.musterfirma.de",
    "rechnungsnummer": "MF",
    "faelligkeit": "14",
    "abrechnungszyklus": 3,
    "letzte_rechnung": "2024-12",
    "hauptleistung": {
      "beschreibung": "Individuelle Beratung",
      "einheit": "Monat",
      "betrag": "65,00"
    },
    "weitere_leistungen": [
      { "beschreibung": "Zusätzliche E-Mail-Adressen", "preis": "9,99" },
      { "beschreibung": "Support inklusive", "preis": "Inklusive" }
    ],
    "archiv_pfad": "C:/Users/DEINNAME/Desktop/test Archiv"
  }
]
```

---

## 📤 Rechnung erzeugen & versenden

```bash
python main.py
```

> Erzeugt PDF-Rechnungen, versendet sie per Mail, archiviert sie, aktualisiert den Verlauf und bietet Löschoption für einmalige Kunden.

---

## 📁 Projektstruktur

```
rechnung-automation/
├── .gitignore                     # Ausschlüsse (z. B. .venv/, data/)
├── .venv/                         # Virtuelle Umgebung (nicht ins Git)
├── bin/
│   ├── wkhtmltopdf.exe            # PDF-Konverter für Windows
│   └── gtk/                       # Zusatzbibliotheken für wkhtmltopdf
├── data/
│   ├── daten.json                 # Kunden- und Rechnungsdaten
│   ├── environment.env            # SMTP-Zugangsdaten
│   ├── konfiguration.json         # Absender-, Steuer- und Bankdaten
│   └── verlauf-20XX.json          # Automatisch gepflegter Rechnungsverlauf
├── img/
│   └── logo.png                   # Optionales Logo für PDF und Mail
├── install/
│   ├── install.ps1                # Einrichtungsskript (PowerShell)
│   ├── install.sh                 # Einrichtungsskript (Linux/macOS)
│   ├── install.bat                # Einrichtungsskript (CMD Windows)
├── licenses/
│   ├── gpl-2.0.txt
│   ├── LGPL-3.0.txt
│   └── wkhtmltopdf_lizenzhinweis.txt
├── sample/
│   ├── daten.sample.jsonc
│   ├── environment.sample.env
│   ├── konfiguration.sample.json
│   ├── mail_template.sample.html
│   └── rechnung_template.sample.html
├── src/
│   └── main.py                    # Hauptskript zur Rechnungserstellung
├── stunden/                       # Stundenlisten pro Monat
├── tools/
│   ├── kunden_anlegen.py         # Interaktive Kundenerfassung
│   ├── update_tool.py            # Tool zum GitHub-Update
├── vorlagen/
│   ├── mail_template.html         # HTML-Vorlage für E-Mail
│   └── rechnung_template.html     # HTML-Vorlage für PDF-Rechnung
├── rechnung_generieren.ps1        # Schnellstart-Skript (optional)
├── rechnung_generieren.bat        # Schnellstart-Skript (optional)
├── version.py                     # Zentrale Versionsnummer
├── CHANGELOG.md
├── LICENSE.md
└── README.md
```

---

## 🧩 Templates

- `vorlagen/rechnung_template.html` → PDF-Design
- `vorlagen/mail_template.html` → E-Mail-Text (HTML)
- `img/logo.png` → Logo für die PDF

Bearbeite die Templates direkt, um Texte, Farben oder Formatierungen zu ändern.

---

## 🛠 Erweiterungsmöglichkeiten

- Rechnung mit Steuersatz und Mehrwertsteuer
- Automatische Verarbeitung von Zahlungseingängen
- Integration mit Zeiterfassung oder CRM

---

## 🔄 Update

Verwende `tools/update_tool.py` um die aktuellste Version von GitHub zu laden.

```bash
python tools/update_tool.py
```

> Persönliche Daten bleiben erhalten – nur Systemdateien werden aktualisiert.

---

## 📋 Changelog

Siehe [CHANGELOG.md](CHANGELOG.md)

---

## ⚖️ Lizenz

MIT License – frei nutzbar, kommerziell verwendbar, keine Gewährleistung.