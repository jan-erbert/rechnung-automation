# Installation und Updates

## Voraussetzungen

- Python ab 3.10, Git und eine passende virtuelle Umgebung.
- Systembibliotheken und Schriftarten für WeasyPrint. Die benötigten Pakete
  unterscheiden sich je nach Betriebssystem; die maßgebliche Anleitung ist die
  [WeasyPrint-Installation](https://doc.courtbouillon.org/weasyprint/stable/first_steps.html).
- Ein SMTP-Konto mit STARTTLS oder implizitem TLS für tatsächlichen Versand.
- Schreibbare Verzeichnisse für private Laufdaten, Backups und gewünschte Archive.

Linux und macOS verwenden Bash-Skripte, Windows PowerShell. Unter Windows müssen
zusätzlich die WeasyPrint-DLLs erreichbar sein; die Python-Pakete allein reichen
nicht. Optionale [ZUGFeRD-Pakete](zugferd.md) haben eigene Plattformvoraussetzungen.

## Neu einrichten

Repository klonen, in den Projektordner wechseln und den passenden Installer starten:

```bash
# Linux/macOS
./install/install.sh
```

```powershell
# Windows
./install/install.ps1
```

Die Installer erzeugen `.venv`, installieren die festgelegten Abhängigkeiten und
legen `.env`, `config/invoice.yaml` sowie Laufverzeichnisse an. Bestehende private
Dateien bleiben erhalten. Es werden keine Kunden und keine Zeitpläne angelegt.
Die technische Fehleradresse wird separat konfiguriert.

Anschließend [Konfiguration](konfiguration.md) und [Kunden](kunden.md) pflegen.
Die Shell-/PowerShell-Startskripte finden die Projektumgebung selbst. Für direkte
Python-Werkzeuge zuerst die virtuelle Umgebung aktivieren:

```bash
source .venv/bin/activate
```

```powershell
.venv\Scripts\Activate.ps1
```

Alle folgenden `python`-Beispiele setzen diese Umgebung und das Projektverzeichnis
als Arbeitsverzeichnis voraus. Ohne Aktivierung kann der Interpreter direkt als
`.venv/bin/python` beziehungsweise `.venv\Scripts\python.exe` angesprochen werden.

## Einrichtung prüfen

```bash
python tools/check_setup.py
```

Der Check prüft Konfiguration, Kunden, Stunden, Templates, Branding und Pfade.
Er erzeugt keine Rechnungen und stellt keine SMTP-Verbindung her. Für Schreibziele
kann er kurzlebige Testdateien erstellen und unmittelbar entfernen. Ohne Kunden
ist die Einrichtung noch nicht für einen Rechnungslauf vollständig.

Der nächste Schritt ist ein bewusst gestarteter [Dry-Run](betrieb.md), kein
automatischer Versandtest. Erst danach echte Empfänger und Scheduler freigeben.

## Bestehende Installation aktualisieren

1. Zeitplanung pausieren und sicherstellen, dass kein Rechnungslauf aktiv ist.
2. Private Konfiguration, Kunden, Stunden, Versandverläufe und Archive sichern.
3. Arbeitsbaum und [Changelog](https://github.com/jan-erbert/rechnung-automation/blob/main/CHANGELOG.md) prüfen, dann den freigegebenen
   Quellstand übernehmen. Bei Git-Installationen nur nachvollziehbar vorwärts
   aktualisieren; lokale Änderungen nicht überschreiben.
4. Abhängigkeiten in der Projektumgebung aktualisieren:

   ```bash
   python -m pip install -r install/requirements.txt
   ```

5. Erforderliche Datenanpassungen durchführen, Setup und Dry-Run prüfen.
   Scheduler erst nach Prüfung wieder einschalten.

Ein `git pull` allein installiert keine neuen Abhängigkeiten. Im Containerbetrieb
muss eine passende Worker-Laufzeit bereits vor der Codeübernahme vorhanden sein.
Private Daten bleiben außerhalb der Quellcodeaktualisierung.

## Ältere JSON-Struktur und Kontaktschema

**Inkompatible Änderung:** Das frühere `contact.name` wird nicht mehr akzeptiert.
Vor dem ersten Lauf müssen Vorname, Nachname und Anrede ausdrücklich gepflegt
sein; siehe [Kunden](kunden.md). Eine automatische Namenszerlegung findet nicht statt.

Für entsprechend vorbereitete Legacy-Daten gibt es getrennte Werkzeuge:

| Werkzeug unter `tools/` | Inhalt |
| --- | --- |
| `migrate_legacy_data.py` | Rechnungs-/Kunden-JSON nach YAML |
| `migrate_legacy_hours.py` | Alte Stunden-JSON nach Monats-YAML |
| `migrate_legacy_layout.py` | Alte Verlauf-/Template-Struktur |

Bei Daten- und Stundenmigration zuerst die Vorschau ohne Schalter ansehen,
mit `--apply` schreiben und anschließend mit `--verify` vergleichen. Bestehende
widersprüchliche Ziele führen zum Abbruch. Alte Quellen bleiben erhalten;
`--delete-legacy` ist eine gesonderte, endgültige Löschoption dieser beiden Werkzeuge
und für die Umstellung nicht erforderlich.

Installer und normale Programmstarts können dieselbe vorbereitete Legacy-Migration
idempotent ausführen. Fehlende Namensfelder müssen trotzdem vorher korrigiert
werden. Deshalb Updates zunächst auf einer gesicherten Kopie prüfen. Ein Dry-Run
schreibt keine Legacy-Migration.
