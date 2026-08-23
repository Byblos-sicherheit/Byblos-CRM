# Audit input schema

```json
{
  "context": {
    "use": "commercial",
    "stage": "production",
    "data_sensitivity": "high",
    "required_region": "EU"
  },
  "components": [
    {
      "name": "Provider Product",
      "trial_only": false,
      "commercial_use": "allowed",
      "card_required": true,
      "auto_overage": true,
      "hard_spend_cap": false,
      "egress_metered": true,
      "inactivity_action": "sleep",
      "data_region": "EU",
      "backup": "manual",
      "export": "standard",
      "support": "community",
      "tls_included": true,
      "verified_on": "2026-08-04",
      "unknowns": []
    }
  ]
}
```

## Allowed values

- `context.use`: personal, open-source, internal, commercial.
- `context.stage`: prototype, MVP, production.
- `context.data_sensitivity`: normal, high, regulated.
- `commercial_use`: allowed, restricted, unknown.
- `inactivity_action`: none, sleep, pause, suspend, delete, reclaim, unknown.
- `backup`: included, manual, paid, none, unknown.
- `export`: standard, proprietary, none, unknown.
- `support`: sla, ticket, community, none, unknown.
- Boolean fields may be `true`, `false`, or `null` where unknown.
- `verified_on`: absolute date in YYYY-MM-DD.

Do not replace unknown values with favorable defaults.
