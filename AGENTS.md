# AGENTS.md

Projektspezifische Arbeitsregeln fuer das Repository `rechnung-automation`.

Diese Datei ergaenzt die globale `AGENTS.md`. Die globale Datei bleibt verbindlich und muss immer beachtet werden. Bei Konflikten gelten zuerst Sicherheit und explizite Nutzeranweisungen, danach diese projektspezifischen Regeln.

## Projektkontext

Dieses Projekt kann Rechnungen erzeugen, PDFs erstellen, Archive schreiben und E-Mails versenden. Dadurch koennen produktive Aktionen ausgeloest, lokale Daten veraendert oder vertrauliche Informationen verarbeitet werden.

Standardmaessig duerfen keine produktiven Ablaeufe ausgefuehrt werden. Produktive oder potenziell produktive Befehle duerfen nur nach ausdruecklicher Freigabe des Nutzers gestartet werden.

## Nicht Ausfuehren

Die folgenden Befehle und Skripte duerfen ohne ausdrueckliche Freigabe nicht ausgefuehrt werden:

- `python src/main.py`
- `python main.py`
- `./start-rechnung.sh`
- `start-rechnung.sh`
- `rechnung_generieren.bat`
- `rechnung_generieren.ps1`
- `install/install.sh`
- `install/install.bat`
- `install/install.ps1`
- `tools/kunden_anlegen.py`

Ebenfalls verboten sind alle Befehle oder Skripte, die Rechnungen erzeugen, PDFs aus Projekt- oder Produktivdaten erstellen, Dateien in `data/` veraendern, E-Mails versenden oder produktive Ablaeufe starten koennten.

## Erlaubte Statische Pruefungen

Standardmaessig erlaubt sind nur ungefaehrliche statische Pruefungen:

- Dateien lesen
- `rg`, `grep`, `find`
- `git status`
- `git diff`
- `git log`
- `file`
- `cat`, `head`, `tail`, `sed`

Keine Tests oder Checks ausfuehren, die Projektcode starten, Rechnungen erzeugen, PDFs erzeugen, E-Mails versenden oder Dateien in `data/` veraendern koennten.

## Sensible Daten

Die folgenden Inhalte duerfen nicht committed, in Antworten ausgegeben oder ohne ausdrueckliche Freigabe veraendert werden:

- `data/`
- `.env`
- `environment.env`
- Rechnungsdaten
- Zugangsdaten
- SMTP-Daten
- generierte PDFs
- lokale Archive oder produktive Ausgabedateien

Secrets, Tokens, Passwoerter und vollstaendige Inhalte von lokalen Konfigurationsdateien duerfen nicht angezeigt werden.

## Arbeitsweise

- Aenderungen klein, nachvollziehbar und in einzelnen Schritten durchfuehren.
- Vor Aenderungen immer den Ist-Zustand pruefen, mindestens mit `git status --short`.
- Relevante Dateien vor dem Bearbeiten lesen und bestehende Struktur respektieren.
- Nur Dateien aendern, die fuer die aktuelle Aufgabe notwendig sind.
- Keine unnoetigen Refactorings.
- Keine neuen Abhaengigkeiten ohne ausdrueckliche Begruendung.
- Nach Aenderungen immer `git diff --stat` und relevante Diffs pruefen und nennen.
- Fremde oder bereits vorhandene lokale Aenderungen nicht ueberschreiben oder zuruecksetzen.

## Python-Stil

- Python-Code klar, robust und wartbar halten.
- Kurze, praezise Funktions-Docstrings verwenden.
- Bestehende Namens-, Logging- und Fehlerbehandlungsmuster respektieren.
- Keine Debug-Ausgaben im finalen Code belassen.

## Aktueller Umbaukontext

Fuer den aktuellen Umbau gelten diese zusaetzlichen Regeln:

- Fokus zunaechst auf Linux.
- Windows-Dateien nicht aendern, solange das nicht ausdruecklich beauftragt ist.
- `wkhtmltopdf.exe` vorerst nicht entfernen.
- WeasyPrint soll vorbereitet werden.
- Produktive PDF-Erzeugung darf nicht ausgefuehrt werden.
- `environment.env` soll spaeter zu `.env` migriert werden.
