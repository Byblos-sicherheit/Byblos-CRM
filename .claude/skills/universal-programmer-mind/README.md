# Universal Programmer Mind

A multilingual, cross-platform Agent Skill for disciplined software engineering and technology decision-making across requirements, architecture, implementation, debugging, review, testing, security, performance, databases, APIs, DevOps, deployment, migration, documentation, vendor evaluation, and executive adoption cases.

## Languages

- Arabic
- English
- German
- Bilingual output using a requested pair; Arabic + English is the fallback pair

## Package contents

- `SKILL.md`: canonical Agent Skill
- `agents/openai.yaml`: ChatGPT display metadata
- `references/`: detailed engineering procedures, executive technology-adoption workflow, and a current-source Develocity evaluation model
- `scripts/project_inventory.py`: read-only repository inventory
- `AGENTS.md`: OpenAI Codex and compatible repository-agent wrapper
- `CLAUDE.md`: Claude Code persistent wrapper
- `GEMINI.md`: Gemini CLI persistent wrapper
- `system-prompt.md`: portable fallback for assistants without Agent Skills

## Install

### ChatGPT

Upload `skill.zip` from the Skills interface using Create → Upload from computer. Availability and workspace controls depend on the account and administrator settings.

### Claude.ai

Upload the skill through Customize → Skills when Skills and code execution are enabled for the account or organization.

### Claude Code

Copy the directory to one of:

```text
.claude/skills/universal-programmer-mind/
~/.claude/skills/universal-programmer-mind/
```

Optionally copy `CLAUDE.md` to the repository root for persistent guidance.

### Gemini CLI

Install or link the directory:

```bash
gemini skills install /path/to/universal-programmer-mind
gemini skills link /path/to/universal-programmer-mind
```

Or copy it to one of:

```text
.gemini/skills/universal-programmer-mind/
~/.gemini/skills/universal-programmer-mind/
.agents/skills/universal-programmer-mind/
~/.agents/skills/universal-programmer-mind/
```

Then run `/skills reload` and `/skills list`.

Optionally copy `GEMINI.md` to the workspace root for persistent guidance.

### OpenAI Codex

Copy `AGENTS.md` to the repository root. Where Agent Skills are supported, install the complete directory instead of using only the wrapper.

### Other assistants

Paste `system-prompt.md` into custom instructions or a system-instruction field. This fallback cannot create tool access; the target platform must provide file, shell, web, Git, database, or connector capabilities.

## Repository inventory script

Read-only usage:

```bash
python scripts/project_inventory.py /path/to/project
python scripts/project_inventory.py /path/to/project --json
```

It detects common languages, manifests, lockfiles, CI configuration, instruction files, test directories, and likely project commands without reading secret values or executing project code.

## Security

Review any skill before installation. The included script is read-only and does not execute project scripts. Tool permissions remain controlled by the target platform.

## Executive technology-adoption cases

Use the skill for leadership memos, vendor evaluations, business cases, board narratives, and closing arguments. The workflow verifies current official sources, separates capability from vendor claims and organizational inference, maps technical mechanisms to business outcomes, and builds an ROI model without fabricating internal numbers.

For Develocity evaluations, the package includes a dedicated source map, governance/efficiency/DORA causal model, ROI inputs, pilot design, and worked pitch structure. Product claims must still be refreshed before external use.

## Executive decision toolkit

Version 5 adds an approval-oriented layer beyond persuasive writing:

- pilot design and attribution controls;
- transparent ROI equations and a calculator that requires supplied inputs;
- preweighted scorecard evaluation with mandatory gates;
- executive objection handling and red-team questions;
- a reusable Develocity decision memo and CSV pilot scorecard;
- a dated Develocity source snapshot that must be refreshed before external use.

Example ROI calculation:

```bash
python scripts/executive_roi_model.py inputs.json --format markdown --output roi.md
```

Example pilot scoring:

```bash
python scripts/pilot_scorecard.py scorecard.json --output result.json
```
