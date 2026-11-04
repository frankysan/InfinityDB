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

No pending test-design obligations.

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

- [ ] **VR-0077 (2026-11-04; ready-to-run):** Verify the V1S-034 basic
  BS/CC attack reference expansion. Base revision: `dd0b894b40691aa0a68dea47ee4d8abb76792bcd`;
  target: the committed implementation containing the VD-0020 curated hash and
  rules DB `8f2fa36b3ce3f0293fa217641d780db9d2c300da2f82438d1a6e9adcbc88b609`.
  Work: [V1S-034](TODO.md#rules-and-contextual-reference-completion);
  design: VD-0020 completed by static review of `tests/test_combat_attack_reference.py`
  and shared `tests/reference_acceptance_support.py`: pinned PDF/Wiki, curated/runtime/API
  parity and 1440/390/320 px ordinary Skill navigation/semantic links with errors,
  failed requests, Developer Mode off and overflow assertions. No tests ran in VD.
  Immediate: maintained-text audit zero candidates/residuals;
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

- [ ] **VR-0078 (2026-11-04; ready-to-run):** Verify V1S-034 Template
  references. Base revision: `c451a22d8d7311d0fdc136751839f9e63eda91bb`;
  target: committed implementation with VD-0021 curated hash and rules DB
  `3fd3b9209d5702eb24c9b8bbf6404d70db0ecafafcdce5fd8020d465ebab464f`.
  Design: VD-0021 completed by static review of `tests/test_template_reference.py`
  and the shared helper: source/FAQ/Wiki, exact Trait identity, runtime/API/search,
  three-width normal General Rule/Trait catalog entry points and keyboard links,
  captured browser errors/failed requests and overflow. No tests ran in VD. Immediate artifact-integrity exception: deterministic twin
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

- [ ] **VR-0080 (2026-11-04; ready-to-run):** Verify V1S-035 Hacking
  source/citation and scoped procedure updates. Base:
  `67e3f0447ca9a5990bd8d818105434ef70ea53f8`; target: committed VD-0023
  curation with rules DB `121480b02d2ec81223d167ea1b1c00a556ddd256a42c418b9622059667493349`.
  Design: VD-0023 completed by static review of `tests/test_hacking_source_followup.py`
  and shared helper: printed pages, twelve primary citations, Supportware/Repeater
  corrections, scoped timing/defense, runtime/API parity and 1440/390/320 px
  Program/General Rule/Equipment catalog and link acceptance. No tests ran in VD.
  Immediate: read-only four-Device and 12-Program source
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

  First execution of the three new modules at `b064fd2c`, Linux job
  `linux-dev:477be92e0b784d4e98508b285f477ff0`, returned 10 passed / 5 failed.
  The failures were test expectations: Supportware's literal “only sustain one”
  phrase, FAQ printed-page versus cover offset, and Impact Template's rendered
  “separately” wording at three widths. Corrected assertions retain byte pins,
  API/browser invariants and conditions; execution is still pending on the fix.

- [ ] **VR-0081 (2026-11-04; ready-to-run):** Verify Phase 1 static integrity
  checking for the V1S backlog checker. Base revision:
  `cde1fe7bbb20c426c4705eec0e9252bc8e293de9`; target:
  `52744d32ee37a9923efb3d532d8a1a1f370bcbfa`. Work:
  [V1S-096](TODO.md#final-10-acceptance) and its
  [backlog checker plan](v1s-backlog-checker-plan.md); design VD-0024 was
  statically reviewed and retired without executing tests.
  Windows immediate checks passed: `tests/test_check_v1_backlog.py` and
  `tests/test_test_sections.py` passed 20/20; the default CLI reported 53
  declarations and zero warnings, matching an independent declaration count;
  Ruff, Pyright, Markdownlint, and documentation links passed.
  Deferred broader check: `tools/run_checks.py --profile code`.
  The connected MCP `linux-dev` worker was independently rediscovered and a
  bounded fetch completed on its clean `dev/v1.0.0` checkout. The earlier
  Windows-only workflow's unavailable-runner finding is superseded for this
  handoff. Pin the cumulative committed revision before Linux parity/full-code
  execution; do not infer parity from Windows results. No tests ran during VD design.

- [ ] **VR-0082 (2026-11-04; ready-to-run):** Execute V1S-038's complete
  reviewed Ammunition source/storage/API/browser parity gate. Target: the
  cumulative committed test-design revision following
  `c00e12596043387ad5b7f516dc88bd3401dc6509`, with the unchanged release pair.
  Work: [V1S-038](TODO.md#rules-and-contextual-reference-completion).
  No new test design: existing `tests/test_ammunition_publication_parity.py`,
  `tests/test_ammunition_visibility_opposition.py` and
  `tests/test_verify_ammunition_publication_browser.py` cover eleven base
  identities, five exact ordered combined forms, full source/API publication
  parity and ordinary browser links at 1440/390/320 px. Preserve disclosed
  T2/Flash Pulse and chart conflicts, Combined Saving Roll distinction and
  unreported/sentinel data. Require real Chromium, pinned sources, full assets
  and no skips in these selectors. Run the cumulative full-assets suite and
  `--profile code` on pinned `linux-dev`, after rebuilding/checking ignored
  deployed-object publication. Adding this fifth VR triggers a drain of all
  execution entries; first design VD-0020/0021/0023 without running tests.

  Cumulative Linux code-profile execution at `1c780010`, job
  `linux-dev:2e8fd555a2054cf09299180239a2b04c`, finished with 5,099 passed,
  24 failed, 29 skipped; Ruff/Pyright passed. All fifteen new acceptance cases
  passed. The remaining failures identified missing Template interaction-review
  coverage, two unclassified non-catalog mentions, browser-lane registrations,
  and stale record/source-locator/citation assertions. Repairs are scoped to
  V1S-034/035 integration, preserving historical 367/D304/S63 counts and all
  source/API/browser assertions. These entries stay open until corrected focused
  execution and a pinned cumulative rerun pass. The repaired five-module Windows
  check passed **261/261**, zero skips, in 34.31 s pytest / 35.67 s runner;
  the corrected Linux cumulative run is still required. Complete logs remain in the
  Linux job and ignored run report; dispatch alone does not retire any VR.

## Next unused IDs

- Design: `VD-0025`; active obligations are listed above.
- Execution: `VR-0083`; active obligations are listed above.

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
