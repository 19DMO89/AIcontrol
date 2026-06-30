@echo off
title AI-Monitor - Autostart einrichten
echo ============================================
echo  AI-Monitor - Windows Autostart einrichten
echo ============================================
echo.

:: Get full path to this directory
set SCRIPT_DIR=%~dp0
set MONITOR_PATH=%SCRIPT_DIR%start_monitor_hidden.bat

echo Monitor-Pfad: %MONITOR_PATH%
echo.

:: Add to registry for current user
reg add "HKCU\Software\Microsoft\Windows\CurrentVersion\Run" ^
    /v "AIMonitor" ^
    /t REG_SZ ^
    /d "\"%MONITOR_PATH%\"" ^
    /f

if errorlevel 1 (
    echo [FEHLER] Konnte Autostart nicht einrichten.
    echo Bitte als Administrator ausfuehren.
) else (
    echo [OK] Autostart eingerichtet!
    echo Der Monitor startet ab sofort automatisch mit Windows.
    echo.
    echo Zum Entfernen: autostart_remove.bat ausfuehren
)

echo.
pause
