# Als Administrator ausführen.
$ErrorActionPreference = "Stop"
$CurrentIdentity = [Security.Principal.WindowsIdentity]::GetCurrent()
$Principal = New-Object Security.Principal.WindowsPrincipal($CurrentIdentity)
if (-not $Principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    throw "PowerShell als Administrator starten."
}

$Rules = @(
    @{ Name = "Byblos Gateway HTTP TCP 80"; Protocol = "TCP"; Port = 80 },
    @{ Name = "Byblos Gateway HTTPS TCP 443"; Protocol = "TCP"; Port = 443 },
    @{ Name = "Byblos Gateway HTTP3 UDP 443"; Protocol = "UDP"; Port = 443 }
)

foreach ($Rule in $Rules) {
    if (-not (Get-NetFirewallRule -DisplayName $Rule.Name -ErrorAction SilentlyContinue)) {
        New-NetFirewallRule `
            -DisplayName $Rule.Name `
            -Direction Inbound `
            -Action Allow `
            -Protocol $Rule.Protocol `
            -LocalPort $Rule.Port `
            -Profile Private
    }
}

Write-Host "Firewallregeln wurden für das private Netzwerkprofil gesetzt."
