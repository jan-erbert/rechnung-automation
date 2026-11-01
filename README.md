# Rechnung-Automation

Python-Tool zur Erstellung, Archivierung und zum SMTP-Versand von Rechnungen.
Es läuft interaktiv, als Cronjob oder optional als Windmill-Flow unter Linux,
Windows und macOS. Die Rechnungslogik ist für alle Einstiege dieselbe.

**Letzter Release: 1.4.1.** Dieses Handbuch beschreibt den aktuellen Quellstand;
noch nicht veröffentlichte Änderungen stehen im [Changelog](CHANGELOG.md).
Das neue Kontaktschema erfordert eine bewusste [Datenumstellung](docs/kunden.md).

## Was das Tool bietet

- PDF-Rechnungen aus anpassbaren HTML-Vorlagen mit WeasyPrint
- Optionale ZUGFeRD-PDF mit eingebetteter XML, ohne Java
- Monatliche, pauschale, einmalige und stundenbasierte Abrechnung
- SMTP mit TLS, CC/BCC und eigener technischer Fehleradresse
- YAML-Kundenakten, nachvollziehbarer Versandverlauf und Zustandsbackups
- Konfigurierbares Branding, Tabellenfarben, Symbole und PDF-Seitenabstände
- Optionale Windmill-Flows und Kundenformulare mit SMTP-Ressourcen/OpenBao

## Einstieg

Python ab 3.10 und die Systembibliotheken für WeasyPrint werden benötigt.
Die [Installation](docs/installation.md) beschreibt Einrichtung und Voraussetzungen.
Im frisch geklonten Projekt:

```bash
# Linux und macOS
./install/install.sh
```

```powershell
# Windows PowerShell
./install/install.ps1
```

Danach private Absender-/SMTP-Daten und Kunden nach den mitgelieferten Vorlagen
pflegen. Die Installer überschreiben bestehende private Dateien nicht und
richten keinen Zeitplan ein. Vor einem Versand zuerst prüfen:

```bash
# In der aktivierten .venv, aus dem Projektverzeichnis
python tools/check_setup.py
```

Ein ausdrücklich gestarteter Dry-Run rendert fällige PDFs im Speicher und
schreibt ein Log. Er versendet nichts und verändert keinen Rechnungszustand:

```bash
./generate_invoices.sh --dry-run
```

```powershell
./generate_invoices.ps1 -DryRun
```

**Die Startskripte ohne Dry-Run-Schalter versenden echte Rechnungen.**
Vorher Empfänger einschließlich CC/BCC, Fälligkeit und Archivpfade kontrollieren.
Der [Betriebsleitfaden](docs/betrieb.md) erklärt Vorschau, Zeitplanung und Fehlerfälle.

## Handbuch

Das vollständige Handbuch liegt versioniert unter [docs/](docs/index.md).
Es ist zugleich die Quelle für Backstage TechDocs und die beiden Projekt-Wikis:
[GitHub-Wiki](https://github.com/jan-erbert/rechnung-automation/wiki) ·
[Forgejo-Wiki](https://git.jecloud.de/adminjan/rechnung-automation/wiki).

| Thema | Inhalt |
| --- | --- |
| [Installation](docs/installation.md) | Linux, Windows, macOS und bestehende Installationen |
| [Konfiguration](docs/konfiguration.md) | Absender, SMTP, Design, Vorlagen und Dateipfade |
| [Kunden und Abrechnung](docs/kunden.md) | Anreden, Fälligkeit, Stunden und zukünftige Konditionen |
| [Betrieb](docs/betrieb.md) | Laufarten, Scheduler, Versandstatus, Fehler und Backups |
| [ZUGFeRD](docs/zugferd.md) | Optionale Installation, Formatwahl und XML-Prüfung |
| [Windmill](docs/windmill.md) | Flows, Ressourcen, OpenBao und Kundenformulare |
| [Entwicklung](docs/entwicklung.md) | Tests, Dokumentationspflege, Git und Releases |

Konfigurationsbeispiele stehen unter [sample/](sample/). Private Daten,
Zugangsdaten, Logs und Rechnungen gehören nicht in Git.

## Lizenz

Projektlizenz: [LICENSE.md](LICENSE.md). Hinweise zu eingebundenen Komponenten
und Symbolen: [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
