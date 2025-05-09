# install.ps1 – Einrichtungsskript für das Rechnungssystem

Write-Host "🔧 Starte Einrichtung der virtuellen Umgebung..."

# 1. Virtuelle Umgebung erstellen, falls nicht vorhanden
if (-Not (Test-Path ".venv")) {
    python -m venv .venv
    Write-Host "✅ Virtuelle Umgebung wurde erstellt."
} else {
    Write-Host "🔁 .venv bereits vorhanden."
}

# 2. Umgebung aktivieren (nur Hinweis)
Write-Host "🪄 Virtuelle Umgebung aktiviert (bitte manuell aktivieren bei Bedarf)."

# 3. Abhängigkeiten installieren
if (Test-Path "requirements.txt") {
    Write-Host "📦 Installiere Pakete aus requirements.txt..."
    pip install -r requirements.txt
} else {
    Write-Host "⚠️ Keine requirements.txt gefunden."
}

# 4. Beispieldateien kopieren
if (-Not (Test-Path "daten.json")) {
    Copy-Item -Path "sample\daten.sample.jsonc" -Destination "daten.json"
    Write-Host "📄 daten.json erstellt."
}

if (-Not (Test-Path "environment.env")) {
    Copy-Item -Path "sample\environment.sample.env" -Destination "environment.env"
    Write-Host "🔐 environment.env erstellt."
}

Write-Host ""
Write-Host "✅ Projekt ist bereit! Du kannst jetzt 'mail_versenden.py' ausführen."
