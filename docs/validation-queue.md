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
  Count open `needs-design` IDs toward the **3-requirement design threshold**.
- Execution items are `VR-0001`, `VR-0002`, etc. Each item represents one
  distinct implementation change awaiting deferred verification, including
  changes whose required test design is unfinished. Count distinct open
  implementation changes, not files, tests, commits, or repeated runs, toward
  the **5-change execution threshold**. Combine multiple checks for the same
  change under one VR item. Link any blocking VD IDs.
- **Strict drain loop (check at every work boundary):**
  1. If **VD >= 3**, process **all open VD entries to zero**, one at a
     time. Otherwise, process any VD due by age or a mandatory gate.
     Write/revise the tests and link them to VR, but **run no tests**.
  2. If **VR >= 5** or any VR is due by age or a mandatory gate, first
     complete **all open VD prerequisites** of those due VR entries,
     even when VD is below 3. A blocked VD leaves its dependent VR
     blocked; never bypass the prerequisite.
  3. If **VR >= 5**, execute and reconcile **all open VR entries to zero**.
     Otherwise, process VR entries due by age or gate. **Run the smallest
     sufficient impact-based focused test set first.** Compatible VRs may
     share the same pinned execution, but **each VR must be reconciled
     individually** against its own requirements. The five-item threshold
     never requires a full suite by itself: run one only for a separately
     documented release/cumulative gate or cross-cutting risk that focused
     tests cannot cover. Repair focused failures before widening tests.
     Grouping work does not defer a due VR, waive a prerequisite or change
     any threshold. **Dispatch is not completion**.
  4. Recount both queues and check overdue/gated entries. If VD >= 3 or
     VR >= 5, restart at step 1; otherwise resume ordinary implementation
     only after all individually due work is handled.
  Reaching a numeric threshold triggers a drain to **zero**, not a pause
  when the count falls below its threshold. Never start ordinary
  implementation while due queue work is idle or running focused VR tests.
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
  Follow the [dispatch/retirement protocol](testing.md#parallel-windows-development-and-linux-validation)
  and [validation batch procedure](testing.md#validation-batch-planning).
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

A VD entry records its ID/date/status (`needs-design` or `blocked`),
owning TODO work and revision, concrete missing assertion/edge case,
existing coverage, risk, linked VR ID, and resulting test selector and
static design-review outcome. Do not record a test result in VD. Retire
the entry when its design review is complete; retain the unrun test
selector and other dependencies in its VR item.

- [ ] VD-0115 (2026-11-07; needs-design): Review the shared
  `rulesReferenceSection` regression for a cited rules card with no
  redundant collection/game line and an uncited card retaining
  applicability; confirm the Citation link and source metadata remain
  unchanged. Review the 1440/390/320 px, light/dark FAQ geometry
  assertion for at least 16 px between a FAQ group and its next visible
  Unit-use/disclosure section (including a hidden Developer Mode
  intermediate sibling).
  Work: [Reference card layout and FAQ citations](TODO.md#implemented-foundations-and-remaining-scope);
  change: `rules-reference.js`, `page-overrides.css`; risk: low.
  Existing modified selectors: `tests/rules_text_render_harness.mjs`,
  `tests/test_web.py::test_detail_frontends_share_curated_rules_reference_renderer`, and
  `tests/test_verify_scenario_faq_browser.py::test_faq_single_source_line_and_card_separation`.
  Design only; linked execution: **VR-0141**.

## Pending deferred execution

A VR entry records its ID/date/status (`awaiting-design`,
`ready-to-run` or `blocked`), the implementation revision/artifact,
immediate focused checks and results, any required VD dependencies,
deferred test selectors/gates, and the final execution outcome.
Retire it once required checks pass on the intended state and the outcome
is recorded. Failed or incomplete verification remains open.

- [ ] VR-0138 (2026-11-07; ready-to-run): Verify the Skill-detail
  FAQ/occurrences spacing and Developer Mode-only exact source usage.
  Work: [Skill detail spacing](TODO.md#implemented-foundations-and-remaining-scope);
  revision: CSS base `9add9ae`, visibility base `3551d09`, plus this
  focused UI batch (pin final SHA before execution); risk: low.
  Design: **VD-0112 completed**, selectors statically reviewed with
  Ruff and Pyright green; no browser tests executed.
  Deferred: `tests/test_verify_scenario_faq_browser.py::test_skill_faq_card_padding_and_developer_occurrence_geometry`
  (1440/390/320 px, both themes, card inset and 24 px source-occurrence
  clearance) and
  `tests/test_web.py::test_variant_usage_browser_links_exact_contexts_and_unit_profile_groups`
  (Skill/Equipment hidden-visible-hidden and original Unit links).
  Outcome: pending.

- [ ] VR-0139 (2026-11-07; ready-to-run): Validate standalone
  /rules/restrictions, backward-compatible anchors, typed contextual links,
  responsive theme/layout and controlled source failure.
  Work: [Restrictions chart standalone page](TODO.md#implemented-foundations-and-remaining-scope);
  revision: `877d308` chart, `3551d09` contextual visibility and this
  test-design batch (pin final SHA before execution); risk: moderate.
  Design: **VD-0113 completed**, Ruff and Pyright static checks green.
  Existing dedicated-page and 3-width core navigation passed on
  `877d308`, but **not the subsequently changed assertions**.
  Deferred: `tests/test_game_mode_source_table.py::test_restrictions_chart_normal_chromium_at_three_widths`
  (desktop/390/320, light/dark, Back/Forward, hash links, seven owner
  contexts hidden by default and shown in Developer Mode, controlled 503),
  plus `test_restrictions_reference_has_standalone_rules_page` and
  source-publication integrity. Outcome: pending.

- [ ] VR-0140 (2026-11-07; ready-to-run): Validate individual Deployed
  object cards, full-width Orders & AROs sections, and single linked FAQ
  `Sources:` lines with readable spacing and intact source discrepancies.
  Work: [Reference card layout and FAQ citations](TODO.md#implemented-foundations-and-remaining-scope);
  revision: this UI batch from `3551d09` (pin SHA before execution);
  risk: moderate. Design: **VD-0114 completed**; Ruff and Pyright static
  checks green, no implementation-time browser tests run.
  Deferred: focused
  `tests/test_verify_deployed_object_publication_browser.py::test_chromium_reviewed_attributes_delivery_navigation_and_missing_values`,
  `tests/test_verify_orders_aros_browser.py::test_orders_aros_page_renders_and_filters_without_overflow`,
  `tests/test_verify_scenario_faq_browser.py::test_faq_single_source_line_and_card_separation`,
  `tests/test_verify_scenario_faq_browser.py::test_fireteam_faq_discloses_real_source_conflict_not_language_omission`,
  and affected FAQ source/browser and movement cases, at 1440/390/320
  in both themes where applicable. Check the JavaScript DOM harness and
  unchanged FAQ temporal/source-selection API gates. Outcome: pending.

- [ ] VR-0141 (2026-11-07; awaiting-design): Verify suppression
  of redundant applicability text when a rules card already cites its
  source, continued scope display for uncited cards, and 24 px FAQ
  bottom margin before Unit-use disclosures.
  Work: [Reference card layout and FAQ citations](TODO.md#implemented-foundations-and-remaining-scope);
  revision: post-`25a2280` follow-up (pin final SHA); risk: low.
  Design: **VD-0115**. Deferred: shared JS rules-card Node DOM
  harness; focused rules-reference frontend assertion and 1440/390/320 px
  light/dark FAQ separation test. No browser/Node tests executed in
  implementation. Outcome: pending.

The [V1S-083 disclosure and consumer batches](testing.md#known-source-disclosure-acceptance-v1s-083--vr-0137)
passed on the recorded Linux/Windows states and close VR-0137. Hosted CI
and final release gates remain separate.

The five-item November 4 drain was verified at
`1d0d5c196b87983737981b8b8244321b552527a4`; see the linked testing
summary above. The
[VR-0126 Property regression](testing.md#v1s-082-weapon-property-source-and-browser-regression-vr-0126)
and [VR-0127 Equipment regression](testing.md#v1s-082-equipment-glossary-navigation-regression-vr-0127)
and [VR-0128 Label source visibility](testing.md#v1s-082-label-vocabulary-source-visibility-vr-0128)
and [VR-0129 embedded source visibility](testing.md#v1s-082-embedded-glossary-source-visibility-vr-0129)
and [VR-0130 reference-only Equipment variants](testing.md#v1s-082-reference-only-equipment-variants-vr-0130)
and [VR-0131 Pheroware citations](testing.md#v1s-082-pheroware-citation-regression-vr-0131)
and [VR-0133 Weapon Chart rows](testing.md#v1s-082-weapon-chart-early-row-regression-vr-0133)
and [VR-0134 Weapon-profile citations](testing.md#v1s-082-weapon-profile-citation-regression-vr-0134)
and [VR-0135 Equipment source scope](testing.md#v1s-082-reference-only-equipment-source-scope-vr-0135)
and [VR-0136 runtime snapshot identity](testing.md#v1s-082-runtime-snapshot-identity-repair-vr-0136)
passed on pinned Windows revisions. Hosted CI and final release gates retain separate owners.

## Next unused IDs

- Design: `VD-0116`; active obligations are listed above.
- Execution: `VR-0142`; active obligations are listed above.

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
