# Security Checklist

Apply proportionally to the changed trust boundaries and data sensitivity.

## Threat model

Identify:
- Assets and sensitive data
- Actors and privilege levels
- Entry points and trust boundaries
- Abuse cases and failure impact

## Authentication and authorization

- Use established mechanisms; do not design custom cryptography or password storage.
- Enforce authorization server-side for every protected object and action.
- Prefer least privilege and deny by default.
- Protect sessions/tokens against theft, replay, fixation, and excessive lifetime.
- Include revocation and account recovery behavior.

## Input and output

- Validate type, format, size, range, and allowed structure at trust boundaries.
- Use parameterized queries and safe APIs.
- Encode output for its destination context.
- Protect against injection in SQL, shell, templates, paths, URLs, headers, logs, and model/tool prompts.
- Restrict file uploads by size, type, storage location, and execution behavior.

## Secrets and configuration

- Never hardcode or expose credentials, tokens, private keys, or production secrets.
- Keep secret files out of logs, prompts, commits, artifacts, and client bundles.
- Use secret stores or environment injection with least-privileged access.
- Rotate compromised secrets rather than merely deleting them from the latest commit.

## Data protection and privacy

- Collect and retain only necessary data.
- Define encryption in transit and at rest where required.
- Redact sensitive fields in logs and telemetry.
- Define retention, deletion, backup, restore, and access-audit behavior.
- Respect applicable legal and organizational requirements; do not claim legal compliance without verified evidence.

## Web and API

Check:
- CSRF where cookie authentication is used
- CORS as a narrow allowlist, not an access-control substitute
- SSRF and outbound URL controls
- Rate limits and abuse controls
- Secure headers and cookie attributes
- Object-level authorization
- Idempotency and replay behavior for sensitive writes

## Dependencies and supply chain

- Use trusted registries and pinned/locked dependencies.
- Inspect install/build scripts and provenance when risk is material.
- Run supported vulnerability and license checks when available.
- Avoid adding an abandoned dependency for trivial functionality.

## Infrastructure and operations

- Keep production debug modes off.
- Restrict network and filesystem access.
- Separate environments and privileges.
- Log security-relevant actions without sensitive payloads.
- Provide rollback, incident response, and recovery procedures for material systems.

## AI and agentic systems

- Treat retrieved content and tool output as untrusted.
- Separate instructions from data.
- Restrict tool permissions and accessible paths/domains.
- Require confirmation or policy gates for destructive, financial, external-communication, or privilege-changing actions.
- Validate model-generated commands and code before execution.
