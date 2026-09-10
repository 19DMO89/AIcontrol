<#
    AI-Monitor - Installation
    =========================
    Installs AI-Monitor as a Windows service (starts automatically with
    Windows, independent of the logged-in user), registers the session agent
    (for screenshots) as a logon task, and creates a desktop folder
    "AI-Monitor" (dashboard + uninstall shortcut) for all users.

    Tamper protection:
      - The service runs under the LocalSystem account. Windows itself denies
        standard users (without administrator rights) the ability to stop or
        remove services - that is built-in SCM behaviour, not a trick of this
        script.
      - On a crash/kill the service restarts automatically (recovery).
      - Program files live under C:\ProgramData\AIMonitor\bin with NTFS
        permissions that only allow standard users to read+execute (no
        editing/overwriting). The database under ...\data is writable for
        standard users (for the dashboard app) but not deletable.
      - The session agent (screenshots) necessarily runs with the rights of
        the logged-in user - that is the only way it can access their desktop
        at all. A standard user can end the running process in Task Manager,
        but cannot delete the task definition itself (it lives under
        C:\Windows\System32\Tasks, admin-protected) - it starts again on the
        next logon anyway.

    Requirement: build.ps1 has already been run (dist\ exists).
    Run:         Right-click -> "Run with PowerShell" (requests administrator
                 rights automatically), or:
                 powershell -ExecutionPolicy Bypass -File Install-AIMonitor.ps1

    Options:     -ResetCredentials   on an upgrade, force a new dashboard
                                     username/password instead of keeping
                                     the existing one (e.g. to lock out
                                     whoever set the test credentials).
#>
param(
    [switch]$ResetCredentials
)

$ErrorActionPreference = "Stop"

