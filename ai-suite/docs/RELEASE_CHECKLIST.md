# Release-Checkliste

## Backend

- [ ] Produktionskonto und Projekt in OpenAI festgelegt.
- [ ] `OPENAI_API_KEY` in einem Secret Manager gespeichert.
- [ ] `OPENAI_MODEL`, Tokenlimit und Budgetgrenzen festgelegt.
- [ ] Echte Authentifizierung und serverseitige Autorisierung aktiviert.
- [ ] Verteiltes Rate Limiting und Benutzerquoten aktiviert.
- [ ] HTTPS-Domain, Health-/Readiness-Probes und Monitoring eingerichtet.
- [ ] Backup-, Incident- und Schlüsselrotationsverfahren dokumentiert.
- [ ] `npm ci`, Tests und Syntaxprüfung in CI erfolgreich.

## Android

- [ ] `BACKEND_BASE_URL` ist eine reale HTTPS-URL.
- [ ] Kein statischer Test-Token im öffentlichen Release.
- [ ] Unit Tests, Lint und Debug-Build erfolgreich.
- [ ] Room-Migrationstest auf Emulator/Gerät erfolgreich.
- [ ] Compose-Instrumentationstest erfolgreich.
- [ ] Release-Build mit R8 auf zentralen Nutzerpfaden geprüft.
- [ ] Upload-Key und Play App Signing eingerichtet.
- [ ] AAB erstellt und im internen Testkanal installiert.
- [ ] Tests auf API 23 bis API 37, kleinen/großen Displays, RTL und Dark Mode durchgeführt.

## Recht und Store

- [ ] Datenschutzerklärung und Anbieterkennzeichnung veröffentlicht.
- [ ] Zweck, Umfang und Empfänger der KI-Datenverarbeitung dokumentiert.
- [ ] Google-Play-Data-Safety-Angaben geprüft.
- [ ] Kontolöschung und Datenlöschung umgesetzt, sofern Konten existieren.
- [ ] Supportkontakt, Screenshots, Icon, Beschreibung und Inhaltsklassifizierung fertig.
- [ ] Interner/geschlossener Test und gestufter Rollout geplant.
