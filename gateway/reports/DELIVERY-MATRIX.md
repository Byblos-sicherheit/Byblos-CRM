# Liefermatrix

| ID | Modul | Abnahmekriterium | Priorität | Gewicht | Status | Nachweis |
|---|---|---|---|---:|---|---|
| GW-01 | HTTPS | Domain ist für automatisches TLS konfiguriert | Muss | 12 | implementiert | `config/Caddyfile`, `compose.yaml` |
| GW-02 | Login | Alle App-Routen verlangen bcrypt-Login | Muss | 15 | implementiert | `config/Caddyfile`, Benutzer-Skripte |
| GW-03 | Routing | `/`, `/crm/`, `/wks/`, `/files/` sind getrennt geroutet | Muss | 15 | implementiert | `config/Caddyfile` |
| GW-04 | Secrets | Keine produktiven Passwörter/Schlüssel im Paket | Muss | 10 | verifiziert | Secret-Scan im Testbericht |
| GW-05 | Container | Reproduzierbarer Compose-Start mit persistenten Volumes | Muss | 10 | implementiert | `compose.yaml` |
| GW-06 | Windows | Setup, Firewall, Benutzerverwaltung vorhanden | Muss | 10 | implementiert | PowerShell-/CMD-Skripte |
| GW-07 | Betrieb | Start, Update, Logs und Fehlerdiagnose dokumentiert | Soll | 8 | verifiziert | `docs/OPERATIONS.md` |
| GW-08 | Backup | Backup und Restore dokumentiert | Soll | 6 | verifiziert | `docs/BACKUP-RESTORE.md`, statische Dokumentenprüfung |
| GW-09 | Sicherheit | Header, Credential-Abschirmung und Grenzen dokumentiert | Muss | 8 | implementiert | `config/Caddyfile`, Sicherheitsnotizen |
| GW-10 | Außenprüfung | DNS, Router, echtes Zertifikat und Apps extern geprüft | Muss | 6 | blockiert | Server-/Routerzugriff erforderlich |

Gesamtgewicht: 100.

## Fortschritt

- Implementierung: **94 %**  
  Summe der Gewichte mit Status `implementiert` oder `verifiziert`: 94 von 100.
- Verifizierung: **24 %**  
  Summe der Gewichte mit Status `verifiziert`: 24 von 100.

Die restlichen Prüfungen erfordern Docker sowie den tatsächlichen Server-,
Router-, DNS- und App-Zugriff.
