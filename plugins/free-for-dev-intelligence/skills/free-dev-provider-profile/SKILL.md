---
name: free-dev-provider-profile
description: Build and validate an evidence dossier for one developer-service provider or product, recording free-tier status, billing triggers, quotas, regions, privacy/legal documents, exportability, inactivity behavior, backups, SLA, and source provenance without turning missing evidence into positive claims. Use when a provider needs due diligence, a reusable decision record, evidence completeness scoring, conflict detection, or normalized inputs for comparison, compliance, cost, risk, or architecture workflows.
---

# Free Dev Provider Profile

## Workflow

1. Collect provider-controlled evidence for material facts.
2. Record each fact as a claim with field, value, source type, source URL, and verification date.
3. Run `scripts/provider_profile.py` to normalize claims and identify conflicts or gaps.
4. Treat evidence completeness as documentation coverage only, never as a quality or compliance score.
5. Pass the normalized dossier to comparison, compliance, cost, risk, architecture, or migration skills.

## Required rules

- Do not mark GDPR compliance from an EU region or DPA alone.
- Do not infer commercial permission from a public free-tier page unless terms support it.
- Do not infer `no card required` from a signup page that merely omits card language.
- Mark conflicting current provider claims as `conflict` until resolved.

## Resources

- `scripts/provider_profile.py`: normalize evidence claims and calculate coverage.
- `references/profile-schema.md`: supported fields and source types.
