# Entwicklung und Releases

Dieses Projekt kann Rechnungen erzeugen, E-Mails versenden und Daten verändern.
Entwicklung und Tests verwenden deshalb isolierte, fiktive Daten. Die lokalen
Arbeitsregeln stehen in [AGENTS.md](https://github.com/jan-erbert/rechnung-automation/blob/main/AGENTS.md).

## Arbeitsumgebung und Branches

Eine eigene Arbeitskopie verwenden und im Projektverzeichnis installieren:

```bash
python -m venv .venv
# Linux/macOS: source .venv/bin/activate
# Windows PowerShell: .venv\Scripts\Activate.ps1
python -m pip install -r install/requirements.txt -r install/requirements-dev.txt
```

Vor Änderungen `git status` und den passenden Branch prüfen. Features und Fixes
entstehen auf `feature/...`, `fix/...` oder einem gesonderten Entwicklungsbranch.
Vor Übernahme nach `main` Diff, Tests und Auswirkungen auf Daten prüfen; die
Übernahme erfolgt bewusst nach Review. `main` ist der freigegebene Quellstand,
kein automatisch sicherer Ersatz für eine Daten- oder Versandfreigabe.

Eine eigene Dev-Bereitstellung kann `dev` folgen. Sie verwendet eigene Kunden,
Historien, Archive und Ressourcen. Eine Dev-Prüfung aktiviert keine produktiven
Zeitpläne. Details zur optionalen Laufumgebung: [Windmill](windmill.md).

Private Konfiguration, `.env`, Kundendaten, Archive, Logs und lokale Umgebungen
nicht committen. Anwendung, Installer, Mailtest oder Kundenwerkzeuge nicht auf
einer Produktivinstallation zu Entwicklungszwecken starten. Auch ein Dry-Run
rendert PDFs und schreibt Logs beziehungsweise eine Lauf-Sperre.

## Tests und Prüfungen

Die normalen Tests verwenden isolierte Daten und simulierte Mail-/PDF-Dienste:

```bash
python -m pytest
```

Die CI prüft Python 3.10 und 3.12 auf Linux sowie Python 3.12 unter Windows und
macOS. Forgejo führt seine Tests unter Linux aus. Für Quellcode und Werkzeuge
werden folgende Scopes geprüft:

```bash
python -m black --check --diff --no-cache --workers 1 src tools tests install integrations
python -m flake8 --jobs 1 src tools tests install integrations
bash -n install/install.sh invoice_cron.sh generate_invoices.sh
```

Black wird lokal gemäß den Arbeitsregeln bewusst vom Nutzer ausgeführt. Die
Windows-CI prüft zusätzlich die Syntax der PowerShell-Dateien. Die Workflows
liegen in [.github/workflows/ci.yml](https://github.com/jan-erbert/rechnung-automation/blob/main/.github/workflows/ci.yml) und
[.forgejo/workflows/ci.yml](https://github.com/jan-erbert/rechnung-automation/blob/main/.forgejo/workflows/ci.yml).

Die separaten ZUGFeRD-Integrationstests erzeugen echte PDFs ausschließlich aus
fiktiven Testdaten. Sie benötigen die [optionalen Pakete und PDF-Bibliotheken](zugferd.md)
und werden nur ausdrücklich aktiviert:

```bash
# Linux/macOS; in einer isolierten Entwicklungsumgebung
RUN_ZUGFERD_INTEGRATION=1 python -m pytest tests/test_zugferd_integration.py
```

```powershell
$env:RUN_ZUGFERD_INTEGRATION = "1"
python -m pytest tests/test_zugferd_integration.py
Remove-Item Env:RUN_ZUGFERD_INTEGRATION
```

Die PDF-CI läuft bei GitHub auf drei Betriebssystemen, bei Forgejo auf Linux;
produktive Daten und SMTP-Secrets werden nicht benötigt.

## Eine gemeinsame Dokumentationsquelle

Das vollständige Handbuch liegt unter `docs/`. Die kurze [README](https://github.com/jan-erbert/rechnung-automation/blob/main/README.md)
ist der Einstieg; zusätzliche Wegweiser verlinken auf das Handbuch. Inhalte nur
an ihrer maßgeblichen Stelle pflegen. Beispiele bleiben fiktiv und müssen zu
aktuellen Feldern, CLI-Schaltern und den mitgelieferten Vorlagen passen.

`mkdocs.yml` enthält die Navigation für Backstage TechDocs. Der bestehende
JE-Backstage-Katalog erkennt das Repository und seine Dokumentation automatisch;
eine eigene `catalog-info.yaml` ist dafür nicht erforderlich. Backstage liest
`docs/` aus dem freigegebenen Main-Stand. Es liest nicht die separaten Wiki-Repositories.

Für einen lokalen Build in einer separaten Doku-Umgebung wird das Plugin
`mkdocs-techdocs-core==1.7.1` benötigt. Im Repository-Root prüft
`python -m mkdocs build --strict` die Dokumentation. Dies ist keine Abhängigkeit
der Rechnungsanwendung und veröffentlicht nichts. Die normale Ansicht erfolgt
über die Plattform-Wikis beziehungsweise Backstage.

Die Wikis von Forgejo und GitHub sind jeweils eigene Git-Repositories. Ein
normaler Push zu den beiden Code-Remotes aktualisiert diese Wikis nicht.
`tools/build_wiki.py` liest das Handbuch im aktuellen Checkout. Zuerst den
gewünschten Stand auschecken und dann einen neuen, leeren Ausgabeordner angeben:

```bash
python tools/build_wiki.py --output-dir /tmp/rechnung-wiki \
  --repository-url https://github.com/DEIN-KONTO/rechnung-automation \
  --ref vX.Y.Z --ref-type tag
```

`--ref` setzt nur die Quellenlinks und checkt keinen anderen Stand aus.
`--ref-type` ist für Branches `branch` (Standard), für Tags `tag` und für
Commit-IDs `commit`; Forgejo verwendet dafür unterschiedliche Quellpfade. Für
Forgejo denselben Checkout mit dessen Repository-URL in einen zweiten Ordner
exportieren. Das Werkzeug verbindet sich nicht mit den Plattformen und pusht nicht.

Erzeugte Inhalte erst prüfen, dann nach ausdrücklicher Freigabe die beiden
Wiki-Repositories (`<repository>.wiki.git`) separat klonen und ihren Stand
aktualisieren. Erzeugte Markdown-Seiten übernehmen, Diff prüfen und jeweils
committen/pushen; den `.git`-Ordner der Wikis erhalten. Das Werkzeug erzeugt auch
Wegweiser für alte Seitenadressen. Anschließend Hauptseiten, Navigation und
Quelllinks auf beiden Plattformen prüfen. Inhalte ausschließlich unter `docs/` pflegen;
ein Dokumentationsentwurf ist keine Freigabe zur Veröffentlichung.
Es werden keine automatischen Push-Hooks oder CI-Veröffentlichungen eingerichtet.
Eine freigegebene Dokumentationsaktualisierung kann unabhängig von einem neuen
Software-Release veröffentlicht werden.

## Release vorbereiten und freigeben

Der letzte veröffentlichte Stand ist `1.4.1`; die zentrale Versionsangabe liegt
in [install/version.py](https://github.com/jan-erbert/rechnung-automation/blob/main/install/version.py). Änderungen danach stehen im
[Changelog](https://github.com/jan-erbert/rechnung-automation/blob/main/CHANGELOG.md) unter `Unreleased` und sind noch kein neuer Release.
Insbesondere ersetzt das neue Kontaktschema `contact.name` durch drei Felder.
Bestehende Kundendaten benötigen vor dem Update die bewusste [Umstellung](kunden.md).

1. Umfang, Migration und Versionssprung prüfen. Die inkompatible Schemaänderung
   spricht für einen neuen Hauptversionsstand; Nummer erst bei Freigabe festlegen.
2. Versionsdatei, Changelog, Handbuch und Beispielkonfigurationen abgleichen.
   Erforderliche Tests und CI auf dem konkreten Kandidaten abschließen.
3. Erst nach Betreiberfreigabe nach Main übernehmen, Tag und Release auf beiden
   Plattformen veröffentlichen. Release-Notizen nennen Änderungen, Migration
   und Installationsweg; private Laufdaten gehören nicht hinein.
4. Wiki-Ausgabe aus genau dieser freigegebenen Referenz erzeugen, prüfen und
   separat veröffentlichen. Danach Versions- und Dokumentationslinks kontrollieren.
