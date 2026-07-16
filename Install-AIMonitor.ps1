<#
    AI-Monitor - Installation
    =========================
    Installiert den AI-Monitor als Windows-Dienst (startet automatisch mit
    Windows, unabhaengig vom angemeldeten Benutzer) und legt ein Dashboard-
    Icon auf dem Desktop aller Benutzer an.

    Manipulationsschutz:
      - Der Dienst laeuft unter dem LocalSystem-Konto. Windows selbst
        verweigert Standardbenutzern (ohne Administratorrechte) das Stoppen
        oder Entfernen von Diensten - das ist eingebautes SCM-Verhalten,
        kein Trick dieses Skripts.
      - Bei einem Absturz/Kill startet der Dienst automatisch neu (Recovery).
      - Programmdateien liegen unter C:\ProgramData\AIMonitor\bin mit NTFS-
        Rechten, die Standardbenutzern nur Lesen+Ausfuehren erlauben (kein
        Bearbeiten/Ueberschreiben). Die Datenbank unter ...\data ist fuer
        Standardbenutzer schreibbar (fuer die Dashboard-App), aber nicht
        loeschbar.

    Voraussetzung: build.ps1 wurde bereits ausgefuehrt (dist\ existiert).
    Ausfuehren:    Rechtsklick -> "Mit PowerShell ausfuehren" (fordert
                   automatisch Administratorrechte an), oder:
                   powershell -ExecutionPolicy Bypass -File Install-AIMonitor.ps1
#>

$ErrorActionPreference = "Stop"

