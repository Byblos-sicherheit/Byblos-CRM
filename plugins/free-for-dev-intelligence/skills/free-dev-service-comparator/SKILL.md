---
name: free-dev-service-comparator
description: Compare and rank free-tier developer services against explicit workload constraints using hard disqualifiers plus transparent weighted scoring. Use when the user has two or more candidate providers and asks which is best, wants a decision matrix, needs ranking by quotas, card requirements, regions, privacy evidence, portability, operational risk, or wants machine-readable comparison output.
---

# Free Dev Service Comparator

## Rules

1. Verify time-sensitive provider facts before treating them as scoring inputs.
2. Apply hard constraints before scoring. A failed hard requirement is disqualified regardless of score.
3. Use explicit `unknown` values instead of optimistic assumptions.
4. Penalize unknown evidence when the missing fact is decision-critical.
5. Keep the scoring model visible and adjustable.

## Deterministic comparison

Prepare JSON using `references/input-schema.md`, then run:

```bash
python scripts/compare_services.py services.json --constraints constraints.json
```

The script is a ranking aid, not an evidence collector. Feed it provider-verified facts whenever possible.

## Default scoring dimensions

- capability fit;
- quota headroom;
- billing safety;
- region/data-residency fit;
- operational reliability signals;
- portability/lock-in;
- documentation/evidence confidence.

## Output

Report disqualifications first, then ranked viable candidates with score components and evidence gaps. Never hide that weights are subjective.

## Resources

- `scripts/compare_services.py`: deterministic hard-filter and weighted-ranking engine.
- `references/input-schema.md`: JSON input contract.
- `references/scoring-model.md`: interpretation and default weights.
