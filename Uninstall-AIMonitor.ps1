<#
    AI-Monitor - Deinstallation
    ===========================
    Stoppt und entfernt den Windows-Dienst, die Programmdateien und die
    Desktop-Verknuepfung. Erfordert Administratorrechte (bewusst so, damit
    Teilnehmer die Ueberwachung nicht selbst entfernen koennen).

    Ausfuehren:  powershell -ExecutionPolicy Bypass -File Uninstall-AIMonitor.ps1
    Optionen:    -KeepData   Datenbank/Screenshots unter C:\ProgramData\AIMonitor\data behalten
                 -Force      Ohne Rueckfrage deinstallieren
#>
param(
    [switch]$KeepData,
    [switch]$Force
)

$ErrorActionPreference = "Stop"

$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltinRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "Starte mit Administratorrechten neu (UAC-Abfrage bestaetigen) ..." -ForegroundColor Yellow
    $argList = @("-NoExit", "-ExecutionPolicy", "Bypass", "-File", "`"$($MyInvocation.MyCommand.Path)`"")
    if ($KeepData) { $argList += "-KeepData" }
    if ($Force)    { $argList += "-Force" }
    try {
        Start-Process powershell -Verb RunAs -ArgumentList $argList -ErrorAction Stop
    } catch {
        Write-Host ""
        Write-Host "Administratorrechte wurden nicht erteilt (UAC abgebrochen?)." -ForegroundColor Red
        Write-Host "Fehler: $($_.Exception.Message)" -ForegroundColor Red
        Write-Host ""
        Read-Host "Fenster mit Enter schliessen"
    }
    exit
}

try {

$installRoot = "$env:ProgramData\AIMonitor"
$binDir      = Join-Path $installRoot "bin"
$dataDir     = Join-Path $installRoot "data"

if (-not $Force) {
    $answer = Read-Host "AI-Monitor wirklich deinstallieren? (ja/nein)"
    if ($answer -notin @("ja", "j", "yes", "y")) {
        Write-Host "Abgebrochen."
        exit
    }
}

# ── Dienst stoppen und entfernen ─────────────────────────────────────────────
$svc = Get-Service -Name AIMonitor -ErrorAction SilentlyContinue
if ($svc) {
    Write-Host "==> Stoppe Dienst ..." -ForegroundColor Cyan
    if ($svc.Status -ne "Stopped") {
        Stop-Service -Name AIMonitor -Force -ErrorAction SilentlyContinue
        Start-Sleep -Seconds 2
    }
    & sc.exe delete AIMonitor | Out-Null
    Write-Host "[OK] Dienst entfernt."
} else {
    Write-Host "Dienst 'AIMonitor' ist nicht installiert."
}

# ── Sitzungs-Agent (Screenshots) stoppen und Aufgabe entfernen ──────────────
$agentTask = "AIMonitorSessionAgent"
$existingTask = Get-ScheduledTask -TaskName $agentTask -ErrorAction SilentlyContinue
if ($existingTask) {
    Write-Host "==> Entferne Sitzungs-Agent-Aufgabe ..." -ForegroundColor Cyan
    Get-Process -Name AISessionAgent -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
    Unregister-ScheduledTask -TaskName $agentTask -Confirm:$false -ErrorAction SilentlyContinue
    Write-Host "[OK] Sitzungs-Agent entfernt."
}

# ── Desktop-Verknuepfung entfernen ───────────────────────────────────────────
$desktop = [Environment]::GetFolderPath("CommonDesktopDirectory")
$lnk = Join-Path $desktop "AI-Monitor Dashboard.lnk"
if (Test-Path $lnk) {
    Remove-Item $lnk -Force
    Write-Host "[OK] Desktop-Verknuepfung entfernt."
}

# ── Legacy-Autostart-Eintrag (alte .bat-Versionen) entfernen ────────────────
# try/catch statt Stream-Umleitung, siehe Install-AIMonitor.ps1 fuer den Grund.
try { reg delete "HKCU\Software\Microsoft\Windows\CurrentVersion\Run" /v "AIMonitor" /f *>$null } catch {}

# ── Programmdateien / Daten entfernen ────────────────────────────────────────
if (Test-Path $installRoot) {
    # Eigene NTFS-Sperren zuruecksetzen, damit das Loeschen nicht daran
    # scheitert. try/catch statt Stream-Umleitung, siehe Install-AIMonitor.ps1.
    try { icacls $installRoot /reset /T /C *>$null } catch {}

    if ($KeepData) {
        Write-Host "==> Entferne Programmdateien (Daten bleiben erhalten unter $dataDir) ..." -ForegroundColor Cyan
        if (Test-Path $binDir) { Remove-Item $binDir -Recurse -Force }
    } else {
        Write-Host "==> Entferne Programmdateien und Daten ..." -ForegroundColor Cyan
        Remove-Item $installRoot -Recurse -Force
    }
    Write-Host "[OK] Entfernt."
} else {
    Write-Host "Kein Installationsverzeichnis gefunden ($installRoot)."
}

Write-Host ""
Write-Host "Deinstallation abgeschlossen." -ForegroundColor Green
if ($KeepData) {
    Write-Host "Daten liegen weiterhin unter: $dataDir"
}
Write-Host ""
Read-Host "Fenster mit Enter schliessen"

} catch {
    Write-Host ""
    Write-Host "FEHLER: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host $_.ScriptStackTrace -ForegroundColor DarkGray
    Write-Host ""
    Read-Host "Fenster mit Enter schliessen"
    exit 1
}
