<#
    AI-Monitor - Paketierung
    ========================
    Packt das bereits gebaute dist\ (siehe build.ps1) zusammen mit
    Install-AIMonitor.ps1 in eine einzige AIMonitor-Setup.exe, damit auf dem
    Zielrechner nur noch ein Doppelklick noetig ist - kein Python, kein
    manueller Build-Schritt.

    Funktionsweise: dist\ + Install-AIMonitor.ps1 + Uninstall-AIMonitor.ps1
    werden in bundle.zip gepackt (der Installer kopiert den Deinstaller mit
    auf den Zielrechner und traegt ihn in "Apps & Features" ein) und als
    eingebettete Ressource in einen winzigen C#-Stub
    kompiliert (per csc.exe, Teil jeder .NET-Framework-Installation - kein
    Zusatzwerkzeug noetig). Die fertige EXE traegt ein "requireAdministrator"-
    Manifest, fragt beim Doppelklick also selbst per UAC nach Adminrechten,
    entpackt sich dann in einen Temp-Ordner und ruft dort
    Install-AIMonitor.ps1 auf. Kein Selbst-Neustart-Race wie bei anderen
    Self-Extractor-Ansaetzen, weil der gesamte Vorgang von Anfang an in
    einem einzigen (bereits elevierten) Prozessbaum laeuft.

    Voraussetzung: build.ps1 wurde bereits ausgefuehrt (dist\ existiert).
    Ausfuehren:    powershell -ExecutionPolicy Bypass -File package.ps1
    Ergebnis:      AIMonitor-Setup.exe
#>
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root

$distDir = Join-Path $root "dist"
if (-not (Test-Path (Join-Path $distDir "AIMonitorService")) -or
    -not (Test-Path (Join-Path $distDir "AIMonitorDashboard.exe")) -or
    -not (Test-Path (Join-Path $distDir "AISessionAgent.exe"))) {
    Write-Error "dist\ nicht gefunden oder unvollstaendig. Bitte zuerst build.ps1 ausfuehren."
    exit 1
}

$csc = Join-Path $env:WINDIR "Microsoft.NET\Framework64\v4.0.30319\csc.exe"
if (-not (Test-Path $csc)) {
    Write-Error "csc.exe (.NET-Framework-Compiler) nicht gefunden unter: $csc"
    exit 1
}

$stagingDir = Join-Path $root "build\installer_staging"
if (Test-Path $stagingDir) { Remove-Item $stagingDir -Recurse -Force }
New-Item -ItemType Directory -Force -Path $stagingDir | Out-Null

Write-Host "==> Packe dist\ + Install-AIMonitor.ps1 nach bundle.zip ..." -ForegroundColor Cyan
$bundleContentDir = Join-Path $stagingDir "bundle_content"
New-Item -ItemType Directory -Force -Path $bundleContentDir | Out-Null
Copy-Item $distDir (Join-Path $bundleContentDir "dist") -Recurse -Force
Copy-Item (Join-Path $root "Install-AIMonitor.ps1") $bundleContentDir -Force
# Der Installer kopiert diese beiden mit nach %ProgramData%\AIMonitor\bin und
# registriert sie als "Apps & Features"-Deinstaller - ohne sie im Bundle
# bliebe auf dem Zielrechner kein Weg zum Deinstallieren.
Copy-Item (Join-Path $root "Uninstall-AIMonitor.ps1") $bundleContentDir -Force
Copy-Item (Join-Path $root "AI-Monitor deinstallieren.bat") $bundleContentDir -Force

# Versionsnummer aus config.py ziehen und beilegen, damit der Installer sie
# fuer den "Apps & Features"-Eintrag kennt (config.py selbst wird nicht
# mitgeliefert - nur die Zahl).
$ver = "0.0.0"
$m = Select-String -Path (Join-Path $root "config.py") -Pattern 'VERSION\s*=\s*["'']([^"'']+)["'']' | Select-Object -First 1
if ($m) { $ver = $m.Matches[0].Groups[1].Value }
Set-Content -Path (Join-Path $bundleContentDir "VERSION.txt") -Value $ver -NoNewline -Encoding ascii
Write-Host "    Version: $ver"
$zipPath = Join-Path $stagingDir "bundle.zip"
Compress-Archive -Path (Join-Path $bundleContentDir "*") -DestinationPath $zipPath -CompressionLevel Optimal

