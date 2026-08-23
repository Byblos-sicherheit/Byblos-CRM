param(
    [Parameter(Mandatory = $true)]
    [string]$Username
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$UsersFile = Join-Path $ProjectRoot "config\users.caddy"
$Utf8NoBom = New-Object System.Text.UTF8Encoding($false)

if (-not (Test-Path $UsersFile)) {
    throw "Benutzerdatei nicht gefunden."
}

$ActiveLines = [System.IO.File]::ReadAllLines($UsersFile) |
    Where-Object { $_ -match '^\s*[A-Za-z0-9][A-Za-z0-9._-]*\s+\$2[aby]\$' }
$Remaining = $ActiveLines |
    Where-Object { $_ -notmatch ('^\s*' + [regex]::Escape($Username) + '\s+') }

if ($Remaining.Count -eq $ActiveLines.Count) {
    throw "Benutzer '$Username' wurde nicht gefunden."
}
if ($Remaining.Count -eq 0) {
    throw "Der letzte Benutzer wird nicht entfernt. Zuerst einen Ersatzbenutzer anlegen."
}

$OutputLines = @("# Automatisch verwaltete bcrypt-Zugänge. Keine Klartext-Passwörter.") + $Remaining
[System.IO.File]::WriteAllLines($UsersFile, $OutputLines, $Utf8NoBom)
Write-Host "Benutzer '$Username' wurde entfernt."
Write-Host "Zum Aktivieren: docker compose restart gateway"
