# Backend-Auswahl

Die Android-App spricht ausschließlich den stabilen Vertrag `POST /v1/chat/stream` an. Dadurch kann sie ohne Quellcodeänderung gegen zwei unterschiedliche Servervarianten betrieben werden.

## Variante A: OpenAI Responses API

Pfad: `backend/`

- Laufzeit: Node.js 22+
- Credential: `OPENAI_API_KEY`
- Standardport: `3000`
- Zweck: direkter, schlanker ChatGPT-/OpenAI-Betrieb
- Agentenwerkzeuge: keine

## Variante B: Google Antigravity

Pfad: `agent-backend/`

- Laufzeit: Python 3.11+
- Credential: `GEMINI_API_KEY` oder Vertex Application Default Credentials
- Standardport: `3100`
- Zweck: agentische Laufzeit mit Skills und später erweiterbaren Werkzeugen
- Aktueller Sicherheitsmodus: nur `finish` ist aktiviert; Datei-, Shell-, Web-, MCP- und Subagentenfunktionen sind deaktiviert

## Android konfigurieren

OpenAI-Backend im Emulator:

```bash
./gradlew assembleDebug -PBACKEND_BASE_URL=http://10.0.2.2:3000/
```

Antigravity-Backend im Emulator:

```bash
./gradlew assembleDebug -PBACKEND_BASE_URL=http://10.0.2.2:3100/
```

Für Release-Builds ist HTTPS zwingend. Ein statischer `BACKEND_API_TOKEN` ist nur eine interne Testschranke und keine echte Nutzeranmeldung.

## Entscheidung

Für den ersten produktiven Rollout ist das OpenAI-Backend die kleinere und leichter auditierbare Variante. Das Antigravity-Backend sollte erst dann aktiviert werden, wenn ein konkreter Agentenbedarf besteht und jeder zusätzliche Toolzugriff separat freigegeben, protokolliert und getestet wurde.
