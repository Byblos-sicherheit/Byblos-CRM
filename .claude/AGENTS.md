# Byblos CRM — Agent Instructions

Powered by **Everything Claude Code (ECC) v2.2.0** — 68 specialized agents for production-ready software development.

## Project Context

Byblos CRM is a Python/Flask desktop and web CRM application with SQLite, Docker support, and Windows/Linux packaging.

## Core Principles

1. **Agent-First** — Delegate to specialized agents for domain tasks
2. **Test-Driven** — Write tests before implementation, 80%+ coverage required
3. **Security-First** — Never compromise on security; validate all inputs
4. **Immutability** — Always create new objects, never mutate existing ones
5. **Plan Before Execute** — Plan complex features before writing code

## Available Agents (curated for this project)

| Agent | Purpose | When to Use |
|-------|---------|-------------|
| planner | Implementation planning | Complex features, refactoring |
| architect | System design and scalability | Architectural decisions |
| code-reviewer | Code quality and maintainability | After writing/modifying code |
| security-reviewer | Vulnerability detection | Before commits, sensitive code |
| python-reviewer | Python code review | All Python files |
| django-reviewer | Django/Flask code review | Route handlers, ORM, APIs |
| django-build-resolver | Build, migration, and setup errors | Startup, dependency, migration failures |
| database-reviewer | PostgreSQL/SQLite specialist | Schema design, query optimization |
| doc-updater | Documentation | Updating README, changelogs |
| build-error-resolver | Fix build/type errors | When build fails |

## Agent Orchestration

Use agents proactively:
- Complex feature requests → **planner**
- Code just written/modified → **code-reviewer**
- Security-sensitive code → **security-reviewer**
- Python/Flask logic → **python-reviewer**
- Database schema or queries → **database-reviewer**
- Build errors → **build-error-resolver** or **django-build-resolver**

## Security Guidelines

**Before ANY commit:**
- No hardcoded secrets (API keys, passwords, tokens)
- All user inputs validated and sanitized
- SQL injection prevention (parameterized queries)
- XSS prevention (sanitized HTML output)
- Authentication/authorization verified
- Error messages don't leak sensitive data

## Coding Style

- Python 3.x, PEP 8 compliant
- Functions small (<50 lines), files focused (<800 lines)
- No deep nesting (>4 levels)
- Proper error handling at every level
- No hardcoded values — use config/env vars

## Testing Requirements

**Minimum coverage: 80%**

Run tests: `python -m pytest test_byblos_crm.py -v`

TDD workflow:
1. Write test first (RED)
2. Write minimal implementation (GREEN)
3. Refactor (IMPROVE)

## Git Workflow

**Commit format:** `<type>: <description>`
Types: `feat`, `fix`, `refactor`, `docs`, `test`, `chore`, `perf`, `ci`

**PR workflow:** Analyze full commit history → draft comprehensive summary → include test plan → push with `-u` flag.
