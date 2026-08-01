# 🧾 Rechnung-Automation

Ein flexibles Python-Tool zur automatisierten Erstellung und Versendung von PDF-Rechnungen per E-Mail – ideal für Freelancer und Kleinunternehmer.

**Aktuelle stabile Version:** `1.3.6`

## ✅ Funktionen

- 📄 Erstellung von PDF-Rechnungen aus HTML-Vorlagen
- 📧 Versand der Rechnungen per E-Mail mit BCC-Unterstützung
- 📁 Automatische Archivierung der PDFs an frei definierbare Pfade
- 🧾 Logdateien pro Rechnungslauf, optional abschaltbar
- 🧠 Automatische Generierung von Rechnungsnummer, Abrechnungszeitraum, Fälligkeitsdatum
- 🕒 Unterstützung stundenbasierter Abrechnung (mit Monatsdateien)
- 🔁 Zyklische oder einmalige Abrechnung, je nach Kundeneinstellung
- 💡 Rückfrage bei fehlenden Daten, z. B. Stunden oder fehlerhaften Dateien
- 🖼 Anpassbares HTML/CSS-Design (Logo, Farben, Templates)
- 🩺 Setup-Check ohne Rechnungserzeugung
- ⚙️ Interaktive Einrichtung über `install/install.ps1` (Windows) oder `install/install.sh` (Linux)
- 🖱 Desktop-Verknüpfung für Windows-Nutzer wird automatisch erstellt

---

## 🚀 Schnellstart

### 1. Voraussetzungen

- Python 3.10 oder neuer
- Linux: WeasyPrint für die PDF-Erzeugung; je nach Distribution können zusätzlich Systembibliotheken und Fonts für HTML/CSS-Rendering nötig sein.
- Internetzugang für den Mailversand (SMTP)

### 2. Einrichtung (abhängig vom Betriebssystem)

```powershell
# Windows PowerShell
./install/install.ps1

# Linux Terminal
./install/install.sh
```

> Erstellt `.venv`, installiert Abhängigkeiten, fragt zentrale Konfigurationsdaten ab und erstellt unter Windows eine Desktop-Verknüpfung auf das PowerShell-Startskript. Die Installer validieren zentrale Eingaben und schreiben lokale Setup-Dateien sicher mit Sonderzeichen.

### Entwickler-Abhängigkeiten

Nur für Entwicklung und statische Prüfungen:

```bash
source .venv/bin/activate
python -m pip install -r install/requirements-dev.txt
```

Empfohlene Prüfungen:

```bash
python -m black --check .
python -m flake8 .
python -m pytest
```

---

## ⚙️ Konfiguration

### `config/settings.yaml`

Enthält nicht-sensitive Projekteinstellungen wie Pfade, Runtime-Optionen und die PDF-Engine-Auswahl. Zugangsdaten und Kundendaten gehören nicht in diese Datei.

```yaml
pdf:
  engine: weasyprint

design:
  pdf:
    accent_color: "#2f3c50"
    accent_text_color: "#ffffff"
    accent_muted_text_color: "#dbe2ea"
  mail:
    accent_color: "#1e3a70"
    link_color: "#007BFF"

branding:
  pdf_logo: logo.png
  mail_logo: null
  pdf_logo_height: 40
  mail_logo_height: 60
  header_title: null
  header_subtitle: null
```

Als PDF-Engine wird `weasyprint` verwendet.
Unter `design` können die Akzentfarben der PDF-Rechnung und der
Rechnungsmail als sechsstellige Hex-Farben angepasst werden. Die gezeigten
Werte entsprechen dem Standarddesign. `design.mail.accent_color` färbt den
Kopfbereich der Rechnungsmail; dessen Textfarben entsprechen den konfigurierten
PDF-Akzenttextfarben.

