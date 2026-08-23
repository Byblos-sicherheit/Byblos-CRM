# Betrieb

## Status und Protokolle

```powershell
docker compose ps
docker compose logs --tail 200 gateway
docker compose logs -f gateway
```

Die Zugriffprotokolle liegen zusätzlich im Docker-Volume
`byblos_gateway_logs`. Caddy rotiert sie bei 25 MiB, behält höchstens zehn
Dateien und entfernt Protokolle nach 30 Tagen.

## Konfigurationsänderung

1. `.env`, `config/Caddyfile` oder Benutzerdatei ändern.
2. Validieren:

   ```powershell
   powershell.exe -File .\scripts\validate.ps1
   ```

3. Neu laden:

   ```powershell
   docker compose restart gateway
   ```

## Update

```powershell
docker compose pull
docker compose up -d
docker image prune
```

Vor einem Versionssprung Backup erstellen und Caddy-/Compose-Konfiguration
validieren. Das Image ist bewusst auf `2.11.4-alpine` festgelegt. Ein Update
erfolgt kontrolliert durch Änderung dieser Version in `compose.yaml` und in den
Benutzerskripten.

## Stopp

```powershell
docker compose down
```

Kein `docker compose down -v` verwenden: `-v` löscht Zertifikats-, Konfigurations-
und Log-Volumes.

## Fehlerdiagnose

| Symptom | Prüfung |
|---|---|
| Kein Zertifikat | DNS, TCP 80/443, Caddy-Logs |
| HTTP 502 | Interne App läuft nicht oder falscher Port in `.env` |
| Login wiederholt sich | Benutzerdatei/Hash prüfen, Gateway neu starten |
| App ohne CSS/JS | Base-URL der App für Unterpfad konfigurieren |
| Intern erreichbar, extern nicht | Router-Portweiterleitung, Firewall, CGNAT/DS-Lite |
