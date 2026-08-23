# Byblos AI Suite

Die Suite enthält eine Android-App sowie zwei austauschbare Servervarianten für einen gestreamten KI-Chat: ein schlankes Node.js/OpenAI-Backend und ein optionales Python-Backend auf Basis des hochgeladenen Google-Antigravity-SDKs. Alle Provider-Schlüssel bleiben vollständig außerhalb des APK.

## Projektstruktur

```text
android-app/   Jetpack Compose, Room, ViewModel, SSE
backend/       OpenAI Responses API, Validierung, Limits, Streaming
agent-backend/ Antigravity/Gemini, Skills, gleicher SSE-Vertrag
scripts/       lokale Prüfungen
.github/       CI für Backend und Android
docs/          Architektur, Sicherheit und Release-Checkliste
```

## Lokaler Start

### Backend

```bash
cd backend
cp .env.example .env
# OPENAI_API_KEY sicher in .env setzen; die Datei nie committen.
npm install
npm test
npm start
```

Standardmodell: `gpt-5-mini`. Der Server lauscht standardmäßig auf Port 3000.

### Optionales Antigravity-Agentenbackend

```bash
cd agent-backend
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# GEMINI_API_KEY sicher in .env setzen oder Vertex-ADC konfigurieren.
set -a; . ./.env; set +a
python -m byblos_agent.server
```

Der Agentenserver lauscht standardmäßig auf Port 3100 und implementiert denselben Android-SSE-Vertrag. Details und Sicherheitsgrenzen stehen in `agent-backend/README_DE.md` und `docs/BACKEND_SELECTION.md`.

### Android

1. `android-app/` in Android Studio öffnen.
2. JDK 17 und Android SDK 37 verwenden.
3. Backend starten.
4. Debug-App im Emulator starten. `10.0.2.2` verweist aus dem Emulator auf den Entwicklungsrechner.

```bash
cd android-app
./gradlew testDebugUnitTest lintDebug assembleDebug
```

Ein Release-Build verlangt eine reale HTTPS-Backend-URL und bricht bei der Platzhalterdomain ab:

```bash
./gradlew bundleRelease \
  -PBACKEND_BASE_URL=https://api.example.de/
```

## Lokale Gesamtprüfung

```bash
./scripts/verify-local.sh
RUN_ANDROID_BUILD=1 ./scripts/verify-local.sh
```

Der zweite Befehl benötigt verfügbare Gradle-Abhängigkeiten, JDK und Android SDK.

## Sicherheitsstatus

Das Paket ist ein gehärteter Prototyp für interne Tests, kein öffentlich freigabefertiges Produkt. Das Backend verweigert im Produktionsmodus den Start, solange weder der mindestens 32 Zeichen lange private Test-Token gesetzt noch die Testschranke durch echte Authentifizierung ersetzt wurde. Vor einem öffentlichen Release fehlen insbesondere echte Benutzeridentitäten, serverseitig persistente Quoten, Produktionsmonitoring sowie die rechtlichen und Google-Play-Prozesse. Details stehen in `docs/SECURITY.md` und `docs/RELEASE_CHECKLIST.md`.