`branding.pdf_logo` und `branding.mail_logo` wählen optionale PNG- oder
JPEG-Logos aus. Relative Pfade werden innerhalb von `paths.image_dir` gesucht;
Unterordner wie `branding/mail-logo.png` sind möglich. Alternativ kann ein
absoluter Pfad angegeben werden. Mit `null` wird das jeweilige Logo deaktiviert.
Das Mail-Logo wird eingebettet und rechts im Kopf der Rechnungsmail angezeigt.
Mit `branding.header_title` und `branding.header_subtitle` können die beiden
Textzeilen im Kopf von PDF und Rechnungsmail unabhängig von den Absenderdaten
angepasst werden. Bei `null` werden weiterhin `absender.name` und
`absender.firma` verwendet.
`branding.pdf_logo_height` und `branding.mail_logo_height` steuern die
Logo-Höhe in Pixeln. Erlaubt sind Werte von `10` bis `200`.

### Logging

```yaml
logging:
  enabled: true
  directory: logs
  level: INFO
```

Wenn `logging.enabled` aktiv ist, schreibt jeder Rechnungslauf eine Logdatei mit Zeitstempel in `logs/`. Der Ordner wird nicht versioniert. Mit `enabled: false` wird kein Logfile geschrieben.

### `.env`

```env
MAIL_SERVER=smtp.example.com
MAIL_PORT=587
MAIL_USER=deine@email.de
MAIL_PASS=dein_passwort
```

### `daten.json`

Beinhaltet die Kunden-, Leistungs- und Abrechnungsdaten. Kann interaktiv über `tools/kunden_anlegen.py` erweitert werden.

