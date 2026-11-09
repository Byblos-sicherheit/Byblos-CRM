# Specialist routing

| User intent | Primary skill | Follow-up skills |
|---|---|---|
| Broad/mixed request | free-dev-query-router | route to specialists |
| Repeated/large catalog search | free-dev-catalog-index | catalog-search, tier-verifier |
| Find free services | free-dev-catalog-search | tier-verifier, service-comparator |
| Build a provider evidence dossier | free-dev-provider-profile | tier-verifier, compliance-filter |
| Build a full stack | free-dev-stack-planner | architecture-designer, verifier, risk-auditor, cost-estimator |
| Review topology/failure domains | free-dev-architecture-designer | risk-auditor, cost-estimator |
| Is this free tier still current? | free-dev-tier-verifier | provider-profile, risk-auditor |
| Compare providers | free-dev-service-comparator | verifier, compliance-filter |
| EU / GDPR / DPA / residency | free-dev-compliance-filter | verifier, provider-profile, risk-auditor |
| What happens above the free quota? | free-dev-cost-estimator | verifier |
| Replace a rejected provider | free-dev-alternative-finder | comparator, verifier |
| Move to another provider | free-dev-migration-planner | alternative-finder, verifier |
| Update catalog snapshot | free-dev-live-sync | catalog-index, catalog-diff |
| Export results | free-dev-exporter | none |
| Catalog change history | free-dev-catalog-diff | tier-verifier |
| Monitor a shortlist for material changes | free-dev-change-watch | live-sync, tier-verifier |

Prefer one primary skill plus only the follow-ups required to make the decision reliable.
