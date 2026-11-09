---
name: free-dev-catalog-search
description: Search, filter, and shortlist services from the free-for.dev catalog for a concrete developer, DevOps, infrastructure, API, hosting, database, monitoring, security, collaboration, AI, or SaaS need. Use when the user asks for free-tier tools, alternatives, category discovery, services with specific limits, no-card options, commercial-use candidates, or a structured export from a current free-for.dev README snapshot.
---

# Free Dev Catalog Search

## Core rule

Treat free-for.dev as a discovery index, not as current pricing authority. Quote its claim as a catalog claim and clearly separate it from a verified provider claim.

## Workflow

1. Resolve the user's actual workload and constraints:
   - capability or category;
   - expected usage scale;
   - commercial or personal use;
   - region or data residency;
   - card requirement tolerance;
   - open-source/public-project eligibility;
   - acceptable inactivity, sleep, or support constraints.
2. Obtain a current official source snapshot:
   - preferred source: `https://github.com/ripienaar/free-for-dev/blob/master/README.md` or its raw form;
   - accept a user-supplied Markdown snapshot;
   - do not rely on a bundled service list because limits change.
3. For local processing, run:

```bash
python scripts/catalog_tool.py stats README.md
python scripts/catalog_tool.py search README.md --query "managed postgres" --commercial --exclude-card-required --limit 10
```

4. Search one capability at a time. For a full stack, invoke the stack-planning skill rather than combining unrelated terms in one query.
5. Rank candidates by requirement fit, not by popularity.
6. Remove any entry that explicitly violates a hard constraint.
7. For final recommendations, verify the top candidates with the tier-verifier skill against provider-controlled pricing or documentation pages.

## Search behavior

- Use category aliases from `references/category-map.md`.
- Interpret script flags as weak textual signals only. Absence of a flag is not proof of absence.
- Do not infer commercial permission, data residency, SLA, support, privacy compliance, or hard spending caps from silence.
- Do not call a trial a free tier.
- Prefer candidates with explicit quotas over vague wording such as “generous free plan.”
- Prefer direct provider pages over affiliate, comparison, or reposted pages.
- If the user requests “completely free,” state that free tiers may change and distinguish zero-price entry from zero financial risk.

## Output format

Use this structure unless the user asks for another format:

### Requirement fit
A concise statement of the interpreted workload and hard constraints.

### Shortlist
For each candidate provide:
- service and category;
- catalog claim;
- fit rationale;
- disqualifiers or unknowns;
- verification status: `catalog-only`, `partially verified`, or `verified`;
- source links.

### Decision
Name the strongest candidate only when the evidence supports a decision. Otherwise identify what remains unverified.

## Quality checks

Before answering:
- confirm every shortlisted item belongs to the requested capability;
- exclude explicitly non-commercial options for a commercial workload;
- flag card-required, trial, open-source-only, personal-only, region, and inactivity signals;
- verify all limit claims that materially affect the decision;
- never present a catalog line as a contractual guarantee.

## Resources

- `scripts/catalog_tool.py`: parse, summarize, and search a Markdown snapshot.
- `references/category-map.md`: current category inventory and common query aliases.
- `references/source-policy.md`: source hierarchy, freshness, and claim labeling.
## Specialist handoff

- Use `free-dev-service-comparator` after discovery when several verified candidates remain.
- Use `free-dev-compliance-filter` for EU, DPA, residency, or GDPR evidence requirements.
- Use `free-dev-alternative-finder` when a named incumbent must be replaced.
- Use `free-dev-exporter` for machine-readable output.

