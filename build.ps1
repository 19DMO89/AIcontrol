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
      dist\AISessionAgent.exe                      (Screenshot-Helfer, laeuft in der Nutzersitzung)
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

# PyInstaller's dependency scan only follows DLLs it sees directly imported
# from Python (e.g. pywintypesNNN.dll, used by win32service/win32event).
# pythoncomNNN.dll lives in the same pywin32_system32 folder but is only
# pulled in by servicemanager.pyd's own native imports, which the scanner
# never sees - so it silently gets left out of the onedir build. Without it,
# servicemanager fails during the real SCM-driven service startup handshake
# (StartServiceCtrlDispatcher) while every other launch path (--onedir exe
# run directly, "debug" mode, a scheduled task) keeps working, because none
# of those exercise that handshake - which made this very confusing to
# track down (Event 7009 timeout, but the process visibly runs fine
# everywhere except when actually started as a real Windows service).
# Bundle the whole pywin32_system32 folder explicitly so nothing is missing.
$pywin32Sys32 = python -c "import sysconfig, os; print(os.path.join(sysconfig.get_paths()['purelib'], 'pywin32_system32'))"
if (-not (Test-Path $pywin32Sys32)) {
    Write-Error "pywin32_system32 Ordner nicht gefunden unter: $pywin32Sys32"
    exit 1
}

# --windowed (not --console): a Windows Service runs in Session 0, which has
# no console at all. The --console bootloader tries to attach/create one
# there anyway and dies before Python (and our exception logging) ever runs -
# cleanly and silently, with no crash dump and no traceback. monitor_service.py
# already redirects sys.stdout/stderr to os.devnull when they're None, which
# is exactly the --windowed condition (sys.stdout is *always* None there).
python -m PyInstaller --noconfirm --clean `
    --name AIMonitorService `
    --onedir `
    --windowed `
    --icon icon.ico `
    --hidden-import win32timezone `
    --add-binary "$pywin32Sys32\*.dll;pywin32_system32" `
    monitor_service.py

Write-Host "==> Baue AIMonitorDashboard.exe (Dashboard) ..." -ForegroundColor Cyan
python -m PyInstaller --noconfirm --clean `
    --name AIMonitorDashboard `
    --onefile `
    --windowed `
    --icon icon.ico `
    --hidden-import PIL._tkinter_finder `
    viewer.py

Write-Host "==> Baue AISessionAgent.exe (Screenshot-Helfer) ..." -ForegroundColor Cyan
# Laeuft absichtlich in der Nutzersitzung, nicht als Dienst - nur von dort
# aus ist ein Screenshot des tatsaechlichen Desktops ueberhaupt moeglich.
python -m PyInstaller --noconfirm --clean `
    --name AISessionAgent `
    --onefile `
    --windowed `
    --icon icon.ico `
    --hidden-import PIL._tkinter_finder `
    session_agent.py

Write-Host ""
Write-Host "==> Fertig." -ForegroundColor Green
Write-Host "    dist\AIMonitorService\AIMonitorService.exe"
Write-Host "    dist\AIMonitorDashboard.exe"
Write-Host "    dist\AISessionAgent.exe"
Write-Host ""
Write-Host "Naechster Schritt: Install-AIMonitor.ps1 als Administrator ausfuehren."
