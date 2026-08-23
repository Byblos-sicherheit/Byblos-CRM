# Offene Punkte

## Extern blockiert

1. Tatsächliche Ports/Adressen von LexAI-Pro, CRM, WKS-Pro und FileBrowser
   eintragen und jede App lokal prüfen.
2. Router-Portweiterleitung für TCP 80/443 setzen.
3. DNS-A-Record für `ai.byblos-sicherheit.com` setzen.
4. Prüfen, ob öffentliche IPv4 oder DS-Lite/CGNAT vorliegt.
5. Falls die öffentliche IP wechselt: DNS-Anbieter und Router feststellen,
   danach passende DDNS-Lösung konfigurieren.
6. Altes im Chat übertragenes TLS-Zertifikat beim bisherigen Aussteller
   widerrufen.
7. Externen Mobilfunk-Test und Test aller App-Routen durchführen.

## App-spezifisch nicht verifiziert

- Unterpfad-/Base-URL-Unterstützung der drei Apps unter `/crm/`, `/wks/` und
  `/files/`.
- App-interne Rollen und Berechtigungen.
- WebSocket-, Cookie- und Redirect-Verhalten unter den Unterpfaden.

Unzureichende Daten zur Verifizierung: Quellcode, Startbefehle und reale
Portbelegung der vier Apps sowie Router- und DNS-Zugangsdaten liegen nicht vor.
