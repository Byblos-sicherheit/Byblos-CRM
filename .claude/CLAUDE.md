# Byblos Universal Skill Suite

## Active Skills

This repository uses the **Byblos Universal Skill Suite** — a merged collection of 8 skill domains.

### Skill Triggers

| Trigger words / intent | Skill to invoke |
|---|---|
| "بناء فريق وكلاء", "harness", "agent team", "meta-skill", "orchestrate agents" | `/meta-harness` |
| "راقب المهارات", "observer", "improve skill", "task-observer", "self-improve" | `/meta-observer` |
| "إعداد Claude", "setup recommendations", "ما الأتمتة المقترحة", "configure hooks" | `/setup` |
| "implement", "refactor", "test", "review", "code quality", "CI/CD", "debugging", "performance", "API design", "documentation", "deploy", "git", "incremental", "spec", "context engineering" | `/engineering` |
| "network", "MikroTik", "RouterOS", "ISP", "RADIUS", "VPN", "Ubuntu server", "Docker", "Kubernetes", "K3s", "firewall", "VLAN", "infrastructure" | `/infrastructure` |
| "free tier", "free service", "compare services", "migration plan", "stack planner", "free alternative", "developer tools cost" | `/free-services` |
| "lottie", "animation", "رسوم متحركة", "JSON animation", "Bodymovin", "Skottie", "loader", "icon animation" | `/animation` |
| "intervention plan", "Interventionsplan", "Sicherheitskonzept", "Objektkonzept", "security concept", "Byblos document", "بياتسن", "خطة تدخل" | `/byblos-intervention-planner` |

### Orchestrator Rule

When a task spans multiple domains (e.g. "build a CRM feature with tests and deploy it"), invoke `/byblos-master` — it coordinates across skills and can spawn an agent team via `/meta-harness`.

### Production Safety Gate

Before ANY destructive or irreversible action (database migration, force push, server restart, file deletion, credential rotation): **STOP** and read `references/production-safety-gates.md` before proceeding.

### Evidence Discipline

- State facts, product claims, and assumptions separately
- Never invent secrets, IPs, credentials, or test results
- When a fact cannot be verified: state "Insufficient data to verify"
- Treat runtime evidence as authoritative over design assumptions

---

*Byblos Sicherheit & Facility Services — byblossicherheit@gmail.com*
