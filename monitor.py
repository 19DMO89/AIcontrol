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

# ── Logging ──────────────────────────────────────────────────────────────────

def log(msg):
    ts = datetime.now().strftime("%H:%M:%S")
    try:
        print(f"[{ts}] {msg}", flush=True)
    except Exception:
        pass


# ── Screenshot helper ─────────────────────────────────────────────────────────

def take_screenshot() -> str | None:
    if not config.SCREENSHOT_ON_DETECTION:
        return None
    try:
        from PIL import ImageGrab
        d = Path(config.SCREENSHOT_DIR)
        d.mkdir(parents=True, exist_ok=True)
        fname = d / f"shot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        # all_screens=True captures all connected monitors as one combined image
        ImageGrab.grab(all_screens=True).save(str(fname))
        return str(fname)
    except Exception:
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


def match_ai_domain(hostname: str) -> str | None:
    hl = hostname.lower()
    for domain in config.AI_DOMAINS:
        dl = domain.lower()
        if dl in hl or hl.endswith("." + dl) or hl == dl:
            return domain
    return None


# ── Network monitor ───────────────────────────────────────────────────────────

_seen_connections: set[tuple] = set()
_seen_lock = threading.Lock()


def _check_single_connection(conn_info):
    try:
        ip   = conn_info.raddr.ip
        port = conn_info.raddr.port
        key  = (ip, port)

        with _seen_lock:
            if key in _seen_connections:
                return
            _seen_connections.add(key)

        hostname = resolve_ip(ip)
        matched  = match_ai_domain(hostname)
        if not matched:
            return

        proc_name = "?"
        try:
            if conn_info.pid:
                proc_name = psutil.Process(conn_info.pid).name()
        except Exception:
            pass

        shot = take_screenshot()
        db.log_event(
            event_type="network",
            severity="critical",
            title=f"KI-Verbindung: {matched}",
            details=f"Prozess: {proc_name}  |  IP: {ip}  |  Host: {hostname}  |  Port: {port}",
            screenshot_path=shot,
            event_key=f"net_{ip}_{port}",
        )
        log(f"[NETZWERK] KI-Verbindung erkannt → {hostname} ({matched}) via {proc_name}")
    except Exception:
        pass


def monitor_network():
    log("Netzwerk-Monitor gestartet")
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

_seen_pids: set[int] = set()
_pid_lock  = threading.Lock()


def _classify_process(name: str, exe: str, matched_rule: str) -> tuple[str, str]:
    """Return (human_label, unique_event_key) for a matched AI process."""
    exe_l = exe.lower()
    name_l = name.lower()

    # Claude Desktop App vs Claude Code CLI
    if "claude" in name_l:
        if "claude-code" in exe_l or "anthropic-ai" in exe_l or "node_modules" in exe_l:
            return "Claude Code CLI (KI-Coding-Assistent)", "proc_claude_code_cli"
        if "windowsapps" in exe_l or "program files" in exe_l:
            return "Claude Desktop App", "proc_claude_desktop"
        return f"Claude ({name})", f"proc_claude_{name_l}"

    # ChatGPT Desktop
    if "chatgpt" in name_l or ("chatgpt" in exe_l):
        return "ChatGPT Desktop App", "proc_chatgpt_desktop"

    # Cursor / Windsurf IDE
    if "cursor" in name_l or "cursor" in exe_l:
        return "Cursor KI-IDE", "proc_cursor"
    if "windsurf" in name_l or "windsurf" in exe_l:
        return "Windsurf KI-IDE", "proc_windsurf"

    # Generic: deduplicate by exe path bucket (strip version numbers)
    import hashlib
    path_key = hashlib.md5(exe_l.encode()).hexdigest()[:8]
    return f"{name} (Regel: {matched_rule})", f"proc_{name_l}_{path_key}"


