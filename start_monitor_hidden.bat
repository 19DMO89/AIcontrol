@echo off
:: Startet Monitor unsichtbar im Hintergrund (kein Konsolenfenster)
start "" /B pythonw monitor.py
echo Monitor gestartet (unsichtbar).
timeout /t 2 >nul
