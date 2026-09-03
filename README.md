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

## Installation (für die meisten: nur das hier lesen)

Unter [Releases](https://github.com/19DMO89/AIcontrol/releases/latest)
liegt eine fertig gebaute **`AIMonitor-Setup.exe`** zum Download — kein
Python, kein Bauen nötig. Auf dem Zielrechner (z. B. dem Wettbewerbs-PC):

1. `AIMonitor-Setup.exe` herunterladen und doppelklicken.
2. UAC-Abfrage bestätigen (die Datei fordert die Rechte automatisch an).
3. Am Ende: Dashboard-Benutzername/-Passwort vergeben, wenn danach gefragt
   wird (min. 6 Zeichen) — **sofort erledigen**, bevor der PC an
   Teilnehmer übergeben wird.

Das war's — Dienst und Session-Agent laufen, auf dem Desktop liegt der
Ordner **`AI-Monitor`** mit der Dashboard- und einer Deinstallations-
Verknüpfung.

Programmdateien liegen danach unter `%ProgramData%\AIMonitor\bin` (nur
lesbar/ausführbar für Standardbenutzer), Datenbank und Screenshots unter
`%ProgramData%\AIMonitor\data`.

## Bauen & Paketieren (nur für Entwickler)

Nötig, wenn du `config.py` (Erkennungsliste) oder den restlichen Code
änderst und daraus eine neue `AIMonitor-Setup.exe` erzeugen willst.

Voraussetzungen: Windows, Python 3.10+, Abhängigkeiten installiert:

```powershell
python -m pip install -r requirements.txt
```

1. **Bauen** (erstellt `dist\AIMonitorService`, `dist\AIMonitorDashboard.exe`,
   `dist\AISessionAgent.exe` per PyInstaller):

   ```powershell
   powershell -ExecutionPolicy Bypass -File build.ps1
   ```

2. **Paketieren** (packt `dist\` + `Install-AIMonitor.ps1` +
   `Uninstall-AIMonitor.ps1` in eine einzige `AIMonitor-Setup.exe`, siehe
   oben):

   ```powershell
   powershell -ExecutionPolicy Bypass -File package.ps1
   ```

   Braucht nur `csc.exe` (Teil jeder .NET-Framework-Installation, kein
   Zusatzwerkzeug). `AIMonitor-Setup.exe` liegt danach im Projektordner und
   kann auf beliebig viele Zielrechner kopiert werden.

### Manuell installieren (ohne AIMonitor-Setup.exe)

Alternativ direkt aus dem gebauten `dist\` heraus installieren, z. B. zum
Testen auf dem Entwickler-Rechner selbst:

```powershell
powershell -ExecutionPolicy Bypass -File Install-AIMonitor.ps1
```

Alternativ per Doppelklick auf `AI-Monitor installieren.bat`. Fordert
automatisch Administratorrechte per UAC an.

> **Häufigster Fehler:** `dist\ nicht gefunden oder unvollstaendig.`
> Das bedeutet, Schritt 1 (`build.ps1`) wurde noch nicht oder nicht
> vollständig ausgeführt.

Fertige `AIMonitor-Setup.exe` als neues Release veröffentlichen:

```powershell
gh release create vX.Y.Z AIMonitor-Setup.exe --title "vX.Y.Z" --notes "..."
```

## Deinstallation

Die Installation legt einen Eintrag **„AI-Monitor"** unter Windows-
Einstellungen → *Apps* (bzw. *Systemsteuerung → Programme und Features*) an.
Von dort „Deinstallieren" wählen — die UAC-Abfrage bestätigen, fertig.

Alternativ direkt das mitinstallierte Skript ausführen:

```powershell
powershell -ExecutionPolicy Bypass -File "%ProgramData%\AIMonitor\bin\Uninstall-AIMonitor.ps1"
```

bzw. im Entwickler-Ordner:

```powershell
powershell -ExecutionPolicy Bypass -File Uninstall-AIMonitor.ps1
```

Erfordert Administratorrechte (bewusst so, damit Teilnehmer die Überwachung
nicht selbst entfernen können). Optionen:

- `-KeepData` — Datenbank/Screenshots unter `%ProgramData%\AIMonitor\data`
  behalten statt zu löschen
- `-Force` — ohne Rückfrage deinstallieren

Alternativ per Doppelklick auf `AI-Monitor deinstallieren.bat` (liegt nach
der Installation auch unter `%ProgramData%\AIMonitor\bin`).

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

## Änderungsverlauf

Siehe [CHANGELOG.md](CHANGELOG.md).

## Was wird erkannt?

Die überwachten Domains, Prozessnamen, Fenstertitel-Schlagwörter und
Zwischenablage-Muster stehen in `config.py` und können dort erweitert
werden (z. B. `AI_DOMAINS`, `AI_PROCESSES`, `AI_WINDOW_KEYWORDS`,
`AI_CLIPBOARD_PATTERNS`). Nach einer Änderung muss neu gebaut und neu
installiert werden (Schritte 1 und 2 oben), da der Python-Quellcode
vollständig in die EXE-Dateien kompiliert wird.
