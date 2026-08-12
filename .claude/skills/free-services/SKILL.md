---
name: free-services
description: "Find, compare, and plan migration between free-tier developer services — merged from free-for-dev plugin v6 (25 skills). Use when searching for free alternatives, comparing service tiers, planning stack architecture with free tools, auditing costs/risks, or migrating between providers. Covers 40+ permanently free providers."
---

# Free Services Suite

Helps find, evaluate, and choose free-tier developer services using hard constraints plus transparent weighted scoring.

## Sub-skill Routing

| User intent | Action |
|---|---|
| "Find free alternative to X" | Alternative Finder mode |
| "Compare A vs B vs C" | Service Comparator mode |
| "Plan my free stack for this workload" | Stack Planner mode |
| "Is this tier still free? Verify it" | Tier Verifier mode |
| "Plan migration from X to Y" | Migration Planner mode |
| "Design architecture using free services" | Architecture Designer mode |
| "What are the risks of using X free tier?" | Risk Auditor mode |
| "Export my service list" | Exporter mode |
| "Simulate this workload against free limits" | Workload Simulator mode |
| "Search the catalog semantically" | Semantic Search mode |

## Universal Rules

1. **Verify time-sensitive provider facts** before treating them as scoring inputs — free tiers change frequently.
2. **Apply hard constraints first** — a failed hard requirement disqualifies regardless of score.
3. Use explicit `unknown` values instead of optimistic assumptions.
4. **Penalize unknown evidence** when the missing fact is decision-critical.
5. Keep the scoring model visible and adjustable.
6. Verify card/payment requirements — some "free" tiers require a credit card.

## Service Comparator (most common use)

Dimensions scored:
- Capability fit for the stated workload
- Quota headroom (requests, storage, compute)
- Billing safety (no surprise charges, card-free)
- Region / data-residency compliance
- Operational reliability signals
- Portability / lock-in risk
- Documentation / evidence confidence

**Output format:** Disqualifications first → ranked viable candidates with score components and evidence gaps.

## Stack Planner

For designing a complete free stack:
1. Collect workload requirements (traffic, storage, compute, regions)
2. Map to service categories (hosting, DB, auth, email, CDN, monitoring...)
3. For each category: find free candidates → apply hard constraints → score → select
4. Validate combined stack for quota conflicts and integration complexity
5. Output: stack diagram + monthly free-tier budget

## Migration Planner

Steps for provider migration:
1. Inventory current services and usage metrics
2. Identify migration triggers (quota approach, feature gap, cost)
3. Map current → target service equivalents
4. Assess data portability (export formats, API compatibility)
5. Generate migration checklist with validation steps
6. Estimate downtime / cutover risk

## Risk Auditor

Dimensions assessed:
- Quota exhaustion risk (buffer vs. headroom)
- Billing escalation triggers (overage auto-charges)
- Service continuity (SLA on free tier, history of tier changes)
- Data lock-in (export limitations)
- Regulatory / privacy compliance on free tier
