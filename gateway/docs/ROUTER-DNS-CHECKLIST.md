# Router- und DNS-Checkliste

- [ ] Server-PC hat eine feste lokale IP/DHCP-Reservierung.
- [ ] Docker Desktop läuft nach Neustart automatisch.
- [ ] TCP 80 ist im privaten Windows-Firewallprofil erlaubt.
- [ ] TCP 443 ist im privaten Windows-Firewallprofil erlaubt.
- [ ] Router leitet TCP 80 auf den Server-PC weiter.
- [ ] Router leitet TCP 443 auf den Server-PC weiter.
- [ ] Optional: UDP 443 ist für HTTP/3 freigegeben und weitergeleitet.
- [ ] DNS-A-Record `ai.byblos-sicherheit.com` zeigt auf die öffentliche IPv4.
- [ ] Kein falscher/unerreichbarer AAAA-Record vorhanden.
- [ ] Öffentliche IPv4 ist vorhanden; CGNAT/DS-Lite wurde ausgeschlossen.
- [ ] Bei wechselnder IP ist DDNS beim Router/DNS-Anbieter eingerichtet.
- [ ] Test über Mobilfunk liefert `/healthz` = `ok`.
- [ ] Zugriff ohne Login liefert HTTP 401.
- [ ] Alle vier App-Routen wurden nach Login geprüft.
- [ ] Altes exponiertes Zertifikat wurde widerrufen.
- [ ] Verschlüsseltes Backup von `.env`, Benutzerdatei und Caddy-Daten erstellt.
