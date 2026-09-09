@echo off
:: Double-click to run. Tests why the service will not start and writes the
:: result to C:\ProgramData\AIMonitor\diagnose_output.log
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0Diagnose-AIMonitor.ps1"
if errorlevel 1 (
    echo.
    echo An error occurred ^(see above^).
    pause
)
