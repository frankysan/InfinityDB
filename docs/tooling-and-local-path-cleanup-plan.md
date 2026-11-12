# Tools and local-path cleanup plan

**Project domains:** Project infrastructure, Data processing, Acquisition, Deployment

**Status:** Proposed for the next cleanup project. **Planning only:** no paths, files,
commands, or tool interfaces have been migrated or retired by this document.

**Planning baseline:** `dev/v1.1.0` at
`a55b09ff5a7a37d6d7207f055a79ef2161a7e410`, inspected 2026-11-12.
Select a fresh implementation branch and exact baseline at kickoff; the v1.1.0
merge/release/deployment process remains a separate decision.

## Outcome and governing principles

Make repository ownership and file lifetimes obvious without opening a file.
Reduce top-level clutter, retire completed one-use tools, and ensure that
untracked source/research/build artifacts live under `local/` by default.
A stricter layout should simplify maintenance, not create another compatibility
framework or make normal checkout/Docker builds depend on private assets.

- **Tracked published inputs and artifacts stay tracked.** The three selected
  runtime databases (`data/generated/army.db`, `rules_n5.db`, `its_18.db`),
  curated data, reviewed configuration, static assets and the published symbol
  manifest retain their current tracked responsibilities.
- **Ignored project data belongs in `local/`.** New ignored downloads,
  snapshots, audits, intermediates, derived data, diagnostics and reports
  must not be written elsewhere without a documented, narrow exception.
  Existing ignored `data/` subtrees should normally move to `local/data/`.
- **One clear owner per path.** `src/` contains application and build
  implementation; `tools/` contains maintained developer/operator tooling;
  `local/` contains nontracked state; external acquisition/symbol/model
  producers own their own local inputs and processing.
- **Retire rather than merely relocate completed code.** Git history preserves
  superseded implementations. Keep original externally acquired evidence when
  provenance, licensing or unfinished research requires it.
- **Move consumers with producers.** Changes to CLI defaults, Python module
  imports, tests, CI, scripts, Syncthing, documentation and developer habits
  are part of each migration, not deferred cleanup.
- **Do not turn accidental local state into an input.** Normal serving,
  installed-wheel and Docker builds must remain deterministic from their
  documented, supported inputs. Optional research can use explicitly selected
  local data, with hash/snapshot checks.
- **Never bulk-delete private material.** Verify bytes, ownership, backup,
  external producer sync and restore before removing old files.
- **Public compatibility is separate.** Keep published URLs and player-facing
  behavior. Internal Python module paths/commands may change through an
  explicit cutover once live consumers are accounted for.

