# Evidence & Confidence Matrix

Use this to assess and communicate confidence levels in facts, recommendations, and outputs.

## Confidence Levels

| Level | Label | Meaning |
|---|---|---|
| ★★★ | VERIFIED | Confirmed by running code, official docs, or direct observation |
| ★★☆ | PLAUSIBLE | Strongly supported by evidence but not directly tested |
| ★☆☆ | ASSUMED | Reasonable inference from context — not verified |
| ✗ | UNKNOWN | Insufficient data — explicitly state what's missing |

## Citation Rules

1. **Facts from official docs** → cite the doc/version (e.g. "per RouterOS 7.15 docs")
2. **Facts from running code** → state what was run and what the output was
3. **Design patterns** → cite the source (e.g. "from agent-skills incremental-implementation pattern")
4. **Assumptions** → prefix with "Assuming:" and flag as ★☆☆
5. **Gaps** → state "Insufficient data to verify: [specific fact needed]"

## What Never to Invent

Under no circumstances should these be invented:
- IP addresses, VLAN IDs, interface names
- Credentials, API keys, passwords, tokens
- Customer data, real names, contact info
- Test results (never claim tests passed without running them)
- Config values specific to a production system
- Versions of running software (always check if you can)

## Distinguishing Claim Types

| Type | Example | How to label |
|---|---|---|
| Engineering fact | "Python 3.12 supports match-case" | State directly, cite docs if version-specific |
| Product claim | "Service X offers 10GB free storage" | "X claims..." — verify before scoring |
| Company claim | "Byblos handles X type of contract" | "Per Byblos documentation..." |
| Assumption | "I assume the DB is PostgreSQL" | "Assuming PostgreSQL — confirm before proceeding" |
| Gap | "I don't know the current server OS version" | "Insufficient data: need OS version" |

## Evidence Quality by Source

| Source | Trust level | Notes |
|---|---|---|
| Running the command / code | Highest | Runtime evidence is authoritative |
| Official vendor documentation | High | Check version match |
| GitHub source code | High | For open-source tools |
| Public blog post / tutorial | Medium | May be outdated |
| AI memory / training data | Low | Always verify against live sources |
| User's description of their system | Medium | May be incomplete — ask clarifying questions |
