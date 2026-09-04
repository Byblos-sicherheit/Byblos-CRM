# Byblos Company Context

Reference for Claude Code sessions working on Byblos projects.

## Company

**Byblos Sicherheit & Facility Services**
- Security services (Sicherheitsdienst, Objektschutz, Interventionsdienst)
- Facility services (Reinigung, Hausmeisterservice, Entrümpelung)
- Based in Germany
- Contact: byblossicherheit@gmail.com

## Technology Stack (CRM)

**Repositories:**
- `byblos-sicherheit/byblos-crm` — Main CRM application (Python, has Dockerfile)
- `byblos-sicherheit/crm.byblos` — CRM frontend / deployment (Next.js, GitHub Actions)

**Known tech:**
- Python backend (ByblosCRM.spec suggests PyInstaller packaging → desktop app or server)
- Docker support (Dockerfile present)
- GitHub Actions CI/CD
- Windows deployment scripts (.bat files)

## Document Types (Byblos-specific)

German operational documents produced by the `byblos-intervention-planner` skill:
- **Interventionsplan** — Emergency intervention procedure for a specific site
- **Sicherheitskonzept** — Security concept / overall security plan
- **Objektkonzept** — Site-specific operational concept
- **Wachschutzkonzept** — Guard protection concept
- **Notfallplan** — Emergency response plan
- **Reinigungskonzept** — Cleaning service concept
- **Hausmeisterkonzept** — Facility management concept
- **Entrümpelungskonzept** — Clearance/junk removal concept
- **Objektaufnahme** — Site survey / intake form
- **Angebot** — Quotation / offer document

## Code Standards for Byblos Projects

- Language: primarily Python (backend), may include TypeScript/React (frontend)
- Commit messages: descriptive, English or German
- No secrets in code (use .env files, never commit credentials)
- Docker-first deployment where possible
- CI/CD via GitHub Actions

## Skill Suite Installed

This project uses the **Byblos Universal Skill Suite** v2.0.0 (15 skill domains):

**Core Skills (v1.0.0):**
- `/engineering` — Software development (+ Karpathy behavioral guidelines)
- `/infrastructure` — Server and network (MikroTik, Docker, K3s, Ubuntu)
- `/free-services` — Free developer tool selection and migration
- `/animation` — Lottie/Bodymovin JSON animations
- `/meta-harness` — Agent team factory (6 team patterns)
- `/meta-observer` — Skill evolution and self-improvement engine
- `/setup` — Claude Code configuration optimizer
- `/byblos-intervention-planner` — German security/facility documents (separate skill)

**New Skills (v2.0.0):**
- `/interface-design` — UI/UX design with Byblos aesthetic (React, Tailwind, RTL, accessibility)
- `/nosql` — NoSQL and polyglot DB architecture (MongoDB, Redis, Cassandra, DynamoDB, Neo4j)
- `/security-audit` — 6-phase security audit, OWASP, penetration test planning
- `/marketing` — 50+ sub-skills: content, growth, ads, email, SEO, PR, CRO, social
- `/playwright` — Playwright browser testing and automation (E2E, page objects, CI)
- `/technical-it-analyst` — IT material analysis (networking, DNS, Windows, security)
- `/seo` — Technical SEO, local SEO, Core Web Vitals, schema markup, keyword research

## Agents Available

- `orchestrator` — Multi-domain task coordination
- `engineer` — Code implementation
- `infrastructure` — Server/network operations
- `reviewer` — Independent code and security review
