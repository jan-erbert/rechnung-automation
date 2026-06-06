# Changelog

Alle signifikanten Änderungen dieses Projekts werden in diesem Dokument aufgeführt.

## [1.3.5] - Unreleased

### Fixed

- Leere optionale Webseitenangaben werden in Rechnungen, E-Mails und Leistungspositionen nicht mehr als leere Beschriftungen, Links oder Klammern ausgegeben.
- Ein fehlendes optionales Logo erzeugt in Rechnungen kein leeres oder defektes Bildelement mehr.
- Der in `letzte_rechnung` konfigurierte Endmonat löst die noch ausstehende letzte reguläre Rechnung unabhängig vom normalen Abrechnungszyklus aus.
- Kunden mit erreichtem Endmonat können nach der erfolgreich versendeten letzten Rechnung im interaktiven Lauf entfernt werden.
- Ungültige Beträge werden nicht mehr stillschweigend als `0,00 EUR` verarbeitet.
- Fehlerhafte Abrechnungszyklen, Fälligkeiten, Abrechnungseinheiten und Datumsformate werden vor der Rechnungserzeugung verständlich abgelehnt.
- Pauschale Zusatzleistungen werden unabhängig vom Abrechnungszyklus nur einmal zur Rechnungssumme addiert.
- Eindeutig fehlgeschlagene Mailversuche werden als `failed` gespeichert und beim nächsten Lauf erneut versucht.
- Unklare Versandzustände bleiben als `pending` markiert und blockieren automatische Wiederholungen, um Doppelversand zu vermeiden.
- Fehler bei Archivierung oder Kundenentfernung werden getrennt vom erfolgreichen Mailversand protokolliert.
- Stundenbasierte Cron-Abrechnungen mit `0` Stunden bleiben im aktuellen Fälligkeitsmonat als `waiting_hours` für nachgetragene Stunden offen.
- Abgelaufene Nullstunden-Wartezustände werden als `no_invoice` abgeschlossen und lösen keine verspätete oder doppelte Rechnung aus.
- Nullstunden-Abschlüsse berücksichtigen weiterhin den konfigurierten Abrechnungszyklus.
- Unvollständige Stundenzeiträume bei mehrmonatigen Cron-Abrechnungen werden nicht mehr als Teilrechnung versendet.
- Der Linux-Installer schreibt `.env` und `data/konfiguration.json` strukturiert, sodass Sonderzeichen die erzeugten Dateien nicht mehr beschädigen.
- Der Linux-Installer validiert Pflichtangaben, SMTP-Port, Ja-/Nein-Auswahl und Mehrwertsteuersatz bereits während der Einrichtung.
- Eine unvollständige `.venv` oder eine fehlende Runtime-Requirements-Datei führt im Linux-Installer jetzt zu einem klaren Abbruch.
- Der Linux-Installer bereitet nur noch die unterstützten Startskripte `rechnung_generieren.sh` und `rechnung_cron.sh` vor.
- Der Windows-Installer erkennt unvollständige virtuelle Umgebungen und validiert SMTP-Port sowie Mehrwertsteuersatz innerhalb sinnvoller Grenzen.
- Der Windows-Installer schreibt `.env` strukturiert, sodass Sonderzeichen in SMTP-Zugangsdaten die Datei nicht mehr beschädigen.
- Ein unerwarteter Fehler bei einem Kunden bricht den Rechnungslauf nicht mehr für nachfolgende Kunden ab.
- Fehler beim PDF-Archivieren werden als schwere Fehler protokolliert, da die Rechnung bereits versendet wurde.
- Unerreichbare Kunden-Archivpfade stoppen nur den betroffenen Kunden, bevor eine Rechnung erzeugt oder versendet wird.

### Added

- Rendering-Tests für optionale Webseitenangaben und Logos ergänzt.
- Grenzfalltests für den konfigurierten letzten Rechnungsmonat ergänzt.
- Zentrale Validierung für abrechnungsrelevante Kundendaten ergänzt und in Setup-Check sowie Kundenanlage eingebunden.
- Berechnungstests für pauschale, monatliche und inklusive Zusatzleistungen ergänzt.
- Atomare Speicherung und Versandstatus `pending`, `sent` und `failed` für den Rechnungsverlauf ergänzt.
- Tests für Versandstatus, Wiederholungslogik und atomare Verlaufsaktualisierung ergänzt.
- Verlaufsstatus `waiting_hours` und `no_invoice` für stundenbasierte Abrechnungen ergänzt.
- Isolierte Tests für die sichere Erzeugung der lokalen Linux-Setup-Dateien ergänzt.
- Cron-Fehlerberichte an den konfigurierten BCC-Empfänger für tatsächlich protokollierte `ERROR`- und `CRITICAL`-Meldungen ergänzt.
- Separates SMTP-Testskript `tools/mailversand_testen.py` ergänzt, das ausschließlich eine Bestätigungsmail an den BCC-Empfänger sendet.
- Tests für Kundenisolation, schwere Laufmeldungen, Cron-Fehlerberichte und SMTP-Testmails ergänzt.
- Vollständige Pfadprüfung im Setup-Check für zentrale Dateien, Verzeichnisse und Kundenarchive ergänzt.
- Echte, sofort entfernte Schreibproben für konfigurierte Daten-, Backup-, Log- und Archivziele ergänzt.
- Schlanker Mini-Check vor jedem Rechnungslauf für zentrale Dateien sowie Runtime-, PDF- und Mail-Konfiguration ergänzt.
- Tests für Pfadprüfungen und Startvoraussetzungen ergänzt.

