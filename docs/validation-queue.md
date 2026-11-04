# Phased validation queue

**Project domain:** Project infrastructure

This file is the single active register for validation work deferred under the
[phased development workflow](testing.md#phased-development-and-validation).
It tracks **test design and execution obligations**, not implementation features,
release scope, or source ambiguities. `docs/TODO.md` owns implementation work
and defects; `docs/releasing.md` owns mandatory release acceptance. Keep stable
IDs here and link the owning task instead of duplicating its description.

## Queue rules

- Separate **implementation**, **test design (VD)** and **test execution
  (VR)**. Implementation normally records concrete missing tests as VD
  instead of writing and executing a regression suite immediately. VD
  work creates or edits tests and links their execution to VR; **no tests
  run during a VD pass**, including new-test sanity runs. VR is the only
  deferred test-execution phase. Exceptionally urgent correctness,
  security, migration or artifact-safety checks remain immediate and
  must be named explicitly. See
  [testing.md](testing.md#phased-development-and-validation).
- Before ending an implementation pass, record **all concrete missing test
  designs** as VD, including new focused regression tests unless an immediate
  safety exception requires them, and each change's **deferred execution** as
  VR. A VR may await one or more VD items; existing tests requiring reruns
  need only VR. Record exact immediate exception selectors/results separately.
  Never call an unrun check passed or defer a required safety, migration or
  publication gate.
- Design items are `VD-0001`, `VD-0002`, etc. Each ID is one independently
  actionable test requirement, not one test function or a speculative idea.
  Count open `needs-design` IDs toward the **5-requirement design threshold**.
- Execution items are `VR-0001`, `VR-0002`, etc. Each item represents one
  distinct implementation change awaiting deferred verification, including
  changes whose required test design is unfinished. Count distinct open
  implementation changes, not files, tests, commits, or repeated runs, toward
  the **5-change execution threshold**. Combine multiple checks for the same
  change under one VR item. Link any blocking VD IDs.
- **Strict drain loop (check at every work boundary):**
  1. If **VD >= 5**, process VD entries **one at a time until no open VD
     remains**. Write or revise the required tests and create/update their
     linked VR entries, but **do not execute any tests**. When VD is empty,
     proceed to the VR check.
  2. If **VR >= 5**, process VR entries **one at a time until no open VR
     remains**, verifying the exact tests, state and acceptance evidence for
     each. Shared full-suite results may satisfy several entries, but review
     and retire each independently. **Dispatch is not completion**.
  3. Recount both queues. If either has reached 5, return to step 1.
     Otherwise ordinary implementation can resume.
  The threshold is a trigger for draining to **zero**, not permission to
  resume as soon as the count falls below 5. Never start another ordinary
  implementation pass while a due queue is idle or running focused VR work.
  **Exception:** while an actual full test suite is running asynchronously on
  a pinned, independent `linux-dev` checkout, unrelated Windows development
  may continue. Its new VD/VR obligations still enter the queue, and the
  outstanding VR entries remain open; resume the drain when the full run
  completes. This exception does not apply to focused or partial Linux jobs,
  nor to merely scheduling a future run. Failed and blocked entries remain
  open and must be triaged individually; if no safe action can clear them,
  report the blockers and leave the queue explicitly undrained rather than
  claiming success or looping indefinitely.
  A critical gate or an overdue item takes priority.
- **Maximum age:** process any open deferrable item within 7 calendar days of
  its recorded date, even below threshold. Also process it before the relevant
  release, merge, deployment, or other mandatory acceptance gate. Reassess the
  counts and oldest dates at the beginning and end of every agent pass.
- Never queue work that is required immediately for correctness or risk control.
  [Immediate checks and exceptions](testing.md#phased-development-and-validation)
  still apply, and required hosted CI remains unchanged.
- When design discovers a product defect, add/link the implementation fix in
  `docs/TODO.md` and mark the affected entry `blocked`; do not fix unrelated
  behavior during a dedicated design/execution pass. Failed executions stay
  open until the relevant checks pass on a corrected state.
- Include sufficient version/commit or artifact identity for results to be
  reproducible. A green result from an older state cannot verify a later edit.
  Store bulky reports under ignored `local/`; retain concise durable acceptance
  evidence in its canonical document when required.
- **Linux is the preferred deferred-execution worker**, not an automatic
  mirror of Windows. When execution is due, the agent prepares the
  *committed* target revision using separately invoked safe Git
  fetch/fast-forward operations on `linux-dev`, as already authorized
  for the validation handoff. Never force, reset, rebase or disturb a
  divergent/dirty checkout; report an unsafe or unavailable revision
  as a blocker. Batch compatible selectors into one pinned asynchronous
  `linux-dev` job with `expected_commit`. **Only while the entire
  full-suite run is actually executing on Linux** may independent Windows
  development continue; a focused/partial job does not suspend VR
  draining. Check the full-suite result at meaningful boundaries,
  resume processing open VR entries after it finishes, and respond
  to actionable failures. A Linux run cannot verify later Windows
  edits. Git synchronization remains explicit, bounded and
  validation-triggered, never a background mirror.
  Follow the [dispatch/retirement protocol](testing.md#parallel-windows-development-and-linux-validation).
  A successful job applies only to its verified revision and coverage.
  At each pass boundary, report queue counts, due/blocked items and what
  was actually dispatched; do not equate green immediate tests with an
  empty deferred-execution queue.
- **Retire completed entries immediately after processing:** remove each VD
  item once the test code/selector has been inspected for design completeness,
  and carry the selector to an open VR item **without executing it**. Remove
  each VR only after its required execution and evidence have passed for the
  exact intended state. Keep failed, blocked or unrun work open; separately
  owned hosted CI and release gates are not implicitly accepted.
- This is an **active queue, not a completion log**. Git history retains
  retired detail; do not copy finished items into another running diary.
  Advance the next-unused-ID counters on creation and never reuse an ID.

## Pending test design

Only open VD requirements belong here. **No pending entries.**

A VD entry records its ID/date/status (`needs-design` or `blocked`),
owning TODO work and revision, concrete missing assertion/edge case,
existing coverage, risk, linked VR ID, and resulting test selector and
static design-review outcome. Do not record a test result in VD. Retire
the entry when its design review is complete; retain the unrun test
selector and other dependencies in its VR item.

## Pending deferred execution

Only open VR obligations belong here. **Current count: 12 distinct
changes** (VR-0052 through VR-0063; five-change execution threshold reached).
No VD item is pending. The oldest open entries are dated 2026-11-03,
due 2026-11-10; no age threshold is overdue.

The pinned Linux cumulative batch at
`a9f564650ff0f42d28fca29f5a1daf87f8642edb`, job
`linux-dev:c4d857d310ab47949ccd94feb06f7f56`, passed **5,074 tests,
29 skipped, zero failures** in 431.85 s pytest / 432.51 s runner,
with all 808 SVGs and its rebuilt/checked ignored matched publication.
This completes the Linux obligations through VR-0061 on that revision;
the earlier four movement-only count failures are corrected. See
[the pinned evidence](testing.md#parallel-windows-development-and-linux-validation).

Hosted acceptance remains open. At documentation successor `6a4b05aa`,
Source checks passed both Linux jobs and Windows, and both smoke workflows
passed. GitHub could not acquire a macOS hosted runner: the cancelled job
had **no runner and no steps**, with an explicit macOS arm64 capacity
annotation. The dependent cross-platform byte-comparison job was skipped.
The latest affected macOS job was retried once under the transient-runner
policy: Source run
[`41858032642`](https://github.com/frankysan/InfinityDB/actions/runs/41858032642),
attempt 2, replacement job
[`126684025015`](https://github.com/frankysan/InfinityDB/actions/runs/41858032642/job/126684025015).
It was queued when recorded. No audit assertion or workflow gate was weakened,
and no entry is retired before the missing hosted acceptance is verified.

VR-0062 owns the later Cover/vertical-movement change and requires a new
pinned `linux-dev` full-assets batch and exact-candidate hosted checks.
The preceding Linux result does not validate those later edits. The known
cross-host SQLite byte boundary remains separate from strict logical replay;
the [hosted byte gate](v1.0-source-coverage-audit.md#cross-host-rules-rebuild-comparison-v1s-032-validation-2026-11-04)
is still mandatory.

- [ ] **VR-0052** (2026-11-03; ready-to-run): Validate the
  Windows CP1252-safe JSON stdout change in
  `tools/audit_army_faction_semantics.py` from V1S-013.
  Work: [source inventory and gap batches](TODO.md#source-inventory-and-gap-batches);
  risk: low (audit CLI only; source data and runtime unchanged).
  Immediate Windows: `tests/test_audit_army_faction_semantics.py`
  **4/4**, direct actual-database CLI exit 0 (previously
  `UnicodeEncodeError`), Ruff on tool/test and full Pyright pass.
  Design: none; limited-encoding regression already added.
  Deferred: pinned committed-revision Linux focused module and
  cumulative full suite when the validation threshold is due,
  plus exact-SHA hosted CI. Retire only after checking those
  outcomes; final frozen-release acceptance remains separate.

- [ ] **VR-0053** (2026-11-03; ready-to-run): Validate
  the paired raw/application Army source-audit adapter and
  explicit current-only historical-review boundary from V1S-014.
  Work: [source inventory and gap batches](TODO.md#source-inventory-and-gap-batches);
  risk: low/medium (read-only audit tooling, no runtime changes).
  Immediate Windows: new `tests/test_paired_audit_connection.py`
  **3/3**, existing relationship **7/7**, Peripheral **6/6**,
  normalization **3/3**, published Unit relationship Chromium
  **1/1**, Controller API **1/1**. Actual source audits all
  pass in their applicable modes, and the five historical
  endpoint IDs remain unresolved under `--current-only`.
  Design: none; paired/mismatch/legacy tests added, with the
  original snapshot-bound guard kept.
  Deferred: pinned committed-revision Linux focused tests,
  cumulative full suite when the threshold is due, and
  exact-SHA hosted CI. A future separately approved
  re-review may rebind historical endpoint evidence; do
  not count this current-only mode as such approval.

- [ ] **VR-0054** (2026-11-04; ready-to-run): Validate the
  V1S-032A source-backed Command Token general reference and matched
  schema-v9 `rules.db` / deployed-object publication.
  Work: [Rules and contextual reference completion](TODO.md#rules-and-contextual-reference-completion);
  artifact: `data/generated/rules.db` SHA-256
  `e3d367cf881833d9a4820c1d659467e51556a249146c63d7d933769e3240e6aa`;
  risk: medium (new public canonical Rule plus tracked matched release pair).
  Immediate: deterministic double export, all 483 prior rule identities unchanged,
  source/API 3/3, Chromium 3/3 at three widths, baseline 49/49,
  rules database 166/166, curated rules 670/670, interactions 15/15,
  deployed-object publication 12/12 and maintained links 38/38;
  strict interaction audit, rules build, Ruff, Pyright and docs pass.
  Design: none; the source, publication, mismatch/rollback guard
  and normal-browser checks are implemented.
  Deferred: pinned Linux focused/full suite and exact-candidate hosted CI,
  including Source checks cross-platform deterministic rules/database
  output comparison. The final release-wide browser/source gate remains
  separately mandatory.

- [ ] **VR-0055** (2026-11-04; ready-to-run): Validate
  V1S-032C1's two source-backed Game Sequence/Order Pool
  references, bilingual SRC-031 disclosure and matched
  schema-v9 publication. Work:
  [Rules and contextual reference completion](TODO.md#rules-and-contextual-reference-completion);
  artifact: tracked `rules.db` SHA-256
  `871a76f8fb69c4d4f9ba9120494635713cdc4970a79b448c191d83cff08a42ea`.
  Risk: medium (two new public Rule identities and matched release pair).
  Immediate: exact English/Spanish source hashes and clauses,
  deterministic double export; all 484 prior composed rules unchanged;
  phase/source 3/3, source/API/publication 4/4, Chromium 3/3 at
  1440/390/320, baseline 49/49, rules DB 166/166, curated
  670/670, interactions 15/15, deployed-object publication 12/12,
  maintained-text 38/38 (**960 focused tests**);
  guarded matched-pair check, full Ruff, Pyright, data/rules build
  and docs checks passed.
  Design: none; source, scope, route and paired-publication
  assertions are implemented; no runtime evaluator.
  Deferred: pinned Linux source/model/browser tests, cumulative
  full suite at the five-change threshold and exact-SHA hosted CI;
  final release-wide source/browser acceptance remains separate.
  Linux source review at `cd33920d` had **3/4** due to a
  cross-version SQLite *physical* rebuild hash; its other clauses
  passed. The complete schema/rows were identical (SQLite
  3.50.4 Windows vs 3.46.1 Linux). A strict logical rebuild
  check is staged for a newer committed validation revision;
  the byte-specific hosted Source checks remain required.

- [ ] **VR-0056** (2026-11-04; ready-to-run): Validate
  V1S-032C2's N5.3 pp. 13–14 Automatic Reaction Order reference
  and p. 16 Deployment Phase conditions without affecting
  existing ARO Trait, Order Expenditure or declaration legality.
  Work: [Rules and contextual reference completion](TODO.md#rules-and-contextual-reference-completion);
  tracked rules SHA-256
  `1334b79375af5d4cf10ecb108225dc9df9bcd06f74454152b31d2ad3a4aba790`.
  Risk: medium (new General Rule and updated existing Deployment Rule;
  tracked database and ignored deployed-object publication).
  Immediate Windows: source/api/pair **5/5**, Chrome **3/3**
  at 1440/390/320, frozen baseline **49/49**,
  rules database **166/166**, curated **670/670**,
  interactions **15/15**, deployed-object **12/12**,
  maintained-text **38/38**, C1 source/API **4/4**,
  C1 Chrome **3/3**, pinned phase-source **3/3**:
  **968 focused tests**. Deterministic matched pair,
  all 485 unrelated composed records unchanged;
  full Ruff/Pyright, data/rules build and docs pass.
  The C1 deterministic regression now compares with the
  *current* published SHA rather than freezing C1's historical
  whole-database count/hash, preserving future additive releases.
  Design: none; source PDF clauses and normal-browser
  assertions already added.
  Deferred: Linux exact-commit focused and full tests at this
  five-change threshold, independent source/asset verification,
  exact-SHA hosted CI and final 1.0 source/browser acceptance.
  Linux source review at `cd33920d` was **4/5** because
  the SQLite 3.46.1 rebuild differs physically from tracked
  Windows SQLite 3.50.4 bytes, although the entire table
  schema and logical rows match. The updated guarded
  read-only check requires strict logical equality; rerun on
  the next pinned revision. This is not a cross-host byte
  determinism approval; see the [recorded boundary](v1.0-source-coverage-audit.md#cross-host-rules-rebuild-comparison-v1s-032-validation-2026-11-04).

- [ ] **VR-0057** (2026-11-04; ready-to-run): Verify the grouped
  Chromium scheduler registration for the newly published Game Sequence
  and ARO/Deployment real-browser modules (V1S-032C1/C2).
  Work: [Rules and contextual reference completion](TODO.md#rules-and-contextual-reference-completion);
  risk: medium (Linux opt-in four-lane suite fails before collection;
  ordinary browser/product data are unchanged).
  Reproduction: Linux full-assets run on `4af5ac14`, job
  `linux-dev:0bb08ca52bf84dcfbd680dcb2369b77c`, exited 1 at
  `tests/conftest.py:203` with missing
  `test_verify_aro_deployment_browser` group; pre-fix Windows
  `test_two_browser_lanes_cover_all_real_chromium_modules` failed
  and independently identified `test_verify_turn_sequence_browser`.
  Immediate Windows: registering both modules in all 2/3/4 lane maps
  and testing each map against the independent browser-section registry
  passed `tests/test_browser_test_capacity.py` **25/25**;
  Ruff on tool/test passed.
  Design: none; the existing registry parity test was strengthened.
  Deferred: a pinned Linux cumulative four-lane full-assets suite with
  collection and browser-lane assertions, plus exact-SHA hosted CI.
  The five preceding VR items remain open until their own checks pass.

- [ ] **VR-0058** (2026-11-04; hosted acceptance pending):
  Reconcile V1S-032 additive General Rules and Deployment source revision
  with tests/negative-review evidence, without weakening publication
  equivalence or treating Deployment Tokens as deployed devices.
  Work: [Rules and contextual reference completion](TODO.md#rules-and-contextual-reference-completion);
  risk: medium (source-review manifest and General Rule catalog
  invariant tests; no runtime source/binary changes).
  Reproduction: pinned Linux full-assets job
  `linux-dev:0a90f21cf1944c5a8d4a3d486e505213` at
  `ad1416a0`: **5,042 passed, 28 skipped, 15 failed**;
  three tests froze the General Rules count at 30 despite 34 current
  source-backed rules, and twelve other failures cascaded from stale
  `rule:deployment-phase` summary evidence in the non-catalog
  review manifest after the reviewed p. 16 placement additions.
  Correction: match published General Rule slugs against the *entire
  current curated source*, retaining the original 30-rule baseline and
  explicitly checking all four V1S-032 additions. The browser verifier
  now accepts additive General Rules without relaxing the fixed
  Ammunition/Label/State/Trait inventories or source/slug equality.
  Re-pin the exact Deployment excerpt and pp. 15–16 provenance;
  source-backed reviews classify new game-sequence, order-pool and
  Command Token resources as **non-objects** (54/54 reviewed), and
  new Automatic Reaction Order Marker mentions as **non-objects**
  in the separate expanded scan (26/26 reviewed).
  The legacy citation staging inserter now bounds a record by the next
  sibling object rather than assuming the next record begins with
  `id`; the three schema-v9 staging cases pass.
  Immediate Windows evidence: General Rules parity 17/17,
  non-catalog 4/4, expanded lexical 4/4, legacy staging 3/3,
  citation migration 7 passed/1 skipped and the affected WSGI
  General Rules API 1/1; Ruff passed.
  Linux full-assets rerun passed at `df7191fc` (5,056/29 skipped/zero failed).
  Deferred: hosted exact-SHA CI; final release acceptance remains separate.

- [ ] **VR-0059** (2026-11-04; ready-to-run):
  Restore historical Git evidence for hosted Source checks. All four
  platform jobs in the prior `d22096be` run failed three
  `tests/test_report_reference_baseline.py` cases because the
  default shallow `actions/checkout` could not resolve frozen
  curated source commit `c5400ab1`; this is not a source-content
  mismatch. The Source checks matrix now uses `fetch-depth: 0`
  without altering the unrelated packaging/deployment checkouts.
  Work: [source inventory and gap batches](TODO.md#source-inventory-and-gap-batches);
  risk: low (CI source checkout and one regression guard; no product
  data, published assets or Python runtime changed).
  Immediate Windows: the workflow regression
  `test_source_ci_builds_ignored_release_publication_before_tests`
  **1/1** and Ruff pass; docs/link validation passed.
  Deferred: verify that an exact-commit hosted Source checks run
  retrieves and uses the frozen revision on all platforms, including
  the cross-platform deterministic-output job. Do not retire based
  solely on local full-history success.

  Follow-through: hosted run `41846453882` at full SHA
  `60c4ddbc3172d52d16e8471083a2216b54b2a921` passed three matrix
  jobs but failed Ubuntu 3.11's clean-index preflight on the same three
  frozen-evidence tests: that export intentionally has no Git repository.
  The default audit now reads the exact hash-pinned extraction of the
  original 17 retired declaration records, preserving historical commit,
  full-file digest and exact original contents. No transition approval or
  frozen inventory is changed. Direct no-Git/drift, extraction replay and
  reviewed-join tests pass. The actual Git-free index export passed the
  full baseline module **42 passed / 9 expected source/history skips**,
  with its ignored publication built and verified. Replacement hosted checks
  remain required. The latest Installed wheel and Deployment smoke runs
  passed, but their success does not accept the failed Source workflow.

- [ ] **VR-0060** (2026-11-04; ready-to-run): Validate the V1S-033A
  Moving and Measuring / General Movement Rules references and expanded
  `skill:move` conditions, based on `60c4ddbc` and pinned N5.3 pp. 27-30.
  Work: [Rules and contextual reference completion](TODO.md#rules-and-contextual-reference-completion);
  risk: medium (new public Rules, revised Skill, synchronized v9 artifacts).
  Rules SHA-256: `b71ddbaed6bba191e1c7b6b87bd385e8965f22283f72eb24731895920c15bd85`.
  Immediate Windows: source/conditional boundaries **2/2**, API/search and
  deterministic matched-pair replay **2/2**, normal Chrome **3/3** at
  1440/390/320 px, repeat/mismatch write-refusal **1/1**, and registry
  parity **4/4** across the supported lane maps. The guarded promotion
  preserved 486 unrelated records and all deployed-object contents;
  only the rules/curated fingerprints changed in the ignored publication.
  New lexical mentions are reviewed as existing game-element movement,
  not new object identities. Updated inventory assertions preserve the
  frozen 367-record baseline and its original D/S tiers.
  Design: none; direct source, API/search, browser and pair checks exist.
  Deferred: pinned `linux-dev` focused/cumulative full-assets tests,
  exact-SHA hosted Source checks including deterministic outputs,
  Installed wheel and Deployment smoke. The parent V1S-033B-E and
  final source/browser release acceptance remain separately open.

  Follow-through: Linux full-assets job
  `linux-dev:1b7f55f0fea34e9c992c1f6844271c4a` and hosted Source run
  `41850874089`, both at `cae85151037aae8c09fc6577d415033fc5d4bf64`,
  exposed four stale `tests/test_audit_rules_interactions.py` totals
  (395/213/209 before the two new Rules; current movement-only counts
  were 397/215/211). Assertions now compare the entire report identity
  sets with maintained review/catalog identities, retaining fixed
  historical release counts, complete/pending checks and 1.0 source scope.
  All four failing selectors passed immediately, and the full interaction
  module subsequently passed within the **960/960** integrity regression
  batch. No audit gate, reviewed identity, scope exception or source
  status was weakened. The actual Git-free index export passed both
  interaction and baseline modules: **57 passed / 9 expected source/history
  skips**, with the matching ignored publication built and checked.
  Linux cumulative and hosted reruns remain required.

- [ ] **VR-0061** (2026-11-04; ready-to-run): Validate V1S-033B's six
  shared geometry Rules, expanded `attribute:s` help and movement-to-LoF
  links, based on `fcfa1453` and pinned English N5.3 pp. 18-22.
  Work: [Rules and contextual reference completion](TODO.md#rules-and-contextual-reference-completion);
  risk: medium (public conditional rules prose and synchronized v9 pair).
  Rules SHA-256: `4414819fbc9246cc283ccc36c1261b4a9ce5d5a4cb4d999e624680c7a97b95f5`.
  Immediate Windows: source/boundary **3/3**, storage/API/search and matched
  pair/refusal **2/2**, real Chrome **3/3** at 1440/390/320 px with keyboard
  links, source citations, S1-S8 diagrams, request/page-error and overflow
  assertions; integrity modules **960/960**. Ruff, Pyright, Army/rules build
  and strict interaction checks pass. The deterministic promotion preserved
  487 unrelated records, Restrictions and all deployed-object contents.
  The existing Weapon range Trait, Fireteam-specific effects and diagrams
  retain their owners. No unconditional State relation or geometry engine
  was introduced; three new lexical mentions are explicitly reviewed as
  existing game-element geometry/replacement rather than new object profiles.
  Design: none; essential source, publication, negative guard and browser
  assertions exist. Deferred: pinned `linux-dev` focused/cumulative full-assets
  suite and exact-SHA hosted Source checks, including deterministic outputs,
  Installed wheel and Deployment smoke. V1S-033C-E and final release-wide
  source/browser acceptance remain separate.

- [ ] **VR-0062** (2026-11-04; ready-to-run): Validate V1S-033C's
  shared Cover reference and Climb/Jump procedures, with linked Climbing
  Plus conditions, based on `6a4b05aa` and N5.3 pp. 32-34/41-42/88.
  Work: [Rules and contextual reference completion](TODO.md#rules-and-contextual-reference-completion);
  risk: medium (conditional public prose and synchronized schema-v9 pair).
  Rules SHA-256: `a6cbdd5e94d35f00263b72a7a1325ac3cfe7b71ff2a494abbdbd152a2a8a674d`.
  Immediate Windows: pinned source, preserved Skill metadata and boundary
  checks **3/3**, storage/API/search/FAQ and pair/refusal **2/2**, Chrome
  **3/3** at 1440/390/320 px. Integrity modules passed **959** tests; the
  remaining legacy LoF-text assertion was updated to require the new typed
  link and passed directly **1/1**, retaining Super-Jump's existing check.
  Ruff, Pyright, Army/rules builds and strict interaction checks pass.
  Maintained-text audit has zero unlinked candidates and zero residuals;
  four obsolete ordinary-word fingerprints were removed, without adding
  or broadening an exception. The existing Silent (X) review marker remains.
  Publication preserved 492 unrelated records, Restrictions, all object
  contents and the separate dated vaulting FAQ. Native declaration types,
  Army source mappings, distance parameters and State relations are unchanged.
  Design: none; essential source, metadata, browser, FAQ and negative-guard
  coverage exists. Deferred: pinned `linux-dev` focused/cumulative full-assets
  tests and exact-SHA hosted Source checks, including macOS and deterministic
  outputs, Installed wheel and Deployment smoke. Final V1S-033D-E and
  source-wide release acceptance remain separate.

- [ ] **VR-0063** (2026-11-04; ready-to-run): Validate V1S-033D's
  optional Difficult Terrain and Saturation reference pair from N5.3
  pp. 143–145, with historic terminology alias and conditional modifiers.
  Work: [Rules and contextual reference completion](TODO.md#rules-and-contextual-reference-completion);
  risk: medium (two public General Rule identities and synchronized v9 pair).
  Rules SHA-256:
  `bff440233627e2f0fce8a69cec40a34f2ed45d8285db3989f7adcae29e1c000c`.
  Immediate Windows: source/scope/conditions, API/search and paired publication
  **4/4**, Chrome **3/3** at 1440/390/320 px (keyboard, citations,
  navigation, request/page errors and overflow). The deterministic
  promoter preserved 496 previous Rule records, Restrictions and all
  deployed-object contents; the historical `Difficult Movement` alias
  introduces no second mechanic. Existing Skill variants, Visibility
  Zones, Access Width and illustrative combinations remain unchanged.
  Promoter and affected tests pass Ruff; full Ruff, Pyright, docs, data,
  strict rules-interaction audit and rules build pass. Curated **670/670**,
  interaction review **15/15**, reference baseline **51/51**,
  deployed-object publication **12/12**, and rules database
  **165/166** with the one stale total corrected by a direct **1/1**
  rerun. Design: none; source, negative-scope, publication/refusal and
  normal-browser checks exist.
  Deferred: exact-pinned `linux-dev` cumulative full-assets suite and
  hosted Source checks, including macOS and cross-platform deterministic
  outputs, Installed Wheel and Deployment smoke. V1S-033E and final
  release-wide acceptance remain separate.

The pinned `e31094c6` full-assets Linux attempt
`linux-dev:738388c1295e4f0fa82d7881fe36c5ec` ran
**5,081 passed / 29 skipped / 1 failed** in 431.86 s pytest.
The only failure was a stale literal Jump tooltip-preview expectation in
`tests/test_web.py::test_maintained_text_tokens_resolve_links_distances_and_tooltips`
following V1S-033C's reviewed Jump summary expansion. Its assertion
now checks link identity and the live matching Jump summary rather than
the superseded sentence, and passed **1/1** directly on Windows.
This failed Linux run is not retrospective acceptance; rerun on the
new committed revision before retiring VR-0062/63 or other open obligations.

Infiltration fixed-PH source-47 review **VR-0051** retired at pinned
`dd071c4df04d6c90cddc1a84a6974952506a097d` after Linux
source-variant **100/100**, full-assets **5,014 passed / 29 expected
skips / zero failures**, and all three GitHub workflows passed. The
source-boundary and paired-publication details are in
[testing.md](testing.md#parallel-windows-development-and-linux-validation).
Final frozen-candidate release gates remain separate.

Combat Jump source-35 occurrence semantics **VR-0050** retired at
pinned `c1d8adc6cd547063ee5b8a85e831aa73cd4d4195`. The exact
N5.3 p. 89 Army variants cover **121 qualified/90 unqualified**
direct occurrences across six signatures, retaining landing-only
PH modifications and the separate one-use Explosion attack. The
guarded schema-v9 release refresh preserved unrelated records and
the paired deployed-object projection. Windows source-variant
**97/97**, curated **670/670**, rules DB **166/166**, data/build,
rules, Ruff and Pyright passed. The explicitly rebuilt ignored Linux
publication passed its matched-pair `--check`; Linux source-variant
**97/97** passed, and its full suite passed **5,011 / 29 expected
skips / zero failed** in **417.86 s pytest / 418.50 s runner** (job
`linux-dev:858b769b73294503b857031c802abf74`), with
**808/808** published SVGs, correct four-lane worker assignment,
**56.00 summed worker-seconds** of Chromium admission waiting and
two known Python 3.14 `fork()` warnings. GitHub Source Checks
(all four matrix jobs plus cross-platform deterministic outputs),
Installed Wheel Smoke and Deployment Smoke all passed. The
cross-Army variant usage index remains separate and unimplemented.

At pinned Linux commit `06ae1c4856d3213a3f03c88f7f6f219b23366ee7`,
the full suite passed **4,946 tests / 28 expected skips / 0 failures**
with 808/808 SVG assets. This retires VR-0040 (Army/Section and
Commlink browser context), VR-0041 (all published Reinforcement profile/
loadout source parity) and VR-0042 (all source-backed Commlink extras).
The preceding `5d6a30d8` run passed the same suite; a subsequent
fixed-tuple Pyright correction was retested on the final revision.
See [testing.md](testing.md#parallel-windows-development-and-linux-validation)
for the pinned jobs, warnings and residual scope. The independent
Chromium skip-reason and controlled capacity comparisons were tracked
under VR-0023/24, both now retired below. Git updates are explicit,
not background mirroring.

The later pinned Linux suite at `ad3314dc3da02ec3a9087b5361dcbdc1b374cabf`
passed **4,952 tests / 29 expected skips / 0 failures** with 808/808
published SVG assets. It retires VR-0043 (legacy staging freshness guard);
full evidence and the two existing `fork()` warnings are recorded in
[testing.md](testing.md#parallel-windows-development-and-linux-validation).
The independent Chromium diagnostics were tracked as VR-0023/24;
both were subsequently retired below.

The 2026-11-03 Lieutenant publication and development tooling batches
retired **VR-0044/45/46** at pinned `60bd855932f663bf6bec0de5dc29f3439006e6ed`.
The initial Lieutenant suite at `14590055` exposed two test defects,
both corrected by `bda102e6`: cross-platform SQLite byte-layout
comparison and an incomplete reviewed-extra identity assertion.
The corrected `bda102e6` Linux suite passed **4,959 / 29 skipped /
0 failed**; its two original failing selectors passed separately on
Linux. On the final revision the raw-inspector module passed **11/11**
and the directory/ZIP database-size fixtures passed **2/2** on Linux.
The final full Linux job `linux-dev:0f5828bdc96a4172bb46c5fcce1e991e`
passed **4,970 / 29 skipped / 0 failed** in **594.79 s**, with **808/808**
published SVGs; all three GitHub workflows passed. The two existing
Python 3.14 fork warnings and independent controlled Chromium
benchmarking are not resolved by these results. See
[testing.md](testing.md#parallel-windows-development-and-linux-validation).

Terrain source-58 review **VR-0047** retired at pinned
`333a091cb4336cb5cce0d9b0c2eae9b27c7abaa0`: source-variant
module **82/82** on Linux (`linux-dev:e4b0c232a25c499b8ff18941da38edad`),
and full Linux suite **4,977 passed / 29 skipped / 0 failed**
in **593.76 s** (`linux-dev:bbfa0a7fd0f64ab79e67e19041c371f3`),
with **808/808** published SVGs. Two existing Python 3.14
`fork()` warnings remain. All three GitHub workflows passed.
Chromium setup included **6,301.22 summed worker-seconds** of resource
waiting across 31 events; this is included in pytest wall time.
The unresolved `Religious Troop (Total)` source anomaly is unchanged.

Camouflage source-29 review **VR-0048** retired at pinned
`5ac294165a8be49a13125ba9324281b17b406264`: the matched
publication and Linux source-variant module passed **89/89**; the full
Linux suite passed **4,984 / 29 skipped / 0 failed** in **596.40 s**
(pytest; `linux-dev:ec597818137143ffa8cb26c741a8fd87`), with
**808/808** published SVGs. Existing Python 3.14 `fork()` warnings
persist. All GitHub workflows passed, including Source Checks after
rerunning its initially cancelled macOS job and final deterministic-
output comparison. No source-data or FAQ semantics changed during
the retry; the reviewed annotation remains metadata, not a match-state
tracker.

Linux host-only Chromium profile **VR-0049** retired at
`47122aa519b6d81c0b471797e9aa93ec77f4588a`.
On Linux the ignored `local/browser-test-profile.json` was enabled
explicitly and the maintained runner's generated command verified
**eight xdist workers, four slots, four lanes and Scenario FAQ A/D
split**. Focused profile tests passed **17/17**, operational section
**365/one skip**, and the pinned full suite
`linux-dev:33798d90fffe42caa22b2b2c697994c6` passed
**5,001/29 skipped/zero failures** in **422.07 s pytest / 422.72 s
runner**, with **808/808** SVGs, correct one-worker-per-lane assignments,
**54.42 summed worker-seconds** of Chromium admission waiting, and
two existing Python 3.14 fork warnings. Windows retained standard
`-n auto --dist worksteal` and the two-slot cap; its operational
section passed **361/five skips**. All three GitHub workflows passed,
including the cross-platform deterministic-output matrix. The
profile is host-local and reversible; the separate metrics gate
VR-0024 and VR-0023 are both retired below.

Chromium metrics and timeline instrumentation **VR-0024** retired
at pinned `6177a8dc0befd544971913db010168254bf431fb`.
The maintained operations section passed **361 / 5 skipped** on
Windows (`708666f4030c45549c0737c36c90c95b`) and
**365 / 1 skipped** on Linux
(`linux-dev:36888a30c0b545d5b0e1d21e552a68ec`).
Independent two-/four-slot parallel browser runs at `5ac29416`
passed **600/16 skipped/zero failed** on both platforms, with
one-worker-per-lane guards passing; namespace-partitioned slot
timelines found **no confirmed same-slot overlap**. Full-duration
native CPU/RAM sampling covered **100% of each four host/capacity
test windows**, and the analyzer's overlap-weighted summaries and
per-worker slot wait/hold data were verified. Linux's repeated
four-slot run at `48d0cd84` also passed **600/16 skipped**;
its host-specific four-slot full suite at `47122aa5` passed
**5,001/29 skipped/zero failed** in **422.07 s**. All hosted
checks at `47122aa5` passed. This closes the metrics
implementation/verification obligation, **not** the Windows four-slot
timeout or cross-host source/skip parity. VR-0023 now documents
the environment-specific differences, while deeper investigation is
explicitly deferred to after v1.0. Linux keeps its opt-in four-slot
profile; Windows and CI remain unchanged.

Chromium cross-host skip diagnostics **VR-0023** retired at pinned
`955c55a02bf4aa74023313506105b29a6620c862`. The maintained
runner's `--skip-details` opt-in lists each skipped pytest node ID
and reason alongside independently controlled grouped skip counts;
it changes neither selection, admission slots, nor exit status.
Focused Windows capacity tests **25/25**, runner tests **108/one
expected skip**, Ruff and Pyright passed. With `--skip-details`
and full assets, Windows model tests passed **3,055/6 skipped**
(job `30eed8ebb1624bf6bc16d81bdb40167e`), Linux model
**3,049/12 skipped** (job
`linux-dev:07d181f703904818b9de7a07a58a313c`).
Exactly **six additional Linux model skips** come from five absent
ignored FAQ/N5.2–N5.3 PDF checks and one local migration report;
the other six model skips are shared, pre-promotion/opt-in cases.
Windows operations passed **363/five skipped**
(`4e04d81e25d047d7baeb324cc0715d90`); all five skips
are Windows symlink-privilege checks. Linux operations passed
**367/one skipped**
(`linux-dev:beaf812a636044818dc85d7c6026dd1a`), the skip
being a Windows-only native API test. Separately,
`tests/test_web_metrics.py` passed Windows **2/two skipped**
(Linux Gunicorn/fork-only cases) and Linux **4/4**. All compared
sections have zero failures; unequal skip counts are explicitly
environment-labeled, not falsely described as equivalent coverage.
The prior pinned four-slot Linux full suite at `47122aa5`
passed **5,001/29 skipped/zero failed**, and VR-0024 separately
retired the slot/resource instrumentation. The deeper analysis
of Windows full-load Glossary/Spec-Ops timeouts, Scenario FAQ
long tails, browser pooling, and optional identical PDF/staging
coverage is **deferred to the Post-1.0 backlog** in
[TODO.md](TODO.md#performance-storage-and-build-tooling).
The chosen Linux four-slot and Windows two-slot limits remain
unchanged. No new 1.0 validation obligation is created by this
performance investigation.

A VR entry records its ID/date/status (`awaiting-design`,
`ready-to-run` or `blocked`), the implementation revision/artifact,
immediate focused checks and results, any required VD dependencies,
deferred test selectors/gates, and the final execution outcome.
Retire it once required checks pass on the intended state and the outcome
is recorded. Failed or incomplete verification remains open.

## Next unused IDs

- Design: `VD-0007` (through `VD-0006` retired).
- Execution: `VR-0064` (`VR-0052` through `VR-0063` open; `VR-0051` and earlier entries retired).

Increment the relevant next-unused ID when adding a task, even if that
task is later removed. Previous completed records remain in Git history.
The 2026-11-02 cumulative local suite evidence is summarized in
[testing.md](testing.md#controlled-chromium-concurrency-and-browser-reuse-benchmark);
mandatory CI and final release acceptance remain separate.

## Recording template

Copy only the applicable entry to the corresponding active section and
replace the sample ID with the next unused ID shown above. Do not create
entries for work fully verified during implementation.

```text
- [ ] VD-NNNN (YYYY-MM-DD; needs-design): <required assertion/edge case>.
  Work: <TODO anchor>; change: <revision/files>; risk: <level>.
  Existing coverage: <selector or none>; linked execution: VR-NNNN.
  Outcome: <authored test selectors and static design review; no tests run>.

- [ ] VR-NNNN (YYYY-MM-DD; awaiting-design): <one implementation change>.
  Work: <TODO anchor>; revision: <commit/artifact>; risk: <level>.
  Immediate: <essential regression selector/result and required validators>.
  Design: VD-NNNN or none.
  Deferred: <existing module/full-suite/integration/manual checks>.
  Outcome: <tested revision, command, counts and evidence, when run>.
```