def monitor_processes():
    log("Prozess-Monitor gestartet")
    while True:
        try:
            for proc in psutil.process_iter(["pid", "name", "exe"]):
                try:
                    name = (proc.info["name"] or "").lower()
                    exe  = (proc.info["exe"]  or "").lower()
                    pid  = proc.info["pid"]

                    with _pid_lock:
                        if pid in _seen_pids:
                            continue

                    for ai_proc in config.AI_PROCESSES:
                        if ai_proc.lower() in name or ai_proc.lower() in exe:
                            with _pid_lock:
                                if pid in _seen_pids:
                                    break
                                _seen_pids.add(pid)

                            # Build descriptive label and unique key based on exe path
                            label, app_key = _classify_process(proc.info["name"], exe, ai_proc)

                            if db.event_key_exists(app_key):
                                break

                            shot = take_screenshot()
                            db.log_event(
                                event_type="process",
                                severity="critical",
                                title=f"KI-Programm erkannt: {label}",
                                details=f"Pfad: {proc.info['exe'] or 'unbekannt'}\nPID: {pid}",
                                screenshot_path=shot,
                                event_key=app_key,
                            )
                            log(f"[PROZESS] KI-App erkannt: {label} (PID {pid})")
                            break
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
        return rows
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


# Track already-logged browser URLs
_seen_browser_keys: set[str] = set()
_browser_lock = threading.Lock()


def _check_browser_rows(rows, browser: str, time_converter=None):
    for row in rows:
        url   = row[0] or ""
        title = row[1] or ""
        for domain in config.AI_DOMAINS:
            if domain.lower() in url.lower():
                key = f"browser_{url}"
                with _browser_lock:
                    if key in _seen_browser_keys:
                        break
                    _seen_browser_keys.add(key)
                if db.event_key_exists(key):
                    break

                shot = take_screenshot()
                db.log_event(
                    event_type="browser",
                    severity="critical",
                    title=f"KI-Webseite geöffnet ({browser}): {domain}",
                    details=f"URL: {url[:300]}\nTitel: {title}",
                    screenshot_path=shot,
                    event_key=key,
                )
                log(f"[BROWSER] KI-URL erkannt ({browser}): {url[:80]}")
                break


def monitor_browser():
    log("Browser-Monitor gestartet")
    local  = Path(os.environ.get("LOCALAPPDATA", ""))
    appdata = Path(os.environ.get("APPDATA", ""))

    browsers = {
        "Chrome": local / "Google" / "Chrome" / "User Data" / "Default" / "History",
        "Edge":   local / "Microsoft" / "Edge" / "User Data" / "Default" / "History",
        "Brave":  local / "BraveSoftware" / "Brave-Browser" / "User Data" / "Default" / "History",
        "Opera":  appdata / "Opera Software" / "Opera Stable" / "History",
    }

    while True:
        since = time.time() - config.BROWSER_CHECK_INTERVAL * 3
        for name, path in browsers.items():
            if path.exists():
                rows = _read_chromium_history(path, name, since)
                _check_browser_rows(rows, name)

        # Firefox
        ff_profiles = appdata / "Mozilla" / "Firefox" / "Profiles"
        if ff_profiles.exists():
            for profile in ff_profiles.iterdir():
                places = profile / "places.sqlite"
                if places.exists():
                    rows = _read_firefox_history(places, since)
                    _check_browser_rows(rows, "Firefox")

        time.sleep(config.BROWSER_CHECK_INTERVAL)


# ── Clipboard monitor ─────────────────────────────────────────────────────────

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
    log("Zwischenablage-Monitor gestartet")
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
                    key = f"clip_{hash(text[:200])}"
                    if not db.event_key_exists(key):
                        excerpt = text[:400].replace("\n", " ")
                        db.log_event(
                            event_type="clipboard",
                            severity="warning",
                            title="KI-typischer Text in Zwischenablage",
                            details=f'Muster: "{matched_pattern}"\n\nAuszug: {excerpt}…',
                            event_key=key,
                        )
                        log(f"[CLIPBOARD] Verdächtiger Text erkannt (Muster: {matched_pattern})")
        except Exception:
            pass
        time.sleep(config.CLIPBOARD_CHECK_INTERVAL)