The canonical current-state owners are
[architecture](architecture.md), [data lifecycle](../data/README.md),
[testing](testing.md), [CI](ci.md), [Syncthing](syncthing-assets.md) and
[one-use tool policy](README.md#one-use-tool-and-audit-lifecycle).
This document is a *proposed work plan*, not a competing operational manual.
The [backlog](TODO.md) owns the open implementation item; only approved,
implemented rules move into those canonical owners.

## Observed starting condition

The initial root-level inspection found:

- `tools/`: **123 Python modules** plus `templates/` (124 entries).
  Tools mix current validators, builders, operations, optional measurements,
  bounded research and completed migrations. Several import one another from
  flat paths or are invoked via `python -m tools.NAME`.
- `local/`: **447 immediate entries**, mixing loose scripts and reports,
  release evidence, recovery directories, screenshots, source material and
  benchmarks. This count is *not* a total file count.
- Root `reports/`: **367 immediate entries**, mostly ignored check/release
  output, outside the intended `local/` owner.
- `data/raw/`, `data/wiki/`, `data/pdf/`, `data/work/`,
  `data/reports/`, `data/logs/`, `data/backups/`, `data/runtime/`
  and `data/manifests/snapshots/` are ignored or contain ignored contents.
  `data/generated/` mixes three tracked databases with ignored files
  such as `army.raw.db` and old diagnostic JSON/screenshots.
- `image_overrides/`, ignored static-font TTF inputs and `docs/audits/`
  are additional nonlocal ignored-data locations.
- Current build defaults, source audits and
  [Syncthing activation](syncthing-assets.md) still name legacy
  `data/raw/`, `data/pdf/`, `data/wiki/` and `image_overrides/`.
  These are real migration dependencies, not just stale documentation.
- `.gitignore` and `.dockerignore` explicitly encode current exceptions.
  Their change must preserve the tracked database/manifest allowlist and
  exclude private material from installed wheels and images.

This is an inventory **sample**, not evidence that all affected files,
symlinks, ACLs, sizes, readers or producers have been located.

## Proposed path contract (approve in phase L1)

### `local/`: private and generated state

Require a directory path to identify **domain, purpose, scope and lifetime**.
Prefer stable lowercase hyphenated directory components; preserve the exact
upstream filename when its identity is part of verified provenance. A final
filename should describe the artifact's role/type, not repeat every directory
component. Prefer UTC timestamp plus abbreviated source/commit SHA when a run
needs a unique identifier; never use `latest` as the only provenance key.

Suggested top-level categories:

- `local/data/` — ignored source and derived *data-family* artifacts, with
  initial migration retaining intuitive subtrees:
  `raw/`, `wiki/`, `pdf/`, `manifests/snapshots/`, `work/`,
  `generated/`, `reports/`, `logs/`, `backups/`, and `runtime/`.
  Subdivide by source family (`army`, `rules-n5`, `its-18`,
  `human-sphere`, `symbols`) where necessary. `local/data/generated/`
  does **not** contain the tracked runtime databases.
- `local/research/<domain>/<topic>/<source-revision>/` — manually retained
  source comparisons, evidence and experiments.
- `local/validation/<domain>/<scope>/<run-id>/` — test, CI, browser and
  release-candidate receipts, including existing loose `reports/` output.
- `local/performance/<system>/<scenario>/<run-id>/` — benchmark inputs,
  captures and analysis.
- `local/operations/<service>/<task>/<run-id>/` — deployment diagnostics,
  monitoring snapshots and *approved* recovery evidence.
- `local/work/<domain>/<task-or-run-id>/` — disposable scripts, scratch
  files, intermediates and short-lived workspaces.
- `local/handoffs/<producer>/<artifact-family>/<snapshot-or-run-id>/` —
  verified cross-repository handoff candidates awaiting consumption.

The first pass should minimize nesting, not enforce all these folders when
empty. Avoid placing a second `local/` inside a category, generic `misc/`
or `temp-final/` buckets, and new loose files directly under `local/`.
Use paths like:

- `local/data/raw/army/JSON 20260929-114335.zip` — immutable original
  archive name retained for its externally pinned identity.
- `local/research/rules-n5/weapon-chart/v5.3/chart-diff.json` — retained
  version-scoped research.
- `local/validation/symbols/publication/20261112T101800Z-a55b09ff/
  asset-verification.json` — dated, revision-pinned acceptance evidence.
- `local/work/rules-n5/restrictions-migration-20261112/
  inspect-candidate.py` — task-scoped, disposable code.

For new tool outputs, require an explicit or predictable destination and
document whether it is (a) **scratch**: auto-prunable after success;
(b) **run evidence**: retained while a check or diagnosis is open;
(c) **pinned source**: immutable until consumer/provenance retirement;
(d) **accepted release evidence**: retained under the release/operations
policy; or (e) **operator recovery**: delete only after explicit verified
closure. A descriptive path does not by itself authorize cleanup.

### Ignored-path exceptions

Keep an explicit, reviewed exception registry rather than interpreting
`.gitignore` as approval for an arbitrary private path. Typical justifiable
exceptions are tool-controlled virtual environments, package/install
directories, Python/pytest/linter caches, standard `build/` and `dist/`
outputs, local editor preferences, host-specific environment/secrets and OS
metadata that must remain in their conventional locations. Document owner,
reason, retention and whether a configurable alternative exists.

**Not** blanket exceptions: ignored `data/` work/source directories,
ignored files alongside tracked SQLite databases, root `reports/`,
`docs/audits/`, `image_overrides/`, or downloaded font source files.
Review each for relocation, external-producer ownership or justified
special handling. Never put secrets in tracked inventories or diagnostic logs.
Do not move a third-party cache into `local/` merely to satisfy a checker
when it would break its supported toolchain convention.

### `tools/`: maintained executables and shared helpers

Categorize by **responsibility and current consumer**, not just verb prefix:

- `tools/data/` — offline Army/Rules/ITS build and selected-database checks.
- `tools/research/` (optionally `army/`, `rules/`, `weapons/`,
  `its/`) — repeatable source investigations with an active question.
- `tools/symbols/` — application-side source plans, handoff verification,
  artwork-review templates, publication preparation and promotion; external
  `InfinityDB-symbol-tools` continues to own graphical processing.
- `tools/browser/` — browser and hosted release-candidate acceptance.
- `tools/testing/` — reusable test harness, pytest instrumentation and
  test-section policy.
- `tools/ci/` — deterministic build checks, packaging, release evidence
  and CI-specific validation.
- `tools/operations/` — deployment observability, diagnostics and
  operator commands.
- `tools/performance/` — opt-in benchmarks and resource investigations.
- `tools/dev/` — worktrees, coordination, development status and explicit
  asset activation.
- `tools/_shared/` — narrow helpers genuinely reused across categories.

Retain only a **documented minimal root command surface**, e.g. the stable
`tools/run_checks.py` if it is still the canonical developer entry point,
and `tools/__init__.py`. Do not create empty packages or permanent wrappers
for obsolete one-off commands. Relocations must update exact Python imports,
`-m` invocations, test sections, entry points, subprocesses, CI workflows,
docs, fixtures, packaging, source pins and optional MCP tool allowlists.
Historical-only tests can retire with completed tools; preserve independent
semantic checks. New tools should declare domain, role, expected output
path/lifetime and retirement condition in their module docstring or help.

## Execution phases

### L0 — Full read-only inventory and ownership mapping

1. Capture branch/SHA and status. Enumerate **all** tracked tools (including
   templates) and ignored/locally generated paths across Windows and Linux.
   Capture path, byte size, kind, tracked/ignored status, Git rule, timestamps
   where trustworthy, and SHA-256 for candidate migrations; do not include
   private content or credentials in published reports.
2. For each tool, record purpose, inputs/outputs, owner, calls/imports from
   source/tests/tools/CI/scripts/docs/agent skills, optional local-only
   consumers, publication side effects, and lifetime. Classify:
   `retain`, `move`, `extract-and-replace`, `archive-evidence`,
   `retire`, or `needs-decision`. A historical test alone is not a reason
   to retain its obsolete implementation.
3. For ignored files, distinguish immutable upstream originals,
   re-creatable diagnostics, accepted evidence, active Syncthing inputs,
   recoverable backups and unrecognized material. Never infer that an
   old filename means its bytes are disposable.
4. Produce a proposed move/delete manifest (old path, new path,
   owner, consumer list, size/hash, evidence retained, rollback and review
   status), plus a small risk-ranked decision list. Keep sensitive
   per-file metadata in ignored `local/`; track only reviewed conclusions.

**Exit:** Every currently relevant path and tool has an owner and disposition
proposal. Unresolved ownership or unique evidence is explicitly marked.

### L1 — Approve and publish the new path policy

1. Confirm the categories above, any scoped exceptions, naming examples,
   lifecycle/retention rules and who may prune each class.
2. Select the canonical tracked owner for the adopted policy
   (`docs/architecture.md` and `data/README.md`, with short references in
   `AGENTS.md` and `docs/README.md`). Keep the detailed migration
   inventory in this project, not a second permanent manual.
3. Decide an implementation branch from the release state. Freeze input
   identities and the initial migration manifest before any destructive step.

**Exit:** Reviewed mapping and bounded exceptions approved. No project-wide
silent rename or removal follows from this plan alone.

### L2 — Migrate writers, readers and cross-repository handoffs

1. Find path defaults and fixed filenames in `src/`, `tools/`,
   `tests/`, `config/`, `scripts/`, CI, Docker, docs, installer,
   agent/MCP operations, and producer repositories. Include direct path
   literals, dynamic discovery, `INFINITY_DB_DB_DIR`, build staging,
   asset references, browser/source fixtures and output conventions.
2. Implement destination selection for ignored artifacts under `local/`
   before moving their bytes. Keep the selected tracked three-database
   `data/generated/` contract unchanged. Use explicit source paths where
   reproducibility is necessary; update safe default discovery for local
   input snapshots.
3. Coordinate Army/Wiki/Symbol producer outputs, Windows Syncthing folder
   paths and Linux staging/activation/ACLs. Synchronization remains explicit;
   neither MCP nor the build implicitly copies or downloads data.
4. Use short, explicitly bounded transitional readers only when required
   for a controlled cutover. Reject ambiguous duplicate input sources;
   never silently choose between old and new snapshots. Remove transitional
   readers at the agreed cutoff.

**Exit:** Representative build, source-audit, private asset activation and
research operations can run from their new paths while published outputs
remain unchanged.

### L3 — Relocate ignored data safely

1. Migrate by independent source family: raw snapshots + provenance,
   Wiki/Human Sphere, PDFs, legacy symbol/override evidence, generated
   raw/diagnostic files, logs/backups/work, root reports and research.
2. For each batch: inventory/hashes, copy to destination, verify hashes
   and manifests, test relevant consumer commands on Windows and Linux,
   verify backup/recovery and Syncthing state, then authorize removal of
   old ignored paths separately. Avoid an unreviewed destructive sweep.
3. Update `.gitignore` and `.dockerignore` without accidentally excluding
   any tracked release bytes or including private assets in a wheel/image.
   Only remove stale ignore clauses after old paths are no longer used.
4. Ensure test fixtures use isolated temporary directories and explicit
   ignored input requirements; clean CI must not require the developer's
   local snapshots.

**Exit:** Non-exempt ignored project-owned files are under `local/` or
an explicitly owned external staging area. Hash/manifest evidence and
cross-host acceptance are recorded; legacy project paths are no longer
required.

### L4 — Reorganize maintained `tools/` by responsibility

1. Finalize the per-file L0 disposition. Move only genuinely maintained
   modules into the selected categories in small, dependency-coherent
   slices, preserving useful test semantics. Include
   `tools/templates/symbol_artwork_review.html` with its current owner
   if the review builder moves.
2. Replace imports and command invocations atomically; update CLI help,
   docs, tests, CI, module packaging and MCP allowlists. Do not leave
   duplicate implementations in the old flat layout.
3. Repair `verify_release_candidate_browser` to validate the **complete
   Army/Rules/ITS three-database identity** before treating it as a
   v1.1+ release gate. This is a correctness task, not a rename.
4. Address dated defaults such as the November 11 symbol-artwork review
   inputs by requiring explicit, pinned current/candidate selections for
   future runs.

**Exit:** The root tool directory contains only reviewed public command
exceptions and package structure; all moved tool modules have live consumers
and passing focused tests.

### L5 — Retire completed investigations and consolidate reusable checks

1. First review the P5 historical comparison pair
   `compare_symbol_canonical_paths` /
   `verify_production_symbol_processing`, its tests and old commands.
   Preserve the accepted symbol-cutover evidence.
2. Then review bounded deployed-object, Weapon-chart, historical 1.0,
   symbol provenance and other one-use research clusters. Preserve open
   source questions, stable finding IDs and immutable source hashes in
   canonical research records. Extract current reusable parsers/validators
   before retiring a wrapper.
3. Consolidate overlapping audit, browser and benchmark infrastructure
   only if duplication is demonstrated. Do not retire current release
   gates, reproducible source investigations or useful optional
   diagnostics solely because they are not called in ordinary CI.

**Exit:** Every deletion has an explicit fulfilled purpose, an audited
consumer graph and preserved current behavior/evidence. The removed code
remains recoverable through Git history.

### L6 — Add proportional enforcement and output hygiene

1. Add a deterministic, read-only path-policy check for *tracked changes*:
   unexpected root `tools/*.py` additions, documented module categories,
   prohibited new tracked/private output roots, and any deliberately
   maintained exception list. Wire it into the normal docs/lint gate only
   after testing false positives across platforms.
2. Add a separate **opt-in local audit** for Git-ignored paths, with
   safe metadata-only reporting and suggestions. Hosted CI cannot inspect
   an individual developer's `local/` or discover all ignored files.
   Do not delete or rewrite private data as part of a lint check.
3. Update output-producing CLI defaults/help so new reports receive a
   domain/purpose/scope/run-ID destination without overwriting prior
   evidence. Reject unsafe paths and stale/mismatched pinned inputs.
4. Document concise creation/retirement guidance for agents, producers
   and operators. Prefer a single maintained path resolver/helper only
   where multiple actual consumers need it.

**Exit:** New stray artifacts and tool entrypoints are detected early,
while standard Python/Node/OS caches and local secrets continue working.

### L7 — Integrated validation, measurement and closeout

1. Run affected focused tests at each phase. At the integrated boundary
   validate source snapshot selection, Army/Rules/ITS deterministic
   generation, source freshness, SVG publication, checkout server,
   installed wheel and disposable Docker preview. Use the complete
   three-database semantic baseline with `--db-dir data/generated`;
   confirm ITS 18 Battleground and the preserved Seed Soldier URL.
2. Run the appropriate cross-platform/source CI gate **once** at a
   coherent validated revision; do not repeat a full suite for each
   documentation or path-only patch. Optional research inputs and
   skips must be reported honestly.
3. Measure baseline/final root file counts, retained/moved/retired
   tool counts, non-exempt ignored paths outside `local/`, loose files
   under `local/`, duplicate wrappers and actual required developer
   steps. Record timing comparisons only with the same pinned inputs and
   conditions; otherwise record observed times without a speedup claim.
4. Move approved permanent contracts into canonical documents, close
   the backlog item, remove obsolete transition shims and leave this
   plan as historical evidence or retire it if redundant. Release,
   merge and deployment remain separately authorized.

**Exit:** Normal development and deployment remain correct on a clean
checkout; private file ownership/lifetimes are discoverable; no live
consumer depends on retired paths; measured simplification and remaining
exceptions are documented.

## Priority and decision checkpoints

- **First safety issue:** the release-browser verifier's legacy two-file
  identity must be corrected before relying on it for a three-database
  release, independently of broad tool relayout.
- **First low-risk tool removal candidate:** historical P5 path/process
  comparison pair, after clearing its dedicated tests/docs.
- **First high-impact data migration:** `data/raw/` and
  `data/manifests/snapshots/` together, but *only after* source builders,
  explicit archive selectors and cross-host Syncthing activation have
  been updated and hash-verified.
- **Highest preservation risk:** ignored PDFs/wiki source archives,
  historical overrides, accepted review evidence and backup/recovery
  artifacts. Do not infer disposability from age or location.
- **No automatic mass move:** L0 inventories and L1 approval precede
  destructive actions; each L2–L5 slice has an independent recovery
  and acceptance record.

This project is not a prerequisite to publishing the already reviewed
v1.1.0 restructuring implementation. It is separate future cleanup work
unless a concrete correctness or release-blocking issue is identified.
