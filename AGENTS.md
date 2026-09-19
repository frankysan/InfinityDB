# Agent instructions

This file contains repository-wide instructions for coding agents working on
InfinityDB.

After reading this file, also read root-level `AGENTS.local.md` when it exists.
That optional companion is intentionally Git-ignored and is reserved for
user-specific workflow, communication, tooling, and machine-local preferences.
It must not define project architecture, data semantics, repository-wide
constraints, or durable decisions that other contributors need. Tracked
repository instructions and documentation take precedence if the local file
conflicts with them. Promote a local preference into tracked project
documentation only when the user explicitly wants it to become project policy.

Before making substantial changes, read:

- `docs/architecture.md` — architecture, engineering principles, and subsystem
  boundaries.
- `docs/data-model.md` — normalized data and persistence semantics.
- `docs/AI_CONTEXT.md` — durable project decisions, invariants, and development
  context.
- `docs/testing.md` — standard development-check orchestration and reporting.

The engineering principles in `docs/architecture.md` are authoritative for
technical design decisions.

## Python environment

Use the project virtual environment for Python tooling. Do not intentionally use
a system Python when the project virtual environment is available.

Virtual-environment interpreters are normally:

- Windows: `.venv\Scripts\python.exe`
- Linux/macOS: `.venv/bin/python`

Use `tools/run_checks.py` as the standard entry point for repository checks. It
invokes pytest, Ruff, Pyright type checking, Army data-build validation, and
curated rules-database validation through the same Python
interpreter that launched the runner and keeps stage selection/reporting
consistent across local development and agent handoffs. Examples:

```text
<venv-python> tools/run_checks.py --profile code
<venv-python> tools/run_checks.py --profile data
<venv-python> tools/run_checks.py --all
<venv-python> tools/run_checks.py --stage test tests/test_availability.py
<venv-python> tools/run_checks.py --profile code --report
<venv-python> tools/run_checks.py --stage test --assets off
<venv-python> tools/run_checks.py --stage test --assets required
```

With `--report` and no path, the runner writes an ignored repository-local
`reports/CHECKS YYYYMMDD-HHMMSS.txt` file using the same run-start timestamp as
the report header. An explicit report path overrides that convention. Requested
stages continue after failures by default; use `--fail-fast` when appropriate.
See `docs/testing.md` for the complete contract.

Direct pytest/Ruff/Pyright commands remain appropriate when debugging those
tools in isolation, and package installation still runs through the virtual-environment
Python, for example:

```text
<venv-python> -m pytest tests/test_specific.py -q
<venv-python> -m ruff check path/to/file.py
<venv-python> -m pyright
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
- Prefer validated configuration for project-specific aliases, mappings,
  filters, overrides, exceptions, and other maintained domain knowledge rather
  than burying that knowledge in implementation code. Generated manifests are
  for provenance/build state, not maintained policy.
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

### Changelog discipline

`docs/CHANGELOG.md` is the canonical release history and should be written so it can also serve as the source for a user-facing **Changes** page.

Record **meaningful release outcomes**, not a detailed implementation history. Prefer describing what was added, what behaves differently, what was fixed, or what an operator must do when upgrading.

When adding or consolidating changelog entries:

- Write from the perspective of a user or operator of InfinityDB.
- Describe the resulting capability, behavior, correctness improvement, or upgrade consequence rather than the implementation steps that produced it.
- Consolidate related engineering changes into a single outcome-oriented entry where they form one coherent improvement.
- Keep `Added`, `Changed`, and `Fixed` as the normal categories. Use an `Upgrade notes` section when a release requires an explicit action such as rebuilding generated databases.
- Keep wording understandable without requiring knowledge of InfinityDB's internal architecture, build pipeline, CI setup, or implementation tools.
- Retain technical terminology only when it identifies a meaningful user-visible concept or is necessary for an operator to act on the change.
- Prefer concise entries. A release should communicate its important changes without becoming an inventory of commits.

Normally omit standalone changelog entries for:

- version-number or release-metadata updates;
- schema or compatibility revision numbers when the only important consequence is that generated data must be rebuilt;
- linting, formatting, type-checking, or test-coverage work;
- internal refactors with no externally meaningful behavioral change;
- query plans, indexes, batching strategies, or other implementation-level performance work when these can instead be summarized as a performance improvement;
- cache-busting, asset fingerprints, or similar implementation details unless they directly fix a user-visible problem;
- CI workflow details, validation mechanics, acceptance-test milestones, or individual regression tests;
- exact tool or script names unless users or operators interact with them directly;
- project-management milestones whose durable outcome is already described elsewhere in the release notes.

Detailed implementation history should remain available through Git history, architecture and data-model documentation, deployment documentation, manifests, generated reports, and tests rather than being duplicated in the changelog.

Before finalizing a release, review the complete `Unreleased` section as a whole rather than only promoting individual accumulated entries. Merge overlapping entries, remove implementation-only details, and ensure the resulting release notes tell a concise and coherent story of the release.

- Update `docs/architecture.md` when changing architectural boundaries,
  engineering principles, or lasting design decisions.
- Update `docs/data-model.md` when changing documented data semantics or
  persistence structure.
- Update `docs/AI_CONTEXT.md` when introducing a durable, non-obvious project
  invariant or development constraint.
- Add identified future work to `docs/TODO.md`.
- Record meaningful changes under `Unreleased` in `docs/CHANGELOG.md`.
- Update `README.md` for user-visible behavior, setup, or major capabilities.
- When changing the Army database schema or compatibility revision, update all
  documented current schema/compatibility values and related rebuild guidance in
  the same change.

Do not duplicate canonical documentation unnecessarily; link to the
authoritative document instead.

### Documentation status discipline

Keep implementation status explicit throughout the documentation corpus:

- **Current design/behavior** describes what the repository and application do
  now. Unqualified statements in reference documentation should normally mean
  current behavior.
- **Design direction** describes an accepted architectural decision or intended
  boundary that is not fully implemented yet. Label it explicitly; do not write
  it as though the corresponding files, schema fields, tooling, or runtime
  behavior already exist.
- **Planned/unimplemented work** belongs in `docs/TODO.md`. Architecture and
  data-model documents may explain the intended shape and rationale, but should
  point to the backlog instead of maintaining a second task list.

When one topic has both a current implementation and a future design, separate
them with explicit headings or wording. Do not silently rewrite legacy source or
curated data to match a future contract; document the current limitation and
track the migration until the responsible implementation is changed.

## Local rules reference

User-supplied PDFs and wiki snapshots under `data/` may be used as research
sources for rules-aware features and data review. They are not inputs to the
Infinity Army merge/normalization/build pipeline.

When deriving structured facts from these materials:

- record source version/date and printed-page citations for PDFs;
- preserve the wiki source identity actually available to the current curated
  contract, including snapshot-local path and snapshot date;
- do not invent an exact timestamped archive identity/hash for legacy wiki
  references before the downloader/packager and curated provenance contract are
  migrated;
- keep core rules, FAQ/errata, ITS season material, and historical sources
  distinct;
- do not bulk-extract or serve copyrighted text or artwork.

Official Infinity Army data and current official publications remain
authoritative where they supersede archived local material.
