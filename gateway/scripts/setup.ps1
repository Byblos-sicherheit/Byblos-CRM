$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot
$EnvFile = Join-Path $ProjectRoot ".env"
$EnvExample = Join-Path $ProjectRoot ".env.example"
$Utf8NoBom = New-Object System.Text.UTF8Encoding($false)

function Require-Command([string]$Name, [string]$Message) {
    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        throw $Message
    }
}

function Read-WithDefault([string]$Prompt, [string]$DefaultValue) {
    $Value = Read-Host "$Prompt [$DefaultValue]"
    if ([string]::IsNullOrWhiteSpace($Value)) {
        return $DefaultValue
    }
    return $Value.Trim()
}

function Set-EnvValue([string[]]$Lines, [string]$Key, [string]$Value) {
    $Result = New-Object System.Collections.Generic.List[string]
    $Found = $false
    foreach ($Line in $Lines) {
        if ($Line -match ('^' + [regex]::Escape($Key) + '=')) {
            $Result.Add("$Key=$Value")
            $Found = $true
        }
        else {
            $Result.Add($Line)
        }
    }
    if (-not $Found) {
        $Result.Add("$Key=$Value")
    }
    return $Result.ToArray()
}

Require-Command "docker" "Docker wurde nicht gefunden. Docker Desktop installieren und starten."
& docker info *> $null
if ($LASTEXITCODE -ne 0) {
    throw "Docker Desktop läuft nicht."
}
& docker compose version *> $null
if ($LASTEXITCODE -ne 0) {
    throw "Docker Compose ist nicht verfügbar."
}

if (-not (Test-Path $EnvFile)) {
    Copy-Item $EnvExample $EnvFile
}

$Lines = [System.IO.File]::ReadAllLines($EnvFile)
$Domain = Read-WithDefault "Öffentliche Domain" "ai.byblos-sicherheit.com"
$AcmeEmail = Read-WithDefault "E-Mail für Zertifikatshinweise" "info@byblos-sicherheit.de"
$LexAi = Read-WithDefault "LexAI-Pro intern (Host:Port)" "host.docker.internal:3000"
$Crm = Read-WithDefault "CRM intern (Host:Port)" "host.docker.internal:3001"
$Wks = Read-WithDefault "WKS-Pro intern (Host:Port)" "host.docker.internal:3002"
$Files = Read-WithDefault "FileBrowser intern (Host:Port)" "host.docker.internal:8080"

if ($Domain -notmatch '^[A-Za-z0-9.-]+\.[A-Za-z]{2,}$') {
    throw "Die Domain ist ungültig. Nur den DNS-Namen ohne https:// oder Pfad eingeben."
}
if ($AcmeEmail -notmatch '^[^@\s]+@[^@\s]+\.[^@\s]+$') {
    throw "Die E-Mail-Adresse ist ungültig."
}

$Lines = Set-EnvValue $Lines "DOMAIN" $Domain
$Lines = Set-EnvValue $Lines "ACME_EMAIL" $AcmeEmail
$Lines = Set-EnvValue $Lines "LEXAI_UPSTREAM" $LexAi
$Lines = Set-EnvValue $Lines "CRM_UPSTREAM" $Crm
$Lines = Set-EnvValue $Lines "WKS_UPSTREAM" $Wks
$Lines = Set-EnvValue $Lines "FILES_UPSTREAM" $Files
[System.IO.File]::WriteAllLines($EnvFile, $Lines, $Utf8NoBom)

& (Join-Path $PSScriptRoot "add-user.ps1")
if ($LASTEXITCODE -ne 0) {
    throw "Benutzer konnte nicht angelegt werden."
}

& (Join-Path $PSScriptRoot "validate.ps1")
if ($LASTEXITCODE -ne 0) {
    throw "Validierung fehlgeschlagen."
}

& docker compose up -d
if ($LASTEXITCODE -ne 0) {
    throw "Gateway konnte nicht gestartet werden."
}

& docker compose ps
Write-Host ""
Write-Host "Gateway wurde gestartet."
Write-Host "Jetzt Router, DNS und Windows-Firewall nach DEPLOY-ANLEITUNG.md konfigurieren."
