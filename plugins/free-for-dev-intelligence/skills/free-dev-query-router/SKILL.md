---
name: free-dev-query-router
description: Convert natural-language free-tier and developer-service requests into a structured routing plan containing intents, service categories, hard constraints, decision criteria, required evidence, and specialist skills. Use when a request is broad, ambiguous, combines several goals, or needs deterministic routing before catalog search, verification, comparison, compliance review, cost modeling, architecture design, migration planning, or change monitoring.
---

# Free Dev Query Router

## Workflow

1. Extract the requested capability, workload, geography, commercial context, budget posture, and explicit exclusions.
2. Treat explicit requirements such as no credit card, EU-only processing, no trial, commercial use, or a hard budget as pass/fail constraints.
3. Run `scripts/query_router.py --query "..."` when a reproducible baseline route is useful.
4. Refine the deterministic route with the user's actual wording; the script is a routing aid, not a semantic authority.
5. Send discovery requests to `free-dev-catalog-search` or `free-dev-catalog-index`.
6. Route material provider claims through `free-dev-tier-verifier` before making a final recommendation.
7. Route architecture, migration, monitoring, cost, privacy, or risk questions to their matching specialist.

## Required output

Return:

- primary intent;
- secondary intents;
- candidate service categories;
- hard constraints;
- weighted preferences;
- missing decision inputs;
- specialist routing sequence.

Do not silently convert a preference into a hard constraint or the reverse.

## Resources

- `scripts/query_router.py`: deterministic intent and constraint extraction.
- `references/routing-contract.md`: intent names and routing contract.
