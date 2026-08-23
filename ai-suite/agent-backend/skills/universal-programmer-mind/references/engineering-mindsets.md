# Engineering Mindsets

Use these as decision lenses, not theatrical personas. Activate only the lenses relevant to the task and synthesize one answer.

## 1. Requirements and product lens

Ask:
- What outcome does the user need?
- Who uses it, under which conditions, and what does failure cost?
- What are the explicit acceptance criteria?
- Which constraints are legal, operational, budgetary, platform-specific, or time-sensitive?
- What is MVP, and what is unnecessary scope?

Reject feature volume that does not improve the target outcome.

## 2. Computer-science and algorithm lens

Examine:
- Data structures and invariants
- Correctness and termination
- Time and space complexity
- Numerical stability and precision
- Concurrency, ordering, and consistency
- Boundary and adversarial cases

Prefer a clear correct algorithm before micro-optimization.

## 3. Software architecture lens

Examine:
- Module boundaries and dependency direction
- Data ownership and contracts
- Coupling, cohesion, extensibility, and replacement cost
- Failure isolation, compatibility, and migration path
- Operational topology and trust boundaries

Choose the simplest architecture that satisfies current evidence and plausible near-term change.

## 4. Language and ecosystem specialist

Examine:
- Existing repository conventions
- Runtime and deployment environment
- Type system, memory model, concurrency model, package ecosystem, tooling, and support horizon
- Team capability and maintenance burden

Do not force a favorite language into an unsuitable problem.

## 5. Backend and API lens

Examine:
- Domain model, authorization, validation, transactions, idempotency, pagination, rate limits, retries, and timeouts
- API versioning, status/error contracts, observability, and backward compatibility
- Data consistency and partial failure

Treat every network boundary as unreliable.

## 6. Frontend and user-interface lens

Examine:
- User flows and information hierarchy
- State ownership, loading, empty, error, offline, and recovery states
- Responsive behavior, accessibility, localization, and perceived performance
- Browser/device compatibility and security boundaries

A visually working happy path is not a finished interface.

## 7. Mobile lens

Examine:
- Lifecycle, background execution, permissions, battery, network variability, offline storage, deep links, and platform guidelines
- Release signing, store constraints, crash reporting, and backward OS compatibility

## 8. Data and database lens

Examine:
- Source of truth, schema constraints, normalization/denormalization, indexes, cardinality, query plans, migrations, retention, backup, and recovery
- Transaction boundaries, isolation, replication, and consistency requirements

Make invalid states difficult or impossible to store.

## 9. AI/ML lens

Examine:
- Whether ML is actually required
- Data quality, provenance, privacy, evaluation set, baseline, drift, hallucination, latency, cost, and fallback behavior
- Prompt/model versioning, observability, human review, and safety controls

Never label an unmeasured demo as reliable intelligence.

## 10. Security and privacy lens

Examine:
- Assets, actors, trust boundaries, threat model, least privilege, secure defaults, secrets, authentication, authorization, injection, supply-chain risk, logging, encryption, retention, and incident response

Security is a design constraint, not a final checklist only.

## 11. Testing and quality lens

Examine:
- Observable contract, failure modes, deterministic tests, test isolation, useful coverage, regressions, mutation risk, and realistic integration boundaries

A test that cannot fail for the intended defect is not evidence.

## 12. Performance lens

Examine:
- Measured bottleneck, workload, latency percentiles, throughput, memory, I/O, network, query behavior, caching, contention, and cost

Measure before optimizing; protect correctness while optimizing.

## 13. SRE, DevOps, and release lens

Examine:
- Reproducible builds, CI/CD, configuration, environments, infrastructure, health checks, observability, capacity, rollback, disaster recovery, and runbooks

A deployment without a recovery path is incomplete.

## 14. Code-review and maintainability lens

Examine:
- Correctness, clarity, local conventions, unnecessary complexity, ownership, testability, documentation, compatibility, and future change cost

Distinguish blocking defects from optional improvements.

## Synthesis rule

When lenses conflict, decide using this priority unless the task requires another order:

1. Safety, security, and data integrity
2. Explicit user requirements and correctness
3. Reliability and compatibility
4. Maintainability and operability
5. Performance supported by evidence
6. Delivery speed and convenience
7. Novelty or stylistic preference
