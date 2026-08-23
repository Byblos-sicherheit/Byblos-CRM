# Platform Adapters

The canonical capability is the directory containing `SKILL.md`, references, scripts, and metadata. Platform wrapper files are included for systems that also support persistent project instructions.

## ChatGPT

Use the packaged `skill.zip` as the skill bundle. In supported ChatGPT accounts, open Skills, choose Create, then upload from the computer. ChatGPT scans uploaded skills before activation. Workspace permissions may control creation, uploading, sharing, or installation.

Canonical official reference:
- https://help.openai.com/en/articles/20001066-skills-in-chatgpt/

## OpenAI Codex and compatible coding agents

Copy `AGENTS.md` to a repository root for persistent project-level instructions. Keep the complete skill directory available when the environment supports Agent Skills. More deeply nested `AGENTS.md` files can define narrower rules for subdirectories.

Canonical official references:
- https://openai.com/index/introducing-codex/
- https://github.com/openai/codex/blob/main/docs/agents_md.md

## Claude.ai

Upload the complete skill directory/archive through the Skills interface when available. Code execution must be enabled for skills that use scripts.

Canonical official references:
- https://support.claude.com/en/articles/12512176-what-are-skills
- https://support.claude.com/en/articles/12512180-use-skills-in-claude

## Claude Code

Install the directory at either:
- Project scope: `.claude/skills/universal-programmer-mind/`
- User scope: `~/.claude/skills/universal-programmer-mind/`

`SKILL.md` is the on-demand skill. `CLAUDE.md` is an optional persistent wrapper for projects that should apply the core discipline continuously.

Canonical official references:
- https://code.claude.com/docs/en/skills
- https://code.claude.com/docs/en/memory
- https://code.claude.com/docs/en/settings

## Gemini CLI

Install or link the complete skill directory. Supported discovery paths include:
- User scope: `~/.gemini/skills/` or `~/.agents/skills/`
- Workspace scope: `.gemini/skills/` or `.agents/skills/`

Useful commands:
- `gemini skills install <url-or-path>`
- `gemini skills link <path>`
- `/skills list`
- `/skills reload`

`GEMINI.md` is an optional persistent wrapper for workspace-wide instructions and can import other Markdown files.

Canonical official references:
- https://geminicli.com/docs/cli/skills/
- https://geminicli.com/docs/cli/creating-skills/
- https://geminicli.com/docs/cli/gemini-md/

## Other assistants

Use, in descending order of preference:
1. Native Agent Skills support: install the entire directory.
2. Repository instruction support: copy `AGENTS.md`, `CLAUDE.md`, or `GEMINI.md` as supported.
3. Custom/system instructions: paste `system-prompt.md`.

Do not assume a platform executes scripts or grants file, shell, web, or connector access. The runtime must expose those tools and permissions.
