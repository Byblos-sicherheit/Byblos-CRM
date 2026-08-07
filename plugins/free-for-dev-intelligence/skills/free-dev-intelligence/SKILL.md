---
name: free-dev-intelligence
description: "Orchestrate end-to-end free developer-service intelligence: natural-language routing, current catalog acquisition, local indexing, discovery, provider evidence profiles, verification, comparison, compliance review, cost modeling, risk analysis, architecture design, alternatives, migration planning, exports, catalog diffs, and material-change monitoring. Use for broad requests such as finding the best free stack, evaluating providers, creating a decision dossier, planning a migration, or coordinating several free-dev specialist skills."
---

# Free Dev Intelligence

## Mission

Turn a free-tier question into an evidence-labeled technical decision. Treat free-for.dev as discovery data, not as contractual pricing, legal, privacy, availability, or product authority.

## Routing workflow

1. For broad or mixed natural-language requests, use `free-dev-query-router` to identify intent, categories, hard constraints, and specialist sequence.
2. Obtain a current free-for.dev catalog snapshot with `free-dev-live-sync` when freshness matters.
3. For repeated or large-scale discovery, build/query `free-dev-catalog-index`; otherwise use `free-dev-catalog-search` directly.
4. Discover candidate services and exclude explicit catalog-level mismatches without treating silence as proof.
5. For a provider under serious consideration, build a normalized evidence dossier with `free-dev-provider-profile`.
6. Verify material current claims with `free-dev-tier-verifier` against provider-controlled sources.
7. Compare viable candidates with `free-dev-service-comparator` after hard constraints have been evaluated.
8. For commercial or EU workloads, run `free-dev-compliance-filter` and `free-dev-risk-auditor`.
9. Model quota headroom and paid transition with `free-dev-cost-estimator` when usage is known.
10. For a multi-service topology, use `free-dev-stack-planner` followed by `free-dev-architecture-designer`.
11. Find substitutes with `free-dev-alternative-finder` when a candidate fails a hard constraint.
12. Plan source-to-target moves with `free-dev-migration-planner` when replacement requires migration.
13. Export final structured data with `free-dev-exporter` if requested.
14. Use `free-dev-catalog-diff` for historical catalog changes and `free-dev-change-watch` for narrowly scoped material-change monitoring.

## V4 MCP tool routing

When the bundled MCP server is available, prefer its deterministic tools for repeatable operations:

- Use `search` then `fetch` for citation-compatible catalog discovery. The returned URL identifies the catalog source; `metadata.provider_url` identifies the provider link.
- Use `catalog_search` for catalog-level category and policy filters.
- Use `route_query` before broad multi-step requests.
- Use `provider_profile`, `compare_services`, `estimate_cost`, `check_capacity`, `compliance_filter`, `audit_risks`, `design_architecture`, and `plan_migration` for their corresponding deterministic stages.
- Use `compare_profiles` and `compare_catalog_snapshots` for change analysis.
- Use `refresh_catalog` only when a fresh local snapshot is required; it writes only plugin cache data and fetches only the operator-configured upstream source.
- Use `render_comparison` only after final candidates are prepared. Do not use the widget as a discovery or scoring engine.

Continue using web/provider-controlled sources for current verification. The MCP catalog tools do not convert catalog claims into provider-verified facts.

## Evidence labels

Use one of these labels for every material claim:

- `catalog-claim`: present in free-for.dev only.
- `provider-verified`: confirmed by current provider pricing, docs, terms, status, or policy pages.
- `derived`: calculated from verified numeric inputs.
- `unknown`: insufficient evidence.
- `conflict`: reliable sources or current provider pages disagree.

Never convert `unknown` into a positive result.

## Decision rules

- Hard constraints are pass/fail and override weighted scoring.
- Prefer provider-controlled sources for quotas, pricing, region availability, card requirements, deletion policy, commercial terms, privacy documents, and deprecation status.
- Never call a service GDPR compliant merely because it has an EU region or DPA.
- Distinguish zero current charge from zero billing risk.
- Distinguish a free tier from a free trial.
- Distinguish open-source-only benefits from generally available free plans.
- If pricing is dimensional, model each material dimension separately.
- Evidence completeness is not a provider quality score.
- Do not recommend an architecture as production-ready if material quotas, failure domains, backups, regions, or billing behavior remain unknown.

## Default output

### Requirements
Summarize capability, workload, scale, hard constraints, preferences, and unknowns.

### Candidate matrix
For each candidate provide capability fit, verified free limits, billing trigger, region/privacy evidence, operational risks, lock-in notes, and evidence status.

### Architecture or migration impact
Include topology, failure-domain, exportability, or migration implications when they affect the choice.

### Recommendation
Name a winner only if it passes hard constraints and has adequate evidence. Otherwise state that no verified winner exists.

### Verification gaps
List only facts that could materially change the decision.

## Upstream contribution restriction

The free-for.dev repository states that AI-generated edits are not accepted. Do not generate or submit an upstream pull request, contribution patch, or contribution text intended to be represented as human-authored. Analysis and private change detection are allowed.

## Resources

Read `references/routing.md` for specialist routing and `references/evidence-policy.md` for evidence standards.
