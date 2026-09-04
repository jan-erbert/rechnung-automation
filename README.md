# Rechnung-Automation

Python-Tool zur automatisierten Erstellung, Archivierung und Versendung von
PDF-Rechnungen. Linux und Windows werden ueber getrennte Start- und
Installationsskripte unterstuetzt.

**Aktuelle Version:** `1.4.1`

## Funktionen

- PDF-Erzeugung aus HTML-Vorlagen mit WeasyPrint
- Versand per SMTP mit optionalen CC- und BCC-Empfaengern
- STARTTLS oder implizites TLS/SSL
- Monatliche, pauschale, einmalige und stundenbasierte Abrechnung
- Sichere Versandzustaende `pending`, `sent` und `failed`
- Atomare Speicherung von Verlauf und Kundendateien
- Eine uebersichtliche YAML-Datei pro Kunde
- Konfigurierbares Design, Branding und Logging
- Nicht-interaktiver Cronbetrieb mit Fehlerbericht
- Ungefaehrlicher Setup-Check ohne Rechnungs- oder Mailerzeugung

## Voraussetzungen

- Python 3.10 oder neuer
- Linux-Systembibliotheken und Fonts fuer WeasyPrint, distributionsabhaengig
- SMTP-Zugang fuer den Mailversand

## Installation

```powershell
# Windows PowerShell
./install/install.ps1
```

```bash
# Linux
./install/install.sh
```

Die Installer erstellen `.venv`, installieren die Abhaengigkeiten und legen
die lokale `.env` sowie `config/invoice.yaml` an. Bestehende lokale Dateien
werden nicht ueberschrieben. Vorhandene Legacy-Dateien werden vor der
Neuanlage erkannt, in die aktuelle Struktur migriert und anschliessend
validiert; die alten Quellen bleiben dabei als Sicherung erhalten.

Entwicklerabhaengigkeiten:

```bash
source .venv/bin/activate
python -m pip install -r install/requirements-dev.txt
```

## Konfiguration

Menschengepflegte Daten verwenden YAML. Maschinell erzeugte Verlaufsdaten
bleiben JSON. Zugangsdaten stehen ausschliesslich in `.env`.

### `config/settings.yaml`

Enthaelt technische Einstellungen fuer Pfade, PDF, Design, Branding, Logging
und SMTP-Verhalten:

```yaml
paths:
  data_dir: data
  customers_dir: customers
  invoice_config: config/invoice.yaml
  templates_dir: templates
  image_dir: img
  hours_dir: hours
  backup_dir: backup

pdf:
  engine: weasyprint

mail:
  security: starttls
  timeout_seconds: 30

logging:
  enabled: true
  directory: logs
  level: INFO
```

`mail.security` akzeptiert `starttls` oder `ssl`. Die passende Portnummer wird
weiterhin in `.env` festgelegt.

Aktivierte Laufprotokolle erhalten gut lesbare Namen nach dem Schema
`invoice-YYYY-MM-DD_HH-MM-SS.log`. Falls zwei Laeufe in derselben Sekunde
starten, wird automatisch ein Zaehlsuffix wie `-02` angehaengt.

### `config/invoice.yaml`

Enthaelt Absender-, Bank-, Steuer- und sichtbare Mailangaben. Die lokale Datei
wird wegen personenbezogener Daten nicht versioniert. Eine vollstaendige
Vorlage liegt unter `sample/invoice.sample.yaml`.

```yaml
sender:
  name: Max Mustermann
  company: Musterfirma GmbH
  street: Musterstraße 1
  postal_code: "01234"
  city: Musterstadt
  phone: "+49 123 456789"
  email: max@example.com

bank:
  name: Musterbank
  account_holder: Max Mustermann
  iban: DE12345678901234567890
  bic: MUSTDE00XXX

tax:
  identifier_type: tax_number
  tax_number: 12/345/67890
  small_business: false
  vat_rate: "19.00"

mail:
  bcc:
    - rechnung@example.com
  from_name: Musterfirma Rechnungen
```

