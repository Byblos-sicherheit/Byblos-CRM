---
name: engineering
description: "Full software engineering skill suite — merged from agent-skills (23 skills). Use for: implementing features, code review, testing, refactoring, CI/CD, debugging, performance optimization, API design, documentation, git workflow, security hardening, incremental delivery, spec-driven development, and context engineering. Routes internally to the right references based on the sub-task."
---

# Engineering Suite

Covers the full software development lifecycle. This skill merges 23 engineering sub-skills into a single smart entry point — it reads only the references relevant to the active task.

## Sub-skill Routing

| User intent | References to load |
|---|---|
| Implementing a feature or change | `references/incremental-implementation.md` |
| Code review, quality, correctness | `references/code-review.md` |
| Writing tests, TDD | `references/testing.md` |
| Designing APIs or interfaces | `references/api-design.md` |
| Frontend UI, React, CSS | `references/frontend.md` |
| Performance bottlenecks | `references/performance.md` |
| Security hardening, OWASP | `references/security.md` |
| Git workflow, branching, PRs | `references/git-workflow.md` |
| CI/CD pipelines, deployment | `references/ci-cd.md` |
| Observability, logging, metrics | `references/observability.md` |
| Documentation, ADRs | `references/documentation.md` |
| Debugging, error recovery | `references/debugging.md` |
| Refactoring, simplification | `references/simplification.md` |
| Deprecation, migration | `references/migration.md` |
| Planning, task breakdown | `references/planning.md` |
| Context setup for new session | `references/context-engineering.md` |
| Spec-driven development | `references/spec-driven.md` |
| Source-driven development | `references/source-driven.md` |
| Shipping, launch readiness | `references/shipping.md` |
| Browser testing, DevTools | `references/browser-testing.md` |
| Interview preparation | `references/interview.md` |
| Idea refinement | `references/idea-refine.md` |

## Universal Engineering Principles

These apply regardless of which sub-task is active:

### Incremental Delivery
Build in thin vertical slices — implement one piece, test it, verify it, then expand.
Never implement an entire feature in one pass. Each increment must leave the system in a working, testable state.

**The increment cycle:** Implement → Test → Verify → Commit → next increment

### Context Hierarchy
Feed agents the right information at the right time:
1. Rules files (CLAUDE.md) — always loaded, project-wide
2. Spec / architecture docs — loaded per feature
3. Relevant source files — loaded per task
4. Conversation history — most transient

### Code Quality Defaults
- No comments unless the WHY is non-obvious (hidden constraint, subtle invariant, bug workaround)
- No error handling for scenarios that cannot happen — trust internal guarantees
- No premature abstraction — three similar lines beats a speculative helper
- Validate only at system boundaries (user input, external APIs)
- No half-finished implementations

### Definition of Done
A task is done when:
- [ ] The code works (tests pass or manual verification complete)
- [ ] The change is the minimum needed — no scope creep
- [ ] No new security vulnerabilities introduced
- [ ] Commit message explains WHY, not what

## References

Load `references/definition-of-done.md` and `references/security-checklist.md` on every significant implementation task.
