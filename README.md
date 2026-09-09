# AI-Monitor

Monitors a Windows machine for the use of AI tools (ChatGPT, Claude,
Copilot, local LLMs, AI browser extensions, suspicious clipboard content,
...) and logs findings including a screenshot in a local, password-protected
database. Intended for exam / competition situations (e.g. WorldSkills) where
the use of AI aids must be ruled out.

Runs as a Windows service under the `LocalSystem` account, starts
automatically with Windows and cannot be stopped or removed by a standard
user without administrator rights (built-in Windows SCM behaviour).

The dashboard and event text are available in **English or German**,
switchable with the `EN | DE` toggle in the dashboard (and on the login
screen). English is the default; the choice is stored per installation.

## Components

| Component | Purpose |
|---|---|
| `AIMonitorService.exe` | Background service: monitors processes, network connections, browser history, clipboard |
| `AISessionAgent.exe` | Runs in the user session, takes screenshots on a hit (a service in Session 0 has no access to the desktop) |
| `AIMonitorDashboard.exe` | Password-protected viewer for the logged events and screenshots |

## Installation (for most people: read only this)

A pre-built **`AIMonitor-Setup.exe`** is available for download under
[Releases](https://github.com/19DMO89/AIcontrol/releases/latest) — no
Python, no build needed. On the target machine (e.g. the competition PC):

1. Download `AIMonitor-Setup.exe` and double-click it.
2. Confirm the UAC prompt (the file requests the rights automatically).
3. At the end: set a dashboard username/password when prompted (min. 6
   characters) — **do this immediately**, before the PC is handed to
   participants.

That's it — the service and session agent are running, and the desktop has
an **`AI-Monitor`** folder with the dashboard and an uninstall shortcut.

The installed version is shown in the dashboard and on the login screen (top
bar / under the title) and in Windows Settings → Apps.

Program files are then under `%ProgramData%\AIMonitor\bin` (read/execute only
for standard users), the database and screenshots under
`%ProgramData%\AIMonitor\data`.

### Updating an existing installation

Just run the new `AIMonitor-Setup.exe` over the old one (double-click →
UAC). The installer detects the existing installation and performs a clean
upgrade: the service and session-agent task are re-registered, a running
dashboard is closed first, and the **database, screenshots and password are
kept**. No password prompt on an upgrade, no prior uninstall needed. Already
logged events are not rewritten — a language switch or a detection change
only affects new events.

## Build & package (developers only)

Needed when you change `config.py` (the detection list) or the rest of the
code and want to produce a new `AIMonitor-Setup.exe` from it.

Requirements: Windows, Python 3.10+, dependencies installed:

```powershell
python -m pip install -r requirements.txt
```

1. **Build** (creates `dist\AIMonitorService`, `dist\AIMonitorDashboard.exe`,
   `dist\AISessionAgent.exe` via PyInstaller):

   ```powershell
   powershell -ExecutionPolicy Bypass -File build.ps1
   ```

2. **Package** (packs `dist\` + `Install-AIMonitor.ps1` +
   `Uninstall-AIMonitor.ps1` into a single `AIMonitor-Setup.exe`, see
   above):

   ```powershell
   powershell -ExecutionPolicy Bypass -File package.ps1
   ```

   Only needs `csc.exe` (part of every .NET Framework install, no extra
   tooling). `AIMonitor-Setup.exe` is then in the project folder and can be
   copied to any number of target machines.

The version number has a single source: `VERSION` in `config.py`. Bump it
there; the dashboard UI and the installer pick it up.

### Manual install (without AIMonitor-Setup.exe)

Alternatively install directly from the built `dist\`, e.g. for testing on
the developer machine itself:

```powershell
powershell -ExecutionPolicy Bypass -File Install-AIMonitor.ps1
```

Or double-click `Install AI-Monitor.bat`. Requests administrator rights via
UAC automatically.

> **Most common error:** `dist\ not found or incomplete.` This means step 1
> (`build.ps1`) has not been run, or not completely.

Publish a finished `AIMonitor-Setup.exe` as a new release:

```powershell
gh release create vX.Y.Z AIMonitor-Setup.exe --title "vX.Y.Z" --notes "..."
```

## Uninstall

The installation adds an **"AI-Monitor"** entry under Windows Settings →
*Apps* (or *Control Panel → Programs and Features*). Choose "Uninstall"
there — confirm the UAC prompt, done.

Alternatively run the installed script directly:

```powershell
powershell -ExecutionPolicy Bypass -File "%ProgramData%\AIMonitor\bin\Uninstall-AIMonitor.ps1"
```

or in the developer folder:

```powershell
powershell -ExecutionPolicy Bypass -File Uninstall-AIMonitor.ps1
```

Requires administrator rights (deliberately, so participants cannot remove
the monitoring themselves). Options:

- `-KeepData` — keep the database/screenshots under
  `%ProgramData%\AIMonitor\data` instead of deleting them
- `-Force` — uninstall without confirmation

Or double-click `Uninstall AI-Monitor.bat` (also placed under
`%ProgramData%\AIMonitor\bin` after installation).

## Troubleshooting

If the service does not start after installation (Windows Event 7009 /
timeout), the diagnostics script produces a precise error output by running
the installed service EXE once under the SYSTEM account — the same context
the real service uses:

```powershell
powershell -ExecutionPolicy Bypass -File Diagnose-AIMonitor.ps1
```

The result lands in `diagnose_output.log`. Or double-click
`AI-Monitor Diagnostics.bat`.

## Changelog

See [CHANGELOG.md](CHANGELOG.md).

## What is detected?

The monitored domains, process names, window-title keywords and clipboard
patterns are in `config.py` and can be extended there (e.g. `AI_DOMAINS`,
`AI_PROCESSES`, `AI_WINDOW_KEYWORDS`, `AI_CLIPBOARD_PATTERNS`). After a
change you must rebuild and reinstall (steps 1 and 2 above), because the
Python source is compiled entirely into the EXE files.

`AI_PROCESSES` entries are matched against the *exact* process / file name
(not as a substring of the full path); domains are matched on a real label
boundary (`x.ai` matches `api.x.ai`, not `climax.airlines.com`).

**Repeated use:** the same app/domain/URL is logged once per time window and
again in the next window — so repeated use stays visible instead of
collapsing into a single lifetime entry. Window length: `REDETECT_AFTER` in
`config.py` (default 5 minutes).