Als `identifier_type` werden `tax_number` und `vat_id` unterstuetzt. Geld- und
Prozentwerte muessen in Anfuehrungszeichen stehen und werden intern mit
`Decimal` verarbeitet.

### `.env`

```dotenv
MAIL_SERVER=smtp.example.com
MAIL_PORT=587
MAIL_USER=deine@email.de
MAIL_PASS=dein_passwort
```

Diese Datei darf nicht committed werden.

## Kundendateien

Jeder Kunde liegt in einer eigenen Datei unter `customers/`. Die stabile `id`
entspricht im Normalfall dem Dateinamen. Eine vollstaendige Vorlage befindet
sich unter `sample/customer.sample.yaml`.

```yaml
id: musterfirma
active: true

contact:
  name: Herr Mustermann
  company: Musterfirma GmbH
  email: kunde@example.com
  cc:
    - buchhaltung@example.com
  street: Musterstraße 1
  postal_code: "12345"
  city: Musterstadt

billing:
  invoice_prefix: MF
  cycle_months: 3
  due_days: 14
  end_month: null
  invoice_date: null
  one_time: false

main_service:
  description: Individuelle Beratung
  unit: month
  unit_price: "65.00"

additional_services:
  - description: Zusatzleistung
    unit: flat
    unit_price: "9.99"
  - description: Support inklusive
    unit: included

archive:
  directory: null
```

Unterstuetzte Einheiten der Hauptleistung sind `month`, `hour` und `flat`.
Zusatzleistungen verwenden `month`, `flat` oder `included`. Postleitzahlen,
Telefonnummern, Geldwerte und Prozentwerte sollten immer als Text in
Anfuehrungszeichen stehen. `billing.invoice_date` verwendet `YYYY-MM-DD`,
`billing.end_month` verwendet `YYYY-MM`.

Neue Kunden koennen interaktiv angelegt werden:

```bash
python tools/create_customer.py
```

Abgeschlossene einmalige Kunden werden im interaktiven Lauf auf Wunsch durch
`active: false` deaktiviert, nicht geloescht.

## Stundenbasierte Abrechnung

Monatliche Stundenwerte liegen unter `hours/` in einer YAML-Datei pro
Leistungsmonat. Der Dateiname und `period` verwenden `YYYY-MM`; Kunden werden
ueber ihre stabile ID referenziert. Eine Vorlage liegt unter
`sample/hours.sample.yaml`.

```yaml
period: "2026-08"

customers:
  musterfirma:
    hours: 8.50
```

Stundenwerte duerfen als einfache YAML-Zahlen ohne Anfuehrungszeichen notiert
werden und muessen nichtnegativ sein sowie hoechstens zwei Nachkommastellen
besitzen. Ein Lauf im
September liest fuer einen monatlich abgerechneten Stundenkunden den
Leistungsmonat August. Bei mehrmonatigen Zyklen werden entsprechend mehrere
abgeschlossene Vormonate geladen.

Fehlt ein Wert im interaktiven Lauf, wird die abgefragte Stundenanzahl atomar
in der passenden Monatsdatei gespeichert. Im nicht-interaktiven Cronlauf wird
keine Eingabe erfunden; die Abrechnung bleibt mit `waiting_hours` offen.

Alte Dateien wie `stunden_2026_08.json` koennen kontrolliert migriert werden:

```bash
python tools/migrate_legacy_hours.py
python tools/migrate_legacy_hours.py --apply
python tools/migrate_legacy_hours.py --verify
```

Nach erfolgreicher Pruefung koennen die alten Stunden-JSONs explizit entfernt
werden:

```bash
python tools/migrate_legacy_hours.py --delete-legacy
```

## Migration von JSON nach YAML

Das Migrationswerkzeug veraendert die alten JSON-Dateien standardmaessig nicht.
`--apply` erzeugt die YAML-Dateien und vergleicht sie anschliessend mit den
JSON-Quellen. Eine bestehende Migration kann separat geprueft werden:

```bash
python tools/migrate_legacy_data.py
python tools/migrate_legacy_data.py --apply
python tools/migrate_legacy_data.py --verify
```

Erst wenn dieser Vergleich und die normalen YAML-Loader erfolgreich sind, kann
das Werkzeug mit folgendem expliziten Schalter die beiden alten Dateien
`data/daten.json` und `data/konfiguration.json` loeschen:

```bash
python tools/migrate_legacy_data.py --delete-legacy
```

Das Loeschen ist nicht rueckgaengig zu machen. Eine Sicherung der JSON-Dateien
ist daher sinnvoll. Ohne `--delete-legacy` bleiben sie immer erhalten. Beim
Erzeugen bricht das Werkzeug ab, sobald eine Zieldatei bereits existiert. Nach
der Migration sollte zusaetzlich `python tools/check_setup.py` ausgefuehrt
werden. Erst danach sollte ein Rechnungslauf gestartet werden.

Beim normalen Start und durch die Installer wird dieselbe Migration
automatisch und idempotent ausgefuehrt. Sie umfasst alte Kunden- und
Konfigurations-JSONs, Stunden-JSONs, `verlauf-YYYY.json` sowie alte technische
Templatenamen. Widerspruechliche vorhandene Ziele fuehren zu einem sicheren
Abbruch; Legacy-Quellen werden nie automatisch geloescht.

## Setup pruefen

```bash
python tools/check_setup.py
```

Der Check erzeugt keine Rechnungen und versendet keine E-Mails. Er validiert
Settings, Rechnungskonfiguration, alle Kunden- und Stunden-YAMLs, Templates,
Branding, SMTP-Schluessel und konfigurierte Pfade. Schreibproben verwenden
kurzlebige Testdateien und entfernen sie sofort wieder.

## Rechnungslauf

```bash
# Produktiver interaktiver Lauf
./generate_invoices.sh

# Produktiver nicht-interaktiver Lauf
./invoice_cron.sh
```

Unter Windows wird `generate_invoices.ps1` verwendet.

Eine projektweite Sperrdatei verhindert parallele Rechnungsläufe und damit
versehentliche Doppelversendungen. Eindeutig verwaiste Sperren werden beim
naechsten Start automatisch bereinigt.

> Achtung: Rechnungsläufe koennen PDFs erzeugen, E-Mails versenden,
> Verlaufsdaten aktualisieren und Archive beschreiben.

## Tests und Codequalitaet

```bash
python -m pytest
python -m flake8 .
python -m black --check .
```

Black wird in diesem Projekt bewusst vom Nutzer ausgefuehrt.

Forgejo Actions fuehrt dieselben Tests fuer Python 3.10 und 3.12 sowie Black-,
Flake8- und Shell-Syntaxpruefungen ueber `.forgejo/workflows/ci.yml` aus. Der
Workflow startet keine Rechnungs- oder Mailablaeufe und benoetigt keine
Secrets.

## Projektstruktur

```text
config/
├── settings.yaml
└── invoice.yaml              # lokal, nicht versioniert
customers/
└── <customer-id>.yaml        # lokal, nicht versioniert
data/
└── invoice-history-<year>.json       # maschinell erzeugter Zustand
hours/
└── YYYY-MM.yaml              # Stunden pro Leistungsmonat
sample/
├── customer.sample.yaml
├── hours.sample.yaml
├── invoice.sample.yaml
├── email_template.sample.html
├── invoice_template.sample.html
└── settings.sample.yaml
src/                         # Anwendungslogik
templates/                   # produktive HTML-Vorlagen
tests/                       # ungefaehrliche Tests
tools/                       # Setup-, Kunden- und Migrationswerkzeuge
install/                     # Linux-/Windows-Installer
```

## Lizenz

Siehe `LICENSE.md` und `licenses/`.
