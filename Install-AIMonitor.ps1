<#
    AI-Monitor - Installation
    =========================
    Installiert den AI-Monitor als Windows-Dienst (startet automatisch mit
    Windows, unabhaengig vom angemeldeten Benutzer), registriert den
    Sitzungs-Agenten (fuer Screenshots) als Anmelde-Aufgabe und legt ein
    Dashboard-Icon auf dem Desktop aller Benutzer an.

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
      - Der Sitzungs-Agent (Screenshots) laeuft zwangslaeufig mit den
        Rechten des angemeldeten Benutzers - nur so kann er ueberhaupt auf
        dessen Desktop zugreifen. Ein Standardbenutzer kann den laufenden
        Prozess im Taskmanager beenden, aber die Aufgabendefinition selbst
        nicht loeschen (liegt unter C:\Windows\System32\Tasks, admin-
        geschuetzt) - bei der naechsten Anmeldung startet er ohnehin wieder.

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
        Start-Process powershell -Verb RunAs -Wait -ArgumentList "-ExecutionPolicy", "Bypass", "-File", "`"$($MyInvocation.MyCommand.Path)`"" -ErrorAction Stop
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
$agentSrc   = Join-Path $root "dist\AISessionAgent.exe"
$installRoot = "$env:ProgramData\AIMonitor"
$binDir      = Join-Path $installRoot "bin"
$svcDir      = Join-Path $binDir "service"
$dataDir     = Join-Path $installRoot "data"
$svcExe      = Join-Path $svcDir "AIMonitorService.exe"
$dashExe     = Join-Path $binDir "AIMonitorDashboard.exe"
$agentExe    = Join-Path $binDir "AISessionAgent.exe"
$agentTask   = "AIMonitorSessionAgent"

if (-not (Test-Path $svcSrc) -or -not (Test-Path $dashSrc) -or -not (Test-Path $agentSrc)) {
    Write-Error "dist\ nicht gefunden oder unvollstaendig. Bitte zuerst build.ps1 ausfuehren."
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

$existingTask = Get-ScheduledTask -TaskName $agentTask -ErrorAction SilentlyContinue
if ($existingTask) {
    Get-Process -Name AISessionAgent -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
    Unregister-ScheduledTask -TaskName $agentTask -Confirm:$false -ErrorAction SilentlyContinue
}

# ── Verzeichnisse anlegen und Dateien kopieren ───────────────────────────────
New-Item -ItemType Directory -Force -Path $svcDir  | Out-Null
New-Item -ItemType Directory -Force -Path $dataDir | Out-Null

Copy-Item "$svcSrc\*" $svcDir -Recurse -Force
Copy-Item $dashSrc $dashExe -Force
Copy-Item $agentSrc $agentExe -Force

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
# /C laesst icacls ueber einzelne fehlerhafte Dateien hinweg weiterlaufen -
# aber unter $ErrorActionPreference = "Stop" wuerde selbst eine einzelne
# Fehlerzeile auf stderr (2>$null hin oder her) das ganze Skript trotzdem
# abbrechen, siehe reg-delete-Kommentar weiter unten. try/catch macht /C's
# "bestmoeglich weitermachen" auch tatsaechlich wirksam.
try { icacls $installRoot /reset /T /C *>$null } catch {}
icacls $installRoot /inheritance:r                                             | Out-Null
icacls $installRoot /grant:r "${SID_SYSTEM}:(OI)(CI)F" "${SID_ADMINS}:(OI)(CI)F" | Out-Null
icacls $binDir       /grant:r "${SID_USERS}:(OI)(CI)RX"                         | Out-Null
icacls $dataDir      /grant:r "${SID_USERS}:(OI)(CI)M"                          | Out-Null

# Screenshots duerfen von Standardbenutzern angelegt (der Sitzungs-Agent laeuft
# ja mit ihren eigenen Rechten - anders geht ein Screenshot des eigenen
# Desktops technisch nicht), aber nicht geloescht werden koennen. DE (Delete)
# und DC (Delete Child) werden hier gezielt verweigert - eine explizite Deny-
# ACE gewinnt in NTFS immer gegen die geerbte Allow-ACE von oben (Modify
# schliesst Loeschen normalerweise mit ein). Bewusst nur auf diesem
# Unterordner, nicht auf $dataDir insgesamt - dort braucht SQLite im WAL-Modus
# Loeschrechte fuer seine eigenen Begleitdateien (siehe Kommentar oben).
$screenshotsDir = Join-Path $dataDir "screenshots"
New-Item -ItemType Directory -Force -Path $screenshotsDir | Out-Null
icacls $screenshotsDir /grant:r "${SID_USERS}:(OI)(CI)M"       | Out-Null
icacls $screenshotsDir /deny    "${SID_USERS}:(OI)(CI)(DE,DC)" | Out-Null

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

# Die SCM-Datenbank braucht nach der Registrierung einen kurzen Moment, bevor
# der neue Dienst per Name abfragbar ist - ohne diese Pause schlaegt der
# unmittelbar folgende Start-Service-Aufruf sporadisch mit "Es kann kein
# Dienst mit diesem Namen gefunden werden" fehl, obwohl die Registrierung
# tatsaechlich erfolgreich war.
Start-Sleep -Milliseconds 1000

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

# ── Sitzungs-Agent als Anmelde-Aufgabe registrieren ─────────────────────────
# Laeuft mit den Rechten des jeweils angemeldeten Benutzers (RunLevel
# Limited, kein Passwort hinterlegt/benoetigt - "AtLogOn" ist ein
# interaktiver Trigger). GroupId statt einem festen Benutzernamen, damit
# das auf jedem Konto funktioniert, das sich anmeldet, nicht nur auf dem
# zum Installationszeitpunkt aktiven.
Write-Host "==> Registriere Sitzungs-Agent (Screenshots) ..." -ForegroundColor Cyan
$agentAction    = New-ScheduledTaskAction -Execute $agentExe
$agentTrigger   = New-ScheduledTaskTrigger -AtLogOn
# SID statt "BUILTIN\Users" - der Name allein loeste auf diesem System
# "Zuordnungen von Kontennamen und Sicherheitskennungen wurden nicht
# durchgefuehrt" aus (Lokalisierungsproblem), die SID ist sprachunabhaengig.
$agentPrincipal = New-ScheduledTaskPrincipal -GroupId "S-1-5-32-545" -RunLevel Limited
$agentSettings  = New-ScheduledTaskSettingsSet -RestartCount 999 -RestartInterval (New-TimeSpan -Minutes 1) `
                    -ExecutionTimeLimit ([TimeSpan]::Zero) -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
Register-ScheduledTask -TaskName $agentTask -Action $agentAction -Trigger $agentTrigger `
    -Principal $agentPrincipal -Settings $agentSettings -Force | Out-Null

# Sofort auch fuer die aktuelle Sitzung starten, statt auf die naechste
# Anmeldung zu warten.
Start-ScheduledTask -TaskName $agentTask -ErrorAction SilentlyContinue

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
# Erwartet meist ein "Wert nicht gefunden" (der Eintrag existiert nur bei
# Upgrades von der alten .bat-basierten Autostart-Version) - das ist kein
# Fehler. reg.exe's eigene Fehlerausgabe wuerde unter $ErrorActionPreference
# = "Stop" trotz 2>$null als abbrechender Fehler behandelt, daher try/catch
# statt Stream-Umleitung.
try { reg delete "HKCU\Software\Microsoft\Windows\CurrentVersion\Run" /v "AIMonitor" /f *>$null } catch {}

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
