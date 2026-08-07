---
name: free-dev-catalog-diff
description: Parse and compare two free-for.dev README snapshots to identify added, removed, moved, renamed, or materially changed service entries. Use for catalog monitoring, change reports, stale-claim detection, historical comparisons, or structured JSON/Markdown diffs. Do not use this skill to generate or submit AI-authored pull requests to the upstream repository, because the upstream contribution policy rejects AI-edited contributions.
---

# Free Dev Catalog Diff

## Boundary

Analyze catalog changes for the user. Do not draft, edit, or submit a pull request to the upstream free-for-dev repository. Its published contribution instructions reject AI-edited contributions.

## Workflow

1. Obtain two complete UTF-8 Markdown snapshots: old and new.
2. Preserve the files unchanged as evidence.
3. Run:

```bash
python scripts/catalog_diff.py old-README.md new-README.md --json -o diff.json
python scripts/catalog_diff.py old-README.md new-README.md -o diff.md
```

4. Review automated matches. URL-based identity is preferred; entries without HTTP URLs fall back to normalized category and name.
5. Classify each change:
   - addition;
   - removal;
   - category move;
   - rename or URL change;
   - quota or wording change;
   - warning or availability-status change.
6. For decision-critical changes, verify the provider's current official pricing or documentation with the tier-verifier skill.

## Interpretation rules

- A wording change is not automatically a pricing change.
- A removed entry does not prove the service was discontinued.
- An added entry does not prove the free tier is current or suitable.
- URL redirects or rebrands can produce false add/remove pairs; manually reconcile obvious cases.
- Report snapshot dates, source URLs, and hashes when available.

## Output format

### Summary
Counts for old, new, added, removed, and changed entries.

### Material changes
Prioritize changes affecting quota, duration, card requirements, commercial eligibility, security, region, inactivity, or billing exposure.

### Verification queue
List provider claims that require primary-source checking.

### Repository-policy notice
State that the report is for analysis only and must not be converted into an AI-authored upstream contribution.

## Resources

- `scripts/catalog_tool.py`: shared Markdown parser.
- `scripts/catalog_diff.py`: deterministic snapshot comparison.
- `references/change-taxonomy.md`: change classification and false-positive handling.
## Specialist handoff

Use `free-dev-live-sync` to acquire reproducible snapshots. Material catalog changes must still be checked with `free-dev-tier-verifier` before being treated as provider truth.

