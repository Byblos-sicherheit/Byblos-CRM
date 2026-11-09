# MCP Endpoint & Agent-Reach Integration

## WordPress MCP Endpoint

Der Byblos-MCP-Endpoint ist unter folgender URL erreichbar:

```
https://byblos-sicherheit.de/wp-json/easy-mcp-ai/v1/mcp
```

### Claude Code konfigurieren

Erstelle eine `.mcp.json`-Datei im Projektverzeichnis (nicht ins Git einchecken, da sie Secrets enthalten kann):

```json
{
  "mcpServers": {
    "wordpress": {
      "type": "http",
      "url": "https://byblos-sicherheit.de/wp-json/easy-mcp-ai/v1/mcp",
      "headers": {
        "Authorization": "Bearer ${BYBLOS_MCP_API_KEY}"
      }
    }
  }
}
```

Oder per CLI (empfohlen — schreibt in `~/.claude.json`):

```bash
claude mcp add --transport http wordpress \
  https://byblos-sicherheit.de/wp-json/easy-mcp-ai/v1/mcp \
  --header "Authorization: Bearer <DEIN_API_KEY>"
```

> **Wichtig**: Den API-Schlüssel niemals direkt im Code oder in Git speichern.
> Verwende stets die Umgebungsvariable `BYBLOS_MCP_API_KEY`.

### Umgebungsvariablen

| Variable | Beschreibung |
|----------|-------------|
| `BYBLOS_MCP_API_KEY` | API-Schlüssel für den MCP-Endpoint |
| `BYBLOS_MCP_URL` | (Optional) Abweichende Endpoint-URL |

Beispiel `.env`-Datei (nicht einchecken!):

```env
BYBLOS_MCP_API_KEY=sk_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

---

## Agent-Reach Integration

[Agent-Reach](https://github.com/Panniantong/Agent-Reach) gibt KI-Agenten Lese-/Suchzugang zu 13 Internet-Plattformen.

### Installation

```bash
# Aus dem lokalen Klon
pip install -e /home/user/Agent-Reach

# Oder direkt von PyPI
pip install agent-reach
```

### CRM-Routen (nach `register_mcp_routes(app)`)

| Endpoint | Methode | Beschreibung |
|----------|---------|-------------|
| `/api/mcp/health` | GET | MCP-Endpoint-Status |
| `/api/mcp/tools` | GET | Verfügbare MCP-Tools auflisten |
| `/api/mcp/call` | POST | MCP-Tool aufrufen (`{"tool": "...", "arguments": {...}}`) |
| `/api/agent-reach/search?q=...` | GET | Multi-Kanal-Suche via Agent-Reach |
| `/api/agent-reach/read?url=...` | GET | URL über Agent-Reach lesen |

### Integration in app.py

```python
from extensions_v2_mcp_integration import register_mcp_routes

# Nach app = Flask(__name__):
register_mcp_routes(app)
```

---

## Sicherheitshinweise

- API-Schlüssel **niemals** hartcodieren oder einchecken
- `.env`-Dateien in `.gitignore` aufnehmen
- Secrets regelmäßig rotieren
- MCP-Endpoint nur über HTTPS ansprechen
