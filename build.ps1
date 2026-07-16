<#
    AI-Monitor - Build-Skript
    Erstellt aus dem Python-Quellcode zwei eigenstaendige EXE-Dateien mit
    PyInstaller. Der komplette Python-Quellcode (inkl. config.py mit der
    KI-Erkennungsliste) wird dabei in die EXE hineinkompiliert - danach liegt
    kein bearbeitbarer .py-Quelltext mehr neben den Programmen.

    Ausfuehren:  powershell -ExecutionPolicy Bypass -File build.ps1

    Ergebnis:
      dist\AIMonitorService\AIMonitorService.exe   (Hintergrunddienst)
      dist\AIMonitorDashboard.exe                  (Dashboard, ein File)
#>
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root

python -m PyInstaller --version | Out-Null
if (-not $?) {
    Write-Error "PyInstaller ist nicht installiert. Zuerst ausfuehren: python -m pip install -r requirements.txt"
    exit 1
}

Write-Host "==> Baue AIMonitorService.exe (Hintergrunddienst) ..." -ForegroundColor Cyan
python -m PyInstaller --noconfirm --clean `
    --name AIMonitorService `
    --onedir `
    --console `
    --hidden-import win32timezone `
    monitor_service.py

Write-Host "==> Baue AIMonitorDashboard.exe (Dashboard) ..." -ForegroundColor Cyan
python -m PyInstaller --noconfirm --clean `
    --name AIMonitorDashboard `
    --onefile `
    --windowed `
    --hidden-import PIL._tkinter_finder `
    viewer.py

Write-Host ""
Write-Host "==> Fertig." -ForegroundColor Green
Write-Host "    dist\AIMonitorService\AIMonitorService.exe"
Write-Host "    dist\AIMonitorDashboard.exe"
Write-Host ""
Write-Host "Naechster Schritt: Install-AIMonitor.ps1 als Administrator ausfuehren."
