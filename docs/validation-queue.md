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
- **Hosted CI has its own owner:** `docs/ci.md` specifies CI execution,
  failures and matrix results; `docs/releasing.md` owns final acceptance.
  **Do not hold a locally verified VR item open solely for a hosted CI run**.
  Preserve its still-mandatory CI acceptance in those owners and the active
  source-coverage evidence; never describe VR retirement as hosted approval.
  A VR with no remaining local execution work but a pending hosted check
  should be migrated to its CI/release owner, not retained indefinitely
  as a completed local task. This separation does **not** waive hosted
  platform, wheel, deployment or deterministic-byte requirements.
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

- [ ] **VD-0020 (2026-11-04; needs-design):** Pin the basic attack/close-combat
  source-to-reference conditions added under
  [V1S-034](TODO.md#rules-and-contextual-reference-completion).
  Change: `n5-core-v5.3.json` SHA-256
  `8249fd75b6eb42f1aa1a76ab9d7667ef5fa57fc10c32d97414aeadf55a122dae`;
  risk: player-facing conditional rules prose. Design
  `tests/test_combat_attack_reference.py` for pinned PDF/Wiki evidence,
  whole-Burst selection/invalid-dice/range limits, -6 per engaged ally and
  failed-roll hits, Coup de Grâce with both exceptions, two-or-more eligibility,
  separate Active/Reactive contributor exclusions and engaged-allied contact.
  Verify curated-to-runtime/API parity while leaving base Weapon B unchanged.
  Add a real-Chromium Skill-page check at 1440/390/320 px with Developer Mode
  off, visible new text and semantic links, API assertions, page-error and
  failed-request capture, and no horizontal overflow. Reuse current browser
  fixtures; inspect selectors statically without executing tests in VD.
  Existing coverage: `tests/test_catalog_rules.py`,
  `tests/test_other_source_variant_provenance.py`; linked execution: VR-0077.

- [ ] **VD-0021 (2026-11-04; needs-design):** Pin shared Template and distinct
  Direct/Impact reference procedures under
  [V1S-034](TODO.md#rules-and-contextual-reference-completion).
  Change: curated SHA-256 `ad0b2b0da3eea1258ef6dceebd7821bdc201d026a94c6a644c20d68de1b2d5e8`;
  risk: conditional player-facing rules. Design
  `tests/test_template_reference.py` with pinned N5.3 pp. 43–49/FAQ p. 1 and
  exact archived Wiki members: Main Target miss, partial Burst cancellation,
  allied/neutral no-PS/no-condition conjunction, retained ARO/Disposable,
  whole-engagement effect, Partial Cover SR exclusion, scenery, main-only
  Criticals, separate target opposition and single-Dodge comparisons.
  Distinguish ordinary Direct no-roll fire, Intuitive WIP exception,
  Direct placement/self-exclusion and FAQ corners from Impact placement,
  Targetless and Speculative exceptions. Verify sourceIdentity preservation,
  new General Rule export/API/search and typed-link resolution.
  Add real Chromium normal-mode catalog/detail/link checks at 1440/390/320 px
  for General Rules and both Traits, with matching API content, page errors,
  failed requests and overflow assertions. Existing coverage:
  `tests/test_catalog_rules.py`, `tests/test_rules_database.py`,
  `tests/test_faq_ruling_references.py`; linked execution: VR-0078.

- [ ] **VD-0023 (2026-11-04; needs-design):** Pin V1S-035 Hacking provenance
  corrections and the White Noise/Zero Pain procedures.
  Work: [V1S-035](TODO.md#rules-and-contextual-reference-completion).
  Change: Core `7c5ce6ac3196d6c3427f6a73c2cdf65fae21237af3fa9f7dceb7709191f29bdc`,
  Hacking `b8a1cd9ed669d0549989f335ff52fbd26fe3dd661131ee078db801ac7d9592ea`;
  risk: source links and conditional rules text. Design
  `tests/test_hacking_source_followup.py` to pin Repeater p. 56, shared
  Supportware p. 55 (including three Program citations), all twelve exact
  primary Program sections on pp. 59–61, White Noise end-of-Order placement
  versus Controlled Jump declaration timing, and Zero Pain B2 in both turns,
  either-die cancellation and no Saving Rolls/special effects without creating
  new ARO eligibility. Preserve source/Army statistics, labels, grants and
  unresolved Charontid extras. Verify curated-to-runtime/API citations/facts
  and real Chromium normal-mode Program/Supportware/Repeater links at
  1440/390/320 px, with page errors, failed requests and overflow assertions.
  Existing coverage: `tests/test_hacking_program_publication.py`,
  `tests/test_rules_database.py`, `tests/test_audit_source_variant_inputs.py`;
  linked execution: VR-0080. No tests run during VD.

A VD entry records its ID/date/status (`needs-design` or `blocked`),
owning TODO work and revision, concrete missing assertion/edge case,
existing coverage, risk, linked VR ID, and resulting test selector and
static design-review outcome. Do not record a test result in VD. Retire
the entry when its design review is complete; retain the unrun test
selector and other dependencies in its VR item.

## Pending deferred execution

The most recent pinned Linux full-assets acceptance, including the 2026-11-04
queue drain, is recorded in
[testing.md](testing.md#parallel-windows-development-and-linux-validation).
The active queue does not duplicate completed evidence: Git history retains
the retired VD/VR entries. Hosted Source checks (including macOS and
cross-platform deterministic outputs), Installed wheel, Deployment smoke
and final release acceptance are still independently required under
[CI policy](ci.md) and [V1S-093](TODO.md#final-10-acceptance);
**an empty VR queue does not certify those gates**.

A VR entry records its ID/date/status (`awaiting-design`,
`ready-to-run` or `blocked`), the implementation revision/artifact,
immediate focused checks and results, any required VD dependencies,
deferred test selectors/gates, and the final execution outcome.
Retire it once required checks pass on the intended state and the outcome
is recorded. Failed or incomplete verification remains open.

- [ ] **VR-0077 (2026-11-04; awaiting-design):** Verify the V1S-034 basic
  BS/CC attack reference expansion. Base revision: `dd0b894b40691aa0a68dea47ee4d8abb76792bcd`;
  target: the committed implementation containing the VD-0020 curated hash and
  rules DB `8f2fa36b3ce3f0293fa217641d780db9d2c300da2f82438d1a6e9adcbc88b609`.
  Work: [V1S-034](TODO.md#rules-and-contextual-reference-completion);
  design: VD-0020. Immediate: maintained-text audit zero candidates/residuals;
  guarded paired publication and two-build determinism passed, 498 identities
  retained and 496 unrelated composed records unchanged. Publication integrity
  required this immediate gate; no routine tests were run in implementation.
  Deferred selectors: new `tests/test_combat_attack_reference.py` (including
  real Chromium), `tests/test_catalog_rules.py`,
  `tests/test_other_source_variant_provenance.py`, `tests/test_rules_database.py`,
  and cumulative full-suite `tools/run_checks.py --stage test --assets required`.
  Intended host: pinned `linux-dev` after safe fetch/fast-forward, full source
  inputs/browser dependencies, and rebuilding/verifying ignored deployed-object
  publication; Windows may supply complementary browser evidence. Preserve
  actual revision, source pins, terminal counts and skips. Hosted and final
  candidate acceptance remain independently owned.

- [ ] **VR-0078 (2026-11-04; awaiting-design):** Verify V1S-034 Template
  references. Base revision: `c451a22d8d7311d0fdc136751839f9e63eda91bb`;
  target: committed implementation with VD-0021 curated hash and rules DB
  `3fd3b9209d5702eb24c9b8bbf6404d70db0ecafafcdce5fd8020d465ebab464f`.
  Design: VD-0021. Immediate artifact-integrity exception: deterministic twin
  exports, 498 prior identities retained plus one General Rule, unchanged
  Restrictions and 496 unrelated composed records, matched publication and
  verified recovery pair. Maintained-text audit: zero candidates/residuals.
  No routine tests run. Deferred: `tests/test_template_reference.py`,
  `tests/test_catalog_rules.py`, `tests/test_rules_database.py`,
  `tests/test_faq_ruling_references.py`, and cumulative
  `tools/run_checks.py --stage test --assets required`.
  Intended host: pinned `linux-dev` with PDF/Wiki/FAQ, Chromium and full assets;
  rebuild/verify ignored deployed-object publication before execution. Record
  actual commit, source identity, results and skips; do not substitute this
  check for final candidate or hosted acceptance. A newer cumulative snapshot
  can also verify VR-0077 after confirming both attack records are unchanged.

- [ ] **VR-0080 (2026-11-04; awaiting-design):** Verify V1S-035 Hacking
  source/citation and scoped procedure updates. Base:
  `67e3f0447ca9a5990bd8d818105434ef70ea53f8`; target: committed VD-0023
  curation with rules DB `121480b02d2ec81223d167ea1b1c00a556ddd256a42c418b9622059667493349`.
  Design: VD-0023. Immediate: read-only four-Device and 12-Program source
  audits passed; maintained-text candidates/residuals zero. Mandatory
  publication-integrity gate passed with two identical exports, 499 identities,
  485 unrelated records unchanged, original recovery bytes and matched pair.
  No routine tests run. Deferred: `tests/test_hacking_source_followup.py`,
  `tests/test_hacking_program_publication.py`, `tests/test_rules_database.py`,
  `tests/test_audit_source_variant_inputs.py`, and cumulative
  `tools/run_checks.py --stage test --assets required`.
  Intended host: pinned `linux-dev` with PDF/Wiki/FAQ/raw archive and Chromium;
  regenerate/verify ignored deployed-object publication before the full suite.
  Preserve actual revision, assets, terminal results and skipped coverage;
  hosted and final-candidate gates remain independently required.

## Next unused IDs

- Design: `VD-0024`; active obligations are listed above.
- Execution: `VR-0081`; active obligations are listed above.

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
