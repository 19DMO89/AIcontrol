<#
    AI-Monitor - Build script
    Compiles the Python source into stand-alone EXE files with PyInstaller.
    The complete Python source (incl. config.py with the AI detection list)
    is compiled into the EXE - afterwards there is no editable .py source left
    next to the programs.

    Run:  powershell -ExecutionPolicy Bypass -File build.ps1

    Result:
      dist\AIMonitorService\AIMonitorService.exe   (background service)
      dist\AIMonitorDashboard.exe                  (dashboard, single file)
      dist\AISessionAgent.exe                      (screenshot helper, runs in the user session)
#>
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root

python -m PyInstaller --version | Out-Null
if (-not $?) {
    Write-Error "PyInstaller is not installed. Run first: python -m pip install -r requirements.txt"
    exit 1
}

Write-Host "==> Building AIMonitorService.exe (background service) ..." -ForegroundColor Cyan

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
    Write-Error "pywin32_system32 folder not found at: $pywin32Sys32"
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

Write-Host "==> Building AIMonitorDashboard.exe (dashboard) ..." -ForegroundColor Cyan
python -m PyInstaller --noconfirm --clean `
    --name AIMonitorDashboard `
    --onefile `
    --windowed `
    --icon icon.ico `
    --hidden-import PIL._tkinter_finder `
    viewer.py

Write-Host "==> Building AISessionAgent.exe (screenshot helper) ..." -ForegroundColor Cyan
# Runs deliberately in the user session, not as a service - only from there
# is a screenshot of the actual desktop possible at all.
python -m PyInstaller --noconfirm --clean `
    --name AISessionAgent `
    --onefile `
    --windowed `
    --icon icon.ico `
    --hidden-import PIL._tkinter_finder `
    session_agent.py

Write-Host ""
Write-Host "==> Done." -ForegroundColor Green
Write-Host "    dist\AIMonitorService\AIMonitorService.exe"
Write-Host "    dist\AIMonitorDashboard.exe"
Write-Host "    dist\AISessionAgent.exe"
Write-Host ""
Write-Host "Next step: run Install-AIMonitor.ps1 as administrator."
