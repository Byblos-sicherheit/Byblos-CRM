# Testbericht

## Ergebnis

- Implementierung: **94 %**
- Verifizierter Gesamtstatus: **24 %**
- Lokale statische Prüfungen: **bestanden**
- Docker-/Caddy-Laufzeitprüfung: **nicht ausgeführt**
- Externer Produktivtest: **blockiert**

Die Prozentwerte folgen den vorab festgelegten Gewichten in
`DELIVERY-MATRIX.md`. Nur Kriterien mit bestandenem, angemessenem Nachweis
zählen zur Verifizierung.

## Prüfumgebung

- Datum: 29.07.2026
- System: Linux x86_64, Kernel 6.12.13
- Python: 3.12.13
- PyYAML: 6.0.3
- Docker: in dieser Arbeitsumgebung nicht installiert
- PowerShell: in dieser Arbeitsumgebung nicht installiert

## Bestandene Prüfungen

### Statische Paketprüfung

Befehl:

```bash
sh tests/run-static-tests.sh
```

Ergebnis:

```text
Statische Gateway-Prüfungen: BESTANDEN
Benutzeranlage ohne Klartextspeicherung: BESTANDEN
Benutzerentfernung und Schutz des letzten Benutzers: BESTANDEN
```

Geprüft wurden:

- Shell-Syntax der Linux-Verwaltungsskripte
- erforderliche Caddy-Routen und Authentisierungskonfiguration
- konsistente Umgebungsvariablen
- festgelegtes Caddy-Image `2.11.4-alpine`
- Ports 80/TCP, 443/TCP und 443/UDP
- persistente Caddy-Volumes
- keine produktive `.env`
- kein aktiver Standardbenutzer
- kein privater Schlüssel, AWS- oder OpenAI-Schlüssel
- vorhandene Betriebs-, Backup-, Sicherheits- und Rollenunterlagen
- gültige relative Markdown-Links
- Benutzeranlage speichert nur einen Hash
- Benutzerentfernung erhält andere Benutzer
- letzter Benutzer kann nicht entfernt werden

### Compose-YAML

`compose.yaml` wurde mit PyYAML 6.0.3 eingelesen und gegen Service-, Image-,
Volume-, Port- und Healthcheck-Pflichtwerte geprüft.

Ergebnis: **bestanden**.

## Nicht ausgeführte Prüfungen

### Caddy-Konfigurationsadapter und Containerstart

Nicht ausgeführt, weil in der Prüfumgebung weder Docker noch ein
Caddy-Binärprogramm vorhanden ist.

Nachholbefehl auf dem Zielserver:

```powershell
powershell.exe -ExecutionPolicy Bypass -File .\scripts\validate.ps1
docker compose up -d
docker compose ps
```

### PowerShell-Laufzeitprüfung

Die PowerShell-Skripte wurden manuell auf Windows-PowerShell-5.1-kompatible
Syntax ausgelegt, konnten hier aber mangels PowerShell nicht ausgeführt werden.

Nachholschritt: `SETUP-WINDOWS.cmd` auf dem Zielserver ausführen.

### Produktivprüfung

Blockiert durch fehlenden Zugriff auf:

- die tatsächlichen Ports von LexAI-Pro, CRM, WKS-Pro und FileBrowser
- Server-PC und Docker Desktop
- Router-Portweiterleitung
- DNS-Zone `byblos-sicherheit.com`
- öffentliche IP-/CGNAT-Situation

Nachholschritt: Nach `DEPLOY-ANLEITUNG.md` konfigurieren und anschließend
`scripts/test-gateway.ps1` über einen externen Mobilfunkzugang ausführen.
