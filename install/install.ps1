# install.ps1 – Einrichtungsskript für das Rechnungssystem
Write-Host "🔧 Starte Einrichtung der virtuellen Umgebung..."

# 1. Virtuelle Umgebung erstellen
if (-Not (Test-Path ".venv")) {
    python -m venv .venv
    Write-Host "✅ Virtuelle Umgebung wurde erstellt."
} else {
    Write-Host "🔁 .venv bereits vorhanden."
}

# 2. Pakete installieren
if (Test-Path "requirements.txt") {
    Write-Host "`n📦 Installiere Pakete aus requirements.txt..."
    .\.venv\Scripts\pip.exe install -r requirements.txt
} else {
    Write-Host "⚠️ Keine requirements.txt gefunden."
}

# 3. Konfiguration erstellen
$konfigPath = "data\konfiguration.json"
if (-Not (Test-Path $konfigPath)) {
    Write-Host "`n🛠️  Konfigurationsdatei wird erstellt ($konfigPath)...`n"

    function PflichtEingabe($prompt) {
        do {
            $wert = Read-Host $prompt
            if (-not $wert) {
               Write-Host "⚠️  Dieses Feld ist gesetzlich erforderlich."
            }
        } until ($wert)
        return $wert
    }

    $website = Read-Host "🔗 Webseite (optional)"

    $absender = @{
        name     = PflichtEingabe "👤 Dein Name (z. B. Jan Erbert)"
        firma    = PflichtEingabe "🏢 Firmenname (z. B. Web Development)"
        straße   = PflichtEingabe "📍 Straße und Hausnummer"
        plz      = PflichtEingabe "📮 PLZ"
        ort      = PflichtEingabe "🌆 Ort"
        telefon  = PflichtEingabe "📞 Telefonnummer"
        email    = PflichtEingabe "📧 E-Mail-Adresse"
        website  = $website
    }

    $bank = @{
        bankname     = PflichtEingabe "🏦 Bankname"
        kontoinhaber = PflichtEingabe "👤 Kontoinhaber"
        iban         = PflichtEingabe "💳 IBAN"
        bic          = PflichtEingabe "🏷️  BIC"
    }

    $steuernummer     = PflichtEingabe "🧾 Steuernummer"
    $finanzamt        = PflichtEingabe "🏛️  Finanzamt"
    $kuInput          = Read-Host "❓ Kleinunternehmerregelung nach § 19 UStG? (y/n)"
    $kleinunternehmer = $kuInput -eq "y"

    $finanzen = @{
        steuernummer     = $steuernummer
        finanzamt        = $finanzamt
        kleinunternehmer = $kleinunternehmer
    }

    if (-not $kleinunternehmer) {
        $mwst = PflichtEingabe "💰 Mehrwertsteuersatz in % (z. B. 19)"
        $finanzen["mehrwertsteuer_prozent"] = [int]$mwst
    }

    Write-Host "⚠️  Hinweis: Für steuerkonforme Rechnungen muss eine Kopie gemäß § 14b UStG aufbewahrt werden."
    $bcc = Read-Host "📧 BCC-Empfänger (optional, empfohlen zur Archivierung)"
    if (-not $bcc) {
        Write-Host "📌 Es wird empfohlen, eine BCC-Adresse zur revisionssicheren Archivierung anzugeben.`n"
    }

    $mail = @{ bcc = $bcc }

    $config = @{
        absender = $absender
        bank     = $bank
        finanzen = $finanzen
        mail     = $mail
    }

    New-Item -Path "data" -ItemType Directory -Force | Out-Null
    $config | ConvertTo-Json -Depth 4 | Out-File $konfigPath -Encoding UTF8
    Write-Host "`n✅ konfiguration.json wurde gespeichert unter: $konfigPath"
} else {
    Write-Host "🗂️  konfiguration.json ist bereits vorhanden – keine Änderungen vorgenommen."
}

# 4. Startskript erzeugen
$startScriptPath = "start-rechnung.bat"
if (-not (Test-Path $startScriptPath)) {
    @"
@echo off
chcp 65001 >nul
echo Starte Rechnungsgenerierung...
.venv\Scripts\python.exe src\main.py
pause
"@ | Set-Content $startScriptPath -Encoding UTF8
    Write-Host "🚀 start-rechnung.bat wurde erstellt."
}

# 5. Desktop-Verknüpfung
$desktop = [Environment]::GetFolderPath("Desktop")
$linkPath = Join-Path $desktop "Rechnung starten.lnk"
$target = (Resolve-Path ".\start-rechnung.bat").Path
$wsh = New-Object -ComObject WScript.Shell
$shortcut = $wsh.CreateShortcut($linkPath)
$shortcut.TargetPath = $target
$shortcut.WorkingDirectory = (Resolve-Path ".").Path
$shortcut.WindowStyle = 1
$shortcut.Save()
Write-Host "📎 Desktop-Verknüpfung 'Rechnung starten' wurde erstellt."

Write-Host "`n✅ Projekt ist bereit! Du kannst jetzt 'start-rechnung.bat' ausführen."
