# Changelog

Alle signifikanten Änderungen dieses Projekts werden in diesem Dokument aufgeführt.

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
