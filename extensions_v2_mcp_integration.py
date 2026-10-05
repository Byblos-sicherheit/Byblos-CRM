"""
extensions_v2_mcp_integration.py — Byblos CRM MCP & Agent-Reach Integration
==============================================================================
Integriert:
  - WordPress MCP Endpoint (https://byblos-sicherheit.de/wp-json/easy-mcp-ai/v1/mcp)
  - Agent-Reach: Multi-Channel-Suche und KI-Agent-Routing

Umgebungsvariablen:
  BYBLOS_MCP_API_KEY   — API-Schlüssel für den WordPress-MCP-Endpoint
  BYBLOS_MCP_URL       — (optional) MCP-Endpoint-URL (Standard: byblos-sicherheit.de)

Konfiguration (.mcp.json im Projektverzeichnis, für Claude Code):
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
"""

from __future__ import annotations

import os
import json
import logging
from typing import Any, Dict, Optional

try:
    import requests
    REQUESTS_OK = True
except ImportError:
    REQUESTS_OK = False

logger = logging.getLogger(__name__)

MCP_DEFAULT_URL = "https://byblos-sicherheit.de/wp-json/easy-mcp-ai/v1/mcp"


def _get_mcp_url() -> str:
    return os.environ.get("BYBLOS_MCP_URL", MCP_DEFAULT_URL)


def _get_mcp_headers() -> Dict[str, str]:
    api_key = os.environ.get("BYBLOS_MCP_API_KEY", "")
    headers: Dict[str, str] = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    return headers


# ──────────────────────────────────────────────────────────────
# MCP-Endpoint-Client
# ──────────────────────────────────────────────────────────────

class ByblosMCPClient:
    """Leichtgewichtiger HTTP-Client für den WordPress-MCP-Endpoint."""

    def __init__(
        self,
        url: Optional[str] = None,
        api_key: Optional[str] = None,
        timeout: int = 30,
    ) -> None:
        self.url = url or _get_mcp_url()
        self._api_key = api_key or os.environ.get("BYBLOS_MCP_API_KEY", "")
        self.timeout = timeout

    @property
    def _headers(self) -> Dict[str, str]:
        h: Dict[str, str] = {"Content-Type": "application/json"}
        if self._api_key:
            h["Authorization"] = f"Bearer {self._api_key}"
        return h

    def call(self, method: str, params: Optional[Dict[str, Any]] = None) -> Any:
        """Ruft eine MCP-Methode auf und gibt das Ergebnis zurück."""
        if not REQUESTS_OK:
            raise RuntimeError("requests-Bibliothek nicht installiert (pip install requests)")

        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": method,
            "params": params or {},
        }
        try:
            resp = requests.post(
                self.url,
                json=payload,
                headers=self._headers,
                timeout=self.timeout,
            )
            resp.raise_for_status()
            data = resp.json()
            if "error" in data:
                raise ValueError(f"MCP-Fehler: {data['error']}")
            return data.get("result")
        except requests.exceptions.RequestException as exc:
            logger.error("MCP-Anfrage fehlgeschlagen: %s", exc)
            raise

    def list_tools(self) -> Any:
        """Listet verfügbare MCP-Tools auf."""
        return self.call("tools/list")

    def call_tool(self, name: str, arguments: Optional[Dict[str, Any]] = None) -> Any:
        """Ruft ein einzelnes MCP-Tool auf."""
        return self.call("tools/call", {"name": name, "arguments": arguments or {}})

    def health_check(self) -> bool:
        """Prüft ob der MCP-Endpoint erreichbar ist."""
        try:
            self.list_tools()
            return True
        except Exception:
            return False


# ──────────────────────────────────────────────────────────────
# Agent-Reach-Integration
# ──────────────────────────────────────────────────────────────

