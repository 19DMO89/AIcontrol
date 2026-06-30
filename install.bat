@echo off
title AI-Monitor Installation
echo ============================================
echo  AI-Monitor - Installation
echo  Berufsweltmeisterschaften Ueberwachung
echo ============================================
echo.

:: Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [FEHLER] Python nicht gefunden!
    echo Bitte Python 3.10+ von https://python.org installieren.
    pause
    exit /b 1
)

echo [OK] Python gefunden:
python --version

echo.
echo Installiere Abhaengigkeiten...
python -m pip install -r requirements.txt

echo.
echo ============================================
echo  Installation abgeschlossen!
echo.
echo  Naechste Schritte:
echo   1. start_monitor.bat  - Ueberwachung starten
echo   2. view_events.bat    - Ereignisse pruefen
echo   3. autostart.bat      - Bei Windows-Start automatisch starten
echo ============================================
pause
