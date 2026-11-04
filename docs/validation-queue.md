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

- [ ] VR-0069 (2026-11-04; ready-to-run): verify the PT: Endgame review
  disposition update without changing source fields or player-facing
  behavior. Work: [V1S-034](TODO.md#rules-and-contextual-reference-completion);
  revision: source-review and test-design working tree based on
  `39b910cde2dfe656e3746e8d2e8227eb26b4cd6a`; risk: medium. Source evidence:
  N5.3 PDF SHA-256
  `53921e91c2d3d62ad5f7125abcd4174b2cf937d45320233eed5b6d301b66af3f`,
  Army DB SHA-256
  `8a5840d1ff632e89de26210ee7bcb47e54c6579c15b5c3436e226702e872d7c8`,
  Wiki history ZIP SHA-256
  `d49db0515420af297a7349201e8bb7750ecb422048d32bb494273ee1cea78a5d`,
  `Weapon_Chart` revision 4083 and member SHA-256
  `a3a6230051bc3a03e61a6de917306b403bac35ddfa6dcb8962595316bb3722ed`;
  official update dated 2025-04-03. Design: VD-0012 retired after static
  review; no tests executed. Deferred selectors:
  `tests/test_audit_weapon_trait_cross_sources.py::test_pt_endgame_review_explains_trait_and_keeps_army_intent_open`,
  `tests/test_audit_weapon_trait_cross_sources.py::test_wiki_source_review_requires_exact_pdf_revision_and_member_hash`,
  and the full `tests/test_audit_weapon_trait_cross_sources.py` module.
  Also rerun `tools.audit_weapon_trait_cross_sources` with the pinned PDF and
  Wiki ZIP, and `tools/run_checks.py --stage docs`, on the committed revision.
  Intended host: Windows.

## Next unused IDs

- Design: `VD-0013` (through `VD-0012` retired).
- Execution: `VR-0070` (through `VR-0068` retired; VR-0069 active).

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
