# Tools and local-path cleanup plan

**Project domains:** Project infrastructure, Data processing, Acquisition, Deployment

**Status:** Active implementation on `dev/tooling-workspace-cleanup`.
Prospective P1–P5 conventions accepted 2026-11-13.

**Current cleanup decision (2026-11-13):** R5 Syncthing/receiver
investigation is complete. Earlier requirements for further live-service
checks, exhaustive ACL inspection, independent backup/trial restore, and
formal rollback tooling are **retired as prerequisites** for L2/R6 path
reorganization. Later checkpoints retain the historical findings but do
not reopen those gates. Continue moving selected source families and their
consumers together; check important copied inputs and retain unique
originals until the replacement is verified. Public tracked artifacts,
private-source publication, and deployment changes remain separately scoped.

**L4 implementation:** The first maintained-tool batch groups five
Chromium/host-resource and runtime benchmark utilities under
`tools/performance/`, updating their test imports and documented invocations.
Existing benchmark output paths remain unchanged. The next L4 batch moves the
test-worker runner, Linux browser-host profile and Docker host probe to the
same package. Entrypoints use `python -m tools.performance.*` while retaining
existing test runner behavior and the host-local profile path.

The next dependency-coherent L4 batch groups the operational alert, diagnostic,
resource and metrics-report tools under `tools/operations/`, and HTTP load
testing under `tools/performance/`. It updates active tests and documented
module commands without changing report formats or output destinations.

**R6 Windows source-copy checkpoint (2026-11-14):** 96 ignored files were
copied without replacing or deleting originals: six Army ZIPs, five Army
provenance JSONs, five Wiki/Human-Sphere ZIPs, five matching provenance JSONs,
and 75 PDFs. `tools.data.copy_legacy_sources` selects these families explicitly,
checks source/destination SHA-256, refuses differing destinations and supports
idempotent repeat copies. One older Army ZIP has no matching manifest and is
not a source-pinned build candidate. The selected newest Army pair passed
`tools.export_symbol_source_plan` from `local/data/` (1,101 authoritative URLs);
the N5 v5.2/v5.3 PDF comparison passed using `--source-layout local`.
The copies establish an alternate source home, **not** a default reader,
producer, Syncthing sender, Linux receiver, tracked source-label or deployment
cutover. Preserve all legacy originals until those consumers are updated.

**R6 symbol-source copy extension (2026-11-14):** All 14 historical raw-symbol
ZIPs and 14 matching v1/v3 provenance manifests were copied from
`data/raw/symbols/` and `data/manifests/snapshots/` to their explicit
`local/data/` destinations. The extended helper verifies archive basenames,
family type and archive/destination SHA-256; a second dry run found zero
missing destinations or conflicts. This brings the Windows source-copy count
to **124 files**. No live raw-symbol handoff, override application, publication,
Syncthing activation, or producer/default-path change was performed.

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
- **Preserve private originals during moves.** Keep unique ignored
  originals until the destination copy has been checked; do not bulk-delete
  source evidence or include private assets in tracked publication.
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

## L1 decision package — P accepted, T and M pending (2026-11-13)

**Decision status:** The user accepted the **P prospective conventions**
on 2026-11-13, limited to publishing policy and implementing new
non-destructive output contracts. This is not an L0 exit or approval
of tracked retirements, existing paths, producer changes or private-data
migration. All **120 current root Python modules** and the
artwork-review template have named L0 dispositions; this is filename
and code-ownership coverage, **not complete L0 exit**. A tracked-doc
lifecycle pass and Army/Wiki/Symbol producer interface checks are
recorded below. The previous exact InfinityDB revision
`eb272cd2eb3347211a14b04e9b72d3b002af10dd` passed all three
hosted workflows; CI on the newer review revision must be evaluated
separately. The private 44-file move candidate, inaccessible reports
and Syncthing/backup status remain **unapproved and unverified**.

### P — Prospective project conventions (one non-destructive policy decision)

**Accepted by the user on 2026-11-13 as one prospective policy only.**
There is no immediate authorization to change existing file paths, CLI
defaults, ignore rules, databases, service volumes, producer repositories
or private bytes:

- **P1 — Ignored output home:** New, project-owned, ignored
  sources and run artifacts should be created beneath `local/`.
  The intended categories are `local/data/`, `local/research/`,
  `local/validation/`, `local/performance/`,
  `local/operations/`, `local/work/` and `local/handoffs/`.
  Preserve exact immutable upstream basenames and source identities.
  Do not create empty category trees or a catch-all `misc/`.
- **P2 — Name and lifecycle:** Paths identify domain, purpose, source
  revision or candidate, and lifetime. For repeatable reports,
  prefer `<UTC-run-id>-<short-commit-or-source-sha>/`, followed by a
  concise role-based filename. Accepted inputs/receipts include
  source/artifact SHA-256. New run-evidence writers must reject
  collisions instead of truncating a previous run; a documented
  *explicit publication* workflow is separately allowed to replace
  its reviewed tracked output. No automatic age-based deletion:
  scratch is prunable after successful verified completion; open
  diagnostics last until closeout; source/recovery/release evidence
  lasts until its independent provenance, consumer and retention
  obligations are discharged.
- **P3 — New maintained tools:** Use `tools/data/`,
  `research/`, `symbols/`, `browser/`, `testing/`,
  `ci/`, `operations/`, `performance/`, `dev/` or
  `_shared/` by responsibility and consumer. The initial minimal
  root exceptions are `tools/run_checks.py` and package
  `__init__.py`. This does **not** move or rename an existing
  module; L4 uses separately validated atomic import, test, CI,
  MCP and direct-command cutovers.
- **P4 — Narrow documented exceptions:** Keep conventional
  `.venv/`, `node_modules/`, `__pycache__/`, `.pytest_cache/`,
  `.ruff_cache/`, package/build caches, OS/editor state,
  host-specific secrets, and selected pytest scratch locations
  with their owners. GitHub's step-output file, external producer
  staging and the production `metrics_history` Docker volume
  are **not** project-generated `local/` reports. No blanket
  exception is granted for checkout-root `reports/`,
  `docs/audits/`, ignored `data/`, `image_overrides/`, or
  loose downloaded web-font inputs; assess those separately.
- **P5 — Tracked publication boundaries:** Preserve
  `data/generated/army.db`, `rules_n5.db`, `its_18.db`,
  curated source inputs, `symbol-publication.json`, generated
  *reviewed* checklist/catalog-scope documents, and any immutable
  tracked source/acceptance records. Do not classify these as
  disposable ignored evidence or move the production SQLite
  volume into the checkout. Installed wheels, production images,
  normal serve and deterministic build must remain independent of
  `local/` contents.

