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


_last_clipboard = ""


def _lang() -> str:
    return i18n.normalize(db.get_setting("language", config.DEFAULT_LANGUAGE))


def _check_clipboard():
    global _last_clipboard
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

def main():
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
