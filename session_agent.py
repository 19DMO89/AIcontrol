"""
AI-Monitor session agent

Runs in the session of the logged-in user (not as SYSTEM). Two jobs that are
only possible from inside the interactive session:

  1. Screenshots. The main service (monitor_service.py) runs as LocalSystem in
     Session 0, which has no desktop and therefore cannot take a screenshot (a
     Windows security boundary, not a bug). This agent fulfils the screenshot
     requests the service leaves in the shared database.

  2. Clipboard. The clipboard is a per-desktop resource - Session 0 never sees
     what the competitor copies. This agent reads the clipboard and logs an
     entry when the text looks AI-generated (scoring in aitext.py).

Started automatically at every logon via Task Scheduler (see
Install-AIMonitor.ps1) - a standard user cannot delete/disable the task
definition itself (it lives in an admin-protected system folder), even though
they can end the running process in Task Manager. Task Scheduler then starts
it again at the next logon anyway.
"""

import ctypes
import ctypes.wintypes
import hashlib
import time
from datetime import datetime
from pathlib import Path

import aitext
import config
import database as db
import i18n

POLL_INTERVAL = 1.5
# Requests left unanswered longer than this (e.g. because the screen was
# locked) are abandoned rather than retried forever.
MAX_REQUEST_AGE_SECONDS = 120

CF_UNICODETEXT = 13

# ── Win32 clipboard bindings ────────────────────────────────────────────────
# restype/argtypes MUST be declared: HANDLE/pointer return values default to
# a 32-bit C int in ctypes, which truncates the pointer on 64-bit Windows -
# GlobalLock then dereferences garbage and wstring_at raises, and if that
# happens between OpenClipboard and CloseClipboard the clipboard is left
# locked for every other application (the v3.2.0 "can't copy anymore" bug).
_u32 = ctypes.windll.user32
_k32 = ctypes.windll.kernel32
_u32.OpenClipboard.argtypes = [ctypes.wintypes.HWND]
_u32.OpenClipboard.restype = ctypes.wintypes.BOOL
_u32.CloseClipboard.restype = ctypes.wintypes.BOOL
_u32.IsClipboardFormatAvailable.argtypes = [ctypes.wintypes.UINT]
_u32.IsClipboardFormatAvailable.restype = ctypes.wintypes.BOOL
_u32.GetClipboardData.argtypes = [ctypes.wintypes.UINT]
_u32.GetClipboardData.restype = ctypes.wintypes.HANDLE
_u32.GetClipboardSequenceNumber.restype = ctypes.wintypes.DWORD
_u32.GetClipboardSequenceNumber.argtypes = []
_k32.GlobalLock.argtypes = [ctypes.wintypes.HANDLE]
_k32.GlobalLock.restype = ctypes.c_void_p
_k32.GlobalUnlock.argtypes = [ctypes.wintypes.HANDLE]
_k32.CreateMutexW.restype = ctypes.wintypes.HANDLE
_k32.GetLastError.restype = ctypes.wintypes.DWORD


# ── Screenshots ─────────────────────────────────────────────────────────────

def _take_screenshot() -> str | None:
    try:
        from PIL import ImageGrab
        d = Path(config.SCREENSHOT_DIR)
        d.mkdir(parents=True, exist_ok=True)
        fname = d / f"shot_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}.png"
        ImageGrab.grab(all_screens=True).save(str(fname))
        return str(fname)
    except Exception:
        return None


def _service_screenshot_requests():
    for req_id, event_id, requested_at in db.get_pending_screenshot_requests():
        try:
            age = (datetime.now() - datetime.fromisoformat(requested_at)).total_seconds()
        except Exception:
            age = 0

        if age > MAX_REQUEST_AGE_SECONDS:
            db.fulfill_screenshot_request(req_id, event_id, None)
            continue

        shot = _take_screenshot()
        if shot:
            db.fulfill_screenshot_request(req_id, event_id, shot)
        # else: leave unfulfilled, retried on the next poll until it ages out


# ── Clipboard ───────────────────────────────────────────────────────────────

def _read_clipboard() -> str:
    """Read CF_UNICODETEXT. CloseClipboard is guaranteed via `finally` - the
    v3.2.0 bug was an exception between OpenClipboard and CloseClipboard
    leaving the clipboard locked for every other app."""
    if not _u32.IsClipboardFormatAvailable(CF_UNICODETEXT):
        return ""
    # OpenClipboard returns 0 if another process holds it right now - don't
    # block, don't retry, just skip this round.
    if not _u32.OpenClipboard(None):
        return ""
    text = ""
    try:
        handle = _u32.GetClipboardData(CF_UNICODETEXT)
        if handle:
            ptr = _k32.GlobalLock(handle)
            if ptr:
                try:
                    text = ctypes.wstring_at(ptr)
                finally:
                    _k32.GlobalUnlock(handle)
    except Exception:
        text = ""
    finally:
        _u32.CloseClipboard()
    return text or ""


_last_clipboard = ""
_last_clip_seq = None


def _clipboard_changed() -> bool:
    """True only when the clipboard's contents actually changed since the last
    check - avoids opening the clipboard at all on every poll, which is what
    caused contention with other apps."""
    global _last_clip_seq
    try:
        seq = _u32.GetClipboardSequenceNumber()
    except Exception:
        return True
    if seq == _last_clip_seq:
        return False
    _last_clip_seq = seq
    return True


def _lang() -> str:
    return i18n.normalize(db.get_setting("language", config.DEFAULT_LANGUAGE))


def _check_clipboard():
    global _last_clipboard
    if not _clipboard_changed():
        return
    text = _read_clipboard()
    if not text or len(text) < config.CLIPBOARD_MIN_CHARS:
        return
    if text == _last_clipboard:
        return
    _last_clipboard = text

    is_ai, score, reasons = aitext.analyse(text)
    if not is_ai:
        return

    # One entry per copied text per re-detect window.
    text_hash = hashlib.md5(text[:200].encode("utf-8", "replace")).hexdigest()[:12]
    bucket = int(time.time() // max(60, config.REDETECT_AFTER))
    key = f"clip_{text_hash}#{bucket}"
    if db.event_key_exists(key):
        return

    lang = _lang()
    signals = "; ".join(reasons) if reasons else f"score {score}"
    excerpt = text[:400].replace("\r", " ").replace("\n", " ")
    title = i18n.t("event.clipboard.title", lang)
    details = i18n.t("event.clipboard.details", lang, signals=signals, excerpt=excerpt)
    db.log_event("clipboard", "warning", title, details=details, event_key=key)


# ── Main loop ───────────────────────────────────────────────────────────────

_singleton_handle = None


def _acquire_singleton() -> bool:
    """False if another AISessionAgent is already running in this session.
    Two agents both polling the clipboard multiply the contention that broke
    copy/paste - only one may run."""
    global _singleton_handle
    try:
        ERROR_ALREADY_EXISTS = 183
        _k32.SetLastError(0)
        _singleton_handle = _k32.CreateMutexW(None, False, "Local\\AIMonitorSessionAgent")
        return _k32.GetLastError() != ERROR_ALREADY_EXISTS
    except Exception:
        return True


def main():
    if not _acquire_singleton():
        return
    db.init_db()
    last_clip_check = 0.0
    while True:
        try:
            _service_screenshot_requests()
        except Exception:
            pass

        now = time.time()
        if now - last_clip_check >= config.CLIPBOARD_CHECK_INTERVAL:
            last_clip_check = now
            try:
                _check_clipboard()
            except Exception:
                pass

        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    main()
