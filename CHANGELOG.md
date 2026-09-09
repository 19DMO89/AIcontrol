# Changelog

All notable changes to AI-Monitor. Newest version first.

## v3.0.0 — 2026-09-09

### Changed
- **The whole project is now in English.** Dashboard, login screen, event
  text, the install / uninstall / diagnostics scripts, the `.bat` launchers
  and this documentation. German is available as a switchable alternative:
  an `EN | DE` toggle in the dashboard top bar and on the login screen.
  English is the default; the choice is stored per installation in the
  database (`settings` table) and is shared between the service and the
  dashboard.
- Event text (titles/details) is written by the service in the configured
  language. A later language switch only affects **new** events — entries
  already logged keep their wording, like any audit log.
- `.bat` launchers renamed: `Install AI-Monitor.bat`,
  `Uninstall AI-Monitor.bat`, `AI-Monitor Diagnostics.bat`.

### Notes
- No database schema change that affects existing rows — upgrading over an
  existing installation is safe; the DB, screenshots and password are kept.
- False positives logged by older versions are not rewritten or removed.
  Select and delete old entries in the dashboard.

## v2.0.0 — 2026-09-07

### Added
- **Version shown in the dashboard and on the login screen.** Makes it
  obvious at a glance which version a machine runs — useful for bug reports
  and to tell a pre-update false positive still in the DB from a live
  detection.
- `AIMonitorDashboard.exe --version` prints the version on the console.
- The version number now has a single source (`VERSION` in `config.py`);
  the installer picks it up for the "Apps & Features" entry.

## v1.5.0 — 2026-09-03

### Fixed
- **`bing.com` matched as AI.** Bare `bing.com` was in the detection list —
  but Windows 11, Edge, Chrome, the widgets and Windows Search contact it
  constantly with zero AI use. Caused "Bing detected as AI" and "Chrome
  detected as AI" false positives (Chrome caught on that very bing.com
  connection). Replaced with `copilot.microsoft.com` and the paths
  `bing.com/chat`, `bing.com/copilot`.
- **Process detection matched a substring of the full path.** A list entry
  like `jan` (a local LLM runner) would have flagged *every* process of a
  Windows user named "Jan" (path `C:\Users\Jan\…`) as an AI program. Now an
  exact match against the process / file name.
- **Domain matching on a label boundary.** `x.ai` now matches `api.x.ai`
  but no longer `climax.airlines.com` and the like.

### Changed
- **Repeated use is now logged.** Previously every app/domain/URL was
  recorded exactly once for its lifetime — frequent use of the same running
  session was invisible. Now: one entry per time window (`REDETECT_AFTER`,
  default 5 min), then another in the next. Browser hits are placed by the
  actual visit time.

## v1.4.0 — 2026-09-03

### Fixed
- **The login dialog gave no feedback on a wrong entry.** The error message
  ("Wrong username or password", "Password too short" …) was set but sat
  outside the visible area of the fixed-size, non-resizable login window.
  The status line now sits in the login card, and the window is taller.

### Added
- **The uninstaller is installed and registered in Windows.** The
  installation places `Uninstall-AIMonitor.ps1` under
  `%ProgramData%\AIMonitor\bin` (read/execute only for standard users) and
  adds an **"AI-Monitor"** entry under Settings → *Apps* / *Programs and
  Features*. Previously `AIMonitor-Setup.exe` left no way to uninstall on
  the target machine.
- **Desktop folder instead of a loose shortcut.** An `AI-Monitor` folder is
  created on the common desktop with the dashboard and an uninstall shortcut
  (the latter asks for administrator rights via UAC).

### Improved
- **Upgrading over an existing installation.** A still-open dashboard is
  closed before copying (otherwise overwriting `AIMonitorDashboard.exe`
  failed). Existing dashboard credentials are kept and not asked for again
  on a re-install (`--has-credentials` check).
- The uninstaller also removes the "Apps & Features" entry and the desktop
  folder, and copies itself from the install folder to `%TEMP%` on start so
  it does not block its own cleanup.
- `package.ps1` bundles `Uninstall-AIMonitor.ps1` and the uninstall `.bat`
  into `AIMonitor-Setup.exe`.

## v1.3.1 — 2026-08-19

- **Installation:** service registration sporadically failed with "access
  denied" (exit code 5) because antivirus was scanning the freshly copied
  `AIMonitorService.exe`. Now retried automatically.
- **Uninstall:** the own tamper-protection rule (deny for standard users on
  the screenshots folder) sometimes blocked its own cleanup, since an admin
  account is usually also a member of that group. Left-over database /
  screenshot files were not removed as a result.

## v1.3.0 — 2026-08-19

- Pre-built `AIMonitor-Setup.exe` for download — no Python, no manual build
  needed anymore. `build.ps1` + `package.ps1` regenerate the file from
  source.

## v1.2.0 — 2026-07-16

### Most important fix
- The Windows service had never **actually started** (silent 30-second
  timeout, Event 7009). Three nested PyInstaller/pywin32 bugs fixed and
  verified end-to-end on a real installed service: missing `pythoncom` DLL
  in the build; wrong `--console` mode (services run in Session 0 without a
  console); the actual cause: `HandleCommandLine` does not drive the SCM
  handshake in this pywin32 version — `StartServiceCtrlDispatcher` is now
  called directly.

### Added
- Screenshots now work via a new session agent (runs in the user session,
  since a service in Session 0 has no access to the desktop).
- The screenshot folder is now write-only for standard users, not
  deletable — evidence cannot be removed.
- Browser detection now works via the real service too (multiple
  Chrome/Edge/Brave profiles, real user profiles instead of SYSTEM
  environment variables).
- GitHub Copilot detection fixed, plus JetBrains AI, Amazon Q, Cody,
  Supermaven added.
- Own app icon; old `.bat` scripts replaced by the service approach removed.

## v1.1.0 — 2026-07-16

- Windows service installation (`monitor_service.py`) incl. install /
  uninstall scripts.
- Diagnostics tool `Diagnose-AIMonitor.ps1` for troubleshooting service
  problems.
- Fixed data folder `%PROGRAMDATA%\AIMonitor\data` so the service and
  dashboard use the same data.
- Build script `build.ps1` for PyInstaller builds.
- More detection keywords for AI windows/processes.

## v1.0.0

- First release: AI-Monitor for WorldSkills.
