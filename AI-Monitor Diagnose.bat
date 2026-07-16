@echo off
:: Per Doppelklick startbar. Testet, warum der Dienst nicht startet, und
:: schreibt das Ergebnis nach C:\ProgramData\AIMonitor\diagnose_output.log
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0Diagnose-AIMonitor.ps1"
if errorlevel 1 (
    echo.
    echo Ein Fehler ist aufgetreten ^(siehe oben^).
    pause
)
