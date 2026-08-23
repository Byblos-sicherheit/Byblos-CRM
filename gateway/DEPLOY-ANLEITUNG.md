# Deployment-Anleitung – Byblos Server Gateway

## 1. Ergebnis

Das Gateway veröffentlicht vier vorhandene lokale Anwendungen unter einer
HTTPS-Domain und verlangt vor jedem App-Zugriff einen persönlichen
Benutzernamen samt Passwort:

| URL | Anwendung | Interne Zielvariable |
|---|---|---|
| `/` | LexAI-Pro | `LEXAI_UPSTREAM` |
| `/crm/` | CRM | `CRM_UPSTREAM` |
| `/wks/` | WKS-Pro | `WKS_UPSTREAM` |
| `/files/` | FileBrowser | `FILES_UPSTREAM` |

Caddy beschafft und erneuert das öffentliche TLS-Zertifikat automatisch. Ein
bereits vorhandenes Zertifikat und ein privater Schlüssel werden nicht benötigt.

## 2. Voraussetzungen auf dem Server-PC

- Windows 10/11 oder Linux
- Docker Engine bzw. Docker Desktop mit Docker Compose
- Die vier Apps laufen bereits und sind auf dem Server-PC über ihre lokalen
  Ports erreichbar
- Der PC erhält im lokalen Netzwerk eine feste IPv4-Adresse oder eine
  DHCP-Reservierung
- Kein anderer Dienst belegt TCP-Port 80 oder 443

Prüfung in PowerShell:

```powershell
docker --version
docker compose version
Get-NetTCPConnection -LocalPort 80,443 -ErrorAction SilentlyContinue
```

Wenn die letzte Zeile einen anderen Webserver zeigt, diesen nicht blind
beenden. Zuerst klären, ob er weiter benötigt wird.

## 3. Installation

### Windows

1. Ordner `ByblosServer-Apps\gateway` auf den Server-PC kopieren.
2. Docker Desktop starten.
3. `SETUP-WINDOWS.cmd` doppelt anklicken.
4. Für jede App die tatsächlich lokal funktionierende Adresse eintragen.
   Beispiele wie `host.docker.internal:3000` sind nur Startwerte und müssen
   mit den realen Ports übereinstimmen.
5. Einen persönlichen Benutzernamen und ein starkes Passwort anlegen.

Das Setup erzeugt `.env`, schreibt nur einen bcrypt-Passwort-Hash in
`config\users.caddy`, validiert die Konfiguration und startet das Gateway.

### Linux

```bash
cd ByblosServer-Apps/gateway
cp .env.example .env
nano .env
chmod +x scripts/*.sh
./scripts/add-user.sh adminname
./scripts/validate.sh
docker compose up -d
```

## 4. Interne App-Adressen prüfen

Auf dem Server-PC müssen die Apps vor dem externen Deployment lokal antworten:

```powershell
curl.exe -I http://localhost:3000
curl.exe -I http://localhost:3001
curl.exe -I http://localhost:3002
curl.exe -I http://localhost:8080
```

Die Portnummern durch die tatsächlichen Ports ersetzen. Falls eine App nur an
`127.0.0.1` gebunden ist und Docker sie nicht erreicht, die App kontrolliert
auf die LAN-/Docker-Schnittstelle binden oder in dasselbe Compose-Netz
verschieben. Den App-Port nicht im Router freigeben.

## 5. Windows-Firewall

PowerShell als Administrator öffnen:

```powershell
cd C:\PFAD\ZU\ByblosServer-Apps\gateway
powershell.exe -ExecutionPolicy Bypass -File .\scripts\open-firewall.ps1
```

Das Skript öffnet TCP 80, TCP 443 und UDP 443 ausschließlich im privaten
Windows-Netzwerkprofil. TCP 80 und TCP 443 sind für Zertifikat und HTTPS
entscheidend. UDP 443 ermöglicht HTTP/3, ist aber für die Zertifikatsausstellung
nicht zwingend.

## 6. Feste lokale IP

Im Router eine DHCP-Reservierung für die MAC-Adresse des Server-PCs setzen.
Beispiel: Der PC erhält dauerhaft `192.168.178.50`. Keine IP aus einem fremden
Netz übernehmen; die echte Router-Konfiguration verwenden.

Prüfen:

```powershell
ipconfig
```

## 7. Portweiterleitungen im Router

Folgende Regeln auf die feste lokale IP des Server-PCs setzen:

| Außen | Protokoll | Innen | Ziel |
|---:|---|---:|---|
| 80 | TCP | 80 | Server-PC |
| 443 | TCP | 443 | Server-PC |
| 443 | UDP | 443 | Server-PC, optional für HTTP/3 |

Keine Weiterleitungen für die App-Ports 3000, 3001, 3002 oder 8080 anlegen.
Damit bleiben die Apps ausschließlich hinter Login und Caddy erreichbar.

