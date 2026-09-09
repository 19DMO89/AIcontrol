"""
AI-Monitor - Background monitoring service
Run via:  pythonw monitor.py   (hidden, no console)
      or: python monitor.py    (with console output for debugging)
"""

import os
import sys
import socket
import sqlite3
import shutil
import threading
import time
import ctypes
import ctypes.wintypes
from datetime import datetime
from pathlib import Path

import psutil

import config
import database as db
import i18n

# ── Logging ──────────────────────────────────────────────────────────────────

def log(msg):
    ts = datetime.now().strftime("%H:%M:%S")
    try:
        print(f"[{ts}] {msg}", flush=True)
    except Exception:
        pass


# ── Event logging with screenshot request ─────────────────────────────────────
# The service runs as LocalSystem in Session 0, which has no desktop and so
# cannot grab a screenshot itself - Windows session isolation blocks this
# outright (verified: PIL.ImageGrab raises "OSError: screen grab failed"
# there, every time, regardless of code). Log the event immediately, then
# leave a screenshot request for session_agent.py - a separate process that
# runs in the competitor's own logon session, where screen capture actually
# works - to fulfill asynchronously.
#
# Event title/details are rendered here in the installation's configured
# language (settings table). A later language switch only affects new events;
# already-logged entries keep their wording, like any audit log.

def _lang() -> str:
    return i18n.normalize(db.get_setting("language", config.DEFAULT_LANGUAGE))


def log_event(event_type, severity, msg_key, event_key=None, screenshot=True, **args):
    lang = _lang()
    title = i18n.t(f"{msg_key}.title", lang, **args)
    details = i18n.t(f"{msg_key}.details", lang, **args)
    event_id = db.log_event(event_type, severity, title, details=details, event_key=event_key)
    if event_id and screenshot and config.SCREENSHOT_ON_DETECTION:
        db.request_screenshot(event_id)
    return event_id


# ── Re-detection windows ──────────────────────────────────────────────────────
# Every event_key is suffixed with a time bucket so the same app/domain/URL is
# logged once per REDETECT_AFTER window and then again in the next window -
# repeated use (even of one long-running session, after a gap) stays visible
# instead of collapsing into a single lifetime entry.

_REDETECT = max(60, int(getattr(config, "REDETECT_AFTER", 600)))

_logged_keys: set[str] = set()
_logged_lock = threading.Lock()


