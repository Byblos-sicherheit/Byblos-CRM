# Testing Standards

## Select tests from risk

Use the smallest set that provides credible evidence, then expand according to blast radius.

### Pure logic
- Unit tests for normal, boundary, invalid, and adversarial cases
- Property-based tests when invariants span many inputs

### API or service
- Contract and integration tests
- Authentication/authorization and error-path tests
- Database transaction and migration tests
- Timeout, retry, idempotency, and partial-failure tests where relevant

### User interface
- Component behavior and accessibility checks
- Integration tests for state and API behavior
- End-to-end tests for critical user journeys
- Loading, empty, error, offline, and recovery states

### Data or migration
- Schema validation
- Forward migration and rollback/recovery test when supported
- Representative-volume and data-integrity checks
- Backup/restore rehearsal for critical systems

### Infrastructure or deployment
- Configuration validation
- Build and artifact verification
- Health/readiness checks
- Smoke test in the target-like environment
- Rollback verification

## Test quality

Tests must be:
- Deterministic unless nondeterminism is the property under test
- Independent and isolated
- Focused on observable behavior, not fragile implementation details
- Named to describe the contract
- Able to fail for the defect they claim to cover

## Verification sequence

1. Reproduce or write the failing test.
2. Run the narrowest relevant test.
3. Implement the change.
4. Run the narrow test again.
5. Run affected suites.
6. Run formatter, linter, type checker, static analysis, build, and package checks as applicable.
7. Inspect warnings and output.

## Reporting

Report each command and observed result. Distinguish:
- Passed
- Failed
- Not run
- Blocked by environment

Coverage percentage alone is not proof of correctness.
