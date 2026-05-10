# build_msix.ps1 – Byblos CRM MSIX Builder v2
# Aufruf: .\msix\build_msix.ps1
# Oder:   PowerShell als Admin, dann: cd <root>; .\msix\build_msix.ps1
#
# Optionen:
#   -CertPath "C:\certs\mein.pfx"  -CertPass "geheim"
#   -Version  "2.0.1.0"

param(
    [string]$CertPath = "",
    [string]$CertPass = "",
    [string]$Version  = "2.0.0.0"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Write-Step($m) { Write-Host "`n[STEP] $m" -ForegroundColor Cyan }
function Write-OK($m)   { Write-Host "[OK]   $m" -ForegroundColor Green }
function Write-Warn($m) { Write-Host "[WARN] $m" -ForegroundColor Yellow }
function Write-Fail($m) { Write-Host "[FAIL] $m" -ForegroundColor Red; exit 1 }

# Pfade immer relativ zum Root-Verzeichnis (ein Ordner ueber msix\)
$Root   = (Split-Path $PSScriptRoot -Parent)
$Layout = "$Root\msix\PackageLayout"
$Output = "$Root\msix\ByblosCRM_$($Version -replace '\.','_').msix"

Write-Step "Byblos CRM MSIX Builder v2"
Write-Host "   Root:    $Root"
Write-Host "   Layout:  $Layout"
Write-Host "   Output:  $Output"

# 1. EXE pruefen
Write-Step "Pruefe PyInstaller-Build..."
$ExeDir = "$Root\dist\ByblosCRM"
$ExePath = "$ExeDir\ByblosCRM.exe"
if (-not (Test-Path $ExePath)) {
    Write-Fail "EXE nicht gefunden: $ExePath`n`nBitte zuerst BUILD_WINDOWS.bat ausfuehren!"
}
Write-OK "EXE gefunden: $ExePath"

# 2. MakeAppx.exe suchen
Write-Step "Suche MakeAppx.exe (Windows SDK)..."
$SDKBase = "C:\Program Files (x86)\Windows Kits\10\bin"
$MakeAppx = $null
if (Test-Path $SDKBase) {
    $MakeAppx = Get-ChildItem -Path $SDKBase -Recurse -Filter "makeappx.exe" -EA SilentlyContinue |
        Where-Object { $_.FullName -match "x64" } |
        Sort-Object -Descending |
        Select-Object -First 1 -ExpandProperty FullName
}
if (-not $MakeAppx) {
    Write-Fail "MakeAppx.exe nicht gefunden.`nBitte Windows SDK installieren:`nhttps://developer.microsoft.com/windows/downloads/windows-sdk/"
}
Write-OK "MakeAppx: $MakeAppx"

# 3. Layout aufbauen
Write-Step "Erstelle Package-Layout..."
if (Test-Path $Layout) { Remove-Item $Layout -Recurse -Force }
New-Item -ItemType Directory -Path $Layout | Out-Null

# EXE-Ordner kopieren
Copy-Item $ExeDir "$Layout\ByblosCRM" -Recurse
Write-OK "EXE-Ordner kopiert."

# Assets erstellen
$AssetsDir = "$Layout\assets"
New-Item -ItemType Directory -Path $AssetsDir | Out-Null

# Manifest schreiben
$Manifest = @"
<?xml version="1.0" encoding="UTF-8"?>
<Package
  xmlns="http://schemas.microsoft.com/appx/manifest/foundation/windows10"
  xmlns:uap="http://schemas.microsoft.com/appx/manifest/uap/windows10"
  xmlns:rescap="http://schemas.microsoft.com/appx/manifest/foundation/windows10/restrictedcapabilities"
  IgnorableNamespaces="uap rescap">
  <Identity Name="ByblosSicherheitsdienst.ByblosCRM"
            Publisher="CN=ByblosSicherheitsdienst"
            Version="$Version"
            ProcessorArchitecture="x64" />
  <Properties>
    <DisplayName>Byblos CRM</DisplayName>
    <PublisherDisplayName>Byblos Sicherheitsdienst</PublisherDisplayName>
    <Logo>assets\StoreLogo.png</Logo>
  </Properties>
  <Dependencies>
    <TargetDeviceFamily Name="Windows.Desktop" MinVersion="10.0.17763.0" MaxVersionTested="10.0.22621.0" />
  </Dependencies>
  <Resources><Resource Language="de-DE" /></Resources>
  <Applications>
    <Application Id="ByblosCRM" Executable="ByblosCRM\ByblosCRM.exe" EntryPoint="Windows.FullTrustApplication">
      <uap:VisualElements DisplayName="Byblos CRM" Description="Byblos CRM Betriebssoftware"
        BackgroundColor="#0e1117"
        Square150x150Logo="assets\Square150x150Logo.png"
        Square44x44Logo="assets\Square44x44Logo.png">
        <uap:DefaultTile Wide310x150Logo="assets\Wide310x150Logo.png" ShortName="Byblos CRM" />
        <uap:SplashScreen Image="assets\SplashScreen.png" BackgroundColor="#0e1117" />
      </uap:VisualElements>
    </Application>
  </Applications>
  <Capabilities>
    <Capability Name="internetClient" />
    <Capability Name="privateNetworkClientServer" />
    <rescap:Capability Name="runFullTrust" />
  </Capabilities>
</Package>
"@
$Manifest | Set-Content "$Layout\AppxManifest.xml" -Encoding UTF8
Write-OK "AppxManifest.xml erstellt."

# Platzhalter-PNGs erzeugen (System.Drawing)
Add-Type -AssemblyName System.Drawing
$sizes = @(
    @{N="Square44x44Logo.png";   W=44;  H=44 },
    @{N="Square150x150Logo.png"; W=150; H=150},
    @{N="Wide310x150Logo.png";   W=310; H=150},
    @{N="SplashScreen.png";      W=620; H=300},
    @{N="StoreLogo.png";         W=50;  H=50 }
)
foreach ($s in $sizes) {
    $dst = "$AssetsDir\$($s.N)"
    if (-not (Test-Path $dst)) {
        $bmp = New-Object System.Drawing.Bitmap($s.W, $s.H)
        $g   = [System.Drawing.Graphics]::FromImage($bmp)
        $g.Clear([System.Drawing.Color]::FromArgb(14,17,23))
        $br  = New-Object System.Drawing.SolidBrush([System.Drawing.Color]::FromArgb(192,57,43))
        $fnt = New-Object System.Drawing.Font("Arial",[Math]::Max(10,[int]($s.H/5)),[System.Drawing.FontStyle]::Bold)
        $sf  = New-Object System.Drawing.StringFormat
        $sf.Alignment = [System.Drawing.StringAlignment]::Center
        $sf.LineAlignment = [System.Drawing.StringAlignment]::Center
        $g.DrawString("B",$fnt,$br,[System.Drawing.RectangleF]::new(0,0,$s.W,$s.H),$sf)
        $bmp.Save($dst,[System.Drawing.Imaging.ImageFormat]::Png)
        $g.Dispose(); $bmp.Dispose()
    }
}
Write-OK "Assets erstellt."

# 4. MSIX bauen
Write-Step "Erstelle MSIX-Paket..."
if (Test-Path $Output) { Remove-Item $Output -Force }
& $MakeAppx pack /d $Layout /p $Output /nv 2>&1
if ($LASTEXITCODE -ne 0) { Write-Fail "MakeAppx fehlgeschlagen (Exit $LASTEXITCODE)." }
Write-OK "MSIX erstellt: $Output"

# 5. Signieren (optional)
if ($CertPath -and (Test-Path $CertPath)) {
    Write-Step "Signiere MSIX..."
    $SignTool = Get-ChildItem "C:\Program Files (x86)\Windows Kits\10\bin" -Recurse -Filter "signtool.exe" -EA SilentlyContinue |
        Where-Object { $_.FullName -match "x64" } | Select-Object -First 1 -ExpandProperty FullName
    if ($SignTool) {
        & $SignTool sign /fd SHA256 /f $CertPath /p $CertPass $Output
        if ($LASTEXITCODE -eq 0) { Write-OK "Signiert." } else { Write-Warn "Signierung fehlgeschlagen." }
    } else { Write-Warn "signtool.exe nicht gefunden." }
} else {
    Write-Warn "Kein Zertifikat – MSIX ist UNSIGNIERT (nur Sideload/Test)."
}

Write-Step "Fertig!"
Write-OK "MSIX: $Output"
Write-Host ""
Write-Host "Installation (Admin-PowerShell):" -ForegroundColor White
Write-Host "  Add-AppxPackage -Path `"$Output`" -AllowUnsigned" -ForegroundColor Gray
Write-Host ""
