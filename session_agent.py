"""
AI-Monitor Sitzungs-Agent

Laeuft in der Sitzung des angemeldeten Benutzers (nicht als SYSTEM) - der
Hauptdienst (monitor_service.py) laeuft als LocalSystem in Session 0, die
keinen Desktop hat, und kann deshalb technisch keinen Screenshot machen
(Windows-Sicherheitsgrenze, kein Bug). Dieser Agent erledigt genau das:
er wartet auf Screenshot-Anfragen des Dienstes (ueber die gemeinsame
Datenbank) und erfuellt sie aus der Sitzung heraus, wo ein echter Desktop
existiert.

Wird per Aufgabenplanung bei jeder Anmeldung automatisch gestartet (siehe
Install-AIMonitor.ps1) - die Aufgabendefinition selbst kann ein
Standardbenutzer nicht loeschen/deaktivieren (liegt in einem admin-
geschuetzten Systemordner), auch wenn er den laufenden Prozess im
Taskmanager beenden kann. Die Aufgabenplanung startet ihn dann bei der
naechsten Anmeldung ohnehin wieder.
"""

import time
from datetime import datetime
from pathlib import Path

import config
import database as db

POLL_INTERVAL = 1.5
# Anfragen, die laenger als das hier unbeantwortet sind (z.B. weil der
# Bildschirm gesperrt war), werden aufgegeben statt endlos neu versucht.
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
