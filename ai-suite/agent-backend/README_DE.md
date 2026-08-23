# Optionales Antigravity-Agentenbackend

Dieses Backend ist eine optionale Alternative zum vorhandenen Node/OpenAI-Backend. Es implementiert denselben HTTP- und SSE-Vertrag, sodass die Android-App nur eine andere `BACKEND_BASE_URL` benötigt.

## Sicherheitsgrenze

Das SDK läuft ausschließlich auf dem Server. Weder `GEMINI_API_KEY` noch Google-Cloud-Zugangsdaten gehören in die APK. Alle eingebauten Agentenwerkzeuge außer dem für die Antwortausgabe erforderlichen `finish`-Werkzeug sowie sämtliche Subagenten sind in dieser Variante deaktiviert. Der mitgelieferte Skill liefert nur Entwicklungswissen; er erhält keinen Shell- oder Dateizugriff.

## Voraussetzungen

- Python 3.11 oder neuer
- Das veröffentlichte PyPI-Paket `google-antigravity==0.1.8`; der hochgeladene Quellcode allein enthält laut dessen README nicht die erforderliche plattformspezifische Runtime-Binärdatei
- Entweder `GEMINI_API_KEY` oder Vertex/Enterprise-Agent-Platform mit Application Default Credentials

## Lokaler Start

```bash
cd agent-backend
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
set -a; . ./.env; set +a
python -m byblos_agent.server
```

Android-Debug-URL für den Emulator:

```text
http://10.0.2.2:3100/
```

## Tests ohne Providerzugriff

```bash
PYTHONPATH=. python -m unittest discover -s tests -v
```

Diese Tests verwenden Fake-Provider. Sie prüfen API-Vertrag, CORS, Limits, Timeout, Abbruch und Streaming, nicht die echte Gemini- oder Antigravity-Verbindung.

## Provider wählen

- Bestehendes OpenAI-Backend: Port 3000, `OPENAI_API_KEY`
- Antigravity-Agentenbackend: Port 3100, `GEMINI_API_KEY` oder Vertex-ADC

Nur ein Backend muss von der Android-App angesprochen werden. Beide gleichzeitig sind nur für Vergleichstests nötig.


## Reifegrad

Der hochgeladene SDK-Quellstand bezeichnet Version `0.1.8` als Alpha. Dieses Backend ist daher eine isolierte Evaluierungsoption, nicht automatisch die bevorzugte Produktionsvariante.
