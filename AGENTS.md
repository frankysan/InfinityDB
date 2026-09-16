# Agent instructions

This file contains repository-wide instructions for coding agents working on
InfinityDB.

Before making substantial changes, read:

- `docs/architecture.md` — architecture, engineering principles, and subsystem
  boundaries.
- `docs/data-model.md` — normalized data and persistence semantics.
- `docs/AI_CONTEXT.md` — durable project decisions, invariants, and development
  context.

The engineering principles in `docs/architecture.md` are authoritative for
technical design decisions.

## Python environment

Use the project virtual environment for Python tooling. Do not intentionally use
a system Python when the project virtual environment is available.

Virtual-environment interpreters are normally:

- Windows: `.venv\Scripts\python.exe`
- Linux/macOS: `.venv/bin/python`

Run tools through that interpreter, for example:

```text
<venv-python> -m pytest
<venv-python> -m ruff check src tests
<venv-python> -m pip install ...
```

Local developer wrappers or command-launching tools may be used, but repository
instructions must not depend on a particular user's machine configuration.

## Repository rules

- Support Windows, Linux, and macOS. Do not introduce machine-specific absolute
  paths or assume a particular shell.
- Preserve raw upstream inputs; transformations belong in separate working or
  generated outputs.
- Do not silently discard ambiguous, unresolved, or source-specific information.
- Keep source-format, database, HTTP, browser, and deployment concerns in their
  established layers.
- Normal builds and tests must not unexpectedly require network access.
- Do not redistribute third-party data or assets unless their licensing permits
  it; see `THIRD_PARTY_NOTICES.md`.
- Prefer validated manifests/configuration for project-specific aliases,
  mappings, filters, overrides, exceptions, and other maintained domain
  knowledge rather than burying that knowledge in implementation code.
- Do not add a JavaScript build step unless a clear requirement justifies it.

## Repository write safety

When modifying the repository through a remote Git/GitHub API rather than a
normal local working tree:

- Read the target branch tip immediately before starting any write sequence and
  use that exact commit as the expected base.
- Prepare and review the complete intended change set before creating Git blobs,
  trees, or commits. Do not use repository object creation as scratch staging.
- Prefer a direct file-update operation for a single-file change. For a
  multi-file atomic change, create blobs/tree/commit only after every replacement
  is ready, then move the branch ref once with a non-forced fast-forward update.
- Never report a change as committed merely because blobs, trees, or a commit
  object were created. A change is on the branch only after the branch ref has
  been updated successfully.
- Immediately after a write sequence, re-read the branch tip and inspect the
  resulting commit/diff or changed-file set. Confirm that only the intended
  files changed before reporting success.
- If a tool call fails, stalls, or the user interrupts a write sequence, stop
  making writes and re-read the branch tip before continuing. Explicitly state
  whether the branch changed; unattached Git objects do not count as repository
  changes.
- Do not force-update a branch unless the user explicitly requests history
  rewriting or a previously agreed recovery requires it.

## Documentation and project tracking

- Update `docs/architecture.md` when changing architectural boundaries,
  engineering principles, or lasting design decisions.
- Update `docs/data-model.md` when changing documented data semantics or
  persistence structure.
- Update `docs/AI_CONTEXT.md` when introducing a durable, non-obvious project
  invariant or development constraint.
- Add identified future work to `docs/TODO.md`.
- Record meaningful changes under `Unreleased` in `docs/CHANGELOG.md`.
- Update `README.md` for user-visible behavior, setup, or major capabilities.

Do not duplicate canonical documentation unnecessarily; link to the
authoritative document instead.

## Local rules reference

User-supplied PDFs and wiki snapshots under `data/` may be used as research
sources for rules-aware features and data review. They are not inputs to the
Infinity Army merge/normalization/build pipeline.

When deriving structured facts from these materials:

- record source version/date and printed-page citations for PDFs;
- preserve snapshot-local identity and date for wiki sources;
- keep core rules, FAQ/errata, ITS season material, and historical sources
  distinct;
- do not bulk-extract or serve copyrighted text or artwork.

Official Infinity Army data and current official publications remain
authoritative where they supersede archived local material.
