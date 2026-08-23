# Provider profile schema

Input JSON:

```json
{
  "provider": "Provider name",
  "service": "Product name",
  "claims": [
    {
      "field": "card_required",
      "value": false,
      "source_type": "provider_pricing",
      "url": "https://provider.example/pricing",
      "verified_at": "2026-08-07"
    }
  ]
}
```

Recommended evidence fields: `free_tier`, `trial_only`, `card_required`, `commercial_use`, `free_limits`, `overage_behavior`, `regions`, `dpa`, `subprocessors`, `data_residency`, `inactivity_policy`, `data_deletion`, `backup`, `sla`, `export`, and `support`.

Source types should identify provenance, for example `provider_pricing`, `provider_docs`, `provider_terms`, `provider_privacy`, `provider_dpa`, or `provider_status`.
