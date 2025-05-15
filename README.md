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

### `konfiguration.json`

Beinhaltet zentrale Daten wie Absenderadresse, Steuersatz, Bankverbindung und steuerliche Optionen.

```jsonc
{
  "absender": {
    "name": "Jan Erbert",
    "firma": "Web Development",
    "email": "mail@jan-erbert.de",
    "strasse": "Sponheimerstraße 4",
    "ort": "55543 Bad Kreuznach"
  },
  "bank": {
    "kontoinhaber": "Jan Erbert",
    "iban": "DE67 5605 0180 1200 4871 12",
    "bic": "MALADE51KRE",
    "bankname": "Sparkasse Rhein-Nahe"
  },
  "finanzen": {
    "kleinunternehmer": false,
    "mehrwertsteuer_prozent": 19
  }
}
```

Beispiel: Wenn kleinunternehmer = true, wird keine MwSt berechnet (Hinweis nach §19 UStG erscheint automatisch).

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
├── .venv/                        # Virtuelle Umgebung (nicht im Git)
├── bin/
│   └── wkhtmltopdf.exe          # PDF-Konverter für Windows (optional)
├── img/
│   └── logo.png                 # Optionales Logo für PDF und Mail
├── sample/
│   ├── daten.sample.jsonc
│   ├── environment.sample.env
│   ├── konfiguration.sample.json
│   ├── mail_template.sample.html
│   └── rechnung_template.sample.html
├── stunden/                     # Stundenlisten pro Monat (z. B. stunden_2025_04.json)
├── vorlagen/
│   ├── mail_template.html       # E-Mail-HTML-Vorlage
│   └── rechnung_template.html   # PDF-HTML-Vorlage
├── tools/
│   └── update_tool.py           # Separates Update-Skript (GitHub Releases)
├── daten.json                   # Kunden- und Rechnungsdaten
├── konfiguration.json           # Absender-, Steuer- und Bankdaten
├── environment.env              # SMTP-Zugangsdaten
├── verlauf-2025.json            # Automatisch gepflegter Rechnungsverlauf
├── version.py                   # Zentrale Versionsvariable
├── main.py                      # Hauptskript zur Rechnungserstellung
├── install.ps1                  # Einrichtungsskript (nur Windows)
├── requirements.txt             # Python-Abhängigkeiten
├── CHANGELOG.md
├── README.md
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

## 🔄 Update

Um die Software auf die neueste Version zu aktualisieren, kannst du das integrierte **Update-Tool** verwenden. Es prüft automatisch, ob ein neuer [GitHub Release](https://github.com/jan-erbert/rechnung-automation/releases) verfügbar ist, und installiert bei Bedarf die aktualisierten Dateien.

### 📥 Ausführen des Update-Tools

```bash
python tools/update_tool.py
```
Das Tool:

- vergleicht die lokale Version mit der neuesten GitHub-Version,
- lädt das Release-ZIP bei Bedarf herunter,
- ersetzt nur freigegebene Dateien (z. B. main.py, vorlagen/*.html, requirements.txt),
- lässt alle persönlichen Daten wie daten.json, stunden/, verlauf*.json unberührt.

⚠️ Voraussetzung: Eine funktionierende Internetverbindung und ein installierter Python-Paketmanager (requests, packaging – bereits in requirements.txt enthalten).

### 💡 Hinweis

Wenn du selbst Änderungen an Systemdateien vorgenommen hast, könnten diese beim Update überschrieben werden. Persönliche Konfigurations- und Abrechnungsdaten bleiben jedoch erhalten.

---

## 📋 Changelog

Siehe [doc/CHANGELOG.md](doc/CHANGELOG.md)

---

## ⚖️ Lizenz

MIT License – frei nutzbar, kommerziell verwendbar, keine Gewährleistung.