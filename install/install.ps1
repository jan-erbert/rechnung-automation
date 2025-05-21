# install.ps1 – Einrichtungsskript für das Rechnungssystem

Write-Host "🔧 Starte Einrichtung der virtuellen Umgebung..."

# 1. Virtuelle Umgebung erstellen
if (-Not (Test-Path ".venv")) {
    python -m venv .venv
    Write-Host "✅ Virtuelle Umgebung wurde erstellt."
} else {
    Write-Host "🔁 .venv bereits vorhanden."
}

# 2. Hinweis zur Aktivierung
Write-Host "`n💡 Bitte aktiviere die Umgebung mit:"
Write-Host "   .\.venv\Scripts\Activate.ps1`n"

# 3. Abhängigkeiten installieren
if (Test-Path "requirements.txt") {
    Write-Host "📦 Installiere Pakete aus requirements.txt..."
    .\.venv\Scripts\pip.exe install -r requirements.txt
} else {
    Write-Host "⚠️ Keine requirements.txt gefunden."
}

# 4. Konfiguration erstellen
$konfigPath = "data\konfiguration.json"
if (-Not (Test-Path $konfigPath)) {
    Write-Host "`n🛠️  Konfigurationsdatei wird erstellt (data\konfiguration.json)...`n"

    function PflichtEingabe($prompt) {
        do {
            $wert = Read-Host $prompt
            if (-not $wert) {
               Write-Host "⚠️  Dieses Feld ist gesetzlich erforderlich, da Rechnungen gemäß § 14 UStG bestimmte Pflichtangaben enthalten müssen – z. B. vollständiger Name, Adresse, Steuernummer oder Kontoverbindung.`n"
            }
        } until ($wert)
        return $wert
    }
    $website = Read-Host "🔗 Webseite (optional)"
    # ABSENDER
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

    # BANK
    $bank = @{
        bankname       = PflichtEingabe "🏦 Bankname"
        kontoinhaber   = PflichtEingabe "👤 Kontoinhaber"
        iban           = PflichtEingabe "💳 IBAN"
        bic            = PflichtEingabe "🏷️  BIC"
    }

    # FINANZEN
    $steuernummer     = PflichtEingabe "🧾 Steuernummer"
    $finanzamt        = PflichtEingabe "🏛️  Finanzamt"
    $kleinunternehmer = Read-Host "❓ Kleinunternehmerregelung nach § 19 UStG? (y/n)"
    $kleinunternehmer = $kleinunternehmer -eq "y"

    $finanzen = @{
        steuernummer     = $steuernummer
        finanzamt        = $finanzamt
        kleinunternehmer = $kleinunternehmer
    }

    if (-not $kleinunternehmer) {
        $mwst = PflichtEingabe "💰 Mehrwertsteuersatz in % (z. B. 19)"
        $finanzen["mehrwertsteuer_prozent"] = [int]$mwst
    }

    # MAIL
    Write-Host "⚠️  Hinweis: Für steuerkonforme Rechnungen muss eine Kopie nach § 14 UStG aufbewahrt werden."
    $bcc = Read-Host "📧 BCC-Empfänger (optional, z.B. empfohlen zur Archivierung)"
    if (-not $bcc) {
        Write-Host "📌 Es wird empfohlen, eine BCC-Adresse zur revisionssicheren Archivierung anzugeben.`n"
    }

    $mail = @{ bcc = $bcc }

    # Gesamtobjekt
    $config = @{
        absender = $absender
        bank     = $bank
        finanzen = $finanzen
        mail     = $mail
    }

    # Sicherstellen, dass data/ existiert
    New-Item -Path "data" -ItemType Directory -Force | Out-Null

    # Speichern
    $config | ConvertTo-Json -Depth 4 | Out-File $konfigPath -Encoding UTF8
    Write-Host "`n✅ konfiguration.json wurde gespeichert unter: $konfigPath"
} else {
    Write-Host "🗂️  konfiguration.json ist bereits vorhanden – keine Änderungen vorgenommen."
}

# 5. Start-Skript für Windows erzeugen
$startScriptPath = "start-rechnung.bat"
if (-not (Test-Path $startScriptPath)) {
    @"
@echo off
call .venv\Scripts\activate.bat
python main.py
pause
"@ | Set-Content $startScriptPath -Encoding UTF8
    Write-Host "🚀 start-rechnung.bat wurde erstellt."
}

# 6. Desktop-Verknüpfung (nur Windows, optional)
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
Write-Host "`n✅ Projekt ist bereit! Du kannst jetzt 'main.py' ausführen."