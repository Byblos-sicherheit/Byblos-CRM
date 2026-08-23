param(
    [Parameter(Mandatory = $false)]
    [string]$BaseUrl = "https://ai.byblos-sicherheit.com"
)

$ErrorActionPreference = "Stop"
$BaseUrl = $BaseUrl.TrimEnd("/")

Write-Host "1/3 Öffentlicher Health-Endpunkt"
$Health = Invoke-WebRequest -Uri "$BaseUrl/healthz" -UseBasicParsing -TimeoutSec 20
if ($Health.StatusCode -ne 200 -or $Health.Content.Trim() -ne "ok") {
    throw "Health-Endpunkt ist fehlerhaft."
}

Write-Host "2/3 Zugriff ohne Anmeldung muss 401 liefern"
try {
    Invoke-WebRequest -Uri "$BaseUrl/" -UseBasicParsing -TimeoutSec 20 | Out-Null
    throw "Sicherheitsfehler: Zugriff ohne Anmeldung wurde zugelassen."
}
catch {
    if ($_.Exception.Response.StatusCode.value__ -ne 401) {
        throw
    }
}

Write-Host "3/3 Anmeldung und App-Routen"
$Credential = Get-Credential -Message "Gateway-Zugang eingeben"
$NetworkCredential = $Credential.GetNetworkCredential()
$CredentialBytes = [System.Text.Encoding]::UTF8.GetBytes(
    "$($NetworkCredential.UserName):$($NetworkCredential.Password)"
)
$Authorization = "Basic " + [Convert]::ToBase64String($CredentialBytes)
$Routes = @("/", "/crm/", "/wks/", "/files/")
foreach ($Route in $Routes) {
    try {
        $Response = Invoke-WebRequest `
            -Uri "$BaseUrl$Route" `
            -Headers @{ Authorization = $Authorization } `
            -UseBasicParsing `
            -MaximumRedirection 5 `
            -TimeoutSec 30
        Write-Host "$Route -> HTTP $($Response.StatusCode)"
    }
    catch {
        $Status = $_.Exception.Response.StatusCode.value__
        Write-Host "$Route -> FEHLER HTTP $Status"
    }
}
$Authorization = $null
$CredentialBytes = $null
$NetworkCredential = $null

Write-Host "Gateway-Grundschutz ist erreichbar. App-Routen mit Fehler müssen gegen die lokalen Ports geprüft werden."