**Effect of accepted P:** The prospective policy is published in the
canonical [architecture](architecture.md#accepted-workspace-conventions-prospective-not-a-path-migration)
and [data lifecycle](../data/README.md#accepted-ignored-artifact-policy-prospective)
owners, with short navigation pointers. It authorizes narrowly
scoped **new**, non-destructive output-contract implementation.
**P is not permission to execute existing-data L2/L3 migrations,
relocate existing tools, retire tracked code, mutate ignored
originals, alter Syncthing, or delete anything.** Legacy
writer/reader paths must continue to work until an individually
reviewed compatibility cutover.

### T — Tracked-code/document retirement (separate per-batch decisions)

- **T1 — Candidate:** Retire
  `tools/symbol_raster_validation.py` and the two
  historical-only tests in `tests/test_symbol_raster_validation.py`.
  `InfinityDB-symbol-tools` owns the identical visual-comparison
  implementation inside canonical compression; the InfinityDB
  duplicate has no other tracked tool imports. **Not yet approved:**
  finish the independent caller/packaging scan and obtain current
  producer regression acceptance (the MCP attempt returned
  `validation_unknown`). Keep receipt/ZIP verification and
  source-to-publication acceptance intact; do not claim producer
  raster evidence is a separate consumer visual parity check.
- **T2 — Candidate:** Retire the completed
  `docs/v1.0-coverage-workflow-plan.md` only after confirming
  its pilot selection, constraints, benchmark findings and
  independent acceptance evidence remain in
  `config/validation/`, `v1.0-source-coverage-audit.md`
  and the active backlog. Clear any remaining references atomically;
  retain unique source-pinned findings instead of making another
  archival document.
- **T3 — Not ready:** `probe_docker_test_host.py`, historical
  V1S wrappers and broad `tools/` moves need a demonstrated
  replacement or an explicit consumer/CI cutover first. Merely
  finding only a historical test is not a retention argument.

**Effect of approving a specific T batch:** Permit only that named
tracked-code/document removal *after* its stated preconditions, with
relevant focused/full validation and an independently reviewed Git
diff. It grants no right to delete private source, reports or
backups. Git history is the default archive.

### M — Existing private-source relocation or deletion (blocked)

**No approval requested yet.** The 44-file refined source/provenance
move list is a *candidate*, not a migration manifest approved for
execution. Each family must first have exact old/new paths,
producers/readers, hashes, source-selection ambiguity checks,
independent backup **and successful trial restore**, synchronized
sender/receiver snapshot and reversible cutover evidence.

The **19 inaccessible Windows `reports/` directories** have unknown
contents. They require authorized, read-only enumeration and
retention classification. Do not elevate access, change ACLs,
move or delete them by inference. The Windows send-only Syncthing
state also needs a fresh verification; replica agreement is not an
independent backup. Linux `image-overrides/` receiver naming,
MCP source paths and the production `metrics_history` volume
remain separately protected.

A later **M-copy** decision may authorize one specifically identified
reversible family after L2 has updated writers/readers; a subsequent
**M-delete** decision would require independent restore,
post-copy hash/source verification, confirmed consumers switched,
retention sign-off and rollback documentation. Do not bundle these
approvals, assume that a successful CI run proves recovery, or
promote `army.raw.db` retirement without its own consumer check.

### Implementation and approval handoff

1. **P accepted 2026-11-13.** Publish its policy in canonical owners
   (completed in this documentation batch), then begin bounded L2
   non-destructive output-contract changes (collision refusal, report
   classification and producer options). Keep existing defaults and
   legacy readers until an independently validated cutover, using
   focused tests and no implicit local-data discovery.
2. **Review T1/T2 individually** after their listed checks; process
   any accepted tracked retirement as a separate tested commit.
   The producer and MCP execution contracts remain independent of
   InfinityDB's repo layout.
3. **Keep M closed** until backup/restore, report ACL classification,
   producer/Syncthing state and hash-preserving source selection are
   demonstrably ready. Only then propose exact family-by-family
   migration and later deletion requests.

**Current recommendation:** Implement new non-destructive output
contracts under the accepted P conventions; continue T acceptance
preparation and L0 recovery investigation independently. Only the
prospective P decision is approved; continued cleanup work is not
approval of T, M, or a legacy-path cutover.

The [detailed L0 disposition and cross-repository evidence](#execution-phases)
remains the audit trail. The [L1 prerequisites](#l1-approval-prerequisites--consolidated-outstanding-decision-register)
remain binding for any physical migration.

### First bounded L2 output-contract update — 2026-11-13

**Baseline:** Clean `dev/tooling-workspace-cleanup` at
`2eb4c0fe1fffcbf5b9a762f6143a14dcf203795e`, after the
prospective P conventions were documented, checked and pushed.
The existing pinned-determinism Docker runner already required an
explicit output beneath `local/`. Its previous preflight nevertheless
allowed an existing manifest to be overwritten on repeated runs.

`tools.run_pinned_determinism` now rejects existing selected manifest
paths and output symlinks **before launching Docker**, preserving the
prior report bytes. The direct `--output` interface, existing
`local/reports/` destinations, source-checks workflow and artifact
consumer remain unchanged. Manual repeated evidence should use a
fresh categorized `local/validation/determinism/<run-id>-<SHA>/`
directory. This first change was a bounded preflight protection,
**not** an atomic concurrent-writer lock; the later
[fifth L2 output update](#fifth-bounded-l2-output-contract-update--generic-determinism-manifest-2026-11-13)
adds exclusive-create behavior to the generic generator without
migrating existing evidence.

**Validation:** Windows focused `test_run_pinned_determinism.py`
passed **6/6**, including duplicate-output refusal before Docker and
the portable symlink-rejection branch. Targeted Ruff, documentation
lint/link/backlog checks and `git diff --check` passed. No real
Docker run, Linux check, hosted CI, source migration or private-data
modification was performed. The broader L2 writer/collision inventory,
producer destination options and T/M gates remain open.

### Second bounded L2 output-contract update — release CI records (2026-11-13)

**Baseline:** Clean `dev/tooling-workspace-cleanup` at
`fde55596096a17b717410bbfc21fdc75f27dba27`, following the
pinned-determinism output guard. The active `prepare_release_ci_evidence`
CLI already required explicit JSON and annotated-tag filenames, but wrote
both using unconditional truncation, so a repeated command could replace
accepted exact-SHA release evidence.

The collector now preflights the two user-selected output paths **before
network collection** and again after hosted evidence/metadata validation,
rejecting existing files, symlinks and duplicate normalized destinations.
Both files use exclusive creation so a race after the preflight cannot
truncate an existing release record. All original CLI arguments, exact-SHA
source/workflow checks and historical `reports/` path support remain.
The current [release checklist](releasing.md) now recommends a fresh,
revision-pinned `local/validation/project-infrastructure/release-ci/`
folder and uses that same tag-message filename for the eventual
operator-authorized tag. The paired outputs are **not an atomic
two-file transaction**: an interruption or write failure may leave newly
created partial evidence to inspect; no old record is removed.

**Validation:** The Windows release-evidence test module passed **29/29**
including both single-file collisions, duplicate selections, a file
appearing after collection, output symlinks and exclusive-create behavior.
The release-scope **4/4** and release-metadata **3/3** test modules also
passed. Targeted Ruff, repository Pyright (zero errors/warnings),
documentation lint/links/backlog and `git diff --check` passed.
No GitHub requests, release tag, source mutation or deployment were
performed. A broader batch must still check the report-generation
inventory and CI/release acceptance at a separately selected exact SHA.
This change does not approve any tracked retirement (T) or private-data
migration (M).

### Third bounded L2 output-contract update — cross-browser evidence (2026-11-13)

**Baseline:** Clean `dev/tooling-workspace-cleanup` at
`9e5301638f30ec8537dcf1661e7d2a5b10e26918`, after the
release-evidence collision guard. The active opt-in cross-browser runner
and its browser failure handler previously reused
`local/cross-browser-compatibility/`: JUnit, screenshot and trace
filenames from a later run could replace earlier failure evidence.

The runner now reserves a **fresh** directory under
`local/validation/project-infrastructure/cross-browser/<UTC-run-id>-<short-SHA>/<engine>/`,
refusing existing directories and paths outside `local/validation/`.
The automatic directory labels the current Git HEAD (not uncommitted
worktree bytes), and `--output-dir` permits an explicitly selected fresh
local validation directory. Hosted exact-SHA acceptance remains separate. The same relative directory is handed to the browser test
module in `INFINITYDB_CROSS_BROWSER_ARTIFACT_DIR`, so JUnit and all
failure screenshot/trace files share one run boundary. A selected engine
without that directory fails closed instead of silently falling back to
the old fixed path. The hosted workflow's artifact upload root was
updated to the new `local/validation/` tree, retaining `if: always()`,
the same named matrix jobs, and failure semantics. Existing private
`local/cross-browser-compatibility/` evidence is untouched.

**Validation:** The Windows hermetic runner contract passed **9/9**,
including fresh revision-specific paths, consistent pytest/environment
routing, explicit paths, preserved failures, duplicate-run refusal,
out-of-scope paths, invalid revision refusal and hosted artifact-path
wiring. The test-section registry passed **15/15**, deployment-script
regressions **47/47**, and release-evidence regressions **29/29**.
The existing browser-cohort module had **14 expected skips** without an
explicitly selected engine. Targeted Ruff, repository Pyright (zero
errors/warnings), documentation checks and `git diff --check` passed.
The actual multi-engine browser matrix, hosted CI, Linux/Windows source
parity and release acceptance remain separate validations; no real
Playwright journey, source migration or deployment was performed. No T
or M approval is implied.

### Fourth bounded L2 output-contract update — release-candidate JSON (2026-11-13)

**Baseline:** Clean `dev/tooling-workspace-cleanup` at
`8be3d9763cea8780fb1aef0190bf7d1b54232a69`, after per-run
cross-browser evidence was introduced. The optional `--json-output`
from `tools.verify_release_candidate_browser` could previously
truncate accepted evidence after its runtime/browser postflight.

The verifier now rejects an existing selected output (including a
dangling symlink) **before** starting browser or runtime acceptance.
Its success-only receipt writer rechecks the destination and opens
in exclusive-create mode, preserving prior bytes if another writer
arrives before publication. A write failure blocks CLI acceptance
without printing PASS. The optional-output interface, default/no-output
behavior, exact complete Army/Rules/ITS database gate, served
snapshot/static/version preflight, representative browser journeys
and postflight identity checks remain unchanged. The [testing
guide](testing.md#complete-set-release-candidate-browser-verifier)
now recommends a fresh run-specific `local/validation/` destination,
while preserving historical explicit paths. This is a single-file
collision guard, **not atomic crash-safe publication**; an interrupted
write may leave a new partial file to classify separately. Existing
private artifacts have not been moved, deleted or rewritten.

**Validation:** The Windows verifier test module passed **41/41**
including real local Chromium preflight/DOM/postflight acceptance,
two existing-file collision cases, dangling symlink refusal,
a report appearing during verification, exclusive-create behavior,
and blocked receipt-write errors. Ruff for the affected source and
test files, repository Pyright (zero errors/warnings), Markdown lint,
documentation links/backlog and `git diff --check` passed.
Hosted release acceptance, Linux parity and complete CI remain
separate gates; no hosted candidate was accepted or deployed.
The tracked-retirement (T) and private-data migration (M)
decisions are still unapproved.

### Fifth bounded L2 output-contract update — generic determinism manifest (2026-11-13)

**Baseline:** Clean `dev/tooling-workspace-cleanup` at
`b8f5869ae0e6afadc2ff2de3657588787fe4f30e`, following the
release-candidate receipt guard. The direct generic
`tools.build_determinism_manifest` CLI had two independently
truncating destinations: required `--output` and optional
`--diagnostics-output`. Unlike the previously protected Docker wrapper,
direct invocation and the library's optional diagnostics branch could
silently replace previously accepted evidence.

The generator now checks both selected filenames before starting any
expensive fixture/database/archive work, rejects existing files and
symlinks, and detects a duplicate normalized destination. Both outputs
use exclusive file creation and the unchanged canonical `json_text`
serialization (sorted keys, UTF-8, LF, and trailing newline). Direct
`build_manifest(..., diagnostics_output=...)` preflights and
exclusively writes diagnostics as well. Collisions arriving during
the build cannot truncate either previous output. No existing CLI
arguments, v1/v2 manifest format, hash membership, direct comparison,
Docker command/mount, or hosted artifact upload path were changed.

The current [CI owner](ci.md#cross-platform-deterministic-outputs)
documents fresh categorized local report destinations while preserving
the hosted `local/reports/determinism-manifest.json` compatibility
path. The two outputs are **not an atomic transaction**: an interrupted
or failed build may leave a new partial diagnostics or manifest file
that requires separate inspection. No existing private evidence was
moved or deleted; this is not an L3 migration or L4 tool cutover.

**Validation:** The Windows hermetic comparator/generator regression
module passed **22/22** (including both occupied destinations, duplicate
selection, symlink refusal, the direct diagnostics path, late-arriving
manifest collision, canonical byte formatting and exclusive creation).
The pinned Docker wrapper passed **6/6** and deterministic I/O tests
passed **4/4**, for **32/32 focused tests**. Targeted Ruff, repository
Pyright (zero errors/warnings), documentation lint/links/backlog and
`git diff --check` passed. A real pinned Docker manifest build, hosted
cross-platform byte parity and exact-SHA CI acceptance were not run.
T retirements and M private-source actions remain unapproved.

### Sixth bounded L2 output-contract update — reference-baseline reports (2026-11-13)

**Baseline:** Clean `dev/tooling-workspace-cleanup` at
`8865a50ef7f0231e057d1293bd172c5df216eeaf`, after the
generic determinism manifest guard. The multi-purpose
`tools.report_reference_baseline` CLI previously used unconditional
`Path.write_text` for its JSON and Markdown reports, current citation
minimum, explanation reconciliation, review batches and review pilot.
Repeated explicit paths could silently replace accepted source/audit
evidence.

The CLI now preflights **all four selected output arguments** before
running a source inventory or audit, rejecting previously existing
files, dangling symlinks, and two filenames resolving to the same
destination. All report branches use a shared exclusive-create writer,
preserving UTF-8, LF and existing JSON/Markdown serialization; later
collisions cannot truncate earlier reports. The prior output switches,
reconciliation flags, source verification, comparison semantics and
stdout-only invocation remain intact. The
[testing guide](testing.md) describes fresh
`local/validation/` run directories, without changing old
`local/audits/` input/output paths or producer defaults.

**Known limitation:** Output writing is **not atomic across multiple
files**. A late collision or interruption may leave one *new* report
while another fails, and partially created new files require inspection.
Existing report bytes are never deliberately replaced. This is
a prospective, non-destructive L2 output-contract guard, not migration
authorization. T retirements and M private-source actions remain pending.

**Validation:** The Windows reference-baseline suite passed **79 tests
with 2 skips**, including original real-data baseline/reconciliation
coverage, occupied JSON/Markdown/review paths, citation-minimum preflight,
duplicate normalized output selection, dangling symlink refusal, late
collisions, exclusive-create byte preservation, and independent
fresh-output reproducibility checks. The dependent source-coverage
disposition suite passed **23/23** (total **102 passed, 2 skipped**).
Targeted Ruff, repository Pyright (zero errors/warnings), Markdown lint,
documentation links/backlog and `git diff --check` all passed. The
full suite and hosted exact-SHA CI checks were not run for this update.

### Seventh bounded L2 output-contract update — catalog browser receipts (2026-11-13)

**Baseline:** Clean `dev/tooling-workspace-cleanup` at
`9334588c2e058525fef193696e1735ca08e260a7`, after
`report_reference_baseline` collision protection. The eleven
optional browser verifiers share a need for JSON run evidence but
retain distinct source and browser semantics. Five catalog-navigation
entrypoints—Ammunition, General Rules, Labels, States and canonical
Traits—share one `verify_ammunition_browser.verify` implementation
and identical direct JSON receipt-writing conventions.

Added a new maintained `tools/browser/report_output.py` helper and
migrated only these five catalog entrypoints to it. With `--output`,
they reject existing destinations (including dangling symlinks)
**before** source discovery or Playwright startup, and use exclusive
creation to prevent later collisions while preserving sorted,
indented UTF-8/LF JSON. Parent directories are created only when
writing a fresh report. No `--output` runs still print their normal
summary; failed browser observations still result in nonzero exit
and, when selected, a report preserving those failures. Existing
explicit output filenames remain supported but cannot be overwritten.

The [testing guide](testing.md#optional-catalog-navigation-browser-report-evidence)
recommends fresh
`local/validation/browser/catalog-navigation/<UTC-run-id>-<short-SHA>/`
run destinations. No browser engine, selector, source URL, source
membership, optional/hosted gate or CLI argument changed. The remaining
six specialized verifiers (`verify_hacking_programs_browser`,
`verify_non_skill_army_browser`,
`verify_unit_skill_presentation_browser`,
`verify_rule_fragment_browser`,
`verify_structured_skill_charts_browser`,
`verify_trait_wiki_browser`) still require a separate, focused
writer-and-consumer cutover; this batch does not touch their reports
or third-party saved Wiki HTML inputs.

**Limitations:** Each output is exclusively created but not an atomic
crash-safe write; interrupted fresh reports need separate inspection.
The helper is only for optional browser-run JSON, not a new public
release acceptance gate or permission to migrate existing evidence.
No T retirement or M private-source action is implied.

**Validation:** Windows focused checks passed **24/24** new hermetic
report-contract tests, **55/55** General Rules/source-catalog tests,
**22/22** Trait Wiki source-contract tests and **15/15** test-section
registry tests: **116 passed**, no skips/failures. Targeted Ruff for
the six added/edited Python implementations and the test module,
repository Pyright (zero errors/warnings), documentation lint/links/
backlog, and `git diff --check` passed. No direct hosted matrix,
complete-suite run or new live multi-catalog Playwright acceptance
was performed; those remain separately pinned validation gates.

### Eighth bounded L2 output-contract update — Hacking and non-Skill browser receipts (2026-11-13)

**Baseline:** Clean `dev/tooling-workspace-cleanup` at
`d626da623dcb0cd240a017bd211d3ed444e03622`, after the first
five catalog verifiers adopted `tools.browser.report_output`.
Two more optional browser verifiers, `verify_hacking_programs_browser`
and `verify_non_skill_army_browser`, still had direct
`Path.write_text` JSON outputs. Hacking Programs could truncate a
selected historical receipt, while non-Skill Army also created a
parent directory before overwriting.

Both entrypoints now preflight `--output` through the same helper
**before** starting Playwright or a local WSGI server, and publish
the unchanged sorted, indented UTF-8/LF JSON via exclusive creation.
Existing files and symlinks fail closed; newly occupied paths cannot
replace old evidence. Parent directories are created only for a fresh
report. The original browser observations, source identities, fixed
12-Program set, seven representative Army Unit cases, width checks,
stdout summaries and nonzero failure semantics remain intact.
Hacking Programs retains its `--self-host`/non-default
`--base-url` exclusivity and the same source/WSGI acceptance; non-Skill
Army still uses an externally served source-consistent application.
Historical explicit report paths are accepted as names but never
overwritten. There are no changes to published databases, runtime
code, private saved HTML, hosted gates or browser engines.

The [testing guide](testing.md#optional-hacking-programs-and-non-skill-army-browser-receipts)
now recommends fresh domain-scoped `local/validation/browser/`
run folders for each command. The four remaining specialized
verifiers—`verify_unit_skill_presentation_browser`,
`verify_rule_fragment_browser`,
`verify_structured_skill_charts_browser` and
`verify_trait_wiki_browser`—are outside this cutover. As with the
preceding L2 slices, a new receipt may be partially written after
an interrupted process, and the receipt is not an atomic or universal
acceptance gate. T and M decisions remain unapproved.

**Validation:** Windows regression checks passed **39/39**
shared browser receipt tests (including the two specialized CLI paths,
`--self-host`, collisions before/during verification, stdout-only
invocation and unchanged failure outcomes), **10/10** Hacking Program
source/publication tests and **14/14** non-Skill Army presentation tests:
**63 passed**, no skips or failures. Targeted Ruff, repository Pyright,
documentation lint/links/backlog and `git diff --check` results were
verified separately. No fresh live Playwright matrix, hosted exact-SHA
CI, full-suite execution or Linux validation was performed.

### Ninth bounded L2 output-contract update — Unit Skill and rule-fragment browser reports (2026-11-13)

**Baseline:** Clean `dev/tooling-workspace-cleanup` at
`e796f271fbeeb3f0cb218f18945fca19c10f6284`. Seven of the
eleven optional browser commands already used the shared new-file-only
`tools.browser.report_output` JSON writer. The Unit Skill
presentation and Weapon/Glossary rule-fragment verifiers still used
unconditional `Path.write_text`, allowing historical evidence to
be truncated and repeated invocations to overwrite earlier reports.

Only these two CLI writers were cut over: optional `--output` is
preflighted before Chromium or optional WSGI startup and is written
with exclusive file creation, preserving sorted indented UTF-8/LF
bytes, error observations, CLI summaries and existing nonzero status
on failed checks. Parent directories are created only for fresh
reports; existing files and symlinks are refused, and a race between
preflight and publication cannot overwrite a prior report.

Unit Skill retains explicit slugs, widths, optional availability
filters, distance units, browser channel and headed mode; the
Rule Fragment verifier retains the `--self-host` versus
non-default `--base-url` exclusion and its link/fragment assertions.
The underlying `verify(...)` APIs and browser/WSGI navigation
remain unchanged, as do output-free CLI invocations. This does
not modify source data, private evidence, hosted workflows or
published build assets. The [testing guide](testing.md#optional-unit-skill-and-rule-fragment-browser-receipts)
names new domain/run-scoped `local/validation/browser/` destinations
without migrating existing reports.

**Boundary:** The remaining two specialized L2 writer reviews are
`verify_structured_skill_charts_browser` and
`verify_trait_wiki_browser` (the latter takes private saved Wiki
HTML and must preserve that source boundary). A fresh exclusive
receipt is not crash-atomic and an interrupted write can leave a
new partial file requiring inspection. T retirements and M
private-source moves/deletions remain unapproved.

**Validation:** Windows focused checks passed **55/55** shared browser
receipt regressions, **34/34** Unit Skill Presentation tests
(including live local Chromium for optional flags, complex profiles,
distance formatting, contextual relations and Spec-Ops), and
**12/12** Rule Fragment tests (including the ephemeral WSGI host):
**101 passed**, no skips/failures. Targeted Ruff for both verifiers
and the test module, repository Pyright (zero errors/warnings),
documentation lint/links/backlog and `git diff --check` all passed.
The complete test suite, all-browser matrix, hosted exact-SHA CI and
Linux worker acceptance were not run for this slice.

### Tenth bounded L2 output-contract update — Structured Skill Charts and Trait Wiki browser receipts (2026-11-13)

**Baseline:** Clean `dev/tooling-workspace-cleanup` at
`d3a771af624a4c10dc2dea047287c0112cf17999`. Nine of the
eleven optional browser verifier CLIs had migrated to the common
exclusive-creation output writer. `verify_structured_skill_charts_browser`
and `verify_trait_wiki_browser` were the final two unconditional
`Path.write_text` JSON report writers. The Structured Skill
Charts verifier checks Martial Arts, Booty and MetaChemistry source
rows/DOM; the Trait Wiki verifier uniquely requires a private,
previously saved official Traits HTML source via `--wiki-html`.

Both now preflight selected `--output` paths through
`tools.browser.report_output.require_new_browser_report` before
reading source or starting a browser, and use
`write_browser_report` to exclusively create unchanged sorted,
indented UTF-8/LF JSON. The optional writer can create the parent
directory for a fresh receipt. Existing destinations and symlinks
are rejected, and a report arriving after preflight cannot be
truncated. All original browser selectors, source comparisons,
exit codes, headings, CLI arguments and output-free summaries remain
unchanged.

**Private source boundary:** `--wiki-html` is still mandatory,
read using `utf-8-sig`, and passed as a string into the same source
audit/browser mock of official Wiki routes. Its HTML bytes are
never modified, copied to tracked sources or used as a writable
output. An explicit attempt to select the saved HTML file itself
as `--output` is blocked because it exists. The new report is
separate from retained ignored source material. The
[testing guide](testing.md#optional-structured-skill-charts-and-trait-wiki-browser-receipts)
shows domain/run-scoped `local/validation/browser/` output examples.

**L2 browser family:** All eleven previously audited optional
browser CLI `--output` JSON paths now share the non-overwrite
guard. This closes the *bounded browser-verifier receipt family*,
not all possible L2 output producers, and does not retire or
move any historical or private artifact. The newly created report
is not crash-atomic; interruptions may leave incomplete *new*
evidence requiring inspection. T retirements and M private-source
actions remain unapproved. Complete hosted matrix, full-suite,
Linux parity and release acceptance remain independent gates.

**Validation:** Windows focused runs passed **69/69** shared browser
report-contract tests (source/output separation, occupied and late
collisions, preserved CLI summaries and failure status, mandatory
Wiki HTML, UTF-8 BOM preservation), **17/17** structured chart
source/publication tests and **22/22** Trait Wiki references/tests:
**108 passed**, no skips or failures. Targeted Ruff for both tools
and receipt tests, repository Pyright (zero errors/warnings),
documentation lint/links/backlog and `git diff --check` passed.
No new live third-party-snapshot Playwright run, hosted exact-SHA
matrix, complete suite or Linux worker acceptance was executed
for this L2 slice.

### Eleventh bounded L2 output-contract update — test-worker benchmark receipts (2026-11-13)

**Baseline:** Clean `dev/tooling-workspace-cleanup` at
`3e06a20001652704a481ce11510e538ebb8e39d9`. After the
eleven optional browser-verifier reports were protected, a
read-only scan of retained root `tools/` writers found additional
L2 concerns. The scan included direct `.write_text(` and
`.write_bytes(` uses, but is **not** exhaustive for `open`,
SQLite, external programs or dynamically constructed paths.

**Remaining output families and distinctions:**

- **Run evidence still at risk:** retained audit/reconciliation
  commands with optional `--output`, `--json-output` and
  `--markdown-output` writes, such as
  `audit_1_0_reference_inputs`, weapon-trait audits,
  `audit_database_separation` and
  `audit_runtime_database_surface`; operational/capacity JSON
  from `capacity_test`, `deployment_resources`,
  `deployment_diagnostics` and `deployment_alerts`.
  They need individually reviewed caller/output/exit contracts
  and non-overwrite tests before L2 can close.
- **Distinct state contracts:** tracked generated databases and
  curated publication outputs have deliberate, validated replacement
  paths; the deployed `metrics_history` volume is persistent
  state; build scratch/intermediates, pytest temporary files,
  append-only metrics, browser slot locks and explicit host-profile
  toggles need their own owner/lifetime policy. Do not apply a
  one-size-fits-all receipt guard to those categories.
- **Already protected:** prior release evidence, reference baseline,
  generic determinism, and the eleven optional browser verifiers.
  This update protects the separate test-worker benchmark
  measurement receipt, **not** every remaining writer.

**Implemented bounded batch:** `benchmark_test_workers` now
resolves its original default or explicit `--report` destination
immediately after parsing/validating benchmark options and before
running `tools/run_checks.py` even once. Occupied files and
symlinks fail with existing usage-error status 2 and leave old
bytes untouched. `write_report` preserves the canonical sorted,
indented UTF-8/LF JSON but uses exclusive `open("x")` to reject
late collisions. The original default `reports/TEST-WORKERS
<timestamp>.json`, explicit path support, normal check-runner
command, schedule, failure recording and exit statuses are
unchanged; no legacy report is moved.

The [testing guide](testing.md#benchmark-tooling) recommends
fresh `local/performance/test-workers/<run-id>-<sha>/` destinations
without making the old default invalid. Fresh report writing is
not crash-atomic: an interruption may leave incomplete new
evidence requiring inspection. No T/M action, cleanup of root
`reports/`, package move or hosted deployment is authorized.

**L2 state:** **Open.** Next work should prioritize a bounded
operations-report pair or coherent audit-report family with
independent consumer tests. L4 tool categorization remains separate
from L2 path/writer migration and requires import/entrypoint
review. The full test suite, hosted exact-SHA CI and Linux worker
parity are independent validation gates.

**Validation:** Windows focused `tests/test_benchmark_test_workers.py`
passed **15/15** tests, covering preserved JSON, stale/symlink
collisions, exclusive-write races, default and explicit output
preflight, successful and failed check-run reports and late
collisions. Ruff passed for the implementation and regression tests;
repository Pyright returned **0 errors/0 warnings**; docs lint (47
files), local links (46 files), backlog validation and
`git diff --check` passed. No actual benchmark subprocess,
hosted CI, Linux worker run, complete test suite, or legacy report
migration was performed.

### Twelfth bounded L2 output-contract update — operational receipt family (2026-11-13)

**Baseline:** Clean `dev/tooling-workspace-cleanup` at
`19163372ba066159279818ec04ada0c84415dbd1`. The previous
eleventh slice protected worker-benchmark receipts; the next four
retained operational commands still overwrote an arbitrary
`--output` path after potentially expensive or stateful collection.
The four naturally form one **larger, coherent L2 batch** because
they share run-receipt JSON formatting and independent but related
resource/capacity/diagnostics/alerts consumers.

**Implementation:** Added `tools/operations/receipt_output.py`
for new optional/required operational JSON evidence. Its
`require_new_receipt` refuses existing files and dangling symlinks
*before* network measurement, wrapped commands, Docker or host
sampling, log collection, input report loading or alert evaluation.
The new `write_new_json_receipt` uses exclusive `open("x")` at
publication to defeat late collisions and preserves the existing
sorted, indented, UTF-8/LF JSON format. New parent directories are
created only at write time. The four consumers are
`capacity_test`, `deployment_resources`,
`deployment_diagnostics` and `deployment_alerts`.

**Compatibility and distinct statuses:** Existing direct-script
and module invocations remain available. The cleanup also corrected
the pre-existing direct-script import failure in
`deployment_alerts`, with a focused `--help` subprocess guard.
No HTTP workload, resource sample, Docker log sanitization,
threshold, metrics/health interval, warning/critical classification,
source schema or CLI flag changed. Existing measured outcomes keep
the same statuses: capacity load errors return 1; wrapped resource
commands forward their own exit codes; diagnostics succeeds with 0;
alerts return OK=0, warning=1, critical=2, unknown=3.
**Output-path errors** return capacity=2, resources=2,
diagnostics=2 and alerts=3. In particular, an alert receipt
collision never creates a false critical alert (2).
For diagnostics and alerts, a selected input resource report may
not also be the output file; it is never overwritten.

The [deployment guide](deployment.md#repeatable-http-capacity-scenario)
and [testing guide](testing.md#benchmark-tooling) now recommend
fresh `local/performance/http-capacity/<run-id>/` and
`local/operations/deployment/<domain>/<run-id>/` run evidence,
using matching run identifiers when correlating observations.
This changes prospective examples, **not** accepted CLI defaults
or the location of any prior ignored `reports/` material.
A newly created receipt is not crash-atomic; an interruption
can leave partial new evidence requiring inspection.

**L2 remains open:** remaining independent audit-report writers
(`--output`, `--json-output`, `--markdown-output`) and their
consumer/fixture contracts need larger family-based inspection;
do not apply receipt guards to persistent metrics/history SQLite,
tracked published assets, build scratch or append-only streams.
No live host/Docker, network load, production, private-source
migration (M), tracked retirement (T), broad tool moves (L4)
or root report cleanup was performed. Hosted exact-SHA CI, full
test suite and Linux parity remain separate acceptance gates.

**Validation:** Windows focused suites passed **30/30** new operational
receipt tests, **6/6** HTTP capacity tests, **9/9** resource
capture tests, **8/8** diagnostics tests and **8/8** alert
evaluation tests, together **61 passed**. Test-section registration
passed **15/15** more: **76 total, no skips/failures**. The new
tests cover early/late report collisions, exclusive creation,
dangling symlinks, impossible parent paths, source/output aliasing,
exact canonical JSON bytes, alert exit states 0–3, wrapped command
exit passthrough, stdout-only operation and direct-script `--help`
for all four commands. Targeted Ruff passed for all six Python
implementation and regression files, repository Pyright reported
zero errors/warnings, docs lint/links/backlog passed, and
`git diff --check` passed. No actual load test, Docker resource
capture, live incident diagnostics, hosted CI, Linux parity
or full suite was run for this slice.

### Thirteenth bounded L2 output-contract update — eight source-audit JSON/Markdown writers (2026-11-13)

**Baseline:** Clean `dev/tooling-workspace-cleanup` at
`738d0c1b56d8f784af67248ec5b0354da4c9c234` after the
four-command operational batch. This larger source-audit family
repeated the same independently unsafe behavior: JSON and Markdown
receipt paths could overwrite historical evidence, potentially
*after* reading private source PDFs, Wiki archives and curated review
files. Some commands require both outputs, some require JSON
only, and others permit stdout-only JSON. Existing reference
baseline reconciliation already has its separate verified writer;
that implementation was not changed.

**Scope (eight retained CLIs):**
`audit_1_0_reference_inputs`,
`audit_weapon_chart_profiles`,
`audit_weapon_definition_gaps`,
`audit_weapon_trait_cross_sources`,
`audit_weapon_traits_prose`,
`audit_weaponry_family_clauses`,
`audit_wiki_weapon_chart_names`, and
`audit_auxiliary_silhouette_provenance`.
No source-audit result, source-authority policy, review decision,
PDF extraction, Wiki archive, Army/Rules database, published
profile or source-difference finding was edited.

**Implemented contract:** `tools/research/report_output.py`
preflights the full selected JSON/Markdown output set **before**
calling the original audit. It rejects occupied files (including
dangling symlinks), equivalent/canonicalized duplicate destinations,
and any saved source path accidentally selected for output.
The unchanged serialized JSON/Markdown strings are created using
UTF-8/LF `Path.open("x")`, preserving each command's original
`sort_keys`, `ensure_ascii`, Markdown rendering, stdout and
CLI success status. An output arriving after initial preflight
cannot replace accepted bytes. Directory creation is deferred until
a fresh receipt is actually written. Invalid/occupied outputs
exit 1 with a bounded error message, without starting the audit.

The [testing guide](testing.md#source-and-weapon-audit-jsonmarkdown-run-receipts)
now recommends ignored, role-named JSON and Markdown under
`local/research/weapon-source-audits/<UTC-run-id>-<source-or-checkout-SHA>/`.
Existing explicit destinations and source consumers remain supported
when the output paths are unoccupied. This is a prospective writer
change, not approval for relocating archived reports or source
material. A new file is not crash-atomic, and the two-file output
is not transactional: after partial failure, inspect and discard
*only newly created incomplete receipts* through a separate
approved retention process. No silent deletion or overwrite.

**Validation:** Windows hermetic output-contract regression
`tests/test_source_audit_report_output.py` passed **57/57**,
including all eight CLI interfaces, first/second-path collisions,
canonical duplicate destinations, late concurrent claims, source
aliasing, stable JSON/Markdown bytes and stdout-only cases.
The eight original audit tests passed **148/148** combined,
including available pinned source fixture reviews. The
test-section registry passed **15/15** more: **220 focused tests
passed**, zero skips/failures. Ruff passed for all eight entrypoints,
the shared helper and the new tests; repository Pyright returned
**0 errors/warnings**, docs lint (47 files), Markdown links
(46 files), backlog and `git diff --check` all passed. Hosted
exact-SHA CI, a complete suite and Linux worker validation
were not performed.

**L2 state:** Still open. The remaining separate single-output
semantic and runtime database audit CLI family, enrichment and
source-presentation audits, and other specialized producers need
classification by output purpose and actual consumer. Persistent
SQLite, tracked source publication, append-only captures and
temporary build state remain explicitly excluded from a blanket
receipt rule. T tracked retirements and M private-file migration
or deletion are not approved.

### Fourteenth bounded L2 output-contract update — fourteen single-output semantic/source/runtime audits (2026-11-13)

**Baseline:** Clean `dev/tooling-workspace-cleanup` at
`f4d4ed17f25e889d784ca4b0bf02092bf503e390` after the
eight-command JSON/Markdown source-audit batch. A further
**fourteen** maintained single-output `audit_*` commands accepted
optional `--output` JSON receipts but still overwrote the
selected destination, sometimes after expensive database
validation or reading private Wiki HTML.

**Scope:** `audit_army_faction_semantics`,
`audit_database_separation`, `audit_enrichment_coverage`,
`audit_fireteam_semantics`, `audit_loadout_semantics`,
`audit_normalization_links`, `audit_peripheral_semantics`,
`audit_profile_semantics`, `audit_relationship_semantics`,
`audit_runtime_database_surface`,
`audit_semantic_deduplication`,
`audit_source_presentation`, `audit_trait_wiki_anchors`,
and `audit_unit_semantics`. These are report-only commands
and do not rewrite published databases or curated policies.

All fourteen now preflight their optional report destination
with the existing `tools.research.report_output` guard **before**
calling `audit_database`, `audit_coverage` or the saved Traits
HTML parser. The report is created with exclusive `open("x")`
after its original serialization, which preserves sorted/indented
UTF-8/LF JSON and each command's choice of `ensure_ascii`.
Occupied files, symlinks, input-file aliases and late collisions
cannot overwrite earlier evidence. `--output` remains optional:
JSON stdout or human-oriented audit summary behaviors, saved-source
UTF-8 BOM parsing, source checks, success/failure gates, prior
CLI argument validation and existing public tool APIs are
unchanged. Report collision exits 1, before any audit work.

**Separate lifecycle contract:** `audit_rules_interactions` also
contains an intentional `--refresh-catalog-scope` mode that can
update maintained source data. It is **excluded** from this
single-output receipt batch and requires an explicit joint
output/check/refresh consumer review; no rewrite mode was
implicitly repurposed. Other special audit tools and standalone
writers remain subject to L2 inventory. This pass does not
authorize archived report deletion, a global path-default change,
tracked history retirement (T) or private source migration (M).

The [testing guide](testing.md#single-output-semantic-and-runtime-audit-json-receipts)
documents run-scoped ignored paths under
`local/validation/data-model/` and
`local/research/trait-wiki-audits/`. A newly created report is
not crash-atomic; an interrupted write requires inspection.
No source file, SQLite database, rule definition, publisher,
browser, Syncthing configuration or deployment was changed.

**Validation:** The new hermetic single-output regression suite
passed **74/74** tests, exercising all fourteen CLI families:
occupied prior receipts, input/output aliases, exact JSON
serialization, no-output summaries, late collisions and original
failure statuses for semantic, source-presentation and Trait Wiki
checks. The fourteen existing audit/source-reference suites
passed **113 tests with 1 skipped fixture case**, and the
registered test-section suite passed **15/15**. The previous
shared source-audit report regression suite also passed
**57/57**, yielding **259 passed, 1 skipped, zero failures**.
Targeted Ruff passed for all fourteen modified tools and the
new suite, Pyright returned zero errors and warnings,
documentation lint/links/backlog and `git diff --check` passed.
Hosted exact-SHA CI, full-suite,
Linux worker parity, actual live source collection and deployment
were not run in this bounded slice.

**L2 status:** Open for review of special producers and explicit
rewrite/check modes. Subsequent L4 tool organization should
happen only after import/entrypoint and generated-output consumer
boundaries are audited. The reserved T/M phases remain gated.

### Fifteenth bounded L2 output-contract update — specialized audit lifecycle boundaries (2026-11-13)

**Baseline:** Clean `dev/tooling-workspace-cleanup` at
`b5b9eb1f512aedf650b1f14e76a399915ab479d5`. The
fourteenth L2 slice protected fourteen single-output JSON audits,
but three retained source/check/publication CLIs needed a different
contract review. These were combined into one **specialized
research-and-validation batch**, not mechanically converted to
new-file-only `--output` behavior.

**Rules interaction checklist (`audit_rules_interactions`):**
The existing `--output` deliberately **regenerates** a selected
Markdown checklist, including the tracked
`docs/rules-interaction-checklist.md`; it remains an explicit
replacement command. `--check-output` remains read-only,
`--report-catalog-scope-drift` remains a read-only database
comparison, and `--refresh-catalog-scope` remains an explicit
intentional rewrite of the reviewed scope using paired
Army/Rules databases. All existing CI/release check arguments
and exit statuses are unchanged. Checklist regeneration now
also refuses a destination that aliases the policy JSON, catalog
scope JSON or any file within the selected curated Rules directory;
ordinary tracked checklist regeneration still works. Added
**`--receipt-output`** for independent immutable Markdown
*run evidence*. Its selected
path is preflighted before source analysis and written through
`tools.research.report_output` using exclusive UTF-8/LF
creation. Receipt mode cannot combine with regenerating the
checklist (`--output`), rewriting catalog scope
(`--refresh-catalog-scope`) or producing drift-only stdout.
Read-only `--check-output` and release gates are compatible,
including retaining a fresh receipt from a failing review gate.
No maintained checklist or catalog-scope bytes were changed
by this batch.

**Pinned PDF revisions (`audit_pdf_revision_deltas`):**
The original fixed ignored output default
`local/audits/pdf-deltas-2026-11-06.json` remains available
*only when new*. Any existing or symlinked destination is
rejected *before* reading the pinned PDF inventory or running
expensive version-locked extraction. JSON formatting, source
hash verification, pair selection, outside-`local/` prohibition
and console summaries remain unchanged. The final JSON write
uses exclusive creation, protecting against another process
claiming the selected destination after extraction. New runs
should choose `local/research/pdf-revision-deltas/<RUN_ID>/`.

**Restrictions candidate (`audit_restrictions_source_chart`):**
`--output` remains a *new candidate publication file*, not
a replacement of tracked rules or a general audit receipt.
The existing rule limiting it to ignored `local/`, and the
mutual exclusion with `--check-publication`, are preserved.
The previous `Path.write_bytes` following a preflight could
truncate a concurrently created file. The shared
`write_audit_bytes_or_exit` now exclusively opens `xb`
after the existing source projection, with an added explicit
dangling-symlink refusal. The exact projected bytes, typed
negative-condition semantics, original tracked publication
and read-only publication comparison are unchanged.

**Excluded after contract inspection:** Host resource sampling
already uses exclusive `open("x")` for its fresh
`local/benchmarks/*.jsonl` streaming sample. No change is
needed. Work-tree ZIP archiving has a distinct default
content-addressed deduplication and *explicit replacement*
contract, with separate inputs/consumers; it is not converted
to a JSON audit receipt guard here. Other stateful publishers,
tracked database builders and retention/migration decisions
remain separate.

The [testing guide](testing.md#specialized-audits-maintained-checklist-pdf-deltas-restrictions-candidates)
documents run-scoped output examples and the explicit
regeneration-versus-evidence boundary. Newly created receipts
and publication candidates are not crash-atomic; operators
must inspect interrupted new files. No private source copies,
historical reports, release artifacts, tracked rule scope,
databases, deploys, Syncthing configuration or work-tree
archives were altered. T retirement, M migration/deletion
and L4 package moves remain separately gated.

**Validation:** Windows focused suites passed **31/31**
specialized output regression cases, including retained checklist
regeneration, source-alias rejection, deliberate catalog-scope
refresh, immutable failing-gate receipts, existing and late
collisions, pinned PDF hashes/output bytes, Restrictions Chart
projection bytes and direct-script launch. Existing
`test_audit_rules_interactions` passed **15/15**,
`test_game_mode_source_table` **15/15** (including Chromium
at three widths), unchanged host-sampler contract **22/22**,
shared source-audit writer **57/57**, test-section registration
**15/15**, and CI check-runner consumers **111 passed with
1 skipped**. **Total: 266 passed, 1 skipped, zero failures.**
Targeted Ruff passed for all changed Python files,
repository Pyright returned zero errors/warnings,
docs lint (47 files), links (46 files), backlog validation
and `git diff --check` passed. This does **not** assert
full-suite, hosted exact-SHA CI, Linux worker parity,
live pinned-PDF extraction or deployment acceptance.

**L2 state:** Still open for a final focused inventory of
remaining specialized report writers, especially explicit
ZIP export, source/planning exports, one-off ignored artifacts
and maintained-state builders. Not every `--output` denotes
immutable run evidence; classification must precede changes.

### Sixteenth bounded L2 output-contract update — pinned exports and candidate protection (2026-11-13)

**Baseline:** Clean `dev/tooling-workspace-cleanup` at
`0f15d571c31d92357a579888d5a30e4ca6469839`, following
the specialized Markdown/PDF/Restrictions candidate slice. This
larger L2 batch reviewed developer-audit JSON, Variant Usage
source candidates, symbol source/override handoff plans and
deterministic work-tree ZIP archives together. Those output
families have **different reuse/replacement contracts**.

**Deployed-object audit receipt:** `audit_deployed_object_inventory`
previously wrote `--json-output` through an unconditional
`Path.write_text` and did not create nested directories.
It now uses `tools.research.report_output`: occupied files and
symlinks are checked **before** source/Army database analysis,
and a new JSON report is created exclusively. Its original
`ensure_ascii=False`, indentation, UTF-8/LF serialization and
stdout-only fallback are unchanged. It does not rewrite the
maintained delivery/candidate/source-domain review records.

**Variant Usage review candidate:** `build_variant_usage` used
a fixed sibling `.json.tmp` file followed by
`Path.replace`, which could overwrite an earlier candidate
despite the output representing unapproved source analysis.
The selected `--output` path is now checked before source
projection, including symlink and occupied-file rejection.
The **existing strict `local/variant-usage-*.json` name
restriction** remains for compatibility. Its sibling staging
file is created exclusively, then the complete new candidate
is published via same-directory `os.link`, which cannot
replace a competing file. Only the temporary file created by
the current invocation is cleaned up. Existing `--check`
is still read-only, mutually exclusive with `--output`,
and source-parity/summary JSON semantics are unchanged.
The loose `local/` filename is a *documented temporary
exception*, not a new path-policy template; consumer review
is needed before allowing a categorized default directory.

**Pinned symbol handoff plans:** `write_source_plan`, shared
by `export_symbol_source_plan` and
`export_symbol_override_lookups`, already accepted identical
existing bytes idempotently and refused a different plan.
However, its `.tmp` staging followed by `Path.replace`
could overwrite a destination created concurrently. The
publication now creates a hard link to its completely staged
file, atomically and **without replacing existing bytes**.
If another producer wins, identical bytes are accepted
idempotently; differing or symlink destinations fail.
The exclusive staging guard and cleanup of only owned
`.tmp` files remain intact, as do exact JSON format,
source hashes, source-plan provenance and read-only handoff.
Hard-link support is required on the selected filesystem;
an unsupported filesystem fails rather than degrading
to an overwriting operation.

**Excluded after explicit classification:**

- `create_work_archive` retains its distinct work-tree ZIP
  archive lifecycle: default names include commit/dirty
  fingerprint and identical content is reused, while an
  operator-chosen `--output` is an intentionally replaceable
  backup destination. A regression test preserves that
  behavior; no default path or ZIP membership changed.
- `build_symbol_artwork_review` already uses exclusive new
  HTML file creation. `prepare_symbol_publication` reserves
  fresh candidate directories, while publisher/promoter
  tools intentionally change validated tracked publication
  state. No blanket receipt guard was added to these
  stateful workflows, source downloads, pinned databases,
  build intermediates or append-only metrics.
- Existing ignored files and root-level archival material
  were not moved. Private source/review migration (M),
  historical tracked retirements (T), and L4 tool/package
  reorganizations remain gated separately.

The [testing guide](testing.md#deployed-object-receipts-variant-usage-candidates-and-symbol-export-plans)
documents examples and the retained default/CLI boundaries.
New source-audit receipts should use
`local/validation/deployed-objects/<RUN_ID>/`, and pinned
source-handoff exports can use
`local/research/symbol-source-plans/<RUN_ID>/`. The strict
Variant Usage filename exception and explicit ZIP replacement
contract are called out rather than disguised as completed L2
path migrations. Newly created report files may still be
partial after interruption; existing source and previously
accepted outputs are never implicitly deleted.

**Validation:** Windows focused suites passed
**19/19** new export/candidate contract tests (including
supported direct-script versus module invocation);
**6/6** pinned symbol source/override plan tests;
**99 passed, 2 skipped** Variant Usage tests;
**7/7** deployed-object inventory tests;
**6/6** Variant Usage source-parity tests;
**6/6** deployed-object reference tests;
**8/8** work-tree archive tests including the unchanged
explicit replacement contract; and **15/15** registered
test-section tests. **Total: 166 passed, 2 skipped, zero
failures.** Targeted Ruff passed for all changed Python
files, repository Pyright returned zero errors/warnings,
documentation lint (47 files), links (46 files), backlog
validation and `git diff --check` passed. Test fixtures
do not substitute for a live symbol handoff, cross-platform
network filesystem hard-link acceptance, hosted exact-SHA CI,
a complete suite or Linux-worker parity.

**L2 state:** Open for final classification and closure audit
of remaining special writers and for an explicit L3/L4
handoff. Closing L2 must not imply approval of T/M or
unverified host/Linux parity. A focused implementation batch
does not replace the full suite or hosted exact-SHA CI.

### Seventeenth bounded L2 writer-classification and remaining output-safety closeout (2026-11-13)

**Baseline:** Clean `dev/tooling-workspace-cleanup` at
`c2256b04f9da898747e7e3f3597f84c9100634a8` after sixteen
non-destructive L2 output-contract slices. This pass went beyond
the `tools/` reports alone: it reviewed active output commands in
the `src/infinity_db` application CLI and acquisition provenance,
sampled the maintained `scripts/` and GitHub workflow destinations,
and cross-checked the known CLI/test/CI/export and build consumers.
The targeted repository text scans included **127 readable
`tools/` files, 1,081 `src/` files, 7 `scripts/` files
and 5 workflow files**. These are *bounded text searches*
for writers/entrypoints, not a formal whole-repository AST or
external producer filesystem audit.

**Gap A — retained check transcripts:** `tools/run_checks.py`
already rejected source/data extensions and Git-tracked
destinations, but its `Reporter` used `open("w")` for
`--report`. That could truncate an earlier check result, including
a repeated legacy `reports/CHECKS YYYYMMDD-HHMMSS.txt` within
one second. It now rejects occupied output and symlink
destinations *before* any selected stage, and opens the
new transcript exclusively via `open("x")`. Current
console streaming, partial-on-interruption semantics, report
argument normalization, legacy defaults and original 0/1
stage outcomes remain unchanged; collision returns the
existing runner-error exit code **2**. The
[testing guide](testing.md#reports) recommends fresh
`local/validation/project-infrastructure/checks/<RUN_ID>/`
paths without moving or replacing historical root reports.

**Gap B — explicitly replaceable full-asset ZIP:** The
`build_full_asset_bundle` workflow intentionally rebuilds
the selected full-asset ZIP, including its existing default
`reports/full-assets.zip`, for the manually selected
external full-assets CI handoff. This is **not** immutable run
evidence. Its former fixed `.<destination>.tmp` cleanup
unconditionally deleted any existing staging file from
another producer before writing. Staging is now exclusively
reserved and cleaned up **only if created by this invocation**;
a symlink final destination is refused. The *completed final
ZIP remains intentionally replaceable* after canonical
validation. ZIP bytes, digest, staging/CI consumer checks
and default destinations are unchanged. The
[optional full-asset CI guide](ci.md#optional-external-bundle-check)
now recommends a fresh `local/handoffs/full-assets/<RUN_ID>/`
path when different bundle generations must be retained.

**Gap C — installed CLI Peripheral coverage:** The
`infinity-db validate-peripheral-identities --database ...
--output ...` command generated an optional source-validation
JSON via unconditional `Path.write_text`. It now
preflights occupied/symlink destinations before opening
reviewed identity sources and uses an exclusive UTF-8/LF
create at publication. The original JSON schema,
`--database` dependency, console counts, source validation
and 0/1 outcomes are unchanged. Standalone scenario-map
SVG rendering is separately classified as an intentional
repeatable render/export; its public behavior was not changed.

**Gap D — immutable acquisition provenance:** The core
`write_snapshot_manifest` (Army/Wiki/Symbol source
handoffs) accepted an identical existing manifest
idempotently, but wrote a fixed sibling `.json.tmp`
and then called `Path.replace`, allowing a competing
acquisition's provenance to be clobbered. It now refuses
symlink outputs, exclusively stages complete canonical
JSON, and atomically publishes with same-directory
no-replace `os.link`. If the final path appears concurrently,
the writer accepts *only identical canonical content*;
a different provenance record is never overwritten.
Stale staging is retained for owner inspection, and
only this invocation's staging is removed. The
[data lifecycle guide](../data/README.md#current-paths-and-behavior)
documents this no-clobber guarantee and filesystem
hard-link requirement. Nothing was downloaded or
moved in this change.

**Consolidated L2 writer classification:**

| Writer/output family | Retention and publication contract | Remaining transition |
| --- | --- | --- |
| Check runner, release/CI/determinism/browser receipts, benchmark and operational measurements, audit JSON/Markdown, Peripheral review | Fresh evidence; reject occupied files and symlinks, use exclusive creation; retain failed-run evidence | Keep legacy explicit locations/readers until independently accepted, then prefer categorized `local/` paths |
| Immutable Army/Wiki/Symbol snapshot manifests and exported source/override plans | Identical complete content is idempotent; different source identity is rejected; atomic no-replace publication | Cross-repository source/provenance staging and Windows/Linux filesystem acceptance |
| Variant Usage and Restrictions candidates, symbol artwork comparisons and prepared publication candidates | New candidate file or directory, not tracked release state; preserve source hashes, review and publication boundary | Review strict legacy Variant Usage filename and candidate consumers before new-path cutover |
| Rules interaction checklist, full-asset transfer ZIP, explicitly selected work-tree ZIP, scenario SVG, generated Army/Rules/ITS databases and web fonts | Deliberate regeneration or reviewed publication; may replace the selected artifact, with their own validation/recovery contract | Do not apply generic receipt-only semantics; protect serving and published three-database set |
| Browser host profile, agent coordination registry, production metrics history and deployment state | Explicitly mutable host/runtime state or append-only records, not immutable audit files | Preserve operator-owned locations, volumes and coordination concurrency semantics |
| Read-only stdout audits/benchmarks, temporary build/pytest scratch, installed-wheel smoke | No retained file, or disposable output under a controlled temporary lifecycle | Avoid treating these as historical evidence or migrating arbitrary temp directories |

**Closeout decision:** The maintained, known **writer-safety
and report-classification sub-scope** of L2 is complete at this
bounded checkpoint, including the additional core CLI and
snapshot-provenance writers. This **does not satisfy the
full L2 phase exit** at
[the execution definition](#l2--migrate-writers-readers-and-cross-repository-handoffs).
L2 remains **OPEN** for the still-gated reader/default
migration: exact Army/Wiki/Symbol producer and consumer
path maps, Windows Syncthing and Linux staging/activation
acceptance, external handoff contract checks, ambiguous
legacy-vs-`local/` input selection and separately approved
reversible M-copy/cutover. The 19 inaccessible
historical `reports/` directories and independent
backup/restore evidence are unresolved. No source paths,
ignored originals, historical reports, build databases
or container volumes were relocated or deleted; no
T retirement, M copy/delete or broad L4 tool move is
authorized by this closeout. The next non-destructive
work should produce a **reader/producer path cutover
decision package** from current verified paths; execution
of any physical migration remains separately gated.

**Validation:** Windows hermetic focused suites passed
`test_run_checks` **116 passed / 1 skipped**,
`test_build_full_asset_bundle` **8/8**,
`test_stage_full_asset_bundle` **8/8**,
`test_test_sections` **15/15**,
`test_app_cli` **30/30**,
`test_snapshot_provenance` **23/23**,
`test_army_snapshot_source` **6/6** and
`test_export_symbol_source_plan` **6/6**.
Total **212 passed, 1 skipped, zero failures**.
Regression cases cover early/late transcript and source
report collisions, duplicate one-second default,
symlink refusal, preservation of competing ZIP staging,
deliberately replaceable final bundle bytes, no-clobber
snapshot provenance, identical concurrent manifest
idempotency and pinned consumer compatibility.
Targeted Ruff and repository Pyright (zero
errors/warnings), docs lint/links/backlog and
`git diff --check` passed. The focused pass is **not**
full-suite or hosted exact-SHA CI, Linux parity,
live acquisition, live Docker/full-assets handoff
or source/backup restoration validation.

### Eighteenth bounded L2 checkpoint — reader/producer path-cutover decision package (2026-11-13)

**Status:** **Read-only planning completed; no path migration approved or
executed.** Baseline: clean `dev/tooling-workspace-cleanup` at
`df65f6b1e2a75d21d50975392f5eeb1d544699e4`. The preceding
[writer closeout](#seventeenth-bounded-l2-writer-classification-and-remaining-output-safety-closeout-2026-11-13)
covers no-clobber evidence, but *not* read-side path changes. This
checkpoint traced actual CLI defaults, source-plan and manifest
interfaces, source-audit pins and Syncthing activation across four
repositories; it does not claim a complete private-file inventory.

**Independent source checkouts inspected without editing:**
`InfinityDB-army-acquisition` `main` at
`7926c0f3968ae60915f48a443f8327718e9787ec`;
`InfinityDB-wiki-acquisition` `main` at
`2fd89373afc1c3bd5dab3c74ee96da114412b168`;
`InfinityDB-symbol-tools` `main` at
`54700b78a7650b6299bd0d87bbb05da6c8f52815`. All three were clean.
`InfinityDB-products` contains separate ongoing product and
miniature changes; **exclude it from this source-path cutover**.
These revisions describe the inspected code, not current hosted CI
or an approved multi-repository commit set.

#### Exact current and *proposed* path mapping

Paths are repository-relative unless an external staging root is
shown. Proposed destinations describe a potential future family
cutover only; no new default, prefix match or fallback is active.

| Family / owner | Current production or development contract | Proposed destination, not yet activated | Consumers and required adaptation |
| --- | --- | --- | --- |
| **A1 Army original ZIP** — `InfinityDB-army-acquisition` | `infinity-army-snapshot [data/raw] --manifest-dir data/manifests/snapshots`; immutable `JSON YYYYMMDD-HHMMSS[-N].zip` | `local/data/raw/army/<original ZIP basename>` | `src/infinity_army_data/cli.py:DEFAULT_RAW_DIRECTORY` and `latest_snapshot`; `tools.army_snapshot_source.resolve_army_snapshot`; symbol source/override plan exports; Syncthing `raw/` sender/receiver |
| **A2 provenance pair** — three acquisition packages | `data/manifests/snapshots/<archive stem>.json` | `local/data/manifests/snapshots/<archive stem>.json` | `tools.activate_synced_assets` assumes the current staged `snapshots/` directory and `snapshot.archive.path` can be mapped to `data/raw/` or `data/wiki/`; `load_snapshot_manifest(archive=...)` independently validates both hashes |
| **W1 Wiki / Human Sphere ZIPs** — `InfinityDB-wiki-acquisition` | `--root data/wiki --work-root data/work/wiki --manifest-dir data/manifests/snapshots`; `WIKI-en`, `WIKI-es` and `HUMAN-SPHERE` archive stems | `local/data/wiki/<original ZIP basename>` and `local/data/work/wiki/<run-specific crawl>` | Preserve distinct site/language identities and incomplete-crawl work; explicit `--root`, `--work-root`, `--resume-work` consumers; staged `wiki/` folder and snapshot-manifest mapping |
| **P1 PDF originals** — manually sourced official material | `data/pdf/rules/`, `data/pdf/faq/`, `data/pdf/its/`, `data/pdf/legacy/` | Same relative subtrees under `local/data/pdf/` | Tracked `data/curated/rules/*.json` `localPath` values and `config/validation/*.json` hash pins, `audit_1_0_reference_inputs`, `audit_pdf_revision_deltas` and other PDF readers; Syncthing `pdf/` and `--file data/pdf/...` |
| **S1 reviewed symbol overrides** — external `InfinityDB-symbol-tools` | Main checkout `image_overrides/`, Syncthing receiver `image-overrides/`; symbol-tools examples use explicit `--overrides local/image_overrides` in the *producer checkout* | Main `local/data/symbols/overrides/` (exact member basenames retained) | `activate_synced_assets` has fixed `image_overrides` prefix; producer override lookups contain relative override paths, not raw ZIP paths; explicit `--overrides` selection and source hashes need separate producer contract acceptance |
| **S2 raw/effective symbol handoff** | Producer defaults `data/raw/symbols/`, `data/manifests/snapshots/`; separate `.raw-report.json`; effective ZIP and processing receipts are producer-managed | For accepted consumer imports, `local/handoffs/symbol-tools/<source-SHA-or-run-id>/` and, only if needed, `local/data/raw/symbols/` | InfinityDB `export_symbol_source_plan`, `export_symbol_override_lookups`, `verify_raw_symbol_handoff` and later processed-publication verifiers all require explicit, hash-pinned selected files. Do **not** infer a complete `army-symbol-build.json` or browser publication from the raw ZIP |
| **B1 ignored build work** — InfinityDB | `data/work/build/`, `data/work/its/` and other explicitly selected scratch | `local/data/work/build/` or source-specific `local/work/` only after builder/fixture review | Complete Army/Rules/ITS build, temporary raw sibling, source normalization, standalone `build-rules`, and tests; keep current defaults until a complete-set build on both platforms proves parity |
| **E1 output evidence** — multiple tools | Root `reports/`, `data/reports/`, `data/logs/`, historical `docs/audits/` | New reports in domain-scoped `local/validation/`, `local/research/`, `local/performance/` and `local/operations/` | New receipts already recommend `local/`; existing archives, recovery logs and 19 inaccessible directories need separate retention, ownership and ACL decisions; **not part of a source ZIP migration** |
| **X1 tracked serving/publication** — InfinityDB | `data/generated/{army.db,rules_n5.db,its_18.db}`, `data/curated/`, `data/manifests/symbol-publication.json` | **No move** | Three-file build and serving, Docker, cached revision, source-reviewed rules, processed SVG publication and exact-SHA release acceptance |

The conceptual `local/data/` destinations follow the accepted P
conventions. Do **not** impose InfinityDB's target layout as an
automatic change to each standalone producer repository's own
`data/` and `local/` conventions. Its selected *handoff artifacts*
must be validated before importing them; no private folders are
implicitly shared, mounted or synchronized between repositories.

#### Critical reader/provenance compatibility findings

1. **Archive location is not a portable activation authority.**
   The immutable v3 snapshot contract stores
   `snapshot.archive.{name,sha256}` and
   `snapshot.contentSha256`. The generic verifier checks those
   hashes against an *explicitly provided* archive, treating a
   producer-relative `archive.path` as informational. In contrast,
   `tools/activate_synced_assets.py:_snapshot` requires
   `archive["path"]`, only accepts `data/raw/` or
   `data/wiki/`, and uses it to choose a fixed `raw/` or
   `wiki/` receiver mapping. A producer run outside the selected
   project root may omit the optional path entirely. Merely changing
   the producer destination to `local/data/` therefore **breaks
   activation**. Proposed fix for a separately reviewed change:
   select an explicit *source layout* and map the validated archive
   basename/type to a configured staging family, retaining the
   original manifest bytes and both hashes. Accept old/new declared
   path forms only under explicit layout selection; never derive
   absolute host paths from untrusted manifest text.
2. **Latest-archive discovery is not migration-safe.**
   `infinity_army_data.cli.latest_snapshot` currently searches
   `data/raw/*.zip` and chooses by filesystem mtime (then name).
   Copies may alter mtimes; when legacy and local roots both contain
   ZIPs, a silent newest-file search across both can select the
   wrong source. Pilot all new-layout operations with a **selected
   exact archive and manifest**. The eventual default cutover
   must reject ambiguous dual-root discovery and verify source
   revision, metadata, ZIP SHA-256 and manifest identity.
3. **Source-pinned PDF `localPath` is tracked evidence, not a
   disposable link.** Multiple `data/curated/rules/` and
   `config/validation/` records refer to exact `data/pdf/`
   relative paths and SHA-256 values; some auditors enforce a
   `data/pdf/rules/` prefix. Relocating a PDF without a reviewed
   path-binding change may mark genuine evidence missing, or break
   source validation. Preserve original PDFs and hash records.
   Updating tracked path labels requires an independent schema,
   source identity, direct-reader and reference-report review.
4. **Provenance code has multiple owners after extraction.**
   InfinityDB's `src/infinity_db/snapshot_provenance.py` now
   publishes manifest files with an exclusive stage plus
   non-replacing hard link. As inspected here, the standalone
   Army/Wiki/Symbol repositories still use a fixed `.json.tmp`
   followed by `Path.replace`. Their v3 *data format* is compatible,
   but their concurrent-writer safety behavior is not yet aligned.
   Plan an explicit, independently tested change in each producer
   (rather than importing InfinityDB runtime code), including
   Windows/Linux hard-link support and identical-versus-different
   output races; preserve the original archive's basename and
   manifest bytes. No external repository was edited in this pass.
5. **Source copies are not a Syncthing or backup cutover.**
   Current Windows Send Only and Linux Receive Only configuration
   uses five legacy folders: `data/raw`→`raw/`,
   `data/wiki`→`wiki/`, `data/pdf`→`pdf/`,
   `data/manifests/snapshots`→`snapshots/`,
   `image_overrides`→`image-overrides/`.
   `INFINITYDB_SYNC_STAGING_ROOT` controls the Linux worker's
   external staging root; activation defaults to a dry run and
   requires `--apply` for checkout writes. Its real ACL,
   synchronization state, backup versioning and source snapshots
   **have not been checked now**. Do not rename Syncthing folders,
   make the worker a writer or change a sender root as part of a
   reader-only patch. Syncthing is not an independent backup.

#### Dependency order and narrowly bounded future acceptance

| Gate | Next operation | Acceptance before advancing |
| --- | --- | --- |
| **R1 — read-only Army selection** | Add *explicit*, independently hash-verified new-root input selection to consumer code; legacy default remains unchanged. This is the first recommended implementation slice | Test identical source at both roots, mismatched SHA-256, missing/ambiguous metadata, selected vs newest semantics, no-network normal build, three-database identity from an explicitly selected archive, Windows and Linux fixture parity |
| **R2 — provenance contract** | Align standalone Army/Wiki/Symbol manifest publication with no-replace/idempotent semantics; define schema-neutral path handling for an explicit consumer-selected archive | Producer mock acquisitions on pinned revisions; manifest byte/hash comparison with InfinityDB; successful same/different collision tests on each host; no fallback and no deletion of other producer's output |
| **R3 — reader/activation selection** | Design and test a separately configured legacy/local source-layout mapping, leaving the current five staged folders and destinations working | Hermetic staged-pair tests for both layouts, malformed/outside-root paths, duplicate names, symlinks, hash conflicts, inaccessible staging, no writes in verify/preview; explicit `--apply` only against a disposable test checkout |
| **R4 — PDFs / overrides** | Inventory each pinned source and owner, then prepare a per-family path-binding patch; keep source labels and validation hashes stable until accepted | Review curated `localPath` semantics and fixed-prefix audits; compare PDF/override hashes; preserve read-only source checks, reviewed lookups and the symbol processing/publication distinction |
| **R5 — operations and source synchronization** | Refresh exact Windows sender/Linux receiver/ACL facts and prepare one reversible M-copy proposal *after* reader changes | Independent backups and **tested restore**; source/manifest SHA inventory, source-selection conflict scan, paused/verified Syncthing during any root change, Linux worker read-only ACL and dry-run activation, rollback plan |
| **R6 — physical cutover / cleanup** | Only with separate family-specific approval, copy and verify the eligible ignored originals; later decide deletion/retirement independently | Identical hashes/manifest contents, all named consumers switched, Windows/Linux checks, Syncthing and backup recovery accepted; do not alter the tracked three-file serving contract |

**No gate above is authorized merely by this decision package.**
R1 can begin separately as a reversible code-and-test slice because
it does not require physical file moves or producer modifications.
R2–R5 should not be bundled as an unreviewed path rewrite.
An M-copy decision needs *exact* per-file old/new paths, hashes,
matched source/provenance, access and verified recovery. M-delete
is a later decision with independent sign-off. L4 tool relocation
and tracked T retirements remain separately gated.

**Focused current-contract verification:** Windows hermetic tests
`tests/test_activate_synced_assets.py` **15 passed / 3 skipped**,
`tests/test_cli.py` **7 passed**,
`tests/test_army_snapshot_source.py` **6 passed** and
`tests/test_export_symbol_source_plan.py` **6 passed**:
**34 passed, 3 skipped; no failures**. These prove only the
legacy/explicit interfaces exercised by those fixtures; they
are **not** a completed new-layout cutover, producer-network
test, external Syncthing snapshot, Linux parity or full CI.
No current output default, producer package, tracked source
record, ignored source byte, repository linkage or Git branch
was changed by the inventory itself.

**L2 state: OPEN.** The writer-safety sub-scope has closed.
This checkpoint supplies the non-destructive consumer/producer
decision basis for future R1–R6 acceptance and is *not*
the L2 exit described under
[execution phases](#l2--migrate-writers-readers-and-cross-repository-handoffs).

### Nineteenth bounded L2 checkpoint — R1 explicit Army source selection (2026-11-13)

**R1 implementation completed; Windows and Linux fixture acceptance
verified at the same SHA. Hosted CI and real-source transfer are separate.**
Starting baseline: clean `dev/tooling-workspace-cleanup` at
`67df86067578c4d065011a6dbd08c561beba062c`. This change
implemented the first **non-destructive** gate from the
[eighteenth L2 path decision](#eighteenth-bounded-l2-checkpoint--readerproducer-path-cutover-decision-package-2026-11-13).
No ignored source archive, snapshot manifest, tracked runtime SQLite
publication, producer checkout, Syncthing directory, service or default
was relocated.

**Explicit application CLI:** The installed `infinity-db build`
now accepts `--snapshot-manifest PATH` **only together with an explicit
Army ZIP positional `source`**. The existing default
`infinity-db build --compact` still chooses the newest
`data/raw/*.zip` by current mtime ordering. The standalone
`infinity-army build` interface and legacy `--metadata` behavior
remain unchanged. The pinned mode rejects `--metadata` instead of
silently switching source authority. `--db-dir` continues to select
the *complete* three-file destination independently from serving.

**Single verifier, no runtime dependency on `tools/`:**
`src/infinity_db/army_snapshot_source.py` now owns the offline
Army source resolver shared by application builds and development
tools. The old `tools.army_snapshot_source` path remains a
backward-compatible import facade for symbol source-plan export
and existing callers. Pinned mode requires version-3 provenance,
exact selected ZIP and manifest basenames, `army` source type,
`en` language, both archive and logical-content SHA-256, valid
ZIP/metadata member, encoded Army source-revision date,
manifest `dataChangedOn` and document count. The
`snapshot.archive.path` field remains **informational** and is
never used to resolve a different source location; it may still
name the producer's legacy layout when the exact same archive is
explicitly selected under `local/data/raw/army/`.

**Metadata/source ambiguity:** The ZIP's own `metadata.json`
is authoritative in the pinned mode. A sidecar with identical
bytes remains compatible with the existing ingestion routine;
a conflicting, non-file or symlinked sidecar fails *before*
database work. An explicitly selected external `--metadata`
cannot accompany `--snapshot-manifest`. Source/hash/manifest
checks execute before creating build work or touching outputs;
they repeat after generating the complete set and before
replacement. The manifest's own SHA-256 is compared across
the run in addition to the normal maintained-input envelope,
so an altered source URL/manifest cannot silently pass if the
ZIP hash has not changed. Earlier accepted database files
are preserved on prepublication failure.

**Read-only sample invocation:**

```powershell
infinity-db build "local/data/raw/army/JSON EXAMPLE.zip" --snapshot-manifest "local/data/manifests/snapshots/JSON EXAMPLE.json" --db-dir "local/work/data/army-selection/RUN_ID" --compact
```

This is a **future-layout example**; the files are not
automatically present there. Run it only with an actually
verified ZIP/manifest pair and a disposable `--db-dir`.
Current release symbol-publication input pins, reviewed data
sources, offline normalization and the exact three-database
publish boundary remain mandatory. No extra search across
both source roots or implicit conversion of legacy manifests
to v3 was added.

**Windows focused validation:** `test_army_snapshot_source`
**17/17**, `test_cli` **7/7**, and
`test_database_set_builder` **26/26**,
`test_export_symbol_source_plan` **6/6**,
`test_app_cli` **30/30**, and
`test_snapshot_provenance` **23/23** passed:
**109 tests passed, zero failed/skipped**. The complete
builder fixture tested **two actual three-file set builds** from
byte-identical legacy and `local/data` ZIP/provenance paths:
all three resulting SHA-256 values and recorded build-set
identity matched. It also tested manifest mutation after
generation, archive tampering, version-2 provenance exclusion,
non-English identity rejection, sidecar disagreement,
explicit-metadata conflict, missing positional source,
no implicit latest-file discovery, and unchanged legacy
parser defaults. Pyright reported zero errors/warnings;
targeted Ruff and repository docs/diff checks passed.
The symbol source-plan and application CLI consumers passed
their focused Windows suites.

**Linux exact-SHA fixture acceptance (2026-11-13):**
The detached `linux-dev` validation checkout explicitly fetched
and selected `8de09b277e579bd8cb942c6aba242bfe4f71ceca`
without changing a named branch. On this exact SHA, Linux passed
the same six suites as Windows: **17+26+7+6+30+23 =
109/109 tests**, including two complete three-database builds
from identical legacy and proposed `local/data/` source bytes,
with matching build identities/output hashes. The checkout was
not synchronized with ignored source folders. Hosted exact-SHA
CI, real source-provenance selection and cross-host
manifest/path transfer are **not certified** by synthetic
SQLite fixtures. R2–R6 and separately approved T/M remain
independent gates.

**L2 state: OPEN.** R1 is an opt-in reader capability, not
a producer-path or physical-data migration.

### Twentieth bounded L2 checkpoint — R2 snapshot producer publication alignment (2026-11-13)

**R2 implementation and Windows/Linux fixture acceptance: complete.**
The standalone Army, Wiki and Symbol writers and InfinityDB now share
byte-exact, non-replacing v3 manifest publication. The first producer
publication commits are superseded by these reviewed transaction fixes:

| Producer owner | R2 first-slice SHA | Accepted transaction SHA |
| --- | --- | --- |
| Army API acquisition | `95bfb2de8ed14849062d9f607d8ef81c8284da17` | `6d6789859e945d26a7a3fe3da275615103a22490` |
| Infinity Wiki / Human Sphere acquisition | `f82f809e255031fc091d85d82ac88042570c411f` | `7338317bdc450d8b9d641063e4e49e7ec9d4fa70` |
| Symbol acquisition and processing | `f03ebd2a3983386fc7e663d9b2d8fbcac9019efc` | `542faba40872221f4b5e78049912c50a95c136b4` |

**Current contract:** The [data lifecycle owner](../data/README.md#snapshot-provenance-contract)
defines canonical UTF-8/LF bytes, exclusive sibling staging, non-replacing
hard-link publication and the distinction between idempotent direct writes
and newly owned transaction outputs. The optional `require_new=True`
writer argument is used by Army acquisition, Wiki acquisition, raw Symbol
acquisition and effective Symbol processing. A competing identical manifest
is reusable by a direct writer but rejected by these rollback-capable
transactions. CRLF is not byte-identical to LF. Source ZIP creation remains
exclusive. The four provenance implementations have identical source bytes,
SHA-256 `92c55b7a5b021382060ea8948c71ebb425627c12c355c8c44c4ba351a14ed66c`.

**Path compatibility:** No schema or CLI default changed. The receiver
explicitly selects an archive and manifest; an embedded producer-relative
path remains informational and is never used to discover a different
input. The same immutable pair can be verified at a different local
layout without rewriting its JSON. Pinned Army build selection retains
its stronger original-basename, Army/en and source-revision checks.

**Windows/Linux acceptance:** Each full producer suite used offline mock
acquisition and temporary artifacts. Army passed **56/56** on each host;
Wiki passed **66/66**; Symbol passed **116 with one filesystem case-collision
skip on Windows**, and **117/117 on Linux**. Each producer run also passed
seven subtests. Caller race tests cover both identical and conflicting
manifest winners, plus a source ZIP that appears during exclusive
publication. Rollback preserves the winner's bytes, removes only the
loser's newly owned outputs and preserves incomplete Wiki crawl evidence.
Missing hard-link support has no overwrite fallback. Dependency and Git
whitespace checks passed in every producer.

InfinityDB's four focused suites (`test_snapshot_manifest_publication`,
`test_snapshot_provenance`, `test_army_snapshot_source`,
`test_database_set_builder`) passed **77/77 plus seven subtests on each
host**, including two complete three-database builds from equivalent
explicit source layouts. Targeted Ruff, full Pyright and docs checks passed.
Linux used isolated, hash-inventoried exports, not a moved interactive or
worker checkout. The final producer export SHA-256 was
`072afa38a20b324263c16499b8e0daa7393ce2581b63e306dc4dbd90ac984861`;
its source/test bytes were verified unchanged against the delivered commits.
Consumer source/test bytes were unchanged from their Windows/Linux runs.

**Cross-repository handoff:** A deterministic synthetic ZIP produced
byte-identical manifests in all four implementations on Windows and Linux
for Army, EN Wiki, ES Wiki, Human Sphere and Symbols. Every pair was
verified by the pinned InfinityDB consumer after copying to a different
local layout, without changing producer-relative provenance, and altered
ZIP copies were rejected. The fixture ZIP SHA-256 was
`066236db8f4f9cda823bb882d2f41063696125ea396b6e6db0c3b2b47fb9a934`;
the Army manifest SHA-256 was
`5d45c403ebc093e90f74eb7c25b8498f6f7fd73a0545306b803e8b25a88c5212`.
This is hermetic format/path conformance, not a live source acquisition,
physical migration or production graphical-fidelity certification.

**Hosted acceptance:** The exact producer pushes started Army run
[43424252433](https://github.com/frankysan/InfinityDB-army-acquisition/actions/runs/43424252433),
Wiki run [43424260083](https://github.com/frankysan/InfinityDB-wiki-acquisition/actions/runs/43424260083)
and Symbol run [43424267587](https://github.com/frankysan/InfinityDB-symbol-tools/actions/runs/43424267587).
All three runs completed successfully on their exact producer SHAs:
**nine successful jobs**, covering Windows, Ubuntu and macOS with Python 3.11.
InfinityDB development-branch CI and final release acceptance are independent.

**L2 state: OPEN.** R2's producer/consumer contract work is complete;
R3 staged activation, R4 pinned PDF/override migration and R5–R6 private-data,
Syncthing and backup cutover remain separately gated. No ignored source,
manifest, private override, Syncthing configuration or tracked runtime
database was moved or republished.

### Twenty-first bounded L2 checkpoint — R3 explicit staged snapshot layouts (2026-11-13)

**R3 implementation and Windows/Linux fixture acceptance: complete.**
Starting baseline was clean `dev/tooling-workspace-cleanup` at
`45c5308d5852912aab80ae23922db4c0caede0b7`. The maintained
[staged-asset runbook](syncthing-assets.md#explicit-snapshot-layouts) owns
the current CLI and mapping contract; version-1
[layout policy](../config/operations/synced-asset-layouts.json) owns the
reviewed family paths. The layout implementation changed no default, sender
folder, receiver permission, producer input or tracked runtime database.
The subsequent same-source CI freshness repair is recorded below.

The new explicit `--layout local` selects Army, Wiki/Human Sphere and raw
Symbol archives by configured staged family plus original basename, and
plans their matching JSON under `local/data/manifests/snapshots/`.
Producer-relative paths remain informational in this mode. The default
`legacy` mode retains its allowed legacy path-label translation, including
nested raw-symbol paths; there is no automatic dual-root search. Both modes
validate complete supported provenance (v1/v2/v3), applicable archive/content
hashes and matching archive/manifest names. Duplicate selections, malformed
or duplicate-key policy, unsafe/outside-family paths, symlinks, unreadable
staging, stale source bytes and destination conflicts fail closed. Copy
publication remains non-replacing; multi-file activation is not a transaction.
PDF and override destinations remain unchanged in both layouts for R4 review.

**Focused acceptance:** Windows passed **146 tests, four skips** across
`test_activate_synced_assets`, `test_snapshot_provenance`,
`test_army_snapshot_source` and `test_export_symbol_source_plan`. The skips
were three real-symlink fixtures unavailable without Windows privileges and
one case-colliding filename fixture unsupported by that filesystem. Linux
passed the same **150/150 tests with no skips**, including those real
filesystem cases. Within that batch, activation alone accounts for
**100 passed / four skipped on Windows** and **104/104 on Linux**.
Source guards were also exercised with portable mocked symlink refusals on
both hosts. Targeted Ruff, full Pyright, documentation and whitespace checks
passed. All apply operations used disposable fixture checkouts.

A separate deterministic fixture receipt compared legacy/local applied
archive and manifest bytes for Army, Wiki and raw Symbols. All three pairs
matched across Windows and Linux, retaining exact producer JSON bytes and
leaving source files unchanged. The shared fixture ZIP SHA-256 was
`989e780a897a6806cbab95ee2dceebafbd9eaaf370d55ad9325e886c7054c600`;
the Army manifest SHA-256 was
`6849e9b8b3178391fcd41c2b50c60672f68f10d2e6c18bdc1a9ccfb17f705b0c`.
Linux used an isolated, hash-inventoried export with archive SHA-256
`cafbce5a32a647252248acd9255fc96c913160dc74312f1895b9de4b53f13d42`,
not a moved worker/interactive checkout. This establishes fixture portability,
not real source synchronization, tested restore, live ACL acceptance or
hosted/exact-release validation. Private receipts and the bounded parity
probe may be retired after their acceptance/recovery purpose ends; normal
tests do not depend on them.

**Post-push CI freshness repair:** Hosted Deployment smoke at the R3 layout
commit `4e88bfb4ed3622f29d208ab1bb37a91a08082f7d` failed its existing
build-input freshness gate; Source matrix jobs reported the same cause.
The tracked runtime envelope predated five source files changed by R1/R2,
starting with `src/infinity_army_data/cli.py`. R3 changes no `src/` inputs.
Installed wheel smoke passed on that revision. The freshness gate was retained.

The complete three-database set was rebuilt twice through the integrated
builder from the unchanged, v3-verified `JSON 20260929-114335.zip`, SHA-256
`f103a7afd02e68d845cc9ce38b1948f46914676bbc6a5e6b790d0a04148b6c75`.
The candidate and refreshed tracked output were byte-identical. All gameplay
table schemas and rows remained unchanged; differences were confined to
build provenance and generation/hash bindings in metadata. All **41 current
semantic API/browser-contract routes** matched the previous tracked set.
The new build-set identity is
`14fffd275775263ac8950a86f42fa9db6e16d91e4c927eff58d4f9b64ea41ee4`.
Army SHA-256 is
`98cc82dae13449efa814b3aa3d166db123c075662d224dcfe887048cfd9eb7f3`;
Rules SHA-256 is
`c1b8ee3078f7fcf9ef692fd7e73526c46f3bface7d32b541a05672c6d3b21908`.
ITS remained byte-identical. The full deployment-artifact verifier, including
**808/808 published SVGs and 807/807 browser references**, passed on Windows
and the hash-verified isolated Linux copy. This repairs the stale development
publication. The database-set, deployment-artifact and semantic-baseline suites
also passed **46/46 on each host, with no skips**. Hosted checks of the
replacement commit `39a1eb8fb4eb15183a4f05e59e2bec42070f38ee` subsequently
passed: [Source checks](https://github.com/frankysan/InfinityDB/actions/runs/43429270312)
(all eight jobs, including native matrices and deterministic outputs),
[Installed wheel smoke](https://github.com/frankysan/InfinityDB/actions/runs/43429270332)
and [Deployment smoke](https://github.com/frankysan/InfinityDB/actions/runs/43429270418).
Final release acceptance remains separate.

**L2 state: OPEN.** R1–R3 reader/producer contracts are implemented and have
Windows/Linux fixture acceptance. R4 now owns the next bounded inventory and
per-family path-binding review for pinned PDFs/overrides. R5 operational
evidence and R6 physical copying/cleanup still need their separate approvals.
There was no live source activation, source move, Syncthing reconfiguration,
backup/restore claim, production publication or deployment in R3.

### Twenty-second bounded L2 checkpoint — R4 inventory and first PDF binding (2026-11-13)

**R4 state: OPEN. Inventory and the first read-only PDF-reader binding are
implemented; other consumers and physical migration are not accepted.**
Starting baseline: clean `dev/tooling-workspace-cleanup` at
`39a1eb8fb4eb15183a4f05e59e2bec42070f38ee`, with the three exact-SHA hosted
workflows above successful. No private PDF/SVG, source declaration,
published source row, symbol lookup or runtime database was changed here.

**Measured Windows inventory:** A read-only scan found **75 PDFs** and
**108 SVG overrides**, plus **13 auxiliary files**. The 75 PDFs comprise
12 under `rules/`, four under `faq/`, three under `its/` and 56 under
`legacy/`. The `scenarios/` directory has no files in this inventory.
The override families contain four characteristic, nine faction, five Order,
25 Peripheral and 65 Unit SVGs. The two Syncthing marker files, nine desktop
metadata files and two operator indexes (`sources.txt`, `overrides.txt`)
are separately inventoried and excluded from the PDF/SVG proposal; none
is presumed disposable or eligible to copy with a source family.

Maintained JSON pins **eight distinct PDF paths**. The published Rules
`sources` table contains **12 PDF rows covering six of those paths**;
the other two are the separately inventoried N4 annexes. Every supplied
pin matches the current bytes, without conflicting declarations:

| Recorded PDF label under `data/pdf/` | Maintained pin/source owner |
| --- | --- |
| `rules/n5-rules-v5.3-en.pdf` | Core/Hacking curation and conditional-declaration evidence |
| `rules/n5-rules-v5.3-es.pdf` | Core/Hacking curation |
| `faq/n5-faq-v0.0-en.pdf` | Core historical FAQ source |
| `faq/n5-faq-v0.1-en.pdf` | FAQ curation and question inventory |
| `faq/n5-faq-v0.1-es.pdf` | FAQ curation and question inventory |
| `its/its-18-rules-v2026.09.01-en.pdf` | ITS curation and Reinforcements applicability review |
| `rules/reinforcement-rules-en.pdf` | Historical Reinforcements source inventory |
| `rules/reinforcement-rules-es.pdf` | Historical Reinforcements source inventory |

The two N4 annex PDFs physically remain under `rules/`; that location does
not confer N5 authority. Other local PDFs include research/history with no
pin in those executable owners, some with separate historical hashes in
the [source-history inventory](n5-source-history.md#local-pdf-revision-inventory-2026-11-06).
Neither naming nor absence from the current pin set authorizes replacement,
renaming or deletion. No PDF content or artwork was republished by this scan.

The private inventory records exact per-file bytes, SHA-256, candidate path,
JSON-pointer/SQLite owner and candidate-destination status. Its SHA-256 is
`95d94a8d8c6b359deb507552926e7ec7ba2da936e4d626a68685ff4daacab14b`.
All proposed destinations were absent. A separate **proposal-only** review
lists the 183 PDFs/SVGs with exact old/new paths and hashes, excludes the
13 auxiliary files, and marks every copy/delete decision unapproved. It is
not an M-copy manifest approval or a backup/restore record. The bounded
inventory script and private receipts can be retired after their R4 review
and recovery purpose ends; clean-checkout tools never depend on them.

**First PDF reader:** The [curated-data owner](../data/curated/README.md#explicit-physical-pdf-bindings-for-research)
defines the implemented binding contract. The new research-only helper
`tools.research.source_paths.pinned_pdf_path` reads validated
`config/operations/research-source-layouts.json`. It retains canonical
`data/pdf/...` provenance while explicitly selecting either the unchanged
legacy location or `local/data/pdf/...`. It verifies the existing SHA-256,
rejects links/reparse points and unreadable/unsafe paths, and never searches
another root or writes a file. Historical absence remains not supplied.

`verify_reinforcements_inputs` accepts an optional `source_layout` API
keyword. `audit_reinforcements_applicability` exposes `--source-layout`,
applying it to both historical and current Core/ITS PDF evidence. Default
selection remains `legacy`. Synthetic old/new-layout audits retain identical
historical source records, labels, byte pins, current-reference counts and
authority outcomes. A PDF is hashed again before interpreting its in-memory
bytes. All eight real declared PDFs verify in the default layout; selecting
the currently absent local copies never falls back. The existing live
applicability audit verifies two current and two historical PDFs while
preserving its existing authority findings. This work introduces no new
rules interpretation or publication decision.

**Override boundary:** At producer revision
`542faba40872221f4b5e78049912c50a95c136b4`, the external
`InfinityDB-symbol-tools` enumerator recognized exactly the same **108 relative
SVG paths and hashes** as this inventory. Its existing explicit `--overrides`
root is separate from reviewed relative lookup paths and raw ZIP member paths.
No producer code or lookup was edited. This establishes file/interface identity,
not artwork approval, processing receipt validity or a new publication.

| Consumer family | Current disposition and remaining R4 work |
| --- | --- |
| Reinforcements historical/current evidence | First explicit PDF binding implemented; source labels and pins unchanged |
| `report_reference_baseline` | Still joins physical paths to the report root; add explicit PDF binding without changing runtime-database selection or emitted source identity |
| `audit_pdf_revision_deltas` | Review its fixed `SOURCE` root and ignored revision inventory; retain relative pair labels, hashes and chronology |
| Direct PDF auditors and source-dependent tests | Inventory fixed defaults versus existing explicit PDF arguments; adapt only required implicit readers and prerequisite selection |
| Override producer | Existing root argument is portable; retain exact member basenames and hash-bound relative lookups |
| Staged PDF/override activation | R3 still retains legacy file destinations in both layouts; review per-family mapping separately before changing this contract |

**Validation:** The PDF-binding/source-evidence/applicability batch passed
**108 tests, two skips on Windows** (real symlink privilege unavailable) and
**108 tests, two skips on isolated Linux** (ignored official PDFs absent).
Linux exercised the real symlink cases; both hosts exercised portable link,
reparse-point, hash, missing-layout, policy and provenance guards. Actual
private PDF hashes and page checks were verified on Windows, not inferred
from Linux skips. The fixture export contained no private PDF/SVG originals;
its SHA-256 was
`f55b0c5a1527221bebba14d6e4688fa70f6c1d0a338d6fb3199b3ba245190b05`.
The standalone override module passed **seven tests, one filesystem skip**
on Windows. Targeted Ruff, Pyright, docs and 44 release-note/section tests
passed. All 196 original source/auxiliary file hashes and the existing
runtime build envelope were rechecked unchanged.

**Next R4 slice:** Extend the explicit PDF binding to the reference reporter
and review the revision-delta/direct-reader contracts above. Keep R4 open
until the affected per-family consumers and validation are accepted. R5
operational evidence and R6 copying/deletion retain their separate gates;
no source-label rewrite or physical relocation is authorized by this checkpoint.

### Twenty-third bounded L2 checkpoint — R4 read-only reference and revision-delta PDF consumers (2026-11-13)

**Scope:** Two additional research consumers now accept an explicit
`--source-layout legacy|local` physical PDF binding, retaining `legacy` as the
default. Both continue to report canonical `data/pdf/...` source identities.
No published source rows, annotated citations, version chronology, source hash
pins, tracked three-database serving input, producer or private PDF bytes were
rewritten. R4 remains open for other direct readers and staged PDF/override
activation; R5 operational recovery and R6 physical copy/delete gates remain
separate and unapproved.

- `tools.report_reference_baseline` resolves only PDF source groups under
  `local/data/pdf/...` when explicitly selected, using the existing reviewed
  source SHA-256. It does not scan the legacy root as a fallback. Absent local
  sources retain missing status, while conflicting/unpinned PDF source hashes
  and supplied altered bytes reject the opt-in report. Non-PDF source and
  runtime publication selection are unchanged; default legacy status and
  mismatch reporting remain compatible.
- `tools.audit_pdf_revision_deltas` resolves each exact selected PDF from
  its existing private pin inventory against the declared physical layout,
  checks hash identity before text extraction, and checks extracted bytes
  again. The pair labels and comparison report fields remain unchanged.
  An absent or conflicting selected PDF blocks a fresh report; no alternate
  layout is consulted and prior report files remain protected by exclusive
  creation. No private PDF inventory or existing report has been modified.
- The canonical [curated-data policy](../data/curated/README.md#explicit-physical-pdf-bindings-for-research)
  and [testing contract](testing.md) describe both selectors. The new
  hermetic regression fixtures cover source labels, selected-layout parity,
  no fallback, mismatched hashes and report non-overwrite behavior.

**Windows focused validation:** `test_report_reference_baseline.py`
**81 passed / two skipped**, `test_specialized_audit_receipts.py` **34 passed**,
`test_research_source_paths.py` **40 passed / two skipped**, and
`test_source_coverage_dispositions.py` **23 passed**:
**178 passed, four skipped, zero failures**. The two skips in each relevant
suite are optional unavailable or filesystem-dependent evidence cases, not
accepted source migrations. Targeted Ruff, repository Pyright (zero errors or
warnings), documentation lint/link/backlog checks and Git whitespace checks
passed. No full suite, hosted exact-SHA CI, live private PDF migration,
Windows/Linux receiver activation or backup/restore acceptance is claimed.

**Next R4 work:** Audit remaining direct PDF readers for fixed roots and
hash-authority assumptions; separately review staged PDF/override mappings,
including current published source labels and producer lookup provenance.
Do not treat this code-only selection as private-source migration approval.

### Twenty-fourth bounded L2 checkpoint — R4 explicit staged PDF and override destinations (2026-11-13)

**Starting base:** Clean `dev/tooling-workspace-cleanup` at
`e22cd031d39118f122de6c558d373ddc08f00a33`. Previously,
`tools.activate_synced_assets activate --layout local --file` still copied
individual PDFs and overrides to `data/pdf/` and `image_overrides/`, even
though snapshot pairs supported the explicit `local/data/` layout. This
was a reader/activation mapping inconsistency, not approval to migrate
private sources.

The reviewed version-1 staged-asset policy now maps **only explicitly
selected** `--layout local --file` requests to
`local/data/pdf/<relative>` and
`local/data/symbols/overrides/<relative>`, retaining the current
`pdf/` and hyphenated `image-overrides/` receiver folders. The unchanged
`legacy` default still maps to `data/pdf/` and `image_overrides/`.
Each layout permits exactly its own two destination prefixes; mixed
roots, invalid policy keys, nonexistent staged paths, unsafe names,
symlinks and conflicting destination bytes are rejected without fallback.
An explicit dry run creates no checkout files. The existing `--apply`
mechanism was exercised **only against disposable fixture checkouts**.
Snapshot pair mappings and their v1/v2/v3 provenance validation are
unchanged. This does not reconfigure Syncthing, update producer lookup
identities, validate artwork or make measured-only unpinned files an
authoritative published source.

The [staging runbook](syncthing-assets.md#individual-pdfs-and-overrides)
now specifies both layouts and insists on independent source-pin checks
before research/publication use. **Windows focused validation:**
`tests/test_activate_synced_assets.py` **103 passed, four skipped**,
`test_snapshot_provenance.py` **23 passed**, and
`test_research_source_paths.py` **40 passed, two skipped**:
**166 passed, six skipped, zero failures**. The skips are optional
filesystem/symlink evidence cases on Windows. Repository lint, Pyright
(zero errors/warnings), documentation lint/links/backlog and whitespace
checks passed. Hosted exact-SHA CI, Linux parity and real receiver
activation are separate acceptance gates.
R4 continues with direct fixed-path PDF auditors and source-dependent
test setup; R5 private backup/restore and R6 physical moves/deletions
remain unapproved and blocked. No ignored source or published artifact
was moved, altered or deleted.

### Twenty-fifth bounded L2 checkpoint — R4 remaining direct PDF reader disposition (2026-11-13)

**Starting base:** Clean `dev/tooling-workspace-cleanup` at
`3a6a0afc2ac3f1a9f08a71eb4fd59cbbd837103e`.
This slice separates implicit fixed-path source reads from callers that already
explicitly supply a pinned PDF path. No private PDF data or published source
identity was changed.

- **Bilingual Visibility Zone reviewer:**
  `report_reference_baseline.audit_visibility_zone_evidence` previously read
  `root / data/pdf/rules/n5-rules-v5.3-{en,es}.pdf` directly. Optional
  `source_layout=legacy|local` now selects exactly one path with the common
  `pinned_pdf_path` resolver; `--source-layout` is forwarded through the
  reconciliation CLI when `--verify-visibility-pdfs` is set. The bilingual
  pin definitions, selected page numbers, five reviewed term IDs and report
  contents remain unchanged. Missing, changed or linked selected sources
  fail closed before PDF parsing; no search or fallback is introduced.
- **Explicit-path exceptions (retained):** The same reporter's
  `--verify-declaration-pdf` and `--verify-conditional-pdf` inputs already
  receive caller-selected paths and check pinned bytes. The separate
  `audit_hacking_program_statistics_chart --pdf` similarly hashes its
  manifest-pinned input. Its `PDF` constant is a legacy **test prerequisite**,
  not the CLI's implicit source lookup. These explicit interfaces should not
  acquire an automatic file search or silently override user paths.
- **Source-dependent acceptance tests (still legacy-bound):**
  `tests/reference_acceptance_support.py::pdf_pages` and its Basic Attack,
  Hacking, and Template consumers require the pinned N5 PDF via the existing
  `require_source_files` precondition. The Template suite separately pins
  the FAQ and Wiki. `test_hacking_device_program_source_chart.py` imports
  the statistics PDF constant and uses explicit missing-source skips. Additional
  source suites contain direct `ROOT / data/pdf/...` prerequisites.
  Review their source-only fixture/skip contract family by family before
  offering opt-in layout selection. Do not globally redirect `ROOT`, interpret
  any available PDF as the correct revision, or change test skip/approval scope.

**Windows validation:** The focused reference-baseline suite passed
**84 tests, two skipped**, including hermetic selected-layout parity, CLI
forwarding and hash-failure refusal before PDF opening. The pinned Hacking
Program source suite passed **7 tests**, including the real supplied PDF/Army
archive verification. The common PDF path tests passed **40 tests, two skipped**.
Total: **131 passed, four skipped, zero failures**. Ruff, Pyright (zero errors
or warnings), documentation lint/links/backlog and Git whitespace checks passed.
The real Visibility Zone PDF test ran where the pinned source was available;
source-dependent skips on clean checkouts remain explicit. No live private
PDF relocation, Syncthing reconfiguration, public source publication or
R5/R6 approval follows from these changes. Linux parity is recorded below;
hosted exact-SHA CI remains an independent release/development gate.

**Linux exact-SHA fixture acceptance (2026-11-13):** After explicit
`origin` fetch, the `linux-dev` MCP checkout temporarily detached to
`323bfc05c96a2420653988cf2ccc5b457d53fbfa`. Its reference-baseline
suite passed **84, two skipped**; the Hacking Program source suite passed
**7**; and the shared research path suite passed **42** (including Linux
symlink cases): **133 passed, two skipped** for the current R4 slice.
The preceding R4 staged-file activation mapping also passed on this exact
SHA: **107 passed, zero skipped** in
`tests/test_activate_synced_assets.py`, compared to **103 passed, four
skipped** in the earlier Windows run. The cross-host fixture evidence is
thus **240 Linux tests passed, two skipped, no failures**, across the four
selected suites. Both real pinned PDF audit suites ran with available
legacy source bytes on both hosts; hermetic local-layout tests established
selection behavior, **not** migration/availability of real private PDFs in
the new layout. No source or override was activated outside disposable tests.
After testing, the Linux worker's original detached HEAD
`8de09b277e579bd8cb942c6aba242bfe4f71ceca` was explicitly restored.
The Windows cleanup branch remains independently checked out. Exact-SHA
GitHub smoke jobs passed for the code commit; Source checks were still in
progress at the time of this note, not accepted as green.

**Next R4 step:** Choose and adapt a coherent source-dependent acceptance
fixture family with explicit opt-in selection and reproducible hash checks;
validate its source-only tests on both hosts with supplied pins. Review
real receiver ACLs and backup/restore separately in R5 before any real
activation. Keep the staged override producer's reviewed basenames/hash
bindings separate from the receiver's physical destination mapping.

### Twenty-sixth bounded L2 checkpoint — R4 shared reference-acceptance PDF prerequisites (2026-11-13)

**Starting base:** Clean `dev/tooling-workspace-cleanup` at
`4cc478cdd0caa5e7dbec45a66009b439083b410f`. This is a bounded
consumer/test prerequisite change, not a source or release-data migration.

The shared `tests/reference_acceptance_support.py` source helper now selects
Core N5.3 and FAQ v0.1 PDFs through the already validated, hash-pinned
`pinned_pdf_path` resolver. The three owning source-only tests
(`test_combat_attack_reference.py`, `test_hacking_source_followup.py`,
`test_template_reference.py`) accept a **test-only** explicit
`--reference-pdf-layout legacy|local` pytest option, with `legacy`
as the unchanged default. Only their pinned PDF prerequisites and physical
page extraction change. The preserved source labels remain
`data/pdf/rules/n5-rules-v5.3-en.pdf` and
`data/pdf/faq/n5-faq-v0.1-en.pdf`; Core/FAQ hashes, text assertions, page
numbers and Wiki revision pins are unchanged. Non-PDF Wiki ZIPs stay in
`data/wiki/`; published runtime/database tests and browser assertions do
not consult this option. This does **not** replace the global
`require_source_files` policy for unrelated source tests.

A missing selected Core/FAQ PDF retains a source-only **skip**, with no
fallback to another layout. A present but altered, linked, unreadable or
unsafe selected PDF fails before page extraction; the page helper also
rechecks its selected PDF hash immediately before opening. Nested source
paths remain label-derived, not discovered or rewritten. Hermetic tests
exercise both physical layouts, hash refusal, missing-local while legacy
exists, unsupported-layout refusal and a real synthetic PDF page extraction.
The source-selection option is not a source-completeness or publication gate.

**Windows validation:** All three complete acceptance modules, including
their original API and Chromium browser checks, passed **17 tests, zero
skipped, zero failures**; the three source-only cases verified supplied
legacy PDF/Wiki bytes. Ruff passed after correcting import ordering, and
Pyright reported **zero errors, zero warnings**. Documentation lint, local
link/backlog checks and Git whitespace checks passed.

**Linux exact-SHA source acceptance:** After an explicit Git fetch and
temporary detached checkout at
`ea347cde51f795d5264a6e416dfa9cac647ceac6`, the selected source-only
Basic Attack, Hacking follow-up and Template tests each **passed** against
the supplied unchanged legacy PDFs/Wiki. Both hermetic layout, SHA and
synthetic-page regressions also **passed**: **five passed, zero skipped**.
The Linux checkout was restored to its original detached
`8de09b277e579bd8cb942c6aba242bfe4f71ceca` after these tests.
This validates explicit selection behavior on both hosts and source-only
legacy evidence on Linux; it does **not** demonstrate real local-layout
PDF availability, real migration, or full Linux browser acceptance.
Hosted exact-SHA CI remains a separate gate.

**Next R4 step:** Select the next coherent fixed-path PDF test family
(Hacking Program chart evidence or another existing source acceptance
module), preserving its original skip/hash/authority boundary. R5/R6
private source migration remains gated on independent ACL and tested
backup/restore evidence; this checkpoint does not authorize copying or
deleting any private PDF or SVG override.

### Twenty-seventh bounded L2 checkpoint — R4 Hacking Program chart test PDF selection (2026-11-13)

**Starting base:** Clean `dev/tooling-workspace-cleanup` at
`b871d1e093b5d3ab0af63dd9348eeb8d908ba9b9`. The Hacking Program
statistics tool already accepted a **caller-selected** `--pdf` and checked
its manifest hash; the remaining defect was confined to two independent,
source-dependent tests using the tool's fixed legacy `PDF` constant.

The tests in `tests/test_hacking_device_program_source_chart.py` now accept
the existing pytest `--reference-pdf-layout legacy|local` selector for
their N5.3 Core PDF prerequisite. Default `legacy` behavior, printed
p. 57–61 clause assertions, detailed p. 58 chart-column checks, twelve
Hacking Program identities, published Army comparison, the separate pinned
Army ZIP prerequisite and all citation/source-authority boundaries remain
unchanged. The test-only resolver binds the **canonical** source label
`data/pdf/rules/n5-rules-v5.3-en.pdf` using the existing immutable N5.3
SHA-256, and independently asserts that the statistics manifest still uses
that same canonical pin. A selected but absent PDF continues to skip just
the relevant source-only test; supplied wrong bytes, changed manifest pins,
unsafe/symlinked inputs and unsupported layouts fail closed. A local selection
never searches or falls back to an available legacy PDF. The auditor's
public `audit_files(pdf_path=...)` and CLI `--pdf` interfaces do **not**
change; no implicit lookup is introduced to the tool.

A synthetic no-fallback fixture now covers the selected legacy/local path,
altered local source bytes, missing-local-with-legacy-present, mismatched
manifest pin and invalid layout. The test module calls
`tools.research.source_paths.pinned_pdf_path` directly rather than importing
the browser-centric reference-acceptance helper, so optional PyMuPDF remains
**optional at collection time**. Existing real-PDF checks use
`pytest.importorskip` only at their original source-validation boundary.

**Windows validation:** The Hacking Program chart suite passed **8 tests**
(zero skipped), including both independently pinned real source checks and
the new synthetic layout case. The shared PDF path suite passed **40, two
skipped**: **48 passed, two skipped, zero failures** across the bounded
suites. Ruff, Pyright (zero errors/warnings), documentation lint, link/backlog
checks and Git whitespace checks all passed.

**Linux exact-SHA verification (2026-11-13):** After explicit `origin` fetch,
the registered `linux-dev` worker temporarily detached to
`cf7a30808c94d5e01166baa56f04eac15f4b1a71`. The Hacking Program
chart suite passed **8**, including its pinned PDF and archive checks, and
the shared PDF path suite passed **42** including Linux symlink cases:
**50 passed, zero skipped, zero failures**. The worker's original detached
HEAD `8de09b277e579bd8cb942c6aba242bfe4f71ceca` was then explicitly
restored. Neither worker performed real local-layout PDF migration; the
local layout was exercised with synthetic fixture bytes only. Exact-SHA
GitHub wheel/deployment smoke workflows succeeded for the code commit;
Source checks were still **in progress**, not accepted as green, when
recorded. No source-migration acceptance follows from this test-only change.

**Next R4 work:** Inventory other directly fixed-path source-only test
families, then adapt only meaningful active readers without weakening the
individual source/pin contract. Real receiver ACL/backup/restore and the R5/R6
physical migration remain separately gated. No private PDF or SVG override
was copied, relabeled, deleted or rewritten by this checkpoint.

### Twenty-eighth bounded L2 checkpoint — R4 N5.3 Core source-only fixture family (2026-11-13)

**Starting base:** Clean `dev/tooling-workspace-cleanup` at
`d79555bb24329520f50920866e1a086ba14be001`. Source-test inventory
identified a coherent group of five N5.3 English Core PDF readers that
already pinned the same complete SHA-256 and kept publication/API assertions
separate. These remain active acceptance evidence, not legacy tools whose only
reason to retain them is that the tests exist.

- `tests/test_ammunition_publication_parity.py`: printed combined-ammunition
  examples and maintained Army-to-catalog identity
- `tests/test_ammunition_visibility_opposition.py`: Smoke/Eclipse LoF,
  opposition and visor-source clauses
- `tests/test_cover_publication.py`: Cover/vertical movement PDF clauses and
  independently pinned Wiki evidence when its archive is available
- `tests/test_aro_deployment_publication.py`: ARO/Deployment page 13–16
  accepted source and publication parity
- `tests/test_command_token_source_review.py`: Command Token modes and
  restrictions on pages 128–129

Their **source-only** tests now inject the shared test fixture
`pinned_n53_core_pdf`, which uses the same explicit
`--reference-pdf-layout legacy|local` selection and verified
`pinned_pdf_path`. Default remains `legacy`. The fixture skips an absent
selected PDF, never searches the other layout, and fails on supplied wrong
bytes, links, unsafe paths or invalid layout. Each source test retains its
independent hard-coded N5.3 SHA-256 assertion, exact PDF page/phrase checks,
and its existing import/optional-PDF behavior. Other tests in those modules
still validate runtime/API/publication data independently. The Wiki path and
revision checks were **not** redirected. No new published facts or data were
generated.

**Remaining path-contract inventory — review by purpose, not mechanical
replacement:**

- `test_application_rule_references.py`, `test_silent_immunity_source_scope.py`
  and several `test_curated.py` evidence cases span older N5.2, bilingual
  N5.3, FAQ and/or manifest-defined source sets. They need per-revision pin
  validation, not an English-Core-only fixture.
- `test_audit_weapon_chart_profiles.py`, `test_audit_weapon_traits_prose.py`,
  `test_audit_mine_variant_effects.py` and related specialized audits are
  source-dependent **research/profile reconciliation** with distinct derived
  statuses. Review their accepted purpose and archive/file input contracts
  before migrating, retiring or replacing them.
- `test_deployable_trigger_cross_rules.py`, `test_immunity_*.py`,
  `test_geometry_publication.py`, `test_hacking_program_publication.py`
  and `test_curated.py` contain more direct Core/FAQ evidence prerequisites.
  Partition by source identity, test responsibility and publication gate before
  further updates; preserve review and skip semantics.
- Metadata labels and disposable test fixture strings containing
  `data/pdf/...` are **not** themselves readers and must not be bulk-rewritten.
  The search inventory is a bounded source-test sample, **not** an exhaustive
  filesystem census of ignored private inputs.

**Windows validation:** The five entire modules passed **43 tests, zero
skipped**, including all five real source validations and their independent
API/publication assertions (Ammunition parity 8, visibility opposition 24,
Cover 4, ARO/Deployment 4, Command Tokens 3). The shared PDF resolver suite
passed **40, two skipped**: **83 passed, two skipped, zero failed** in the
selected suites. Ruff, Pyright (zero errors/warnings), documentation
lint/links/backlog and Git whitespace checks passed.

**Linux exact-SHA verification (2026-11-13):** The registered `linux-dev`
worker explicitly fetched from origin and detached to commit
`90734e88a4119cf3b4168a7fadf632f0e8da361f`. All five complete Core
source-acceptance modules passed **43 tests** on Linux (same distribution as
Windows), including their real pinned PDF clauses, Wiki-if-present evidence,
and API/publication assertions. The shared PDF resolver suite passed **42**,
including its Linux-specific symlink cases: **85 passed, zero skipped, zero
failed** in the selected suites. After testing, the worker's original
detached HEAD `8de09b277e579bd8cb942c6aba242bfe4f71ceca` was restored.
Exact-code-SHA installed-wheel and deployment smoke workflows completed
successfully; Source checks were **queued** at evidence capture, not accepted
as green. These tests establish the old-layout source and hermetic path
contract on both hosts; they do **not** demonstrate actual private PDFs under
`local/data/pdf/` or authorize source migration.

**Next:** Resolve the remaining active multi-source and specialized test
families separately, then assess R5 ACL and tested backup/restore before any
approved R6 private source move. No source path labels, ignored PDF or
Wiki bytes, SVG overrides, Syncthing layout or generated databases were
changed as part of this bounded test migration.

### Twenty-ninth bounded L2 checkpoint — R4 weapon-chart source-only tests (2026-11-13)

**Starting base:** Clean `dev/tooling-workspace-cleanup` at
`f2bf26040623f369517fa9fc32fccd814afb577c`. The three current
weapon-profile source-audit modules each still read the exact same N5.3
English Core PDF from a fixed legacy path. Their audit tools already accept
the caller's input PDF path and produce research classifications rather than
published rule facts, so neither their APIs nor their accepted outputs need
to change.

- `tests/test_audit_weapon_chart_profiles.py`: the source-only complete
  chart comparison now uses `pinned_n53_core_pdf`; the 173 compared rows,
  candidate discrepancy and range statuses, auxiliary profiles, and named
  Army/PDF differences remain checked as before.
- `tests/test_audit_weapon_traits_prose.py`: the source-only trait/prose
  alignment check uses the same selected PDF; its 173 trait rows and the
  examined Uragan/Suppressive Fire p.188 anchors remain unchanged.
- `tests/test_audit_mine_variant_effects.py`: each of seven source-only
  variant checks uses the selected PDF and **independently** compares its
  SHA-256 with `config/validation/mine-variant-effects.json`, retaining
  chart footnote, rule-owner, source excerpt, Army object S and unresolved
  PARA/review-status distinctions.

All other synthetic, API and stored-profile checks in these modules retain
their independent meaning. The optional PyMuPDF/fitz test imports remain
inside their source checks, not the fixture or collection phase. The
`--reference-pdf-layout legacy|local` pytest selector remains opt-in
(default `legacy`) and hashes the only selected physical PDF before its
content is opened; absent selected source skips its source-only test while
wrong bytes, unsafe paths and link traversal fail without fallback. No
historical PDF, Wiki/Army source, snapshot, publication database, SVG
override or Syncthing input was moved or renamed. Production audit tools
continue accepting explicit PDF paths and retain their reviewed discrepancy
classification policy.

**Windows validation:** `test_audit_weapon_chart_profiles.py` passed
**27**, `test_audit_weapon_traits_prose.py` passed **15**, and
`test_audit_mine_variant_effects.py` passed **25**. The shared
`test_research_source_paths.py` suite passed **40, two skipped**:
**107 passed, two skipped, zero failed** across all four focused suites.
All real pinned source checks ran with supplied legacy bytes. Ruff, Pyright
(zero errors/warnings), documentation lint/links/backlog and Git whitespace
checks passed.

**Linux exact-SHA validation (2026-11-13):** The registered `linux-dev`
worker explicitly fetched from origin and temporarily detached to
`53b066bbaba7ef52ee900aac712b5ba41b0abb2e`. The full weapon-chart
module passed **27**, trait-prose module **15**, and Mine variant module
**25** (all actual legacy pinned-source checks executed). The shared PDF
path-policy suite passed **42** including Linux symlink cases:
**109 passed, zero skipped, zero failed** across the four focused suites.
The worker was explicitly restored to its previous detached HEAD
`8de09b277e579bd8cb942c6aba242bfe4f71ceca`. At evidence capture,
the exact code-SHA GitHub Source checks, installed-wheel smoke and
deployment smoke workflows were **in progress**, not yet green. This
demonstrates no physical `local/data/pdf/` source availability and does
not approve migration or publication.

**Next:** Review the remaining bilingual/multi-revision and
immunity/deployable source-test families by their actual current purpose and
pin authority; do not bulk-replace source labels or retain historical
tests solely to preserve old data paths. R5 real receiver ACL,
backup/restore and R6 physical migration are still independently gated.

### Thirtieth bounded L2 checkpoint — R4 multi-revision and bilingual source-test selection (2026-11-13)

**Starting base:** Clean `dev/tooling-workspace-cleanup` at
`c2c7ec47dd5a5ceeeb9344a5f446f2a7f8a6f68d`. This bounded migration
covers active acceptance tests that compare independent English/Spanish
Core rules, historical N5.2 wording, FAQ revisions, and N4-vs-N5
Reinforcements source applicability. It does **not** change semantic
source identities, publication rules or producer paths.

A test-only `pinned_pdf_sources` fixture accepts a mapping of canonical
`data/pdf/...` labels to reviewed SHA-256 pins and resolves all requested
members under one **explicit** `--reference-pdf-layout legacy|local`
selection (default `legacy`). The helper verifies every supplied member
before reporting any missing sibling. A missing required PDF skips only
the source-only test; a present but corrupted, unreadable, linked or
unapproved revision fails closed even if another source is missing. A
selected missing PDF never falls back to the other layout. Existing
`pinned_n53_core_pdf`, `require_source_files` and published application
input contracts are unchanged.

- `tests/test_application_rule_references.py` binds the exact N5.3
  English/Spanish, N5.2 English source versions in the Attribute/SWC,
  Hackable profile and V1S-082 Label-review clauses, with separate page
  numbers, language predicates, and final curated/API comparisons.
- `tests/test_silent_immunity_source_scope.py` binds a **two-source**
  N5.3 English/Spanish timing comparison, individually pinned N5.2
  glossary evidence, and FAQ v0.0 English/v0.1 English/Spanish source
  identities. The unresolved Silent/Immunity timing and source-scoped
  disclosure remain intact, rather than being normalized into a rule.
- `tests/test_audit_reinforcements_applicability.py` gathers exactly four
  manifest-defined source pins: historical N4 English/Spanish, current
  N5.3 English and ITS Season 18 English. The production
  `audit_applicability(source_layout=...)` interface already supported
  explicit selection. Its source identity, completeness, historical
  provenance, and **no N5 procedural authority** gates remain unchanged.

Hermetic `tests/test_research_source_paths.py` cases cover both layouts,
bilingual sibling absence, supplied sibling hash drift, and legacy/local
no-fallback without creating or changing private source files. The
specialized Reinforcements tests already exercise synthetic layout
parity and false-authorization refusal. The larger `test_curated.py`,
immunity/geometry and deployable source families are **not** modified
in this checkpoint and require separate review by active test purpose.

**Windows focused validation (working tree on the starting base):**
`test_application_rule_references.py` **55 passed**;
`test_silent_immunity_source_scope.py` **15 passed**;
`test_audit_reinforcements_applicability.py` **18 passed**;
`test_research_source_paths.py` **42 passed, two skipped**:
**130 passed, two skipped, zero failed**. Legacy supplied source
bytes were actually checked on Windows. Ruff, Pyright (zero
errors/warnings), documentation lint/links/backlog and Git whitespace
checks all passed.

**Linux exact-SHA verification (2026-11-13):** The registered
`linux-dev` worker explicitly fetched origin and temporarily detached
to `58aacd829a1cee2f58d7be8cbbb3c1a6bae8edba`. Full modules
passed **55** Application Rule, **15** Silent/Immunity and **18**
Reinforcements applicability; the shared research-source path suite
passed **44** including Linux link-safety cases: **132 passed, zero
skipped, zero failed**. The same N5.2, N5.3 bilingual, FAQ, historical
N4 and ITS18 pinned sources were verified as legacy inputs, while the
hermetic cases exercised both physical layouts. Linux was explicitly
restored to its previous detached
`8de09b277e579bd8cb942c6aba242bfe4f71ceca` after the tests.
At evidence capture the code-SHA GitHub installed-wheel and deployment
smoke workflows had **succeeded**, while Source checks were **queued**.
These local tests are not approval of real local PDF availability,
production publication or private source migration.

**Next R4:** Partition remaining current-source immunity/deployable/
geometry modules from the much larger historical and curated-rule evidence
suite; do not bulk-change provenance labels. R5 real receiver ACL,
backup/restore and R6 physical migration are **not** authorized. This
checkpoint moves no ignored PDF/Wiki content, SVG overrides, Syncthing
folders or generated databases.

### Thirty-first bounded L2 checkpoint — R4 immunity Core PDF source tests (2026-11-13)

**Starting base:** Clean `dev/tooling-workspace-cleanup` at
`307bed14c7461ec2dafc170fe7e634793adc0cf9`. An inventory found
16 current `tests/test_immunity_*.py` modules whose source-only tests
all opened the same fixed `data/pdf/rules/n5-rules-v5.3-en.pdf` and
independently asserted the identical official N5.3 English Core
SHA-256. They cover active rules/publication acceptance (critical-hit
and combined-ammunition cases, AP/T2, BTS E/M and component immunity,
Comms exceptions, and printed weapon/saving-roll examples); none was
retired merely because its evidence input is an ignored file.

For each of the 16 modules, **only** the source-only test's input path
was changed to the existing, test-only `pinned_n53_core_pdf` fixture.
The redundant fixed physical `PDF` constant was removed. Each
test retains its own full SHA-256 check, original page text and clause
assertions, special-case/discrepancy expectations, and unchanged
curated/Army/API tests. Default remains explicitly selected `legacy`;
`--reference-pdf-layout local` reads only `local/data/pdf/`, never
falling back to legacy. Missing selected source skips source-dependent
checks; present wrong bytes, unsafe inputs and links fail closed before
PDF parsing. The production data/build/audit inputs remain unchanged.

**Scope held out:** Deployable trigger, movement/geometry, hacking
publication, the much larger `test_curated.py`, and other indirect
source readers require separate evidence/provenance review; none is
bulk redirected. No N4/N5 authority, bilingual source identity, FAQ
revision, ignored private PDF or runtime database was changed.

**Windows focused validation:** The 16 complete immunity modules
passed **138 tests**, zero skipped/failed, including all their real
legacy pinned-source checks and maintained API/curated assertions.
The shared research-source path suite passed **42, two skipped**:
**180 passed, two skipped, zero failed** across the bounded selection.
Ruff passed after wrapping five over-length function signatures;
Pyright returned zero errors/warnings. Documentation lint/links/backlog
and Git whitespace checks passed.

**Linux exact-SHA verification (2026-11-13):** The registered
`linux-dev` worker explicitly fetched origin and temporarily detached
to code commit `0f150eb78b085a5cda620af5a7798b2632344a38`.
All **16** complete immunity modules passed **138** tests, including
the real legacy source checks and all maintained API/curated assertions.
The shared source-path policy passed **44** (including Linux link
guards): **182 passed, zero skipped, zero failed**. The worker was
explicitly restored to its original detached HEAD
`8de09b277e579bd8cb942c6aba242bfe4f71ceca`.
Exact-code-SHA GitHub installed-wheel and deployment smoke tests
**passed**; Source checks remained **in progress** when evidence was
recorded. These validations exercise actual legacy PDF inputs and
hermetic layout bindings only: no real `local/data/pdf` source was
installed, and no private migration or publication approval follows.

**Next R4:** Review deployable, geometry and movement source acceptance
as a distinct shared-source group, then curate the remaining larger
source-test inventory by purpose. R5 receiver ACL, independent
backup/restore and R6 actual private source migration remain
separately gated and unapproved.

### Thirty-second bounded L2 checkpoint — R4 deployable, spatial, terrain and phase PDF source tests (2026-11-13)

**Starting base:** Clean `dev/tooling-workspace-cleanup` at
`06f43de5a126591550055ce54800803da12f9a05`. This bounded
source-only acceptance migration covers six maintained test modules, not
production source paths or publication semantics:

- `tests/test_deployable_trigger_cross_rules.py` selects the pinned
  English N5.3 Core PDF for all ten source-only test groups and the
  **separately pinned FAQ v0.1 English** source for fired-deployable
  delivery. Original excerpt, page and SHA-256 assertions remain.
- `tests/test_geometry_publication.py`,
  `tests/test_movement_publication.py` and
  `tests/test_terrain_condition_publication.py` use the shared
  `pinned_n53_core_pdf` selector for their single-source page acceptance;
  maintained curated, Rules database and HTTP/API checks are unchanged.
  The two tests' optional **Wiki ZIP** evidence retains its existing
  legacy path and independent hash; R3 Wiki archive cutover is a separate
  decision.
- `tests/test_phase_source_review.py` uses the single Core fixture
  for its English clauses and `pinned_pdf_sources` for the independent
  English/Spanish Lieutenant discrepancy. No bilingual interpretation,
  official clarification status or source authority was normalized.
- `tests/test_turn_sequence_publication.py` selects its English and
  Spanish Core pins **individually**, retaining their separate parametric
  source checks and curated/publication assertions.

Selection is explicit via `--reference-pdf-layout legacy|local` (default
`legacy`), with **no** cross-layout fallback. Missing selected source-only
PDFs skip only the dependent tests; present incorrect, unsafe or
unapproved bytes fail closed before parsing. The shared selector and
its missing-sibling/hash-drift guarantees are not modified.

**Windows focused validation:** Complete six modules passed
**137 tests**, zero skipped/failed, against the actual legacy pinned
Core/FAQ English and Spanish PDFs. Shared
`tests/test_research_source_paths.py` passed **42, two skipped**:
**179 passed, two skipped, zero failed** for this batch. Ruff and the
canonical `run_checks(type)` stage passed (Pyright: zero errors/warnings).
A direct standalone Pyright invocation without the checkout's explicit
Python interpreter reported unresolved environment dependencies; the
canonical typed stage supplied its configured `--pythonpath` and passed.
Documentation lint, links, backlog checks and Git whitespace checks
also passed. Linux exact-SHA verification remains a separate follow-up gate.

**Next R4:** Partition remaining direct source readers, particularly
`test_curated.py` and the other fixed-path source families, by current
acceptance purpose before redirecting anything. R5 real receiver ACL,
independent backup/restore and R6 private-data migration remain
unapproved; no ignored PDF, Wiki archive, override, Syncthing asset or
runtime database was moved or deleted here.

### Thirty-third bounded L2 checkpoint — R4 curated and mixed-source acceptance (2026-11-13)

**Starting base:** Clean `dev/tooling-workspace-cleanup` at
`6e873e9f40f324243ccda83875eacec4c9be8818`. The remaining
source-only PDF checks in `tests/test_curated.py` were partitioned into
**18 single English N5.3 Core** and **three independently versioned
English/Spanish/historical** comparisons. All 21 now select an exact
physical layout through the existing test-only pinned-source fixtures;
source record IDs, page/text assertions, source-specific semantics and
curated/published output remain unchanged.

- The 18 English N5.3 tests use `pinned_n53_core_pdf`; each retains its
  existing independent `weaponry-family-clauses.json` hash assertion.
  Their local `source` variable now aliases the validated selected path.
- The N5.2/N5.3 Jet Propulsion (ESX-02), bilingual Stealth (ESX-01) and
  MSV3 (ESX-03) comparisons select independently reviewed SHA-256 pins
  with `pinned_pdf_sources`, including the historical N5.2 English PDF.
  This strengthens fail-closed version binding without resolving or
  erasing any multilingual or edition-specific discrepancy.
- `tests/test_weapon_profile_publication.py` now supplies its reviewed
  chart auditor with the pinned English Core path. Publication identity,
  chart modes, pages and embedded-profile integrity checks are unchanged.
- `tests/test_audit_auxiliary_silhouette_provenance.py` independently
  pins both English and Spanish N5.3 PDFs before the existing mixed
  PDF/Wiki/Army comparison. The two legacy Wiki ZIP paths, Army database
  and known S0/S1 disagreement remain untouched.
- `tests/test_hacking_program_publication.py` preserves its **optional**
  PDF hash cross-check within a mandatory API/publication test:
  `pinned_pdf_path(..., missing_ok=True)` validates a present source
  against the explicitly selected layout, but missing private PDFs
  cannot skip the publication assertions.

`--reference-pdf-layout legacy|local` still defaults to `legacy` and
never searches the other layout. Missing selected PDFs skip only
source-dependent checks; present incorrect/unsafe inputs fail closed.
The mixed Hacking Program test instead retains its optional check while
running publication assertions regardless of PDF availability. No
publisher labels, `localPath` fields, provenance identities, runtime
database contents or producer paths were rewritten.

**Windows focused validation:** Complete `test_curated.py`,
`test_weapon_profile_publication.py`,
`test_audit_auxiliary_silhouette_provenance.py` and
`test_hacking_program_publication.py` passed **671 + 14 + 4 + 10 = 699**
tests with no skips/failures. Shared
`test_research_source_paths.py` passed **42, two skipped**:
**741 passed, two skipped, zero failed**. All evidence tests
used actual legacy private PDF inputs. Ruff, canonical Pyright (zero
errors/warnings), documentation lint/links/backlog and Git whitespace
checks passed. Linux exact-code-SHA validation remains a follow-up gate.

**Next R4:** Review remaining mixed source consumers by purpose, notably
`test_weaponry_catalog_api.py`, `test_report_reference_baseline.py`,
`test_restriction_storage_candidate.py` and other direct/indirect readers.
Retain published `localPath` labels unless a separately approved source
migration specifically changes that contract. R5 receiver ACL, independent
backup/restore and R6 physical private-data migration remain unapproved.
No ignored PDF, Wiki archive, override or generated database was moved
or removed in this checkpoint.

### Thirty-fourth bounded L2 checkpoint — R4 mixed-source publication and export readers (2026-11-13)

**Starting base:** Clean `dev/tooling-workspace-cleanup` at
`627b66a3077b576e691911463d354e385847c65b`. This is a
test-only source-selection change, not source relocation or approval
to change published provenance.

- `tests/test_weaponry_catalog_api.py`: the Pheroware and page-75
  source-only checks now use the selected pinned N5.3 English Core PDF;
  the ESX-04 AP+T2 CC bilingual chart test uses separately pinned English
  and Spanish sources. The page-75 config path is rooted in the repository
  rather than derived from the PDF's physical parent, so `local`
  selection does not change where the tracked manifest is read.
- `tests/test_report_reference_baseline.py`: ECM/Firewall and
  conditional-declaration source-only checks use the pinned Core fixture.
  The bilingual Visibility Zone check selects both manifest-declared
  PDF pins before passing the explicit layout into the existing auditor.
  The optional declaration-migration PDF check retains its mandatory
  owner/crosswalk assertions when a source is absent and validates a
  present PDF against the tracked restriction-chart hash first.
- `tests/test_restriction_storage_candidate.py`: both the English Core
  optional pin check and each of the 13 declared PDF-source occurrences
  resolve the physical path through the selected layout, with their
  original source IDs, declared `localPath` labels, SHA-256s and SQL
  export comparisons unchanged. The export assertions run even when
  an optional physical PDF is unavailable.

The explicit `--reference-pdf-layout legacy|local` policy remains
`legacy` by default. Missing selected source-only PDFs skip their own
tests; present mismatched or unsafe sources fail closed without
cross-layout fallback. Optional checks inside mandatory publication
or export tests do not skip those tests. No PDF, Wiki archive, runtime
database, or generated asset was moved or deleted.

**Windows validation:** the complete weaponry catalog, reference
baseline and restriction-storage modules passed **196 + 84 + 14 = 294
tests, two skipped**. The shared source-path suite passed **42 tests,
two skipped**: **336 passed, four skipped, zero failed** total. Ruff,
canonical Pyright (zero errors/warnings), docs lint/links/backlog and
Git whitespace checks passed. Linux exact-SHA checks remain a distinct gate.

**Next R4:** Inventory any other direct private PDF readers not yet
converted, then confirm the source-reader phase is sufficiently bounded
to close R4. Do not promote R5 receiver ACL/independent backup-restore
or R6 private-data relocation without their separate approval.

### Thirty-fifth bounded L2 checkpoint — R4 final direct-PDF-reader inventory (2026-11-13)

**Starting base:** Clean `dev/tooling-workspace-cleanup` at
`4332f5b4e4ad0cb31542580b2be751768065f388`.
A fresh whole-`tests/` and `tools/` search separated actual physical
PDF reads from source labels, synthetic migration fixtures and
backward-compatible defaults. The following five maintained test modules
now use explicit `--reference-pdf-layout legacy|local` source selection:

- `tests/test_faq_ruling_references.py` keeps the three independently
  reviewed FAQ v0.0/v0.1 English/Spanish identities and per-source
  inventory, curated metadata, page count and SHA-256 assertions. The
  physical byte reader now uses `pinned_pdf_sources`; no FAQ version
  fallback or source reinterpretation was added.
- `tests/test_audit_1_0_reference_inputs.py` uses independently
  declared historical N4 Reinforcements pins before the existing
  `verify_reinforcements_inputs(..., source_layout=...)` report. This
  remains **historical evidence, not current N5 authority**; synthetic
  negative-path tests retain their deliberately isolated fixture paths.
- `tests/test_visibility_zone_whole_record.py` binds both English and
  Spanish N5.3 PDFs through the shared pinned selector. The exact
  operative clauses, page numbers, five-term record acceptance and
  manifest's language-specific pins remain independent and unchanged.
- `tests/test_conditional_reactive_followup.py` binds the single N5.3
  English PDF before its twelve reviewed-page excerpts. Curated/API
  evidence and heading-only versus full-clause limitations are untouched.
- `tests/test_web.py` binds the isolated five-term Visibility Zone
  English page source check; the entire surrounding web acceptance
  module and pinned content checks remain unchanged.

**Intentional residual references, not hidden physical-layout readers:**
`tests/reference_acceptance_support.py` retains the legacy `PDF`
constant and default `pdf_pages` parameter for compatibility, but the
maintained source-acceptance callers already pass an explicitly selected
`pdf_path`. `tools/audit_hacking_program_statistics_chart.py`
retains its legacy `PDF` constant for compatibility; `audit_files`
only reads a PDF passed as `pdf_path` and the CLI requires an explicit
`--pdf` argument for PDF verification. Fixed paths in
`tests/test_activate_synced_assets.py` and
`tests/test_audit_reinforcements_applicability.py` are synthetic,
disposable staging fixtures; `localPath` strings in manifests, curated
sources and reports are **provenance labels**, not physical layout
selection. Existing PDF auditors that already accept explicit
`source_layout` or `--pdf` are not retargeted behind their callers'
backs.

The default layout remains `legacy` without fallback. Missing
source-dependent private inputs skip only the relevant source tests;
supplied unsafe or mismatched inputs fail closed. No private PDFs,
Wiki ZIPs, source overrides or runtime databases were moved, renamed,
published or deleted.

**Windows validation:** All five affected modules and the shared
source-path suite passed **502 tests, three skipped, zero failed**.
The complete `tests/test_web.py` module contributes **323 passed,
11 deselected** under the normal `not full_assets` profile.
The other modules passed 80 FAQ (one skipped), 50 historical-source,
four conditional-reactive, three whole-record Visibility Zone and
42 source-layout tests (two skipped). Ruff, canonical Pyright
(**0 errors, 0 warnings**), docs lint/links/backlog and Git whitespace
checks passed. Linux exact-SHA verification remains a separate gate.
Neither set substitutes for real-source local-layout parity or
private-asset migration acceptance.

**Next:** Close out any remaining R4 operational evidence gaps
through explicit staging/parity tests only; R5 receiver ACL and
independent backup/restore evidence and R6 physical private-data
migration remain separately gated and unapproved.

### Thirty-sixth bounded L2 checkpoint — R4 staged activation to pinned-reader parity (2026-11-13)

**Starting base:** Clean `dev/tooling-workspace-cleanup` at
`691a307feb3ddac2fcdd3686db86647dd7f8af15`. The prior
[R4 final reader inventory](#thirty-fifth-bounded-l2-checkpoint--r4-final-direct-pdf-reader-inventory-2026-11-13)
completed the direct physical-PDF consumer classification. This checkpoint
closes the remaining *hermetic interface gap* between the staged-asset
activator and pinned PDF source reader, without asserting a live cutover.

The integrated `test_pinned_pdf_and_override_activate_with_matching_read_only_layouts`
in `tests/test_activate_synced_assets.py` now:

- creates disposable, independently named PDF and SVG override inputs in
  the configured staged `pdf/rules/` and `image-overrides/Unit/` families;
- previews both explicit `legacy` and `local` file layouts and checks
  the preview leaves checkout bytes unchanged;
- applies each file in an isolated checkout, verifies idempotent subsequent
  activation, identical PDF/SVG bytes, no alternate-layout destinations,
  and untouched staged inputs;
- verifies the selected PDF through the actual pinned SHA-256 reader for
  each layout, using the unchanged `data/pdf/...` source label;
- introduces an independently valid legacy sibling beside a tampered
  local-selected PDF, proving the pinned reader fails closed without
  cross-layout fallback and the activator refuses to replace the
  conflicting destination.

The [staged-asset runbook](syncthing-assets.md#individual-pdfs-and-overrides)
now explicitly documents **copy-only** compatibility for pinned research
PDFs: `pinned_pdf_path` rejects symlinks/reparse points even when a
different activation workflow permits symlink output. An override's matching
hash is transport evidence only, **not artwork approval** or a declaration
that symbol processing/publication has occurred.

**R4 technical status:** The reader-binding and synthetic staged-layout
acceptance slices are complete and retain the `legacy` default,
provenance labels, source hash authority, independent symbol ownership and
non-replacing activation. This is **not** evidence of real receiver ACLs,
independent backups or tested restore, source synchronisation, a live
`local/` file migration, or approved source deletion. Those belong to
R5/R6, with separate explicit decisions. No ignored or private PDF,
override, Wiki archive or runtime database was moved or deleted.

**Windows validation:** The complete activation module passed
**104 passed, four skipped** (filesystem-specific symlink/case fixtures);
the shared PDF path module passed **42 passed, two skipped**, for
**146 passed, six skipped, zero failed** combined. Ruff, canonical
Pyright (zero errors/warnings), docs lint/links/backlog and whitespace
checks passed. Linux exact-SHA fixture acceptance remains a separate
gate. Hosted CI and full-project tests are not implied by focused
acceptance.

**Next:** Move the workstream to a **read-only R5 operational inventory**:
verify current sender/receiver roots, effective ACLs, independent
backup/restore capability and a per-family hash/rollback decision package.
No physical move, ACL modification, Syncthing reconfiguration or private
asset deletion is authorized by this R4 checkpoint.

### Thirty-seventh bounded L2 checkpoint — R5 live receiver access evidence (2026-11-13)

**Starting base:** Clean `dev/tooling-workspace-cleanup` at
`4cf9f414c2ba7232e0d7a41c1670ee8ec2035e20`. R4's bounded
staged-file and pinned-source parity acceptance is complete. R5 now
requires a separate *operational* read-only evidence sequence; this
checkpoint does **not** authorize a private-source cutover.

**Previously retained private baseline (2026-11-12):** The audited
Syncthing configuration contained five Windows Send Only and Linux
Receive Only folder pairs with matching folder IDs. All five Linux
receiver status snapshots showed idle state, equal local/global file
and byte counts, zero pending files/deletions and no pull errors.
The Windows sender's live GUI/status query failed, and the inspected
receiver had no proven versioning. A separate audit matched all
**24 paired snapshot archives and manifests** by exact bytes, but
Syncthing is not an independent backup and no trial restore was
performed. The 19 access-denied Windows `reports/` directories still
lack authorized content classification. These are historical captures,
**not** proof of the current Windows sender state or current sync
consistency.

**Fresh Linux evidence (2026-11-13, worker `linux-dev`):**

1. On the exact pushed R4 SHA
   `4cf9f414c2ba7232e0d7a41c1670ee8ec2035e20`, the existing
   read-only `activate_synced_assets list --layout local` returned
   **24 staged manifests**. A selected Army snapshot
   `JSON 20260929-114335` verified as the pinned
   SHA-256 `f103a7afd02e68d845cc9ce38b1948f46914676bbc6a5e6b790d0a04148b6c75`.
   The English N5.3 PDF `--layout local --file ...` activation preview
   returned **planned copy**, without `--apply` or checkout writes.
2. A new bounded, read-only module,
   `tools.operations.audit_syncthing_receiver`, and its `ops`
   test module were committed as
   `7994bf0bb69d462e40c3fe09c6347cae8dc8ef91`.
   The probe reads only directory/file metadata and named POSIX ACLs,
   under the explicitly configured `INFINITYDB_SYNC_STAGING_ROOT`.
   It refuses linked receiver roots and linked selected source paths,
   omits private payload names/content from its output, and never
   writes or invokes synchronization.
3. On that exact SHA, running as **`mcpworker`**, all five folder
   roots (`raw`, `wiki`, `pdf`, `snapshots`,
   `image-overrides`) reported existing directories,
   readable **true**, writable **false**, and
   `getfacl` entries `user:mcpworker:r-x` plus
   `default:user:mcpworker:r-x`. The three selected paths
   (Army ZIP, Army manifest, English N5.3 PDF) reported readable
   **true**, writable **false**, and were not owned by
   `mcpworker`. No write test was attempted.
4. The new probe's six hermetic tests passed on Linux, with no
   skips/failures; on Windows **four passed, two skipped** because
   creating real symlinks required unavailable privileges.
   `tests/test_test_sections.py` passed **15/15**,
   Ruff and canonical Pyright passed with zero errors/warnings.
   The Linux worker was returned to its prior detached
   `8de09b277e579bd8cb942c6aba242bfe4f71ceca` after
   inspection.

**Interpretation:** Linux receiver roots and the named samples have
confirmed read-only access *for this worker identity at inspection time*.
This is not a full recursive ACL inspection, a current Syncthing API
check, a proof of future inherited permissions, a live Windows sender
check, a backup inventory or a tested restore. It cannot certify
R5 readiness or justify an R6 migration.

**Remaining R5 acceptance gates, in required order:**

1. Recheck **both** Syncthing services from live read-only status,
   verifying folder IDs, Send/Receive Only flags, sync state,
   per-family local/global/need counts, errors and versioning. Never
   persist Syncthing API keys or tokens in tracked reports.
2. Inventory effective worker read-only ACLs **recursively or with a
   complete deterministic per-family file/dir census**, including
   newly received files and default ACL masks; verify the Windows
   sender's current source roots and accessible private path owners.
   Do not grant extra permissions simply to make the audit pass.
3. Identify an **independent, offline-or-separately-versioned backup**
   covering all selected source families and immutable provenance.
   Record exact archive/manifest/source hashes and run a **trial
   restore into a detached disposable destination**; compare exact
   bytes. A second Syncthing copy is not acceptable backup evidence.
4. Freeze an individually reviewed per-family source/target/hash,
   consumer and rollback manifest. Only then seek separate approval
   for an R6 non-destructive copy. Old-source retirement/deletion
   needs a later independent decision.

**State: R5 OPEN; R6 blocked.** All operations in this checkpoint were
metadata-only, source-byte verification or dry-run inspection.
No private source was moved, deleted or republished; no ACL,
Syncthing configuration, Windows sender path, backup, Docker volume
or runtime database was modified.

### Thirty-eighth bounded L2 checkpoint — R5 sender health and recursive receiver access (2026-11-13)

**Starting base:** Clean `dev/tooling-workspace-cleanup` at
`bb779666cc1c635f7dfbd77cd8c4ca822f117bea`. This phase adds
read-only Syncthing **service** status and recursive effective access
coverage, not a private-data migration or backup implementation.

**Live Windows sender verified:** The credential-redacted
`tools.operations.audit_syncthing_health --role sender` probe,
committed as `bb0a3433dea5406ff4f7a6825c5e84fefba40401`,
successfully read the current Syncthing configuration and queried the
**local loopback REST API** for all five selected folders. Every folder
had the expected source root, configured ID and `sendonly` mode,
was unpaused and idle, and reported matching local/global file and byte
counts, zero pending files/bytes/deletions, zero pull errors and no
versioning. The observed counts were:

- Army/raw: **23 files; 142,272,280 bytes**.
- Snapshot manifests: **25 files; 16,186 bytes**.
- Wiki: **27,313 files; 5,086,349,340 bytes**.
- PDF: **81 files; 1,035,875,348 bytes**.
- Reviewed override receiver family: **113 files; 875,572 bytes**.

Folder IDs and these counts also match the **historical** Linux
receiver-status capture from 2026-11-12. This supports stable,
consistent source metadata across those observations but does **not**
prove the Linux receiver is currently synchronized or connected.

The probe accepts only local configured GUI addresses, forces
loopback GET requests with proxy bypass and redirects disabled, and
never prints API keys, private config paths or unexpected API response
fields. Its **11 hermetic tests passed on both Windows and Linux**;
`tests/test_test_sections.py` passed **15/15**. Ruff, canonical Pyright
(zero errors/warnings) and docs checks passed.

**Direct Linux live status still blocked:** The same tracked probe,
running as `mcpworker` with `--role receiver` at exact SHA
`bb0a3433dea5406ff4f7a6825c5e84fefba40401`, returned
`config-not-readable`. The default configuration discovery runs under
the worker's identity, not the Syncthing owner's identity; this
result alone cannot distinguish absent worker-local config from an
owner-file ACL restriction. No alternate credential source, service
impersonation, ACL changes or privileged helper was attempted.
An **owner-authorized read-only receiver API** check is required to
close the live-sync evidence gap.

**Recursive Linux receiver access verified:** A bounded
`--recursive` extension to `tools.operations.audit_syncthing_receiver`,
committed as `00cb83871802fb6886ab2b028f6238798442e813`,
checks effective worker access through every encountered family entry,
without following symlinks, opening file contents or printing private
names. The exact-SHA `linux-dev` run completed **35,833 entries**,
consisting of **27,560 files and 8,273 directories**, as follows:

- Raw: **24 files, 3 directories**.
- Snapshots: **26 files, 2 directories**.
- PDF: **82 files, 8 directories**.
- Override family: **114 files, 7 directories**.
- Wiki: **27,314 files, 8,253 directories**.

Every family reported `complete: true`,
`effective_readonly: true`, **zero writable, unreadable, linked,
nonregular or uninspectable entries**, and no entry-limit hits.
The counts include Syncthing's own marker metadata, so they need not
equal the application-file counts reported by its REST API. Root-level
named/default `mcpworker:r-x` ACL entries were independently confirmed
in the preceding checkpoint. The recursive scan validates effective
access for present entries; it does **not** inspect every inherited
default ACL or prove future file permissions. It deliberately retains
`recursive_acl_verified: false`.

**Focused validation for the recursive extension:** Windows
**8 passed, 3 skipped** (unavailable real-symlink privileges); Linux
exact-SHA **11 passed, no skips**. Ruff, canonical Pyright (zero
errors/warnings) and whitespace checks passed. After each Linux phase,
the worker was returned to its previous detached
`8de09b277e579bd8cb942c6aba242bfe4f71ceca`.

**R5 state: OPEN; R6 BLOCKED.** Remaining independent requirements:
(1) an owner-authorized direct live Linux receiver status and
configuration/versioning check, including any error and peer state;
(2) nested/default ACL inheritance or mask evidence for future received
files where needed; (3) independently protected backup coverage and a
successful hash-verified **trial restore** for each selected private
source family; and (4) a per-family exact-source/hash/consumer/rollback
approval package. Do not use successful replication, a synced receiver
or Git history as substitute backup evidence.

No private file, Syncthing configuration, credential, ACL, sender or
receiver root, service state, tracked runtime database or symbol
publication was moved, copied, changed or deleted in these checks.

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
`deterministic-outputs` job ID and visible name. It depends on
`fast-validation`, all `source-checks` native legs, and both
`determinism-container` legs. On a full validation, the download
pattern selects **only** the two pinned-container manifests and runs
the original fail-closed `tools.compare_determinism_manifests`.
Any missing artifact, missing version, unexpected artifact name,
or byte/hash difference still fails; no semantic equivalence fallback.
To expose independent determinism evidence when a native source-check
leg fails, this job may still run the byte comparator if fast-validation
and both pinned legs succeeded. Its final explicit native-result gate
then **fails the required job** unless the native matrix was green.
This retains the original release safety contract while preserving
actionable output from the pinned checks. The existing
`fast-validation.outputs.full` reuse policy avoids extra container
builds on an eligible previously validated baseline.

**Evidence / boundary:** Local structural tests assert the unchanged
native matrix, container host releases, exact checkout selection, pinned
runner/probe, both artifacts, unchanged strict comparison and a fail-closed
native result. The Windows/Linux developer-worker manifest v2 check
passed 10/10 at `40a7df27`. In the first actual hosted PR #29 run at
`e40e7545`, both pinned Ubuntu 24.04 and 26.04 jobs **passed**
and uploaded v2 manifest artifacts; GitHub reported identical SHA-256
for both artifact ZIPs. However, both completed native Ubuntu
Python 3.11/3.14 jobs failed earlier on
`tools.verify_deployment_assets --skip-svg` with:
`Runtime databases require rebuilding after input change:
src/infinity_db/army_reference_storage.py`.
The original `deterministic-outputs` job was skipped by its native
dependency; the follow-up job-condition fix lets the strict compare
execute without falsely turning the overall gate green. This native
tracked-release inconsistency is a **separate prerequisite** and must
be resolved before accepting the complete hosted workflow. A successful
hosted exact-byte comparison and fully green source checks have not
yet been demonstrated in this checkpoint. A full project suite or
production database rebuild was not triggered for this CI-only slice.
No private source data or tracked runtime DB was modified.

### Hosted strict comparison and tracked database rebuild — 2026-11-12

At `e2ff5eb4904188f0dcbbcfa59249c4b8b9d5a9a6`, the two independent
Ubuntu 24.04/26.04 pinned jobs passed and the hosted `Compare artifact hashes`
step in `deterministic-outputs` **passed**. Its native-source-result gate
correctly failed, as all four native source-check legs and deployment smoke
rejected stale tracked input provenance after the
`src/infinity_db/army_reference_storage.py` change. Do not weaken that gate.

The pinned Army source `data/raw/JSON 20260929-114335.zip` was independently
verified at SHA-256 `f103a7afd02e68d845cc9ce38b1948f46914676bbc6a5e6b790d0a04148b6c75`.
Two disposable complete builds at the same Git SHA passed 73 normalization
checks, the reviewed 116-warning baseline, 151 variant groups, 62 Weapons,
69 citations, 808 verified SVGs and 41 API baseline routes. All three SQLite
artifacts were byte-identical between both builds. An explicit pinned-source
rebuild of `data/generated/` then produced the same hashes:
`army.db=8d30dbb8bd05afaea8f09f055123fbee5e8ce436c9610283e08aee1cc280529c`,
`rules_n5.db=b7a29f4f6eb3f2e4f62ca6e10284ee4147eb91272c923694400fd7da5e3735d3`,
`its_18.db=e88eb6e9934443f762d8f143efcfd8cdf300636424b3a55c78df569ea43d2b94`.
The entire three-file hash verification passed and
`tools.verify_deployment_assets --skip-svg` returned exit 0.
Only the two tracked Army/Rules binary files changed; the ITS bytes remain
unchanged, and no private source or old raw archive was deleted.
Local acceptance also passed: deployment-script tests **47/47**,
database-set tests **23/23**, the complete symbol/deployment gate (**808/808**
published and **807/807** browser-referenced SVGs), Ruff, Pyright (0 errors),
Markdownlint, links/backlog checks and `git diff --check`.
The rebuilt set is ready for a reviewed commit and push. Fully green hosted
native checks, required comparator and deployment smoke on the new exact SHA
remain outstanding; this is **not** L1 approval or authorization for
ignored-data deletion.

### Production startup import boundary — 2026-11-12

Hosted deployment smoke at `6e796e4c` passed the previously failing
tracked-database provenance gate and built the Docker image, but failed its
runtime startup verification: importing `infinity_db.database.health`
eagerly imported `database.normalized_source`, which imported the
build-only `database.importer` and source normalizer. This attempted
to load `weapon-categories.json` from the removed build-time configuration
path `/usr/local/share/infinity-db/config/catalogs/`.
The production image must **not** restore these inputs to run.

The existing isolated subprocess regression
`tests/test_runtime_import_boundary.py` reproduced the failure before the
fix, enumerating all five imported build-only modules. The normalized-source
verifier now imports `validate_input` only while explicitly validating a
normalized source document, not when importing database/serving modules.
The runtime import regression passed **1/1** after this change.
The normalized/raw parity fixture in `tests/test_variant_usage_source.py`
also now selects explicit `include_raw=True`, in accordance with the
standalone Python export's rawless default. Its tests passed **6/6**
after the fixture correction. Neither change weakens source attestation.
Because `normalized_source.py` is a tracked database-build input,
the Army/Rules set was regenerated again. Two independent complete builds
passed 73 normalization checks and their **three physical SQLite SHA-256s
matched exactly**. The tracked rebuild passed exact hash verification:
`army.db=31e412bfeee453086b32a595e86b0554f94a36ae2b9c325fa543715d9f2c6382`,
`rules_n5.db=8ca2960bb4768dbbaf3568d29a00e9d2e6be42cb5c18e7dc671f98ec4484b911`,
`its_18.db=e88eb6e9934443f762d8f143efcfd8cdf300636424b3a55c78df569ea43d2b94`.
The full deployed-asset gate passed (808/808 published and 807/807
browser-referenced SVGs). The disposable Docker preview built the clean
installed image **without** the removed build configuration, passed
immutable-image verification and semantic parity for **41/41 pinned API paths**,
then stopped its test container and removed the preview image.
The complete-set builder regression suite passed **18/18**, including
repeatable publication, interrupted-replacement recovery and fail-closed
source-provenance handling. This demonstrates the startup repair locally;
hosted deployment smoke, source matrix and required comparator on the
next pushed SHA remain outstanding.

### Performance and testing tooling L0 disposition — 2026-11-12

**Scope:** Read-only review at clean `dev/tooling-workspace-cleanup`
`102af862` of **13 retained root Python modules**: six optional performance
commands and seven test-infrastructure helpers. Compared the current module
entry points, inputs, write behavior, direct imports, focused test consumers
and documented procedures. The initial 124-file private inventory and its
provisional destinations remain intake evidence, not migration authority.
This review does **not** approve the proposed `tools/performance/` or
`tools/testing/` layout.

**Performance: all six retain-active, with distinct purposes.**

- `analyze_chromium_timeline` remains the read-only, namespace-aware
  Chromium lock/queue timeline analyzer. It reads timestamped
  `slot-*.jsonl` and prints statistics, without constructing a synthetic
  timeline from legacy duration-only records. The browser-capacity tests
  import its reusable parsing and summarization functions.
- `sample_test_host_resources` writes bounded CPU/memory samples to a
  **new** `.jsonl` file beneath `local/benchmarks/` (exclusive create).
  `analyze_test_host_resources` independently verifies finished captures,
  exact test-window coverage and overlap-weighted metrics, reading the same
  restricted directory and printing JSON. The pair supports cross-host
  worker-capacity research; preserve their common path contract together.
- `benchmark_runtime` measures cold/warm SQLite repository read paths,
  emitting text or JSON to stdout. `compare_runtime_benchmarks` checks
  the separate before/after report format and comparable case identities.
  Neither writes a report file on its own; both remain opt-in measurement
  utilities, not release-performance gates.
- `benchmark_test_workers` executes repeated real tests through the
  canonical check runner, preserving worker/section/asset/scheduling
  inputs and run results. It has independent benchmark and regression
  consumers. **L0 output-path finding (since addressed by the
  [eleventh L2 slice](#eleventh-bounded-l2-output-contract-update--test-worker-benchmark-receipts-2026-11-13)):**
  its default is the ignored root `reports/TEST-WORKERS
  <timestamp>.json`; it formerly overwrote existing report files.
  The output collision contract now refuses old paths while preserving
  the default location and direct-script invocation. Any later path
  default cutover needs independent review; do not silently change
  historical report locations.

**Testing: all seven retain-active; they are not disposable benchmarks.**

- `browser_test_capacity` owns the pytest-xdist Chromium lane registry,
  cross-process slot locks and optional slot metrics. It is called by
  `tests/conftest.py` and browser timing utilities; its lock files are
  per-run pytest temporary state.
- `browser_test_host_profile` is the explicit, Linux-only local profile
  reader/enable/disable command used by `run_checks`. It writes/removes
  only the reviewed `local/browser-test-profile.json` state. Host-specific
  capacity defaults must remain opt-in.
- `browser_test_metrics` provides the optional timing hooks and
  capacity-owned browser pool used by live browser tests. It and
  `browser_test_capacity` append JSONL files when
  `INFINITYDB_BROWSER_METRICS_DIRECTORY` is set. **L2/L6 review:** that
  environment-selected directory is not itself restricted to the proposed
  `local/performance/` tree; preserve legitimate pytest temporary
  directories while clarifying ownership, lifetime and output policy.
- `browser_wsgi_transport` supplies live test and runtime semantic
  baseline WSGI request helpers; it has numerous independent current
  consumers and is not release-candidate scratch code.
- `pytest_startup_profile` is loaded by `tests/conftest.py` as a pytest
  plugin; it validates loadgroup compatibility, reports timings/waits and
  checks Chromium lane assignment without a persistent report file.
  `resource_waits` supplies its context-local counters and the browser
  slot recorder, not a standalone CLI.
- `test_sections` validates the tracked
  `config/testing/test-sections.json` registry for both
  `run_checks` and pytest collection. It is active test configuration,
  not an old diagnostic.

**Cutover guardrails:** The 13 modules remain at their current import
paths and preserve the existing tests and entry points. A future L4 move
must update `tests/conftest.py`, `run_checks`, direct-script invocation,
import graphs and `benchmark_test_workers`'s explicit runner script path
in one coherent slice. For L2/L6, prioritize output provenance/overwrite
safety and benchmark/pytest-temp exceptions, without deleting current
captures. No private data was opened for migration, moved or deleted in
this review, and no runtime/test code was edited. L0 remains open for the
other tool/document dispositions, private recovery/ACL decisions and
L1 policy approval.

### Hosted acceptance and operations tooling L0 disposition — 2026-11-13

**Hosted CI gate closed:** On exact pushed
`28a8e52ba1129315c1e7a359a121438f4ef34a9d`, GitHub Actions
[Source checks](https://github.com/frankysan/InfinityDB/actions/runs/43315597970),
[deployment smoke](https://github.com/frankysan/InfinityDB/actions/runs/43315597957)
and [installed-wheel smoke](https://github.com/frankysan/InfinityDB/actions/runs/43315597977)
all completed **successfully**. Source checks includes Windows/macOS Python
3.11, Ubuntu Python 3.11/3.14, both pinned Ubuntu 24.04/26.04 determinism
jobs and the required `Cross-platform deterministic outputs` comparison.
This closes the CI acceptance item in `TODO.md`; it does not approve L1,
relocation, ignored-source deletion, merge, release or deployment.

**Operations scope:** Read-only lifecycle/consumer/side-effect review at clean
`28a8e52b` of the **six** proposed `tools/operations/` root modules.
Compared command entry points, tests, documentation, source imports, operational
packaging and write paths. All six are **retain-active**, but their operational
state and output lifetimes differ; the initial category grouping is only a
proposed L4 destination.

- `capacity_test` runs a deliberately selected HTTP load against a deployed
  target, recording bounded aggregate latencies, statuses and synthetic
  requests rather than visitor histories. Its optional `--output` creates
  directories and **overwrites** an arbitrary JSON path; otherwise it prints
  a summary or full JSON. It is an opt-in performance/capacity operation,
  not a source or release gate. Keep the ability to couple it to a resource
  sample; later consider `tools/performance/` ownership instead of
  automatically treating the old proposed `operations/` category as final.
- `deployment_resources` collects bounded Linux host and Docker container
  measurements and can wrap an **explicit operator command**, recording its
  exit status rather than the wrapped command line. It requires
  `--output`, whose destination is unrestricted and overwritten.
  `deployment_diagnostics` independently parses existing Docker/Caddy/
  Gunicorn logs into capped, sanitized events, optionally using that
  resource report's exact time window. It also requires an unrestricted,
  overwriting output path. **Do not replace sanitized reports with raw-log
  archiving** or run these host-dependent commands during an L0 audit.
- `report_metrics` reads a selected trusted aggregate metrics endpoint
  and prints a current-generation operator report; its optional `--raw`
  writes only to stdout. The structured parser/aggregates are also consumed
  by `deployment_alerts`. That separate tool combines a recent
  `deployment_resources` report, two endpoint samples, health probes and
  explicit thresholds; it outputs JSON to stdout or a caller-chosen
  **overwriting** file. Its sampled evaluation is not itself a background
  monitor or complete observability service.
- `metrics_history` is an **active deployed service contract**, not a
  scratch database or another gameplay reference database. The dedicated
  `metrics-history` container continuously writes bounded,
  privacy-reviewed weekly aggregates into the persistent named Compose
  volume `metrics_history`, mounted at `/var/lib/infinitydb-metrics`.
  Its fail-closed normalized-route allowlist, retention limit, SQLite
  migrations and separate rollback semantics must survive any L4 change.
  The checkout CLI's **manual-only fallback** is
  `reports/metrics-history.db`, but the deployed service selects its
  own database with `INFINITYDB_METRICS_HISTORY_DATABASE`. Treat the
  default local report path as an L2/L6 writer-policy candidate, **not**
  authorization to relocate/remove the production volume. Retained
  history requires independently verified backup/restore before any
  service data migration or pruning beyond existing bounded retention.

**L0 output-path finding (subsequently partly resolved by the
[twelfth bounded L2 operational receipt slice](#twelfth-bounded-l2-output-contract-update--operational-receipt-family-2026-11-13)):**
At this inventory baseline, `docs/deployment.md` examples directed
capacity, resource, diagnostic, alert and manually collected history
files to ignored root `reports/`, and the four JSON receipt CLIs
overwrote existing files. The four commands now refuse collisions,
their example destinations are categorized under `local/`, and
their direct-script contract is covered. The separate, persistent
`metrics_history` state and any legacy material in root `reports/`
have **not** been relocated, deleted or reclassified.
Later path-default changes still require separately reviewed
operators, existing consumers and retention compatibility. Preserve explicit
cross-host destinations where justified, and treat persistent Compose volumes
as service-owned state outside the default checkout `local/` rule.

**Retirement/approval boundary:** The six commands have independent
current operating/research purposes and focused regression tests;
no retirement, module move, source input activation, Docker operation or
history volume mutation was performed. This was a read-only code/contract
review followed only by tracked documentation changes. L0 remains open for
the unreviewed tool/document classes and source backup/recovery exceptions.

### Published Army semantic-audit lifecycle review — 2026-11-13

**Scope:** Read-only L0 review at clean `dev/tooling-workspace-cleanup`
`f43f9ebb` of **seven** currently distinct published-application audit
commands and two shared helpers: `audit_fireteam_semantics`,
`audit_unit_semantics`, `audit_profile_semantics`,
`audit_loadout_semantics`, `audit_peripheral_semantics`,
`audit_relationship_semantics`, `audit_normalization_links`,
`payload_audit_common` and `paired_audit_connection`. Compared
module/schema ownership, tests, CLI behavior and current data-model
guidance. The earlier lifecycle decisions for `audit_army_faction_semantics`
and `audit_semantic_deduplication` remain valid and are not repeated here.

**Disposition: retain current independent semantics, not one tool per
historical migration.**

- `audit_unit_semantics` protects representative logical-Unit identity
  and source-context variations; `audit_fireteam_semantics` independently
  checks chart shapes, member resolution, FTO choices, Wildcards and
  Reinforcement-parent Fireteam type limits. These cannot be replaced by
  payload-deduplication counts or by a single generic schema validator.
- `audit_profile_semantics` and `audit_loadout_semantics` enforce
  canonical payload hash/occurrence/group consistency while preserving
  *contextual* AVA/logo and points/SWC differences. They share bounded
  `payload_audit_common` validation and identity helpers; keep those
  helpers with their consumers on any later module relocation.
- `audit_peripheral_semantics` checks definition, attachment and
  availability mechanisms without inventing controller eligibility;
  `audit_relationship_semantics` preserves Include target resolution,
  source-relative relationships, historical-endpoint scope and
  Reinforcement context. `audit_normalization_links` separately
  classifies source-filter joins, option-Weapon indirection and
  canonicalization/provenance mappings **without** treating player-facing
  relationships as disposable normalization.
- The last three commands depend on `paired_audit_connection`. Its
  reviewed, read-only `--normalized` route verifies application/source
  generation and reconstructs required tables in memory. Keep explicit
  input selection, zero-row/source-table fidelity, and fail-closed
  mismatched-source checks; **do not** call the known stale loose
  `data/generated/army.raw.db` a valid current audit input. Preserve
  separately justified legacy pair support until its retirement gate
  is approved.

**Actual current tracked-database probes (no writes):**
`audit_fireteam_semantics data/generated/army.db` returned exit 0 with
57 source charts, 268 teams and 1,249 members; its diagnostic report
contains **2 FTO source anomalies** and 12 non-local/unresolved member
resolutions, which must not be reclassified as audit execution failures.
`audit_unit_semantics` returned exit 0, finding 920 source / 737 logical
Units, 167 multi-source logical Units, four non-representative note-delta
groups and no invalid representatives. `audit_profile_semantics`
returned **PASS** for 5,020 occurrences / 1,108 canonical payloads;
`audit_loadout_semantics` returned **PASS** for 12,993 occurrences /
3,448 canonical payloads. These probes confirm maintained diagnostic
behavior; they do not replace pinned source verification or a full suite.
The three source-attached auditors were not run without a matching
explicit normalized input.

**Output/policy finding:** All seven optional `--output` writers use
caller-selected report paths with directory creation and nonexclusive
`write_text`, permitting overwrite of previous evidence. A plain
audit invocation does not require a persistent output file. L2/L6
should provide or document unique, classified `local/` evidence paths
and retain stdout/CLI compatibility. Keep source-attached diagnostics
under the source-research lifecycle and pure application audits under
model-validation evidence. Future consolidation must preserve each
semantic invariant and a current consumer; historical tests alone
are insufficient justification for keeping a completed wrapper.

**Documentation alignment:** The active `docs/data-model.md`
application-query summary still called the old `infinity.db`,
`rules.db` and `infinity.raw.db` filenames current. This checkpoint
changes only that live summary to the current `army.db`,
`rules_n5.db` and optional legacy `army.raw.db` boundary; frozen
historical research descriptions remain untouched. No audit source,
schema, runtime data, ignored file or output was modified in this
review. L0 and L1 remain open.

### Rules-curation and reference-validation L0 review — 2026-11-13

**Scope:** Read-only review at clean `dev/tooling-workspace-cleanup`
`221f4d2a` of six maintained entrypoints:
`audit_enrichment_coverage`, `audit_rules_interactions`,
`audit_maintained_text_links`, `source_coverage_dispositions`,
`audit_core_scenario_objects` and `audit_deployed_object_inventory`.
Compared current CLI paths, source/config owners, tests and consumers.
The separately documented `report_reference_baseline` disposition remains
**retain-active pending scoped extraction**; avoid repeating its already
reviewed historical inventories.

**Retain distinct current contracts:**

- `audit_enrichment_coverage` checks exposed Skill, Equipment, Weapon,
  Trait and State coverage against the paired Army/Rules databases and
  reviewed gap classifications. It remains an optional source/curation
  diagnostic, used also by the independent `audit_1_0_reference_inputs`
  and Weapon reviews; it does not grant semantic acceptance on its own.
- `audit_rules_interactions` is the **maintained generator and checker**
  of the tracked `docs/rules-interaction-checklist.md`, with explicit
  release-catalog scope, review-policy and database-drift contracts.
  `tools.run_checks --stage rules` invokes its read-only checklist
  check and existing review-release gate. Preserve `--check-output`
  and the separately **explicit, potentially writing**
  `--output`/`--refresh-catalog-scope` workflows, including the
  tracked generated checklist and reviewed catalog-scope config. Those
  accepted tracked outputs are **exceptions** to the general ignored
  `local/` report policy; do not relocate them as scratch evidence.
- `audit_maintained_text_links` is a small stdout-only diagnostic
  around `infinity_db.maintained_text_policy`; the production policy
  and `tests/test_maintained_text.py` protect the live text/semantic-link
  contract independently. Retain the useful direct owner/residual/marker
  report for now; review CLI consolidation only if its diagnostic
  capability stays discoverable and callable.
- `source_coverage_dispositions` validates four fingerprinted,
  clause-scoped review records from the tracked disposition manifest.
  It uses the reporter's maintained explanation inventory rather than
  repeating source parsing. **Fingerprint validity is not source-wide
  completeness, browser approval or a new v1.1 release gate.**
  Keep until a replacement preserves exact-source identity, dependency
  and sign-off refusal semantics; do not retire it solely because V1S-082
  belongs to a finished release.
- `audit_core_scenario_objects` protects the **four N5.3 core-scenario**
  objective/Marker domain boundary against the embedded deployed-object
  publication. It is not the ITS Season 18 scenario pipeline and must
  not infer Weapon/Equipment profiles from Consoles or Supply Boxes.
  It prints to stdout only; retain for pinned source/domain revisions.
- `audit_deployed_object_inventory` is a **thin developer CLI and
  compatibility import surface**, with the maintained logic in
  `infinity_db.deployed_object_inventory`. The explicit Army/curated/
  delivery/candidate/source-clause review inputs are still useful.
  At L4, simplify or retire the wrapper only after replacing its
  independent developer command, two test consumers and documented
  source-review workflow. Do not retain duplicate algorithms or invent
  new object identities.

**Read-only acceptance at the reviewed SHA:** The interaction
`--check-output` returned 0, confirming the historical **0.7.0**
checklist's 182/182 primary and 225/225 supporting reviews; this is
not an assertion about the separate explicit 1.0 primary scope.
Maintained-text inspection returned **0** unlinked candidates and
**0** reviewed-batch residuals, with one intentionally explicit
`trait:silent-x` `scope-unclear` marker. The dispositions CLI
validated **4** scoped reviews and issued **0** whole-record/browser
approvals. The core-object audit confirmed **4** scenarios,
**4** Domination Consoles, **3** Supplies Supply Boxes and **17**
independently reviewed deployed objects.

Focused regression suites passed **111/111**, no skips:
enrichment **17**, interactions **15**, maintained text **39**,
source dispositions **23**, core scenario objects **10** and
deployed-object inventory **7**. No CLI was invoked with a writing
flag, and no pinned private source was altered.

**L2/L6 output distinction:** Optional enrichment `--output` and
deployed-object `--json-output` use nonexclusive `write_text` on a
caller-chosen destination and can overwrite prior generated evidence;
the latter does not create its parent directories. Leave these
interfaces compatible until L1 approves unique, domain-scoped
`local/` output destinations and retention/overwrite rules.
Source dispositions, maintained-text and core-object CLIs are
stdout-only. The tracked checklist generator and review-policy
refresh are separately authorized maintainer operations, not ignored
run reports. No tool, curated fact, generated checklist, private
source, database or publication changed; **L0/L1 remain open**.

### Tracked document lifecycle review and runbook alignment — 2026-11-13

**Scope:** Reviewed the **33** tracked `docs/` entries against the
[documentation authority map](README.md), current consumers, maintained
source/release evidence and the existing earlier L0 dispositions.
No wholesale document retirement follows from a completed milestone
or a version suffix. `docs/` is not an archive for generated private
reports, but it does legitimately contain reviewed, source-pinned evidence.

- **Retain as current contracts:** the canonical architecture, data model,
  application/project domains, browser design, CI, testing, deployment,
  server migration, release, backlog, coordination, Syncthing, validation
  queue, agent context, changelog and documentation-map owners. Rules
  semantics/research, official clarifications and N5 source history own
  current research/evidence interpretation, not a competing task ledger.
  `its-season-database.md` describes the active season schema while
  `season-publication-ownership.md` preserves cross-domain ownership;
  their completed P3 chronology is **not** current implementation work.
- **Retain as uniquely source-pinned historical evidence:**
  `faq-v0.1-scope-inventory.md`; the main `rules-explanation-audit-1.0.md`
  and its inventory, N5.3 reconciliation and source-manifest appendices;
  and `v1.0-source-coverage-audit.md`. They hold question identities,
  REA/SRC finding and source-version locators, reviewed scope boundaries
  and accepted test/route evidence that cannot safely be replaced by a
  generic release summary. Keep their historical-status labels, not
  duplicate live work in them.
- **Completed plan retained pending bounded disposition:**
  `restructuring-plan.md` is P0–P6 historical implementation/acceptance
  evidence, not a current runbook; it has independent links and recorded
  decisions. `v1.0-coverage-workflow-plan.md` is a **specific tracked
  retirement candidate after L1 approval**: V1S-082's release scope is
  owned by `releasing.md`, optional future source-first work by
  `TODO.md`, the selected 35-record cohort and four clause-scoped reviews
  by their tracked `config/validation/` manifests and validator, and
  the measured benchmarks/source discoveries by
  `v1.0-source-coverage-audit.md`. The last source-audit link to the
  historical plan now targets the exact tracked pilot manifest, with
  original constraints retained in the audit. Before deleting, rerun
  a repository-wide backlink/unique-methodology review and docs/link
  checks; Git history supplies the finished execution narrative.
- **Separate extraction candidate, not a deletion target:** `testing.md`
  remains the active check guide but contains substantial revision-pinned
  1.0 test transcripts. Later narrow the *current commands* section and
  classify the original acceptance evidence with source audits/CI rather
  than treating the entire 11k-line document as either obsolete or
  current instruction. Preserve existing deep links during that work.
- **Correct active operator guidance now:** `server-migration.md` still
  claimed current tracked `variant-usage.json` and
  `weapon-profile-sources.json` sidecars, v8/v9 deployed-object export
  and a schema-specific staging bundle. These are no longer the selected
  runtime contract: the verified Dockerfile copies `army.db`,
  `rules_n5.db` and `its_18.db` directly. The migration guide and
  `deployment.md` introduction now agree with the three-file release
  requirements; history/backup volume handling is unchanged.

**Boundary:** This is L0 classification and a narrowly scoped
documentation correction. It does not authorize deletion of the old
V1S-082 plan, wholesale shortening of audit evidence, ignored-data
migration, L1 policy approval or any deployment.

### CI, release and browser entrypoint L0 follow-up — 2026-11-13

**Baseline:** Clean `dev/tooling-workspace-cleanup` at
`684217c3edea1396888c9337d9c79ae0e8d92264`. The current root
`tools/` contains **120 Python files and one `templates/` directory**
(exact current listing; earlier intake counts describe earlier revisions).
This bounded supplement reviews ten release/CI entrypoints not all
individually covered by the [earlier release-tool checkpoint](#release-tool-lifecycle-and-correctness-checkpoint--2026-11-12).
It does not restate the previously accepted browser-verifier correction.

**Retain with explicit category/consumer ownership:**

- `ci_preflight`: optional clean-index export, packaging and isolated-wheel
  preflight; exports the indexed bytes into an automatically removed temporary
  directory and may install/download packages in the explicitly requested
  isolated mode. Its direct script path appears in `testing.md` and in
  `tests/test_run_checks.py`; do not move it without updating those users.
- `release_metadata`: finalized *release-only* version/date/changelog
  consistency gate, intentionally not a routine unreleased-branch PR check.
  `prepare_release_ci_evidence` imports its verifier and
  `releasing.md` calls it before the release handoff.
- `release_validation_scope`: fail-closed change-aware Source CI classifier.
  The hosted workflow invokes it directly, and it requires verified
  exact-base hosted evidence through `prepare_release_ci_evidence` before
  reusing a narrower documentation/test-only scope. Unknown paths, missing
  evidence and source changes retain the full check matrix.
- `prepare_release_ci_evidence`: checks exact-SHA required GitHub workflow
  conclusions, release metadata and optional full-asset/cross-browser
  requirements; its evidence JSON and annotated-tag text are **release
  records**, not disposable benchmark logs. It makes explicit GitHub API
  requests and creates directories for two user-selected output files.
- `run_cross_browser_compatibility`: active opt-in multi-engine test runner
  used by the cross-browser GitHub workflow, with an explicit browser rather
  than silently skipped missing engines. At this L0 baseline, its **fixed**
  `local/cross-browser-compatibility/junit.xml` could overwrite previous
  evidence; the subsequent
  [third L2 output update](#third-bounded-l2-output-contract-update--cross-browser-evidence-2026-11-13)
  now uses fresh, revision-pinned per-engine directories and a matched
  browser failure-artifact destination without weakening CI failure gates.
- `verify_release_candidate_browser`: explicit-version hosted Unit/browser
  acceptance, bound to the complete three-database snapshot and static
  revision; retains JSON-only success evidence through optional
  `--json-output`, which currently overwrites a caller-selected file.
  Keep the release-only operator check distinct from ordinary unit tests.
- `installed_wheel_smoke`: installed-package runtime and CLI validation,
  called from hosted `installed-wheel.yml` and isolated `ci_preflight`.
  Its temporary fresh wheel environment and controlled removal of
  **installed test-environment** build assets are not private-source
  deletion. Preserve the direct-script and isolated-interpreter contract.
- `verify_checkout_server`: ephemeral loopback checkout server and
  pinned 41-route semantic baseline; a selected database directory must
  remain complete. Temporary server logs are not retained by default.
- `preview_runtime_image`: isolated Docker build from explicitly selected
  complete databases with immutable-image and HTTP semantic checks.
  Creates/removes its own `local/` temporary context, disposable image
  and test container; never treat this as deploy authorization.
- `run_pinned_determinism`: shared digest-pinned Linux/amd64 reproducibility
  runner used by `source-checks.yml`. Its manifest may only be written
  beneath `local/`; the caller still chooses a potentially colliding
  filename, so enforce run identity/nonoverwrite in a later L2/L6 slice.
  A `--probe` may pull the pinned Docker image, but the actual comparison
  container has no network access or checkout-write mount.

**Writer and cutover findings at this L0 baseline:** The release runbook
then selected `reports/release-ci-v<version>.json` and
`reports/release-tag-v<version>.txt`. The later
[bounded L2 release-evidence update](#second-bounded-l2-output-contract-update--release-ci-records-2026-11-13)
recommends `local/validation/` and adds collision refusal without
removing historical explicit path support. The cross-browser JUnit and
release-candidate JSON collisions are addressed by the later
[third](#third-bounded-l2-output-contract-update--cross-browser-evidence-2026-11-13)
and [fourth](#fourth-bounded-l2-output-contract-update--release-candidate-json-2026-11-13)
L2 output changes, without relocating pre-existing evidence.
`release_validation_scope` writes to GitHub's workflow-controlled
output file in append mode; that provider-owned step contract is a
narrow **external output exception**, not a general ignored path.
Future L4 renames must update module imports, `-m` commands, direct
script invocations in YAML and tests, and GitHub workflow consumers
atomically. Preserve verified exact-SHA validation and all failure gates;
historical tests alone are not the reason to retain any tool.

**Focused acceptance:** At this pinned SHA the hermetic suites passed
`test_release_ci_evidence.py` **23/23**,
`test_release_validation_scope.py` **4/4**,
`test_run_pinned_determinism.py` **4/4**, and
`test_release_metadata.py` **3/3**: **34 passed, zero skips/failures**.
No Docker build, hosted browser check, release-tag generation or network
release-evidence collection was executed in this L0 review. No private
source, runtime publication or CLI implementation changed.

### Source-provenance and ITS pilot tool L0 review — 2026-11-13

**Baseline:** Clean `dev/tooling-workspace-cleanup` at
`779e36e31c5d5ca37f15e119cf5e050bbc2977e4`.
This review covers **five** additional root commands absent from the
individual L0 dispositions. Their private source requirements, exact
consumers and writer behavior matter more than historical tool age.

- **`audit_auxiliary_silhouette_provenance` — retain as active,
  source-pinned discrepancy reproduction.** This is a seven-object N5.3
  Silhouette comparison across English/Spanish printed PDF rows, separate
  Wiki chart/dedicated pages and matching Army metadata. It deliberately
  refuses to infer gameplay precedence. The source discrepancy remains
  relevant to reviewed research; retiring the independent reproduction
  would lose provenance checks. Explicit `--pdf-en`, `--pdf-es`,
  `--wiki-en`, `--wiki-es` and `--army-db` inputs are required.
  Both required JSON/Markdown output paths currently create parent
  directories and **overwrite** existing files. Preserve source hashes,
  language/revision scope, per-context values and open clarifications
  before any future consolidation.
- **`audit_pdf_revision_deltas` — retain as optional source-history
  triage, not a semantic equivalence test.** It compares 11 declared PDF
  revision pairs (N5, FAQ, ITS) using text-token windows, checking each
  ignored PDF's exact SHA-256 against
  `local/pdf-revision-inventory.json`. It defaults to historical
  `data/pdf/` input and a **fixed, overwriting**
  `local/audits/pdf-deltas-2026-11-06.json` report. These locations need
  explicit L2 reader/writer migration without silently selecting another
  revision by filename or mtime. Current candidate findings are owned by
  `docs/n5-source-history.md`; the tool remains useful for subsequent
  revisions but cannot approve gameplay changes. **Gap:** no dedicated
  `tests/test_audit_pdf_revision_deltas.py` exists. Before changing its
  path handling, add bounded synthetic extraction/CLI tests; rerun any
  private source-dependent check only with authorized exact inputs.
- **`audit_source_variant_inputs` — retain for unresolved
  Skill/Equipment occurrence and Extra-owner research.** Its
  `--normalized` path uses the verified normalized-generation adapter,
  while explicit `--raw` uses the strict same-generation database-pair
  check; never accept a mismatched legacy `army.raw.db`. It defaults
  the application and Rules to tracked `army.db` and `rules_n5.db`,
  but without `--normalized` it still selects the legacy
  `data/work/build/army.raw.db` raw source. **L2:** replace this implicit
  legacy default with a deliberate, fail-closed source-selection contract
  in coordination with the standalone raw-format retirement. Do not
  choose ignored normalized data automatically or remove the raw path
  while independent paired-export research requires it. The CLI prints
  JSON to stdout only; no report file is created.
- **`audit_trait_wiki_anchors` — retain as offline source-link review.**
  It compares curated exact Trait fragment IDs to a user-supplied saved
  `/Traits` HTML page and fingerprints that input; its optional
  `--inventory-unmapped` yields review candidates, never writes new
  destination URLs. Optional `--output` currently **overwrites** an
  existing path and requires its parent to preexist. Keep this separate
  from normal live-Wiki availability and browser rendering tests; a
  previous saved page is not proof about the current website. Migrate
  examples in `docs/testing.md` to run-identified `local/research/`
  after L1, without downloading sources implicitly during tests.
- **`verify_its_pilot_parity` — retain as an independent isolated ITS 18
  parity gate.** It builds a temporary `its_18.db` beneath
  `local/`, selects the tracked season/revision and tests all six
  Battleground API-JSON variants and 24 source-rendered SVG byte
  combinations against the complete selected Army/Rules/ITS runtime.
  It removes its own scratch directory on completion; output is stdout
  JSON, not a persistent report. It does not create another serving
  authority, change the tracked ITS file or authorize deployment.
  Preserve this source-versus-published independence even when the
  earlier P3 milestone narrative is retired.

**Focused acceptance at the pinned SHA:** The hermetic and selected
source-dependent regressions passed:
`test_audit_auxiliary_silhouette_provenance.py` **4/4**,
`test_audit_source_variant_inputs.py` **45 passed / 61 skipped**,
`test_trait_wiki_references.py` **22/22**, and
`test_verify_its_pilot_parity.py` **2/2**. Total **73 passed,
61 skipped**, no failures. The auxiliary silhouette suite also
exercised its available pinned source fixtures, whereas skipped
source-variant cases are **not** acceptance evidence. The PDF-delta
command was intentionally **not** rerun on private PDFs or its
fixed historical output path. No private bytes, generated publications,
source manifests or CLI implementations changed in this review.

**L1 implication:** The five tools do not justify a general
`tools/research/` rename yet. Their explicit source identities and
optional raw-format dependency must be mapped alongside L2 path
migration, and outputs must distinguish immutable research evidence,
temporary parity work and stdout diagnostics. No retirement or
physical relocation is approved.

### Browser-acceptance and shared-helper ownership review — 2026-11-13

**Baseline:** Clean `dev/tooling-workspace-cleanup` at
`5772f5b9a1b4236b1f384489fbaf5fa18f03176a`. Reviewed 11 optional
catalog/detail/Unit browser entrypoints and four shared project helpers
against current source/test/CLI consumers and report-writing behavior.
The earlier verified complete-set release-candidate browser gate remains
its **own** acceptance contract; do not replace it with these spot/scope
checks or silently promote optional commands into default hosted gates.

**Retain independently scoped browser acceptance:**

- **Catalog navigation family:** `verify_ammunition_browser` owns the
  shared Chromium catalog-to-detail implementation, which is imported by
  `verify_general_rules_browser`, `verify_labels_browser`,
  `verify_states_browser` and `verify_traits_catalog_browser`.
  The four thin entrypoints still select **different authoritative
  identities** (qualified General Rules, source Labels/States, canonical
  Traits with exact Wiki URLs and raw Trait labels); these are
  independently valuable acceptance scopes, not four obsolete copies
  of the browser loop. An L4 layout change must update all four
  imports and direct commands together. Preserve pinned catalog
  minima and fail-closed route/name/URL reconciliation; do not invent
  one merged generic public release gate.
- **Army/profile specializations:** `verify_hacking_programs_browser`
  checks the published 12-program structured presentation and offers
  explicit `--self-host`. `verify_non_skill_army_browser` checks
  source-derived Equipment, Training, Marker and attribute-override
  placement for seven pinned Unit cases; those `CASES` and `WIDTHS`
  are imported by `verify_unit_skill_presentation_browser`. The latter
  additionally checks shared/specific Unit rows, optional availability
  flags, exact link targets, distance rendering and narrow viewports,
  reusing `browser_wsgi_transport.route_browser_page`. Preserve
  its externally used case identity and the optional filter/viewport
  controls on relocation.
- **Interaction/special layout checks:** `verify_rule_fragment_browser`
  discovers actual Weapon/Glossary rule-fragment hrefs and follows
  rendered links, with an opt-in loopback `--self-host`. It
  participates in Chromium lane/slot tests; keep its test isolation.
  `verify_structured_skill_charts_browser` tests data-driven Martial
  Arts/Booty/MetaChemistry rows instead of assuming text screenshots
  provide source-table parity.
- **Trait external-link boundary:** `verify_trait_wiki_browser`
  exercises actual popup/hash scrolling using a **supplied saved**
  Wiki HTML snapshot, which it does not fetch from the network.
  `verify_traits_catalog_browser` separately checks local catalog
  rendering against curated Wiki destinations. Keep the offline
  `audit_trait_wiki_anchors` source check, the local catalog browser
  check and the snapshot-backed popup browser check distinct: none
  establishes current third-party uptime.

**Shared helper ownership and L4 import cutovers:**

- `path_sanitization` has two currently observed direct `tools/`
  consumers: `symbol_source` and `symbol_publication`.
  Prefer colocating with the symbols tools unless an independent
  cross-domain consumer is demonstrated; its Windows/macOS/Linux
  filename normalization contract is **not** a generic path traversal
  permission. Preserve unit tests and case/Unicode handling.
- `asset_validation` owns selected symbol-manifest/static SVG hash
  and alias validation for `run_checks`, `build_full_asset_bundle`,
  `stage_full_asset_bundle`, `promote_symbol_publication` and
  `verify_deployment_assets`. It belongs at the shared
  symbols/testing/CI boundary, rather than retiring merely because
  the external symbol processor now owns rendering. Preserve
  off/auto/required and browser-referenced asset semantics.
- `served_runtime` returns a strict in-memory
  `/api/version` identity assertion, shared by
  `report_reference_baseline` and
  `verify_release_candidate_browser`. Keep fail-closed origin
  validation and exact snapshot comparison, without creating a
  duplicate version verifier under separate categories.
- `runtime_semantic_baseline` independently pins the selected
  database set's HTTP/HTML/SVG semantic surface, consumed by
  `verify_complete_database_build`, `verify_checkout_server`,
  `preview_runtime_image` and its own tests. Retain it as the
  offline/loopback parity reference, distinct from actual Playwright
  user interaction and hosted release verification. Its tracked
  fixture and explicit artifact-key normalization are part of the
  test contract.

**Confirmed L2/L6 report issue at the L0 baseline:** All eleven browser
commands offered `--output` with direct `Path.write_text` semantics
and no exclusive-create guard. Some created parent directories while
others required them. The later
[seventh bounded L2 slice](#seventh-bounded-l2-output-contract-update--catalog-browser-receipts-2026-11-13)
now covers five catalog entrypoints; six specialized entrypoints remain
unmigrated and require separate review.
Treat optional JSON as per-candidate, per-browser and per-run
validation evidence under an approved `local/validation/` path.
Keep stdout-only invocation useful, preserve nonzero exit on failed
cases, and avoid overwriting accepted release/baseline receipts.
`verify_trait_wiki_browser` also takes an explicit private saved
HTML input; never silently fetch or publish that source while
migrating its output. Browser suite invocation and reference
baseline fixture semantics need separate migration tests.

**Focused validation at the pinned SHA:** Browser fragment
`tests/test_verify_rule_fragment_browser.py` **12/12**;
Unit presentation `tests/test_verify_unit_skill_presentation_browser.py`
**34/34**, including local live-Chromium optional-filter, distance,
contextual relationship and Spec-Ops cases;
`tests/test_path_sanitization.py` **2/2**;
`tests/test_asset_validation.py` **12/12**; and
`tests/test_runtime_semantic_baseline.py` **10/10**. Total
**70 passed, zero skipped or failed**. This is focused coverage
for the reviewed dependency interfaces, **not** a complete
all-engines/hosted release/browser-acceptance run. No private source,
retained browser report, static publication, tool import, GitHub
workflow or production runtime was modified.
All proposed L4 moves remain **pending L1 decision and atomic
consumer cutover**.

### Exact root-tool reconciliation and remaining L0 gaps — 2026-11-13

**Inventory boundary:** At clean `dev/tooling-workspace-cleanup`
`c05c9bd035a0f8aaa4981e6475ecea78a23e1f60`,
`tools/` has **120 Python files plus one HTML template directory**.
A literal filename-stem comparison against the entire 3,095-line L0
cleanup plan found **97** modules already named and **23** not
individually named. A mention is only a *coverage signal*, not proof
that every import, consumer or ignored output has been reviewed.
The 23 omitted names are reconciled below without inferring retention
from tests alone. The template is explicitly owned by
`build_symbol_artwork_review` and must move with that generator.

**Reconciled root modules and disposition, with current purpose:**

- **Optional agent workspace tooling — retain available, not
  mandatory:** `agent_workspaces` creates scoped clean-checkout
  worktrees and enforces a marker/branch guard;
  `agent_coordination` provides per-Git-common-dir cooperative claims,
  and `agent_global_coordination` provides optional fast-forward-only
  cross-host Git-ref claims. They are cross-dependent, documented under
  `docs/multi-agent-workspaces.md`, and test-backed. Neither active
  claims nor these installed tools automatically enable the optional
  protocol for ordinary development. **L4 portability issue:**
  `agent_workspaces.create` still defaults to
  `dev/v1.0.0`; do not change to a guessed current branch without
  preserving explicitly pinned alternate-branch call sites/tests.
- **Source provenance and publication validation — retain active:**
  `army_snapshot_source` verifies immutable Army ZIP/manifests in the
  offline consumer; `audit_restrictions_source_chart` verifies
  exact N5.3 Chart scope, 14 source-only negative conditions and the
  tracked public projection; `build_weapon_profile_publication` is
  now a **read-only embedded Weapon citation verifier**, despite the
  historical builder-like name; `build_its_season` is an opt-in
  standalone isolated ITS database builder and checker, **not** a
  replacement for `infinity-db build`. L2 must move its default
  ignored `data/work/its/its_18.db` output to a reviewed
  `local/work/` destination while retaining its refusal to replace
  tracked `data/generated/` publications. L4 may rename the
  misleading Weapon verifier after direct-module consumers and
  maintained commands are updated.
- **Current documentation/CI/backlog infrastructure — retain
  with bounded future generalization:** `check_doc_links`
  is active in both Docs stage and hosted Source CI;
  `check_v1_backlog` still owns strict historical V1S validation
  for the Docs stage and is imported by `dev_status` and
  `check_v1_backlog_ci`. The latter remains an **active hosted
  Source CI** first-parent-aware retirement gate, even when the
  current backlog has zero V1S declarations. `dev_status` is a
  useful read-only snapshot of checkout, queues, MCP and exact-SHA
  workflow summaries. A future generic backlog implementation
  must preserve the historical closeout/merge behavior, not
  simply remove all three modules because 1.0 has shipped.
- **Separate symbol producer handoff — retain the independent
  verifier chain:** `export_symbol_source_plan` derives
  authoritative, pinned raw-SVG URL/path requests; its
  `export_symbol_override_lookups` consumer separately pins
  approved override lookup paths. Both use idempotent immutable
  output with differing bytes refused. `verify_raw_symbol_handoff`
  checks downloaded ZIP/source reports; `verify_effective_symbol_handoff`
  checks override-stage provenance;
  `verify_symbol_duplicate_handoff` validates the duplicate and
  font-audit receipts; `verify_processed_symbol_handoff` verifies
  the compressed/canonical artifact. `prepare_symbol_publication`
  verifies all required external receipts and creates a **new,
  exclusive candidate directory** without publishing into the
  tracked runtime. These seven tools/steps cannot be replaced by
  success from the external `InfinityDB-symbol-tools` producer
  alone: the consumer must independently verify source/handoff hashes,
  transformations, missing assets and typed publication identities.
  Their input path literals and companion files are part of L2
  cross-repository handoff negotiation.
- **Weapon audit shared helpers — retain with the auditors:**
  `weapon_chart_source` extracts rows from the *specific*
  N5.3 chart page layout; `weapon_source_common` provides
  constrained name/mode identities and source hashes; and
  `weapon_source_metadata` reads published Army Weapon metadata
  without mutating it. These have active Weapon/source-audit imports;
  they are not standalone build entrypoints and should move as one
  compatible `tools/research/` slice, if that layout is approved.
- **Low-usage tools — two explicit L5 decision candidates:**
  `probe_docker_test_host` is an optional, bounded, read-only
  Docker availability diagnostic, documented for Windows test-host
  triage, with no other current `tools/` importer.
  Retain provisionally until an independent operator/MCP diagnostic
  replacement is demonstrated; its tests alone do not determine
  the disposition. `symbol_raster_validation` contains optional
  Python/Pillow and external-renderer visual-comparison helpers, but
  no current `tools/` import and no standalone CLI; only its
  focused test consumer was found. It is the **stronger tracked
  retirement/extraction candidate**, subject to verifying that
  `InfinityDB-symbol-tools` independently owns the needed
  raster/source-parity workflow and that current publication checks
  do not require these helpers. Do not delete it or its tests merely
  because it is unreferenced by another Python module.

**New acceptance at the reviewed SHA:** Independent read-only
`audit_restrictions_source_chart --check-publication` returned
**6 rows, 14 negative conditions, 7 unmodeled typed edges and
2 conditional relation warnings** (not gameplay-legality approval).
`build_weapon_profile_publication` verified **69 embedded profile
citations**. Six focused test modules passed **52/52**, no skips:
`test_export_symbol_source_plan.py` **6**;
`test_check_v1_backlog_ci.py` **12**;
`test_prepare_symbol_publication.py` **10**;
`test_symbol_raster_validation.py` **2**;
`test_agent_workspaces.py` **7**; and
`test_game_mode_source_table.py` **15**, including live Chromium
Restrictions coverage. Neither the separate symbol producer nor
private input archives were accessed for this acceptance.

**Residual gaps ranked for subsequent review:**

1. **L1 blockers outside code:** backup/restore proof, classification
   of 19 inaccessible `reports/` directories, live Windows Syncthing
   sender state, and receiver/source-path rollback evidence remain
   unverified; no private-data move or deletion is authorized.
2. **L2 output/reader contract:** address the explicit ITS
   `data/work/` default, source PDF/normalized/raw selectors,
   source-plan/producer boundaries and per-run nonoverwrite policy
   before any physical migration. The independently validated
   source ZIP/published SQLite bytes must remain stable.
3. **L4/L5 bounded design:** decide root CLI exceptions and exact
   atomic imports/CI/docs updates, then confirm whether the two
   low-usage diagnostic/raster helpers and the historical V1S
   wrapper can safely consolidate. A test-only reference does not
   by itself justify indefinite retention or immediate deletion.

**Result:** Every currently enumerated root module is now **named**
in this plan, with the 23 prior omissions explicitly classified.
The full per-file private inventory remains the source for byte
hashes, owner-specific recovery and L3 migration decisions.
This is **not** L0 exit: standalone/external consumers, unknown
private directory contents and independent backup/restore proofs
remain pending. No files, runtime behavior, generated sources,
remote workspaces, installed plugins or service state changed
during this review.

### Cross-repository producer and raster ownership verification — 2026-11-13

**Repositories checked read-only:** InfinityDB at
`eb272cd2eb3347211a14b04e9b72d3b002af10dd`,
`InfinityDB-symbol-tools` at
`a3420a40922970090d6710515b052f49b9bec629`
(clean `main`), `InfinityDB-army-acquisition`,
`InfinityDB-wiki-acquisition`, and `mcp-lab` at
`8c426443ea9a21a99373dc64b19825f10b2e50f4`
(clean `main`). This verifies **implementation/ownership**, not a
complete acceptance of private source artifacts on either host.

**Raster duplication resolved as an ownership decision:**
`InfinityDB-symbol-tools/src/infinity_symbol_tools/svg_compress.py`
contains the same resvg/Inkscape rasterization, Pillow RGB RMS/changed-
pixel comparison over *both black and white backgrounds*,
`VisualMetrics`, and multi-size/DPR `RasterValidator` implementation
as InfinityDB's `tools/symbol_raster_validation.py`. The producer
actually calls this implementation from
`svg_canonical_compression.py` to produce pinned compression receipts,
and has compressor/receipt tests. In the InfinityDB checkout the duplicate
module has **zero other `tools/` consumers**, no CLI, and a
two-test historical suite. **Proposed L5 disposition: retire that
duplicate module and its redundant tests as a bounded tracked-code
slice, after explicitly approved removal with a complete import/CI/
docs/packaging scan.** Git history preserves its implementation;
do not vendor it into InfinityDB again during L4.

**Do not equate the producer's visual approval with independent
application acceptance.** InfinityDB's
`verify_raw_symbol_handoff`, `verify_effective_symbol_handoff`,
`verify_symbol_duplicate_handoff`,
`verify_processed_symbol_handoff` and
`prepare_symbol_publication` independently validate the pinned
source/receipt hashes, complete ZIP/CSV membership, XML/no-active-text
and publication identities. `verify_processed_symbol_handoff`
explicitly does **not** re-render or repeat the producer raster
comparison. Neither the unused duplicate module nor its removal
establishes new cross-host **post-publication visual parity**.
If new artwork acceptance requires that guarantee, specify a
separate, bounded image-comparison/reviewer gate with exact candidate
and reference hashes, source assets, renderer/version/tolerances,
review receipts and corresponding tests; do not silently claim an
existing source-hash verifier tests appearance. Preserve the
previously accepted artwork/publication cutoff independently.

**Confirmed external L2 path contracts:**

- `InfinityDB-symbol-tools` raw-acquisition CLI defaults to
  `data/raw/symbols` and `data/manifests/snapshots`; its README's
  intermediate commands select `data/effective`,
  `data/intermediate` and `data/reports`. Actual newer
  `tools/run_production_compression.py` uses
  `local/p5-production-processed/<EFFECTIVE-SYMBOLS stem>/`.
  Those are **mixed conventions in one producer** and must be
  reconciled together, not treated as a ready-to-apply source move.
- `InfinityDB-army-acquisition` CLI still defaults to
  `data/raw` and `data/manifests/snapshots`.
  `InfinityDB-wiki-acquisition` CLI still defaults to
  `data/wiki`, `data/work/wiki`, and
  `data/manifests/snapshots`. They are **separate repositories**:
  implement any producer default change there in individually
  reviewed commits with their own CLI tests, docs, immutable
  ZIP/manifest provenance, and consumer pairing checks. Do not
  rewrite old manifests or infer receipt identity from paths.
- The `mcp-lab` execution interface accepts tracked `tools.*`
  entrypoints by string and knows several browser/test runner
  allowlists, so InfinityDB L4 moves must update the MCP-allowed
  module/job behavior and direct script invocations at the same
  cutoff; no local MCP imports of `symbol_raster_validation`
  were found. The installed MCP gateway did not accept a focused
  `InfinityDB-symbol-tools` pytest invocation through either
  permitted test-job route (reported `validation_unknown`).
  **Do not claim producer pytest was executed in this review.**

**Cross-repository acceptance before L2/L5:** Obtain compatible
current producer `pytest` results and the exact source/processed
handoff receipts; verify InfinityDB's independent read-only
candidate/source checks; exercise new writer/reader defaults in a
scratch path with intentionally colliding filenames; preserve exact
selected inputs and no-network normal build; validate Windows/Linux
receiver activation on the approved source family. No producer,
application, MCP, ignored asset or service files were changed.
**L0 physical-data recovery blockers and L1 approvals remain open.**

### L1 candidate policy decisions — P accepted for new work

**Accepted 2026-11-13 for new work only:** Adopt the stated
`local/data/`, `local/research/`, `local/validation/`,
`local/performance/`, `local/operations/`, `local/work/` and
`local/handoffs/` intent as the **default for newly produced ignored
project artifacts**, with domain/purpose/scope/run-ID paths and
nonoverwriting outputs. Keep tracked curated inputs, source-review
manifests, reproducible publication receipts and three runtime SQLite
files where they are. Keep `tools/run_checks.py` and package
`__init__.py` as proposed minimal root exceptions; defer all actual
`tools/` moves until per-module L0 and complete consumer updates are
accepted.

**Accepted narrow ignored-path exceptions (prospective):** Python/Node build caches and
virtual environments, OS/editor state, explicitly selected pytest
temporary directories, GitHub-managed step output, machine-local
environment/secrets, producer-owned *external* staging and the
production `metrics_history` Docker volume. These are owner-based
exceptions with distinct retention requirements, not permission to
accumulate ignored `reports/`, `data/` or `image_overrides/`
indefinitely. Tracked generated rules checklists, curated catalog scope
and reviewed evidence remain **tracked publication/review artifacts**,
not local scratch.

**Not yet eligible for approval or execution:** Source/snapshot, Wiki,
PDF, override, ignored raw/diagnostic and inaccessible root-report
relocations; retirements dependent on unverified backups; automatic
Syncthing cutover; blanket deletion of any private evidence; and
unreviewed module moves. These require completed L0 consumer/owner
classification, successful independent backup and trial restore,
authorized inspection of the 19 inaccessible report directories,
current sender/receiver state and per-batch hash/rollback evidence.
Prospective *non-destructive* naming defaults (P) are accepted;
tracked-code/document replacements (T) and each private-data
migration/deletion (M) still require specific future approvals.
Until then the existing documented paths keep working.

### L1 approval prerequisites — consolidated outstanding decision register

This is a **review checklist**, not permission to perform L2/L3. The private
per-file hashes, host-specific paths and detailed ACL/receiver observations
remain under ignored `local/research/project-infrastructure/tooling-workspace-cleanup/`.
Keep approvals separate for tracked module changes, ignored bytes,
service-owned volumes and destructive retirement.

1. **Recovery protection — blocked:** Establish an independent backup and
   *successful trial restore* for every source family before deleting old
   ignored source paths. The 24 Windows/receiver archive+manifest pairs
   proved identical at capture, but Syncthing replicas are not backups;
   receiver versioning was disabled at the inspected checkpoint.
2. **Unreadable root reports — blocked:** The 19 access-denied Windows
   `reports/` directories have unknown contents. Require authorized
   enumeration and lifecycle classification; do not elevate access, alter
   ACLs, move or delete them silently. Standard toolchain cache exceptions
   must be reviewed separately from these operator reports.
3. **Cross-host synchronization — partial:** Linux worker fetch and pinned
   optional-override *dry-run* activation were subsequently validated.
   Windows live send-only GUI status was unavailable at capture; recheck
   both ends and prove the selected source family has reached a stable
   state before any physical migration or receiver reconfiguration.
4. **Producer/path contract — partial:** The refined **44-file**
   source/provenance candidate manifest excludes two Syncthing markers
   and three OS metadata files. Freeze selected archive/manifests, retain
   source SHA-256s, handle the Linux hyphenated override receiver with
   explicit mapping, and prove destination/source selection independent
   of new file mtimes. Do not rewrite historical immutable manifest paths
   or prefer one of two ambiguous matching sources.
5. **Tracked versus ignored data — decision required:** Preserve all
   three tracked runtime databases, published manifests and static
   artifacts. Classify ignored `data/generated/` extras (especially
   the mismatched `army.raw.db`) as recoverable evidence until their own
   backup, consumer and deletion decisions. Keep persistent
   `metrics_history` Docker volume outside checkout relocation.
6. **Tool/document lifecycle — still partly open:** The initial
   private intake listed 124 tool artifacts and 48 tracked Markdown
   documents on an earlier revision; the current checkout enumerates
   **120 Python modules and one template directory** and has reconciled
   all module names against bounded ownership/disposition reviews.
   That is **not** proof of complete standalone/external consumer coverage:
   finish low-usage helper disposition, producer/MCP import and
   invocation checks, lifetime/retention triggers and actual source
   rollback evidence before L4/L5 retirement decisions.
7. **Policy accepted; retirement approvals pending:** Prospective
   `local/` categories, scoped cache/host exceptions, intentionally
   tracked generated-review outputs (including the interaction checklist
   and curated catalog-scope files), and filename/run-ID rules were
   accepted on 2026-11-13 for **new work only**. Separately authorize safe
   tracked-code/document retirements and each irreversible ignored-source
   deletion. After L2 writers/readers and source selections are accepted,
   apply L3 only in individually hash-checked, reversible batches.

**Gate:** Prospective P is accepted. L0 exit and an approved, specific
L1 mapping/exception registry are still required before bulk path movement. A green hosted CI run proves build and
publication compatibility, **not** backup recoverability or private-data
retirement eligibility.

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
