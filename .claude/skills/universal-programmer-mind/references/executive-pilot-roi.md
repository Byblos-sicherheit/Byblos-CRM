# Executive Pilot and ROI Discipline

Use this reference when a technology-adoption case must move from persuasive narrative to an investable, measurable decision.

## Principle

Do not treat a vendor feature list or customer case study as an ROI model. Build the financial case from the organization's own baseline, explicit causal assumptions, and a controlled pilot.

## Required baseline inputs

Collect or mark unavailable:

- active committers and participating repositories;
- local, CI, and agent-triggered builds per month;
- median and p90 build/test feedback time;
- engineer wait and failure-diagnosis time;
- loaded engineering cost per hour;
- CI compute, storage, network, and artifact-repository cost;
- rerun rate caused by flaky tests, infrastructure, or dependency failures;
- release frequency, lead time, change failure rate, and recovery time;
- governance, audit, and evidence-collection labor;
- incident and remediation cost attributable to delivery failures;
- platform license, implementation, infrastructure, enablement, and operating cost.

Never silently substitute industry averages for missing internal data. Use ranges or scenarios only when clearly labeled.

## ROI equations

Use auditable components:

`engineering value = reclaimed hours × loaded hourly cost`

`infrastructure value = baseline CI/network/repository cost × measured avoidance rate`

`governance value = reduced evidence and policy-review hours × loaded hourly cost`

`risk value = baseline annual incident/remediation cost × measured or explicitly modeled reduction rate`

`annual gross value = engineering value + infrastructure value + governance value + risk value`

`first-year net value = annual gross value - annual recurring cost - one-time implementation cost`

`steady-state annual net value = annual gross value - annual recurring cost`

`payback months = one-time implementation cost ÷ positive monthly steady-state net value`

Do not calculate payback when steady-state net value is zero or negative. Do not claim risk reduction as realized savings unless the measurement method supports it.

## Scenario discipline

Use three scenarios when uncertainty is material:

- Conservative: only directly measured and low-confidence benefits.
- Expected: pilot-observed improvements applied to eligible scope.
- Upside: broader adoption and additional mechanisms, clearly marked as conditional.

For every scenario, list:

- input values;
- source of each input;
- eligibility boundary;
- realization assumption;
- excluded benefits;
- sensitivity drivers.

## Pilot design

### Scope

Choose repositories that are representative and measurable, not merely politically easy. Include enough variation to test the platform without turning the pilot into a full rollout.

Recommended characteristics:

- material build/test volume;
- visible developer wait or failure burden;
- stable ownership;
- reproducible cost data;
- one or more relevant build systems;
- enough release activity to observe delivery effects;
- governance use case when governance is part of the business case.

### Baseline period

Use a period long enough to include normal variability. Match the period to release cadence and workload seasonality. Do not compare a quiet baseline with a peak adoption period without adjustment.

### Intervention sequence

1. Instrument and validate telemetry before optimization.
2. Establish baseline definitions and ownership.
3. Enable one mechanism at a time when attribution matters.
4. Record operational changes, training, and policy changes alongside product configuration.
5. Compare median and tail behavior; averages can hide severe outliers.
6. Preserve a rollback path.

### Success criteria

Define thresholds before the pilot begins. Use a balanced set:

- feedback time and p90 improvement;
- work avoided or cache effectiveness;
- CI/network cost avoided;
- flaky-test or rerun reduction;
- diagnosis-time reduction;
- provenance and policy coverage;
- DORA movement where the observation window is sufficient;
- user adoption and operational burden;
- security and data-governance acceptance;
- projected net value at eligible enterprise scope.

### Decision gate

At the end, choose one:

- expand;
- expand with conditions;
- extend the pilot because evidence is incomplete;
- stop because the economics or operating fit are inadequate.

Do not redefine success criteria after results are known without disclosing the change.

## Attribution controls

Track simultaneous changes that could contaminate the result:

- CI migration;
- hardware or runner changes;
- test-suite reductions;
- repository restructuring;
- release-process changes;
- staffing changes;
- AI-agent rollout;
- dependency upgrades;
- major seasonal workload shifts.

When clean attribution is impossible, state the limitation and use multiple evidence sources rather than false precision.

## Procurement readiness

Before requesting approval, document:

- package and dependency assumptions;
- pricing unit and eligible user population;
- deployment model and operating ownership;
- data retention and access-control requirements;
- implementation services and internal labor;
- renewal and expansion risk;
- exit plan and data portability;
- support and success criteria;
- contract conditions tied to the pilot where negotiable.
