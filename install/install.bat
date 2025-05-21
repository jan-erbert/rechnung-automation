@echo off
setlocal EnableDelayedExpansion

echo 🔧 Starte Einrichtung der virtuellen Umgebung...

REM 1. Virtuelle Umgebung erstellen
if not exist .venv (
    python -m venv .venv
    echo ✅ Virtuelle Umgebung wurde erstellt.
) else (
    echo 🔁 .venv bereits vorhanden.
)

REM 2. Hinweis zur Aktivierung
echo.
echo 💡 Bitte aktiviere die Umgebung mit:
echo    .venv\Scripts\activate.bat
echo.

REM 3. requirements.txt installieren
if exist requirements.txt (
    echo 📦 Installiere Pakete aus requirements.txt...
    .venv\Scripts\pip.exe install -r requirements.txt
) else (
    echo ⚠️  Keine requirements.txt gefunden.
)

REM 4. Konfiguration erstellen
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

    REM data-Ordner anlegen
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

echo.
echo ✅ Projekt ist bereit! Du kannst jetzt main.py ausführen.
goto :eof

REM Funktion für Pflichtfelder mit Wiederholung
:prompt
setlocal
:ask
set /p eingabe=%~1: 
if "%eingabe%"=="" (
    echo ⚠️  Dieses Feld ist gesetzlich erforderlich, da Rechnungen gemäß § 14 UStG bestimmte Pflichtangaben enthalten müssen – z. B. vollständiger Name, Adresse, Steuernummer oder Kontoverbindung.
    goto ask
)
REM 5. Start-Skript für Windows erzeugen
if not exist start-rechnung.bat (
    echo @echo off > start-rechnung.bat
    echo call .venv\Scripts\activate.bat >> start-rechnung.bat
    echo python main.py >> start-rechnung.bat
    echo pause >> start-rechnung.bat
    echo 🚀 start-rechnung.bat wurde erstellt.
)

REM 6. Desktop-Verknüpfung anlegen (nur bei Windows mit wscript)
set "desktop=%USERPROFILE%\Desktop"
set "lnk=%desktop%\Rechnung starten.lnk"

powershell -Command ^
  "$s = (New-Object -ComObject WScript.Shell).CreateShortcut('%lnk%'); ^
   $s.TargetPath = '%cd%\start-rechnung.bat'; ^
   $s.WorkingDirectory = '%cd%'; ^
   $s.Save()"
echo 📎 Desktop-Verknüpfung "Rechnung starten" wurde erstellt.

endlocal & set "%~2=%eingabe%"
goto :eof