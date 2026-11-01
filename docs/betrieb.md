# Betrieb, Versand und Sicherung

## Laufarten und ihre Auswirkungen

| Einstieg | Wirkung |
| --- | --- |
| `python tools/check_setup.py` | Struktur-/Pfadprüfung, keine Rechnung oder SMTP-Verbindung; kurzlebige Schreibproben möglich |
| `./generate_invoices.sh --dry-run` | Fälligkeit, Mailaufbau und PDF im Speicher prüfen; kein Versand, Archiv oder Rechnungszustand |
| `./generate_invoices.ps1 -DryRun` | Derselbe Dry-Run unter Windows |
| `./generate_invoices.sh` / `.ps1` | Interaktiver echter Rechnungslauf |
| `./invoice_cron.sh` / `.ps1` | Echter Rechnungslauf ohne Nutzereingaben |

Direkte Python-Werkzeuge benötigen die aktivierte Projektumgebung. Ein Dry-Run
schreibt ein Laufprotokoll und verwendet die Projektsperre. Er ist daher keine
vollständig schreibfreie Aktion. Eine Betriebssystem-Dateisperre verhindert
parallele Rechnungsläufe; getrennte Projektkopien teilen diese Sperre nicht.

Vor jedem Versand Empfänger einschließlich CC und BCC, Fälligkeit, Stunden,
Absender und Archivzugriff prüfen. Ein Test benötigt eigene Daten und begrenzte
Empfänger. Der normale CLI-Einstieg hat keine fest eingebaute Testdomain.

## Vorschau und gezielte Mailtests

`python tools/preview_customer_invoice.py <customer-id>` schreibt eine deutlich
mit `VORSCHAU` markierte PDF in das konfigurierte Kundenarchiv. Kein Versand und
kein Rechnungsverlauf; der Archivzugriff ist trotzdem ein echter Schreibvorgang.
Fehlende Stunden führen zum Abbruch.

`tools/test_mail_delivery.py` versendet eine echte technische Testmail an die
konfigurierten globalen BCC-Adressen. `tools/send_test_invoice.py` versendet eine
markierte Rechnung aus fiktiven Daten und verwendet ebenfalls die BCC-Konfiguration
als Ausgangspunkt für die Empfängerwahl. Diese Werkzeuge sind keine Dry-Runs und
verwenden nicht die Wartungsadresse aus `notifications.yaml`.

## Automatische Zeitplanung

Die Anwendung entscheidet bei jedem Lauf anhand der Daten, wer fällig ist.
Ein Scheduler startet lediglich den nicht-interaktiven Einstieg. Beispiel unter
Linux/macOS für täglich 09:00 in der Zeitzone des Cron-Dienstes:

```cron
0 9 * * * /absoluter/pfad/rechnung-automation/invoice_cron.sh
```

Unter Windows kann die Aufgabenplanung `powershell.exe` mit
`-NoProfile -File "C:\Pfad\rechnung-automation\invoice_cron.ps1"` starten.
Arbeitsverzeichnis und Benutzerrechte passend zur Installation setzen.
Alternativ einen [Windmill-Zeitplan](windmill.md) verwenden, nicht zusätzlich
Cron auf dieselben Daten aktivieren. Scheduler-/Systemzeitzone bewusst abstimmen;
die Anwendung arbeitet mit lokaler Zeit.

Exitcode `0` bedeutet einen fehlerfreien Lauf, `1` mindestens einen Fehler.
Auch fehlgeschlagene Prozesse überwachen, da eine Fehlermail nicht immer zustellbar ist.

## Versandstatus und Wiederholungen

Der maschinelle Verlauf liegt unter `data/invoice-history-<year>.json`.
Er gehört zum Produktivzustand und darf bei Updates nicht ersetzt werden.

