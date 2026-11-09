# Validation report - V4

## Result

**PASS**

## Skill packaging

- 18 skill directories retained.
- 18/18 official skill packaging runs reported successful validation and packaging.
- 18/18 distributable archives are present as `skill.zip`.
- Every skill ZIP passed ZIP integrity testing.
- No skill ZIP contains `__pycache__` or `.pyc` content.
- Largest individual skill archive: 10,135 bytes, below the 25 MB skill-package limit.

## Plugin contract

- 23 plugin-contract checks passed.
- Required `.codex-plugin/plugin.json` is present and points to `./skills/` and `./.mcp.json`.
- Repo-local marketplace path resolves to the plugin root.
- Release package intentionally has no `.app.json` or manifest `apps` binding before a real `plugin_asdk_app...` ID exists.
- 18 MCP tool descriptors are registered for stdio.
- Only `render_comparison` attaches UI metadata.
- Widget MIME is `text/html;profile=mcp-app` and its network CSP allowlists are empty.

## MCP and regression tests

- MCP server self-test: 5/5 passed.
- MCP functional integration suite: 10/10 passed.
- V3 compatibility regression suite: 13/13 passed.
- Stdio protocol test passed: initialize, initialized notification, `tools/list`, and `search`; 18 tools exposed.
- HTTP security/transport test passed: unauthenticated request -> 401; disallowed Origin -> 403; unsupported protocol -> 400.
- HTTP default tool surface contains 17 read-only tools; `refresh_catalog` is hidden and direct remote calls are denied unless remote writes are explicitly enabled.
- ChatGPT app binder passed in a temporary copy; the release tree remained unbound.
- Python sources compiled successfully during development.

## External validation boundary

The build environment could not install the official MCP Python package from its restricted package mirror, so protocol compatibility was tested directly over stdio and HTTP rather than with MCP Inspector in this environment.

A live ChatGPT Developer-mode registration, the account-specific `.app.json` ID, public HTTPS hosting, and any public directory submission are infrastructure/account-specific steps and are not fabricated by this package.

## Evidence limitation

These tests validate software behavior and package structure. They do not certify any third-party provider's current pricing, limits, legal terms, privacy position, availability, or free-tier status. Material provider facts still require current provider-controlled verification.
