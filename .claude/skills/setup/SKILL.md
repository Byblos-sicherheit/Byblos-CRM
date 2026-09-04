---
name: setup
description: "Claude Code environment analyzer and automation recommender — derived from claude-code-setup (official Anthropic plugin). Use when configuring Claude Code for a new project, asking for automation recommendations, or optimizing the current project's Claude setup. Analyzes the codebase and suggests top 1-2 automations across 5 categories."
---

# Setup — Claude Code Environment Optimizer

Analyzes the current project and recommends the top 1-2 automations in each of 5 categories. Read-only — recommends but does not modify files directly.

## 5 Automation Categories

### 1. MCP Servers
External integrations that give Claude access to external tools and data.

Detection signals:
- Project uses databases (Supabase, PlanetScale, PostgreSQL) → database MCP
- Project uses GitHub heavily → GitHub MCP already configured?
- Project needs web search → search MCP
- Project uses Figma / design tools → Figma MCP
- Project has API calls to specific services → check if MCP exists

### 2. Skills
Packaged expertise for recurring task types in this project.

Detection signals:
- Python/Django project → suggest: test-driven-development, code-review skill
- Infrastructure files (docker-compose, k8s) → suggest: infrastructure skill
- Animation / frontend heavy → suggest: animation skill
- Multi-developer project → suggest: meta-harness for agent teams
- Skills already in CLAUDE.md → check for gaps

### 3. Hooks
Automatic actions on Claude Code events (SessionStart, PostToolUse, Stop...).

Detection signals:
- `package.json` with test scripts → PostToolUse: run tests after edits
- Linting config (.eslintrc, .ruff.toml) → PostToolUse: run linter after edits
- Pre-commit hooks in `.pre-commit-config.yaml` → verify hooks are triggering
- Build system → PostToolUse: run type-check after edits

### 4. Subagents
Specialized reviewers and parallel workers for this project.

Detection signals:
- Complex codebase with multiple domains → suggest domain-expert subagents
- Security-sensitive code → suggest security-reviewer subagent
- Heavy frontend + backend split → suggest FE and BE specialist agents

### 5. Slash Commands
Quick workflow shortcuts for common operations in this project.

Detection signals:
- Repetitive deploy commands → `/deploy` slash command
- Frequent database migrations → `/migrate` slash command
- Common debug sequences → `/debug` slash command

## Analysis Workflow

1. Scan project root: package.json, pyproject.toml, docker-compose.yml, .github/, CLAUDE.md
2. Identify tech stack, external services, CI/CD setup
3. Check for existing .claude/ configuration (skills, agents, hooks already set up)
4. Generate top 1-2 recommendations per category with:
   - **What**: the specific automation
   - **Why**: what problem it solves for this project
   - **How**: exact config or command to set it up

## Output Format

```
## Claude Code Setup Recommendations — <project-name>

### Current Setup
- Skills: <list or "none">
- Agents: <list or "none">  
- Hooks: <list or "none">

### Recommended Automations

**MCP Servers** (top 1-2)
1. <name>: <why it fits this project> | Setup: `claude mcp add <...>`

**Skills** (top 1-2)
1. <name>: <why it fits> | Already in suite: yes/no

**Hooks** (top 1-2)
1. <event> → <command>: <why it helps>

**Subagents** (top 1-2)
1. <name>: <role and trigger>

**Slash Commands** (top 1-2)
1. /<name>: <what it does>
```
