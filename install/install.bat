@echo off
setlocal EnableDelayedExpansion

chcp 65001 >nul
echo 🔧 Starte Einrichtung der virtuellen Umgebung...

REM 1. Virtuelle Umgebung erstellen
if not exist .venv (
    python -m venv .venv
    echo ✅ Virtuelle Umgebung wurde erstellt.
) else (
    echo 🔁 .venv bereits vorhanden.
)

REM 2. requirements.txt installieren
if exist requirements.txt (
    echo.
    echo 📦 Installiere Pakete aus requirements.txt...
    .venv\Scripts\pip.exe install -r requirements.txt
) else (
    echo ⚠️  Keine requirements.txt gefunden.
)

REM 3. Konfiguration erstellen
set "konfigPath=data\konfiguration.json"
if not exist %konfigPath% (
    echo.
    echo 🛠️  Konfigurationsdatei wird erstellt (%konfigPath%)...
    echo.

    call :prompt "👤 Dein Name (z. B. Jan Erbert)" name
    call :prompt "🏢 Firmenname (z. B. Web Development)" firma
    call :prompt "📍 Straße und Hausnummer" strasse
    call :prompt "📮 PLZ" plz
    call :prompt "🌆 Ort" ort
    call :prompt "📞 Telefonnummer" telefon
    call :prompt "📧 E-Mail-Adresse" email
    set /p website=🔗 Webseite (optional):

    call :prompt "🏦 Bankname" bankname
    call :prompt "👤 Kontoinhaber" kontoinhaber
    call :prompt "💳 IBAN" iban
    call :prompt "🏷️  BIC" bic

    call :prompt "🧾 Steuernummer" steuernummer
    call :prompt "🏛️  Finanzamt" finanzamt

    set /p kleinunternehmer=❓ Kleinunternehmerregelung nach § 19 UStG? (y/n): 
    if /i "%kleinunternehmer%"=="y" (
        set "kuBool=true"
    ) else (
        set "kuBool=false"
        call :prompt "💰 Mehrwertsteuersatz in %% (z. B. 19)" mwst
    )

    echo ⚠️  Hinweis: Für steuerkonforme Rechnungen muss eine Kopie gemäß § 14b UStG aufbewahrt werden.
    set /p bcc=📧 BCC-Empfänger (optional, z.B. empfohlen zur Archivierung): 
    if "%bcc%"=="" (
        echo 📌 Es wird empfohlen, eine BCC-Adresse zur revisionssicheren Archivierung anzugeben.
    )

    if not exist data (
        mkdir data
    )

    REM JSON schreiben
    > %konfigPath% (
        echo {
        echo   "absender": {
        echo     "name": "!name!",
        echo     "firma": "!firma!",
        echo     "straße": "!strasse!",
        echo     "plz": "!plz!",
        echo     "ort": "!ort!",
        echo     "telefon": "!telefon!",
        echo     "email": "!email!",
        echo     "website": "!website!"
        echo   },
        echo   "bank": {
        echo     "bankname": "!bankname!",
        echo     "kontoinhaber": "!kontoinhaber!",
        echo     "iban": "!iban!",
        echo     "bic": "!bic!"
        echo   },
        echo   "finanzen": {
        echo     "steuernummer": "!steuernummer!",
        echo     "finanzamt": "!finanzamt!",
        echo     "kleinunternehmer": !kuBool!!IF "!kuBool!"=="false" echo,
        if "!kuBool!"=="false" (
            echo     "mehrwertsteuer_prozent": !mwst!
        )
        echo   },
        echo   "mail": {
        echo     "bcc": "!bcc!"
        echo   }
        echo }
    )

    echo.
    echo ✅ konfiguration.json wurde gespeichert unter: %konfigPath%
) else (
    echo 🗂️  konfiguration.json ist bereits vorhanden – keine Änderungen vorgenommen.
)

REM 4. Start-Skript erstellen
if not exist start-rechnung.bat (
    echo @echo off > start-rechnung.bat
    echo chcp 65001 ^>nul >> start-rechnung.bat
    echo echo Starte Rechnungsgenerierung... >> start-rechnung.bat
    echo .venv\Scripts\python.exe src\main.py >> start-rechnung.bat
    echo pause >> start-rechnung.bat
    echo 🚀 start-rechnung.bat wurde erstellt.
)

REM 5. Desktop-Verknüpfung anlegen
set "desktop=%USERPROFILE%\Desktop"
set "lnk=%desktop%\Rechnung starten.lnk"

powershell -Command ^
  "$s = (New-Object -ComObject WScript.Shell).CreateShortcut('%lnk%'); ^
   $s.TargetPath = '%cd%\start-rechnung.bat'; ^
   $s.WorkingDirectory = '%cd%'; ^
   $s.Save()"

echo 📎 Desktop-Verknüpfung "Rechnung starten" wurde erstellt.

echo.
echo ✅ Projekt ist einsatzbereit! Nutze 'start-rechnung.bat' oder die Desktop-Verknüpfung.

endlocal
goto :eof

:prompt
setlocal
:ask
set /p eingabe=%~1: 
if "%eingabe%"=="" (
    echo ⚠️ Dieses Feld ist erforderlich.
    goto ask
)
endlocal & set "%~2=%eingabe%"
goto :eof