```json
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

Beinhaltet die eigenen Daten wie Absender, Bankdaten und Mail. Kann interaktiv über `install/install.sh` oder `install/install.ps1` erstellt werden.

```json
{
  "absender": {
    "name": "Max Mustermann",
    "firma": "Musterfirma GmbH",
    "straße": "Musterstraße 1",
    "plz": "12345",
    "ort": "Musterstadt",
    "telefon": "+49 123 456789",
    "email": "muster.mann@mustermann.de",
    "website": "www.mustermann.de"
  },
  "bank": {
    "bankname": "Sparkasse XY",
    "kontoinhaber": "Max Mustermann",
    "iban": "DE12345678901234567890",
    "bic": "SPKEXY12XXX"
  },
  "finanzen": {
    "steuer_id_typ": "steuernummer",
    "steuernummer": "12/345/67890",
    "finanzamt": "Finanzamt Musterstadt",
    "kleinunternehmer": false,
    "mehrwertsteuer_prozent": 19
  },
  "mail": {
    "bcc": "rechnung@mustermann.de",
    "from_name": "Musterfirma Rechnungen"
  }
}
```

Für Rechnungen muss entweder eine Steuernummer oder eine USt-IdNr. konfiguriert werden. Der Installer fragt ab, welche Variante verwendet werden soll. Für die USt-IdNr. werden stattdessen folgende Felder verwendet:

```json
"steuer_id_typ": "ust_id",
"ust_id": "DE123456789"
```

`mail.from_name` ist optional und steuert den sichtbaren Namen des
Mail-Absenders. Ohne Wert wird wie bisher nur die SMTP-Adresse aus `.env`
verwendet.

Die SMTP-Adresse aus `.env` (`MAIL_USER`) ist die technische Versand- und
Absenderadresse der E-Mail. Die Adresse unter `absender.email` bleibt davon
getrennt und wird als formelle Kontaktadresse in PDF-Rechnung und
HTML-Mailinhalt angezeigt.

Wenn `kleinunternehmer` auf `false` steht, versteht das Tool die bei den
Leistungen hinterlegten Beträge als Nettopreise. Der konfigurierte
Mehrwertsteuersatz wird zusätzlich berechnet und Rechnung sowie Mail weisen
Netto-, Steuer- und Bruttobetrag aus. Bei `kleinunternehmer: true` wird keine
Mehrwertsteuer addiert.

---

## 📤 Rechnung erzeugen & versenden

### Setup prüfen

```bash
python tools/check_setup.py
```

Der Check gibt keine `.env`-Werte oder Kundendaten aus. Er prüft neben
Pflichtfeldern auch Beträge, Abrechnungszyklen,
Fälligkeiten, Abrechnungseinheiten, Datumsformate sowie konfigurierte Lese- und
Schreibpfade. Für Schreibziele erzeugt und entfernt er unmittelbar eine
temporäre Testdatei.

Vor jedem Rechnungslauf prüft zusätzlich ein kleiner, rein lesender Mini-Check
die zentralen Konfigurationsdateien, Vorlagen sowie Runtime-, PDF- und
Mail-Konfiguration. Ein unerreichbarer Kunden-Archivpfad stoppt nur den
betroffenen Kunden vor PDF-Erzeugung und Mailversand.

### Variante A: Manuell im Terminal

```bash
python src/main.py
```

> Achtung: Dieser Befehl startet die produktive Verarbeitung. Dabei können PDFs erzeugt, E-Mails versendet, Verlaufsdaten aktualisiert und Archivdateien geschrieben werden.

### Variante B: Per Doppelklick oder Ausführen aus dem Terminal (empfohlen)

- **Windows:** `.\rechnung_generieren.ps1` (Desktop-Verknüpfung wird automatisch angelegt)
- **Linux:** `./rechnung_generieren.sh`

> Die Startskripte nutzen automatisch die Python-Umgebung aus `.venv` und starten `src/main.py`.

> Erzeugt PDF-Rechnungen, versendet sie per Mail, archiviert sie, aktualisiert den Verlauf und bietet Löschoption für einmalige Kunden.

### Variante C: Cronjob oder Serverbetrieb

```bash
./rechnung_cron.sh
```

Dieses Skript läuft ohne Rückfragen und ist für automatisierte Starts gedacht. Beispiel für einen monatlichen Cronjob am ersten Tag um 08:00 Uhr:

```cron
0 8 1 * * cd /pfad/rechnung-automation && ./rechnung_cron.sh
```

Der Python-Prozess schreibt bei aktivem Logging selbst in `logs/`. Eine zusätzliche Shell-Umleitung ist deshalb normalerweise nicht nötig.

Treten während eines Cronlaufs schwere Fehler mit Log-Level `ERROR` oder
`CRITICAL` auf, wird am Laufende eine Zusammenfassung an den in
`data/konfiguration.json` hinterlegten BCC-Empfänger gesendet. Warnungen lösen
keine Fehlerberichtsmail aus. Fehler eines einzelnen Kunden werden protokolliert,
ohne die Verarbeitung nachfolgender Kunden abzubrechen.

Bei stundenbasierten Cron-Abrechnungen werden fehlende oder unvollständige
Stundenzeiträume im aktuellen Fälligkeitsmonat erneut geprüft. Nach dem
Monatswechsel wird der offene Zeitraum ohne Rechnung abgeschlossen. Bereits
versendete oder abgeschlossene Zeiträume werden durch spätere Änderungen nicht
erneut versendet.

### Mailversand testen

```bash
python tools/mailversand_testen.py
```

> Dieser Befehl sendet eine echte Testmail ausschließlich an den konfigurierten
> BCC-Empfänger. Er erzeugt keine Rechnungen, PDFs oder Verlaufsdaten.

### Darstellung mit einer Musterrechnung testen

```bash
python tools/testrechnung_versenden.py
```

> Dieser Befehl erzeugt eine echte PDF-Musterrechnung und versendet eine echte
> Rechnungsmail. Standardempfänger ist die konfigurierte BCC-Adresse; beim
> Start kann eine andere Adresse eingegeben werden. Das Tool fragt nach einem
> Monats-, Pauschal- oder Stundenmuster und verwendet ansonsten die aktuelle
> Konfiguration, Vorlagen, Farben und Logos. PDF, Betreff und Mailtext sind
> deutlich als Muster gekennzeichnet. Kundendaten, Verlauf und Archive werden
> nicht verändert.

---

## 📁 Projektstruktur

```
rechnung-automation/
├── .gitignore                     # Ausschlüsse (z. B. .venv/, data/)
├── .env                           # SMTP-Zugangsdaten (nicht im Git)
├── .venv/                         # Virtuelle Umgebung (nicht ins Git)
├── config/
│   └── settings.yaml              # Nicht-sensitive Projekteinstellungen
├── data/
│   ├── daten.json                 # Kunden- und Rechnungsdaten
│   ├── konfiguration.json         # Absender-, Steuer- und Bankdaten
│   └── verlauf-20XX.json          # Automatisch gepflegter Rechnungsverlauf
├── img/
│   └── logo.png                   # Standardlogo für die PDF
├── logs/                          # Lokale Logdateien (nicht ins Git)
├── install/
│   ├── install.ps1                # Einrichtungsskript (Windows PowerShell)
│   ├── install.sh                 # Einrichtungsskript (Linux)
│   ├── requirements.txt           # Python-Abhängigkeiten
│   └── version.py                 # Zentrale Versionsnummer
├── licenses/
│   └── gpl-2.0.txt
├── sample/
│   ├── daten.sample.jsonc
│   ├── .env.sample
│   ├── konfiguration.sample.json
│   ├── mail_template.sample.html
│   ├── rechnung_template.sample.html
│   └── settings.sample.yaml
├── src/
│   ├── faelligkeit.py             # Fälligkeitsprüfung für Rechnungen
│   ├── konfiguration.py           # Konfigurations- und Mail-Env-Laden
│   ├── kunden.py                  # Kundenliste aktualisieren
│   ├── leistungen.py              # Leistungs- und Stundenberechnung
│   ├── logging_setup.py           # Zentrale Logging-Konfiguration
│   ├── mail.py                    # Mail-Aufbau und SMTP-Versand
│   ├── main.py                    # Hauptskript zur Rechnungserstellung
│   ├── pdf.py                     # PDF-Erzeugung per konfigurierter Engine
│   ├── paths.py                   # Zentrale Projektpfade aus Einstellungen
│   ├── rechnungen.py              # Rechnungsdatum, Nummer, Zeitraum und Steuer
│   ├── settings_loader.py         # YAML-Loader für Projekteinstellungen
│   ├── templates.py               # Template-Laden und Kontextaufbau
│   ├── verlauf.py                 # Rechnungsverlauf laden und absichern
│   └── workflow.py                # Orchestrierung pro Rechnungslauf
├── hours/                         # Stundenlisten pro Monat
├── tools/
│   ├── check_setup.py             # Ungefährlicher Setup-Check
│   ├── kunden_anlegen.py          # Interaktive Kundenerfassung
│   ├── mailversand_testen.py      # SMTP-Testmail ausschließlich an BCC
│   └── testrechnung_versenden.py  # Markierte Musterrechnung versenden
├── templates/
│   ├── mail_template.html         # HTML-Vorlage für E-Mail
│   └── rechnung_template.html     # HTML-Vorlage für PDF-Rechnung
├── rechnung_generieren.ps1        # Schnellstart-Skript für Windows
├── rechnung_generieren.sh         # Schnellstart-Skript für Linux
├── rechnung_cron.sh               # Nicht-interaktiver Start für Cron/Server
├── tests/                         # Ungefährliche Tests für reine Logik
├── CHANGELOG.md
├── LICENSE.md
└── README.md
```

---

## 🧩 Templates

- `templates/rechnung_template.html` → PDF-Design
- `templates/mail_template.html` → E-Mail-Text (HTML)
- `branding.pdf_logo` → optionales Logo für die PDF
- `branding.mail_logo` → optionales, eingebettetes Logo für die Rechnungsmail

Bearbeite die Templates direkt, um Texte, Farben oder Formatierungen zu ändern.

---

## 🛠 Erweiterungsmöglichkeiten

- Rechnung mit Steuersatz und Mehrwertsteuer
- Automatische Verarbeitung von Zahlungseingängen
- Integration mit Zeiterfassung oder CRM

---

## 🔄 Update

```bash
git pull
```

Vor einem Update sollten lokale Änderungen committed oder gesichert sein. Persönliche Daten in `.env` und `data/` werden nicht versioniert.

---

## 📋 Changelog

Siehe [CHANGELOG.md](CHANGELOG.md)

---

## 📚 Dokumentation

Eine vollständige Dokumentation findest du im **[offiziellen GitHub-Wiki](https://github.com/jan-erbert/rechnung-automation/wiki)**.  
Dort sind alle Bereiche detailliert erklärt:

- Einrichtung & Systemvoraussetzungen
- Konfigurationsdateien (`daten.json`, `konfiguration.json`, `.env`)
- Betrieb, Cronjobs und Logging
- PDF- und E-Mail-Vorlagen
- Archivierung, Updates & Fehlerbehandlung
- Technischer Aufbau und Erweiterungsmöglichkeiten

---

## ⚖️ Lizenz

MIT License – frei nutzbar, kommerziell verwendbar, keine Gewährleistung.
