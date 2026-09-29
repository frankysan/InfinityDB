# Documentation map

**Project domain:** Project infrastructure

InfinityDB documentation is organized by **authority**, not by development chronology. Current
behavior should have one maintained owner; secondary documents link to that owner instead of
repeating the same contract. Git history and `docs/CHANGELOG.md` preserve release history.

## Canonical current-state documents

Use these documents when deciding how the project works now:

- `architecture.md` — system boundaries, engineering principles, ownership between subsystems,
  runtime/browser/deployment architecture, and accepted design direction.
- `data-model.md` — current source/application identities, semantic provenance, persistence,
  query semantics, and generated-database contracts.
- `application-domains.md` — canonical player-facing domain ownership and publication capabilities.
- `web-design-guidelines.md` — browser layout, reusable surfaces, tables, controls, responsive
  behavior, typography, accessibility, and theming rules.
- `project-domains.md` — engineering ownership labels used by planning and release notes.
- `data/README.md` — external inputs, generated artifacts, snapshot provenance, and publication
  lifecycle.
- `data/curated/README.md` — authored/curated data schemas and review contracts.
- `testing.md` — local validation entry points, test slices, asset modes, reports, and benchmark
  tooling.
- `ci.md` — hosted CI workflows and repository-level validation policy.
- `deployment.md` — production install/update/rollback/operations contract.
- `server-migration.md` — moving released or development environments between hosts.
- `releasing.md` — mandatory release gate and the 1.0 completeness definition.

When two documents appear to overlap, prefer the owner above. Correct the owner first, then reduce
secondary text to a link or short boundary statement.

## Maintained evidence and research

These files intentionally retain reviewed evidence that is useful beyond one release:

- `rules-semantics.md` — audited rules meaning that already has a concrete InfinityDB consumer.
- `rules-research.md` — verified source findings retained for possible future product/model work.
- `rules-interaction-checklist.md` — generated cross-release interaction-review ledger. Regenerate
  it with `tools/audit_rules_interactions.py`; do not edit it manually. Its release labels record the
  original review/defer decision and are evidence provenance, not the active roadmap; use `TODO.md`
  for current milestone planning.

Completed audit/closeout documents are **not** permanent reference documentation by default. Once
an audit closes, move lasting contracts into the canonical owner above, record user/operator-visible
outcomes in `CHANGELOG.md`, and let Git history preserve the detailed narrative. Keep a tracked audit
only when it contains unique rationale that still guides active work.

## Planning and history

- `TODO.md` — only work that is still unimplemented or intentionally deferred.
- `CHANGELOG.md` — concise release outcomes and upgrade consequences.
- `AI_CONTEXT.md` — compact agent-oriented index of non-obvious current invariants and pointers to
  canonical documentation. It is not a second architecture or data-model specification.

## Local audit workspace

`docs/audits/` is intentionally ignored by Git. Use it for generated matrices, command output,
comparison results, screenshots, exploratory notes, and machine/deployment-specific evidence.
Nothing in normal builds, tests, CI, or runtime behavior may depend on this directory.

A normal audit therefore has three steps:

1. collect transient evidence under `docs/audits/`;
2. correct code/data/documentation and validate the result; and
3. promote only durable conclusions into the canonical documents above.

This keeps the repository documentation useful as a current technical reference instead of an
archive of every completed review.
