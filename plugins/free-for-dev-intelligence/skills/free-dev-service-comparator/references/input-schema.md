# Input schema

`services.json` is an array of objects. Recommended fields:

```json
[
  {
    "name": "Example",
    "capability_fit": 0.9,
    "quota_fit": 0.8,
    "billing_safety": 1.0,
    "region_fit": 0.5,
    "operations": 0.7,
    "portability": 0.6,
    "evidence": 0.9,
    "card_required": false,
    "commercial_allowed": true,
    "eu_region": true
  }
]
```

Scores are numbers from 0 to 1. Boolean hard constraints may be true, false, or omitted when unknown.

`constraints.json` may contain:

```json
{
  "require_no_card": true,
  "require_commercial": true,
  "require_eu_region": false,
  "unknown_hard_constraint_policy": "disqualify",
  "weights": {"capability_fit": 3, "quota_fit": 2}
}
```
