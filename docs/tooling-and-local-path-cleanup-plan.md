# Tools and local-path cleanup plan

**Project domains:** Project infrastructure, Data processing, Acquisition, Deployment

**Status:** Started 2026-11-12; L0 inventory and ownership review in progress.
The path contract and remaining dispositions below remain proposals. Bounded
P5 retirements are recorded below; no private inputs have been moved or deleted.

**Planning baseline:** `dev/v1.1.0` at
`a55b09ff5a7a37d6d7207f055a79ef2161a7e410`, inspected 2026-11-12.
**Implementation baseline:** `dev/tooling-workspace-cleanup`, created with user
authorization from clean `dev/v1.1.0` at
`a08651d894a045940e8e3c6217b23532da550c9a` on 2026-11-12.
The v1.1.0 merge/release/deployment process remains a separate decision.

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
This document owns the cleanup execution record and *proposed migrations*,
not a competing operational manual.
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

## Lifecycle/disposition audit (existing policy, L0–L1 implementation)

The canonical [completed-file policy](README.md#disposition-and-naming-of-completed-files)
governs removal, evidence archival, renaming and reusable-logic extraction.
The cleanup project must make those decisions **per artifact**, not use an
automated age cutoff or relocate every old file to an archive.

Inventory both tracked and ignored **plans, reports and audits**, not just
Python tools and source archives. For each item, capture its owner/domain,
purpose, source revision or task scope, current versus historical status,
producing command, consumers, open findings, retention reason, evidence
integrity/backup, and proposed retirement trigger. The review must answer:

- **Plans:** Is implementation still open in `TODO.md`? Have durable
  architectural decisions moved to canonical docs? Does the completed plan
  contain unique rationale worth a visibly labeled historical record?
- **Audits:** Are any unresolved findings still assigned to a maintained
  register? Is source identity independently reproducible? Is a newer audit
  a replacement of the evidence or only an additional observation?
- **Reports:** Are results required for a current release, legal/provenance
  obligation, ongoing diagnosis or reproducible comparison? Can raw
  intermediates be discarded while preserving the accepted summary?
- **Tools:** Is the command still used for repeatable research, a current
  validation/build contract or a supported operator action? Can useful
  helpers be extracted before an obsolete wrapper is retired?
- **Ignored/private files:** Is the material immutable source, active
  scratch, accepted evidence, recovery data or an unrecognized file?
  Treat unknown ownership as `needs-decision`, never `safe-to-delete`.

The approved disposition manifest should distinguish `retain-active`,
`retain-frozen-evidence`, `rename-or-move`, `extract-and-retire`,
`retire-to-git-history`, `delete-reproducible-local-output` and
`needs-decision`. Record a concise reason, exact old/new path, impacted
consumers, validation method and (where needed) retention/review trigger.
A renamed historical file must not continue posing as a maintained command
or active plan. Only unique shared evidence belongs in a tracked historical
location; private evidence stays in categorized `local/`.

Do **not** create a general tracked `archive/` tree, a permanent duplicate
catalog of retired files or placeholder wrappers for old commands. Git
history is the default archive for superseded tracked code and narrative.
Prevent ambiguous references to archived materials by updating links,
indexes, scripts and instructions with each approved retirement batch.
Old private source/backup deletion remains separately authorized.

## Execution phases

### Kickoff checkpoint — 2026-11-12

**Completed intake:** Enumerated all **124 tracked tool files** (123 Python
modules plus the artwork-review template) and all **48 tracked Markdown
documents** at the implementation baseline. Captured sizes and SHA-256 values,
module purposes, AST imports and literal paths, tracked reference matches and
bounded private-script reference matches. Supplemented the graph with
`from tools import NAME` imports and the template's actual builder reference;
reference counts alone do not establish an independent current consumer.

The private tool proposal covers every enumerated tool, including tentative
responsibility/destination, ownership, review state and validation/rollback
requirements. Categories are **provisional**, not an adopted path policy:

| Proposed category | Files |
| --- | ---: |
| Minimal root surface | 2 |
| Data | 5 |
| Research | 41 |
| Symbols, including template | 17 |
| Browser | 15 |
| Testing | 7 |
| CI | 16 |
| Operations | 6 |
| Performance | 6 |
| Development | 6 |
| Shared helpers | 3 |

The Windows metadata walk observed **65,465 pre-existing private files**
(13,046,584,300 bytes), excluding this audit's own output and the contents of
184 collapsed conventional cache/build/package directories. Recorded relative
paths, sizes, modification timestamps, file kind and matching Git ignore rule;
no untracked nonignored files were found in that enumerated scope. This is a
lower bound: **19 report directories could not be traversed** due to access
denials. Directory links are not followed. Cache exception candidates still
require review; collapsing their contents does not approve them as policy.

Prepared an **initial, unapproved 49-file raw/snapshot-tree move manifest**
(142,288,710 bytes) preserving relative names under `local/data/`.
Each original was SHA-256 hashed with stable size/mtime during hashing; this
did not establish archive/manifest agreement, backup, Syncthing state or producer
authority at kickoff. The next checkpoint refines this proposal to exclude
control/OS metadata. No copy, activation or deletion was performed. Other private files
and documents remain `needs-decision` until their individual ownership,
findings and retention purpose are reviewed.

The independent Linux interactive checkout was inventoried read-only at its
own older revision: 135 tracked Python tools, 43 Markdown documents and 27,681
private files, excluding 11 collapsed directories; one large tracked JSON was
outside the consumer scan's size limit. The dedicated Linux worker was separately
confirmed clean at another older revision using an offline status job. Neither
checkout was synchronized or changed. The worker's private files and the external
Syncthing staging area still need inventory; this is **not cross-host migration
acceptance**. The three acquisition/symbol producer checkouts were inspected
read-only and were clean; their output/configuration consumers remain to review.

**Reviewed priorities:**

- At kickoff, `verify_release_candidate_browser.local_revision` hashed only
  Army and Rules. The independent correctness correction below resolves that
  finding before the gate is used for v1.1+ complete-set acceptance.
- At kickoff, the P5 comparison pair was proposed for retirement to Git
  history. The bounded retirement checkpoint below records removal of its
  dedicated test/command while preserving accepted evidence, the maintained
  processed-handoff verifier and published Seed Soldier compatibility.
- Keep the artwork-review HTML template with its builder. Do not infer zero
  consumers from a Python-module-only reference search.

**Private evidence:** The completed Windows intake, tool proposals, candidate
move manifest and hash receipts are under
`local/research/project-infrastructure/tooling-workspace-cleanup/20261112-l0-windows-v2/`.
The sibling `20261112-l0-windows/` retains the Linux interactive capture and
partial first Windows attempt. That attempt was stopped after a slow reference
scan and replaced with a single-pass scan; its partial metadata is not an
accepted receipt. One-use capture/review scripts remain task-scoped under
`local/work/project-infrastructure/tooling-workspace-cleanup-l0/` and retire
after this project's accepted closeout. Per-file private metadata stays ignored.

**Validation:** The inventory integrity check passed exact Git/tool coverage,
all 124 unchanged tool hashes, all 49 original candidate hashes and both receipt
sets. The canonical `tools/run_checks.py --stage docs` passed Markdownlint
(49 files, zero issues), local links (48 tracked Markdown files) and backlog
structure. These checks validate this intake/documentation batch, not runtime
behavior, backup recovery or migration acceptance.

**L0 handoff at kickoff:** Resolve the unreadable report directories without changing ACLs
or deleting evidence implicitly; inventory worker/staging and producer handoff
dependencies; review each tool/document's independent purpose, side effects,
open findings and retention; then complete per-artifact dispositions and the
exception/backup decisions needed for L1 review. L0's exit is **not met**;
the parent backlog item remains open. No new location policy, executable
retirement or ignored-source removal is approved by this checkpoint.

### Host and source handoff checkpoint — 2026-11-12

**Baseline:** Clean `dev/tooling-workspace-cleanup` at
`4a00127b630a10907259165b8c26d4ac1e3eb63e`. Continued L0 read-only review;
neither Linux checkout nor producer repositories were synchronized or changed.

Completed the dedicated worker metadata intake at its separately pinned older
revision: **140 tracked Python tools**, 43 tracked Markdown files and **92
private files**, with eight conventional toolchain directories collapsed and
no enumeration errors. One large tracked JSON remains outside the bounded
consumer scan. Inventoried the actual source-staging families as the worker:
**27,560 files**, including control/OS metadata, with no traversal errors.
Inspected root access controls read-only. These measurements do not validate
the older worker's runtime artifacts against the current Windows revision.

Verified **24 Windows snapshot archive/manifest pairs** using the maintained
`snapshot_provenance` validator: manifest schema, exact archive bytes and
logical-content SHA-256 where declared. Ran the exact current activation
verifier from stdin as the worker, without installing code or activating files;
all **24 staged pairs** passed its path/archive-hash checks. The staged archive
and manifest hashes match the Windows pairs exactly. This establishes the
captured source identities, not source authority, backup recovery or cutover
acceptance.

The initial 49-file proposal included **two Syncthing control markers and
three OS directory-metadata files**. Its original receipt remains intact;
the refined proposal contains **44 source/provenance files**. The five excluded
files have separate ownership decisions and remain untouched. A Syncthing
marker is service-owned folder state, not an immutable source artifact to copy
blindly into a new location. L1 must account for that lifecycle separately.

Reviewed these producer/consumer boundaries for the future cutover:

| Owner | Current inputs/outputs and affected consumer |
| --- | --- |
| Army acquisition | Default `data/raw/` ZIPs and `data/manifests/snapshots/` provenance; explicit offline Army snapshot resolver and symbol-plan exporters consume the pair. |
| Wiki/Human Sphere acquisition | Default `data/wiki/`, resumable `data/work/wiki/` and snapshot provenance; research and activation consume pinned archives. |
| Symbol producer | Default raw-symbol destination and manifest directory; override/derived stages require explicit outputs. Consumer plan exporters and handoff/publication verifiers retain their separate responsibilities. |
| Complete runtime builder | Uses `latest_snapshot` or explicit source ZIP, API metadata and maintained inputs; hashes its build inputs independently of research provenance-manifest lookup. |
| Syncthing activation | Uses explicit staging mappings and recorded archive paths; relocate readers/destinations with producers and preserve byte identities. |

`latest_snapshot` orders candidates by **mtime, then case-folded filename**,
not the acquisition date in the name. Record an explicit selected source or
preserve timestamps and prove selection identity during relocation. Snapshot
provenance paths are producer-relative evidence: the general validator accepts
an explicitly selected archive, while activation currently uses the recorded
path as a lookup/destination. L2 must resolve that distinction without rewriting
immutable manifests or silently selecting between old/new copies.

**Preservation findings:** Source removals still lack verified recovery/restore
evidence. All five live receiver folders reported no pending files/bytes or pull
errors at capture; Windows GUI live status was unavailable. Configuration and
actual physical staging mappings require reconciliation before optional override
activation can be accepted. Exact configuration, permission diagnostics and
recovery gaps remain private. All 19 denied report directories remain unreadable
after a metadata/ACL-only review; none is approved for deletion.

**Evidence and resumption:** Private captures, producer contracts, refined
proposals, access reviews and receipts are under
`local/research/project-infrastructure/tooling-workspace-cleanup/20261112-l0-handoffs/`.
The first staging capture covered the default override path; the second also
inventoried the configured physical path. A wrong helper name in the one-use
verification harness was corrected; the failed receipt is retained alongside
the completed verification. **L0 remains open** for per-tool/document purpose,
side effects, findings, lifetime and disposition review, plus exception and
recovery decisions before L1. No path policy, moves, source deletion or service
configuration change is approved by this checkpoint.

### Release-tool lifecycle and correctness checkpoint — 2026-11-12

**Baseline:** Clean `dev/tooling-workspace-cleanup` at
`ea34259301d7bcc80364f6221756b252f33c6472`; its Source checks, installed-wheel
and deployment-smoke workflows completed successfully. Reviewed the release
acceptance cluster's independent current purposes, inputs/outputs, side effects
and retirement triggers. The browser verifier, Unit browser harness, checkout
server verifier, complete-build verifier, semantic baseline helper and root
check runner support current repeatable acceptance and are retained as active
tooling. Their eventual directory proposals remain subject to L1/L4 review.
The large historical reference-baseline reporter still needs a separate
extraction/disposition review; its reused served-version helper is not evidence
that every historical reporting branch must remain. The 1.0 source-coverage
and explanation audits retain their frozen source/finding evidence under the
existing documentation-map contract.

Implemented the separately prioritized browser-verifier correction without
moving tools or private inputs. It now selects **one complete `--db-dir`** and
uses the shared serving validator for Army/Rules/ITS integrity, schema,
publication and matched provenance checks. All three filenames/hashes determine
the expected served identity. The old two-path API and individual-database CLI
flags are retired for this tool; unrelated research/fixture APIs are unchanged.
The gate also rejects local selected-set/static drift during browser acceptance.
The [testing guide](testing.md#complete-set-release-candidate-browser-verifier)
owns the current command and its representative-browser acceptance limits.

**Validation:** Windows focused regressions passed **24 tests, zero skips**,
including real loopback Chrome at 390 px, missing complete-set members,
corrupt/incompatible/mismatched ITS, ITS-only identity changes and local drift.
Ruff passed for both changed Python files; repository-wide Pyright passed with
zero errors/warnings. This is local development evidence, not hosted-candidate,
Linux or final-release acceptance. Private lifecycle decisions and receipts are
under `local/research/project-infrastructure/tooling-workspace-cleanup/20261112-l0-release-tools/`.
**L0 remains open** for the other tool/document dispositions and L1 preservation
decisions. No path migration or private-source deletion is approved here.

### Completed P5 comparison-tool retirement — 2026-11-12

**Baseline:** Clean `dev/tooling-workspace-cleanup` at
`ba51e6d33afeccc315fb47794c7a61f0144b7d4a`. Applied the existing completed-file
policy to the plan's first low-risk tracked-tool removal, independently of new
directory-policy approval or private-data relocation.

Retired `tools/compare_symbol_canonical_paths.py` and
`tools/verify_production_symbol_processing.py` to Git history: their dated
legacy/external comparison purpose was fulfilled by the accepted P5 matched-input
parity and publication. The wrapper only composed the retained processed-handoff
verifier with that obsolete comparison; no reusable current logic needed extraction.
Removed the dedicated `tests/test_compare_symbol_canonical_paths.py`, its test-section
entry and the stale runbook command together. Four private references were frozen
intermediate runbook snapshots, not maintained operations; they remain unchanged.
No tracked consumers remain in application, CI, skills, scripts or producer/MCP
repositories. Historical descriptions remain explicitly historical.

Current processed/duplicate handoff checks, semantic publication preparation,
compatibility-alias validation and promotion recovery stay maintained. The
accepted matched-input raster report still matches its documented SHA-256;
all **22 pinned evidence, compatibility-policy, publication-manifest and runtime
database files** were preserved byte-for-byte. No private evidence, sources,
SVGs or runtime artifacts were moved or deleted; no new archive or wrapper was added.
The flat tool inventory is now **121 Python modules plus one template**, down
from 123 Python modules plus one template at kickoff.

**Validation:** The surviving handoff/preparation/promotion/test-registry cohort
passed **56 tests, zero skips**. Deployment-artifact verification passed all
**808 published SVGs / 807 browser references**, with embedded runtime data and
reviewed citations source-matched. Full Ruff, Pyright and documentation checks
also passed. Private disposition, consumer and preservation
receipts are under
`local/research/project-infrastructure/tooling-workspace-cleanup/20261112-l0-p5-retirement/`;
the focused run report is categorized under `local/validation/`.
At this checkpoint the larger runbook still mixed current guidance and historical
evidence. The following checkpoint resolves its disposition. Continue L0 for the
remaining tool/document lifecycles and L1 preservation decisions; this bounded
retirement does not complete L5 or authorize ignored-source removal.

### P5 artwork-review workflow and runbook checkpoint — 2026-11-12

**Baseline:** Clean `dev/tooling-workspace-cleanup` at
`86263d74adeea01fef9ac7fabedb2e3efdc53586`. The completed P5 parity runbook
mixed dated commands and unique acceptance details with current artwork-review
and promotion guidance. Its disposition is **extract-and-retire**: current
procedures now belong to the [symbol lifecycle](../data/README.md#offline-publication-artwork-review),
while the [pinned P5 results](testing.md#p57-override-provenance-classification)
retain the audit scope, input-selection roles, findings, original/candidate
manifest identities and acceptance limits. The superseded narrative is in Git
history; no duplicate private archive was created. Its tracked links and
historical references were reconciled. The three producer checkouts and MCP
checkout had no tracked consumers of the retired runbook or review commands;
ignored historical snapshots were left unchanged.

The audit exposed a current workflow gap: artwork review defaulted to the
already promoted November candidate, while no tracked tool produced its
required comparison format. `tools.build_symbol_artwork_review` now writes a
deterministic comparison from explicitly selected, hash-pinned manifests and
requires explicit current/candidate paths and a fresh output for review.
Both steps fail on mismatched inputs or existing outputs. Existing P5
comparison records remain accepted when explicitly selected; their review
fingerprints and decisions are not silently transferred to a new comparison.
At this checkpoint the classifier required legacy P5 evidence; the later
[provenance retirement](#p5-provenance-classifier-retirement--2026-11-12)
resolves its lifecycle, not a general future-publication classifier.

**Validation:** The affected review, classifier and test-registry cohort
passed **99 tests, zero skips**, including six real-Chrome cases. Targeted
Ruff and repository-wide Pyright passed. The documentation stage passed
Markdownlint, local links and backlog structure. Against the actual pinned P5
manifests and preserved artwork, the new comparison exactly matched the
historical changed/added/removed inventory; all **118** review pairs and
their hashes matched the historical page, with the old URL still flagged
as unresolved at that comparison stage. Both new outputs are run evidence
under `local/validation/symbols/publication/20261112-l0-review-cli-86263d74/`,
not artwork approvals. Before transferring the documentation, all 22 prior
preservation pins matched; the 21 other pinned files still match, while
`testing.md` is intentionally updated here.
No source acquisition, asset promotion, private evidence removal or path
policy approval occurred. **L0 and the parent cleanup remain open.**

### Reference reporter dependency checkpoint — 2026-11-12

**Baseline:** Clean `dev/tooling-workspace-cleanup` at
`4b70bb9157d2e46924a88096c27993684f332ac4`. The historical reference reporter
cannot be retired wholesale: its current-citation minimum supports the
[1.0 citation gate](releasing.md#version-10-data-completeness-gate), and its
explanation inventory supplies the retained clause-disposition validator.
Those source-review dispositions remain scoped evidence, not a requirement for
exhaustive source review or a release approval. Other reporting and investigation
branches still require individual lifecycle decisions.

The shared served-runtime identity check is now independent of the reporter.
The baseline keeps its existing two-database status and error interface; the
complete-set browser verifier reports a runtime-revision match rather than
incorrectly labeling its Army/Rules/ITS receipt a database-pair match. Both
retain explicit-origin validation and fail-closed snapshot comparison. The
[testing guide](testing.md#complete-set-release-candidate-browser-verifier)
owns the current acceptance scope; its baseline guidance now distinguishes the
two-database inventory from a complete-set release candidate. The narrow shared
helper is retained for these two consumers in the existing flat layout, without
approving the proposed L1/L4 path policy or retiring the reporter.

**Validation:** The Windows reporter, disposition and release-verifier cohort
passed **121 tests**, including real loopback Chrome; two optional Army archive
tests skipped because the ignored raw database is stale against the tracked
Army database. After tightening the receipt-shape assertion and adding the
postflight network-failure check, both targeted selectors passed. Targeted
Ruff, repository-wide Pyright, documentation checks and `git diff --check`
passed. The read-only current-citation CLI reported **495/495** declarations;
the disposition CLI validated four scoped reviews and no browser approvals.
These checks do not establish source semantics or full coverage. They also do
not validate the stale private raw database, a hosted candidate, Linux or
release acceptance.

No ignored source, private evidence, generated database or service was changed.
**L0 and the parent cleanup remain open.**

### P5 provenance-classifier retirement — 2026-11-12

**Baseline:** Clean `dev/tooling-workspace-cleanup` at
`151cc6307282be13ea18a555eb92433c21a280bc`. The classifier's independent
purpose was the completed P5 legacy-to-external attribution, not an ongoing
external-to-external classifier. Its accepted findings remain in the
[P5 evidence](testing.md#p57-override-provenance-classification); the
one-use generator and its dedicated tests are retired to Git history.
The artwork reviewer retains its version-1 report loader, cause labels and
fail-closed pin, coverage, pair-hash and summary checks. Loading a report does
not independently verify its attribution chain. Current raw/effective/processed
handoff validators remain separate.

The original selector's current-manifest path now contains the later promoted
manifest. For a read-only replay, the exact old manifest bytes were recovered
from the pinned Git revision into temporary session files, selected explicitly,
and removed afterward. The replay matched the retained report in every field
except the necessarily changed selection fingerprint: **118 assets, 154 source
identities and 25 multi-source assets**. The previously documented count of 24
was corrected. The original selector, report, overrides and all other private
inputs remain unchanged; no publication, acquisition or approval was performed.

**Validation:** The Windows artwork-review, raw/effective/duplicate/processed
handoff, candidate and test-registry cohort passed **121 tests, zero skips**,
including six real-Chrome cases. The retained loader also accepted the saved
118-pair report using pins and pair hashes independently derived from the
selected comparison and manifests. Targeted Ruff, repository-wide Pyright,
documentation checks and `git diff --check` passed. This does not constitute
Linux, hosted CI or release acceptance.

**L0 and the parent cleanup remain open.** This retirement does not approve
the proposed path policy, private-source deletion or a future general
provenance-classifier contract.

### Deployed-object discovery retirement — 2026-11-12

**Baseline:** Clean `dev/tooling-workspace-cleanup` at
`bf01666c822cd2afc7d52d84d6c8613c02051918`. The two non-catalog
keyword-discovery commands were bounded investigations, not the maintained
object builder or a complete source inventory. Their final read-only runs
reported **61/61** and **28/28** reviewed definitions, respectively, with
zero unreviewed candidates or missing maintained N5.3 citations. Retired both
commands and their discovery-only tests after moving the lasting checks to
`tests/test_source_conflict_publication.py`.

The two review manifests remain tracked, including all 89 source-scoped
decisions and caveats. The replacement regression pins their exact
identity/classification pairs, verifies current cited pages and summary/detail
anchors, checks summary-only and non-object boundaries, and preserves the
14 promoted source/database citation checks. It does **not** parse the source
PDF or discover new keyword matches. The review used the pinned English N5.3
source identified in the [historical source audit](v1.0-source-coverage-audit.md#deployed-object-source-discovery-v1s-073-2026-11-05);
the current curated source SHA-256 is
`ca6364073ea48854bf51fe1efc31f2c9cf22fb444283a75c3f595ef54463b57a`.
The non-catalog and expanded review-manifest SHA-256 values are
`0ea16bc6efd44617ad4f2d88ee572af8322609c2a912a2affe578a4f61b0f376`
and `4a603409d799a4d928a861bf58081555cf9ea07a36fdf074954a8107daec6080`.
Each hash matched both the baseline Git bytes and the working tree. Current
positive-object inventory, builder, storage, delivery and Unit-use checks remain
separate; unresolved source discrepancies were not changed.

The bounded private consumer inventory identified two snapshot-specific
promotion scripts already depending on other retired modules and several
historical snapshots. They were left untouched. The three producer checkouts
had no tracked reference to either retired command; this is not a claim about
unscanned private consumers.

**Validation:** Windows focused source, publication, storage, Include and
test-registry checks passed **62 tests, zero skips**, with **808/808** published
SVGs and **807/807** browser-referenced SVGs. In-memory mutation checks
confirmed that the retained regression rejects eleven forms of review/source
drift while accepting unchanged and reformatted inputs. Two separate raw-source
parity nodes were excluded because the ignored raw Army database is stale;
they were not needed to validate this retirement and were not claimed as passed.
Targeted Ruff, canonical Pyright, documentation checks and `git diff --check`
passed. No source, private input or generated database was changed. This is not
Linux, hosted CI or release acceptance.
**L0 and the parent cleanup remain open.**

### Weapon-source research-tool disposition review — 2026-11-12

**Baseline:** Clean `dev/tooling-workspace-cleanup` at
`aa6ef436195a389bd1ab36a4fbde74b83cca2c11`. Reviewed the remaining
Weapon Chart research cluster against its current source-research procedures,
maintained review configuration, tests and open source questions. The following
optional, read-only tools remain **bounded/open**, not standard build or release
dependencies:

- `audit_weapon_chart_profiles` retains the pinned PDF-to-Army profile and range
  comparison, including the open Kobra/Suppressive Fire/Katyusha discrepancies
  and seven auxiliary Silhouette conflicts. Its shared chart reader and output
  are consumed by other optional source reviews and publication regressions.
- `audit_wiki_weapon_chart_names` retains exact alias and repeated alternative-row
  handling for the pinned Wiki/Army pair. The current 174-identity inventory is
  resolved, but broader source-revision research remains open; its identity result
  does not settle the separate value conflicts or imply gameplay equivalence.
- `audit_weapon_traits_prose` and `audit_weapon_trait_cross_sources` preserve
  distinct PDF/Army trait and named-section review scopes; source-layout
  candidates remain review evidence, not confirmed defects.
- `audit_weaponry_family_clauses` checks its selected, source-pinned clauses and
  typed curated relationships without claiming complete prose or relationship
  coverage. `audit_weapon_definition_gaps` separately reconciles pinned profile
  and enrichment evidence without turning a chart match into a rules definition.

These are not kept merely because tests import them: their source scopes,
review manifests, explicit discrepancies and optional research procedures remain
independently useful while the source-research TODO and clarification work is
open. Outputs and private upstream inputs remain local; no new normal-build,
CI, serving or release dependency is introduced. Reassess the tools individually
when their named research scope closes or a superseding source revision is
selected. No command was retired, no source interpretation or maintained data
was changed, and no private evidence was accessed or moved in this review.

**L0 remains open.** This bounded retention decision does not approve the
proposed tools directory layout, path policy or private-data migration.

### Hacking Program statistics audit disposition — 2026-11-12

**Baseline:** Clean `dev/tooling-workspace-cleanup` at
`28a8f50a3ab6707c39b0df639154a18b1b212aa4`. Reviewed the distinction between
the retired one-use Hacking Device entitlement chart wrapper and
`audit_hacking_program_statistics_chart`, which independently checks the
twelve individual Program profiles against Army metadata and printed N5.3 p.58
evidence. Retain the latter as an optional, read-only, source-pinned audit:
Program rows appear in different orders in the chart and Army data, so it
reconciles by explicit Program identity and preserves the printed dash, target,
Skill Type and reviewed Special-clause meanings. It does not derive device
entitlements, Units, or deployed-object identities and is not part of standard
build, serving, or release acceptance.

On the current Windows checkout, the manifest-only command reported **12 rows,
zero mismatches**, and the expected source-order difference. The explicit
archive/PDF comparison also reported **12 rows, zero mismatches** and matched
the pinned Army archive SHA-256
`f103a7afd02e68d845cc9ce38b1948f46914676bbc6a5e6b790d0a04148b6c75`
and English N5.3 PDF SHA-256
`53921e91c2d3d62ad5f7125abcd4174b2cf937d45320233eed5b6d301b66af3f`.
The focused Hacking Device/Program source tests passed **7/7, zero skips**.
The retained tool serves repeatable verification of these pinned independent
source inputs; this does not assert completeness beyond the twelve reviewed
Programs or authorize changes to their source data.

No tool, manifest, source, database, or private input was changed. The
corresponding source procedures remain documented in
[`testing.md`](testing.md#n53-hacking-programs-statistics-source-chart).
**L0 remains open.** This disposition does not approve a tools-directory
reorganization, path policy, or private-data migration.

### Docker build-context containment and exception triage — 2026-11-12

**Baseline:** Clean `dev/tooling-workspace-cleanup` at
`ef1ffd3199a0f1b84de9d2439b8c8b3479dc1d8c`. Compared the actual
`.gitignore`, `.dockerignore`, deployment contract and font-source producer.
The Git ignore rules excluded temporary Google Drive transfer directories,
test caches and upstream font TTF/README inputs that were not all explicitly
excluded from Docker's build context. Added narrowly corresponding Docker
exclusions, leaving published WOFF2/OFL files, the three tracked runtime
databases and the symbol manifest untouched. This protects the context
boundary; it does **not** establish that those files entered a previous image.

**Focused validation:** `tests/test_deployment_scripts.py` passed **46/46**;
Ruff passed for that file. The regression tests the declared exclusion
patterns; no actual Docker engine/context inspection, installed-wheel build,
Linux run or hosted workflow was performed at this checkpoint.

**Proposed L1 exception classification (not yet approved):**

- Conventional tool locations can retain narrowly owned exceptions:
  `.venv/`, `node_modules/`, interpreter/linter/pytest caches,
  `*.egg-info/`, `build/`, `dist/`, OS metadata, editor preferences
  and the machine-local `AGENTS.local.md`. Review tool-owned transfer
  scratch paths individually before calling them permanent exceptions.
- The host-specific deployment environment file must stay excluded from
  publication; secrets require independent access controls and must not be
  exposed by a path audit or moved automatically.
- `reports/`, `docs/audits/`, ignored `data/` families, loose
  `data/generated/` outputs, `image_overrides/` and downloaded font
  sources are **migration candidates**, not general exceptions. Update their
  writers and independent consumers before relocation.
- Broad ignored `*.zip`/`*.patch` patterns may hide loose research or
  handoff artifacts outside `local/`; preserve existing files and decide
  placement from ownership and provenance rather than extending blanket
  exclusions. Review Docker context exposure of these other file classes
  separately.
- The dated `workflow-improvement-review-2026-11-04.md` is historical,
  but still holds a proposed catalog change-impact preflight not in the
  current backlog. Mark its retirement `needs-decision` until that
  recommendation is deliberately accepted, deferred or declined; do not
  silently promote all its dated recommendations into current policy.

**L0 and L1 remain open.** This isolated containment fix does not approve
the path taxonomy, a tracked-document retirement, a source move, deletion or
Syncthing reconfiguration.

### Dated workflow-improvement report retirement — 2026-11-12

**Baseline:** Clean `dev/tooling-workspace-cleanup` at
`943a80774ecca1cae52a5e3c706b679462014442`. Reviewed the dated
`docs/workflow-improvement-review-2026-11-04.md` against the current backlog,
documentation ownership, Git/CI workflow, test-section and development-status
implementations. Its November 4 observations were explicitly historical and
were not an approved task ledger. Current backlog, testing, CI, coordination
and agent contracts live in their canonical owners, so its earlier proposals
are not additional binding rules. The optional catalog change-impact preflight
and PR CI cancellation/root-cause diagnostics were **recommendations**, not
approved development commitments; any future adoption needs a new independently
scoped backlog decision, not preservation of an obsolete report.

**Disposition:** `retire-to-git-history` for the report, including its dated
100-commit sample, failed-CI observations and suggestions. Removed its sole
maintained index link; the only other tracked mention was the earlier
`needs-decision` note in this cleanup plan, now resolved here. Searches of
`src/`, `tools/`, `tests/`, `scripts/`, `config/`, `.agents/` and
`.github/` found no consumers. No unique open source finding, required
acceptance receipt or private file is being deleted. Git history preserves
the original evidence without keeping a frozen recommendation sheet in the
current documentation tree.

This is a bounded document retirement only; **L0/L1 and the parent cleanup
remain open**. It does not adopt or reject future catalog-impact tooling,
approve ignored-source deletion or grant path-policy approval.

### Optional override staging-path correction and L0 risk triage — 2026-11-12

**Baseline:** Clean `dev/tooling-workspace-cleanup` at
`307cd827de5aba12cbcbb8be6d2126bf3433549e`.
The inspected five-folder Syncthing configuration names the optional Linux
receiver `image-overrides/`; the existing activation mapping instead looked
under `image_overrides/`. Captured staging inventory found **113 synchronized
override files** under the configured receiver, none under the old lookup
sibling. The Windows source and checkout destination are still
`image_overrides/`, deliberately distinct from the Linux physical name.

**Correction:** Map repository-relative `image_overrides/` explicitly to the
configured Linux `image-overrides/` source in
`tools.activate_synced_assets`. Updated the maintained Syncthing runbook and
added hermetic dry-run/apply, source-identity and missing-mapping regression
tests. Activation remains explicitly selected, hash-measuring and
non-destructive by default; there is no fallback to the incorrectly spelled
sibling. **No actual Linux activation was performed**, and no Syncthing
settings, private file, live checkout data or published asset was changed.
This closes the *code/default-name mismatch*, not host runtime acceptance.

**Focused validation:** The activation test module passed **15 tests, with 3
platform-dependent symlink skips**; Ruff passed for changed Python files,
repository-wide Pyright reported **zero errors/warnings**, and docs/link/backlog
checks passed (Markdownlint: 47 files, zero issues). The Linux receiver and
actual checkout activation remain untested at this exact candidate revision.

**L0 exception and preservation triage (reviewed proposals, not L1 approval):**

- **Allowed-location candidates:** `.venv/`, language package caches,
  `node_modules/`, `build/`, `dist/`, editor/OS metadata and necessary
  machine-local environment files remain conventional tool-controlled
  locations. These are not general permission for arbitrary private sources
  outside `local/`; secret files require separate access controls.
- **Active migration candidates:** ignored `data/raw/`, `data/wiki/`,
  `data/pdf/`, `data/manifests/snapshots/`, `data/work/`,
  `data/generated/` extras, `image_overrides/`, `reports/`,
  `docs/audits/` and nonpublished font source inputs. Their live producers,
  consumers, privacy and Syncthing configuration must be reconciled before
  moving bytes. The **three selected tracked runtime DBs** are exceptions
  to moving `data/generated/`, not ignored output.
- **Syncthing-owned controls:** the two captured `.stfolder` markers are
  service state; the three captured `desktop.ini` files are OS metadata.
  They were excluded from the **44-file** verified source/provenance move
  proposal. Leave controls in place until separately reviewed reconfiguration;
  never copy them as source evidence or delete them with archives.
- **Source preservation:** 24 Windows archive/manifest pairs and their 24
  Linux staging counterparts matched exactly at capture. This confirms
  captured identity, not recoverable backup. Windows Send Only and Linux
  Receive Only are *replicas*, not independent immutable backups; Linux's
  five receiving folders reported no configured versioning.
- **Access-blocked reports:** 19 Windows `reports/` directories failed
  read-only enumeration/ACL inspection. Their contents and lifecycle cannot
  be classified; preserve the directories, do not change ACLs automatically,
  and require authorized inspection before any root-report relocation or
  cleanup. Do not infer their contents are disposable test scratch.
- **Cutover gates:** verify independent backup **and trial restore** of each
  source family; resolve those 19 ACL gaps with authorized access; confirm
  Windows live Syncthing state (earlier local GUI query failed); exercise
  Linux dry-run override activation at an agreed exact worker Git revision;
  rehash candidate inputs before migration; pin source selection rather than
  depend on changed mtimes; update producer defaults and all consumers in
  L2; approve L1 layout/exception decisions separately. No step authorizes
  bulk removal from legacy paths.

The private per-file inventories, exact source/staging hashes, Syncthing
configuration observations and ACL probes remain in
`local/research/project-infrastructure/tooling-workspace-cleanup/20261112-l0-handoffs/`.
**L0 and L1 remain open**; the category list is a bounded reviewed proposal,
not a permission to migrate/delete ignored assets.

### Development-tool retention and archive context boundary — 2026-11-12

**Baseline:** Clean `dev/tooling-workspace-cleanup` at
`a7361d345db65069859d5e66587dcfcdf254f832`.
Reviewed the actual Docker image and deployment contract, active determinism
and optional full-asset CI callers, archive helpers and Linux worker state.

**Purpose-based L0 dispositions:**

- `tools.activate_synced_assets` is **retain-active** for development and
  source research. It verifies/copies explicitly selected private source
  snapshots, PDFs and optional override inputs into a development checkout
  only. The Linux *deployment* path instead consumes the three Git-tracked
  runtime databases, symbol-publication manifest and published static assets;
  release Docker construction does not invoke this activation tool. Its
  retention is not a requirement to sync private files onto the server.
- `tools.create_work_archive` and `tools.snapshot_archive` are
  **retain-active**: the cross-platform determinism manifest builder consumes
  both, and the snapshot helper also supports the maintained full-asset
  bundler. `create_work_archive` uses an explicitly selected scratch
  destination inside the determinism build; its optional CLI default creates
  a transferable ZIP beside the checkout. Classify that default as a
  specifically reviewed external-handoff case in L1/L2, not disposable
  scratch or an excuse to remove the reproducibility implementation.
- `tools.build_full_asset_bundle` and `tools.stage_full_asset_bundle`
  are **retain-active**, with independent deterministic bundle creation and
  optional full-asset CI transfer/validation. The builder's default
  `reports/full-assets.zip` and the optional external transfer are output
  placement/lifetime review candidates, **not** grounds to retire the tools
  or silently change a CI command.
- `tools.prepare_web_fonts` remains **retain-active**: it converts explicitly
  selected upstream TTF downloads into tracked WOFF2/license publication.
  Upstream TTFs currently ignored alongside web static assets are L2/L3
  private-input relocation candidates. The supported explicit source-root
  argument permits a future `local/` path without an implicit source
  search or altering the published browser font tree.

**Docker context containment:** `.gitignore` broadly excludes loose
`*.zip` and `*.patch` files, which could include private handoffs outside
`local/`. Added corresponding `**/*.zip` and `**/*.patch` patterns to
`.dockerignore`. Neither Dockerfile copies these file types, and
`reports/`, tracked runtime databases and the published symbol manifest
retain their existing explicit treatment. The focused deployment-script
tests passed **46/46**, Ruff passed and `git diff --check` was clean.
These tests assert declared ignore patterns; no Docker engine or actual
context archive was inspected here.

**Linux verification still blocked:** The worker's last observed clean
checkout was `dev/v1.0.0` at `a47a573d2afd6376dcc46abe9539e04177c6ca98`.
An explicit remote fetch and a second Git-operation fetch both returned
`git_command_failed`, with no actionable diagnostic; a checkout dry-run
also refused. No Linux Git checkout was updated, and no revised
`activate_synced_assets` code was exercised on the receiver. Diagnose
remote Git access/ref visibility through the worker before claiming
host-side acceptance; neither a change to local Windows Git nor a copied
script is a substitute for validating the pinned worker revision.

**L0 remains open:** Preserve the unreadable report folders and all private
archives, verify independent source backups/restores and full producer
handoffs, resolve Linux worker fetch/access, then review and approve L1
exceptions/path moves separately. No ignored data, Syncthing setting,
published DB or graphics were modified by this checkpoint.

### Linux Git diagnostic checkpoint — 2026-11-12

**Candidate:** Windows `dev/tooling-workspace-cleanup` remained clean at
`ac8050c0c29c9546c935365fb4b31b3f7f6a32ab`. An explicit Windows
MCP fetch succeeded. GitHub confirms the remote cleanup branch points
to the same SHA; Source checks, installed-wheel smoke and deployment
smoke all completed successfully there. No further push was required.

The updated MCP job interface now preserves bounded, client-safe Git
failure details. Both Linux `sync_worker_repository(fetch)` and
`git_worker_operation(fetch)` failed at Git `fetch` with
`git_ref_unavailable` (category `reference`, Git exit 128).
This is an actionable classification, **not** proof of the cause.
The fetch request specifies no branch; GitHub no longer lists the
worker's checked-out `dev/v1.0.0` branch. A stale branch-specific
`remote.origin.fetch` refspec is a plausible explanation, but its
actual value has not been read and credentials/remote configuration
have not been independently checked. Do not label the failure fixed.

A read-only Linux fast-forward preview confirmed the worker remains
clean on `dev/v1.0.0` at
`a47a573d2afd6376dcc46abe9539e04177c6ca98`; its cached
`origin/dev/v1.0.0` target was `2c312edbc38d47663dfb053e57efc2724a4618e4`.
A detached checkout dry-run for `ac8050c0` failed at `rev-parse`
because that commit was not locally available. The worker checkout
was **not** synchronized, checked out or changed.

**Next host gate:** Have the operator inspect the worker service
account's `remote.origin.fetch` configuration and remote branch
visibility, without exposing credentials or changing Syncthing.
Correct a stale refspec only if confirmed, then explicitly fetch and
verify the expected commit, detached-checkout the clean worker to that
SHA, and dry-run one actual staged `image-overrides/` file through
the corrected `tools.activate_synced_assets` mapping. Record the
selected file's expected destination, hash and dry-run result without
activating or overwriting private files. This Linux acceptance is
still blocked; Windows and GitHub CI passing do not substitute for it.

### Reference-baseline reporter disposition — 2026-11-12

**Baseline:** Windows `ac8050c0`, read-only lifecycle/consumer review.
`tools.report_reference_baseline` is a 3,292-line multi-purpose
reporter and is **retain-active pending a scoped extraction review**,
not eligible for wholesale retirement:

- The standalone current N5 citation-minimum audit serves the maintained
  1.0 citation contract. A fresh read-only run returned **495/495**
  current citations, zero missing; this checks declarations, not source
  contents or semantic acceptance.
- The two-database Army/Rules baseline, optional pinned Army archive
  comparison and served-pair check are independent offline investigation
  and historical publication evidence. They do not validate ITS or the
  complete-set release-candidate browser gate.
- The frozen 367-record explanation reconciliation and its declaration,
  numeric replacement, conditional-declaration, visibility, pilot,
  batching and reviewed-evidence branches are optional source-scoped
  investigations. They must be evaluated branch by branch against the
  preserved findings and open reconciliation work rather than retired
  simply for being dated.
- `tools.source_coverage_dispositions` imports the reporter's
  `reconcile_explanation_inventory` and current-collection identity
  contract. Extract or relocate those active interfaces only with that
  consumer and its tests; CI has no direct reporter invocation.

The read-only explanation reconciliation returned **367 frozen, 466
current, 350 retained, 116 added, 17 retired** and **830 source locators
pending clause review**. The current reporter and disposition test
coverage is in `tests/test_report_reference_baseline.py` and related
source-disposition tests. No private input or publication artifact
was changed by these commands.

**Output-path finding for L2/L6:** Generic `--json-output` and
`--markdown-output` writers accept arbitrary paths and overwrite
existing files; the specialized pilot and batch output paths are
restricted to `local/`, but still overwrite. The current testing guide
uses categorized `local/validation/` destinations for baseline
evidence. Review all output branches and their retained consumers before
changing defaults or adding fail-closed destination checks. Do not
prematurely break supported research commands or treat generated review
output as independently accepted evidence.

**Validation:** The reporter suite passed **64 tests, 2 skips**;
the independent disposition consumer passed **23/23 tests**. The two
read-only reporter commands returned successfully without writing output.
The documentation stage passed Markdownlint (47 files, zero issues),
local links (46 files) and backlog structure; `git diff --check` passed.
These are Windows checks, not Linux activation, source-authority or
hosted acceptance for this documentation change.

**L0 remains open.** This review grants no tool retirement, output
migration, private-file deletion or L1 path-policy approval.

### Linux worker activation acceptance and document triage — 2026-11-12

**Host gate resolved:** The operator confirmed that the `mcpworker` Git checkout
had the branch-specific fetch refspec
`+refs/heads/dev/v1.0.0:refs/remotes/origin/dev/v1.0.0`.
That branch no longer exists remotely. Replacing the worker's refspec with
`+refs/heads/*:refs/remotes/origin/*` restored normal branch fetching.
An explicit MCP Linux fetch completed with exit code 0, followed by a
successful clean, detached checkout at the reviewed remote cleanup commit
`ac8050c0c29c9546c935365fb4b31b3f7f6a32ab`; the worker subsequently
reported that exact HEAD and a clean tree. The separate interactive Linux
checkout was not synchronized by this operation. The Windows development
checkout was clean at `b637df0fa5037696b1dabecbfd5aab796644eadf`
(documentation-only follow-up to the remote revision).

**Actual receiver dry-runs:** On the pinned Linux worker, the maintained
`tools.activate_synced_assets activate --file` command returned exit code 0
and `planned` for each of:

- `image_overrides/characteristics/cube.svg`
- `image_overrides/units/achilles-team-1-1.svg`

These resolve to files beneath the actual hyphenated Syncthing receiver
`image-overrides/` and plan copies to the matching underscore-named checkout
destinations. The tool read both source files and measured SHA-256 internally,
but did **not** emit the digests or verify immutable provenance pins; those
stronger source-identity claims remain outside this acceptance. Neither command
used `--apply`. No private file was activated, overwritten or deleted, and
no Syncthing configuration or production deployment was changed.

**L0 document dispositions (no removal):**

- `docs/faq-v0.1-scope-inventory.md` is **retain-frozen-evidence**. Its
  question/semantic inventory, bilingual source qualifications, reviewed
  identity pins and deferred ITS applicability have independent ongoing
  research value and are cited by source history, official clarifications and
  source-coverage findings. The maintained FAQ model and regression manifest
  own current published semantics; this report does not become a second
  active task list.
- `docs/v1.0-coverage-workflow-plan.md` is **retain-frozen-evidence pending
  later consolidation**. The V1S-082 acceptance scope is superseded by the
  current citation gate; the document's pilot methodology, measured limitations
  and optional P2/P3 ideas are historical research, not required release steps.
  The independently open optional comprehensive reconciliation is owned by
  `docs/TODO.md`; the maintained disposition validator, tests and source audit
  own implemented behavior/evidence. The historical source audit directly
  links to this plan's P1 details, so do not delete it without preserving
  that unique context and correcting the link.

**Validation:** Linux focused activation regression suite **18 passed, zero skips**
at the pinned worker commit. Windows documentation checks passed Markdownlint
(47 files, zero issues), link validation (46 tracked files), backlog validation
and `git diff --check`.

The Linux mapping/runtime gate is now accepted. **L0 remains open** for the
remaining ownership/disposition inventory, source backup-and-trial-restore
evidence, nineteen inaccessible Windows report directories, and L1 decisions
on exceptions and migration. This checkpoint approves no ignored-data moves,
source deletion, automatic worker synchronization or L1 path policy.

### Historical 1.0 source-input auditor disposition — 2026-11-12

**Baseline:** Clean Windows `dev/tooling-workspace-cleanup` at
`5348319e9eb5f2b786ee1114e9ad979fad737654`, read-only
source/consumer review. `tools.audit_1_0_reference_inputs` is
**retain-active pending scoped extraction review**, not eligible for
whole-file retirement merely because its initial report is named 1.0.

- The separate active `tools.audit_reinforcements_applicability` imports
  `verify_reinforcements_inputs` and `SourceEvidenceError` to preserve the
  fail-closed distinction between verified historical N4 PDFs and unverified
  N5 procedural authority. This is a current source-integrity boundary, not a
  historical test artifact. The application-rule regression tests also reuse
  the reporter's `_WikiHeadings` parser; a test import alone is insufficient
  justification for retaining the entire historical report.
- The opt-in CLI retains an independent, documented offline source-evidence
  workflow: exact supplied Wiki history/revision identities, curated Wiki
  snapshot members and headings, source-pinned Core/FAQ PDFs, and independent
  enrichment gaps. It accepts explicit inputs and does not acquire sources,
  amend curated records or establish semantic completeness. Its source-report
  scope is distinct from current build and release acceptance.
- Its `--json-output` and `--markdown-output` paths currently create
  parent directories and overwrite existing files without limiting
  destinations to categorized `local/`. Review output lifetimes and safe
  path handling with the broader L2/L6 writer policy before changing this
  documented command. Extract only genuinely reusable source/parsing
  interfaces if/when its historical composite report is retired.

**Validation:** `tests/test_audit_1_0_reference_inputs.py` **50 passed**;
`tests/test_audit_reinforcements_applicability.py` **16 passed**; zero
skips in both. No sources, tests, private inputs, public artifacts or
Git module paths were changed in this review. **L0 remains open**.

### Database audit lifecycle and version-alignment correction — 2026-11-12

**Baseline:** Clean `dev/tooling-workspace-cleanup` at
`e68c829216fc87024c45745a21c74e8f88ba6016` before this change.
Reviewed `tools.audit_database_separation`,
`tools.audit_runtime_database_surface` and
`tools.audit_semantic_deduplication` against their maintained data-model
contract, CLI entrypoints, actual runtime consumers, tests and current published
Army database. All three are **retain-active**:

- The application/raw separation audit still proves that raw-only source
  tables are excluded from the published database and checks metadata,
  foreign-key and runtime-validation boundaries. It composes the separate
  runtime-surface probe; retiring either would remove a current invariant.
- The runtime-surface audit discovers normal repository method reads and
  classifies table/field usage independently of the raw-archive inspection.
  Its maintained synthetic fixture is reused by other source/presentation
  tests, but that reuse is not the sole reason for retention.
- The semantic deduplication audit independently measures published logical
  Unit payload reuse. A read-only run on the tracked Army database reported
  **5,020 profile occurrences** (1,108 distinct logical-Unit payloads) and
  **12,993 loadout occurrences** (3,448 distinct logical-Unit payloads).
  This is a reproducible measurement, not an unfinished migration or a
  publication requirement.

**Confirmed correctness gap and bounded fix:** Before this change,
`audit_database_separation data/generated/army.db` failed on **14
unexpected tables**. Those tables are maintained Army v27–v31 publication
overlays; `Database.validate()` already recognizes them, whereas the
separation audit assumed the base v26 table list for every version. The audit
now uses the existing versioned publication table registries, explicitly
classifies approved overlay tables, rejects unknown extensions, and inspects
foreign keys across the selected full publication schema. The v26
application/raw fixture and its strict source-only checks remain unchanged.
A focused end-to-end regression against the actual tracked v31 database
prevents the same false failure from recurring.

**Separate private raw-sibling issue:** The default audit still refuses the
locally ignored `data/generated/army.raw.db` because its metadata differs
from the tracked application database. This is an accurate fail-closed
response to mismatched input generations, **not** an exception to remove or
silently ignore. Running with an explicitly selected absent raw sibling
returned exit code 0: **35 canonical, 63 contextual and 46
source/provenance-only logical tables**, no foreign-key or
validation-source-table blockers, with `rawArchive: not_available`.
This does not validate a current lossless raw sibling or authorize replacing
one. Rebuild or select a matched pair only in a separate approved input
maintenance task.

**Output-path follow-up (L2/L6):** Each of these retained audit CLIs
accepts an optional `--output` path, creates parent directories and overwrites
existing output; none enforces the proposed categorized `local/` retention
policy. Review its callers, run-ID conventions and compatibility before a
later output-policy change.

**Validation:** Windows tests for separation **12 passed**, runtime surface
**3 passed** and semantic deduplication **3 passed** (all zero skips).
Focused Ruff passed for the modified auditor and its test; repository Pyright
passed with **zero errors/warnings**; docs/link/backlog checks passed.
The supplied tracked database was only read; no private raw archive,
published database, normal serving or deployment was modified.

**L0 remains open.** This correctness fix does not approve L1 taxonomy,
private-file migration/deletion, a current raw-source reconstruction, or
retirement of these maintained checks.

### Raw archive retirement decision — 2026-11-12

**Disposition:** Retire `army.raw.db` as a retained development artifact,
then retire its intermediate SQLite format when the remaining independent
consumers have safe replacements. This resolves the earlier open
artifact-deduplication decision; it is **not** permission to delete private
bytes or to drop source-integrity tests simply because they mention the archive.

**Verified boundaries and affected consumers:**

- The selected complete runtime set contains only `army.db`,
  `rules_n5.db` and `its_18.db`. `validate_database_set`, normal
  serving and Docker deployment neither require nor read `army.raw.db`.
  The complete builder already creates and discards raw SQLite inside its
  temporary staging directory rather than installing it in the selected
  output directory.
- The base `export_database` operation still generates a paired raw archive
  to preserve exact normalized source rows, including absent versus null
  distinctions. The standalone `infinity-db export` CLI publishes that
  pair, and `database-health --require-raw` and
  `tools.inspect_raw_archive` expose explicit audit contracts.
- Complete-build publication stages v27–v31 currently require a validated
  Army/raw pair. The source-bound variant-usage projection reads raw-only
  profile/loadout occurrences, extras, include and Peripheral relationships
  while comparing them with the application and Rules output.
- Retained optional source audits include
  `audit_army_faction_semantics`, `audit_source_presentation`,
  `audit_source_variant_inputs`, `report_reference_baseline`,
  `audit_database_separation` and clients of
  `paired_audit_connection`. `build_determinism_manifest` fingerprints
  the raw artifact as reproducible build evidence. Their purposes must be
  reconsidered independently; tests alone do not justify retaining the
  archive, but live source/provenance checks cannot be silently discarded.
- The current ignored `data/generated/army.raw.db` already fails the
  application/raw pair-metadata check against tracked `army.db`. It is
  **not** accepted as a usable audit input or current release dependency;
  preserve it pending byte/ownership/recovery classification instead of
  silently replacing or deleting it.

**Implementation sequence:** First define source-equivalent reads from the
pinned Army ZIP and normalized model (or deterministic, job-local SQLite
materialization) with exact source-identity verification. Move independent
source audits and variant/publication transformations onto that contract,
preserving source-only coverage and negative tests for missing, reordered,
duplicated and mismatched occurrences. Then update standalone export and
pair-health/inspection contracts, and stop emitting raw SQLite once no
accepted build/research consumer needs it. Independently compare the three
published database hashes and semantic/citation fixtures from identical
pinned source inputs before cutover. Remove raw-only fixtures and tests
**only** when their independent invariant is superseded, not merely to
make the suite pass.

The separate general build-path redundant-serialization task remains open
until an implementation proves that all required untrusted-input validation
and source integrity survive without double work. Do not alter the current
canonical [data lifecycle](../data/README.md) to describe a not-yet-applied
contract. Changes to CLI compatibility or persistent ignored files require
their own bounded acceptance; the current cleanup manifest's independent
backup/trial-restore and explicit deletion approval still apply.

**No code or private-file modification** is authorized by this L0 decision
alone. The open implementation is tracked in [the backlog](TODO.md).

### First raw-source build cutover — 2026-11-12

**Implementation:** The complete build's Rule/Variant usage projection now
reads `stage/normalized.json` rather than `stage/army.raw.db` as its source
for Skills, Equipment, source occurrences, Include chains and Peripherals.
`src/infinity_db/variant_usage_source.py` reconstructs normalized relations
only in a transient, read-only in-memory SQLite connection (no duplicate
lossless row-JSON storage). It verifies the **entire** normalized document
against the original `export_pair_sha256` carried in `army.db`, reconstructing
the base Army v26 publication fingerprint and compatibility revision from
the versioned v26–v31 application schema. Missing, corrupted or different
generations fail closed before source rows are projected.

The common variant projection still supports the explicitly paired raw
archive for existing external audit and parity consumers, but the complete
builder now selects the verified normalized source. Exact source ownership,
Extra signatures, context-only Include/Peripheral provenance, stable ordering
and publication validation are not relaxed. The published variant source
snapshot intentionally omits the transient raw-database byte digest, which
the portable publication contract already excluded.

**Focused verification:** A new regression test compares all normalized
relational tables against the existing raw archive from the same fixture,
verifies that the source adapter works without a raw file, rejects modified
source rows and export metadata, and compares portable variant candidate
publications from both input routes. Existing variant-usage tests continue
exercising source-owner, Extra, Include, Peripheral, truncation and tamper
failure paths.

**Pinned full-build acceptance:** The maintained
`tools.verify_complete_database_build` command rebuilt **twice** from
`data/raw/JSON 20260929-114335.zip`, whose declared and checked SHA-256 is
`f103a7afd02e68d845cc9ce38b1948f46914676bbc6a5e6b790d0a04148b6c75`.
Both complete runtime sets passed source normalization/lossless validation,
Army v31 / Rules v17 / ITS v2 health, **151** variant groups, **62**
reviewed Weapons, **69** citations, **41** semantic API baseline routes,
all embedded catalog/provenance assertions, and byte-identical repeatable
SQLite output. Two-build SHA-256 identities were
`army.db=b6e556bc3cd55a062dbebe29c912966783ccf9ec3cdb9abb88f638c305ff5716`,
`rules_n5.db=7260dd1a193f93c8cd8c99d617070c9380d474ba76be1be0549996cd06b63fd5`,
`its_18.db=e88eb6e9934443f762d8f143efcfd8cdf300636424b3a55c78df569ea43d2b94`.
The new build-input code enters recorded builder provenance, so these are
**post-change deterministic hashes**, not claims of equality with the old
release image. The separate builder test suite passed **18/18**,
the original variant usage suite **98 passed, 2 skipped** (pinned raw pair
not available), the new normalized-source tests **5/5**, and the runtime
variant storage suite **13/13**. The optional browser-publication suite
skipped all **9** tests for unavailable pinned raw assets; no browser acceptance
is claimed from those skips. Repository Ruff and Pyright passed; no tracked
release binaries were replaced.

**Remaining boundary:** This slice does not stop `export_database` from
generating its temporary raw sibling; Army v27–v31 overlay publishers,
other source audits and standalone `infinity-db export` still depend on
that format. The `data/generated/army.raw.db` ignored file was neither
opened for this cutover nor modified. Moving or deleting it still requires
the reviewed local migration manifest, backup evidence and separate approval.
The next implementation slice must replace the overlay publishers' raw-pair
contract without weakening their checksums or atomic publication behavior.

### Army v27–v31 normalized provenance cutover — 2026-11-12

The five complete-build Army overlay publishers now accept either an explicitly
selected, paired raw SQLite source (legacy API) **or** a complete normalized
source verified against the application's original export generation. Shared
verification lives in `database/normalized_source.py`, not in the
variant-usage domain module; its full-model validation, base-published-table
fingerprint and compatibility restoration preserve the v26 export attestation
through successive v27–v31 overlays. Supplying both sources or neither fails
closed. Each publisher still validates the preceding schema/read model,
authored source identity, foreign keys and the new full-table publication
checksum. The complete builder explicitly passes `raw=None` and the generated
`normalized.json` to all five, and re-verifies that source before Rules
publication. No raw sibling metadata is mutated along that route.

Standalone callers retain the existing positional raw-pair API and matching
post-publication metadata updates; historical pair-health and raw-source audit
semantics have **not** been retired. Synthetic database-set builder fixtures
continue using the old pair API because their normalized placeholder is
intentionally not a valid source document. Those fixtures verify the real
builder selects the new explicit rawless route. Pinned ZIP acceptance is the
source-integrity gate for actual complete builds.

The base exporter still creates temporary `army.raw.db`; removing that
duplicated serialization and addressing standalone `export` consumers are
separate backlog work. The ignored private `data/generated/army.raw.db`
was not deleted, overwritten, moved or accepted as a matched pair.
Neither current production data nor tracked release databases were changed.

**Validation:** Existing raw-pair publisher suites passed v27 **12/12**,
v28 **15/15**, v29 **19/19**, v30 **26/26**, v31 **19/19** (91 total);
new normalized source/selection tests **6/6** and synthetic
database-set builder suite **18/18**. Ruff, Pyright, Markdownlint,
document link/backlog checks and `git diff --check` passed.
The pinned source ZIP `JSON 20260929-114335.zip`
(`f103a7afd02e68d845cc9ce38b1948f46914676bbc6a5e6b790d0a04148b6c75`)
was rebuilt twice in disposable local directories with no tracked
release file replacement. Both complete runtime sets were healthy,
retained **151** variant groups, **62** reviewed Weapons, **69**
citations, **2019** symbol mappings, **808** verified SVGs and **41**
semantic API baseline routes, and had byte-identical SHA-256 values:
`army.db=dd865af9ab47b14a8033b6dbb3dccac8e2d7709470ae31e376d6369ce2f3cbaf`,
`rules_n5.db=51f882397c8804143293ed3b4f2c8fc37e5bc5ded35fb34b7aefbe8c85b47a59`,
`its_18.db=e88eb6e9934443f762d8f143efcfd8cdf300636424b3a55c78df569ea43d2b94`.
These hashes are for the new source-code provenance, **not** expected
to equal previous commit hashes. One preliminary two-build attempt
correctly rejected a developer's source-file edit while building
(`Build inputs changed during generation`); the subsequent
unchanged-tree rerun completed successfully. No full project suite
was run in this slice.

### Complete-build raw SQLite generation retirement — 2026-11-12

**Scope:** The complete runtime builder now invokes the base Army export with
`include_raw=False`, after the maintained Army ZIP merge, normalization and
source-anomaly baseline. The existing exporter still builds and validates the
full relational staging database, including every source-only normalized
table and source-to-canonical consistency constraint, *before* publishing
the self-contained v26 Army application database. The complete normalized
source and its deterministic `export_pair_sha256` remain available to the
already-cut-over Army v27–v31 overlays and variant/Rules publishers. The complete
build no longer writes the approximately 47.6 MB transient `army.raw.db`
archive (nor its duplicate lossless row JSON) to its staging directory.

**Compatibility and safety:** Standalone `infinity-db export` and the
programmatic default `export_database(...)` continue to create and validate
both siblings, including the raw-first/application-last recovery contract
and all raw integrity checks. The application-only mode refuses an existing
raw sibling rather than silently leaving a stale, invalid pair. The normal
three-database runtime publication still occurs only after all three databases
and build identities pass validation; no tracked release binary is replaced
by these development changes. This cutover does not retire the lossless raw
format for standalone research/audits, change source-only normalization
semantics or authorize removal of any ignored `data/generated` file.

**Next tasks:** Independent raw-dependent auditors, pair-health and source-row
inspection interfaces, and standalone export retention require a separate
consumer-by-consumer lifecycle decision. Keep the current full export API
backward-compatible until those invariants have replacements. The separate
combined-path double-validation optimization is not part of this change.

**Acceptance:** The direct Army source/CLI suite passed **21/21**, the full
database/export regression module **175/175**, and the complete-set builder
suite **18/18** (214 tests, zero skips). The new unit tests prove
byte-identical application SQLite output between raw-paired and rawless
exports with and without finalization, no raw-archive creation, fail-closed
refusal of an existing sibling, and continued default paired-export health
and metadata-mismatch rejection. Ruff, Pyright, Markdownlint, documentation
links/backlog validation, and Git whitespace checks passed.

The maintained `tools.verify_complete_database_build` acceptance rebuilt
**twice** from `data/raw/JSON 20260929-114335.zip`, SHA-256
`f103a7afd02e68d845cc9ce38b1948f46914676bbc6a5e6b790d0a04148b6c75`,
in disposable output directories. The log reports only the 8,413,184-byte
application export (no raw archive), and both builds passed the 73 normalized
source checks, matched the reviewed 116-warning anomaly baseline, preserved
**151** variant groups, **69** Weapon citations, **2019** symbol mappings,
**808** verified SVGs and **41** semantic API routes. The complete outputs
were byte-identical across runs:
`army.db=9a1577aebd0214a30ccd174d32b58c8c5a257dc5e26d3ab248ce193e74926fad`,
`rules_n5.db=fbbfb45a4e17edb180f30a56428c0faa48dc8d5976ebf0a291dd2d11ef7ff38f`,
`its_18.db=e88eb6e9934443f762d8f143efcfd8cdf300636424b3a55c78df569ea43d2b94`.
These are the **post-code-change** revision fingerprints; older build hashes
need not match, while the source identity, published inventories and API
behavior remain checked. The full project test suite was not run.

### Standalone raw-audit consumer triage and first cutover — 2026-11-12

**Scope:** Audited maintained `tools/` callers that require or optionally
read `army.raw.db`, its generated `raw_database_path`, or the shared
`paired_audit_connection` adapter. Call-site and test review distinguishes
current independent invariants from the mere presence of historical tests.

- **Migrated dual-source interfaces (retain-active):**
  `tools.inspect_raw_archive` now supports an explicit
  `--normalized PATH` route, using complete
  `verified_normalized_document` source-to-application attestation. Exact
  source rows, empty-table counts, stable positions, bounded pagination,
  absent-versus-null fields and source-ID refusal semantics match the
  paired raw archive. The old `--raw` and implicit sibling path remain
  available, but are never silently substituted for missing normalized
  input. A new source-path conflict is rejected. The tool remains read-only
  and keeps its historical module name for compatibility.
  `tools.build_variant_usage` now accepts either `--normalized` or
  `--raw-db` as an explicitly selected, mutually exclusive source; the
  production projection already uses normalized source. Its existing
  candidate-only/no loose publication guards are unchanged.
- **Retain-active, migrate next:** `paired_audit_connection` currently
  attaches a validated raw sibling to expose source-only tables to
  `audit_normalization_links`, `audit_peripheral_semantics` and
  `audit_relationship_semantics`. These review normalization-vs-gameplay,
  exact Peripheral attachment and Include relationship invariants. Plan
  an explicit normalized-source adapter with equivalent relational queries,
  application provenance and source-owner negative tests before removing
  raw attachment. Keep the combined legacy schema route when intentionally
  supplied; do not retain unused historical behavior solely because a test
  still invokes it.
- **Retain-active, migrate as independent source audits:**
  `audit_army_faction_semantics` derives and compares application Army
  identities against source factions and roster occurrences;
  `audit_source_presentation` measures unrepresented source fields and
  occupation; `report_reference_baseline` has a separate, independently
  used citation/source gate and optional pinned archive verification.
  The `audit_database_separation` tool already supports a missing raw
  sibling and validates current published schemas. Source identity and
  row/field evidence still need to be verified, not simply omitted when
  a raw file is unavailable.
- **Provenance hardening needed before cutover:**
  `audit_source_variant_inputs.inventory_source_variants` currently opens
  `application_path` and `raw_path` separately, without invoking
  `validate_database_pair` in that function. It audits exact Skill/Equipment
  owner and Extra semantics, so it cannot be retired wholesale. Require
  explicit source-generation verification before a mixed source may be read;
  test mismatched and missing files as failures, preserve strict occurrence
  semantics, and migrate its read path to verified normalized input.
  The optional `source_extra_owner_context` source-row lookup must share
  the same provenance boundary.
- **Retain as opt-in reproducibility evidence, not runtime input:**
  `build_determinism_manifest` explicitly invokes standalone
  `infinity-db export` and compares its paired raw artifact checksum.
  This is still evidence about the standalone export format, not a reason
  to reintroduce raw SQLite into complete runtime builds. Retire the
  raw-specific measurement when the standalone format/consumer work
  is complete; retain any distinct cross-platform runtime/JSON/archive
  determinism checks that remain useful.

**Acceptance:** `tests/test_inspect_raw_archive.py` **12 passed,
1 skipped** (pinned raw fixture unavailable). New tests compare exact
normalized and raw source rows/counts on an exported fixture, demonstrate
inspection without a persisted raw sibling and reject tampered normalized
source. `tests/test_variant_usage.py` **99 passed, 2 skipped** and
`tests/test_variant_usage_source.py` **6 passed**, including explicit
candidate CLI source selection and existing rawless publication parity.
`tests/test_deployment_scripts.py` also passed **46/46**, covering
existing deployment/packaging constraints. Ruff, Pyright, docs/link/backlog
checks and `git diff --check` passed. The full project suite and full
build acceptance were not rerun. The current cleanup does **not** delete or modify
ignored raw archives, change standalone paired export, remove legacy
source audit APIs, or change the runtime database schema. The complete
release-build acceptance was already established in the preceding slice;
it was not rerun for these source-inspection-only CLI changes.

**Next dependency:** Migrate and validate the shared
`paired_audit_connection` consumers first, then resolve
`audit_source_variant_inputs` pair provenance and source-only joins.
Defer irreversible raw-format and test retirement until independently
accepted research/audit semantics are covered by their replacements.

### Shared semantic-audit normalized-source cutover — 2026-11-12

**Implementation:** The maintained `tools.paired_audit_connection` interface
now accepts an explicit `normalized=PATH` option. It checks the complete
normalized document against the selected Army application's existing
`export_pair_sha256` generation using the shared verifier, then attaches an
in-memory SQLite database and exposes only requested missing source tables as
temporary views. It uses the same normalized column schema and SQLite value
encoding as the legacy raw export, including all schema-defined **zero-row
tables** omitted from the compact JSON document. The main application database
is opened read-only, both sources remain unchanged, and the resulting audit
connection enables `PRAGMA query_only`. If normalized source is explicitly
selected but is missing or mismatched, it fails closed even when a valid raw
sibling exists, or when no requested table is missing.

`audit_normalization_links`, `audit_peripheral_semantics` and
`audit_relationship_semantics` now pass through explicit `--normalized`
options; their public report structures, detailed evidence and established
default raw-sibling/legacy combined SQLite behavior remain compatible.
CLI errors from invalid normalized input are bounded and reported instead of
silently using a different source. Existing callers do not need any changes.

**Regression coverage:** New tests compare exact relational rows and all
three independent semantic audit reports—including detailed Peripheral and
Include evidence—between the matched raw pair and the normalized route after
the raw sibling is deleted. They test temporary-view read-only enforcement,
CLI input selection, zero-row schema fidelity, missing JSON, changed source
rows, tampered export generation, and verification even when the application
already contains every requested table. The first run exposed empty-source
table omission in the adapter (two failures); materializing schema-defined
zero-row tables fixed both. No raw file was created or modified by the new
route. The final adapter suite passed **10/10**, normalization-link suite
**3/3**, Peripheral suite **6/6**, relationship suite **7/7** and runtime
fixture suite **3/3**, all without skips. Ruff and Pyright passed.

**Remaining:** `audit_army_faction_semantics`,
`audit_source_presentation`, `report_reference_baseline` archive
verification and `audit_source_variant_inputs` still need independent
source/provenance review. In particular, the latter still lacks pair
generation validation on its raw read path. Standalone paired export,
`database-health --require-raw`, and the retained historical raw-audit
APIs remain supported. This cutover does not justify deleting
`data/generated/army.raw.db` or replacing any published runtime artifact.

### Skill/Equipment source-variant audit provenance cutover — 2026-11-12

**Cause and correction:** `tools.audit_source_variant_inputs` previously opened
the Army application and raw SQLite paths independently, without checking
the matched export generation. That could combine obsolete or unrelated
source occurrences with newer application catalog mappings. The inventory
now calls `validate_database_pair(application, raw)` **before reading any
cross-source rows**, rejecting missing or mismatched archives instead of
silently auditing a mixed generation.

**Explicit normalized source alternative:** The inventory now accepts
`normalized=PATH` instead of a raw SQLite path. It uses the existing
`paired_audit_connection` normalized-source adapter, which verifies the
**entire normalized document** against the selected Army application's
`export_pair_sha256` generation before constructing read-only in-memory
source table views. These views preserve exact direct Skill/Equipment
occurrence IDs, ordered Extras, raw field strings and zero-row table schemas;
published catalog mappings are read from the same selected application.
Raw and normalized source selection is mutually exclusive, with no implicit
fallback. The CLI exposes `--normalized` and now validates the default or
explicit `--raw` path as well.

The optional exact Extra-owner CLI lookup passes the selected application
and its verified source to the same adapter, including the original source
Unit, Army, parent and Extra relationships. The pre-existing Python helper
remains callable with **only** an explicit raw path for historical
single-source inspection; that mode makes **no claim** about matching an
application export. When an application is supplied, it enforces the pair
generation or the explicit normalized generation; no cross-source owner
lookup bypasses that verification. The selected Rules database supplies
independently curated semantic interpretations, not source identity.

**Focused acceptance:** A hermetic Army fixture compared the **complete**
Skill/Equipment inventory reports and exact Extra-owner rows between the
matched raw pair and normalized source. Both continued to work after deleting
the fixture's raw sibling. Negative tests reject changed raw metadata,
modified normalized source, ambiguous raw+normalized selection, unavailable
normalized input and a mismatched raw pair through the CLI. The revised
`tests/test_audit_source_variant_inputs.py` suite passed **45 tests**;
**61 historical pinned-raw tests skipped** because their source archive
was not available. `tests/test_scenario_api.py` passed **96**, skipped **4**
pinned-source cases. The existing normalized/paired adapter suite passed
**10/10**. Ruff, Pyright, documentation/link/backlog checks and Git whitespace
checks passed. This tools-only cutover did not rebuild the three runtime
databases or run the full project test suite.

**Remaining retirement boundaries:** Raw-dependent independent research
still includes `audit_army_faction_semantics`, `audit_source_presentation`,
`report_reference_baseline` source verification, standalone
`build_determinism_manifest` and explicit paired-export health. Preserve
those checks until their underlying source/identity invariants are covered,
rather than retaining or deleting APIs solely because historical tests use
them. Do not delete or rewrite the ignored `data/generated/army.raw.db`
without the separately approved backup/restore and private-file manifest.

### Army/faction identity and source-presentation audit cutover — 2026-11-12

**Source-invariant decisions:** Both `audit_army_faction_semantics` and
`audit_source_presentation` remain active. The first independently re-derives
Army application identities, aliases, reinforcement parents and faction
memberships from source data and compares the result with the materialized
application and runtime. The second detects occupied source fields that
are not yet represented to players; an unavailable source must **not**
pass its completeness gate. Neither purpose is superseded merely by the
standalone raw archive's retirement.

**Implementation:** Both maintained CLI/audit entrypoints accept explicit
`--normalized PATH` alongside the existing implicit matched raw sibling.
The new route reuses `normalized_source_connection` to verify the **entire**
normalized source document against the Army application's pinned export
generation, then creates read-only, in-memory source tables. Faction derivation
continues to use `identity_config_from_connection`,
`derive_application_armies` and the existing exact application/runtime
comparisons. Source presentation still uses the maintained 70-table/441-field
policy, the same SQLite occupancy semantics (including zero and false), and
the same `--require-no-occupied-gaps` rule. The `rawEvidence` report key is
retained for backward compatibility; its `path` identifies the selected
raw database or normalized JSON input.

**Acceptance:** On independent, normalized-source test fixtures,
`tests/test_audit_army_faction_semantics.py` passed **8/8**. New tests
verify complete report equality, successful repeat after removing the
raw SQLite sibling, matched source identity, rejection of modified source
rows, rejection of a mismatched raw pair, and CLI selection.
`tests/test_audit_source_presentation.py` passed **14** tests and skipped
**1** pinned-raw acceptance test (historical raw file absent/stale).
New tests verify entire report parity except the selected evidence path,
repeatability without a raw sibling, unchanged occupied-field counts,
fail-closed populated-field gate, and rejection of missing/tampered
normalized input. Ruff and Pyright passed. The selected runtime databases
were not rebuilt or modified; the complete project suite was not run.

**Remaining work:** Independent source/reference evidence and paired-export
contract consumers, including `report_reference_baseline` and
`build_determinism_manifest`, require separate review. Keep retained
legacy raw interfaces while they have independently justified use.
This migration does **not** authorize deleting ignored
`data/generated/army.raw.db`, bypassing private-file backup/restore review,
or removing source-integrity tests solely because they refer to raw SQLite.

### Reference baseline and determinism consumer disposition — 2026-11-12

**Retain independent source coverage; remove raw-file retention as a
prerequisite.** The maintained `tools.report_reference_baseline` verifies
the pinned Army source ZIP against the published Army metadata, rechecks
each source document's identities, versions, provenance, membership order,
and nested Profile/Loadout facts, then compares published reference, Extra,
Characteristic, order, Peripheral, Include and Unit-option relationships.
Its previous optional `--army-archive` route additionally required a
matching ignored raw SQLite sibling solely to read those nested source
rows. An explicit `--normalized PATH` route now instead validates the
**complete normalized source model** against the application's
`export_pair_sha256`, materializes a transient in-memory source connection
and runs the same independent parity checks. The pinned ZIP hash still must
match the Army publication; neither matching metadata alone nor a
standalone raw sibling bypasses the cross-source evidence checks.

Existing `--army-archive` usage without `--normalized` preserves its
strict validated raw-pair behavior. Supplying normalized source without a
pinned ZIP is refused. The JSON `sourceIdentityEvidence.nestedStorage`
reports whether Profiles/Loadouts were checked against
`paired-army.raw.db` or `verified-normalized.json`, and the Markdown
statement reflects that provenance. This change does not assert reference
completeness, alter the runtime database schemas or relax citation gates.

**Separate disposition: `build_determinism_manifest` — retain-active,
not a persistent raw consumer.** Its disposable staging directory invokes
the standalone `infinity-db export` command, explicitly measuring hashes
of both the application and raw database together with normalized JSON,
Rules, ITS and archive artifacts. `compare_determinism_manifests`
compares exact artifact sets across machines. The `army.raw.db` entry
measures *standalone paired-export determinism*, which is still a useful
independent format contract; it does not require the ignored raw database
in the development checkout, nor does it authorize complete builds to
reintroduce raw creation. Retire or version this manifest field at the
later **standalone format** cutoff, and retain its distinct normalized,
runtime/Rules/ITS, source ZIP and symbol/citation reproducibility checks.
Changing manifest keys/format prematurely would break comparison of
existing v1 manifests without removing any persistent raw-file dependency.

**Tests:** A hermetic miniature Army ZIP is merged, normalized and exported
to a matched application/raw pair in the test's temporary directory.
The archive verifier's source and nested evidence is compared byte-for-byte
between the verified in-memory normalized route and the paired raw path,
apart from the explicitly reported `nestedStorage` provenance. Removing
the fixture's raw sibling does not change the normalized result; mutated
normalized data is rejected before any source lookup. The end-to-end
baseline/CLI test still runs the same archive and published occurrence checks
against the fixture without raw SQLite (its unrelated released Rules Weapon
citation check is mocked because the tiny synthetic Army intentionally
does not match the current released Rules generation). Existing
`test_report_reference_baseline.py` coverage remains in place for the
release database, source/citation checks and legacy raw route.

**Validation:** `tests/test_report_reference_baseline.py` passed
**69 tests, 2 skipped** (historical pinned raw/source-dependent cases).
New hermetic fixtures run the actual Army ZIP merger/normalizer/exporter,
compare nested raw versus verified normalized audit evidence, and run the
baseline CLI after deleting the temporary raw sibling. Negative tests
reject modified normalized source even if a valid raw sibling exists, and
refuse `--normalized` without `--army-archive`. The release Rules/Weapon
citation check is mocked **only** in the tiny fixture's integration test
because its Army identity is intentionally different from the tracked
release; independent actual-release citation tests remain in the module.
`tests/test_deployment_scripts.py` passed **46/46**. Ruff, Pyright,
Markdownlint, document links/backlog validation and Git whitespace checks
passed. Neither the full project suite nor the standalone determinism
manifest generation was run for this tools-only slice.

**Remaining:** Explicit `database-health --require-raw`, standalone paired
export, dedicated raw-only inspection research and historical paired-archive
tests remain opt-in until their original purpose is retired or superseded.
No ignored archive was moved, deleted or rewritten, and no selected runtime
database was rebuilt. L0 inventory ownership and the independent
backup/trial-restore decision for private bytes remain open.

### Standalone export and health opt-in rawless cutover — 2026-11-12

**Current independent contract:** `infinity-db export NORMALIZED.json ARMY.db`
previously generated both standalone application and lossless raw SQLite
databases, allowing exact, source-only audit queries. The importer has
already supported `include_raw=False` with full untrusted-input and
source-to-canonical staging validation, deterministic publication,
`export_pair_sha256` provenance, and an explicit refusal to overwrite
an application whose raw sibling still exists. It produces **byte-identical**
application output with and without the raw sibling for matched inputs.
Complete three-database builds already use this application-only mode.

**CLI exposure, no breaking default change:** `infinity-db export --no-raw`
now publishes the application database only to a destination **without a raw
sibling**, without creating or removing any raw SQLite file. Standalone export
**without** this flag continues to publish a validated, paired raw archive;
standalone consumers and `build_determinism_manifest` remain compatible.
An existing raw sibling blocks `--no-raw` before publication, preserving
both files and preventing a stale private file from being silently associated
with a newly written application database.

`infinity-db database-health ARMY.db --normalized NORMALIZED.json` is an
explicit, mutually exclusive alternative to `--require-raw`. It calls the
shared full-document `verified_normalized_generation` verifier and reports
source status, input bytes/path, validation time and exact generation
SHA-256 under the opt-in `normalizedSource` JSON key. A missing, altered
or export-mismatched source makes health **unhealthy**, without falling back
to an available raw sibling. The original default and `--require-raw`
machine-readable report structures remain unchanged. Neither source
option is accepted for `--db-dir`, whose only concern is the selected
published runtime set; the normal runtime health path is unaffected.

**Scope/acceptance:** New CLI regression tests compare a paired export
with application-only output byte-for-byte, exercise source verification
in JSON and text modes without a raw sibling, and reject existing raw
destinations, source edits, absent source, conflicting source selectors and
`--db-dir` misuse. Existing tests still require pair validation under
`--require-raw`; all three production databases and ignored user data
remain untouched. Focused validation passed: `tests/test_app_cli.py`
**25/25**, `tests/test_database_set.py` **23/23**,
`tests/test_army_reference_storage.py` **26/26**,
`tests/test_deployment_scripts.py` **46/46**, and the three
application-only importer byte-parity/no-clobber cases **3/3**.
Ruff, Pyright, Markdownlint, document links/backlog validation and
`git diff --check` passed. The complete project test suite and complete
runtime rebuild were not run. The opt-in interfaces establish a usable
migration route, **not** approval to remove raw-format tests,
change the paired export default, or delete any private archive.

### Standalone rawless-default and determinism-manifest v2 cutover — 2026-11-12

**Decision and implementation:** The user-approved standalone format cutoff
makes `infinity-db export NORMALIZED.json ARMY.db` application-only by
default, matching the already-rawless complete database-set builder.
`--with-raw` is now the explicit legacy paired-export option. The former
`--no-raw` flag remains accepted as a deprecated no-op compatibility alias
and is mutually exclusive with `--with-raw`; the programmatic
`export_database(...)` default remains paired **for existing direct API
consumers/tests**, pending a separately reviewed library API cutoff.
Regardless of CLI mode, full untrusted-input, source-to-canonical staging,
published SQLite integrity, deterministic finalization and export-generation
verification stay in force. Default rawless export refuses an existing
`army.raw.db` sibling; it does not remove or rewrite private evidence.
Opt-in `database-health --require-raw` still validates paired output,
and `database-health --normalized` verifies source identity without it.

**Cross-platform determinism format change:** The default
`tools.build_determinism_manifest` output is now **format v2** and
hashes application-only `army.db`; the artifact set retains every other v1
entry (normalized JSON/validation, merged source, Rules, ITS, snapshot/work
ZIP, symbol publication and reviewed Weapon citations). A deliberately
explicit `--legacy-paired` mode recreates **v1** with the additional
disposable raw SQLite checksum. This preserves historical audit
reproducibility without making raw output the active default.
`compare_determinism_manifests` accepts both historical v1 and current v2
manifests, compares every artifact in a same-version pair, and rejects
mixed versions with a clear regeneration instruction. It never implicitly
drops `build/army.raw.db` to paper over a version mismatch. The
`tools/run_checks` build-stage smoke now exercises the default rawless
export, and the installed-wheel smoke verifies the result using the
matched `--normalized` source instead of demanding an absent raw archive.

**Actual generator acceptance on Windows:** Both manifest modes completed
successfully from the tracked portable Army fixture, each including all
**73** normalization checks. The default v2 output had **no**
`build/army.raw.db` entry; explicit v1 emitted
`02fdb8f3621bd27f2e3eb4c31cec7b9ddd21c2b3ce7b891431b5a57e87b3d8a3`
for its transient raw archive. All ten shared artifact hashes matched
exactly across the independent v1/v2 jobs. In particular,
`build/army.db=7d2e1caa365b6d454e185a3006ae427391c8b7cd13e3383a71a8171a1643c910`,
`build/rules_n5.db=28c85673b51c0c4774d3fadd0ba79005c8d1092d7c786897849d4348fac2fa6a`,
and `build/its_18.db=e88eb6e9934443f762d8f143efcfd8cdf300636424b3a55c78df569ea43d2b94`.
The generated manifests were written only under ignored `local/reports/`.
This proves same-machine v1/v2 shared-artifact parity, **not** a
cross-platform equivalence claim; Linux/CI must generate v2 independently
before a cross-platform result can be declared.

**Focused regression acceptance:** CLI **25/25**, manifest
generator/comparator **10/10**, installed-wheel/deployment scripts
**46/46**, and test/check runner **111 passed, 1 skipped**. Ruff,
Pyright (0 errors), Markdownlint, documentation links, backlog validation
and `git diff --check` passed. The maintained `build` check also passed
against the 58-source Army snapshot: lossless merge verification,
**73** normalized checks, Mercenary mapping **49/49**, the reviewed
116-warning source anomaly set, and default application-only SQLite
export in an isolated temporary directory. The full project test suite,
complete three-database release build and Linux-side manifest comparison
were not run in this slice.

**Safety boundary:** The old ignored, mismatched
`data/generated/army.raw.db` has not been moved or deleted, and the
tracked three-database runtime release set remains unmodified. The
retirement of standalone paired-export, `--require-raw`, historical
raw-only research APIs, and direct Python importer defaults remains a
distinct decision requiring relevant consumer closeout. Existing
legacy-archive source tests are not removed solely because they exercise
a deprecated format.

### Direct Python exporter default and Linux validation gate — 2026-11-12

**Library-level disposition:** Production code has only one direct caller
of `database.importer.export_database`, the CLI, which already passes
`include_raw` explicitly. Historical tests that exercised raw-only
source-row evidence, pair metadata parity, interruption recovery or
foreign-key/source integrity had relied on the old implicit
`include_raw=True` default. The direct Python API now defaults to
**`include_raw=False`**, matching the complete builder, standalone CLI and
determinism manifest v2. Retained paired-export tests and other fixture
consumers explicitly request `include_raw=True`; no checks were removed
merely to enable the change. The legacy raw path still verifies both
SQLite files, preserves lossless row JSON and absent-versus-null fields,
and retains the raw-first/application-last recovery contract.

**Source integrity:** The application-only path still validates every
untrusted normalized table against the complete relational staging
database, writes the same deterministic application SQLite bytes and
export-generation fingerprint as paired mode, and refuses any destination
with an existing raw sibling. Normal Army builds must no longer materialize
`army.raw.db`; tests of the normal `_build_army` metadata path now
inspect `normalized.json` directly, while an explicit paired-export
test retains independent raw metadata checks. The normal
`database-health --normalized` route remains the operator's generation
integrity check.

**Linux cross-platform gate currently blocked, not failed:** On the Linux
worker (`linux-dev`) the checkout is at `ac8050c0` while the Windows
rawless-default commit is `1eb3ae12`. A read-only checkout dry-run
reported `git_ref_unavailable` for the Windows SHA. The pinned-revision
script launch was refused (`worker_request_invalid`), and an unpinned
manifest build at `ac8050c0` completed successfully but produced **v1**
with a raw database hash, despite its output filename ending in
`v2-linux.json`. It is **not a valid v2 comparison**. The Windows
branch was not pushed, the Linux Git checkout was not changed, and no
cross-platform hash parity is claimed. After an explicitly authorized
branch push and Linux fetch/checkout, rerun the v2 generator on the exact
same commit and compare the actual manifests.

**Focused Windows validation:** Full `tests/test_database.py`
**175/175**, database-set builder **18/18** (including repeatability,
failure-before-publication and generation mismatch), CLI **25/25**,
source/pair audit adapter **10/10**, source inspector **12 passed,
1 skipped** (unavailable pinned raw archive), database separation
**12/12**, metadata **17/17**, identity metadata **8/8**,
Army/faction **8/8**, presentation **14 passed, 1 skipped**,
runtime-surface **3/3**, source-variant **45 passed, 61 skipped**
(unavailable historical pinned raw fixtures), and reference baseline
**69 passed, 2 skipped**. Ruff, Pyright (0 errors), Markdownlint,
documentation links/backlog validation and `git diff --check`
passed. Legacy tests explicitly request paired output where they
verify lossless source rows or pair publication/recovery. This slice
did not rerun the full project suite or a pinned complete
three-database release build on the new exact commit.

**Legacy API decision:** Retain `create_raw_archive`,
`validate_database_pair`, `raw_database_path`,
`database-health --require-raw`, standalone `--with-raw`, v1 manifest
generation and legacy raw audit/publisher entrypoints as **explicit
compatibility/research interfaces** for now. They do not justify the
continued retention of an ignored generated archive or raw SQLite in
runtime builds. An eventual removal requires a separate API deprecation
decision and independent audit/format acceptance; do not delete their
tests solely because they cover legacy paths.

### Cross-platform determinism v2 investigation — 2026-11-12

**Exact Git identity and synchronization:** Windows Git HEAD and the detached
`linux-dev` worker checkout were both verified at `288aa821`, and later
at `c37344d0` and `73da5e48d7a19786bde19837c96ee0f3b5aaaa17`.
The work branch was explicitly pushed, and Linux explicitly fetched and
checked out the exact revisions before running the paired manifest jobs.
Both runs completed successfully using `tools.build_determinism_manifest`.
The maintained comparator, now supporting two explicit manifest filenames
as well as its historical directory-discovery interface, **failed** on the
five byte-different artifacts; it did not ignore or coerce any SHA mismatch.

**Confirmed source-fixture normalization defect:** Some tracked JSON
deployment fixtures retained pre-attribute CRLF bytes in the Windows
checkout, despite the repository's LF checkout policy. A fixture file was
802 bytes on Windows but 755 on Linux. The v2 generator now copies its
small, tracked fixture into the temporary build root while canonicalizing
JSON line endings to LF, without rewriting the checkout or normalizing
real downloaded Army source archives. A hermetic regression covers both
newline forms. This fixed the `master.json` and `normalized.json`
differences and preserved identical normalized-validation bytes.

**Strict v2 result at `73da5e48`:** **Five of ten artifact SHA-256s
match**: merged master JSON, normalized JSON, normalized validation JSON,
symbol-publication JSON and the reviewed Weapon citation publication.
The remaining five physical artifacts differ: `army.db`,
`rules_n5.db`, `its_18.db`, `snapshot.zip` and `work.zip`.
The exact ITS JSON source file was independently transferred and SHA-256
verified to have identical bytes on both machines.

**Non-approving diagnostic evidence:** An opt-in
`--diagnostics-output` sidecar reports SQLite writer headers, a
writer-version-neutralized physical SHA, every relational table digest
and every ZIP member's uncompressed SHA/CRC/size and compressed size.
All **108 SQLite user tables** have matching canonical row-content
digests (84 Army, 14 Rules, 10 ITS). All three DBs have identical page
counts, but their physical SHA values differ. ITS differs **only in the
SQLite writer-version header** (neutralizing bytes 96–99 makes its
whole-file hash identical); Army and Rules retain additional
non-row-content/layout differences after neutralizing that field.
All **1,608 uncompressed ZIP member payloads** match (3 snapshot, 1,605
work). The compressed sizes differ for **3/3** snapshot members and
**1,555/1,605** work members; compressed ZIP SHA differs in both archives.
Therefore, the current strict byte-determinism gate is still **red**,
even though the tested logical content and archive payloads match.

**Toolchain explanation and next requirement:** The Windows host used
Python **3.14.10**, SQLite **3.50.4** and **zlib-ng 1.3.1**; the Linux
worker used Python **3.14.4**, SQLite **3.46.1** and standard **zlib 1.3.1**.
The SQLite header difference is directly confirmed, while the additional
SQLite page-layout and ZIP compression drift is consistent with these
different implementations. Do **not** weaken the exact-byte comparator,
rewrite SQLite writer metadata to disguise an actual version difference,
or switch archive compression merely to force a green check. Prefer
a pinned, reproducible build toolchain/container shared by both platforms;
then regenerate and compare the v2 manifest at an identical Git SHA.
The optional diagnostics are kept separate from the versioned v2 artifact
inventory, and all generated evidence stays under ignored `local/reports/`.
No tracked runtime DB or private `army.raw.db` was modified or deleted.

**Focused validation:** The determinism/compare test suite passed **15/15**
after adding explicit-manifest arguments; Ruff and Pyright passed for the
diagnostic implementation. Additional documentation checks and the exact
resulting commit are recorded in the Git history. A full project suite or
new pinned complete runtime build was not run for these diagnostics.

### Digest-pinned Windows/Linux determinism runtime — 2026-11-12

**Final result: PASS at exact Git revision
`a164c4b84ba4ca8a0b71b064026bfce9a9052b39`.** The same
`linux/amd64` OCI Python image was pulled, digest-verified and executed
on the Windows Docker Desktop engine and the separate `linux-dev`
Docker engine. The immutable image reference is
`python:3.11.18-bookworm@sha256:726d304906fa5eb468e5531e366548d1903286352f5adb54ef508ac01fbd80c6`.
Both hosts confirmed the same resolved image digest and identity,
Python **3.11.18**, SQLite **3.40.1**, standard zlib **1.2.13** and
Git **2.39.5**. Both Git checkouts were on the same commit.

**Implementation:** `tools.run_pinned_determinism` adds a maintained,
development-only Docker runner. `--probe` pulls and verifies the
selected OCI image and prints its runtime versions. `--output
local/reports/NAME.json` executes the existing strict v2 manifest
generator inside that runtime. The repository checkout is mounted
read-only, output is constrained to an existing or newly created
`local/` directory, container networking is disabled, and temporary
build files stay in disposable container storage. Linux jobs run under
the worker UID/GID; Windows uses a nonroot container user. This does
not alter the deployment Dockerfile, published runtime databases,
downloaded source archives, local research assets or ignored raw archive.
It does not remove the legacy paired export contract.

**Acceptance:** Windows and Linux each completed the 73-check fixture
normalization and generated all ten v2 artifact hashes. The Linux
manifest was transferred back with transport SHA-256 verification.
The maintained strict `tools.compare_determinism_manifests` comparator
returned **exit 0**: `Cross-platform deterministic outputs verified
across 2 manifests.` All **10/10** physical SHA-256 values match,
including both compressed archives and Army/Rules/ITS SQLite. This is
byte-identical output, not merely relational/content parity. Runner
contract tests: **4 passed**, Ruff and Pyright **PASS**. The evidence
lives only in ignored `local/reports/`. Full project tests and a
complete release database-set rebuild were not run for this slice.

**Compatibility and remaining boundary:** Native Windows/Linux toolchains
still generate different physical SQLite and compressed ZIP bytes. The
pinned runtime is the opt-in, strict reproducibility mechanism; regular
host-native builds and platform-specific acceptance tests remain useful
and are not made byte-identical by this change. GitHub Actions currently
runs a host-native Windows/macOS/Linux deterministic-output matrix using
Python 3.11.9; the hosted CI design is **not** migrated here. Follow up
with a dedicated CI gate design that preserves native Windows/macOS build
coverage, uses a genuinely identical toolchain for the strict byte
comparison, and does not assume Linux Docker is present on hosted
Windows/macOS runners. The raw archive deletion approval remains
separate.

### Hosted CI determinism separation — 2026-11-12

**Decision and implemented workflow:** Keep the existing
`.github/workflows/source-checks.yml` native build/test matrix on
Ubuntu, Windows and macOS unchanged (plus the separate Ubuntu Python 3.14
build leg). Do **not** compare their independently generated ZIP/SQLite
bytes: different SQLite/zlib implementations caused proven physical drift
despite equivalent source data. The three host platforms still validate
their selected runtime sets, curated source publication and portable
build/rules stages.

The new `determinism-container` matrix uses two **independent x64
GitHub-hosted Ubuntu environments**, `ubuntu-24.04` and `ubuntu-26.04`.
Both check out the same exact PR candidate SHA with full Git history,
use the host's preinstalled `python3` **only to invoke the existing**
`tools.run_pinned_determinism` runner, probe/pull the same immutable
OCI image, and generate the unmodified v2 manifest from the read-only
checkout with container networking disabled. Each uploads its manifest
as `determinism-container-${{ matrix.os }}`. This avoids assuming
Linux Docker support on hosted Windows/macOS, avoids installing
unneeded host Python dependencies, and tests identical binaries
across two independently provisioned Linux hosts.

**Strict acceptance and job compatibility:** Keep the existing required
`deterministic-outputs` job ID and visible name. It now depends on
`fast-validation`, all `source-checks` native legs, and both
`determinism-container` legs. On a full validation, the download
pattern selects **only** the two pinned-container manifests and runs
the original fail-closed `tools.compare_determinism_manifests`.
Any missing artifact, missing version, unexpected artifact name,
or byte/hash difference still fails; no semantic equivalence fallback.
The existing `fast-validation.outputs.full` reuse policy still avoids
extra container builds on an eligible previously validated baseline.

**Evidence / boundary:** Local structural tests were extended to assert
the exact native matrix, container host releases, identical checkout
selection, pinned runner/probe, independent artifact publication and
unchanged strict comparison. The Windows/Linux developer-worker
manifest v2 check previously passed 10/10 at commit `40a7df27`.
Hosted GitHub Actions must still run against the new workflow revision;
local regression tests and developer-worker parity do **not** constitute
hosted acceptance. Do not mark the hosted acceptance item complete
until both workflow artifacts and the strict comparator are green.
A full project test suite or production database rebuild was not
triggered for this workflow-only change. No local/private source assets
or released databases were modified.

### L0 — Full read-only inventory and ownership mapping

1. Capture branch/SHA and status. Enumerate **all** tracked tools (including
   templates) and ignored/locally generated paths across Windows and Linux.
   Capture path, byte size, kind, tracked/ignored status, Git rule, timestamps
   where trustworthy, and SHA-256 for candidate migrations; do not include
   private content or credentials in published reports.
2. For each tool, plan, audit and report, record purpose, inputs/outputs,
   owner, calls/imports and links from source/tests/tools/CI/scripts/docs/
   agent skills, optional local-only consumers, publication side effects,
   open findings, lifetime and retention trigger. Apply the explicit
   dispositions in the [lifecycle audit](#lifecycledisposition-audit-existing-policy-l0l1-implementation).
   A historical test alone is not a reason to retain its obsolete implementation.
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

1. Review the [canonical disposition policy](README.md#disposition-and-naming-of-completed-files),
   categories above, scoped exceptions, naming examples, lifecycle/retention
   rules and who may prune each class. Approve the plan/report/audit dispositions
   separately from executable-tool retirement and private-data deletion.
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
3. The [independent correctness slice](#release-tool-lifecycle-and-correctness-checkpoint--2026-11-12)
   corrected `verify_release_candidate_browser` to validate the **complete
   Army/Rules/ITS three-database identity**. Preserve that gate when relocating
   the tool; its implementation does not complete the broader L4 reorganization.
4. Preserve the explicit pinned artwork-review selections from the
   [P5 review checkpoint](#p5-artwork-review-workflow-and-runbook-checkpoint--2026-11-12)
   when moving that tool, and review other dated defaults before their cutover.

**Exit:** The root tool directory contains only reviewed public command
exceptions and package structure; all moved tool modules have live consumers
and passing focused tests.

### L5 — Retire completed investigations and consolidate reusable checks

1. The [P5 comparison retirement](#completed-p5-comparison-tool-retirement--2026-11-12)
   completed the first bounded historical-tool removal, including its test and
   stale command. The [P5 review checkpoint](#p5-artwork-review-workflow-and-runbook-checkpoint--2026-11-12)
   retired the superseded runbook after extracting current guidance and evidence.
   Preserve the accepted symbol-cutover evidence and maintained handoff/
   publication checks during subsequent cleanup.
2. Then review other bounded deployed-object, Weapon-chart, historical 1.0,
   symbol provenance and one-use research clusters. Preserve open
   source questions, stable finding IDs and immutable source hashes in
   canonical research records. Extract current reusable parsers/validators
   before retiring a wrapper.
3. Consolidate overlapping audit, browser and benchmark infrastructure
   only if duplication is demonstrated. Do not retire current release
   gates, reproducible source investigations or useful optional
   diagnostics solely because they are not called in ordinary CI.
4. Reconcile completed plans, reports and audits against their original
   purpose and open findings. Remove superseded narratives, keep only
   genuinely unique frozen evidence, and rename retained historical
   material only when that improves its scope/status clarity. Update
   indexes, citations, documentation links and any associated generators
   in the same change.

**Exit:** Every deletion or rename has an explicit fulfilled purpose, an
audited consumer/link graph and preserved current behavior/evidence.
Superseded tracked code and narrative remain recoverable through Git
history; exceptional retained evidence has a documented owner and
retirement/review trigger.

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

- **First safety issue resolved:** the release-browser verifier now checks
  the complete three-database set; preserve that correction during tool relayout.
- **First low-risk tool removal completed:** historical P5 path/process
  comparison pair, with its dedicated test/command reconciled and evidence preserved.
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
