# CLAUDE.md

Project guidance for Claude Code.

## Installed Claude Code plugins & skills

This project vendors the following Claude Code plugins/skills under `.claude/`
(see `skills-lock.json` for the full manifest and sources):

| Plugin/Skill | Path | What it does | Trigger |
|---|---|---|---|
| `claude-ads` | `.claude/plugins/claude-ads/` | Paid-media audits/plans/creative workflows across Google, Meta, TikTok, LinkedIn, Microsoft, Apple, Amazon, YouTube, Reddit, Pinterest, Snapchat, X | invoke via its skills, e.g. `/ads-audit` |
| `taste-skill` | `.claude/plugins/taste-skill/` | Frontend design taste (brutalist, minimalist, soft, redesign, stitch, …) | ask for a design/redesign and reference a taste, e.g. "brutalist" |
| `caveman` | `.claude/plugins/caveman/` | Ultra-compressed communication mode (fewer output tokens) | activated via its own SessionStart/UserPromptSubmit hooks once the plugin is enabled |
| `clone-website` | `.claude/skills/clone-website/SKILL.md` | Reverse-engineers a target website into a clean Next.js codebase | `/clone-website <url>` |
| `everything-claude-code` (overview only) | `.claude/skills/everything-claude-code/SKILL.md` | Summary/pointer skill for the much larger ECC project | see below |

### About ECC (Everything Claude Code)

The uploaded `ECC-main.zip` is a third-party zip re-upload of
[affaan-m/ECC](https://github.com/affaan-m/ECC), a ~4,500-file, 889-skill
cross-harness collection. ECC's own README explicitly warns that **third-party
re-uploads/unofficial mirrors are not reviewed and may contain malware**, and
that it should only be installed from official channels (its GitHub repo, the
`ecc-universal`/`ecc-agentshield` npm packages, the GitHub App, or the plugin
slug `ecc@ecc`).

To avoid vendoring ~30 MB of unverified third-party content (with its own
hooks/workflows) straight into this repo, only the small overview skill was
copied in. To install the full collection, run inside Claude Code:

```
/plugin marketplace add affaan-m/ECC
/plugin install ecc@ecc
```

### Intentionally not installed

A few items from the same upload batch were **not** installed here:

- `fable-capability-orchestrator` skill — built on top of an unverifiable
  document that presents itself as an internal/leaked Anthropic system
  prompt for another Claude model. Not adopted as a behavior override.
- A JetBrains personal license key and an unrelated Android app backup
  (containing a hashed password and a SQLite database) that were bundled in
  the same upload — these are not Claude Code artifacts and were excluded
  for security reasons; they were never committed to this repo.
