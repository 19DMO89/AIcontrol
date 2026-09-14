"""
Tamper-evidence canary.

The database and screenshots live entirely under
C:\\ProgramData\\AIMonitor\\data - a local administrator can stop the
service, delete that folder and restart it; the app then just looks like a
fresh install (see database.init_db / viewer.has_credentials). That is not
fixable from inside the data folder itself, so this module mirrors a minimal
trace of activity to two places outside it that a folder delete does not
touch:

  1. The registry (HKLM\\SOFTWARE\\AIMonitor) - by default writable only by
     administrators, same as the data folder, but a separate delete target.
  2. The Windows "Application" event log, under the "AIMonitor" source the
     service already registers with the SCM. Clearing that log leaves its
     own event (ID 104, "the log file was cleared") naming the account that
     did it - a much less obvious thing to think to do than deleting a data
     folder, and self-incriminating if done.

Every write here is best-effort: a failure must never take the monitor
thread down with it, so every function swallows its own exceptions.
"""

import winreg
from datetime import datetime

_REG_PATH = r"SOFTWARE\AIMonitor"
_EVT_SOURCE = "AIMonitor"
_EVT_ID = 1000


def _reg_write(values: dict):
    try:
        key = winreg.CreateKeyEx(winreg.HKEY_LOCAL_MACHINE, _REG_PATH, 0, winreg.KEY_SET_VALUE)
        for name, value in values.items():
            winreg.SetValueEx(key, name, 0, winreg.REG_SZ, str(value))
        winreg.CloseKey(key)
    except Exception:
        pass


def _reg_read() -> dict:
    out = {}
    try:
        key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, _REG_PATH, 0, winreg.KEY_READ)
        i = 0
        while True:
            try:
                name, value, _ = winreg.EnumValue(key, i)
            except OSError:
                break
            out[name] = value
            i += 1
        winreg.CloseKey(key)
    except Exception:
        pass
    return out


def _event_log(message: str):
    try:
        import win32evtlog
        import win32evtlogutil
        win32evtlogutil.ReportEvent(
            _EVT_SOURCE, _EVT_ID, eventCategory=0,
            eventType=win32evtlog.EVENTLOG_INFORMATION_TYPE,
            strings=[message],
        )
    except Exception:
        pass


def record_install_if_new(total_events: int):
    """Call once at service startup. Writes InstallTime only the very first
    time (no InstallTime yet in the registry) - a later restart must not
    reset it, or a wipe-and-reinstall would erase this trace too."""
    if "InstallTime" in _reg_read():
        return
    now = datetime.now().isoformat(sep=' ', timespec='seconds')
    _reg_write({"InstallTime": now, "EventCount": total_events, "LastHeartbeat": now})
    _event_log(f"AI-Monitor started. {total_events} event(s) already on record.")


def heartbeat(total_events: int, last_event_time: str | None):
    """Call periodically from the monitor loop. Refreshes the canary so its
    last-seen counter/timestamp stays close to the database's real state."""
    now = datetime.now().isoformat(sep=' ', timespec='seconds')
    _reg_write({
        "EventCount": total_events,
        "LastHeartbeat": now,
        "LastEventTime": last_event_time or "",
    })
    suffix = f", most recent at {last_event_time}" if last_event_time else ""
    _event_log(f"AI-Monitor heartbeat: {total_events} event(s) logged so far{suffix}.")


def check_for_wipe() -> dict | None:
    """Call from the dashboard when it is about to show first-run setup
    (no credentials in the database). Returns the last known canary state if
    it shows prior activity that the now-empty database no longer has - a
    sign the data folder was wiped - otherwise None (a genuine first
    install, nothing to flag)."""
    state = _reg_read()
    try:
        if int(state.get("EventCount", 0)) > 0:
            return state
    except (TypeError, ValueError):
        pass
    return None
