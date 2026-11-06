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
     Otherwise, process VR entries due by age or gate. **Execution jobs may
     be batched** across compatible due VRs, including focused selectors as
     well as full-suite coverage; **reconcile and retire each VR individually**
     against its own requirements. Grouping work does not defer a due VR,
     waive a prerequisite or change any threshold. **Dispatch is not
     completion**.
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

## Pending deferred execution

- [ ] VR-0121 (2026-11-06; ready-to-run): Read-only development-status
  CLI reporting Git/V1S, VD/VR, MCP jobs and GitHub exact-SHA workflows.
  Work: user-requested Project infrastructure status command; revision:
  implementation and test-design commit for `tools/dev_status.py` (pin exact
  SHA for VR execution);
  risk: misleading acceptance or stale status.
  Immediate: offline read-only CLI smoke, Ruff, Pyright, docs and Git diff
  checks passed; no online provider smoke was run. These are not deferred
  regression tests.
  Design: VD-0082/0083 completed and retired without executing tests.
  Deferred: `tests/test_dev_status.py` local backlog/queue parsing, exact-SHA
  mocked GitHub responses, monitor filtering/timeout, offline behavior and
  read-only Git inspection; plus
  `tests/test_check_v1_backlog.py::test_selection_accepts_only_documented_pauses_and_not_ambiguous_sources`
  and
  `tests/test_check_v1_backlog.py::test_selection_all_documented_pauses_allow_later_work_without_override`.
  No live CI dispatch or test was run during VD. No skip counts as evidence.
  Intended hosts: Windows and pinned `linux-dev`; reconcile exact-SHA results
  and required providers independently.
