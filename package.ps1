<#
    AI-Monitor - Packaging
    ======================
    Packs the already-built dist\ (see build.ps1) together with
    Install-AIMonitor.ps1 into a single AIMonitor-Setup.exe, so the target
    machine only needs a double-click - no Python, no manual build step.

    How it works: dist\ + Install-AIMonitor.ps1 + Uninstall-AIMonitor.ps1 are
    packed into bundle.zip (the installer copies the uninstaller to the
    target machine and registers it in "Apps & Features") and compiled as an
    embedded resource into a tiny C# stub (via csc.exe, part of every .NET
    Framework install - no extra tooling needed). The finished EXE carries a
    "requireAdministrator" manifest, so on a double-click it asks for admin
    rights via UAC itself, then extracts to a temp folder and runs
    Install-AIMonitor.ps1 there. No self-restart race like other
    self-extractor approaches, because the whole process runs from the start
    in a single (already elevated) process tree.

    Requirement: build.ps1 has already been run (dist\ exists).
    Run:         powershell -ExecutionPolicy Bypass -File package.ps1
    Result:      AIMonitor-Setup.exe
#>
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root

$distDir = Join-Path $root "dist"
if (-not (Test-Path (Join-Path $distDir "AIMonitorService")) -or
    -not (Test-Path (Join-Path $distDir "AIMonitorDashboard.exe")) -or
    -not (Test-Path (Join-Path $distDir "AISessionAgent.exe"))) {
    Write-Error "dist\ not found or incomplete. Please run build.ps1 first."
    exit 1
}

$csc = Join-Path $env:WINDIR "Microsoft.NET\Framework64\v4.0.30319\csc.exe"
if (-not (Test-Path $csc)) {
    Write-Error "csc.exe (.NET Framework compiler) not found at: $csc"
    exit 1
}

$stagingDir = Join-Path $root "build\installer_staging"
if (Test-Path $stagingDir) { Remove-Item $stagingDir -Recurse -Force }
New-Item -ItemType Directory -Force -Path $stagingDir | Out-Null

Write-Host "==> Packing dist\ + Install-AIMonitor.ps1 into bundle.zip ..." -ForegroundColor Cyan
$bundleContentDir = Join-Path $stagingDir "bundle_content"
New-Item -ItemType Directory -Force -Path $bundleContentDir | Out-Null
Copy-Item $distDir (Join-Path $bundleContentDir "dist") -Recurse -Force
Copy-Item (Join-Path $root "Install-AIMonitor.ps1") $bundleContentDir -Force
# The installer copies these two to %ProgramData%\AIMonitor\bin and registers
# them as the "Apps & Features" uninstaller - without them in the bundle there
# would be no way to uninstall on the target machine.
Copy-Item (Join-Path $root "Uninstall-AIMonitor.ps1") $bundleContentDir -Force
Copy-Item (Join-Path $root "Uninstall AI-Monitor.bat") $bundleContentDir -Force

# Pull the version number from config.py and bundle it, so the installer
# knows it for the "Apps & Features" entry (config.py itself is not shipped -
# only the number).
$ver = "0.0.0"
$m = Select-String -Path (Join-Path $root "config.py") -Pattern 'VERSION\s*=\s*["'']([^"'']+)["'']' | Select-Object -First 1
if ($m) { $ver = $m.Matches[0].Groups[1].Value }
Set-Content -Path (Join-Path $bundleContentDir "VERSION.txt") -Value $ver -NoNewline -Encoding ascii
Write-Host "    Version: $ver"
$zipPath = Join-Path $stagingDir "bundle.zip"
Compress-Archive -Path (Join-Path $bundleContentDir "*") -DestinationPath $zipPath -CompressionLevel Optimal

Write-Host "==> Creating self-extract stub ..." -ForegroundColor Cyan
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

Write-Host "==> Compiling AIMonitor-Setup.exe ..." -ForegroundColor Cyan
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
    Write-Error "Compilation failed (exit code $LASTEXITCODE)."
    exit 1
}

Remove-Item $stagingDir -Recurse -Force

Write-Host ""
Write-Host "==> Done: $outputExe" -ForegroundColor Green
Write-Host "    Just double-click it on the target machine - it asks for" -ForegroundColor Green
Write-Host "    administrator rights (UAC) itself and installs everything." -ForegroundColor Green