class AgentReachBridge:
    """
    Bindet Agent-Reach (github.com/Panniantong/Agent-Reach) an den CRM an.

    Agent-Reach gibt KI-Agenten Lese-/Suchzugang zu 13 Internet-Plattformen.
    Diese Bridge leitet CRM-Suchanfragen an Agent-Reach weiter.
    """

    def __init__(self) -> None:
        self._available = self._check_availability()

    def _check_availability(self) -> bool:
        try:
            import importlib
            return importlib.util.find_spec("agent_reach") is not None
        except Exception:
            return False

    def search(self, query: str, channel: Optional[str] = None) -> Dict[str, Any]:
        """
        Durchsucht über Agent-Reach einen oder alle Kanäle.

        Args:
            query:   Suchanfrage
            channel: Optionaler Kanalname (z. B. "github", "reddit").
                     None = automatisches Routing.

        Returns:
            {"results": [...], "channel": "<name>", "ok": bool}
        """
        if not self._available:
            return {"ok": False, "error": "agent_reach nicht installiert (pip install agent-reach)"}

        try:
            from agent_reach.core import read_or_search  # type: ignore
            results = read_or_search(query, channel=channel)
            return {"ok": True, "channel": channel or "auto", "results": results}
        except Exception as exc:
            logger.error("Agent-Reach-Suche fehlgeschlagen: %s", exc)
            return {"ok": False, "error": str(exc)}

    def read(self, url: str) -> Dict[str, Any]:
        """Liest eine URL über Agent-Reach."""
        if not self._available:
            return {"ok": False, "error": "agent_reach nicht installiert"}

        try:
            from agent_reach.core import read_or_search  # type: ignore
            result = read_or_search(url)
            return {"ok": True, "result": result}
        except Exception as exc:
            logger.error("Agent-Reach-Read fehlgeschlagen: %s", exc)
            return {"ok": False, "error": str(exc)}


# ──────────────────────────────────────────────────────────────
# Flask-Routen-Registrierung
# ──────────────────────────────────────────────────────────────

def register_mcp_routes(app: Any) -> None:
    """Registriert MCP- und Agent-Reach-Routen in der Flask-App."""

    mcp_client = ByblosMCPClient()
    agent_bridge = AgentReachBridge()

    @app.route("/api/mcp/health")
    def mcp_health():
        from flask import jsonify
        ok = mcp_client.health_check()
        return jsonify({"status": "ok" if ok else "error", "endpoint": mcp_client.url})

    @app.route("/api/mcp/tools")
    def mcp_tools():
        from flask import jsonify
        try:
            tools = mcp_client.list_tools()
            return jsonify({"ok": True, "tools": tools})
        except Exception as exc:
            return jsonify({"ok": False, "error": str(exc)}), 502

    @app.route("/api/mcp/call", methods=["POST"])
    def mcp_call():
        from flask import request, jsonify
        body = request.get_json(silent=True) or {}
        tool_name = body.get("tool")
        arguments = body.get("arguments", {})
        if not tool_name:
            return jsonify({"ok": False, "error": "Feld 'tool' fehlt"}), 400
        try:
            result = mcp_client.call_tool(tool_name, arguments)
            return jsonify({"ok": True, "result": result})
        except Exception as exc:
            return jsonify({"ok": False, "error": str(exc)}), 502

    @app.route("/api/agent-reach/search")
    def agent_reach_search():
        from flask import request, jsonify
        query = request.args.get("q", "").strip()
        channel = request.args.get("channel")
        if not query:
            return jsonify({"ok": False, "error": "Parameter 'q' fehlt"}), 400
        return jsonify(agent_bridge.search(query, channel=channel or None))

    @app.route("/api/agent-reach/read")
    def agent_reach_read():
        from flask import request, jsonify
        url = request.args.get("url", "").strip()
        if not url:
            return jsonify({"ok": False, "error": "Parameter 'url' fehlt"}), 400
        return jsonify(agent_bridge.read(url))

    logger.info("MCP & Agent-Reach Routen registriert.")
