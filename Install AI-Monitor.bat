@echo off
:: Double-click to run. Calls Install-AIMonitor.ps1, which requests
:: administrator rights via a UAC prompt itself when needed.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0Install-AIMonitor.ps1"
if errorlevel 1 (
    echo.
    echo An error occurred ^(see above^).
    pause
)
