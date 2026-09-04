# Nicht-interaktiver Einstieg fuer die Windows-Aufgabenplanung.

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$ProjectRoot = $PSScriptRoot
$Python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
$MainScript = Join-Path $ProjectRoot "src\main.py"

if (-not (Test-Path $Python -PathType Leaf)) {
    Write-Error "Virtuelle Umgebung nicht gefunden: $Python"
    exit 1
}

& $Python $MainScript --non-interactive
exit $LASTEXITCODE
