# install.ps1 – Einrichtungsskript für das Rechnungssystem

Write-Host "🔧 Starte Einrichtung der virtuellen Umgebung..."

# 1. Virtuelle Umgebung erstellen, falls nicht vorhanden
if (-Not (Test-Path ".venv")) {
    python -m venv .venv
    Write-Host "✅ Virtuelle Umgebung wurde erstellt."
} else {
    Write-Host "🔁 .venv bereits vorhanden."
}

# 2. Hinweis zur Aktivierung
Write-Host "💡 Bitte aktiviere die Umgebung mit:"
Write-Host "   .\.venv\Scripts\Activate.ps1"
Write-Host ""

# 3. Abhängigkeiten installieren
if (Test-Path "requirements.txt") {
    Write-Host "📦 Installiere Pakete aus requirements.txt..."
    .\.venv\Scripts\pip.exe install -r requirements.txt
} else {
    Write-Host "⚠️ Keine requirements.txt gefunden."
}

# 4. Beispieldateien kopieren (wenn nicht vorhanden)
if (-Not (Test-Path "daten.json")) {
    Copy-Item -Path "sample\daten.sample.jsonc" -Destination "daten.json"
    Write-Host "📄 daten.json wurde erstellt."
}

if (-Not (Test-Path "environment.env")) {
    Copy-Item -Path "sample\environment.sample.env" -Destination "environment.env"
    Write-Host "🔐 environment.env wurde erstellt."
}

if (-Not (Test-Path "vorlagen\rechnung_template.html")) {
    Copy-Item -Path "sample\rechnung_template.sample.html" -Destination "vorlagen\rechnung_template.html"
    Write-Host "🧾 rechnung_template.html wurde erstellt."
}

if (-Not (Test-Path "vorlagen\mail_template.html")) {
    Copy-Item -Path "sample\mail_template.sample.html" -Destination "vorlagen\mail_template.html"
    Write-Host "📧 mail_template.html wurde erstellt."
}

Write-Host ""
Write-Host "✅ Projekt ist bereit! Du kannst jetzt 'mail_versenden.py' ausführen."
