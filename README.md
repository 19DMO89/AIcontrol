# AI-Monitor

Überwacht einen Windows-Rechner auf Nutzung von KI-Tools (ChatGPT, Claude,
Copilot, lokale LLMs, KI-Browser-Erweiterungen, verdächtige Zwischenablage-
Inhalte, ...) und protokolliert Funde inkl. Screenshot in einer lokalen,
passwortgeschützten Datenbank. Gedacht für Prüfungs-/Wettbewerbssituationen
(z. B. Berufsweltmeisterschaften), in denen der Einsatz von KI-Hilfsmitteln
ausgeschlossen sein muss.

Läuft als Windows-Dienst unter dem `LocalSystem`-Konto, startet automatisch
mit Windows und ist von einem Standardbenutzer ohne Administratorrechte
weder zu stoppen noch zu entfernen (eingebautes Windows-SCM-Verhalten).

## Bestandteile

| Komponente | Zweck |
|---|---|
| `AIMonitorService.exe` | Hintergrunddienst: überwacht Prozesse, Netzwerkverbindungen, Browserverlauf, Zwischenablage |
| `AISessionAgent.exe` | Läuft in der Nutzersitzung, macht bei Treffern Screenshots (ein Dienst in Session 0 hat keinen Zugriff auf den Desktop) |
| `AIMonitorDashboard.exe` | Passwortgeschütztes Anzeige-Tool für die protokollierten Ereignisse und Screenshots |

## Voraussetzungen zum Bauen

- Windows
- Python 3.10+
- Abhängigkeiten installieren:

  ```powershell
  python -m pip install -r requirements.txt
  ```

Es gibt keine fertigen EXE-Dateien im Repo oder als Release-Anhang — `dist\`
wird bewusst nicht mit eingecheckt (siehe `.gitignore`) und muss lokal
gebaut werden.

## Installation

1. **Bauen** (erstellt `dist\AIMonitorService`, `dist\AIMonitorDashboard.exe`,
   `dist\AISessionAgent.exe` per PyInstaller):

   ```powershell
   powershell -ExecutionPolicy Bypass -File build.ps1
   ```

2. **Installieren** (registriert den Windows-Dienst, legt ein Dashboard-Icon
   auf dem Desktop aller Benutzer an, richtet den Session-Agent-Autostart
   ein). Fordert automatisch Administratorrechte per UAC an:

   ```powershell
   powershell -ExecutionPolicy Bypass -File Install-AIMonitor.ps1
   ```

   Alternativ per Doppelklick auf `AI-Monitor installieren.bat`.

   > **Häufigster Fehler:** `dist\ nicht gefunden oder unvollstaendig.`
   > Das bedeutet, Schritt 1 (`build.ps1`) wurde noch nicht oder nicht
   > vollständig ausgeführt.

3. **Dashboard-Passwort vergeben**: Beim ersten Start von
   `AIMonitorDashboard.exe` nach der Installation wird nach einem
   Benutzernamen und einem Passwort (min. 6 Zeichen) gefragt — dieses
   schützt den Zugriff auf die protokollierten Ereignisse und Screenshots.

Programmdateien liegen danach unter `%ProgramData%\AIMonitor\bin` (nur
lesbar/ausführbar für Standardbenutzer), Datenbank und Screenshots unter
`%ProgramData%\AIMonitor\data`.

## Deinstallation

```powershell
powershell -ExecutionPolicy Bypass -File Uninstall-AIMonitor.ps1
```

Erfordert Administratorrechte (bewusst so, damit Teilnehmer die Überwachung
nicht selbst entfernen können). Optionen:

- `-KeepData` — Datenbank/Screenshots unter `%ProgramData%\AIMonitor\data`
  behalten statt zu löschen
- `-Force` — ohne Rückfrage deinstallieren

Alternativ per Doppelklick auf `AI-Monitor deinstallieren.bat`.

## Fehlersuche

Startet der Dienst nach der Installation nicht (Windows-Ereignis 7009 /
Timeout), liefert das Diagnose-Skript eine genaue Fehlerausgabe, indem es
die installierte Dienst-EXE einmalig unter dem SYSTEM-Konto ausführt —
demselben Kontext, den der echte Dienst nutzt:

```powershell
powershell -ExecutionPolicy Bypass -File Diagnose-AIMonitor.ps1
```

Ergebnis landet in `diagnose_output.log`. Alternativ per Doppelklick auf
`AI-Monitor Diagnose.bat`.

## Was wird erkannt?

Die überwachten Domains, Prozessnamen, Fenstertitel-Schlagwörter und
Zwischenablage-Muster stehen in `config.py` und können dort erweitert
werden (z. B. `AI_DOMAINS`, `AI_PROCESSES`, `AI_WINDOW_KEYWORDS`,
`AI_CLIPBOARD_PATTERNS`). Nach einer Änderung muss neu gebaut und neu
installiert werden (Schritte 1 und 2 oben), da der Python-Quellcode
vollständig in die EXE-Dateien kompiliert wird.