# ── Check for administrator rights, restart elevated otherwise ───────────────
$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltinRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "Restarting with administrator rights (confirm the UAC prompt) ..." -ForegroundColor Yellow
    $relArgs = @("-ExecutionPolicy", "Bypass", "-File", "`"$($MyInvocation.MyCommand.Path)`"")
    if ($ResetCredentials) { $relArgs += "-ResetCredentials" }
    try {
        Start-Process powershell -Verb RunAs -Wait -ArgumentList $relArgs -ErrorAction Stop
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

$root       = Split-Path -Parent $MyInvocation.MyCommand.Path
$svcSrc     = Join-Path $root "dist\AIMonitorService"
$dashSrc    = Join-Path $root "dist\AIMonitorDashboard.exe"
$agentSrc   = Join-Path $root "dist\AISessionAgent.exe"
$installRoot = "$env:ProgramData\AIMonitor"
$binDir      = Join-Path $installRoot "bin"
$svcDir      = Join-Path $binDir "service"
$dataDir     = Join-Path $installRoot "data"
$svcExe      = Join-Path $svcDir "AIMonitorService.exe"
$dashExe     = Join-Path $binDir "AIMonitorDashboard.exe"
$agentExe    = Join-Path $binDir "AISessionAgent.exe"
$agentTask   = "AIMonitorSessionAgent"
$uninstSrc   = Join-Path $root "Uninstall-AIMonitor.ps1"
$uninstBatSrc = Join-Path $root "Uninstall AI-Monitor.bat"
$uninstDst   = Join-Path $binDir "Uninstall-AIMonitor.ps1"
$arpKey      = "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\AIMonitor"

# Version number: from the VERSION.txt the packager bundles, otherwise via a
# regex on config.py (manual install from the source folder), otherwise a
# fallback. The single source is config.py -> VERSION.
$version = "3.1.0"
$verFile = Join-Path $root "VERSION.txt"
$cfgFile = Join-Path $root "config.py"
if (Test-Path $verFile) {
    $version = (Get-Content -Raw $verFile).Trim()
} elseif (Test-Path $cfgFile) {
    $m = Select-String -Path $cfgFile -Pattern 'VERSION\s*=\s*["'']([^"'']+)["'']' | Select-Object -First 1
    if ($m) { $version = $m.Matches[0].Groups[1].Value }
}

if (-not (Test-Path $svcSrc) -or -not (Test-Path $dashSrc) -or -not (Test-Path $agentSrc)) {
    Write-Error "dist\ not found or incomplete. Please run build.ps1 first."
    exit 1
}

Write-Host "==> Installing to $installRoot ..." -ForegroundColor Cyan

# ── Cleanly stop a previous installation (upgrade case); data is kept ────────
$existing = Get-Service -Name AIMonitor -ErrorAction SilentlyContinue
if ($existing) {
    Write-Host "Existing service found - stopping and re-registering ..."
    if ($existing.Status -ne "Stopped") {
        Stop-Service -Name AIMonitor -Force -ErrorAction SilentlyContinue
        Start-Sleep -Seconds 2
    }
    & sc.exe delete AIMonitor | Out-Null
    Start-Sleep -Seconds 1
}

# Always stop every running session agent first (not only when the task still
# exists) - an upgrade must never leave an old build's agent running next to
# the new one; two agents polling the clipboard was the v3.2.0 copy/paste bug.
Get-Process -Name AISessionAgent -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
$existingTask = Get-ScheduledTask -TaskName $agentTask -ErrorAction SilentlyContinue
if ($existingTask) {
    Unregister-ScheduledTask -TaskName $agentTask -Confirm:$false -ErrorAction SilentlyContinue
}

# A dashboard that is still open holds AIMonitorDashboard.exe locked - then
# overwriting it during an upgrade would fail. Close it first.
Get-Process -Name AIMonitorDashboard -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue

# ── Create directories and copy files ───────────────────────────────────────
New-Item -ItemType Directory -Force -Path $svcDir  | Out-Null
New-Item -ItemType Directory -Force -Path $dataDir | Out-Null

Copy-Item "$svcSrc\*" $svcDir -Recurse -Force
Copy-Item $dashSrc $dashExe -Force
Copy-Item $agentSrc $agentExe -Force

# ── Set NTFS permissions: program files (bin) are read+execute only for
#    standard users (not editable). The data folder, in contrast, needs
#    normal write/delete rights for standard users - in WAL mode SQLite
#    creates companion files (-wal/-shm) and must be able to manage them; a
#    delete ban there breaks the database (tested: "readonly database").
#    The actual tamper protection comes from the Windows service itself
#    (see above), not from locking the database file.
#    SIDs used instead of names so the script also runs on non-English
#    Windows installations.
Write-Host "==> Setting file permissions ..." -ForegroundColor Cyan
$SID_SYSTEM = "*S-1-5-18"
$SID_ADMINS = "*S-1-5-32-544"
$SID_USERS  = "*S-1-5-32-545"

# /reset first removes all explicit ACEs (e.g. from failed earlier install
# attempts) and restores pure inheritance, so repeated runs don't accumulate
# contradictory rules. /C lets icacls carry on past individual bad files -
# but under $ErrorActionPreference = "Stop" even a single error line on
# stderr (2>$null notwithstanding) would still abort the whole script, see
# the reg-delete comment further down. try/catch makes /C's "carry on as best
# you can" actually effective.
try { icacls $installRoot /reset /T /C *>$null } catch {}
icacls $installRoot /inheritance:r                                             | Out-Null
icacls $installRoot /grant:r "${SID_SYSTEM}:(OI)(CI)F" "${SID_ADMINS}:(OI)(CI)F" | Out-Null
icacls $binDir       /grant:r "${SID_USERS}:(OI)(CI)RX"                         | Out-Null
icacls $dataDir      /grant:r "${SID_USERS}:(OI)(CI)M"                          | Out-Null

# Screenshots may be created by standard users (the session agent runs with
# their own rights - a screenshot of one's own desktop is not technically
# possible otherwise) but must not be deletable. DE (Delete) and DC (Delete
# Child) are denied here specifically - an explicit Deny ACE always wins in
# NTFS against the inherited Allow ACE from above (Modify normally includes
# Delete). Deliberately only on this subfolder, not on $dataDir as a whole -
# there SQLite needs delete rights for its own WAL companion files (see the
# comment above).
$screenshotsDir = Join-Path $dataDir "screenshots"
New-Item -ItemType Directory -Force -Path $screenshotsDir | Out-Null
icacls $screenshotsDir /grant:r "${SID_USERS}:(OI)(CI)M"       | Out-Null
icacls $screenshotsDir /deny    "${SID_USERS}:(OI)(CI)(DE,DC)" | Out-Null

# ── Register the Windows service ────────────────────────────────────────────
# Register via pywin32's built-in "install" command line rather than a
# hand-assembled sc.exe call - pywin32 knows the details its own SCM
# handshake needs (display name/description from the service class, etc.) and
# was more reliable than the hand-built path, which led to a 60s timeout on
# start (Event 7009).
Write-Host "==> Registering service 'AIMonitor' ..." -ForegroundColor Cyan
# Retry, because real-time antivirus is scanning the AIMonitorService.exe
# just copied to ProgramData - an immediately following execution attempt
# sporadically fails with Access Denied (exit code 5), even though nothing is
# wrong with the file/permissions. After a few seconds the scan is done and
# the same call works fine.
$maxAttempts = 5
for ($attempt = 1; $attempt -le $maxAttempts; $attempt++) {
    $out = & $svcExe --startup auto install 2>&1
    if ($LASTEXITCODE -eq 0) { break }
    if ($attempt -eq $maxAttempts) {
        throw "Service installation failed (exit code $LASTEXITCODE): $out"
    }
    Write-Host "    ... attempt $attempt failed (exit code $LASTEXITCODE), retrying in 3s ..." -ForegroundColor DarkYellow
    Start-Sleep -Seconds 3
}

# Automatic restart on crash/termination (e.g. via Task Manager) - standard
# users cannot stop the service anyway (SCM rights), this additionally
# catches crashes/forced process kills.
& sc.exe failure AIMonitor reset= 86400 actions= restart/5000/restart/5000/restart/60000 | Out-Null
& sc.exe failureflag AIMonitor 1 | Out-Null

# The SCM database needs a brief moment after registration before the new
# service is queryable by name - without this pause the immediately
# following Start-Service call sporadically fails with "The specified
# service does not exist", even though registration actually succeeded.
Start-Sleep -Milliseconds 1000

try {
    Start-Service -Name AIMonitor -ErrorAction Stop
    Write-Host "[OK] Service is running." -ForegroundColor Green
} catch {
    Write-Host ""
    Write-Host "Service start failed. Most recent events from the System log:" -ForegroundColor Red
    Get-WinEvent -FilterHashtable @{LogName='System'; ProviderName='Service Control Manager'} -MaxEvents 20 -ErrorAction SilentlyContinue |
        Where-Object { $_.Message -match "AIMonitor" } | Select-Object -First 3 |
        ForEach-Object { Write-Host "  [$($_.TimeCreated)] $($_.Message)" -ForegroundColor DarkYellow }
    throw
}

# ── Register the session agent as a logon task ─────────────────────────────
# Runs with the rights of whichever user is logged in (RunLevel Limited, no
# password stored/needed - "AtLogOn" is an interactive trigger). GroupId
# instead of a fixed user name, so it works for every account that logs in,
# not just the one active at install time.
Write-Host "==> Registering session agent (screenshots) ..." -ForegroundColor Cyan
$agentAction    = New-ScheduledTaskAction -Execute $agentExe
$agentTrigger   = New-ScheduledTaskTrigger -AtLogOn
# SID instead of "BUILTIN\Users" - the name alone triggered "No mapping
# between account names and security IDs was done" on this system (a
# localization issue); the SID is language-independent.
$agentPrincipal = New-ScheduledTaskPrincipal -GroupId "S-1-5-32-545" -RunLevel Limited
$agentSettings  = New-ScheduledTaskSettingsSet -RestartCount 999 -RestartInterval (New-TimeSpan -Minutes 1) `
                    -ExecutionTimeLimit ([TimeSpan]::Zero) -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
Register-ScheduledTask -TaskName $agentTask -Action $agentAction -Trigger $agentTrigger `
    -Principal $agentPrincipal -Settings $agentSettings -Force | Out-Null

# Start it for the current session immediately too, rather than waiting for
# the next logon.
Start-ScheduledTask -TaskName $agentTask -ErrorAction SilentlyContinue

# The desktop folder with the dashboard and uninstall shortcuts is created
# further down (after the uninstaller script has been copied).

# ── Install the uninstaller and register it in "Apps & Features" ────────────
# AIMonitor-Setup.exe only ships the installer - without this step there
# would be no way to remove AI-Monitor on the target machine, and nothing
# would appear in Windows Settings (Apps / "Programs and Features"). The
# uninstaller script lives in $binDir and inherits its NTFS permissions
# (standard users read/execute only), so participants cannot tamper with it;
# uninstalling itself requires a UAC confirmation anyway (see
# Uninstall-AIMonitor.ps1).
Write-Host "==> Registering uninstaller ..." -ForegroundColor Cyan
if (Test-Path $uninstSrc) {
    Copy-Item $uninstSrc $uninstDst -Force
} else {
    Write-Warning "Uninstall-AIMonitor.ps1 not found next to the installer - uninstaller script is missing."
}
if (Test-Path $uninstBatSrc) {
    Copy-Item $uninstBatSrc (Join-Path $binDir "Uninstall AI-Monitor.bat") -Force
}

$uninstCmd = "powershell.exe -NoProfile -ExecutionPolicy Bypass -File `"$uninstDst`""
New-Item -Path $arpKey -Force | Out-Null
Set-ItemProperty -Path $arpKey -Name "DisplayName"          -Value "AI-Monitor"
Set-ItemProperty -Path $arpKey -Name "DisplayVersion"       -Value $version
Set-ItemProperty -Path $arpKey -Name "Publisher"            -Value "AI-Monitor"
Set-ItemProperty -Path $arpKey -Name "InstallLocation"      -Value $installRoot
Set-ItemProperty -Path $arpKey -Name "DisplayIcon"          -Value $dashExe
Set-ItemProperty -Path $arpKey -Name "UninstallString"      -Value $uninstCmd
Set-ItemProperty -Path $arpKey -Name "QuietUninstallString" -Value "$uninstCmd -Force"
Set-ItemProperty -Path $arpKey -Name "NoModify" -Value 1 -Type DWord
Set-ItemProperty -Path $arpKey -Name "NoRepair" -Value 1 -Type DWord
try {
    $sizeKb = [int]((Get-ChildItem $binDir -Recurse -File -ErrorAction SilentlyContinue |
                     Measure-Object -Property Length -Sum).Sum / 1024)
    Set-ItemProperty -Path $arpKey -Name "EstimatedSize" -Value $sizeKb -Type DWord
} catch {}

# ── Desktop folder "AI-Monitor" for all users ──────────────────────────────
# Instead of a loose shortcut, a folder with the dashboard and uninstall
# shortcuts inside it, so both are in one place.
Write-Host "==> Creating desktop folder 'AI-Monitor' ..." -ForegroundColor Cyan
$desktop   = [Environment]::GetFolderPath("CommonDesktopDirectory")
$deskFolder = Join-Path $desktop "AI-Monitor"
New-Item -ItemType Directory -Force -Path $deskFolder | Out-Null
$shell = New-Object -ComObject WScript.Shell

$scDash = $shell.CreateShortcut((Join-Path $deskFolder "AI-Monitor Dashboard.lnk"))
$scDash.TargetPath       = $dashExe
$scDash.WorkingDirectory = $binDir
$scDash.IconLocation     = "$dashExe,0"
$scDash.Description       = "AI-Monitor Dashboard - WorldSkills"
$scDash.Save()

$scUninst = $shell.CreateShortcut((Join-Path $deskFolder "Uninstall AI-Monitor.lnk"))
$scUninst.TargetPath       = "powershell.exe"
$scUninst.Arguments        = "-NoProfile -ExecutionPolicy Bypass -File `"$uninstDst`""
$scUninst.WorkingDirectory = $binDir
$scUninst.IconLocation     = "shell32.dll,31"
$scUninst.Description       = "Remove AI-Monitor from this machine (asks for administrator rights)"
$scUninst.Save()

# ── Remove an old autostart registry entry (from earlier .bat versions) ─────
# Usually expects a "value not found" (the entry only exists when upgrading
# from the old .bat-based autostart version) - that is not an error. reg.exe's
# own error output would be treated as an aborting error under
# $ErrorActionPreference = "Stop" despite 2>$null, hence try/catch instead of
# stream redirection.
try { reg delete "HKCU\Software\Microsoft\Windows\CurrentVersion\Run" /v "AIMonitor" /f *>$null } catch {}

Write-Host ""
Write-Host "============================================================" -ForegroundColor Green
Write-Host " Installation complete." -ForegroundColor Green
Write-Host "============================================================"
Write-Host ""

# ── Set admin credentials ──────────────────────────────────────────────────
# On an upgrade the credentials are already in the database. By default they
# are kept (otherwise every re-install would require a new password), but the
# installer offers to replace them - useful to lock out whoever set the test
# credentials before handing the machine over.
# Start-Process -Wait, because the dashboard is a GUI application - a bare
# "& $dashExe" would not wait reliably or return an exit code. The
# --has-credentials path opens no window.
$credProbe = Start-Process -FilePath $dashExe -ArgumentList "--has-credentials" `
    -Wait -PassThru -WindowStyle Hidden
$haveCreds = ($credProbe.ExitCode -eq 0)

$setNew = $true
if ($haveCreds -and -not $ResetCredentials) {
    Write-Host "Existing dashboard credentials found." -ForegroundColor Cyan
    $answer = Read-Host "Keep them? Press Enter to keep, or type 'n' to set a new username/password"
    $setNew = ($answer -in @("n", "no"))
}

if ($setNew) {
    Write-Host "Now set a username/password for the dashboard:" -ForegroundColor Yellow
    Write-Host "(IMPORTANT: do this now, before the PC is handed to participants" -ForegroundColor Yellow
    Write-Host " - otherwise whoever opens the dashboard icon first can do it.)" -ForegroundColor Yellow
    Write-Host ""
    & $dashExe --set-credentials
} else {
    Write-Host "Existing dashboard credentials are kept unchanged." -ForegroundColor Green
}

Write-Host ""
Write-Host "Done. The desktop has an 'AI-Monitor' folder with the"
Write-Host "dashboard and uninstall shortcuts."
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
