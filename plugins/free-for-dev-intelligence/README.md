# Free for Dev Intelligence Plugin v4

V4 packages the existing 18 free-for.dev intelligence skills together with an executable MCP server, an optional MCP Apps comparison widget, a local plugin marketplace entry, deployment files, and a ChatGPT app-binding workflow.

The free-for.dev catalog remains discovery evidence. Current provider-controlled sources remain authoritative for pricing, quotas, billing, region availability, legal/privacy documents, product status, and commercial-use terms.

## What V4 adds

- Required plugin manifest at `.codex-plugin/plugin.json`.
- Bundled MCP configuration at `.mcp.json`.
- 18 retained skills under `skills/`.
- 18 local/stdio MCP tools; 17 read-only tools are exposed by HTTP by default.
- Standard `search` and `fetch` tools for citation-compatible catalog discovery.
- Streamable HTTP request/response endpoint at `/mcp`.
- Health and diagnostic REST endpoints.
- Decoupled comparison widget at `ui://free-dev/comparison-v1.html`.
- Local marketplace metadata at `.agents/plugins/marketplace.json`.
- `.app.json.template` and `scripts/bind_chatgpt_app.py` for a registered ChatGPT MCP connection.
- Docker deployment recipe.
- Plugin, MCP, skill, security, and regression tests.

## 18 skills

1. `free-dev-intelligence` - master orchestration and evidence policy.
2. `free-dev-query-router` - normalize mixed natural-language requests.
3. `free-dev-live-sync` - acquire and fingerprint catalog snapshots.
4. `free-dev-catalog-index` - build/query a SQLite FTS5 catalog index.
5. `free-dev-catalog-search` - parse, search, filter, and shortlist catalog entries.
6. `free-dev-provider-profile` - normalize provider evidence dossiers.
7. `free-dev-tier-verifier` - verify current provider-controlled facts.
8. `free-dev-service-comparator` - apply hard filters and rank viable candidates.
9. `free-dev-cost-estimator` - model free quota headroom and paid transition.
10. `free-dev-compliance-filter` - evidence-filter EU/privacy/business requirements.
11. `free-dev-risk-auditor` - audit billing, operational, privacy, security, and lock-in risks.
12. `free-dev-stack-planner` - design multi-service free-tier stacks.
13. `free-dev-architecture-designer` - inspect topology, failure domains, backups, regions, and egress boundaries.
14. `free-dev-alternative-finder` - find replacement candidates.
15. `free-dev-migration-planner` - plan source-to-target migrations.
16. `free-dev-catalog-diff` - compare catalog snapshots.
17. `free-dev-change-watch` - classify material provider/profile changes.
18. `free-dev-exporter` - export JSON, CSV, TSV, and Markdown.

## MCP tools

`search`, `fetch`, `catalog_search`, `route_query`, `provider_profile`, `compare_services`, `estimate_cost`, `check_capacity`, `compliance_filter`, `audit_risks`, `design_architecture`, `plan_migration`, `compare_profiles`, `compare_catalog_snapshots`, `export_results`, `catalog_status`, `refresh_catalog`, and `render_comparison`.

Only `render_comparison` attaches a UI resource. Discovery and analysis tools remain data-only.

## Security defaults

- HTTP binds to localhost unless another host is explicitly supplied.
- Unexpected `Origin` headers are rejected unless listed in `FREE_DEV_ALLOWED_ORIGINS`.
- `FREE_DEV_API_TOKEN` can require a bearer token on MCP and diagnostic API routes.
- HTTP write tools are disabled unless `FREE_DEV_ENABLE_HTTP_WRITES=1`.
- The caller cannot supply an arbitrary refresh URL; the refresh source is operator-controlled by environment configuration.
- The widget has an empty network CSP and loads no external assets.

## Catalog source resolution

1. `FREE_FOR_DEV_CATALOG_PATH` when explicitly set.
2. Cached snapshot under `PLUGIN_DATA` or `FREE_DEV_DATA_DIR`.
3. Live upstream README fetch.

The full upstream catalog is not copied into this repository. Test fixtures are never used as production data unless `FREE_DEV_ALLOW_FIXTURE_FALLBACK=1` is explicitly set.

## Package layout

```text
.codex-plugin/plugin.json
.mcp.json
.app.json.template
.agents/plugins/marketplace.json
mcp_server/
scripts/
skills/
dist/
runtime/
tests/
```

See `INSTALL.md`, `PLUGIN_STATUS_V4.md`, `CAPABILITIES.md`, and `VALIDATION.md`.