| Status | Bedeutung und nächster Schritt |
| --- | --- |
| `sent` | Versand abgeschlossen; derselbe Monat wird übersprungen |
| `pending` | Versandannahme unklar oder Lauf unterbrochen; automatischer Neuversand blockiert, zuerst prüfen |
| `failed` | Fehlgeschlagener Versuch; im selben Monat kann erneut geprüft werden, ältere Fälle bewusst klären |
| `waiting_hours` | Stunden fehlen; im selben Monat nach Erfassung erneut prüfbar |
| `no_invoice` | Zeitraum ohne Rechnung abgeschlossen, etwa bei null Stunden |

SMTP-Annahme und lokales Speichern sind keine gemeinsame Transaktion. Bei
`pending` zuerst SMTP-/Mailserverausgang, Archiv und Logs prüfen. Nicht einfach
den Verlauf löschen oder den ganzen Lauf zurücksetzen: Die Mail könnte bereits
angenommen worden sein. Abgelaufene offene Stundenzeiträume werden ohne nachträglichen
Versand geschlossen; solche Fälle vor weiterer Abrechnung fachlich prüfen.

## Technische Fehlerberichte

Die Datei `config/notifications.yaml` separat aus der
[Vorlage](https://github.com/jan-erbert/rechnung-automation/blob/main/sample/notifications.sample.yaml) anlegen und privat halten:

```yaml
enabled: true
recipient: wartung@example.com
```

Es wird genau eine eigene Wartungsadresse gepflegt. Sie ist unabhängig von
Rechnungsempfängern und BCC. Automatische Sendeläufe melden Fehler mit sicherem
Fehlercode, Zeitpunkt und Laufkennung; keine Kundendaten oder Rohlogs anhängen.
Interaktive Läufe zeigen Fehler im Terminal. Dry-Runs verschicken keine Fehlerberichte.
Der [Windmill-Flow](windmill.md) nutzt einen gesonderten Fehlerhandler, um doppelte
Benachrichtigungen zu vermeiden.

Schlägt SMTP selbst fehl, kann auch der Fehlerbericht scheitern. Der Lauf bleibt
fehlerhaft und wird geloggt; eine gescheiterte Zustellung zählt nicht als `sent`.
Die Wartungsmail ersetzt keine Überwachung des Exitcodes oder Flowstatus.

## Logs

`logging.enabled`, `directory`, `level` und `retention_files` werden in den
Settings gepflegt. Standard sind `logs/`, `INFO` und maximal 100 eigene Logs.
Dateinamen unterscheiden `invoice-interactive-`, `invoice-cron-`,
`invoice-dry-run-`, `invoice-preview-` und Werkzeugläufe. Zeitgleiche Namen erhalten
Suffixe wie `-02`. Unter POSIX werden neue Logs mit `0600` angelegt; die
Aufbewahrung löscht nur eigene `invoice-*.log`, keine fremden Logdateien.
Logs enthalten Betriebsinformationen und gehören nicht ins öffentliche Repository.

## Zustandsbackups und Wiederherstellung

Echte Läufe erstellen standardmäßig vorab eine verifizierte ZIP-Sicherung unter
`backup/state-backup-YYYY-MM-DD_HH-MM-SS.zip`. `backup.keep_last` begrenzt die
Aufbewahrung, standardmäßig auf 30. Enthalten sind private Rechnungskonfiguration,
Kunden, Stunden und Versandverläufe. **Nicht enthalten:** `.env` und externe
PDF-Archive. Diese separat sichern.

Manuell, in der aktivierten Projektumgebung:

```bash
python tools/manage_backups.py create
python tools/manage_backups.py verify backup/state-backup-YYYY-MM-DD_HH-MM-SS.zip
```

Wiederherstellung ausschließlich in einen neuen oder leeren Ordner:

```bash
python tools/manage_backups.py restore backup/state-backup-YYYY-MM-DD_HH-MM-SS.zip backup/restored-state
```

Danach Scheduler gestoppt lassen und konsistenten Daten-/Verlaufsstand prüfen,
bevor Dateien übernommen werden. Eine Sicherung macht bereits versandte Mails
nicht rückgängig. Ein lokales Zustandsbackup ersetzt keine getrennt aufbewahrte
Sicherung der gesamten Installation.
