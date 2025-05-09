# 🧾 Rechnung-Automation

Ein flexibles Python-Tool zur automatisierten Erstellung und Versendung von PDF-Rechnungen per E-Mail – ideal für Freelancer und Kleinunternehmer.

## ✅ Funktionen

- 📄 Erstellung von PDF-Rechnungen auf Basis von HTML-Vorlagen
- 📧 Versand der Rechnung per E-Mail (SMTP) mit BCC-Unterstützung
- 📁 Archivierung der Rechnung an einem frei definierbaren Pfad
- 🧠 Automatische Berechnung von Rechnungsnummer und Fälligkeitsdatum
- 🌐 Unterstützung deutscher Monatsnamen durch `locale`
- 🖼 Anpassbares Design: Logo, Farben, Texte, Templates

---

## 🚀 Schnellstart

### 1. Voraussetzungen

- Python 3.10 oder neuer
- wkhtmltopdf (liegt im Projekt unter `bin/`)
- Internetverbindung zum Versenden von Mails

### 2. Setup (automatisch)

```powershell
./install.ps1
```

> Installiert alle Abhängigkeiten, erstellt `.venv`, `environment.env`, `daten.json` und prüft wkhtmltopdf.

### 3. Konfiguration

#### `environment.env`

```env
MAIL_SERVER=smtp.example.com
MAIL_PORT=587
MAIL_USER=deine@email.de
MAIL_PASS=passwort
MAIL_BCC=optional@adresse.de
```

#### `daten.json`

```jsonc
[
  {
    "name": "Max Mustermann",
    "firma": "Beispiel GmbH",
    "email": "max@example.com",
    "strasse": "Beispielstraße 1",
    "plz": "12345",
    "ort": "Beispielstadt",
    "webseite": "www.beispiel.de",
    "betrag": "19,99",
    "rechnungsnummer": "R",
    "faelligkeit": 14,
    "weitere_leistungen": [
      { "beschreibung": "Support", "preis": "Inklusive" },
      { "beschreibung": "Extra-Dienstleistung", "preis": "10,00" }
    ],
    "archiv_pfad": "C:/Users/DeinBenutzer/Desktop/Archiv"
  }
]
```

---

## 📤 Rechnung erzeugen & versenden

### Option 1: PowerShell
```powershell
./rechnung_generieren.ps1
```

### Option 2: Batch (Windows)
```bat
rechnung_generieren.bat
```

### Option 3: Direktes Python-Skript
```bash
python mail_versenden.py
```

---

## 🧩 Templates

- E-Mail-HTML: `vorlagen/mail_template.html`
- PDF-Vorlage: `vorlagen/rechnung_template.html`
- Logo: `img/logo.png`

Vorschau-Dateien befinden sich im `sample/`-Ordner.

---

## 📁 Projektstruktur

```
rechnung-automation/
├── .venv/                  # Virtuelle Umgebung
├── bin/                    # wkhtmltopdf-Tool (für PDF-Erzeugung, ggf. installation erforderlich)
├── doc/                    # Dokumentation
│   ├── CHANGELOG.md
│   └── README.md
├── img/                    # Bildmaterial (z. B. Logo)
├── sample/                 # Beispieldateien
├── vorlagen/               # HTML-Vorlagen
├── daten.json              # Rechnungsdaten
├── environment.env         # SMTP-Zugang
├── mail_versenden.py       # Hauptskript
├── install.ps1             # Auto-Setup-Skript
├── requirements.txt        # Python-Abhängigkeiten
└── .gitignore              # Git-Ausnahmen
```

---

## 📋 Changelog

Änderungen siehe [CHANGELOG.md](doc/CHANGELOG.md)

## ⚖️ Lizenz

MIT License – frei nutzbar, ohne Garantie oder Support.