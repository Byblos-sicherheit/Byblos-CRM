# Verifizierungsbericht

Stand: 28. Juli 2026

## Tatsächlich in dieser Umgebung ausgeführt

- Node/OpenAI-Backend mit Node Test Runner: **15 bestanden, 0 fehlgeschlagen**.
- Python/Antigravity-Agentenbackend mit `unittest`: **15 bestanden, 0 fehlgeschlagen**.
- Die Python-Tests prüfen API-Vertrag, CORS, Token-Schranke, Rate Limit, Timeout, Requestvalidierung, Promptaufbau, Streaming und Abbruch mit Fake-Providern.
- Syntaxprüfung aller Node-Backend-Einstiegsmodule: bestanden.
- Python-Bytecode-Kompilierung für Agentenbackend und Tests: bestanden.
- XML-, JSON- und TOML-Parsing: bestanden.
- Shell-Syntaxprüfung des Gradle-Bootstrap-Skripts: bestanden.
- Suche nach eingebetteten OpenAI-Schlüsselmustern: kein Treffer.
- Suche nach dem früheren nicht belegten Modellplatzhalter: kein Treffer nach Bereinigung.

## Nicht ausgeführt

- Android-Unit-Tests, Lint, Compose-Tests und Room-Instrumentationstests.
- APK- oder AAB-Erstellung.
- Echter OpenAI-API-Aufruf.
- Echter Gemini-/Vertex-/Antigravity-Aufruf.
- Installation des OpenAI-NPM-Pakets und Erzeugung eines `package-lock.json`; der Registry-Zugriff war in früheren Prüfungen blockiert.
- Installation des veröffentlichten `google-antigravity`-Wheels. Im lokalen Python-Environment fehlen `google.antigravity` und `google.genai`.

## Technische Blocker

Die Build-Umgebung konnte in früheren Läufen `services.gradle.org` und Paketregistries nicht zuverlässig per DNS auflösen. Außerdem war kein vollständiges Android SDK über `ANDROID_HOME` verfügbar. Der hochgeladene Antigravity-Quellcode weist selbst darauf hin, dass das Repository allein nicht genügt und die plattformspezifische Runtime aus dem veröffentlichten PyPI-Wheel benötigt wird.

Ein Android- oder echter Provider-Erfolg wird daher ausdrücklich **nicht** behauptet.

## Nächster reproduzierbarer Prüfpunkt

Auf einem Rechner oder in GitHub Actions mit Netzwerk, JDK 17 und Android SDK 37:

```bash
./scripts/verify-local.sh
RUN_ANDROID_BUILD=1 ./scripts/verify-local.sh
```

Antigravity-Laufzeit prüfen:

```bash
cd agent-backend
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
PYTHONPATH=. python -m unittest discover -s tests -v
python -c "import google.antigravity"
```

Danach mit einem isolierten Testprojekt und begrenztem Budget einen echten Provider-Smoke-Test durchführen. Credentials dürfen nicht in Logs oder das Repository gelangen.

Android-Instrumentationstests:

```bash
cd android-app
./gradlew connectedDebugAndroidTest
```
