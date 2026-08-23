# Debugging Protocol

## 1. Define the failure precisely

Record:
- Expected behavior
- Actual behavior
- Exact error, status, output, or symptom
- Environment and version
- Reproduction steps
- Frequency and first known occurrence
- Recent relevant changes

## 2. Reproduce

Use the smallest reliable reproduction. If reproduction is impossible, collect logs, traces, inputs, timestamps, and environment differences. Label unverified hypotheses as hypotheses.

## 3. Localize the layer

Trace the request or data through:
- User interface
- Client state
- Network/API
- Authentication/authorization
- Application/domain logic
- Database/cache/queue
- External service
- Build/runtime/platform

Find the first point where observed state diverges from expected state.

## 4. Rank hypotheses

Rank by evidence, likelihood, and cost to test. Test one discriminating variable at a time. Avoid random edits.

## 5. Fix the root cause

A valid fix:
- Restores the intended contract
- Handles the triggering boundary case
- Does not weaken validation or tests
- Avoids hiding the error
- Preserves compatibility unless intentionally changed

## 6. Prove the fix

- Add a regression test that fails before the fix and passes after it.
- Run the narrow test first, then affected suites and static checks.
- Test neighboring boundary cases.
- Inspect logs and output, not only exit status.

## 7. Prevent recurrence

When proportional, add:
- Stronger type/schema constraint
- Validation
- Monitoring or alerting
- Documentation or runbook
- Safer default
- CI check

## Anti-patterns

Do not:
- Catch and ignore exceptions to make the symptom disappear.
- Add arbitrary sleeps instead of fixing synchronization.
- Disable failing tests without proving the contract changed.
- Blame a dependency without a reproducer or evidence.
- change several unrelated variables and call the result diagnosed.
