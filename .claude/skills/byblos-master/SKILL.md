---
name: byblos-master
description: "Master orchestrator for the Byblos Universal Skill Suite. Use when a task spans multiple domains (engineering + infrastructure + security + deployment), or when the user asks 'what should I do?' without a clear single domain. Routes to the correct sub-skill or spawns an agent team via meta-harness when parallel work is needed."
---

# Byblos Master Orchestrator

The single entry point for complex, multi-domain tasks. Classifies the request, decides whether one skill or a full agent team is needed, then coordinates execution.

## Core Operating Model

1. **Classify** the request using the routing table in `references/task-routing.md`.
2. **Read** `references/production-safety-gates.md` for any task that modifies production state.
3. **Decide** execution mode:
   - Single domain → invoke the matching skill directly.
   - Multi-domain or parallel workstreams → spawn agent team via `/meta-harness`.
   - Ambiguous → clarify the one question that would resolve the routing, then proceed.
4. **Apply** evidence discipline from `references/evidence-matrix.md`: separate facts, claims, and assumptions.
5. **Verify** before claiming completion — run, test, or provide exact validation commands.

## Routing Table (quick reference)

| Domain | Invoke |
|---|---|
| Software engineering, code, tests, CI/CD | `engineering` skill |
| Network, ISP, Linux, Docker, VPN, MikroTik | `infrastructure` skill |
| Free-tier service search, comparison, migration | `free-services` skill |
| Lottie/animation JSON | `animation` skill |
| Agent team design / orchestration | `meta-harness` skill |
| Skill improvement / pattern capture | `meta-observer` skill |
| Claude Code setup recommendations | `setup` skill |
| Byblos intervention/security documents | `byblos-intervention-planner` skill |
| **Multi-domain** | Spawn harness team |

## Agent Team Decision Matrix

Spawn a team (via `/meta-harness`) when:
- Task requires ≥2 domains working simultaneously
- Output of one workstream feeds into another (pipeline pattern)
- Parallel investigation needed (fan-out → synthesis)
- Quality gate requires an independent reviewer

Run single skill when:
- Clear single domain
- Sequential steps, no parallel benefit
- Task fits in one context window

## References

Always load before complex orchestration:
- `references/task-routing.md` — detailed routing rules
- `references/production-safety-gates.md` — safety checklist for risky actions
- `references/evidence-matrix.md` — confidence levels and citation rules
- `references/byblos-context.md` — company context, tech stack, standards
