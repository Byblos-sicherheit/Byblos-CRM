# free-for.dev capability analysis

## What the site is

free-for.dev is a curated catalog of free tiers useful to infrastructure and software developers. The public site is a Docsify presentation over repository content, with navigation, client-side search, and theme behavior. The core catalog is maintained in the repository README.

## Upstream scope

The published scope favors as-a-Service offerings and requires a real free tier rather than a short free trial. The project also considers basic security posture in admission criteria.

## Why the bundle is larger than the website UI

The upstream site is optimized for discovery. Production decisions require additional workflows that the catalog cannot guarantee: current provider verification, hard-constraint filtering, quota math, paid-transition modeling, EU/privacy evidence review, operational risk analysis, migration alternatives, reproducible snapshots, and structured export.

## Design decision

The bundle separates these concerns into 18 skills instead of copying every catalog category into a separate skill. Category-specific routing is data-driven, while evidence standards and deterministic calculations remain centralized in specialist skills. This avoids duplicate logic and stale category-specific packages.

## Upstream contribution policy

The current CONTRIBUTING.md states that AI-generated edits are not accepted. The bundle therefore prohibits generation or submission of upstream pull requests.

## V4 execution model

V4 adds an MCP server and plugin manifest without changing the evidence policy. Standard search/fetch expose catalog documents, deterministic tools handle bounded calculations and comparisons, and the model remains responsible for current provider verification where required.

## Historical local snapshot note

The original v1 analysis recorded an August 4, 2026 snapshot with 57 main categories and 1,203 primary service entries. Treat those counts as historical snapshot facts, not as a claim about the live catalog on later dates.
