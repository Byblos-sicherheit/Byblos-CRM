# Develocity Decision Pack

Use this reference after the strategic narrative is established. It converts the Develocity case into an approval-ready pilot, scorecard, and decision gate.

## Current-source requirement

Refresh official product, documentation, release, pricing, deployment, security, and support information before external use. Record the retrieval date. Do not use this file as permanent proof of current capabilities.

## Decision requested

Choose one explicit request:

- approve a measured pilot;
- approve phased rollout after a successful pilot;
- approve enterprise adoption with stated conditions;
- decline or defer because evidence is inadequate.

A generic request to "explore" without owners, scope, and a decision date is not a decision.

## Pilot workstreams

### 1. Context and observability

Validate that build, test, dependency, cache, and environment records are captured for the selected toolchains and can be queried by the required human and agent workflows.

### 2. Efficiency

Select mechanisms relevant to the observed bottleneck, such as shared build caching, artifact caching, setup caching, predictive test selection, test distribution, flaky-test management, failure analytics, or performance insights. Do not enable every mechanism merely to increase feature coverage.

### 3. Governance

When in scope, validate provenance, attestations, policy evaluation, gate behavior, evidence retention, access control, and audit retrieval. Include security and compliance owners.

### 4. AI delivery

Measure agent-triggered build volume, time from generated change to merge-ready state, reruns, failure-recovery loops, compute consumption, and human supervision. Do not use lines of generated code as the productivity metric.

### 5. Operating model

Define platform ownership, upgrades, incident response, data retention, support path, configuration governance, onboarding, and chargeback/showback if applicable.

## Develocity-specific baseline measures

- Build and test duration: median, p90, p95.
- Queue time and cold-start/setup time.
- Cacheable work, hits, misses, and avoided execution.
- Dependency and toolchain download volume and duration.
- Test count, selected-test count, distribution efficiency.
- Flaky failures, reruns, quarantines, and diagnosis time.
- Build failures grouped by cause and time to resolution.
- CI CPU, memory, runner hours, storage, and network cost.
- Local developer wait time.
- Build Scan or equivalent telemetry coverage.
- Artifact provenance and policy-gate coverage.
- Deployment frequency, lead time, change failure rate, and recovery time.
- AI-agent runs, validated changes, merged changes, and production outcomes.

## Scorecard categories

Use a 0–5 score with written evidence for each category:

- Strategic fit
- Toolchain coverage
- Observability/context quality
- Acceleration effectiveness
- Test-signal reliability
- Governance and provenance
- Security and data controls
- AI-agent integration
- Operational burden
- Developer experience
- Financial case
- Vendor and exit risk

Weight categories before the pilot. A high total score must not override a failed security, legal, or mandatory technical gate.

## Mandatory gates

Define pass/fail gates for:

- security architecture;
- data protection and residency;
- supported build systems and package managers;
- required CI and repository integrations;
- acceptable build overhead;
- cache correctness and bypass;
- service reliability and support;
- evidence retention;
- total cost boundary;
- exit and rollback feasibility.

## Recommended decision memo structure

1. Decision requested
2. Why now
3. Current-state evidence
4. Develocity capability-to-outcome map
5. Pilot scope and interventions
6. Results against predeclared thresholds
7. ROI and sensitivity analysis
8. Security, governance, and operating model
9. Risks and mitigations
10. Commercial assumptions
11. Recommendation and next gate

## Develocity claim discipline

- Cite current official sources for capabilities.
- Mark customer outcomes as named customer or vendor-reported results.
- Mark organization-specific projections as modeled.
- Distinguish product availability from licensed package inclusion.
- Verify current release, support, and component lifecycle before implementation.
- Do not assume the same support level across Gradle, Maven, Bazel, sbt, npm, Python, or other toolchains without checking current documentation.