Write-Host "==> Erzeuge Self-Extract-Stub ..." -ForegroundColor Cyan
$programCsPath = Join-Path $stagingDir "Program.cs"
@'
using System;
using System.Diagnostics;
using System.IO;
using System.Reflection;

class Program
{
    static int Main()
    {
        string tempDir = Path.Combine(Path.GetTempPath(), "AIMonitorSetup_" + Guid.NewGuid().ToString("N"));
        Directory.CreateDirectory(tempDir);
        try
        {
            string zipPath = Path.Combine(tempDir, "bundle.zip");
            using (Stream res = Assembly.GetExecutingAssembly().GetManifestResourceStream("bundle.zip"))
            using (FileStream fs = File.Create(zipPath))
            {
                res.CopyTo(fs);
            }

            string bootstrapPath = Path.Combine(tempDir, "bootstrap.ps1");
            string bootstrap =
                "$ErrorActionPreference = \"Stop\"\r\n" +
                "$here = Split-Path -Parent $MyInvocation.MyCommand.Path\r\n" +
                "Expand-Archive -Path (Join-Path $here \"bundle.zip\") -DestinationPath $here -Force\r\n" +
                "& (Join-Path $here \"Install-AIMonitor.ps1\")\r\n";
            File.WriteAllText(bootstrapPath, bootstrap);

            ProcessStartInfo psi = new ProcessStartInfo();
            psi.FileName = "powershell.exe";
            psi.Arguments = "-NoProfile -ExecutionPolicy Bypass -File \"" + bootstrapPath + "\"";
            psi.UseShellExecute = false;

            using (Process p = Process.Start(psi))
            {
                p.WaitForExit();
                return p.ExitCode;
            }
        }
        finally
        {
            try { Directory.Delete(tempDir, true); } catch { }
        }
    }
}
'@ | Set-Content -Path $programCsPath -Encoding UTF8

$manifestPath = Join-Path $stagingDir "app.manifest"
@'
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<assembly xmlns="urn:schemas-microsoft-com:asm.v1" manifestVersion="1.0">
  <assemblyIdentity version="1.0.0.0" name="AIMonitor.Setup"/>
  <trustInfo xmlns="urn:schemas-microsoft-com:asm.v3">
    <security>
      <requestedPrivileges>
        <requestedExecutionLevel level="requireAdministrator" uiAccess="false" />
      </requestedPrivileges>
    </security>
  </trustInfo>
</assembly>
'@ | Set-Content -Path $manifestPath -Encoding UTF8

Write-Host "==> Kompiliere AIMonitor-Setup.exe ..." -ForegroundColor Cyan
$outputExe = Join-Path $root "AIMonitor-Setup.exe"
if (Test-Path $outputExe) { Remove-Item $outputExe -Force }

$iconArg = @()
$iconPath = Join-Path $root "icon.ico"
if (Test-Path $iconPath) { $iconArg = @("/win32icon:`"$iconPath`"") }

$cscArgs = @(
    "/nologo",
    "/target:winexe",
    "/out:`"$outputExe`"",
    "/win32manifest:`"$manifestPath`""
) + $iconArg + @(
    "/resource:`"$zipPath`",bundle.zip",
    "`"$programCsPath`""
)

$cscOutput = & $csc @cscArgs 2>&1
if ($LASTEXITCODE -ne 0 -or -not (Test-Path $outputExe)) {
    Write-Host $cscOutput
    Write-Error "Kompilierung fehlgeschlagen (Exit-Code $LASTEXITCODE)."
    exit 1
}

Remove-Item $stagingDir -Recurse -Force

Write-Host ""
Write-Host "==> Fertig: $outputExe" -ForegroundColor Green
Write-Host "    Einfach auf dem Zielrechner doppelklicken - fragt selbst nach" -ForegroundColor Green
Write-Host "    Administratorrechten (UAC) und installiert alles." -ForegroundColor Green
