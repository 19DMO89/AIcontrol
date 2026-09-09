"""
Tiny translation layer for AI-Monitor.

English is the canonical language; German is a switchable alternative. The
active language is stored per installation in the database (`settings` table,
key ``language``) so the monitor service and the dashboard agree on it.

Usage:
    from i18n import t
    t("login.sign_in", "en")                  -> "Sign in"
    t("event.network.title", "de", domain=x)  -> "KI-Verbindung: <x>"

An unknown key returns the key itself (so a missing translation is visible
rather than crashing); an unknown language falls back to English.
"""

LANGUAGES = ("en", "de")
DEFAULT = "en"

_STRINGS: dict[str, dict[str, str]] = {
    "en": {
        # ── Login window ────────────────────────────────────────────────
        "login.window_title":   "AI-Monitor · Sign in",
        "login.subtitle":       "WorldSkills · Monitoring system",
        "login.version":        "Version {version}",
        "login.first_run":      "First-time setup — set credentials",
        "login.username":       "Username",
        "login.password":       "Password",
        "login.confirm":        "Confirm password",
        "login.sign_in":        "Sign in",
        "login.err_user_short": "Username too short (min. 2 characters)",
        "login.err_pw_short":   "Password too short (min. 6 characters)",
        "login.err_pw_match":   "Passwords do not match",
        "login.err_wrong":      "Wrong username or password",
        # ── CLI (--set-credentials) ─────────────────────────────────────
        "cli.username":         "Username: ",
        "cli.password":         "Password: ",
        "cli.confirm":          "Confirm password: ",
        "cli.err_user_short":   "Error: username too short (min. 2 characters).",
        "cli.err_pw_short":     "Error: password too short (min. 6 characters).",
        "cli.err_pw_match":     "Error: passwords do not match.",
        "cli.ok":               "[OK] Credentials for '{username}' set.",
        # ── Dashboard chrome ───────────────────────────────────────────
        "app.window_title":     "AI-Monitor · Activity log",
        "app.signed_in_as":     "Signed in as: {name}",
        "app.stats":            "Total: {total}  |  Critical: {crit}  |  Warnings: {warn}  |  Unread: {unread}",
        "app.export_csv":       "Export (CSV)",
        "app.ack_all":          "Acknowledge all",
        "app.refresh":          "Refresh",
        "app.change_creds":     "Change credentials",
        "creds.title":          "Change credentials",
        "creds.new_username":   "New username",
        "creds.new_password":   "New password",
        "creds.confirm":        "Confirm password",
        "creds.save":           "Save",
        "creds.cancel":         "Cancel",
        "creds.saved":          "Credentials updated. They take effect on the next sign-in.",
        "app.filter":           "Filter:",
        "app.auto_refresh":     "Auto-refresh (30s)",
        "app.details":          "Details",
        "app.acknowledge":      "Acknowledge",
        "app.show_screenshot":  "Show screenshot",
        "app.no_details":       "No further details.",
        "app.screenshot_line":  "\U0001f4f7 Screenshot: {path}",
        "app.status_bar":       "Last updated: {time}   —   Del key: delete entry",
        "app.last_updated":     "Last updated: {time}",
        # column headers
        "col.time":             "Time",
        "col.type":             "Type",
        "col.severity":         "Severity",
        "col.description":      "Description",
        "col.status":           "Status",
        # type labels
        "type.network":         "Network",
        "type.browser":         "Browser",
        "type.process":         "Process",
        "type.clipboard":       "Clipboard",
        "type.all":             "All",
        # severity labels
        "sev.critical":         "Critical",
        "sev.warning":          "Warning",
        "sev.info":             "Info",
        # dialogs
        "dlg.ack_all_title":    "Acknowledge",
        "dlg.ack_all_msg":      "Mark all entries as seen?",
        "dlg.delete_title":     "Delete",
        "dlg.delete_msg":       "Really delete this entry?",
        "dlg.screenshot_title": "Screenshot",
        "dlg.screenshot_missing": "File not found.",
        "dlg.screenshot_load_err": "Error loading: {error}",
        "dlg.screenshot_window": "Screenshot – {name}",
        "dlg.export_title":     "Export activities",
        "dlg.export_ok_title":  "Export successful",
        "dlg.export_ok_msg":    "File saved:\n{path}",
        "dlg.csv_files":        "CSV file",
        "dlg.all_files":        "All files",
        # csv header row
        "csv.timestamp":        "Timestamp",
        "csv.type":             "Type",
        "csv.severity":         "Severity",
        "csv.title":            "Title",
        "csv.details":          "Details",
        "csv.screenshot":       "Screenshot",
        "csv.acknowledged":     "Acknowledged",
        "csv.yes":              "Yes",
        "csv.no":               "No",
        # language switch
        "lang.label":           "Language",
        # ── Event text (written by the monitor service) ────────────────
        "event.network.title":   "AI connection: {domain}",
        "event.network.details": "Process: {proc}  |  IP: {ip}  |  Host: {host}  |  Port: {port}",
        "event.dns.title":       "AI service in DNS cache: {domain}",
        "event.dns.details":     "Domain found in the Windows DNS cache — a connection was made.\nProcess: {proc}",
        "event.browser.title":   "AI website opened ({browser}): {domain}",
        "event.browser.details": "URL: {url}\nTitle: {title}",
        "event.process.title":   "AI program detected: {label}",
        "event.process.details": "Path: {path}\nPID: {pid}",
        "event.flutter.title":   "AI program detected (stand-alone app): {title}",
        "event.flutter.details": "Window title: {title}\nPath: {path}\nPID: {pid}\nDetected via window title (rule: {rule})",
        "event.clipboard.title":   "AI-typical text on the clipboard",
        "event.clipboard.details": "Pattern: \"{pattern}\"\n\nExcerpt: {excerpt}…",
        # process labels (fill {label} above)
        "proclabel.claude_code":    "Claude Code CLI (AI coding assistant)",
        "proclabel.claude_desktop": "Claude desktop app",
        "proclabel.claude_generic": "Claude ({name})",
        "proclabel.chatgpt":        "ChatGPT desktop app",
        "proclabel.cursor":         "Cursor AI IDE",
        "proclabel.windsurf":       "Windsurf AI IDE",
        "proclabel.generic":        "{name} (rule: {rule})",
    },
    "de": {
        # ── Login window ────────────────────────────────────────────────
        "login.window_title":   "AI-Monitor · Anmeldung",
        "login.subtitle":       "Berufsweltmeisterschaften · Überwachungssystem",
        "login.version":        "Version {version}",
        "login.first_run":      "Ersteinrichtung — Zugangsdaten festlegen",
        "login.username":       "Benutzername",
        "login.password":       "Passwort",
        "login.confirm":        "Passwort bestätigen",
        "login.sign_in":        "Anmelden",
        "login.err_user_short": "Benutzername zu kurz (min. 2 Zeichen)",
        "login.err_pw_short":   "Passwort zu kurz (min. 6 Zeichen)",
        "login.err_pw_match":   "Passwörter stimmen nicht überein",
        "login.err_wrong":      "Falscher Benutzername oder Passwort",
        # ── CLI (--set-credentials) ─────────────────────────────────────
        "cli.username":         "Benutzername: ",
        "cli.password":         "Passwort: ",
        "cli.confirm":          "Passwort bestätigen: ",
        "cli.err_user_short":   "Fehler: Benutzername zu kurz (min. 2 Zeichen).",
        "cli.err_pw_short":     "Fehler: Passwort zu kurz (min. 6 Zeichen).",
        "cli.err_pw_match":     "Fehler: Passwörter stimmen nicht überein.",
        "cli.ok":               "[OK] Zugangsdaten für '{username}' gesetzt.",
        # ── Dashboard chrome ───────────────────────────────────────────
        "app.window_title":     "AI-Monitor · Aktivitätsprotokoll",
        "app.signed_in_as":     "Angemeldet als: {name}",
        "app.stats":            "Gesamt: {total}  |  Kritisch: {crit}  |  Warnungen: {warn}  |  Ungelesen: {unread}",
        "app.export_csv":       "Exportieren (CSV)",
        "app.ack_all":          "Alle bestätigen",
        "app.refresh":          "Aktualisieren",
        "app.change_creds":     "Zugangsdaten ändern",
        "creds.title":          "Zugangsdaten ändern",
        "creds.new_username":   "Neuer Benutzername",
        "creds.new_password":   "Neues Passwort",
        "creds.confirm":        "Passwort bestätigen",
        "creds.save":           "Speichern",
        "creds.cancel":         "Abbrechen",
        "creds.saved":          "Zugangsdaten aktualisiert. Sie gelten ab der nächsten Anmeldung.",
        "app.filter":           "Filter:",
        "app.auto_refresh":     "Auto-Refresh (30s)",
        "app.details":          "Details",
        "app.acknowledge":      "Bestätigen",
        "app.show_screenshot":  "Screenshot anzeigen",
        "app.no_details":       "Keine weiteren Details.",
        "app.screenshot_line":  "\U0001f4f7 Screenshot: {path}",
        "app.status_bar":       "Zuletzt aktualisiert: {time}   —   Entf-Taste: Eintrag löschen",
        "app.last_updated":     "Zuletzt aktualisiert: {time}",
        "col.time":             "Zeit",
        "col.type":             "Typ",
        "col.severity":         "Schwere",
        "col.description":      "Beschreibung",
        "col.status":           "Status",
        "type.network":         "Netzwerk",
        "type.browser":         "Browser",
        "type.process":         "Prozess",
        "type.clipboard":       "Zwischenablage",
        "type.all":             "Alle",
        "sev.critical":         "Kritisch",
        "sev.warning":          "Warnung",
        "sev.info":             "Info",
        "dlg.ack_all_title":    "Bestätigen",
        "dlg.ack_all_msg":      "Alle Einträge als gesehen markieren?",
        "dlg.delete_title":     "Löschen",
        "dlg.delete_msg":       "Diesen Eintrag wirklich löschen?",
        "dlg.screenshot_title": "Screenshot",
        "dlg.screenshot_missing": "Datei nicht gefunden.",
        "dlg.screenshot_load_err": "Fehler beim Laden: {error}",
        "dlg.screenshot_window": "Screenshot – {name}",
        "dlg.export_title":     "Aktivitäten exportieren",
        "dlg.export_ok_title":  "Export erfolgreich",
        "dlg.export_ok_msg":    "Datei gespeichert:\n{path}",
        "dlg.csv_files":        "CSV-Datei",
        "dlg.all_files":        "Alle Dateien",
        "csv.timestamp":        "Zeitstempel",
        "csv.type":             "Typ",
        "csv.severity":         "Schwere",
        "csv.title":            "Titel",
        "csv.details":          "Details",
        "csv.screenshot":       "Screenshot",
        "csv.acknowledged":     "Bestätigt",
        "csv.yes":              "Ja",
        "csv.no":               "Nein",
        "lang.label":           "Sprache",
        # ── Event text ────────────────────────────────────────────────
        "event.network.title":   "KI-Verbindung: {domain}",
        "event.network.details": "Prozess: {proc}  |  IP: {ip}  |  Host: {host}  |  Port: {port}",
        "event.dns.title":       "KI-Dienst im DNS-Cache: {domain}",
        "event.dns.details":     "Domain im Windows-DNS-Cache gefunden — eine Verbindung wurde hergestellt.\nProzess: {proc}",
        "event.browser.title":   "KI-Webseite geöffnet ({browser}): {domain}",
        "event.browser.details": "URL: {url}\nTitel: {title}",
        "event.process.title":   "KI-Programm erkannt: {label}",
        "event.process.details": "Pfad: {path}\nPID: {pid}",
        "event.flutter.title":   "KI-Programm erkannt (eigenständige App): {title}",
        "event.flutter.details": "Fenstertitel: {title}\nPfad: {path}\nPID: {pid}\nErkannt über den Fenstertitel (Regel: {rule})",
        "event.clipboard.title":   "KI-typischer Text in der Zwischenablage",
        "event.clipboard.details": "Muster: \"{pattern}\"\n\nAuszug: {excerpt}…",
        "proclabel.claude_code":    "Claude Code CLI (KI-Coding-Assistent)",
        "proclabel.claude_desktop": "Claude Desktop-App",
        "proclabel.claude_generic": "Claude ({name})",
        "proclabel.chatgpt":        "ChatGPT Desktop-App",
        "proclabel.cursor":         "Cursor KI-IDE",
        "proclabel.windsurf":       "Windsurf KI-IDE",
        "proclabel.generic":        "{name} (Regel: {rule})",
    },
}


def normalize(lang: str | None) -> str:
    return lang if lang in _STRINGS else DEFAULT


def t(key: str, lang: str | None = DEFAULT, **kwargs) -> str:
    table = _STRINGS.get(normalize(lang), _STRINGS[DEFAULT])
    template = table.get(key) or _STRINGS[DEFAULT].get(key) or key
    if kwargs:
        try:
            return template.format(**kwargs)
        except (KeyError, IndexError):
            return template
    return template
