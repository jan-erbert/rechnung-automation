# install.ps1 - Einrichtungsskript fuer Windows

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = (Resolve-Path (Join-Path $ScriptDir "..")).Path
$RequirementsFile = Join-Path $ScriptDir "requirements.txt"
$EnvWriter = Join-Path $ScriptDir "write_env.py"
$VenvPython = Join-Path $ProjectRoot ".venv\Scripts\python.exe"

Set-Location $ProjectRoot

function Read-Required {
    param([string]$Prompt)

    do {
        $Value = Read-Host $Prompt
        if ([string]::IsNullOrWhiteSpace($Value)) {
            Write-Host "Dieses Feld ist erforderlich."
        }
    } until (-not [string]::IsNullOrWhiteSpace($Value))

    return $Value.Trim()
}

function Read-RequiredInt {
    param([string]$Prompt)

    do {
        $RawValue = Read-Required $Prompt
        $ParsedValue = 0
        $IsValid = [int]::TryParse($RawValue, [ref]$ParsedValue)
        if (-not $IsValid) {
            Write-Host "Bitte eine ganze Zahl eingeben."
        }
    } until ($IsValid)

    return $ParsedValue
}

function Read-Port {
    param([string]$Prompt)

    do {
        $Value = Read-RequiredInt $Prompt
        $IsValid = $Value -ge 1 -and $Value -le 65535
        if (-not $IsValid) {
            Write-Host "Bitte einen Port zwischen 1 und 65535 eingeben."
        }
    } until ($IsValid)

    return $Value
}

function Read-Percentage {
    param([string]$Prompt)

    do {
        $Value = Read-RequiredInt $Prompt
        $IsValid = $Value -ge 0 -and $Value -le 100
        if (-not $IsValid) {
            Write-Host "Bitte einen ganzzahligen Prozentsatz zwischen 0 und 100 eingeben."
        }
    } until ($IsValid)

    return $Value
}

function Read-RequiredSecret {
    param([string]$Prompt)

    do {
        $SecureValue = Read-Host $Prompt -AsSecureString
        $Value = [System.Net.NetworkCredential]::new("", $SecureValue).Password
        if ([string]::IsNullOrWhiteSpace($Value)) {
            Write-Host "Dieses Feld ist erforderlich."
        }
    } until (-not [string]::IsNullOrWhiteSpace($Value))

    return $Value
}

function Read-YesNo {
    param([string]$Prompt)

    do {
        $Value = (Read-Host $Prompt).Trim().ToLowerInvariant()
    } until ($Value -in @("j", "ja", "y", "yes", "n", "nein", "no"))

    return $Value -in @("j", "ja", "y", "yes")
}

function Read-TaxId {
    # Fragt die steuerliche Identifikationsnummer fuer Rechnungen ab.
    Write-Host "Welche steuerliche Identifikationsnummer soll auf Rechnungen stehen?"
    Write-Host "1) Steuernummer"
    Write-Host "2) Umsatzsteuer-Identifikationsnummer (USt-IdNr.)"

    do {
        $Selection = (Read-Host "Auswahl (1/2)").Trim()
    } until ($Selection -in @("1", "2"))

    if ($Selection -eq "2") {
        return [ordered]@{
            steuer_id_typ = "ust_id"
            ust_id = Read-Required "Umsatzsteuer-Identifikationsnummer (USt-IdNr.)"
        }
    }

    return [ordered]@{
        steuer_id_typ = "steuernummer"
        steuernummer = Read-Required "Steuernummer"
    }
}

Write-Host "Starte Einrichtung der virtuellen Umgebung..."

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    throw "Python wurde nicht gefunden. Bitte installiere Python 3."
}

if (-not (Test-Path $VenvPython -PathType Leaf)) {
    if (Test-Path ".venv") {
        throw ".venv ist vorhanden, aber unvollstaendig oder nicht verwendbar. Bitte den Ordner bewusst entfernen und den Installer erneut starten."
    }
    python -m venv .venv
    Write-Host "Virtuelle Umgebung wurde erstellt."
} else {
    Write-Host ".venv ist bereits vorhanden."
}

if (-not (Test-Path $RequirementsFile)) {
    throw "Requirements-Datei nicht gefunden: $RequirementsFile"
}

Write-Host "Installiere Pakete aus install/requirements.txt..."
& $VenvPython -m pip install -r $RequirementsFile

