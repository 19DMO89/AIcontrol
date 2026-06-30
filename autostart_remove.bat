@echo off
title AI-Monitor - Autostart entfernen
reg delete "HKCU\Software\Microsoft\Windows\CurrentVersion\Run" /v "AIMonitor" /f
if errorlevel 1 (
    echo Autostart-Eintrag nicht gefunden oder bereits entfernt.
) else (
    echo [OK] Autostart entfernt.
)
pause
