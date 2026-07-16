@echo off
:: Per Doppelklick startbar. Ruft Uninstall-AIMonitor.ps1 auf, das sich bei
:: Bedarf selbst die Administratorrechte per UAC-Abfrage holt.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0Uninstall-AIMonitor.ps1"
if errorlevel 1 (
    echo.
    echo Ein Fehler ist aufgetreten ^(siehe oben^).
    pause
)