# ── Auf Administratorrechte pruefen, sonst neu starten ────────────────────────
$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltinRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "Starte mit Administratorrechten neu (UAC-Abfrage bestaetigen) ..." -ForegroundColor Yellow
    try {
        Start-Process powershell -Verb RunAs -ArgumentList "-NoExit", "-ExecutionPolicy", "Bypass", "-File", "`"$($MyInvocation.MyCommand.Path)`"" -ErrorAction Stop
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

$root       = Split-Path -Parent $MyInvocation.MyCommand.Path
$svcSrc     = Join-Path $root "dist\AIMonitorService"
$dashSrc    = Join-Path $root "dist\AIMonitorDashboard.exe"
$installRoot = "$env:ProgramData\AIMonitor"
$binDir      = Join-Path $installRoot "bin"
$svcDir      = Join-Path $binDir "service"
$dataDir     = Join-Path $installRoot "data"
$svcExe      = Join-Path $svcDir "AIMonitorService.exe"
$dashExe     = Join-Path $binDir "AIMonitorDashboard.exe"

if (-not (Test-Path $svcSrc) -or -not (Test-Path $dashSrc)) {
    Write-Error "dist\ nicht gefunden. Bitte zuerst build.ps1 ausfuehren."
    exit 1
}

Write-Host "==> Installiere nach $installRoot ..." -ForegroundColor Cyan

# ── Vorherige Installation sauber stoppen (Upgrade-Fall), Daten bleiben ──────
$existing = Get-Service -Name AIMonitor -ErrorAction SilentlyContinue
if ($existing) {
    Write-Host "Bestehender Dienst gefunden - wird angehalten und neu registriert ..."
    if ($existing.Status -ne "Stopped") {
        Stop-Service -Name AIMonitor -Force -ErrorAction SilentlyContinue
        Start-Sleep -Seconds 2
    }
    & sc.exe delete AIMonitor | Out-Null
    Start-Sleep -Seconds 1
}

# ── Verzeichnisse anlegen und Dateien kopieren ───────────────────────────────
New-Item -ItemType Directory -Force -Path $svcDir  | Out-Null
New-Item -ItemType Directory -Force -Path $dataDir | Out-Null

Copy-Item "$svcSrc\*" $svcDir -Recurse -Force
Copy-Item $dashSrc $dashExe -Force

# ── NTFS-Rechte setzen: Programmdateien (bin) sind fuer Standardbenutzer nur
#    lesbar+ausfuehrbar (nicht bearbeitbar). Der Datenordner braucht dagegen
#    normale Schreib-/Loeschrechte fuer Standardbenutzer - SQLite legt im
#    WAL-Modus Begleitdateien (-wal/-shm) an und muss sie verwalten koennen;
#    ein Loeschverbot dort bricht die Datenbank (getestet: "readonly database").
#    Der eigentliche Manipulationsschutz kommt vom Windows-Dienst selbst
#    (siehe oben), nicht von einer Sperre der Datenbankdatei.
#    SIDs statt Namen verwendet, damit das Skript auch auf nicht-deutschen
#    Windows-Installationen laeuft.
Write-Host "==> Setze Dateiberechtigungen ..." -ForegroundColor Cyan
$SID_SYSTEM = "*S-1-5-18"
$SID_ADMINS = "*S-1-5-32-544"
$SID_USERS  = "*S-1-5-32-545"

# /reset entfernt zuerst alle expliziten ACEs (z.B. von fehlgeschlagenen
# frueheren Installationsversuchen) und stellt reine Vererbung wieder her,
# damit sich bei erneuter Ausfuehrung keine widerspruechlichen Regeln anhaeufen.
icacls $installRoot /reset /T /C 2>$null                                       | Out-Null
icacls $installRoot /inheritance:r                                             | Out-Null
icacls $installRoot /grant:r "${SID_SYSTEM}:(OI)(CI)F" "${SID_ADMINS}:(OI)(CI)F" | Out-Null
icacls $binDir       /grant:r "${SID_USERS}:(OI)(CI)RX"                         | Out-Null
icacls $dataDir      /grant:r "${SID_USERS}:(OI)(CI)M"                          | Out-Null

# ── Windows-Dienst registrieren ──────────────────────────────────────────────
# Ueber die eingebaute pywin32-"install"-Befehlszeile registrieren statt mit
# einem manuell zusammengesetzten sc.exe-Aufruf - pywin32 kennt die fuer seinen
# eigenen SCM-Handshake noetigen Details (u.a. Anzeigename/Beschreibung aus
# der Service-Klasse) und war zuverlaessiger als der handgebaute Weg, der zu
# einem 60s-Timeout beim Start fuehrte (Event 7009).
Write-Host "==> Registriere Dienst 'AIMonitor' ..." -ForegroundColor Cyan
$out = & $svcExe --startup auto install 2>&1
if ($LASTEXITCODE -ne 0) {
    throw "Dienst-Installation fehlgeschlagen (Exit-Code $LASTEXITCODE): $out"
}

# Automatischer Neustart bei Absturz/Beendigung (z.B. per Taskmanager) -
# Standardbenutzer koennen den Dienst ohnehin nicht stoppen (SCM-Rechte),
# das hier faengt zusaetzlich Abstuerze/erzwungenes Prozess-Kill ab.
& sc.exe failure AIMonitor reset= 86400 actions= restart/5000/restart/5000/restart/60000 | Out-Null
& sc.exe failureflag AIMonitor 1 | Out-Null

try {
    Start-Service -Name AIMonitor -ErrorAction Stop
    Write-Host "[OK] Dienst laeuft." -ForegroundColor Green
} catch {
    Write-Host ""
    Write-Host "Dienststart fehlgeschlagen. Letzte Ereignisse aus dem System-Log:" -ForegroundColor Red
    Get-WinEvent -FilterHashtable @{LogName='System'; ProviderName='Service Control Manager'} -MaxEvents 20 -ErrorAction SilentlyContinue |
        Where-Object { $_.Message -match "AIMonitor" } | Select-Object -First 3 |
        ForEach-Object { Write-Host "  [$($_.TimeCreated)] $($_.Message)" -ForegroundColor DarkYellow }
    throw
}

# ── Desktop-Verknuepfung fuer alle Benutzer ─────────────────────────────────
Write-Host "==> Erstelle Desktop-Verknuepfung ..." -ForegroundColor Cyan
$desktop = [Environment]::GetFolderPath("CommonDesktopDirectory")
$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut((Join-Path $desktop "AI-Monitor Dashboard.lnk"))
$shortcut.TargetPath = $dashExe
$shortcut.WorkingDirectory = $binDir
$shortcut.Description = "AI-Monitor Dashboard - Berufsweltmeisterschaften"
$shortcut.Save()

# ── Alten Autostart-Registry-Eintrag (aus fruehreren .bat-Versionen) entfernen
reg delete "HKCU\Software\Microsoft\Windows\CurrentVersion\Run" /v "AIMonitor" /f 2>$null | Out-Null

Write-Host ""
Write-Host "============================================================" -ForegroundColor Green
Write-Host " Installation abgeschlossen." -ForegroundColor Green
Write-Host "============================================================"
Write-Host ""

# ── Admin-Zugangsdaten festlegen, falls noch keine existieren ───────────────
Write-Host "Jetzt Benutzername/Passwort fuer das Dashboard festlegen:" -ForegroundColor Yellow
Write-Host "(WICHTIG: unbedingt jetzt erledigen, bevor der PC an Teilnehmer" -ForegroundColor Yellow
Write-Host " uebergeben wird - sonst kann das der/die Erste tun, der/die" -ForegroundColor Yellow
Write-Host " das Dashboard-Icon oeffnet.)" -ForegroundColor Yellow
Write-Host ""
& $dashExe --set-credentials

Write-Host ""
Write-Host "Fertig. Dashboard-Icon liegt auf dem Desktop aller Benutzer."
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