- [ ] VR-0118 (2026-11-06; ready-to-run): N5.3 Hackable Unit Profile
  help correction. Work: V1S-082; revision: implementation commit containing
  the guarded v9 publication; risk: source and browser reference accuracy.
  Design: VD-0077 (bilingual PDF clauses), VD-0078 (curated/stored/API and
  typed link), VD-0079 (ordinary keyboard/browser 1440/390/320 px), all
  statically reviewed and retired **without running tests**.
  Immediate: exact English p. 8 / Spanish p. 9 PDF hashes, deterministic
  double v9 export, 498 unrelated identities unchanged, schema/Restrictions
  parity, matched deployed-object/variant-usage publications and guarded
  rollback-safe promotion; both publication verifiers and semantic-link
  audit passed. See the
  [bounded review](v1.0-source-coverage-audit.md#v1s-082-bounded-source-review-hackable-profile-help-2026-11-06).
  Deferred: `tests/test_application_rule_references.py::test_hackable_profile_help_pinned_source`
  (2 source cases), `tests/test_application_rule_references.py::test_hackable_profile_help_export_and_api`,
  `tests/test_verify_scenario_faq_browser.py::test_hackable_profile_help_normal_browser`
  (3 Chromium cases), cumulative application source/reference regressions.
  Intended hosts: Windows for both verified PDF files; explicitly pinned
  `linux-dev` for API/browser/cumulative acceptance with required assets.
  No skip on the intended host counts as evidence. Hosted matrix and
  frozen-candidate release gates remain independently required.
- [ ] VR-0122 (2026-11-06; ready-to-run): Isolated Lieutenant
  Loss-of-Lieutenant timing. Work: V1S-082; revision: curated-rule and
  matched tracked rules-database/publication commit (pin exact SHA for
  execution); risk: source-to-record and normal-browser presentation accuracy.
  Design: VD-0084 completed and retired without executing tests. Immediate:
  passed exact bilingual PDF pins, deterministic double export, unchanged
  496 unrelated records/schema/Restrictions, matched deployed-object and
  variant-usage publications, rollback-safe promotion and semantic-link audit.
  Promoted rules SHA-256
  `a2a1e1e4ccd6bd5e79375fa98762f4bf4eebcd189e0dc7279ccc97d223094729`;
  deployed-object SHA-256
  `13450656eec1764a9cfcc2663133474c94ba762aff5572b4b30be6ca99e46919`;
  variant-usage SHA-256
  `f5ddfc569768b522b3ab93cb59e75453dd30a4c2fa900258959354f7c88d8d74`.
  Deferred: cited-claim/record assertion in
  `tests/test_curated.py::test_checked_in_n5_collection_sources_isolated_lieutenant_timing`,
  rules-database assertion in
  `tests/test_rules_database.py::test_command_order_skill_relations_are_bidirectional`,
  API parity in
  `tests/test_web.py::test_reference_catalog_pages_and_rules_backed_apis_are_served`,
  and Chromium route/citation/keyboard/responsive assertions in
  `tests/test_verify_scenario_faq_browser.py::test_isolated_lieutenant_loss_timing_normal_browser`
  at 1440/390/320 px. No tests run during VD.
  Intended hosts: Windows for pinned bilingual PDF evidence; pinned
  `linux-dev` for rules/API/browser/cumulative checks with required assets.
- [ ] VR-0123 (2026-11-06; ready-to-run): V1S-082 P0 pilot page-identity
  reporting. Work: V1S-082; revision: implementation and test-design change
  (pin exact SHA for execution); risk: misleading page-open reuse estimates
  from snapshot-wide Wiki source IDs. Immediate: exact curated archive
  `member` values are preserved and used for page identity; missing/ambiguous
  values remain unresolved. Ruff passed on the changed Python files, Pyright
  passed with 0 errors/warnings/information, docs passed (44 Markdown files
  and link/backlog checks), and read-only pilot CLI/JSON inspection passed.
  Output: 35 records, 10 cohorts, 129 citation occurrences, 125 locators,
  104 page identities, 0 unresolved locators and 25 page-reuse candidates;
  zero approvals and empty measurement fields. V1S selection and
  `git diff --check` passed. No tests or reviewer-time/source-open measurements
  were run.
  Design: VD-0085/0086 completed and retired without executing tests. Deferred:
  `tests/test_report_reference_baseline.py::test_source_page_identity_requires_addressable_locator`
  and
  `tests/test_report_reference_baseline.py::test_v1s082_fixed_pilot_selection_is_valid_fail_closed_and_unapproved`
  and
  `tests/test_report_reference_baseline.py::test_v1s082_pilot_suppresses_page_metrics_when_wiki_member_is_missing`.
  Intended hosts: Windows and pinned `linux-dev`. No tests run during VD.

- [ ] VR-0124 (2026-11-06; ready-to-run): V1S-082 MOV Glossary-anchor
  navigation and source-169 TinBot Firewall usage browser coverage.
  Work: V1S-082; revision: browser-test-design commit, pin exact SHA
  and unchanged tracked Army/rules/variant-usage publications before execution.
  Risk: semantic source variants being hidden, incorrectly labeled, or
  disconnected from the normal keyboard navigation path.
  Design: VD-0087 (follow MOV link into the actual Glossary card) and
  VD-0088 (source ID 169 family/variant/usage), both statically reviewed
  and retired without test execution. Ruff passed on the changed module.
  Deferred: `tests/test_verify_scenario_faq_browser.py::test_movement_attribute_glossary_anchor_normal_browser`
  and `tests/test_verify_scenario_faq_browser.py::test_tinbot_firewall_source_169_usage_normal_browser`
  (each 1440/390/320 px Chromium), plus the existing
  `test_attribute_dash_and_swc_normal_browser`,
  `test_unpublished_tinbot_source_variant_is_not_a_fake_public_route`
  and relevant catalog/source-variant checks.
  Intended host: pinned `linux-dev` with required browser assets and
  matched variant-usage publication. No skip or merely static design
  review counts as acceptance. Hosted CI and source-wide acceptance
  remain separately owned.

A VR entry records its ID/date/status (`awaiting-design`,
`ready-to-run` or `blocked`), the implementation revision/artifact,
immediate focused checks and results, any required VD dependencies,
deferred test selectors/gates, and the final execution outcome.
Retire it once required checks pass on the intended state and the outcome
is recorded. Failed or incomplete verification remains open.

The five-item November 4 drain was verified at
`1d0d5c196b87983737981b8b8244321b552527a4`; see the linked testing
summary above. Hosted CI and final release gates retain separate owners.

## Next unused IDs

- Design: `VD-0089`; VD-0087/0088 were reviewed and retired without running tests.
- Execution: `VR-0125`; active obligations are listed above.

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
