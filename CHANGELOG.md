# Änderungsverlauf

Alle nennenswerten Änderungen an AI-Monitor. Neueste Version zuerst.

## v1.5.0 — 2026-09-03

### Behoben
- **`bing.com` als KI-Treffer.** Das nackte `bing.com` stand in der
  Erkennungsliste — Windows 11, Edge, Chrome, Widgets und die
  Windows-Suche kontaktieren es aber permanent ohne jede KI-Nutzung.
  Führte zu Fehlalarmen „Bing als KI" und „Chrome als KI" (Chrome bei
  genau dieser bing.com-Verbindung erwischt). Ersetzt durch
  `copilot.microsoft.com` und die Pfade `bing.com/chat`,
  `bing.com/copilot`.
- **Prozess-Erkennung per Teilstring gegen den ganzen Pfad.** Ein
  Listeneintrag wie `jan` (lokaler LLM-Runner) hätte bei einem
  Windows-Benutzer namens „Jan" (Pfad `C:\Users\Jan\…`) *jeden* Prozess
  als KI-Programm gemeldet. Jetzt exakter Abgleich gegen Prozess-/
  Dateinamen.
- **Domain-Abgleich auf Label-Grenze.** `x.ai` passt jetzt auf
  `api.x.ai`, aber nicht mehr auf `climax.airlines.com` o. Ä.

### Geändert
- **Wiederholte Nutzung wird protokolliert.** Bisher wurde jede App/
  Domain/URL genau einmal auf Lebenszeit erfasst — häufige Nutzung
  derselben laufenden Sitzung war unsichtbar. Jetzt: ein Eintrag pro
  Zeitfenster (`REDETECT_AFTER`, Standard 10 Min), danach wieder ein
  neuer. Browser-Treffer werden nach dem tatsächlichen Besuchszeitpunkt
  eingeordnet.

## v1.4.0 — 2026-09-03

### Behoben
- **Login-Dialog gab keine Rückmeldung bei falscher Eingabe.** Die
  Fehlermeldung („Falscher Benutzername oder Passwort", „Passwort zu kurz"
  …) wurde zwar gesetzt, lag aber außerhalb des sichtbaren Bereichs des
  fest dimensionierten, nicht vergrößerbaren Anmeldefensters. Die
  Statuszeile sitzt jetzt fest in der Anmeldekarte, das Fenster ist höher
  (Anmeldung 380 px, Ersteinrichtung 500 px).

### Neu
- **Deinstaller wird mitinstalliert und in Windows registriert.** Die
  Installation legt `Uninstall-AIMonitor.ps1` unter
  `%ProgramData%\AIMonitor\bin` ab (für Standardbenutzer nur les-/
  ausführbar) und trägt einen Eintrag **„AI-Monitor"** unter
  Einstellungen → *Apps* bzw. *Programme und Features* ein. Bisher ließ
  die `AIMonitor-Setup.exe` auf dem Zielrechner keinerlei Möglichkeit zum
  Deinstallieren zurück.
- **Desktop-Ordner statt loser Verknüpfung.** Auf dem Desktop aller
  Benutzer entsteht der Ordner `AI-Monitor` mit der Dashboard- und einer
  Deinstallations-Verknüpfung (Letztere fragt per UAC nach
  Administratorrechten).

### Verbessert
- **Upgrade über eine bestehende Installation.** Ein noch geöffnetes
  Dashboard wird vor dem Kopieren automatisch beendet (sonst schlug das
  Überschreiben von `AIMonitorDashboard.exe` fehl). Bereits gesetzte
  Dashboard-Zugangsdaten bleiben erhalten und werden bei der
  Neuinstallation nicht erneut abgefragt (`--has-credentials`-Prüfung).
- Der Deinstaller entfernt zusätzlich den „Apps & Features"-Eintrag und
  den Desktop-Ordner und kopiert sich beim Start aus dem
  Installationsordner nach `%TEMP%`, um sich beim Aufräumen nicht selbst
  zu blockieren.
- `package.ps1` bündelt `Uninstall-AIMonitor.ps1` und
  `AI-Monitor deinstallieren.bat` mit in die `AIMonitor-Setup.exe`.

## v1.3.1 — 2026-08-19

- **Installation:** Dienst-Registrierung schlug sporadisch mit „Zugriff
  verweigert" (Exit-Code 5) fehl, weil der Virenschutz die frisch
  kopierte `AIMonitorService.exe` gerade scannte. Wird jetzt automatisch
  mehrfach wiederholt.
- **Deinstallation:** Die eigene Manipulationsschutz-Regel (Deny für
  Standardbenutzer auf dem Screenshots-Ordner) blockierte teils das
  eigene Aufräumen, da ein Admin-Konto meist ebenfalls Mitglied dieser
  Gruppe ist. Zurückgebliebene Datenbank-/Screenshot-Dateien wurden
  dadurch nicht entfernt.

## v1.3.0 — 2026-08-19

- Fertig gebaute `AIMonitor-Setup.exe` zum Download — kein Python, kein
  manueller Build mehr nötig. `build.ps1` + `package.ps1` erzeugen die
  Datei neu aus dem Quellcode.

## v1.2.0 — 2026-07-16

### Wichtigster Fix
- Der Windows-Dienst startete bisher **nie tatsächlich** (stiller
  30-Sekunden-Timeout, Event 7009). Drei ineinander verschachtelte
  PyInstaller/pywin32-Bugs behoben und end-to-end an einem echten
  installierten Dienst verifiziert: fehlende `pythoncom`-DLL im Build;
  falscher `--console`-Modus (Dienste laufen in Session 0 ohne Konsole);
  eigentliche Ursache: `HandleCommandLine` übernimmt in dieser
  pywin32-Version nicht den SCM-Handshake — jetzt wird
  `StartServiceCtrlDispatcher` direkt aufgerufen.

### Neu
- Screenshots funktionieren jetzt über einen neuen Sitzungs-Agenten
  (läuft in der Nutzersitzung, da ein Dienst in Session 0 keinen Zugriff
  auf den Desktop hat).
- Screenshot-Ordner ist für Standardnutzer nur noch beschreibbar, nicht
  löschbar — Beweise können nicht entfernt werden.
- Browser-Erkennung funktioniert jetzt auch über den echten Dienst
  (mehrere Chrome/Edge/Brave-Profile, echte Benutzerprofile statt
  SYSTEM-Umgebungsvariablen).
- GitHub-Copilot-Erkennung repariert, plus JetBrains AI, Amazon Q, Cody,
  Supermaven ergänzt.
- Eigenes App-Icon; alte, durch den Dienst-Ansatz ersetzte .bat-Skripte
  entfernt.

## v1.1.0 — 2026-07-16

- Windows-Service-Installation (`monitor_service.py`) inkl.
  Installer-/Deinstaller-Skripte.
- Diagnose-Tool `Diagnose-AIMonitor.ps1` zur Fehlersuche bei
  Dienstproblemen.
- Fester Datenordner `%PROGRAMDATA%\AIMonitor\data`, damit Dienst und
  Dashboard dieselben Daten verwenden.
- Build-Skript `build.ps1` für PyInstaller-Builds.
- Weitere Erkennungs-Keywords für KI-Fenster/Prozesse.

## v1.0.0

- Erste Veröffentlichung: AI-Monitor für die Berufsweltmeisterschaften.
