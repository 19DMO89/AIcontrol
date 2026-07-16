"""
AI-Monitor Windows-Dienst

Laeuft als "AIMonitor"-Dienst unter dem LocalSystem-Konto. Ein Dienst kann von
einem Standardbenutzer (ohne Administratorrechte) weder gestoppt noch entfernt
werden - das ist Standard-Windows-Verhalten fuer den Service Control Manager
und der eigentliche Manipulationsschutz, nicht irgendein Trick in diesem Code.

Manuelle Verwaltung (nur zu Testzwecken, normalerweise macht Install-AIMonitor.ps1 das):
    AIMonitorService.exe install
    AIMonitorService.exe start
    net stop AIMonitor      (erfordert Administratorrechte)
    AIMonitorService.exe remove
"""

import os
import sys
import traceback

_CRASH_LOG = r"C:\ProgramData\AIMonitor\data\service_crash.log"


def _log_crash(where, exc=None):
    try:
        os.makedirs(os.path.dirname(_CRASH_LOG), exist_ok=True)
        with open(_CRASH_LOG, "a", encoding="utf-8") as f:
            f.write(f"\n=== {where} ===\n")
            traceback.print_exc(file=f)
    except Exception:
        pass


# Built with --windowed (see build.ps1): a real service start happens in
# Session 0, which has no console at all, and the --console bootloader
# variant tried to allocate/attach one there anyway - dying before Python
# (and even our own exception logging) ever ran. sys.stdout/stderr are None
# unconditionally in a --windowed build, in every context.
#
# The tradeoff: pywin32's own CLI verbs (install/remove/start/debug) print()
# their status, which crashes outright against a None stdout. Those verbs are
# only ever invoked interactively (a real console exists, e.g. Install-
# AIMonitor.ps1's caller) - never by the SCM, which launches with zero
# arguments. So: attach the caller's console for the CLI-verb case only,
# same trick viewer.py uses for --set-credentials; leave the true service
# launch (no args) alone with stdout/stderr redirected to devnull.
try:
    if len(sys.argv) > 1:
        import ctypes
        ATTACH_PARENT_PROCESS = 0xFFFFFFFF
        kernel32 = ctypes.windll.kernel32
        if not kernel32.AttachConsole(ATTACH_PARENT_PROCESS):
            kernel32.AllocConsole()
        sys.stdout = open("CONOUT$", "w")
        sys.stderr = open("CONOUT$", "w")
        sys.stdin = open("CONIN$", "r")
    else:
        if sys.stdout is None:
            sys.stdout = open(os.devnull, "w")
        if sys.stderr is None:
            sys.stderr = open(os.devnull, "w")
except Exception:
    _log_crash("console attach/redirect")
    if sys.stdout is None:
        sys.stdout = open(os.devnull, "w")
    if sys.stderr is None:
        sys.stderr = open(os.devnull, "w")

import threading

try:
    import servicemanager
    import win32event
    import win32service
    import win32serviceutil
except Exception as e:
    _log_crash("import pywin32 modules", e)
    raise

try:
    import monitor
except Exception as e:
    _log_crash("import monitor", e)
    raise


class AIMonitorService(win32serviceutil.ServiceFramework):
    _svc_name_ = "AIMonitor"
    _svc_display_name_ = "AI-Monitor (Berufsweltmeisterschaften)"
    _svc_description_ = (
        "Ueberwacht Netzwerk-, Prozess-, Browser- und Zwischenablage-Aktivitaet "
        "auf KI-Nutzung waehrend der Berufsweltmeisterschaften."
    )

    def __init__(self, args):
        try:
            super().__init__(args)
            self._wait_event = win32event.CreateEvent(None, 0, 0, None)
            self._stop_flag = threading.Event()
        except Exception as e:
            _log_crash("__init__", e)
            raise

    def SvcStop(self):
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        self._stop_flag.set()
        win32event.SetEvent(self._wait_event)

    def SvcDoRun(self):
        try:
            # Muss VOR der (blockierenden) Monitor-Schleife gemeldet werden - sonst
            # wartet der Service Control Manager bis zum Timeout (60s) auf eine
            # Statusmeldung, die nie kommt, und der Dienststart schlaegt fehl
            # (Ereignis 7009), obwohl der Code an sich einwandfrei laeuft.
            self.ReportServiceStatus(win32service.SERVICE_RUNNING)
            servicemanager.LogMsg(
                servicemanager.EVENTLOG_INFORMATION_TYPE,
                servicemanager.PYS_SERVICE_STARTED,
                (self._svc_name_, ""),
            )
            monitor.main(stop_event=self._stop_flag)
        except Exception as e:
            _log_crash("SvcDoRun", e)
            raise


if __name__ == "__main__":
    if len(sys.argv) == 1:
        # Launched bare by the SCM (its ImagePath call never carries extra
        # arguments). win32serviceutil.HandleCommandLine does NOT handle this
        # case in this pywin32 version - it only parses CLI verbs
        # (install/remove/start/stop/debug) and, given zero arguments, just
        # prints usage and sys.exit(1)s (win32serviceutil.py: "if len(argv)
        # <= 1: usage()"). The actual SCM handshake has to be driven directly
        # through servicemanager instead. This is *the* fix for the service
        # never starting (Event 7009/7000) despite every other launch path
        # (debug mode, a scheduled task) working fine - HandleCommandLine was
        # silently exiting before ever reaching our ServiceFramework code.
        try:
            servicemanager.Initialize()
            servicemanager.PrepareToHostSingle(AIMonitorService)
            servicemanager.StartServiceCtrlDispatcher()
        except Exception as e:
            _log_crash("StartServiceCtrlDispatcher", e)
            raise
    else:
        try:
            win32serviceutil.HandleCommandLine(AIMonitorService)
        except Exception as e:
            _log_crash("HandleCommandLine", e)
            raise
