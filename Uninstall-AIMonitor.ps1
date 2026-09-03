<#
    AI-Monitor - Deinstallation
    ===========================
    Stoppt und entfernt den Windows-Dienst, die Programmdateien, den
    "Apps & Features"-Eintrag und den Desktop-Ordner. Erfordert
    Administratorrechte (bewusst so, damit
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

$installRoot = "$env:ProgramData\AIMonitor"

# Aus dem Installationsverzeichnis heraus gestartet (so ruft "Apps & Features"
# den Deinstaller auf)? Dann zuerst in den Temp-Ordner kopieren und von dort
# neu starten - sonst wuerde sich das Skript beim Loeschen von $installRoot
# selbst unter den Fuessen wegziehen. Die Kopie holt sich anschliessend ueber
# den Block unten selbst per UAC die noetigen Administratorrechte.
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

# ── Desktop-Ordner / -Verknuepfung entfernen ─────────────────────────────────
$desktop = [Environment]::GetFolderPath("CommonDesktopDirectory")
$deskFolder = Join-Path $desktop "AI-Monitor"
if (Test-Path $deskFolder) {
    Remove-Item $deskFolder -Recurse -Force
    Write-Host "[OK] Desktop-Ordner entfernt."
}
# Lose Verknuepfung aus aelteren Versionen (vor dem Desktop-Ordner)
$legacyLnk = Join-Path $desktop "AI-Monitor Dashboard.lnk"
if (Test-Path $legacyLnk) { Remove-Item $legacyLnk -Force }

# ── Legacy-Autostart-Eintrag (alte .bat-Versionen) entfernen ────────────────
# try/catch statt Stream-Umleitung, siehe Install-AIMonitor.ps1 fuer den Grund.
try { reg delete "HKCU\Software\Microsoft\Windows\CurrentVersion\Run" /v "AIMonitor" /f *>$null } catch {}

# ── "Apps & Features"-Eintrag entfernen ─────────────────────────────────────
$arpKey = "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\AIMonitor"
if (Test-Path $arpKey) {
    Remove-Item $arpKey -Recurse -Force
    Write-Host "[OK] Eintrag aus 'Apps & Features' entfernt."
}

# ── Programmdateien / Daten entfernen ────────────────────────────────────────
if (Test-Path $installRoot) {
    # Datenbank/Screenshots gehoeren dem LocalSystem-Konto (vom Dienst
    # angelegt) - ein Administrator hat dafuer zwar per Vererbung Vollzugriff,
    # aber icacls /reset scheitert darauf trotzdem mit Zugriff verweigert,
    # solange der Besitz nicht erst auf die Administratoren-Gruppe uebergeht.
    # /A statt /D+Benutzername, damit das unabhaengig von der Sprache der
    # Windows-Installation funktioniert (kein interaktives J/Y-Prompt).
    try { takeown /F $installRoot /R /A *>$null } catch {}
    # Setzt u.a. die explizite Deny-Regel auf dem Screenshots-Ordner zurueck
    # (siehe Install-AIMonitor.ps1) - die greift sonst auch bei einem
    # Administrator-Konto, das ueblicherweise ebenfalls Mitglied der
    # Standardbenutzer-Gruppe ist, und wuerde das Loeschen unten verhindern.
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
