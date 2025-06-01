chcp 65001
Write-Host "Starte Rechnungsgenerierung..."

# Virtuelle Umgebung aktivieren
$venvPath = "$PSScriptRoot\.venv\Scripts\Activate.ps1"
if (Test-Path $venvPath) {
    & $venvPath
    python "$PSScriptRoot\src\main.py"
} else {
    Write-Host "⚠️ Virtuelle Umgebung nicht gefunden unter: $venvPath"
    Pause
    exit 1
}

Pause
# Hinweis: Stelle sicher, dass die virtuelle Umgebung und die Python-Skripte korrekt eingerichtet sind.