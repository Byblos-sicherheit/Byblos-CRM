# TradingView MCP Setup

Connect TradingView live market data to Claude Code or any MCP-compatible AI assistant.

**Requirement:** TradingView Essential subscription or higher (free/trial plans are excluded).

---

## Option A — Official TradingView MCP (Essential+)

The official MCP endpoint is at `https://mcp.tradingview.com/mcp`.

### Claude Code setup (`~/.claude/mcp.json` or `.mcp.json` in project root)

```json
{
  "mcpServers": {
    "tradingview": {
      "url": "https://mcp.tradingview.com/mcp",
      "transport": "http"
    }
  }
}
```

Docs: `https://www.tradingview.com/mcp/docs`

### What it provides
- Real-time and historical chart data
- Technical indicators and screener queries
- Ticker search and symbol resolution
- Pine Script access (where plan allows)

---

## Option B — Desktop Bridge (free alternative, requires TradingView Desktop)

Community server `harshil1502/tradingview-mcp` bridges Claude to a locally running TradingView Desktop app via Chrome DevTools Protocol.

### Install

```bash
npm install -g tradingview-mcp
```

### Launch TradingView Desktop with remote debugging

```
tradingview --remote-debugging-port=9222
```

### Add to `.mcp.json`

```json
{
  "mcpServers": {
    "tradingview": {
      "command": "tradingview-mcp",
      "env": {
        "TV_MCP_PORT": "9222"
      }
    }
  }
}
```

Restart Claude Code after adding.

---

## Option C — Scraper-based (Python, no subscription needed)

Community server `bidouilles/mcp-tradingview-server` — pulls data via the `tradingview_scraper` library.

Requirements: Python 3.11+, `uv`

```bash
# Add to claude MCP config
claude mcp add tradingview -- uvx --from /path/to/mcp-tradingview-server mcp-tradingview
```

---

## Notes

- Options B and C are community-maintained, not official. Verify their licenses and maintenance status before using in production.
- For real financial data in a production context, Option A (official) is the correct choice.
- Never commit TradingView session tokens or API credentials to git.
