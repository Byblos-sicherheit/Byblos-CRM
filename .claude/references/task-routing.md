# Task Routing Reference

Use this to classify incoming tasks and route them to the correct skill or agent.

## Primary Routing Table

### Engineering Domain
**Keywords:** implement, build, fix, bug, feature, test, refactor, review, API, React, HTML, CSS, Python, TypeScript, JavaScript, database query, CRM logic, form, UI, component, endpoint, migration (code), deploy pipeline, CI, GitHub Actions

**Route to:** `engineering` skill → `engineer` agent

### Infrastructure Domain
**Keywords:** server, network, MikroTik, RouterOS, Ubuntu, Debian, Docker, container, Kubernetes, K3s, VPN, WireGuard, firewall, VLAN, DHCP, NAT, ISP, RADIUS, PPPoE, backup, restore, monitoring, Prometheus, Grafana, Nginx, Caddy, SSL certificate, DNS, Cloudflare

**Route to:** `infrastructure` skill → `infrastructure` agent

### Free Services Domain
**Keywords:** free tier, free alternative, compare services, migration plan, stack planner, quota, cost, service comparison, developer tools, SaaS free, no credit card

**Route to:** `free-services` skill

### Animation Domain
**Keywords:** Lottie, animation, JSON animation, Bodymovin, Skottie, loader, spinner, icon animation, SVG animation, logo animation, motion, رسوم متحركة

**Route to:** `animation` skill

### Agent Team / Orchestration
**Keywords:** agent team, harness, multi-agent, orchestrate, build a team of agents, parallel agents, fan-out, pipeline agents

**Route to:** `meta-harness` skill → `orchestrator` agent

### Skill Evolution
**Keywords:** improve skill, capture pattern, observation, what patterns did you notice, update SKILL.md, meta-observer, skill feedback

**Route to:** `meta-observer` skill

### Claude Code Setup
**Keywords:** Claude Code setup, automation recommendations, hooks, MCP server recommendations, what should I configure, optimize Claude

**Route to:** `setup` skill

### Byblos Documents (German security/facility docs)
**Keywords:** Interventionsplan, Sicherheitskonzept, Objektkonzept, Notfallplan, Wachschutz, Reinigungskonzept, Hausmeisterkonzept, Entrümpelungskonzept, Angebot, Byblos document, security concept, intervention plan

**Route to:** `byblos-intervention-planner` skill

## Multi-Domain Routing

When a task touches 2+ domains, route to `byblos-master` which will:
1. Decompose into domain workstreams
2. Decide if sequential or parallel execution fits better
3. Invoke `meta-harness` if parallel agent team is needed

### Common Multi-Domain Combinations

| Combination | Pattern |
|---|---|
| Engineering + Infrastructure | Pipeline: Engineer builds → Infrastructure deploys |
| Engineering + Security Review | Producer-Reviewer: Engineer implements → Reviewer audits |
| Engineering + Free Services | Sequential: Free Services selects stack → Engineer implements |
| Infrastructure + Security | Fan-out: both run in parallel → Orchestrator merges |

## Ambiguity Resolution

If the domain is unclear, ask **one specific question** that would resolve the routing:
- "Is this a code change or a server/network configuration?"
- "Are you looking to build something, or find an existing free tool?"
- "Is the animation for web UI or a standalone Lottie file?"
