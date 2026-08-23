# Byblos Server Gateway

Zentraler HTTPS-Reverse-Proxy für:

| Öffentlicher Pfad | Ziel |
|---|---|
| `https://ai.byblos-sicherheit.com/` | LexAI-Pro |
| `https://ai.byblos-sicherheit.com/crm/` | CRM |
| `https://ai.byblos-sicherheit.com/wks/` | WKS-Pro |
| `https://ai.byblos-sicherheit.com/files/` | FileBrowser |

Alle App-Pfade sind durch HTTP Basic Authentication geschützt. Der technische
Endpunkt `/healthz` ist absichtlich ohne Anmeldung erreichbar und gibt nur
`ok` zurück.

## Windows-Schnellstart

1. Docker Desktop installieren und starten.
2. `SETUP-WINDOWS.cmd` doppelt anklicken.
3. Die tatsächlichen lokalen App-Adressen/Ports eintragen.
4. Einen ersten Benutzer mit einem starken, nur hierfür verwendeten Passwort anlegen.
5. Windows-Firewall als Administrator mit `scripts\open-firewall.ps1` freigeben.
6. Router und DNS nach `DEPLOY-ANLEITUNG.md` konfigurieren.

Die vollständige Betriebsanleitung steht in [DEPLOY-ANLEITUNG.md](DEPLOY-ANLEITUNG.md).

## Nachweise

- [Testbericht](reports/TEST-REPORT.md)
- [Liefermatrix](reports/DELIVERY-MATRIX.md)
- [Offene Punkte](reports/OPEN-ITEMS.md)
- [Sicherheits- und Datenschutzhinweise](docs/SECURITY-PRIVACY.md)
