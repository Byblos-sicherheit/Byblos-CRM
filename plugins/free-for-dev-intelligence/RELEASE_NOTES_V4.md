# Release notes - V4

## Major change

V4 converts the V3 multi-skill intelligence bundle into an executable plugin package with MCP transport and optional UI.

## Added

- `.codex-plugin/plugin.json`.
- `.mcp.json` bundled server configuration.
- `.agents/plugins/marketplace.json` local marketplace entry.
- 18-tool MCP server in `mcp_server/free_dev_mcp.py`.
- Standard `search` and `fetch` catalog tools.
- Streamable HTTP request/response endpoint at `/mcp`.
- Comparison MCP Apps widget.
- Optional bearer authentication and Origin validation.
- Remote write-tool gating; HTTP is read-only by default.
- Diagnostic REST endpoints and health endpoint.
- `.app.json.template` and app-ID binder.
- Docker deployment recipe.
- Plugin contract and MCP transport tests.

## Evidence correction

MCP `search` and `fetch` cite the catalog source URL rather than the provider URL. Provider URLs are preserved as metadata. This prevents free-for.dev catalog wording from being presented as if it came directly from the provider.

## Preserved

All 18 V3 skills, deterministic scripts, the SQLite/FTS runtime, exports, cost/risk/compliance logic, migration/architecture planning, and catalog/profile change detection remain included.
