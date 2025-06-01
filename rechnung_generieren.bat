@echo off
chcp 65001 >nul
echo Starte Rechnungsgenerierung...

REM Absoluter Pfad zur venv-Python.exe
set "VENV_PY=.\.venv\Scripts\python.exe"

REM Prüfen, ob die virtuelle Umgebung existiert
if exist %VENV_PY% (
    %VENV_PY% src\main.py
) else (
    echo ⚠️ Virtuelle Umgebung nicht gefunden unter %VENV_PY%
    pause
    exit /b 1
)

pause