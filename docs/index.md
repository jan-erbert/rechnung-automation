# Handbuch: Rechnung-Automation

Rechnung-Automation erzeugt Rechnungen aus YAML-Kundenakten, rendert PDFs und
versendet sie per SMTP. CLI, Cron und optionale Windmill-Flows teilen sich die
Python-Anwendungslogik. Windmill und OpenBao sind keine Voraussetzung.

Dieses Handbuch beschreibt **Version 2.0.0**. Änderungen und Hinweise zu Updates
stehen im [Changelog](https://github.com/jan-erbert/rechnung-automation/blob/main/CHANGELOG.md).
Vor dem Wechsel von 1.4.1 die [Umstellung der Kundenkontakte](kunden.md) beachten.

## Einrichtung in sinnvoller Reihenfolge

1. [Installation vorbereiten](installation.md) und virtuelle Umgebung einrichten.
2. [Absender, SMTP und Design konfigurieren](konfiguration.md).
3. [Kunden und Fälligkeiten pflegen](kunden.md). Ein aktiver Kunde ohne Verlauf
   kann bereits beim nächsten Lauf fällig sein.
4. Setup prüfen, Dry-Run ansehen und erst danach einen echten
   [Rechnungslauf oder Zeitplan](betrieb.md) freigeben.
5. Bei Bedarf [ZUGFeRD](zugferd.md) oder [Windmill](windmill.md) ergänzen.

## Themen

| Anleitung | Was dort steht |
| --- | --- |
| [Installation](installation.md) | Voraussetzungen, Installer, Updates und Migration |
| [Konfiguration](konfiguration.md) | Dateien, SMTP, Branding und Vorlagen |
| [Kunden](kunden.md) | Anreden, Leistungsarten, Stunden und Änderungen |
| [Betrieb](betrieb.md) | Versand, Scheduler, Logs, Fehlerberichte und Sicherungen |
| [ZUGFeRD](zugferd.md) | PDF mit eingebetteter XML und lokale Prüfungen |
| [Windmill](windmill.md) | Gemeinsame Logik als Flow und Kundenformulare |
| [Entwicklung](entwicklung.md) | Tests, Dokumentation und Releaseprozess |

## Quellcode und private Laufdaten

| Verzeichnis | Aufgabe |
| --- | --- |
| `src/`, `templates/`, `integrations/` | Python-Logik, HTML und optionale Adapter |
| `config/settings.yaml` | Versionierte technische Voreinstellungen |
| `sample/` | Öffentliche Vorlagen mit fiktiven Daten |
| `customers/`, `hours/`, `data/` | Private Kunden, Stunden und Versandzustände |
| `config/invoice.yaml`, `config/notifications.yaml`, `.env` | Private Konfiguration |
| `backup/`, `logs/`, konfigurierte Archive | Laufdaten und Sicherungen |
| `docs/`, `mkdocs.yml` | Handbuch und Backstage-Anbindung |

Die HTML-Dokumentation und die Wikis werden aus `docs/` erzeugt; sie sind kein
zusätzliches Rechnungssystem. Eigene NAS-Pfade, Zugänge und konkrete Zeitpläne
gehören in die Betriebsdokumentation der jeweiligen Installation.

Projektlizenz: [LICENSE.md](https://github.com/jan-erbert/rechnung-automation/blob/main/LICENSE.md). Komponenten und Symbole:
[THIRD_PARTY_NOTICES.md](https://github.com/jan-erbert/rechnung-automation/blob/main/THIRD_PARTY_NOTICES.md).
