# generate_invoices.ps1 - Startskript fuer Windows

param(
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$ProjectRoot = $PSScriptRoot
$Python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
$MainScript = Join-Path $ProjectRoot "src\main.py"

Write-Host "Starte Rechnungsgenerierung..."

if (-not (Test-Path $Python)) {
    Write-Host "Virtuelle Umgebung nicht gefunden: $Python"
    Read-Host "Enter druecken zum Beenden"
    exit 1
}

if ($DryRun) {
    & $Python $MainScript --dry-run
} else {
    & $Python $MainScript
}
$ExitCode = $LASTEXITCODE

if ($ExitCode -ne 0) {
    Write-Host "Rechnungsgenerierung wurde mit Fehlercode $ExitCode beendet."
}

Read-Host "Enter druecken zum Beenden"
exit $ExitCode
