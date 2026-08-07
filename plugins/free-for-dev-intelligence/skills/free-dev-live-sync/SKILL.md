---
name: free-dev-live-sync
description: Acquire, normalize, fingerprint, and record current or user-supplied free-for.dev catalog snapshots for downstream search and change analysis. Use when a request requires the latest catalog, a reproducible snapshot, source metadata, checksum verification, or preparation of two catalog versions for diffing. Prefer official free-for.dev and GitHub sources and support offline fallback to supplied Markdown.
---

# Free Dev Live Sync

## Workflow

1. Prefer the official GitHub repository file `README.md`; the public website is an alternate view of the same catalog.
2. Fetch through an available browser or GitHub connector. Do not assume direct shell networking exists.
3. Save the retrieved Markdown as a snapshot only when the environment permits file writes.
4. Run `scripts/snapshot_manager.py create` to calculate metadata and SHA-256.
5. Run `scripts/snapshot_manager.py verify` before reusing a recorded snapshot.
6. Pass the Markdown snapshot to catalog search, diff, or export skills.

## Freshness policy

- Treat catalog content as dynamic.
- Record acquisition time, source URL, byte count, line count, and SHA-256.
- Do not claim a snapshot is current unless it was fetched during the current task or its acquisition time is explicitly known.
- Do not bundle a full permanent copy of the upstream catalog into the skill.

## Network fallback

If direct network access is unavailable, use a connected GitHub/browser tool or ask the caller to provide a Markdown snapshot only when no available connected source can retrieve it.

## Upstream restriction

Do not create AI-generated contribution patches or pull requests for free-for.dev. This skill is read/snapshot oriented.

## Resources

- `scripts/snapshot_manager.py`: create, verify, and compare snapshot metadata.
- `references/source-locations.md`: official locations and acquisition rules.
