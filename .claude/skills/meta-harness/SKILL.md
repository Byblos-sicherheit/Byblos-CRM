---
name: meta-harness
description: "Agent team factory — derived from harness skill. Use when: (1) building an agent team for a domain, (2) designing multi-agent orchestration, (3) expanding an existing harness with new agents/skills, (4) auditing or maintaining an existing harness. Generates .claude/agents/ and .claude/skills/ files with six pre-defined team-architecture patterns."
---

# Meta-Harness — Agent Team Factory

Turns a domain description into a working agent team with their skills, CLAUDE.md pointers, and orchestration wiring.

## Six Team Architecture Patterns

| Pattern | When to use | Structure |
|---|---|---|
| **Pipeline** | Sequential stages, each output feeds next | A → B → C → output |
| **Fan-out / Fan-in** | Parallel independent work → synthesis | Orchestrator → [A, B, C] → Synthesizer |
| **Expert Pool** | Domain routing to specialists | Router → [Domain Expert A, B, C] |
| **Producer-Reviewer** | Quality gate on output | Producer → Reviewer → (fix loop or accept) |
| **Supervisor** | Dynamic task assignment, monitoring | Supervisor → [Workers] |
| **Hierarchical Delegation** | Complex nested orchestration | Top → [Mid-level] → [Workers] |

## Phase 0: Current-State Audit (always first)

Before building anything:
1. Read `.claude/agents/`, `.claude/skills/`, `CLAUDE.md` in the target project
2. Classify: New build / Expand existing / Maintain/fix existing
3. Report audit result to user, confirm execution plan

**Drift detection:** Compare agents/skills list against CLAUDE.md pointers — mismatches = drift that must be resolved before expanding.

## Phase 1: Domain Analysis

1. Extract domain from user request
2. Identify core task types (generate, validate, edit, analyze, review...)
3. Map to pattern candidates (from Phase 0 + new requirements)
4. Scan codebase: tech stack, data models, key modules
5. Gauge user experience level — adjust communication tone accordingly

## Phase 2: Team Architecture Design

**Default: Agent Team.** Use SendMessage + TaskCreate for intra-team coordination.

Decision:
- ≥2 domains working simultaneously → Agent Team
- Single domain, results returned to main → Sub-agent
- Mixed phases → Hybrid (specify mode per phase in orchestrator)

## Phase 3: Agent File Generation

For each agent, generate `.claude/agents/<name>.md`:

```markdown
---
name: <agent-name>
description: <one-line trigger description>
model: claude-sonnet-5
tools: [Read, Edit, Write, Bash, Glob, Grep]
---

# <Agent Name>

## Role
<what this agent does>

## Trigger
<when to invoke this agent>

## Workflow
<numbered steps>

## Output Contract
<what this agent produces and hands off>
```

## Phase 4: Skill File Generation

For each agent's skill, generate `.claude/skills/<skill-name>/SKILL.md`:
- Follow the standard SKILL.md frontmatter format
- Load references lazily (only what the task needs)
- Include a routing table if the skill covers multiple sub-tasks

## Phase 5: Orchestrator Skill

Generate the orchestrator skill that:
- Routes incoming tasks to the right agent
- Handles inter-agent communication via SendMessage
- Manages shared task list via TaskCreate/TaskUpdate
- Aggregates and synthesizes outputs

## Phase 6: CLAUDE.md Update

Add minimal pointers to CLAUDE.md:
- Trigger rules → which skill/agent handles what
- Change history (date + what changed)
- Production safety gate reminder if applicable

## Continuous Evolution

After each team run:
- Capture what worked and what didn't
- Update agent definitions, skill references, and CLAUDE.md
- The harness is a living system, not a one-time setup