# ── DNS Cache monitor ─────────────────────────────────────────────────────────
# Reads the Windows DNS resolver cache via ipconfig /displaydns.
# This catches desktop apps (Claude, ChatGPT, …) that connect through CDN IPs
# which don't reverse-resolve to their real hostname.

_seen_dns_domains: set[str] = set()
_dns_mon_lock = threading.Lock()


def monitor_dns_cache():
    log("DNS-Cache-Monitor gestartet")
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
                dl = domain.lower()
                if dl not in output:
                    continue

                with _dns_mon_lock:
                    if dl in _seen_dns_domains:
                        continue
                    _seen_dns_domains.add(dl)

                key = f"dns_{dl}"
                if db.event_key_exists(key):
                    continue

                # Try to find which process owns connections to this domain
                proc_name = _find_proc_for_domain(domain)
                shot = take_screenshot()
                db.log_event(
                    event_type="network",
                    severity="critical",
                    title=f"KI-Dienst im DNS-Cache: {domain}",
                    details=f"Domain im Windows DNS-Cache gefunden — Verbindung wurde hergestellt.\nProzess: {proc_name}",
                    screenshot_path=shot,
                    event_key=key,
                )
                log(f"[DNS] KI-Domain erkannt: {domain} (Prozess: {proc_name})")
        except Exception:
            pass
        time.sleep(15)


def _find_proc_for_domain(domain: str) -> str:
    """Best-effort: find a process name connected to the given domain."""
    try:
        ip = socket.gethostbyname(domain)
    except Exception:
        return "unbekannt"
    try:
        for conn in psutil.net_connections(kind="tcp"):
            if conn.raddr and conn.raddr.ip == ip and conn.pid:
                try:
                    return psutil.Process(conn.pid).name()
                except Exception:
                    pass
    except Exception:
        pass
    return "unbekannt"


# ── Flutter / unknown-exe window monitor ──────────────────────────────────────
# Self-built apps (e.g. compiled with Flutter) often ship under a generic
# executable name that never appears in AI_PROCESSES, so name-based process
# matching misses them. Flutter's Win32 window class is fixed, so we instead
# scan top-level window titles for AI-related keywords regardless of exe name.

FLUTTER_WINDOW_CLASS = "FLUTTER_RUNNER_WIN32_WINDOW"

_seen_flutter_hwnds: set[int] = set()
_flutter_lock = threading.Lock()


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
    log("Flutter-Fenster-Monitor gestartet")
    while True:
        try:
            for hwnd in _enum_top_level_windows():
                with _flutter_lock:
                    if hwnd in _seen_flutter_hwnds:
                        continue
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

                    with _flutter_lock:
                        _seen_flutter_hwnds.add(hwnd)

                    pid = ctypes.wintypes.DWORD()
                    ctypes.windll.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
                    exe = "unbekannt"
                    try:
                        exe = psutil.Process(pid.value).exe()
                    except Exception:
                        pass

                    key = f"flutter_{pid.value}_{title_l[:40]}"
                    if db.event_key_exists(key):
                        continue

                    shot = take_screenshot()
                    db.log_event(
                        event_type="process",
                        severity="critical",
                        title=f"KI-Programm erkannt (eigenständige App): {title}",
                        details=f"Fenstertitel: {title}\nPfad: {exe}\nPID: {pid.value}\nErkannt via Fenstertitel (Regel: {matched})",
                        screenshot_path=shot,
                        event_key=key,
                    )
                    log(f"[FENSTER] KI-App erkannt: {title} (PID {pid.value})")
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
    log(f"AI-Monitor gestartet (Session {session_id})")
    log(f"Datenbank: {Path(config.DB_PATH).resolve()}")

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
        log("Monitor gestoppt.")
        db.end_session(session_id)


if __name__ == "__main__":
    main()
