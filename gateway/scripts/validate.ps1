$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

if (-not (Test-Path ".env")) {
    throw ".env fehlt. Zuerst setup.ps1 ausführen."
}
if (-not (Test-Path "config\users.caddy")) {
    throw "config\users.caddy fehlt."
}
$ActiveUsers = Get-Content "config\users.caddy" |
    Where-Object { $_ -match '^\s*[A-Za-z0-9][A-Za-z0-9._-]*\s+\$2[aby]\$' }
if ($ActiveUsers.Count -lt 1) {
    throw "Kein aktiver Benutzer vorhanden. Zuerst add-user.ps1 ausführen."
}

& docker compose config --quiet
if ($LASTEXITCODE -ne 0) {
    throw "Compose-Konfiguration ist ungültig."
}

& docker compose run --rm --no-deps gateway caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile
if ($LASTEXITCODE -ne 0) {
    throw "Caddy-Konfiguration ist ungültig."
}

Write-Host "Compose- und Caddy-Konfiguration sind gültig."
