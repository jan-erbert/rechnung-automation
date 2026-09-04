# install.ps1 - Einrichtungsskript fuer Windows

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = (Resolve-Path (Join-Path $ScriptDir "..")).Path
$RequirementsFile = Join-Path $ScriptDir "requirements.txt"
$EnvWriter = Join-Path $ScriptDir "write_env.py"
$ConfigWriter = Join-Path $ScriptDir "write_config.py"
$LegacyMigrator = Join-Path $ProjectRoot "tools\migrate_legacy_layout.py"
$SetupCheck = Join-Path $ProjectRoot "tools\check_setup.py"
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
            type = "vat_id"
            value = Read-Required "Umsatzsteuer-Identifikationsnummer (USt-IdNr.)"
        }
    }

    return [ordered]@{
        type = "tax_number"
        value = Read-Required "Steuernummer"
    }
}

function Assert-NativeSuccess {
    param([string]$Description)

    if ($LASTEXITCODE -ne 0) {
        throw "$Description ist mit Exitcode $LASTEXITCODE fehlgeschlagen."
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
    Assert-NativeSuccess "Erstellen der virtuellen Umgebung"
    Write-Host "Virtuelle Umgebung wurde erstellt."
} else {
    Write-Host ".venv ist bereits vorhanden."
}

if (-not (Test-Path $RequirementsFile)) {
    throw "Requirements-Datei nicht gefunden: $RequirementsFile"
}

Write-Host "Installiere Pakete aus install/requirements.txt..."
& $VenvPython -m pip install -r $RequirementsFile
Assert-NativeSuccess "Installation der Python-Abhaengigkeiten"

& $VenvPython $LegacyMigrator
Assert-NativeSuccess "Legacy-Migration"

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
        Assert-NativeSuccess "Schreiben der Mail-Konfiguration"
    } finally {
        Remove-Item Env:MAIL_SERVER, Env:MAIL_PORT, Env:MAIL_USER, Env:MAIL_PASS -ErrorAction SilentlyContinue
    }

    Write-Host ".env wurde erstellt."
} else {
    Write-Host ".env ist bereits vorhanden - keine Aenderung vorgenommen."
}

$ConfigPath = Join-Path $ProjectRoot "config\invoice.yaml"
if (-not (Test-Path $ConfigPath)) {
    Write-Host "Konfigurationsdatei wird erstellt (config/invoice.yaml)..."

    $Website = Read-Host "Webseite (optional)"

    $Sender = [ordered]@{
        name = Read-Required "Dein Name"
        company = Read-Required "Firmenname"
        street = Read-Required "Strasse und Hausnummer"
        postal_code = Read-Required "PLZ"
        city = Read-Required "Ort"
        phone = Read-Required "Telefonnummer"
        email = Read-Required "E-Mail-Adresse"
        website = $Website.Trim()
    }

    $Bank = [ordered]@{
        name = Read-Required "Bankname"
        account_holder = Read-Required "Kontoinhaber"
        iban = Read-Required "IBAN"
        bic = Read-Required "BIC"
    }

    $SmallBusiness = Read-YesNo "Kleinunternehmerregelung nach Paragraph 19 UStG? (j/n)"
    $TaxId = Read-TaxId
    $TaxOffice = Read-Required "Finanzamt"

    if (-not $SmallBusiness) {
        $VatRate = Read-Percentage "Mehrwertsteuersatz in Prozent"
    } else {
        $VatRate = ""
    }

    Write-Host "Hinweis: Fuer steuerkonforme Rechnungen muss eine Kopie gemaess Paragraph 14b UStG aufbewahrt werden."
    $Bcc = Read-Host "BCC-Empfaenger (optional, empfohlen zur Archivierung)"
    $MailFromName = Read-Host "Sichtbarer Mail-Absendername (optional)"

    if (-not (Test-Path $ConfigWriter -PathType Leaf)) {
        throw "Konfigurationshelfer nicht gefunden: $ConfigWriter"
    }

    $SetupValues = @{
        SETUP_CONTACT_NAME = $Sender.name; SETUP_COMPANY = $Sender.company
        SETUP_STREET = $Sender.street; SETUP_POSTAL_CODE = $Sender.postal_code
        SETUP_CITY = $Sender.city; SETUP_PHONE = $Sender.phone
        SETUP_EMAIL = $Sender.email; SETUP_WEBSITE = $Sender.website
        SETUP_BANK_NAME = $Bank.name; SETUP_ACCOUNT_HOLDER = $Bank.account_holder
        SETUP_IBAN = $Bank.iban; SETUP_BIC = $Bank.bic
        SETUP_TAX_IDENTIFIER_TYPE = $TaxId.type; SETUP_TAX_IDENTIFIER_VALUE = $TaxId.value
        SETUP_TAX_OFFICE = $TaxOffice
        SETUP_SMALL_BUSINESS = $SmallBusiness.ToString().ToLowerInvariant()
        SETUP_VAT_RATE = [string]$VatRate; SETUP_BCC = $Bcc.Trim()
        SETUP_MAIL_FROM_NAME = $MailFromName.Trim()
    }
    foreach ($Entry in $SetupValues.GetEnumerator()) {
        Set-Item -Path "Env:$($Entry.Key)" -Value $Entry.Value
    }
    try {
        & $VenvPython $ConfigWriter $ConfigPath
        Assert-NativeSuccess "Schreiben der Rechnungskonfiguration"
    } finally {
        foreach ($Entry in $SetupValues.GetEnumerator()) {
            Remove-Item "Env:$($Entry.Key)" -ErrorAction SilentlyContinue
        }
    }
    Write-Host "invoice.yaml wurde gespeichert."
} else {
    Write-Host "invoice.yaml ist bereits vorhanden - keine Aenderung vorgenommen."
}

New-Item -Path (Join-Path $ProjectRoot "customers") -ItemType Directory -Force | Out-Null
New-Item -Path (Join-Path $ProjectRoot "data") -ItemType Directory -Force | Out-Null
New-Item -Path (Join-Path $ProjectRoot "hours") -ItemType Directory -Force | Out-Null

& $VenvPython $SetupCheck
Assert-NativeSuccess "Abschliessender Setup-Check"

$RunScript = Join-Path $ProjectRoot "generate_invoices.ps1"
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

Write-Host "Projekt ist bereit. Starte Rechnungen unter Windows mit .\generate_invoices.ps1."
