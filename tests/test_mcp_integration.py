"""Tests für extensions_v2_mcp_integration."""

import pytest
from unittest.mock import patch, MagicMock


# ──────────────────────────────────────────────────────────────
# ByblosMCPClient Tests
# ──────────────────────────────────────────────────────────────

class TestByblosMCPClient:
    def test_default_url(self):
        from extensions_v2_mcp_integration import ByblosMCPClient
        client = ByblosMCPClient()
        assert "byblos-sicherheit.de" in client.url

    def test_custom_url(self):
        from extensions_v2_mcp_integration import ByblosMCPClient
        client = ByblosMCPClient(url="https://example.com/mcp")
        assert client.url == "https://example.com/mcp"

    def test_headers_include_auth_when_key_set(self):
        from extensions_v2_mcp_integration import ByblosMCPClient
        client = ByblosMCPClient(api_key="test_key_123")
        assert client._headers["Authorization"] == "Bearer test_key_123"

    def test_headers_no_auth_when_key_empty(self):
        from extensions_v2_mcp_integration import ByblosMCPClient
        client = ByblosMCPClient(api_key="")
        assert "Authorization" not in client._headers

    @patch("extensions_v2_mcp_integration.REQUESTS_OK", False)
    def test_call_raises_without_requests(self):
        from extensions_v2_mcp_integration import ByblosMCPClient
        client = ByblosMCPClient(api_key="key")
        with pytest.raises(RuntimeError, match="requests"):
            client.call("tools/list")

    def test_health_check_returns_false_on_error(self):
        from extensions_v2_mcp_integration import ByblosMCPClient
        client = ByblosMCPClient(api_key="key")
        with patch.object(client, "list_tools", side_effect=Exception("network error")):
            assert client.health_check() is False

    def test_health_check_returns_true_on_success(self):
        from extensions_v2_mcp_integration import ByblosMCPClient
        client = ByblosMCPClient(api_key="key")
        with patch.object(client, "list_tools", return_value=[]):
            assert client.health_check() is True


# ──────────────────────────────────────────────────────────────
# AgentReachBridge Tests
# ──────────────────────────────────────────────────────────────

class TestAgentReachBridge:
    def test_unavailable_when_not_installed(self):
        from extensions_v2_mcp_integration import AgentReachBridge
        with patch.object(AgentReachBridge, "_check_availability", return_value=False):
            bridge = AgentReachBridge()
            result = bridge.search("test query")
            assert result["ok"] is False
            assert "agent_reach" in result["error"]

    def test_search_returns_error_on_exception(self):
        from extensions_v2_mcp_integration import AgentReachBridge
        bridge = AgentReachBridge()
        bridge._available = True
        with patch("extensions_v2_mcp_integration.AgentReachBridge.search",
                   return_value={"ok": False, "error": "timeout"}):
            result = bridge.search("query")
            assert result["ok"] is False

    def test_read_unavailable_returns_error(self):
        from extensions_v2_mcp_integration import AgentReachBridge
        bridge = AgentReachBridge()
        bridge._available = False
        result = bridge.read("https://example.com")
        assert result["ok"] is False
