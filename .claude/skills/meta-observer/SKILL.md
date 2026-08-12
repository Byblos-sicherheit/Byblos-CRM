---
name: meta-observer
description: "Skill observer and improvement engine — derived from one-skill-to-rule-them-all / task-observer. Runs continuously during work sessions to detect repeating patterns, notice corrections and preferences, and surface improvement suggestions for existing skills. Use when you want to evolve your skill library over time, capture new patterns, or improve skill quality based on actual usage."
---

# Meta-Observer — Skill Evolution Engine

Watches how skills are used in practice and surfaces concrete improvement recommendations. You review and approve all changes before they are applied.

## Three Core Functions

### 1. Skill Discovery
Detects repeating patterns in the current session that could become new skills.

Signals:
- You typed the same multi-step procedure twice
- You loaded the same references repeatedly without a skill to automate that
- You explained the same domain constraint 3+ times

Output: "New skill candidate: `<name>` — trigger: `<what invokes it>` — core steps: `<what it does>`"

### 2. Skill Improvement
Notices gaps, corrections, and preference drift in existing skills.

Signals:
- A skill produced output you had to correct
- You added a step that the skill didn't include
- A reference was missing from the routing table
- A trigger description was too narrow and you had to manually invoke

Output: "Improvement for `<skill-name>`: `<specific change and why>`"

### 3. Self-Improvement
Captures improvements to this observer's own methodology.

Signals:
- An observation format that proved more actionable
- A detection heuristic that was too noisy or too quiet
- A new principle that emerged from a session

Output: "Observer update: `<what to change in this skill itself>`"

## Session Workflow

At session end (or when explicitly invoked):

1. **Scan session** — review conversation for the three signal types above
2. **Draft observations** — structured log entries:
   ```
   [DATE] [TYPE: discovery|improvement|self]
   Skill: <target skill or "new">
   Observation: <what was noticed>
   Recommendation: <specific change>
   Confidence: high|medium|low
   ```
3. **Present to user** — show only actionable observations (not noise)
4. **Apply on approval** — edit the relevant SKILL.md file(s)
5. **Log the change** — append to `references/observation-log.md`

## Cross-Cutting Principles

Principles that emerge from observations and apply across all skills in the suite:

- Load references lazily — never pre-load the full reference library
- State facts, product claims, and assumptions separately
- Prefer incremental, testable delivery over big-bang implementation
- Every skill should have an explicit routing table when it covers multiple sub-tasks
- Production safety gates apply across all domains, not just infrastructure

## Constraints

- Never apply changes without user approval
- Never delete a skill — mark as deprecated and explain why
- Observations are suggestions, not directives
- Confidence levels must be honest — "low" means "worth considering but uncertain"

## Observation Log

Maintain `references/observation-log.md` as a running journal:
```
## YYYY-MM-DD
- [discovery] New skill candidate: ...
- [improvement] engineering skill: added browser-testing reference to routing table
- [self] Observer: reduced noise by only logging observations with ≥2 supporting signals
```
