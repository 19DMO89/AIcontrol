<#
    AI-Monitor - Diagnostics
    ========================
    For testing: starts the installed service EXE once under the SYSTEM
    account (via a scheduled task) - exactly the context the real Windows
    service uses - and writes the output to a log file, so a failure on
    service start can be traced.

    The result is then in:
        diagnose_output.log (in the same folder as this script)
#>
$ErrorActionPreference = "Stop"
$logFile = Join-Path (Split-Path -Parent $MyInvocation.MyCommand.Path) "diagnose_output.log"

$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltinRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "Restarting with administrator rights (confirm the UAC prompt) ..." -ForegroundColor Yellow
    try {
        Start-Process powershell -Verb RunAs -ArgumentList "-NoExit", "-ExecutionPolicy", "Bypass", "-File", "`"$($MyInvocation.MyCommand.Path)`"" -ErrorAction Stop
    } catch {
        Write-Host "Administrator rights were not granted." -ForegroundColor Red
        Read-Host "Press Enter to close this window"
    }
    exit
}

try {
    "=== AI-Monitor diagnostics - $(Get-Date) ===" | Out-File $logFile -Encoding utf8

    $svcExe = "C:\ProgramData\AIMonitor\bin\service\AIMonitorService.exe"
    if (-not (Test-Path $svcExe)) {
        "ERROR: $svcExe not found - is AI-Monitor installed?" | Add-Content $logFile
        Write-Host "ERROR: $svcExe not found." -ForegroundColor Red
        Read-Host "Press Enter to close this window"
        exit 1
    }

    # No more cmd.exe wrapper: the previous test run showed that cmd.exe
    # itself hangs under the scheduled-task "ServiceAccount" context before
    # it even starts our EXE - that was an artefact of the test setup, not a
    # statement about AIMonitorService.exe. Now: EXE directly as the task
    # action, just observe the process list (no output redirection needed).
    "--- Test run as the SYSTEM account (debug mode, 20s, without cmd.exe) ---" | Add-Content $logFile

    $action = New-ScheduledTaskAction -Execute $svcExe -Argument "debug"
    $principal = New-ScheduledTaskPrincipal -UserId "SYSTEM" -LogonType ServiceAccount -RunLevel Highest
    Register-ScheduledTask -TaskName "AIMonitorDiag" -Action $action -Principal $principal -Force | Out-Null
    Start-ScheduledTask -TaskName "AIMonitorDiag"

    "" | Add-Content $logFile
    "--- Process monitoring during the test run ---" | Add-Content $logFile
    for ($i = 0; $i -lt 10; $i++) {
        Start-Sleep -Seconds 2
        $procs = Get-Process -Name "AIMonitorService" -ErrorAction SilentlyContinue
        $seen = if ($procs) { "RUNNING (PID $($procs.Id -join ','), CPU $([math]::Round(($procs | Measure-Object CPU -Sum).Sum,1))s)" } else { "(not present)" }
        "  t+$(($i+1)*2)s: AIMonitorService.exe = $seen" | Add-Content $logFile
    }

    $taskInfo = Get-ScheduledTaskInfo -TaskName "AIMonitorDiag" -ErrorAction SilentlyContinue
    "" | Add-Content $logFile
    "--- Task Scheduler info ---" | Add-Content $logFile
    "  LastRunTime: $($taskInfo.LastRunTime)  LastTaskResult: $($taskInfo.LastTaskResult) (0x$('{0:X}' -f $taskInfo.LastTaskResult))" | Add-Content $logFile

    Stop-ScheduledTask -TaskName "AIMonitorDiag" -ErrorAction SilentlyContinue
    Get-Process -Name "AIMonitorService" -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
    Unregister-ScheduledTask -TaskName "AIMonitorDiag" -Confirm:$false -ErrorAction SilentlyContinue

    "" | Add-Content $logFile
    "--- Current service status ---" | Add-Content $logFile
    (& sc.exe query AIMonitor 2>&1) | Add-Content $logFile

    "" | Add-Content $logFile
    "--- Most recent Service Control Manager events ---" | Add-Content $logFile
    Get-WinEvent -FilterHashtable @{LogName='System'; ProviderName='Service Control Manager'} -MaxEvents 30 -ErrorAction SilentlyContinue |
        Where-Object { $_.Message -match "AIMonitor" } | Select-Object -First 6 |
        ForEach-Object { "[$($_.TimeCreated)] $($_.Message)" | Add-Content $logFile; "" | Add-Content $logFile }

    Write-Host ""
    Write-Host "Done. The result is in:" -ForegroundColor Green
    Write-Host $logFile
    Write-Host ""
    Get-Content $logFile
    Write-Host ""
    Read-Host "Press Enter to close this window"

} catch {
    "ERROR: $($_.Exception.Message)`n$($_.ScriptStackTrace)" | Add-Content $logFile
    Write-Host "ERROR: $($_.Exception.Message)" -ForegroundColor Red
    Read-Host "Press Enter to close this window"
}
