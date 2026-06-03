# Changelog

Alle signifikanten Änderungen dieses Projekts werden in diesem Dokument aufgeführt.

## [1.3.1] - 2026-06-03

### Added

- `config/settings.yaml` für nicht-sensitive Projektpfade, Runtime-Optionen und vorbereitete PDF-Engine-Auswahl ergänzt.
- Neue Dev-Requirements in `install/requirements-dev.txt` für Black, Flake8 und Pytest ergänzt.
- Neue Module für Fälligkeit, Konfiguration, Kundenlogik, Leistungen, Mail, Pfade, PDF, Rechnungsdaten, Templates, Verlauf und Workflow ergänzt.

### Changed

- `src/main.py` auf einen schlanken Einstiegspunkt reduziert.
- Rechnungsworkflow in kleinere, nachvollziehbare Python-Module ausgelagert.
- README um Entwickler-Abhängigkeiten, YAML-Konfiguration und aktualisierte Projektstruktur ergänzt.
- Runtime-Requirements um `PyYAML` für die YAML-Konfiguration erweitert.

### Notes

- Keine produktive PDF-Engine-Umstellung vorgenommen.
- Windows-Dateien und `wkhtmltopdf.exe` bleiben unverändert.
- `environment.env` wurde nicht zu `.env` migriert.

## [1.3.0] - 2026-06-03

### Added

- Projektspezifische `AGENTS.md` mit Sicherheitsregeln für Rechnungserzeugung, PDF-Erstellung, Archivierung und Mailversand ergänzt.
- `weasyprint` als Python-Abhängigkeit für Linux-Vorbereitung ergänzt.

### Changed

- `install/requirements.txt` von UTF-16 nach UTF-8 mit LF-Zeilenenden normalisiert.
- `install/install.sh` nutzt jetzt zuverlässig die Requirements-Datei aus `install/requirements.txt`.
- README-Installationspfade an die tatsächliche Projektstruktur angepasst.
- README-Hinweis ergänzt, dass der manuelle Start produktive Verarbeitung auslösen kann.
- `.gitignore` schützt nun auch `.env` und `environment.env` im Projektroot.
- Versionsnummer auf `1.3.0` gesetzt.
- `src/main.py` in eine `main()`-Funktion gekapselt und bestehende Funktionen mit kurzen Docstrings ergänzt.

## [1.2.3] - 2026-01-02

### Fixed

- Behebung eines kritischen Fehlers beim Jahreswechsel: Wenn noch keine Verlaufsdatei für das neue Jahr existiert (z. B. `verlauf-2026.json`), wird diese nun korrekt angelegt und das Programm läuft stabil weiter.
- Verhindert einen Absturz (`UnboundLocalError`) bei leerem Rechnungsverlauf zu Jahresbeginn.
- Mehrmonats-Abrechnungszyklen (z. B. 3-, 6-Monats-Rechnungen) berücksichtigen nun korrekt die letzte Abrechnung aus dem Vorjahr.
- Die Prüfung „bereits abgerechnet“ erfolgt jetzt jahresübergreifend, um doppelte Rechnungen an Jahresgrenzen zuverlässig zu verhindern.
- Einmalige Rechnungen werden ebenfalls jahresübergreifend geprüft, sodass eine im Dezember gestellte Einmalrechnung im Januar nicht erneut erzeugt wird.

### Changed

- Der Rechnungsverlauf des Vorjahres wird bei Bedarf read-only in die Fälligkeitslogik einbezogen, ohne das bestehende Jahresdateikonzept zu verändern.
- Das Schreiben von Verlaufsdaten erfolgt weiterhin ausschließlich in der Verlaufsdatei des aktuellen Jahres.

## [1.2.2] - 2025-06-01

### Added

- Erweiterte Startskripte (`rechnung_generieren.bat`, `.ps1`, `.sh`) für zuverlässige Ausführung per Doppelklick – inklusive direktem Aufruf der `.venv`-Python-Umgebung.
- Automatische Erstellung eines Startskripts (`start-rechnung.*`) bei Erstinstallation über install.bat / install.ps1 / install.sh.
- Plattformübergreifende Hinweise zur Aktivierung der virtuellen Umgebung in allen Skripten.
- Hinweis auf BCC-Empfänger zur revisionssicheren Archivierung direkt in der Einrichtung.

### Changed

- Alle Start- und Installationsskripte setzen nun standardmäßig UTF-8 (Windows: `chcp 65001`).
- Die Konfigurationsdatei `konfiguration.json` wird nun JSON-konform erzeugt, inkl. dynamischer Einfügung des Zykluswechsels.
- Die `install.bat`, `install.ps1` und `install.sh` wurden vereinheitlicht und logisch gegliedert.
- Bei Windows: Powershell erzeugt eine Desktop-Verknüpfung zur `start-rechnung.bat` (inkl. Arbeitsverzeichnis).

### Fixed

- Fehlerhafte oder nicht funktionierende Ausführung per Doppelklick außerhalb von VS Code (z. B. `py` nicht gefunden, keine venv aktiviert) wurde behoben.
- Erkennung und Abrechnung nach Zykluswechsel (z. B. von 1 auf 6 Monate) funktioniert jetzt zuverlässig.
- Falscher Pfadaufruf in älteren Startskripten (fehlender Wechsel ins `src`-Verzeichnis) wurde korrigiert.

## [1.2.1] - 2025-05-21

### Added

- Plattformübergreifende Startskripte (`start-rechnung.bat`, `start-rechnung.sh`) zur einfachen Ausführung mit venv-Aktivierung.
- Automatische Erstellung einer Desktop-Verknüpfung unter Windows (install.ps1 / install.bat).
- Neuer interaktiver Installer (install.ps1/install.sh/install.bat) mit Pflichtfeldvalidierung nach §14 UStG.
- Vollständig überarbeitete README.md mit OS-spezifischer Einrichtung und aktualisierter Struktur.
- Erweiterung der install.ps1 um automatische JSON-Erzeugung mit Prüfung aller Pflichtfelder.

### Changed

- Projektstruktur modernisiert (install/Verzeichnis, sample, tools).
- `README.md` vollständig neu aufgebaut für GitHub-Kompatibilität.
- `install.bat` und `install.sh` mit gleichem Funktionsumfang wie `install.ps1` angepasst.
- Mail-Konfiguration (`MAIL_BCC`) als optionales, aber empfohlenes Feld ausgewiesen.

### Fixed

- Falscher Dateiname `enviroonment.env` in README korrigiert.
- Einträge in der Projektstrukturbeschreibung korrigiert (z. B. mehrfach vorhandene `version.py`).
- Verbesserung der Pfadverweise und UTF-8-Speicherlogik für Setup-Tools.

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
