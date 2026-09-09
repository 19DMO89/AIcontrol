<#
    AI-Monitor - Uninstall
    ======================
    Stops and removes the Windows service, the program files, the
    "Apps & Features" entry and the desktop folder. Requires administrator
    rights (deliberately, so participants cannot remove the monitoring
    themselves).

    Run:      powershell -ExecutionPolicy Bypass -File Uninstall-AIMonitor.ps1
    Options:  -KeepData   keep the database/screenshots under C:\ProgramData\AIMonitor\data
              -Force      uninstall without confirmation
#>
param(
    [switch]$KeepData,
    [switch]$Force
)

$ErrorActionPreference = "Stop"

$installRoot = "$env:ProgramData\AIMonitor"

# Started from inside the install directory (this is how "Apps & Features"
# invokes the uninstaller)? Then copy to the temp folder first and restart
# from there - otherwise the script would pull itself out from under its own
# feet when it deletes $installRoot. The copy then obtains the administrator
# rights it needs via the UAC block below.
if ($PSCommandPath -and ($PSCommandPath -like "$installRoot\*")) {
    $tempCopy = Join-Path $env:TEMP ("Uninstall-AIMonitor_{0}.ps1" -f ([guid]::NewGuid().ToString('N')))
    Copy-Item -LiteralPath $PSCommandPath -Destination $tempCopy -Force
    $relArgs = @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", "`"$tempCopy`"")
    if ($KeepData) { $relArgs += "-KeepData" }
    if ($Force)    { $relArgs += "-Force" }
    Start-Process powershell -ArgumentList $relArgs
    exit
}

$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltinRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "Restarting with administrator rights (confirm the UAC prompt) ..." -ForegroundColor Yellow
    $argList = @("-NoExit", "-ExecutionPolicy", "Bypass", "-File", "`"$($MyInvocation.MyCommand.Path)`"")
    if ($KeepData) { $argList += "-KeepData" }
    if ($Force)    { $argList += "-Force" }
    try {
        Start-Process powershell -Verb RunAs -ArgumentList $argList -ErrorAction Stop
    } catch {
        Write-Host ""
        Write-Host "Administrator rights were not granted (UAC cancelled?)." -ForegroundColor Red
        Write-Host "Error: $($_.Exception.Message)" -ForegroundColor Red
        Write-Host ""
        Read-Host "Press Enter to close this window"
    }
    exit
}

try {

$binDir      = Join-Path $installRoot "bin"
$dataDir     = Join-Path $installRoot "data"

if (-not $Force) {
    $answer = Read-Host "Really uninstall AI-Monitor? (yes/no)"
    if ($answer -notin @("yes", "y", "ja", "j")) {
        Write-Host "Cancelled."
        exit
    }
}

# ── Stop and remove the service ────────────────────────────────────────────
$svc = Get-Service -Name AIMonitor -ErrorAction SilentlyContinue
if ($svc) {
    Write-Host "==> Stopping service ..." -ForegroundColor Cyan
    if ($svc.Status -ne "Stopped") {
        Stop-Service -Name AIMonitor -Force -ErrorAction SilentlyContinue
        Start-Sleep -Seconds 2
    }
    & sc.exe delete AIMonitor | Out-Null
    Write-Host "[OK] Service removed."
} else {
    Write-Host "Service 'AIMonitor' is not installed."
}

# ── Stop the session agent (screenshots) and remove its task ───────────────
$agentTask = "AIMonitorSessionAgent"
$existingTask = Get-ScheduledTask -TaskName $agentTask -ErrorAction SilentlyContinue
if ($existingTask) {
    Write-Host "==> Removing session agent task ..." -ForegroundColor Cyan
    Get-Process -Name AISessionAgent -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
    Unregister-ScheduledTask -TaskName $agentTask -Confirm:$false -ErrorAction SilentlyContinue
    Write-Host "[OK] Session agent removed."
}

# ── Remove the desktop folder / shortcut ───────────────────────────────────
$desktop = [Environment]::GetFolderPath("CommonDesktopDirectory")
$deskFolder = Join-Path $desktop "AI-Monitor"
if (Test-Path $deskFolder) {
    Remove-Item $deskFolder -Recurse -Force
    Write-Host "[OK] Desktop folder removed."
}
# Loose shortcut from older versions (before the desktop folder)
$legacyLnk = Join-Path $desktop "AI-Monitor Dashboard.lnk"
if (Test-Path $legacyLnk) { Remove-Item $legacyLnk -Force }

# ── Remove the legacy autostart entry (old .bat versions) ──────────────────
# try/catch instead of stream redirection, see Install-AIMonitor.ps1 for why.
try { reg delete "HKCU\Software\Microsoft\Windows\CurrentVersion\Run" /v "AIMonitor" /f *>$null } catch {}

# ── Remove the "Apps & Features" entry ─────────────────────────────────────
$arpKey = "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\AIMonitor"
if (Test-Path $arpKey) {
    Remove-Item $arpKey -Recurse -Force
    Write-Host "[OK] Entry removed from 'Apps & Features'."
}

# ── Remove program files / data ───────────────────────────────────────────
if (Test-Path $installRoot) {
    # The database/screenshots are owned by the LocalSystem account (created
    # by the service) - an administrator does have full access by
    # inheritance, but icacls /reset still fails on them with access denied
    # unless ownership first passes to the Administrators group. /A instead
    # of /D+username so this works regardless of the Windows install
    # language (no interactive Y/N prompt).
    try { takeown /F $installRoot /R /A *>$null } catch {}
    # Also resets the explicit Deny rule on the screenshots folder (see
    # Install-AIMonitor.ps1) - it otherwise applies even to an administrator
    # account, which is usually also a member of the standard Users group,
    # and would prevent the deletion below.
    try { icacls $installRoot /reset /T /C *>$null } catch {}

    if ($KeepData) {
        Write-Host "==> Removing program files (data is kept under $dataDir) ..." -ForegroundColor Cyan
        if (Test-Path $binDir) { Remove-Item $binDir -Recurse -Force }
    } else {
        Write-Host "==> Removing program files and data ..." -ForegroundColor Cyan
        Remove-Item $installRoot -Recurse -Force
    }
    Write-Host "[OK] Removed."
} else {
    Write-Host "No installation directory found ($installRoot)."
}

Write-Host ""
Write-Host "Uninstall complete." -ForegroundColor Green
if ($KeepData) {
    Write-Host "Data remains under: $dataDir"
}
Write-Host ""
Read-Host "Press Enter to close this window"

} catch {
    Write-Host ""
    Write-Host "ERROR: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host $_.ScriptStackTrace -ForegroundColor DarkGray
    Write-Host ""
    Read-Host "Press Enter to close this window"
    exit 1
}
