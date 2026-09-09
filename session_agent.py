"""
AI-Monitor session agent

Runs in the session of the logged-in user (not as SYSTEM) - the main service
(monitor_service.py) runs as LocalSystem in Session 0, which has no desktop
and therefore cannot technically take a screenshot (a Windows security
boundary, not a bug). This agent does exactly that: it waits for screenshot
requests from the service (via the shared database) and fulfils them from
the session, where a real desktop exists.

Started automatically at every logon via Task Scheduler (see
Install-AIMonitor.ps1) - a standard user cannot delete/disable the task
definition itself (it lives in an admin-protected system folder), even
though they can end the running process in Task Manager. Task Scheduler then
starts it again at the next logon anyway.
"""

import time
from datetime import datetime
from pathlib import Path

import config
import database as db

POLL_INTERVAL = 1.5
# Requests left unanswered longer than this (e.g. because the screen was
# locked) are abandoned rather than retried forever.
MAX_REQUEST_AGE_SECONDS = 120


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


def main():
    db.init_db()
    while True:
        try:
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
                # else: leave unfulfilled, retried on the next poll until MAX_REQUEST_AGE_SECONDS
        except Exception:
            pass
        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    main()
