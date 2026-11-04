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

- [ ] **VD-0015 (2026-11-04; needs-design):** Pin all ten exact single-extra
  BS Attack source-201 signatures, their counts (1,531 total), absence of
  raw/multi-extra variants, and all nine profile-owned `SR-2` occurrences
  against the selected raw Army archive. Reject an added, reordered,
  duplicated or changed signature without independent source review.
  Work: [V1S-055](TODO.md#rule-variant-usage-index-and-restrictions);
  change: 2026-11-04 source review; risk: medium.
  Existing coverage: `test_pinned_source_variant_inventory_is_complete_and_conservative`
  checks aggregate counts only; generic exact-combination checks do not pin
  source 201. Linked execution: VR-0072.
  Target design: `tests/test_audit_source_variant_inputs.py::test_bs_attack_source_201_exact_signatures_and_sr2_owners`.
  Outcome: pending test authorship and static design review; no tests run.

- [ ] **VD-0016 (2026-11-04; needs-design):** Pin CC Attack source-240's
  ten exact single-extra signatures (625 direct occurrences), including
  owner/position/type and literal `+1 Dam` on exactly two Reinforcement
  profiles, and confirm the unknown qualifier remains unreviewed.
  Work: [V1S-056](TODO.md#rule-variant-usage-index-and-restrictions),
  clarification SRC-032; change: 2026-11-04 raw-source review; risk: medium.
  Existing coverage: aggregate inventory fixture and generic unknown-extra
  tests, but no source-240 signatures/owners.
  Linked execution: VR-0073.
  Target design: `tests/test_audit_source_variant_inputs.py::test_cc_attack_source_240_exact_signatures_and_damage_owners`.
  Outcome: pending test authorship and static design review; no tests run.

- [ ] **VD-0017 (2026-11-04; needs-design):** Pin Peripheral source-243's
  five single-extra subtype signatures (439 rows), all profile-owned
  source records and the eight distinct Cyberplug profile occurrences
  (four Connected/Autonomous pairs across two Armies). Assert no
  Controller/Unit/Loadout source owner is manufactured by the subtype
  lookup and no unreviewed extras are promoted.
  Work: [V1S-057](TODO.md#rule-variant-usage-index-and-restrictions);
  change: 2026-11-04 source review; risk: medium.
  Existing coverage: source inventory global counts and synthetic
  Controller/Peripheral relationships; no source-243 owner regression.
  Linked execution: VR-0074.
  Target design: `tests/test_audit_source_variant_inputs.py::test_peripheral_source_243_exact_subtypes_and_profile_ownership`.
  Outcome: pending test authorship and static design review; no tests run.

- [ ] **VD-0018 (2026-11-04; needs-design):** Pin all eight Transmutation
  source-246 single-extra signatures (295 rows), all profile-owned source
  occurrences, the exact trailing ASCII space in the `Escape System -3` value, and
  the two unmodified SWITCHERS GRUPPA `WIP` occurrences. Guard
  threshold, Escape System, Auto and Hatching against loss of the
  exact Army/Profile/occurrence identity; fail closed on new extras.
  Work: [V1S-058](TODO.md#rule-variant-usage-index-and-restrictions);
  change: 2026-11-04 source review; risk: medium.
  Existing coverage: global pinned inventory only; general Transmutation
  family facts and unrelated action tests exist, but no exact source-246
  signature/owner regression. Linked execution: VR-0075.
  Target design: `tests/test_audit_source_variant_inputs.py::test_transmutation_source_246_exact_signatures_and_profile_owners`.
  Outcome: pending test authorship and static design review; no tests run.

- [ ] **VD-0019 (2026-11-04; needs-design):** Guard against cross-family
  source-extra aliasing: the same `+3`, `-3`, Shock/AP/Continuous Damage,
  ReRoll, and `Total` values must not authorize a different Skill's
  occurrence semantics; preserve unqualified Device Plus `SR-1` as unknown.
  Pin ten unresolved Skill source IDs and one unresolved Equipment ID
  without converting reviewed neighboring variants into global effects.
  Work: [V1S-061](TODO.md#rule-variant-usage-index-and-restrictions);
  change: 2026-11-04 cross-family review; risk: medium.
  Existing coverage: individual source extras and generic fail-closed
  combinations, but no cross-family source collision assertion.
  Linked execution: VR-0076.
  Target design: `tests/test_audit_source_variant_inputs.py::test_unresolved_source_extras_do_not_inherit_other_families_review`.
  Outcome: pending static test design, not execution.

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

- [ ] **VR-0072 (2026-11-04; awaiting-design):** Verify V1S-055's
  pinned BS Attack source-201 signature and source-owner characterization.
  Work: [V1S-055](TODO.md#rule-variant-usage-index-and-restrictions);
  revision: 2026-11-04 review commit pending; risk: medium.
  Immediate: read-only source-variant audit reports 1,531 direct source rows,
  ten single-extra signatures, zero raw values and nine `SR-2` profile owners;
  documentation checks to be recorded at commit.
  Design: VD-0015.
  Deferred: new exact pinned-source regression and relevant source-variant
  module, then shared full-suite evidence when required for release.
  Outcome: not executed; raw archive required on the chosen worker.

- [ ] **VR-0073 (2026-11-04; awaiting-design):** Verify V1S-056's exact
  CC Attack source-240 signatures and the two `+1 Dam` owner records.
  Work: [V1S-056](TODO.md#rule-variant-usage-index-and-restrictions),
  SRC-032; revision: 2026-11-04 review commit pending; risk: medium.
  Immediate: read-only source audit confirms 625 direct rows, ten
  single-extra signatures and two `4/TEXT:+1 Dam` profile owners;
  docs verification to be recorded at commit.
  Design: VD-0016.
  Deferred: exact pinned-source regression and the relevant source-variant
  test module; full-suite evidence when required for release.
  Outcome: not executed; raw archive required on the chosen worker.

- [ ] **VR-0074 (2026-11-04; awaiting-design):** Verify V1S-057's
  five exact Peripheral subtype signatures, 439 profile-owner rows
  and the separate Cyberplug Connected/Autonomous pairs.
  Work: [V1S-057](TODO.md#rule-variant-usage-index-and-restrictions);
  revision: 2026-11-04 review commit pending; risk: medium.
  Immediate: read-only source audit and exact owner queries completed;
  docs verification to be recorded at commit. Design: VD-0017.
  Deferred: pinned source-variant regression with raw Army archive and
  relevant source-variant test module; cumulative release acceptance.
  Outcome: not executed; raw archive required on the chosen worker.

- [ ] **VR-0075 (2026-11-04; awaiting-design):** Verify V1S-058's
  Transmutation source-246 eight signatures, 295 profile owners and
  unmodified WIP/trailing-space Escape source distinctions.
  Work: [V1S-058](TODO.md#rule-variant-usage-index-and-restrictions);
  revision: 2026-11-04 review commit pending; risk: medium.
  Immediate: read-only audit and all eight exact source-owner queries
  completed; docs verification to be recorded at commit. Design: VD-0018.
  Deferred: source-exact regression on the pinned raw Army archive,
  relevant source-variant test module and eventual release gates.
  Outcome: not executed; raw archive required on the chosen worker.

- [ ] **VR-0076 (2026-11-04; awaiting-design):** Verify cross-family
  exact source identity and fail-closed collisions against the pinned
  Army/rules pair. Work: V1S-061; change: review commit pending.
  Immediate: read-only unresolved Skill/Equipment inventory audited;
  documentation checks to be recorded. Design: VD-0019.
  Deferred: exact source regression, relevant pinned-source test module.
  Outcome: not executed; raw archive required on the chosen worker.

## Next unused IDs

- Design: `VD-0020` (through `VD-0014` retired; `VD-0015`–`VD-0019` open).
- Execution: `VR-0077` (through `VR-0071` retired; `VR-0072`–`VR-0076` open).

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
