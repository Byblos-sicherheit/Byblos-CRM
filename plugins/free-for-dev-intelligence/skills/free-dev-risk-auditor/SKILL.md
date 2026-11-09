---
name: free-dev-risk-auditor
description: Audit one or more free-tier services or a proposed free-for.dev stack for billing exposure, trial mismatch, commercial-use restrictions, egress, inactivity, data residency, backups, export, support, security, stale verification, and vendor lock-in. Use for business, production, privacy-sensitive, compliance-sensitive, or cost-control reviews before adopting a free service.
---

# Free Dev Risk Auditor

## Principle

Free price is not the same as low operational risk. Audit explicit facts and preserve unknowns. Do not score absent evidence as safe.

## Workflow

1. Define context:
   - use: personal, open-source, internal, or commercial;
   - stage: prototype, MVP, or production;
   - data sensitivity: normal, high, or regulated;
   - required region;
   - recovery and availability requirements.
2. Use the tier-verifier skill to collect current provider facts.
3. Normalize facts into the schema in `references/audit-schema.md`.
4. Run:

```bash
python scripts/risk_audit.py audit-input.json --date YYYY-MM-DD -o audit-result.json
```

5. Review every automated finding. The script is a deterministic checklist, not a substitute for legal, security, privacy, or accounting review.
6. Add architecture-specific risks such as cross-provider egress, shared identity failure, DNS dependency, rate-limit cascades, and unsupported recovery paths.

## Severity meaning

- `critical`: incompatible with the stated use or creates unacceptable security/data-loss exposure.
- `high`: must be resolved or explicitly accepted before production or commercial use.
- `medium`: material operational limitation requiring a control or documented acceptance.
- `low`: administrative or manageable limitation.

Do not reduce severity merely because the service is free.

## Required audit domains

- durable free tier versus trial or temporary credit;
- commercial and account eligibility;
- card, automatic overage, hard cap, and spend alerts;
- egress and cross-provider transfer;
- inactivity, sleep, suspension, deletion, or reclamation;
- region, privacy, and sensitive-data suitability;
- backup, restore, retention, and export;
- TLS and required security controls;
- support and SLA;
- verification freshness and unresolved unknowns;
- replacement and migration path.

## Output format

### Executive decision
State `accept`, `accept with controls`, `prototype only`, or `reject`, with the decisive reason.

### Findings
Group by severity and service. Include evidence and the required control.

### Unknowns
List missing facts separately. Write `Insufficient data to verify` where evidence is absent.

### Controls and exit triggers
Specify spend caps, alerts, backups, verification cadence, quota thresholds, and replacement triggers.

## Resources

- `scripts/risk_audit.py`: deterministic risk classification from supplied facts.
- `references/audit-schema.md`: input fields and allowed values.
- `references/risk-taxonomy.md`: audit domains and control examples.
## Specialist handoff

Use `free-dev-cost-estimator` for numeric paid-transition modeling and `free-dev-compliance-filter` for evidence-based EU/privacy procurement filters.

