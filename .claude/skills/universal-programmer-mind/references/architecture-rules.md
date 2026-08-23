# Architecture Rules

## Start from constraints

Document:
- Users and use cases
- Scale and workload shape
- Data sensitivity and residency
- Availability, latency, recovery, and offline requirements
- Deployment environment and budget
- Existing systems and team competence
- Compatibility and migration constraints

Do not select architecture from diagrams alone.

## Boundaries

- Organize modules around responsibilities and data ownership.
- Keep dependency direction explicit.
- Separate policy from infrastructure where it materially improves testing or replacement.
- Avoid shared mutable state across boundaries.
- Define contracts for APIs, events, files, schemas, and command interfaces.
- Version contracts when independent consumers exist.

## Monolith, modular monolith, or services

Prefer a modular monolith when:
- One team owns the system.
- Deployment can remain coordinated.
- Scale does not require independently scaled components.
- Domain boundaries are not yet stable.

Use separate services only when a demonstrated requirement needs independent ownership, scaling, isolation, technology, compliance, or release cadence. Include network failure, observability, data consistency, and operational cost in the decision.

## Data design

- Assign a source of truth for each entity.
- Enforce invariants in the strongest appropriate layer, preferably schema plus domain logic.
- Design migrations to be observable, reversible where possible, and compatible with rolling deployment.
- Avoid distributed transactions unless the requirement justifies the operational burden.
- Use idempotency for retried write operations.

## API design

- Define request, response, error, authentication, authorization, pagination, rate limit, timeout, and idempotency behavior.
- Validate at entry boundaries.
- Avoid leaking internal implementation details in public contracts.
- Keep backward compatibility or publish an explicit migration.

## Reliability

For each external dependency define:
- Timeout
- Retry policy and retry-safe operations
- Circuit or load-shedding behavior when needed
- Fallback or degraded behavior
- Monitoring and alert condition

## Observability

Provide enough structured logs, metrics, traces, correlation identifiers, and audit events to diagnose production behavior without exposing secrets or sensitive data.

## Decision record

For material architecture choices, capture:
- Context
- Options considered
- Decision
- Consequences and trade-offs
- Revisit trigger

Do not pretend every decision is permanent.
