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

---

## 🚀 Schnellstart

### 1. Voraussetzungen

- Python 3.10 oder neuer
- wkhtmltopdf (liegt im Ordner `bin/` oder muss installiert sein)
- Internetzugang für den Mailversand (SMTP)

### 2. Einrichtung

```powershell
./install.ps1
```

> Erstellt `.venv`, installiert Abhängigkeiten, kopiert Beispieldateien (`daten.json`, `environment.env`, Vorlagen)

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

Beispielstruktur:

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

> Weitere Konfiguration siehe `daten.sample.jsonc` im `sample/`-Ordner.

---

## 📤 Rechnung erzeugen & versenden

### PowerShell (empfohlen):

```powershell
python mail_versenden.py
```

> Erzeugt die PDF, versendet sie per Mail, archiviert sie und protokolliert den Verlauf.

---

## 📁 Projektstruktur

```
rechnung-automation/
├── .venv/                     # Virtuelle Umgebung
├── bin/                      # wkhtmltopdf.exe
├── doc/
│   ├── CHANGELOG.md
│   └── README.md
├── img/
│   └── logo.png             # optional
├── sample/
│   ├── daten.sample.jsonc
│   ├── environment.sample.env
│   ├── mail_template.sample.html
│   └── rechnung_template.sample.html
├── vorlagen/
│   ├── mail_template.html
│   └── rechnung_template.html
├── stunden/                  # Stundenlisten pro Monat (stunden_2025_04.json etc.)
├── daten.json
├── environment.env
├── verlauf-2025.json         # Verlauf automatisch erstellt
├── mail_versenden.py         # Hauptskript
├── install.ps1               # Einrichtungsskript (Windows)
├── requirements.txt
└── .gitignore
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

## 📋 Changelog

Siehe [doc/CHANGELOG.md](doc/CHANGELOG.md)

---

## ⚖️ Lizenz

MIT License – frei nutzbar, kommerziell verwendbar, keine Gewährleistung.