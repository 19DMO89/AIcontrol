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

# Wenn der SCM eine gefrorene (PyInstaller-)EXE startet, gibt es keine echte
# Konsole (Session 0) - sys.stdout/sys.stderr sind dann None statt eines
# Datei-Objekts. Unser eigener Python-Code faengt das ab, aber pywin32s
# C-Erweiterung (servicemanager/win32service) tut das nicht und kann dabei
# haengen bleiben - genau das Muster, das den 60s-SCM-Timeout (Ereignis 7009)
# ausgeloest hat, obwohl im "debug"-Testlauf (mit echter Konsole) alles lief.
# Deshalb hier VOR jedem pywin32-Import auf echte Datei-Objekte umbiegen.
if sys.stdout is None:
    sys.stdout = open(os.devnull, "w")
if sys.stderr is None:
    sys.stderr = open(os.devnull, "w")

import threading

import servicemanager
import win32event
import win32service
import win32serviceutil

import monitor


class AIMonitorService(win32serviceutil.ServiceFramework):
    _svc_name_ = "AIMonitor"
    _svc_display_name_ = "AI-Monitor (Berufsweltmeisterschaften)"
    _svc_description_ = (
        "Ueberwacht Netzwerk-, Prozess-, Browser- und Zwischenablage-Aktivitaet "
        "auf KI-Nutzung waehrend der Berufsweltmeisterschaften."
    )

    def __init__(self, args):
        super().__init__(args)
        self._wait_event = win32event.CreateEvent(None, 0, 0, None)
        self._stop_flag = threading.Event()

    def SvcStop(self):
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        self._stop_flag.set()
        win32event.SetEvent(self._wait_event)

    def SvcDoRun(self):
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


if __name__ == "__main__":
    win32serviceutil.HandleCommandLine(AIMonitorService)
