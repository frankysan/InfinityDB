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