Bei DS-Lite/CGNAT ist eine klassische IPv4-Portweiterleitung möglicherweise
nicht erreichbar. Dann beim Internetanbieter eine öffentliche IPv4-Adresse
beantragen oder einen Tunnel/VPN-Zugang verwenden.

## 8. DNS setzen

Beim DNS-Anbieter der Zone `byblos-sicherheit.com`:

| Typ | Name | Wert | TTL |
|---|---|---|---|
| A | `ai` | öffentliche IPv4-Adresse des Routers | 300 oder automatisch |

Nur wenn ein funktionierender öffentlicher IPv6-Zugang samt Firewall-Regel
vorhanden ist, zusätzlich einen AAAA-Record setzen. Ein falscher AAAA-Record
kann dazu führen, dass ein Teil der Geräte die Seite nicht erreicht.

Prüfen:

```powershell
Resolve-DnsName ai.byblos-sicherheit.com
```

Der A-Record muss die öffentliche IPv4-Adresse des Internetanschlusses liefern.

## 9. Start und Zertifikatsausstellung

```powershell
cd C:\PFAD\ZU\ByblosServer-Apps\gateway
docker compose up -d
docker compose ps
docker compose logs --tail 100 gateway
```

Voraussetzungen für ein öffentlich vertrauenswürdiges Zertifikat:

- A/AAAA-Record zeigt auf den Anschluss
- TCP 80 und 443 erreichen Caddy
- Caddy-Datenvolume ist beschreibbar und bleibt erhalten
- Domain steht korrekt in `.env`

## 10. Externer Test

Nicht nur im eigenen WLAN testen. Am Mobiltelefon WLAN ausschalten und über
Mobilfunk aufrufen:

```text
https://ai.byblos-sicherheit.com/healthz
```

Erwartung: `ok`.

Danach:

```text
https://ai.byblos-sicherheit.com/
https://ai.byblos-sicherheit.com/crm/
https://ai.byblos-sicherheit.com/wks/
https://ai.byblos-sicherheit.com/files/
```

Erwartung: Browser fragt nach Benutzername und Passwort. Ein Test ohne Zugang
muss HTTP 401 liefern:

```powershell
curl.exe -I https://ai.byblos-sicherheit.com/
```

Vollständiger Test:

```powershell
powershell.exe -File .\scripts\test-gateway.ps1
```

## 11. Weitere Benutzer

```powershell
powershell.exe -File .\scripts\add-user.ps1 -Username vorname.nachname
docker compose restart gateway
```

Zugang entfernen:

```powershell
powershell.exe -File .\scripts\remove-user.ps1 -Username vorname.nachname
docker compose restart gateway
```

Jede Person erhält einen eigenen Zugang. Gemeinsame Konten verhindern eine
nachvollziehbare Sperrung einzelner Personen.

## 12. App-Betrieb unter Unterpfaden

Caddy entfernt `/crm`, `/wks` und `/files`, bevor es die Anfrage an die jeweilige
App weiterleitet. Die Apps müssen trotzdem ihre erzeugten Links, Cookies,
WebSocket-Pfade und Weiterleitungen für den jeweiligen öffentlichen Basispfad
unterstützen.

Erforderliche App-Basiswerte:

| App | Öffentlicher Basispfad |
|---|---|
| CRM | `/crm/` |
| WKS-Pro | `/wks/` |
| FileBrowser | `/files/` |

Wenn nach dem Login nur HTML erscheint, aber CSS/JavaScript fehlen, liegt
wahrscheinlich eine falsche Base-URL in der jeweiligen App vor. Ohne Quellcode
und reale Startkonfiguration der drei Apps ist diese App-spezifische Anpassung
nicht verifizierbar.

## 13. Dynamische öffentliche IP

Wenn sich die öffentliche IP ändert, muss der DNS-A-Record automatisch
aktualisiert werden. Die konkrete Umsetzung hängt vom DNS-Anbieter bzw. Router
ab. Vor Einbau eines DDNS-Containers werden folgende Daten benötigt:

- DNS-Anbieter
- API-Verfügbarkeit des DNS-Anbieters
- verwendeter Router
- öffentliche IPv4 vorhanden oder DS-Lite/CGNAT

API-Tokens gehören ausschließlich in eine nicht veröffentlichte `.env`- oder
Secret-Datei und nie in diese Anleitung, den Chat oder das ZIP.

## 14. Altes exponiertes Zertifikat

Ein privater TLS-Schlüssel, der in einem Chat oder anderen nicht kontrollierten
Kanal übertragen wurde, ist als kompromittiert zu behandeln. Das zugehörige
Zertifikat beim bisherigen Aussteller widerrufen und den Schlüssel löschen.
Caddy erstellt danach selbstständig ein neues Schlüsselpaar und Zertifikat.
