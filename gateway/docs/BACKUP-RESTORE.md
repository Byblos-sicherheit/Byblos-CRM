# Backup und Wiederherstellung

Zu sichern:

- `.env`
- `config/users.caddy`
- Docker-Volume `byblos_gateway_data` (Zertifikate und ACME-Daten)
- Docker-Volume `byblos_gateway_config`

Die Dateien enthalten sensible Betriebsdaten. Backup verschlüsseln und Zugriff
begrenzen.

## Backup unter PowerShell

```powershell
New-Item -ItemType Directory -Force .\backups | Out-Null
$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
Copy-Item .env ".\backups\env-$stamp.txt"
Copy-Item .\config\users.caddy ".\backups\users-$stamp.caddy"
docker run --rm `
  -v byblos_gateway_data:/source:ro `
  -v "${PWD}\backups:/backup" `
  alpine:3.22 `
  tar -czf "/backup/caddy-data-$stamp.tar.gz" -C /source .
docker run --rm `
  -v byblos_gateway_config:/source:ro `
  -v "${PWD}\backups:/backup" `
  alpine:3.22 `
  tar -czf "/backup/caddy-config-$stamp.tar.gz" -C /source .
```

## Wiederherstellung

1. Gateway stoppen.
2. Vorhandene Volumes zusätzlich sichern.
3. Dateien zurückkopieren.
4. Archive in die exakt passenden Volumes entpacken.
5. Validieren und starten.

Beispiel:

```powershell
docker compose down
docker volume create byblos_gateway_data
docker run --rm `
  -v byblos_gateway_data:/target `
  -v "${PWD}\backups:/backup:ro" `
  alpine:3.22 `
  tar -xzf /backup/caddy-data-DATUM.tar.gz -C /target
docker compose up -d
```

`DATUM` durch den tatsächlichen Dateinamen ersetzen. Eine Wiederherstellung
wurde in dieser Umgebung nicht gegen den späteren Server-PC getestet.
