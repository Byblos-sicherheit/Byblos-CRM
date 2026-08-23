# Änderungsprotokoll

## 2026-07-27 – gehärtete Übergabeversion

### Backend

- Nicht belegten Modellplatzhalter durch `gpt-5-mini` ersetzt.
- OpenAI-Anfragen mit `store: false`, Ausgabetokenlimit, `safety_identifier` und `prompt_cache_key` ergänzt.
- Request-IDs, strukturierte Logs, Readiness-Endpunkt und kontrollierte SSE-Fehler ergänzt.
- Eingabe-, Header-, Payload-, Parallelitäts-, Rate-Limit- und Timeout-Prüfungen erweitert.
- Client-Abbruch und kontrolliertes Herunterfahren verbessert.
- Docker-Container auf nicht privilegierten Betrieb, Read-only-Dateisystem und reduzierte Capabilities vorbereitet.
- Backend-Testumfang auf 15 Tests erweitert.

### Android

- Stabile pseudonyme Installations-ID und Request-ID ergänzt.
- Stream-Abbruch, expliziten Zustand `CANCELLED` und Wiederherstellung verwaister Nachrichten ergänzt.
- Room-Schreiblast während des Streamings gedrosselt.
- Deutsch und Arabisch als Ressourcenlokalisierung ergänzt.
- Rohfehler aus dem Backend aus der Benutzeroberfläche entfernt.
- Release-Build-Sperre für HTTP- und Platzhalter-Backend-URLs ergänzt.
- Repository- und ViewModel-Tests an die neue Abbruchlogik angepasst.

### Delivery

- GitHub-Actions-CI für Backend und Android ergänzt.
- Dependabot-Konfiguration ergänzt.
- Lokales Verifikationsskript mit Secret-, Syntax- und Formatprüfungen ergänzt.
- Architektur-, Sicherheits- und Release-Dokumentation auf Deutsch ergänzt.

## 0.3.0

- Optionales Python-Agentenbackend auf Basis des hochgeladenen Google-Antigravity-SDKs ergänzt.
- Bestehenden Android-SSE-Vertrag für beide Backendvarianten vereinheitlicht.
- Hochgeladenen `universal-programmer-mind`-Skill als serverseitigen Agenten-Skill eingebunden.
- Tooloberfläche auf das erforderliche `finish`-Werkzeug reduziert; Shell, Dateien, Web, MCP und Subagenten deaktiviert.
- Neun providerunabhängige Python-Tests, Python-CI und Dependabot-Pip-Konfiguration ergänzt.
- Backend-Auswahl und Sicherheitsgrenzen dokumentiert.
