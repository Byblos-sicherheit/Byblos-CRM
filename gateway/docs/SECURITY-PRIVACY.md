# Sicherheit und Datenschutztechnik

## Umgesetzt

- Öffentlich nur 80/443; interne App-Ports bleiben geschlossen.
- Automatisches HTTPS mit persistentem Zertifikatsspeicher.
- Login vor allen App-Routen.
- Nur bcrypt-Hashes; keine Klartext-Passwörter in der Konfiguration.
- Persönliche Konten können einzeln gesperrt werden.
- Das ursprüngliche `Authorization`-Headerfeld wird nicht an Apps weitergegeben.
- Der authentifizierte Benutzer wird als `X-Authenticated-User` gesetzt.
- Container ohne zusätzliche Privilegien und mit reduzierten Linux-Capabilities.
- HSTS, MIME-Sniffing-Schutz, Referrer- und Berechtigungsrichtlinie.
- Rotierende Zugriffsprotokolle mit technischer Aufbewahrung von höchstens
  30 Tagen in der Gateway-Konfiguration.

## Grenzen

- HTTP Basic Authentication besitzt keine Mehrfaktor-Authentisierung, keine
  automatische Kontosperre und keine zentrale Sitzungsverwaltung.
- Caddy protokolliert aufgerufene URLs. Personenbezogene oder geheime Werte
  gehören deshalb nicht in URL-Queryparameter.
- Die Apps selbst benötigen eigene Rollen- und Berechtigungsprüfungen. Der
  Gateway-Login ersetzt keine App-Berechtigungen.
- `X-Authenticated-User` darf nur vertraut werden, wenn die App nicht parallel
  direkt aus fremden Netzen erreichbar ist.
- Der öffentliche Health-Endpunkt gibt ausschließlich `ok` aus.

Für einen größeren externen Benutzerkreis oder besonders schützenswerte Daten
ist ein Identity-Provider mit MFA (OIDC/SAML) die belastbarere Lösung.

## Passwortregeln

- Mindestens 14 Zeichen.
- Für jeden Dienst ein eigenes Passwort.
- Kein gemeinsames Teamkonto.
- Zugang sofort entfernen, wenn eine Person ausscheidet.

## Datenschutz

Vor Produktivbetrieb Verantwortlichkeit, Zweck, Rechtsgrundlage,
Aufbewahrungsfrist, Betroffenenrechte und gegebenenfalls
Auftragsverarbeitungsverträge für die hinterlegten Apps fachlich prüfen. Diese
technische Konfiguration ist keine juristische Konformitätsgarantie.
