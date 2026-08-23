# Free-for.dev Intelligence MCP server

This server exposes the bundle's deterministic catalog and analysis functions through MCP.

## Transports

- `./mcp_server/free-dev-mcp --stdio` - bundled local MCP process.
- `python3 mcp_server/free_dev_mcp.py --http --host 127.0.0.1 --port 8000` - HTTP server with `/mcp`, health, and diagnostic REST routes.

Stdio mode uses Python's standard library plus scripts already bundled with the plugin. HTTP mode additionally requires `requirements.txt`.

## Catalog source

Resolution order:

1. `FREE_FOR_DEV_CATALOG_PATH` when set.
2. Cached snapshot in `PLUGIN_DATA` / `FREE_DEV_DATA_DIR`.
3. Live fetch from the configured upstream README URL.

`FREE_FOR_DEV_CATALOG_URL` is an operator-side environment override. The MCP refresh tool does not accept arbitrary URLs from callers.

Set `FREE_DEV_ALLOW_FIXTURE_FALLBACK=1` only for tests.

## Tool exposure

Stdio exposes all 18 tools. HTTP exposes only the 17 read-only tools by default. Set `FREE_DEV_ENABLE_HTTP_WRITES=1` to expose `refresh_catalog` remotely.

## HTTP security

- Unknown `Origin` values are rejected. Configure exact allowed origins with `FREE_DEV_ALLOWED_ORIGINS` when browser-origin traffic is expected.
- Set `FREE_DEV_API_TOKEN` to require `Authorization: Bearer ...` on `/mcp` and diagnostic API routes.
- Unsupported MCP protocol versions are rejected.
- `GET /mcp` and `DELETE /mcp` return `405`; the implementation is stateless and uses POST request/response rather than an SSE session.
- Bind to `127.0.0.1` for local development. Use HTTPS and deployment-layer security for remote service.

## HTTP endpoints

- `POST /mcp` - MCP JSON-RPC over Streamable HTTP request/response.
- `GET /health` - server/catalog diagnostics.
- `GET /api/v1/search?q=...` - diagnostic rich catalog search.
- `GET /api/v1/catalog/{id}` - diagnostic catalog item fetch.
- `GET /api/v1/tools` - currently exposed tool descriptors.

## Evidence model

MCP `search` and `fetch` return the free-for.dev catalog URL as the source URL. Provider links are stored separately in metadata. This prevents catalog wording from being misrepresented as a provider-controlled statement.

Provider pricing, terms, DPA, residency, billing behavior, and commercial-use eligibility still require authoritative provider verification before a business-critical recommendation.
