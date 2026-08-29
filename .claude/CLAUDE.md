# Byblos Universal Skill Suite

## Active Skills

This repository uses the **Byblos Universal Skill Suite** — a merged collection of 15 skill domains.

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
| "UI design", "interface", "تصميم واجهة", "make it premium", "redesign", "frontend", "React component", "Tailwind", "RTL design", "accessibility", "responsive", "color system", "typography", "dashboard layout" | `/interface-design` |
| "MongoDB", "Redis", "Cassandra", "DynamoDB", "Neo4j", "NoSQL", "polyglot database", "document store", "graph database", "schema design", "data modeling", "partition key" | `/nosql` |
| "security audit", "pentest", "vulnerability", "OWASP", "threat model", "hardening", "CVE", "exploit", "CTF", "injection", "XSS", "audit code" | `/security-audit` |
| "marketing plan", "copywriting", "email campaign", "ad creative", "SEO strategy", "growth", "landing page", "lead magnet", "referral program", "social media", "PR", "CRO", "onboarding flow", "pricing strategy" | `/marketing` |
| "playwright", "e2e test", "browser test", "automate browser", "end-to-end", "test this flow", "visual regression", "page object" | `/playwright` |
| "IT analysis", "technical audit", "port table", "DNS config", "network diagram", "architecture diagram", "IT screenshot", "infographic analysis", "troubleshooting guide", "study notes" | `/technical-it-analyst` |
| "SEO audit", "keyword research", "Core Web Vitals", "schema markup", "local SEO", "backlink", "sitemap", "meta tags", "programmatic SEO", "search ranking" | `/seo` |

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