$EnvPath = Join-Path $ProjectRoot ".env"
if (-not (Test-Path $EnvPath)) {
    Write-Host "Lokale Mail-Konfiguration wird erstellt (.env)..."

    $MailServer = Read-Required "SMTP-Server"
    $MailPort = Read-Port "SMTP-Port"
    $MailUser = Read-Required "SMTP-Benutzer"
    $MailPass = Read-RequiredSecret "SMTP-Passwort"

    if (-not (Test-Path $EnvWriter -PathType Leaf)) {
        throw "Env-Helfer nicht gefunden: $EnvWriter"
    }

    $env:MAIL_SERVER = $MailServer
    $env:MAIL_PORT = [string]$MailPort
    $env:MAIL_USER = $MailUser
    $env:MAIL_PASS = $MailPass
    try {
        & $VenvPython $EnvWriter $EnvPath
    } finally {
        Remove-Item Env:MAIL_SERVER, Env:MAIL_PORT, Env:MAIL_USER, Env:MAIL_PASS -ErrorAction SilentlyContinue
    }

    Write-Host ".env wurde erstellt."
} else {
    Write-Host ".env ist bereits vorhanden - keine Aenderung vorgenommen."
}

$ConfigPath = Join-Path $ProjectRoot "data\konfiguration.json"
if (-not (Test-Path $ConfigPath)) {
    Write-Host "Konfigurationsdatei wird erstellt (data/konfiguration.json)..."

    $Website = Read-Host "Webseite (optional)"

    $Absender = [ordered]@{
        name = Read-Required "Dein Name"
        firma = Read-Required "Firmenname"
        "straße" = Read-Required "Strasse und Hausnummer"
        plz = Read-Required "PLZ"
        ort = Read-Required "Ort"
        telefon = Read-Required "Telefonnummer"
        email = Read-Required "E-Mail-Adresse"
        website = $Website.Trim()
    }

    $Bank = [ordered]@{
        bankname = Read-Required "Bankname"
        kontoinhaber = Read-Required "Kontoinhaber"
        iban = Read-Required "IBAN"
        bic = Read-Required "BIC"
    }

    $Kleinunternehmer = Read-YesNo "Kleinunternehmerregelung nach Paragraph 19 UStG? (j/n)"
    $Finanzen = Read-TaxId
    $Finanzen["finanzamt"] = Read-Required "Finanzamt"
    $Finanzen["kleinunternehmer"] = $Kleinunternehmer

    if (-not $Kleinunternehmer) {
        $Finanzen["mehrwertsteuer_prozent"] = Read-Percentage "Mehrwertsteuersatz in Prozent"
    }

    Write-Host "Hinweis: Fuer steuerkonforme Rechnungen muss eine Kopie gemaess Paragraph 14b UStG aufbewahrt werden."
    $Bcc = Read-Host "BCC-Empfaenger (optional, empfohlen zur Archivierung)"
    $MailFromName = Read-Host "Sichtbarer Mail-Absendername (optional)"

    $Config = [ordered]@{
        absender = $Absender
        bank = $Bank
        finanzen = $Finanzen
        mail = [ordered]@{
            bcc = $Bcc.Trim()
            from_name = $MailFromName.Trim()
        }
    }

    New-Item -Path (Join-Path $ProjectRoot "data") -ItemType Directory -Force | Out-Null
    $Config | ConvertTo-Json -Depth 5 | Set-Content -Path $ConfigPath -Encoding UTF8
    Write-Host "konfiguration.json wurde gespeichert."
} else {
    Write-Host "konfiguration.json ist bereits vorhanden - keine Aenderung vorgenommen."
}

$RunScript = Join-Path $ProjectRoot "rechnung_generieren.ps1"
if (Test-Path $RunScript) {
    $Desktop = [Environment]::GetFolderPath("Desktop")
    if (-not [string]::IsNullOrWhiteSpace($Desktop)) {
        $LinkPath = Join-Path $Desktop "Rechnung starten.lnk"
        $PowerShellExe = (Get-Command powershell.exe).Source
        $Shortcut = (New-Object -ComObject WScript.Shell).CreateShortcut($LinkPath)
        $Shortcut.TargetPath = $PowerShellExe
        $Shortcut.Arguments = "-ExecutionPolicy Bypass -File `"$RunScript`""
        $Shortcut.WorkingDirectory = $ProjectRoot
        $Shortcut.WindowStyle = 1
        $Shortcut.Save()
        Write-Host "Desktop-Verknuepfung 'Rechnung starten' wurde erstellt."
    }
}

Write-Host "Projekt ist bereit. Starte Rechnungen unter Windows mit .\rechnung_generieren.ps1."
