# Risk taxonomy and controls

| Domain | Typical risk | Control |
|---|---|---|
| Billing | Card plus automatic overage and no hard cap | hard budget, provider cap, alerts, isolated account |
| Eligibility | commercial, OSS, education, or personal restriction | provider terms verification and documented entitlement |
| Quota | peak usage exceeds one hidden dimension | normalize every limit and maintain headroom |
| Egress | service is free but outbound transfer is paid | co-locate services, estimate transfer, cache, cap usage |
| Inactivity | sleep, pause, deletion, or reclaim | backup, recovery test, accepted cold start, alternative |
| Data | unknown region or subprocessors | plan-specific residency and privacy verification |
| Recovery | no backup, restore, or export | independent backup and migration test |
| Security | TLS, MFA, RBAC, logs, or secrets missing | reject or add compensating controls |
| Support | community-only support in production | internal on-call capability or paid support |
| Lock-in | proprietary API or export | standard protocol, abstraction, documented migration |
| Freshness | old or missing verification | re-verify before deployment and on a defined cadence |
