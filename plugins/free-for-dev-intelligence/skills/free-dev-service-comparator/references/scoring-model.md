# Scoring model

Default weights:

- capability_fit: 3.0
- quota_fit: 2.5
- billing_safety: 2.0
- region_fit: 1.5
- operations: 1.5
- portability: 1.0
- evidence: 2.0

The final score is the weighted mean of present numeric fields, minus a small penalty for missing scored dimensions. Hard constraints are evaluated before ranking.
