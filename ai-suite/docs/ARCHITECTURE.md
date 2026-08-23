# Architektur

## Systemgrenze

```text
Android-App
  -> HTTPS + SSE
  -> genau eine Backend-Variante
       A) Node.js -> OpenAI Responses API
       B) Python -> Google Antigravity -> Gemini / Vertex
```

Provider-Credentials bleiben ausschließlich im gewählten Backend. Die Android-App kennt nur die Backend-URL und eine pseudonyme Installations-ID. Ein optionaler statischer Test-Token dient ausschließlich privaten Tests und ist keine belastbare Benutzerauthentifizierung.

## Stabiler Android-Backend-Vertrag

Die App sendet an `POST /v1/chat/stream`:

```json
{
  "conversationId": "...",
  "messages": [
    {"role": "user", "content": "..."}
  ]
}
```

Beide Backends liefern SSE-Ereignisse:

- `started`
- `delta`
- `completed`
- `error`

Dadurch bleibt die Android-Schicht providerneutral. Ein Providerwechsel erfordert nur eine andere `BACKEND_BASE_URL`, nicht den Einbau eines Provider-Schlüssels in die App.

## Android

- **UI:** Jetpack Compose, lokalisierte deutsche und arabische Ressourcen.
- **State:** `ChatViewModel` mit `StateFlow` und einem expliziten Send-Job.
- **Datenzugriff:** `ChatRepository` kapselt Netzwerk und Room.
- **Lokal:** Room speichert Nachrichten und Zustände wie `SENDING`, `COMPLETED`, `FAILED` und `CANCELLED`.
- **Remote:** OkHttp SSE verarbeitet `started`, `delta`, `completed` und `error`.
- **Abbruch:** Ein Benutzerabbruch beendet den Netzwerkstream und persistiert den bisherigen Text als abgebrochen.
- **Wiederanlauf:** Beim App-Start werden verwaiste `SENDING`-Einträge als fehlgeschlagen markiert.

## Node/OpenAI-Backend

- Validiert Content-Type, Payloadgröße, Rollen, Nachrichtenanzahl und Textlänge.
- Begrenzt Anfragen pro Client-ID und gleichzeitig aktive Streams.
- Erzeugt oder übernimmt eine validierte Request-ID und reicht sie als `X-Client-Request-Id` an OpenAI weiter.
- Nutzt `store: false`, ein Ausgabetokenlimit und gehashte pseudonyme Kennungen.
- Schreibt strukturierte Betriebslogs ohne Prompt- oder Antwortinhalt.
- Beendet OpenAI-Anfragen bei Client-Abbruch oder Timeout.

## Python/Antigravity-Backend

- Implementiert denselben HTTP-/SSE-Vertrag wie das Node-Backend.
- Lädt optional dateisystembasierte Agent Skills. Der mitgelieferte Skill ist `universal-programmer-mind`.
- Verwendet nur das für die Antwortausgabe erforderliche `finish`-Werkzeug.
- Deaktiviert Datei-, Shell-, Web-, Bild-, MCP- und Subagentenfunktionen.
- Erstellt pro Request ein isoliertes Laufzeitverzeichnis.
- Unterstützt Gemini Developer API oder Vertex/Enterprise-Agent-Platform.
- Setzt kein Modell fest, solange `ANTIGRAVITY_MODEL` nicht ausdrücklich konfiguriert wurde.
- Bricht die Provider-Antwort bei Client-Trennung oder Stream-Timeout ab.

## Bewusste Grenzen

- Keine echte Benutzerverwaltung.
- Keine serverseitige Gesprächsdatenbank.
- In-Memory-Rate-Limitierung ist nicht clusterfähig.
- Keine Push-Benachrichtigungen und kein Offline-Queueing.
- Kein fertiges Billing- oder Mandantenmodell.
- Antigravity ist in dem hochgeladenen Quellstand als Alpha-Version `0.1.8` gekennzeichnet und daher nicht automatisch produktionsreif.
