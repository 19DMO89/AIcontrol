<#
    AI-Monitor - Diagnose
    ======================
    Testweise: startet die installierte Dienst-EXE einmalig unter dem
    SYSTEM-Konto (per geplantem Task) - genau der Kontext, den der echte
    Windows-Dienst benutzt - und schreibt die Ausgabe in eine Log-Datei,
    damit der Fehler beim Dienststart nachvollzogen werden kann.

    Ergebnis liegt danach in:
        diagnose_output.log (im selben Ordner wie dieses Skript)
#>
$ErrorActionPreference = "Stop"
$logFile = Join-Path (Split-Path -Parent $MyInvocation.MyCommand.Path) "diagnose_output.log"

$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltinRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "Starte mit Administratorrechten neu (UAC-Abfrage bestaetigen) ..." -ForegroundColor Yellow
    try {
        Start-Process powershell -Verb RunAs -ArgumentList "-NoExit", "-ExecutionPolicy", "Bypass", "-File", "`"$($MyInvocation.MyCommand.Path)`"" -ErrorAction Stop
    } catch {
        Write-Host "Administratorrechte wurden nicht erteilt." -ForegroundColor Red
        Read-Host "Fenster mit Enter schliessen"
    }
    exit
}

try {
    "=== AI-Monitor Diagnose - $(Get-Date) ===" | Out-File $logFile -Encoding utf8

    $svcExe = "C:\ProgramData\AIMonitor\bin\service\AIMonitorService.exe"
    if (-not (Test-Path $svcExe)) {
        "FEHLER: $svcExe nicht gefunden - ist AI-Monitor installiert?" | Add-Content $logFile
        Write-Host "FEHLER: $svcExe nicht gefunden." -ForegroundColor Red
        Read-Host "Fenster mit Enter schliessen"
        exit 1
    }

    # Kein cmd.exe-Wrapper mehr: der vorherige Testlauf zeigte, dass cmd.exe
    # selbst unter dem Scheduled-Task-"ServiceAccount"-Kontext haengt, bevor
    # es unsere EXE ueberhaupt startet - das war ein Artefakt des Testaufbaus,
    # keine Aussage ueber AIMonitorService.exe. Jetzt: EXE direkt als Task-
    # Aktion, nur Prozessliste beobachten (keine Ausgabe-Umleitung noetig).
    "--- Testlauf als SYSTEM-Konto (debug-Modus, 20s, ohne cmd.exe) ---" | Add-Content $logFile

    $action = New-ScheduledTaskAction -Execute $svcExe -Argument "debug"
    $principal = New-ScheduledTaskPrincipal -UserId "SYSTEM" -LogonType ServiceAccount -RunLevel Highest
    Register-ScheduledTask -TaskName "AIMonitorDiag" -Action $action -Principal $principal -Force | Out-Null
    Start-ScheduledTask -TaskName "AIMonitorDiag"

    "" | Add-Content $logFile
    "--- Prozess-Ueberwachung waehrend des Testlaufs ---" | Add-Content $logFile
    for ($i = 0; $i -lt 10; $i++) {
        Start-Sleep -Seconds 2
        $procs = Get-Process -Name "AIMonitorService" -ErrorAction SilentlyContinue
        $seen = if ($procs) { "LAEUFT (PID $($procs.Id -join ','), CPU $([math]::Round(($procs | Measure-Object CPU -Sum).Sum,1))s)" } else { "(nicht vorhanden)" }
        "  t+$(($i+1)*2)s: AIMonitorService.exe = $seen" | Add-Content $logFile
    }

    $taskInfo = Get-ScheduledTaskInfo -TaskName "AIMonitorDiag" -ErrorAction SilentlyContinue
    "" | Add-Content $logFile
    "--- Task-Scheduler-Info ---" | Add-Content $logFile
    "  LastRunTime: $($taskInfo.LastRunTime)  LastTaskResult: $($taskInfo.LastTaskResult) (0x$('{0:X}' -f $taskInfo.LastTaskResult))" | Add-Content $logFile

    Stop-ScheduledTask -TaskName "AIMonitorDiag" -ErrorAction SilentlyContinue
    Get-Process -Name "AIMonitorService" -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
    Unregister-ScheduledTask -TaskName "AIMonitorDiag" -Confirm:$false -ErrorAction SilentlyContinue

    "" | Add-Content $logFile
    "--- Aktueller Dienststatus ---" | Add-Content $logFile
    (& sc.exe query AIMonitor 2>&1) | Add-Content $logFile

    "" | Add-Content $logFile
    "--- Letzte Service-Control-Manager-Ereignisse ---" | Add-Content $logFile
    Get-WinEvent -FilterHashtable @{LogName='System'; ProviderName='Service Control Manager'} -MaxEvents 30 -ErrorAction SilentlyContinue |
        Where-Object { $_.Message -match "AIMonitor" } | Select-Object -First 6 |
        ForEach-Object { "[$($_.TimeCreated)] $($_.Message)" | Add-Content $logFile; "" | Add-Content $logFile }

    Write-Host ""
    Write-Host "Fertig. Ergebnis steht in:" -ForegroundColor Green
    Write-Host $logFile
    Write-Host ""
    Get-Content $logFile
    Write-Host ""
    Read-Host "Fenster mit Enter schliessen"

} catch {
    "FEHLER: $($_.Exception.Message)`n$($_.ScriptStackTrace)" | Add-Content $logFile
    Write-Host "FEHLER: $($_.Exception.Message)" -ForegroundColor Red
    Read-Host "Fenster mit Enter schliessen"
}
