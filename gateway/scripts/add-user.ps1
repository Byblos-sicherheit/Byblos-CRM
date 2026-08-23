param(
    [Parameter(Mandatory = $false)]
    [string]$Username
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$UsersFile = Join-Path $ProjectRoot "config\users.caddy"
$CaddyImage = "caddy:2.11.4-alpine"
$Utf8NoBom = New-Object System.Text.UTF8Encoding($false)

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    throw "Docker wurde nicht gefunden. Docker Desktop installieren und starten."
}

& docker image inspect $CaddyImage *> $null
if ($LASTEXITCODE -ne 0) {
    Write-Host "Caddy-Image wird einmalig geladen..."
    & docker pull $CaddyImage
    if ($LASTEXITCODE -ne 0) {
        throw "Caddy-Image konnte nicht geladen werden."
    }
}

if ([string]::IsNullOrWhiteSpace($Username)) {
    $Username = Read-Host "Benutzername (3-32 Zeichen)"
}

if ($Username -notmatch '^[A-Za-z0-9][A-Za-z0-9._-]{2,31}$') {
    throw "Ungültiger Benutzername. Erlaubt: Buchstaben, Zahlen, Punkt, Unterstrich und Bindestrich; 3-32 Zeichen."
}

$SecurePassword = Read-Host "Passwort (mindestens 14 Zeichen)" -AsSecureString
$ConfirmPassword = Read-Host "Passwort wiederholen" -AsSecureString
$PasswordPtr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($SecurePassword)
$ConfirmPtr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($ConfirmPassword)

try {
    $PlainPassword = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($PasswordPtr)
    $PlainConfirm = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($ConfirmPtr)

    if ($PlainPassword.Length -lt 14) {
        throw "Das Passwort ist zu kurz. Mindestens 14 Zeichen verwenden."
    }
    if ($PlainPassword -cne $PlainConfirm) {
        throw "Die Passwörter stimmen nicht überein."
    }

    $PasswordHash = (& docker run --rm $CaddyImage caddy hash-password --plaintext $PlainPassword 2>&1 | Out-String).Trim()
    if ($LASTEXITCODE -ne 0 -or $PasswordHash -notmatch '^\$2[aby]\$') {
        throw "Caddy konnte keinen gültigen bcrypt-Hash erzeugen: $PasswordHash"
    }
}
finally {
    if ($PasswordPtr -ne [IntPtr]::Zero) {
        [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($PasswordPtr)
    }
    if ($ConfirmPtr -ne [IntPtr]::Zero) {
        [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($ConfirmPtr)
    }
    $PlainPassword = $null
    $PlainConfirm = $null
}

$ExistingLines = @()
if (Test-Path $UsersFile) {
    $ExistingLines = [System.IO.File]::ReadAllLines($UsersFile) |
        Where-Object {
            $_ -match '^\s*#' -or $_ -notmatch ('^\s*' + [regex]::Escape($Username) + '\s+')
        }
}

$ActiveLines = $ExistingLines | Where-Object { $_ -match '^\s*[A-Za-z0-9][A-Za-z0-9._-]*\s+\$2[aby]\$' }
$OutputLines = @(
    "# Automatisch verwaltete bcrypt-Zugänge. Keine Klartext-Passwörter."
    $ActiveLines
    "$Username $PasswordHash"
)
[System.IO.File]::WriteAllLines($UsersFile, $OutputLines, $Utf8NoBom)

Write-Host "Benutzer '$Username' wurde gespeichert."
Write-Host "Zum Aktivieren: docker compose restart gateway"