def _bucket(ts: float | None = None) -> int:
    return int((time.time() if ts is None else ts) // _REDETECT)


def _bkey(base: str, ts: float | None = None) -> str:
    return f"{base}#{_bucket(ts)}"


def _already_logged(key: str) -> bool:
    """In-memory fast path, then the DB (which is the source of truth and
    survives a service restart within the same window)."""
    with _logged_lock:
        if key in _logged_keys:
            return True
    if db.event_key_exists(key):
        with _logged_lock:
            _logged_keys.add(key)
        return True
    return False


def _mark_logged(key: str):
    with _logged_lock:
        _logged_keys.add(key)


def _domain_matches(haystack: str, domain: str) -> bool:
    """True if `domain` occurs in `haystack` (a hostname, URL or the DNS-cache
    dump) on a real label boundary - so "x.ai" matches "api.x.ai" but not
    "climax.airlines.com". A path-qualified entry ("bing.com/copilot") is a
    plain substring test."""
    haystack = haystack.lower()
    domain = domain.lower()
    if "/" in domain:
        return domain in haystack
    before_ok = ("", ".", "/", "@", ":", " ", "\t", "\n", "\r", "=", '"', "'", "(")
    after_ok  = ("", "/", ":", "?", "#", " ", "\t", "\n", "\r", ",", '"', "'", ")")
    i = 0
    while True:
        i = haystack.find(domain, i)
        if i == -1:
            return False
        before = haystack[i - 1] if i > 0 else ""
        j = i + len(domain)
        after = haystack[j] if j < len(haystack) else ""
        if before in before_ok and after in after_ok:
            return True
        i = j


def match_ai_domain(hostname: str) -> str | None:
    for domain in config.AI_DOMAINS:
        if _domain_matches(hostname, domain):
            return domain
    return None


# ── DNS resolver with cache ───────────────────────────────────────────────────

_dns_cache: dict[str, str] = {}
_dns_lock  = threading.Lock()


def resolve_ip(ip: str) -> str:
    with _dns_lock:
        if ip in _dns_cache:
            return _dns_cache[ip]
    try:
        hostname = socket.gethostbyaddr(ip)[0]
    except Exception:
        hostname = ip
    with _dns_lock:
        _dns_cache[ip] = hostname
    return hostname


# ── Network monitor ───────────────────────────────────────────────────────────

def _check_single_connection(conn_info):
    try:
        ip   = conn_info.raddr.ip
        port = conn_info.raddr.port

        hostname = resolve_ip(ip)
        matched  = match_ai_domain(hostname)
        if not matched:
            return

        key = _bkey(f"net_{matched}")
        if _already_logged(key):
            return

        proc_name = "?"
        try:
            if conn_info.pid:
                proc_name = psutil.Process(conn_info.pid).name()
        except Exception:
            pass

        eid = log_event(
            "network", "critical", "event.network", event_key=key,
            domain=matched, proc=proc_name, ip=ip, host=hostname, port=port,
        )
        if eid:
            _mark_logged(key)
            log(f"[NETWORK] AI connection detected -> {hostname} ({matched}) via {proc_name}")
    except Exception:
        pass


def monitor_network():
    log("Network monitor started")
    while True:
        try:
            conns = psutil.net_connections(kind="tcp")
            for c in conns:
                if c.status == "ESTABLISHED" and c.raddr and c.raddr.ip not in ("127.0.0.1", "::1"):
                    threading.Thread(
                        target=_check_single_connection,
                        args=(c,),
                        daemon=True
                    ).start()
        except Exception:
            pass
        time.sleep(config.NETWORK_CHECK_INTERVAL)


# ── Process monitor ───────────────────────────────────────────────────────────

def _proc_stems(name: str, exe: str) -> set[str]:
    """The identifiers an AI_PROCESSES entry is allowed to match against:
    the process name and the exe file name, each with and without extension.
    Deliberately NOT the full path - a substring test against the path flags
    every process of a user whose folder name happens to contain a rule
    (e.g. C:\\Users\\Jan)."""
    stems: set[str] = set()
    for raw in (name, Path(exe).name if exe else ""):
        raw = raw.lower().strip()
        if not raw:
            continue
        stems.add(raw)
        if raw.endswith(".exe"):
            stems.add(raw[:-4])
    return stems


def _match_ai_process(name: str, exe: str) -> str | None:
    stems = _proc_stems(name, exe)
    for ai_proc in config.AI_PROCESSES:
        if ai_proc.lower() in stems:
            return ai_proc
    return None


def _classify_process(name: str, exe: str, matched_rule: str) -> tuple[str, dict, str]:
    """Return (label_key, label_args, event_key_base) for a matched AI process.
    label_key indexes proclabel.* in i18n; label_args fills its placeholders."""
    exe_l = exe.lower()
    name_l = name.lower()

    # Claude desktop app vs Claude Code CLI
    if "claude" in name_l:
        if "claude-code" in exe_l or "anthropic-ai" in exe_l or "node_modules" in exe_l:
            return "claude_code", {}, "proc_claude_code_cli"
        if "windowsapps" in exe_l or "program files" in exe_l:
            return "claude_desktop", {}, "proc_claude_desktop"
        return "claude_generic", {"name": name}, f"proc_claude_{name_l}"

    # ChatGPT desktop
    if "chatgpt" in name_l or ("chatgpt" in exe_l):
        return "chatgpt", {}, "proc_chatgpt_desktop"

    # Cursor / Windsurf IDE
    if "cursor" in name_l or "cursor" in exe_l:
        return "cursor", {}, "proc_cursor"
    if "windsurf" in name_l or "windsurf" in exe_l:
        return "windsurf", {}, "proc_windsurf"

    # Generic: deduplicate by exe path bucket (strip version numbers)
    import hashlib
    path_key = hashlib.md5(exe_l.encode()).hexdigest()[:8]
    return "generic", {"name": name, "rule": matched_rule}, f"proc_{name_l}_{path_key}"


def monitor_processes():
    log("Process monitor started")
    while True:
        try:
            for proc in psutil.process_iter(["pid", "name", "exe"]):
                try:
                    name = (proc.info["name"] or "")
                    exe  = (proc.info["exe"]  or "")
                    pid  = proc.info["pid"]

                    ai_proc = _match_ai_process(name, exe)
                    if not ai_proc:
                        continue

                    label_key, label_args, app_base = _classify_process(name, exe, ai_proc)
                    key = _bkey(app_base)
                    if _already_logged(key):
                        continue

                    label = i18n.t(f"proclabel.{label_key}", _lang(), **label_args)
                    eid = log_event(
                        "process", "critical", "event.process", event_key=key,
                        label=label, path=exe or "unknown", pid=pid,
                    )
                    if eid:
                        _mark_logged(key)
                        log(f"[PROCESS] AI app detected: {label} (PID {pid})")
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
        except Exception:
            pass
        time.sleep(config.PROCESS_CHECK_INTERVAL)


# ── Browser history monitor ───────────────────────────────────────────────────

def _chrome_time_to_unix(chrome_ts: int) -> float:
    """Chrome stores microseconds since 1601-01-01."""
    return chrome_ts / 1_000_000 - 11_644_473_600


def _read_chromium_history(db_path: Path, browser: str, since_unix: float):
    tmp = Path(os.environ.get("TEMP", ".")) / f"_aim_{browser}_hist.db"
    try:
        shutil.copy2(str(db_path), str(tmp))
        conn = sqlite3.connect(str(tmp), timeout=5)
        cutoff = int((since_unix + 11_644_473_600) * 1_000_000)
        rows = conn.execute(
            "SELECT url, title, last_visit_time FROM urls WHERE last_visit_time > ? ORDER BY last_visit_time DESC",
            (cutoff,)
        ).fetchall()
        conn.close()
        # normalize the visit time to unix seconds, like the Firefox reader
        return [(url, title, _chrome_time_to_unix(ts)) for url, title, ts in rows if ts]
    except Exception:
        return []
    finally:
        try:
            tmp.unlink()
        except Exception:
            pass


def _read_firefox_history(db_path: Path, since_unix: float):
    tmp = Path(os.environ.get("TEMP", ".")) / "_aim_ff_hist.db"
    try:
        shutil.copy2(str(db_path), str(tmp))
        conn = sqlite3.connect(str(tmp), timeout=5)
        cutoff_us = int(since_unix * 1_000_000)
        rows = conn.execute(
            "SELECT url, title, last_visit_date FROM moz_places WHERE last_visit_date > ? ORDER BY last_visit_date DESC",
            (cutoff_us,)
        ).fetchall()
        conn.close()
        # normalize: firefox uses microseconds since unix epoch
        return [(url, title, ts / 1_000_000) for url, title, ts in rows if ts]
    except Exception:
        return []
    finally:
        try:
            tmp.unlink()
        except Exception:
            pass


def _check_browser_rows(rows, browser: str):
    import hashlib
    for row in rows:
        url   = row[0] or ""
        title = row[1] or ""
        visit = row[2] if len(row) > 2 and row[2] else None
        for domain in config.AI_DOMAINS:
            if not _domain_matches(url, domain):
                continue
            # Bucket by the actual visit time, not wall-clock, so each visit
            # episode is its own event even when the service saw it late.
            url_hash = hashlib.md5(url.encode("utf-8", "replace")).hexdigest()[:12]
            key = _bkey(f"browser_{domain}_{url_hash}", visit)
            if _already_logged(key):
                break

            eid = log_event(
                "browser", "critical", "event.browser", event_key=key,
                browser=browser, domain=domain, url=url[:300], title=title,
            )
            if eid:
                _mark_logged(key)
                log(f"[BROWSER] AI URL detected ({browser}): {url[:80]}")
            break


def _chromium_profile_histories(user_data_dir: Path) -> list[Path]:
    """Chromium browsers store each profile ("Default", "Profile 1", "Profile
    2", ...) in its own subfolder under User Data, each with its own History
    file. Only scanning "Default" misses everything if the browser's active
    profile is anything else - a very plausible setup on a competition PC."""
    if not user_data_dir.exists():
        return []
    paths = []
    for entry in user_data_dir.iterdir():
        if not entry.is_dir():
            continue
        if entry.name == "Default" or entry.name.startswith("Profile "):
            hist = entry / "History"
            if hist.exists():
                paths.append(hist)
    return paths


def _real_user_appdata_dirs() -> list[tuple[Path, Path]]:
    """The service runs as LocalSystem, whose own LOCALAPPDATA/APPDATA point
    at C:\\Windows\\System32\\config\\systemprofile - an empty profile that
    was never used to browse anything. The actual competitor's browser data
    lives under their own C:\\Users\\<name>\\AppData, which LocalSystem can
    still read (it isn't restricted the way a *different* standard user
    would be) - it just has to be found by walking C:\\Users directly instead
    of trusting environment variables, which only ever reflect the calling
    process' own account."""
    # Path("C:") / "Users" silently produces the drive-relative path "C:Users"
    # (resolves against the CWD on C:), not the absolute "C:\Users" - pathlib
    # only treats "C:\\" (with the separator) as the drive root.
    system_drive = os.environ.get("SystemDrive", "C:")
    users_root = Path(system_drive + "\\") / "Users"
    skip = {"public", "default", "default user", "all users"}
    dirs = []
    if not users_root.exists():
        return dirs
    for entry in users_root.iterdir():
        if not entry.is_dir() or entry.name.lower() in skip:
            continue
        local_appdata = entry / "AppData" / "Local"
        appdata = entry / "AppData" / "Roaming"
        if local_appdata.exists() or appdata.exists():
            dirs.append((local_appdata, appdata))
    return dirs


def monitor_browser():
    log("Browser history monitor started")

    while True:
        since = time.time() - config.BROWSER_CHECK_INTERVAL * 3

        for local, appdata in _real_user_appdata_dirs():
            chromium_roots = {
                "Chrome": local / "Google" / "Chrome" / "User Data",
                "Edge":   local / "Microsoft" / "Edge" / "User Data",
                "Brave":  local / "BraveSoftware" / "Brave-Browser" / "User Data",
            }
            for name, root in chromium_roots.items():
                for hist_path in _chromium_profile_histories(root):
                    rows = _read_chromium_history(hist_path, name, since)
                    _check_browser_rows(rows, name)

            opera_history = appdata / "Opera Software" / "Opera Stable" / "History"
            if opera_history.exists():
                rows = _read_chromium_history(opera_history, "Opera", since)
                _check_browser_rows(rows, "Opera")

            ff_profiles = appdata / "Mozilla" / "Firefox" / "Profiles"
            if ff_profiles.exists():
                for profile in ff_profiles.iterdir():
                    places = profile / "places.sqlite"
                    if places.exists():
                        rows = _read_firefox_history(places, since)
                        _check_browser_rows(rows, "Firefox")

        time.sleep(config.BROWSER_CHECK_INTERVAL)


# ── Clipboard monitor ─────────────────────────────────────────────────────────
# KNOWN LIMITATION: running as the real LocalSystem service, this executes in
# Session 0, which has no desktop/window station at all - Windows' clipboard
# is a per-desktop resource, so OpenClipboard() here can never see what the
# competitor (in their own interactive session) actually copies. It fails
# quietly (caught below, returns "") rather than erroring, so nothing breaks,
# but this monitor is effectively inert whenever running as the installed
# service. Same constraint applies to monitor_flutter_windows() below -
# EnumWindows() from Session 0 cannot enumerate another session's windows.
# A real fix needs a small companion process running IN the competitor's own
# logon session (e.g. a scheduled task triggered "at log on") that reports
# findings back to this service - out of scope for the current pass.

_last_clipboard = ""
_clipboard_lock = threading.Lock()

CF_UNICODETEXT = 13


def _read_clipboard() -> str:
    text = ""
    try:
        if ctypes.windll.user32.OpenClipboard(0):
            handle = ctypes.windll.user32.GetClipboardData(CF_UNICODETEXT)
            if handle:
                ptr = ctypes.windll.kernel32.GlobalLock(handle)
                if ptr:
                    text = ctypes.wstring_at(ptr)
                    ctypes.windll.kernel32.GlobalUnlock(handle)
            ctypes.windll.user32.CloseClipboard()
    except Exception:
        pass
    return text or ""


def monitor_clipboard():
    global _last_clipboard
    log("Clipboard monitor started")
    while True:
        try:
            text = _read_clipboard()
            if text and len(text) > 80:
                with _clipboard_lock:
                    if text == _last_clipboard:
                        time.sleep(config.CLIPBOARD_CHECK_INTERVAL)
                        continue
                    _last_clipboard = text

                text_lower = text.lower()
                matched_pattern = None
                for pattern in config.AI_CLIPBOARD_PATTERNS:
                    if pattern.lower() in text_lower:
                        matched_pattern = pattern
                        break

                if matched_pattern:
                    import hashlib
                    text_hash = hashlib.md5(text[:200].encode("utf-8", "replace")).hexdigest()[:12]
                    key = _bkey(f"clip_{text_hash}")
                    if not _already_logged(key):
                        excerpt = text[:400].replace("\n", " ")
                        eid = log_event(
                            "clipboard", "warning", "event.clipboard",
                            event_key=key, screenshot=False,
                            pattern=matched_pattern, excerpt=excerpt,
                        )
                        if eid:
                            _mark_logged(key)
                            log(f"[CLIPBOARD] Suspicious text detected (pattern: {matched_pattern})")
        except Exception:
            pass
        time.sleep(config.CLIPBOARD_CHECK_INTERVAL)


# ── DNS Cache monitor ─────────────────────────────────────────────────────────
# Reads the Windows DNS resolver cache via ipconfig /displaydns.
# This catches desktop apps (Claude, ChatGPT, …) that connect through CDN IPs
# which don't reverse-resolve to their real hostname.

def monitor_dns_cache():
    log("DNS cache monitor started")
    import subprocess
    while True:
        try:
            result = subprocess.run(
                ["ipconfig", "/displaydns"],
                capture_output=True, timeout=10,
                creationflags=0x08000000  # CREATE_NO_WINDOW
            )
            # ipconfig writes to the console using the OEM codepage (e.g. cp850 on
            # German Windows), not the ANSI codepage — decoding with text=True
            # (which uses locale.getpreferredencoding()/cp1252) crashes on bytes
            # outside that codepage. Decode leniently instead.
            output = result.stdout.decode("cp850", errors="replace").lower()

            for domain in config.AI_DOMAINS:
                if not _domain_matches(output, domain):
                    continue

                key = _bkey(f"dns_{domain.lower()}")
                if _already_logged(key):
                    continue

                # Try to find which process owns connections to this domain
                proc_name = _find_proc_for_domain(domain)
                eid = log_event(
                    "network", "critical", "event.dns", event_key=key,
                    domain=domain, proc=proc_name,
                )
                if eid:
                    _mark_logged(key)
                    log(f"[DNS] AI domain detected: {domain} (process: {proc_name})")
        except Exception:
            pass
        time.sleep(15)


def _find_proc_for_domain(domain: str) -> str:
    """Best-effort: find a process name connected to the given domain."""
    try:
        ip = socket.gethostbyname(domain)
    except Exception:
        return "unknown"
    try:
        for conn in psutil.net_connections(kind="tcp"):
            if conn.raddr and conn.raddr.ip == ip and conn.pid:
                try:
                    return psutil.Process(conn.pid).name()
                except Exception:
                    pass
    except Exception:
        pass
    return "unknown"


# ── Flutter / unknown-exe window monitor ──────────────────────────────────────
# Self-built apps (e.g. compiled with Flutter) often ship under a generic
# executable name that never appears in AI_PROCESSES, so name-based process
# matching misses them. Flutter's Win32 window class is fixed, so we instead
# scan top-level window titles for AI-related keywords regardless of exe name.

FLUTTER_WINDOW_CLASS = "FLUTTER_RUNNER_WIN32_WINDOW"


def _enum_top_level_windows() -> list[int]:
    user32 = ctypes.windll.user32
    hwnds: list[int] = []

    @ctypes.WINFUNCTYPE(ctypes.wintypes.BOOL, ctypes.wintypes.HWND, ctypes.wintypes.LPARAM)
    def _callback(hwnd, _lparam):
        if user32.IsWindowVisible(hwnd):
            hwnds.append(hwnd)
        return True

    user32.EnumWindows(_callback, 0)
    return hwnds


def _get_window_class(hwnd) -> str:
    buf = ctypes.create_unicode_buffer(256)
    ctypes.windll.user32.GetClassNameW(hwnd, buf, 256)
    return buf.value


def _get_window_title(hwnd) -> str:
    length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
    if length == 0:
        return ""
    buf = ctypes.create_unicode_buffer(length + 1)
    ctypes.windll.user32.GetWindowTextW(hwnd, buf, length + 1)
    return buf.value


def monitor_flutter_windows():
    log("Flutter window monitor started")
    while True:
        try:
            for hwnd in _enum_top_level_windows():
                try:
                    if _get_window_class(hwnd) != FLUTTER_WINDOW_CLASS:
                        continue

                    title = _get_window_title(hwnd)
                    title_l = title.lower()
                    matched = next(
                        (kw for kw in config.AI_WINDOW_KEYWORDS if kw in title_l), None
                    )
                    if not matched:
                        continue

                    pid = ctypes.wintypes.DWORD()
                    ctypes.windll.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
                    exe = "unknown"
                    try:
                        exe = psutil.Process(pid.value).exe()
                    except Exception:
                        pass

                    key = _bkey(f"flutter_{title_l[:40]}")
                    if _already_logged(key):
                        continue

                    eid = log_event(
                        "process", "critical", "event.flutter", event_key=key,
                        title=title, path=exe, pid=pid.value, rule=matched,
                    )
                    if eid:
                        _mark_logged(key)
                        log(f"[WINDOW] AI app detected: {title} (PID {pid.value})")
                except Exception:
                    pass
        except Exception:
            pass
        time.sleep(config.PROCESS_CHECK_INTERVAL)


# ── Main ──────────────────────────────────────────────────────────────────────

def main(stop_event: threading.Event | None = None):
    """Run all monitor threads until interrupted (CLI) or stop_event is set (service)."""
    db.init_db()
    session_id = db.start_session()
    log(f"AI-Monitor started (session {session_id})")
    log(f"Database: {Path(config.DB_PATH).resolve()}")

    threads = [
        threading.Thread(target=monitor_network,   daemon=True, name="net"),
        threading.Thread(target=monitor_dns_cache, daemon=True, name="dns"),
        threading.Thread(target=monitor_processes, daemon=True, name="proc"),
        threading.Thread(target=monitor_flutter_windows, daemon=True, name="flutter"),
        threading.Thread(target=monitor_browser,   daemon=True, name="browser"),
        threading.Thread(target=monitor_clipboard, daemon=True, name="clip"),
    ]
    for t in threads:
        t.start()

    try:
        while not (stop_event is not None and stop_event.is_set()):
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        log("Monitor stopped.")
        db.end_session(session_id)


if __name__ == "__main__":
    main()
