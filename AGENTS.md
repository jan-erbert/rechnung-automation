# AGENTS.md

Projektspezifische Arbeitsregeln fuer das Repository `rechnung-automation`.

Diese Datei ergaenzt die globale `AGENTS.md`. Die globale Datei bleibt verbindlich und muss immer beachtet werden. Bei Konflikten gelten zuerst Sicherheit und explizite Nutzeranweisungen, danach diese projektspezifischen Regeln.

## Projektkontext

Dieses Projekt kann Rechnungen erzeugen, PDFs erstellen, Archive schreiben und E-Mails versenden. Dadurch koennen produktive Aktionen ausgeloest, lokale Daten veraendert oder vertrauliche Informationen verarbeitet werden.

Standardmaessig duerfen keine produktiven Ablaeufe ausgefuehrt werden. Produktive oder potenziell produktive Befehle duerfen nur nach ausdruecklicher Freigabe des Nutzers gestartet werden.

Wenn der Nutzer ausdruecklich bestaetigt, dass in einer Dev-/Testumgebung gearbeitet wird, duerfen produktionsnahe Testlaeufe nur fuer den konkret freigegebenen Zweck ausgefuehrt werden. Vorher muss klar benannt werden, dass dabei PDFs erzeugt, E-Mails versendet, Verlaeufe aktualisiert oder lokale Dateien veraendert werden koennen.

Eine Freigabe als Testsystem gilt nur fuer den aktuellen, vom Nutzer benannten
Arbeitsumfang. Vor einem Mailtest muessen alle aktiven Empfaenger inklusive CC
und BCC ohne Ausgabe ihrer vollstaendigen Adressen auf die freigegebene
Testdomain geprueft werden.

## Nicht Ausfuehren

Die folgenden Befehle und Skripte duerfen ohne ausdrueckliche Freigabe nicht ausgefuehrt werden:

- `python src/main.py`
- `python main.py`
- `./generate_invoices.sh`
- `./invoice_cron.sh`
- `generate_invoices.ps1`
- `invoice_cron.ps1`
- `install/install.sh`
- `install/install.ps1`
- `tools/create_customer.py`
- `tools/send_test_invoice.py`
- `tools/test_mail_delivery.py`
- `tools/manage_backups.py create`
- `tools/manage_backups.py restore`

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
- `python tools/check_setup.py`
- `python -m pytest`, solange nur ungefaehrliche Tests ohne Rechnungserzeugung, PDF-Erzeugung, Mailversand oder `data/`-Schreibzugriffe ausgefuehrt werden

Keine Tests oder Checks ausfuehren, die Projektcode starten, Rechnungen erzeugen, PDFs erzeugen, E-Mails versenden oder Dateien in `data/` veraendern koennten.

Der Dry-Run ueber `./generate_invoices.sh --dry-run` beziehungsweise
`generate_invoices.ps1 -DryRun` versendet keine E-Mails und veraendert keinen
Rechnungszustand, rendert aber PDFs im Speicher und schreibt ein Laufprotokoll.
Er darf deshalb nur mit ausdruecklicher Testfreigabe ausgefuehrt werden.

`python tools/check_setup.py` darf fuer Pfadpruefungen kurzlebige Testdateien in
konfigurierten Schreibzielen erstellen und sofort wieder entfernen. Der Check
darf dabei keine bestehenden Dateien veraendern.

## Sensible Daten

Die folgenden Inhalte duerfen nicht committed, in Antworten ausgegeben oder ohne ausdrueckliche Freigabe veraendert werden:

- `data/`
- `.env`
- Rechnungsdaten
- Zugangsdaten
- SMTP-Daten
- generierte PDFs
- lokale Archive oder produktive Ausgabedateien
- Zustandsbackups unter `backup/`

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

## Multi-Agent-Arbeit

- `multiagents_v2` verwenden, wenn unabhaengige Pruef- oder Arbeitsbereiche
  dadurch sinnvoll parallel bearbeitet werden koennen.
- Aufgaben klar abgrenzen und Schreibkonflikte zwischen Agenten vermeiden.
- Sicherheitskritische, fachlich gekoppelte oder sehr kleine Aenderungen beim
  Hauptagenten belassen.
- Ergebnisse der Agenten immer durch den Hauptagenten pruefen, integrieren und
  gemeinsam testen; Delegation ersetzt keine Abschlusskontrolle.

## Python-Stil

- Python-Code klar, robust und wartbar halten.
- Kurze, praezise Funktions-Docstrings verwenden.
- Bestehende Namens-, Logging- und Fehlerbehandlungsmuster respektieren.
- Keine Debug-Ausgaben im finalen Code belassen.

## Aktueller Umbaukontext

Fuer den aktuellen Umbau gelten diese zusaetzlichen Regeln:

- Linux und Windows werden ueber getrennte Start- und Installationsskripte unterstuetzt.
- Linux nutzt `.sh`-Skripte, Windows nutzt PowerShell-Skripte.
- WeasyPrint wird als PDF-Engine verwendet.
- Produktive oder produktionsnahe PDF-/Mail-Testlaeufe duerfen nur nach ausdruecklichem Go des Nutzers ausgefuehrt werden.
- Black wird nur vom Nutzer ausgefuehrt, da es nur dort gut klappt. Weise
  darauf hin, wenn das Ausfuehren notwendig oder sinnvoll ist.