### Changed

- Interne Versionsnummer auf `1.3.5` gesetzt.

## [1.3.4] - 2026-06-06

### Added

- Auswahl zwischen Steuernummer und Umsatzsteuer-Identifikationsnummer (USt-IdNr.) für Rechnungen ergänzt.
- Tests für beide unterstützten steuerlichen Identifikationsarten ergänzt.

### Changed

- Linux- und Windows-Installer fragen die gewünschte steuerliche Identifikationsart bei der Einrichtung ab.
- Rechnungsvorlagen zeigen abhängig von der Konfiguration die passende Bezeichnung und Nummer an.
- Konfigurationsloader, Setup-Check, Samples und Dokumentation an das neue Auswahlschema angepasst.

## [1.3.3] - 2026-06-04

### Added

- Zentrales Logging mit optionalen Lauf-Logdateien unter `logs/` ergänzt.
- Nicht-interaktives Cron-/Server-Startskript `rechnung_cron.sh` ergänzt.
- Setup-Check `tools/check_setup.py` für ungefährliche Konfigurationsprüfungen ergänzt.
- Erste ungefährliche Pytest-Tests für PDF-Konfiguration und Rechnungslogik ergänzt.

### Changed

- `src/main.py` unterstützt jetzt `--non-interactive` für automatisierte Läufe.
- Workflow-, PDF-, Template- und Stundenlogik nutzen Logging für Laufmeldungen.
- Stundenbasierte Abrechnung nimmt im nicht-interaktiven Modus bei fehlenden Stunden 0 Stunden an, statt eine Eingabe anzufordern.
- `tools/kunden_anlegen.py` strukturell modernisiert und mit kurzen Docstrings versehen.
- README um Logging, Setup-Check, Cron-/Serverbetrieb und Git-basiertes Update ergänzt.
- Versionsnummer auf `1.3.3` gesetzt.

### Removed

- Veraltetes Self-Update-Tool `tools/update_tool.py` entfernt.
- Lokales Release-ZIP-Skript `tools/build_release_zip.py` entfernt.

## [1.3.2] - 2026-06-04

### Added

- Linux-Schnellstartskript `rechnung_generieren.sh` ergänzt.
- `sample/.env.sample` als neue Vorlage für lokale SMTP-Zugangsdaten ergänzt.

### Changed

- PDF-Erzeugung vollständig auf WeasyPrint umgestellt.
- wkhtmltopdf-Unterstützung entfernt, da die GitHub-Organisation `wkhtmltopdf` am 10. Juli 2024 archiviert wurde und das Projekt nicht mehr maintained ist.
- Inhalt von `bin/` entfernt; `wkhtmltopdf.exe` wird nicht mehr mitgeführt.
- `pdfkit` aus den Runtime-Abhängigkeiten entfernt.
- `config/settings.yaml` auf WeasyPrint-only bereinigt.
- Lokale Mail-Konfiguration von `data/environment.env` auf `.env` migriert.
- Linux-Installer erzeugt jetzt `.env`, prüft SMTP-Portwerte und schreibt die Datei mit restriktiven Rechten.
- Windows-Installer auf PowerShell-only nachgezogen und an `.env` sowie WeasyPrint-Requirements angepasst.
- Windows-Start auf `rechnung_generieren.ps1` vereinheitlicht; das Skript nutzt direkt `.venv\Scripts\python.exe`.
- PDF-Template für WeasyPrint optimiert und alte wkhtmltopdf-/Footer-Reste entfernt.
- Sample-Rechnungsvorlage an die produktive Vorlage angeglichen.
- Rechnungsfuß und Steuerkonfiguration überarbeitet.
- Linux-Installer und Beispielkonfiguration an die neue Steuerkonfiguration angepasst.
- README beschreibt Windows über PowerShell und Linux über Shell-Skripte.

### Removed

- Windows-CMD-/BAT-Pfade entfernt; `install/install.bat` und `rechnung_generieren.bat` werden nicht mehr mitgeführt.

### Notes

- Bestehende lokale `data/konfiguration.json` wurde strukturell migriert, ohne sensible Werte auszugeben.

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
