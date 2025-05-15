# Changelog

Alle signifikanten Änderungen dieses Projekts werden in diesem Dokument aufgeführt.

## [1.2.0] - 2025-05-15
### Added
- Neue Konfigurationsdatei konfiguration.json für Absenderdaten, Steueroptionen und Bankverbindung.
- Unterstützung für Kleinunternehmerregelung gemäß §19 UStG und dynamische Mehrwertsteuerberechnung.
- Unterstützung zusätzlicher Leistungen mit automatischer Multiplikation bei zyklischer Abrechnung.
- Anzeige einer Zwischensumme (netto) und einer getrennten MwSt.-Zeile vor dem Gesamtbetrag.
- Dynamische Anzeige des Abrechnungszeitraums in der Leistungsübersicht (auch für Stunden).

### Changed
- Aufteilung und bessere Strukturierung der Konfigurationsdaten zwischen daten.json und konfiguration.json.
- Die Darstellung der Mail- und PDF-Leistungsübersicht wurde optisch verbessert (z. B. mit horizontaler Linie vor dem Gesamtbetrag).
- Automatische Erstellung eines backup-Verzeichnisses bei beschädigter Verlaufsdatei.

### Fixed
- Korrekte Addition von Zusatzleistungen bei stundenbasierter Abrechnung mit mehrmonatigem Zeitraum.
- Fehlerhafte Anzeige oder Berechnung bei fehlendem Stundensatz oder ungültigen Werten korrigiert.

## [1.1.1] - 2025-05-11
### Added
- Neues Update-Tool tools/update_tool.py, das automatisch auf GitHub Releases prüft und bei Bedarf ein ZIP-Update installiert.
- Zentrale Versionsverwaltung über version.py für konsistente Updatevergleiche.
- Erweiterte requirements.txt um requests und packaging zur Unterstützung des Update-Tools.
- Release-Vorlage für GitHub (Markdown) zur schnellen Veröffentlichung neuer Versionen.

### Changed
- Projektstruktur vereinheitlicht (z. B. Umbenennung von mail_versenden.py zu main.py).

### Fixed
- Fehlermeldung bei fehlendem requests oder packaging in VS Code durch klare requirements.txt.

## [1.1.0] - 2025-05-11
### Added
- Unterstützung für stundengenaue Abrechnung auf Basis von monatlichen Stundenlisten (`stunden_YYYY_MM.json`).
- Automatische Rückfrage bei fehlenden Stundendaten.
- Dynamischer Hinweis auf den Stundensatz im PDF und in der E-Mail (optional, nur wenn Stunden abgerechnet wurden).
- Anzeige des Abrechnungszeitraums in PDF und E-Mail auch bei einstufiger Abrechnung (z. B. "Mai 2025").
- Neue Sample-Dateien: `rechnung_template.sample.html`, `mail_template.sample.html`, `daten.sample.jsonc`.
- Neue Markdown-Formatierungen in `README.md` mit besseren Beispielwerten.
- Feld `letzte_rechnung` in `daten.json` zur Begrenzung der Abrechnungsdauer.
- Automatisches Anlegen eines Kunden in der daten.json Datei mittels `kunden_anlegen.py`

### Changed
- Bei Stunden = 0 wird keine Rechnung mehr erstellt, aber ein Verlaufseintrag mit 0 Stunden erzeugt.
- Konsolenausgabe zeigt Umlaute korrekt durch explizites UTF-8-Encoding in `print`.
- Verbesserung der Template-Texte für korrekte Formulierungen abhängig vom Zeitraum.

### Fixed
- Fehlerhafte Anzeige von Umlauten wie "MÃ¤rz" im PDF und Mail.
- Kontext-Fehler (`context not defined`) beim Setzen des `stundensatz_hinweis`.

## [1.0.0] - 2025-05-09
### Added
- Vollständiger Rechnungsworkflow inklusive PDF-Generierung, E-Mail-Versand und Archivierung.
- Unterstützung für HTML-E-Mail-Template mit Logo und Design.
- Unterstützung für BCC-Versand über `MAIL_BCC` aus der `.env`.
- Automatische Rechnungserstellung mit deutschem Monatsnamen.
- Automatische Fälligkeitsberechnung und Rechnungsnummern.
- Unterstützung mehrerer Leistungen pro Rechnung.
- Konfigurierbare Templates (`mail_template.html`, `rechnung_template.html`).
- Automatisches Archivieren der PDFs anhand des Pfads aus `daten.json`.
- Installationsskript (`install.ps1`) für einfaches Setup unter Windows.
- `.gitignore`, `requirements.txt`, `README.md`, `CHANGELOG.md`, `daten.sample.jsonc`, `environment.sample.env` und HTML-Template-Samples.

## [0.9.0] - 2025-04-28
### Improved
- Template-Designs angepasst (modernere Darstellung, bessere Typografie).
- Tabellenlayout für PDF verbessert (Tailwind-inspiriert).
- Header mit Logo neu gestaltet.
- Dateiname der Rechnung auf Firmenname angepasst (`Rechnung_firma_05-2025.pdf`).

## [0.8.0] - 2025-04-22
### Added
- Unterstützung für mehrzeilige Leistungen in der PDF.
- Konfiguration über `.env` (via `python-dotenv`).

## [0.7.0] - 2025-04-18
### Added
- Unterstützung für HTML-Mail mit eingebundenem Logo als Base64.
- HTML-Mail-Vorlage (`mail_template.html`) hinzugefügt.

## [0.6.0] - 2025-04-15
### Improved
- Logging eingeführt für Fehler beim Mailversand und PDF-Erstellung.
- Rechnungsnummernlogik verbessert (Monatsbasierend).

## [0.5.0] - 2025-04-10
### Added
- Einlesen von Rechnungsdaten aus `daten.json`.
- PDF-Erzeugung mit `pdfkit` und `wkhtmltopdf`.

## [0.1.0] - 2025-03-05
### Initial
- Projekt gestartet.
- Erste Tests zur PDF-Erzeugung und SMTP-Versand.