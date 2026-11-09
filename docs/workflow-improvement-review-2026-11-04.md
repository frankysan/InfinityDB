# InfinityDB workflow improvement review — 2026-11-04

**Project domain:** Project infrastructure  
**Type:** Dated investigation and recommendations, not a new implementation register.  
**Review basis:** The `dev/v1.0.0` working tree, repository instructions, development tools, validation/CI contracts, recent Git commits and selected hosted CI logs. The initial investigation reviewed 100 commits covering 2026-11-03 to 2026-11-04, with the published repository at `67e3f044`; this report was saved after subsequent work advanced the branch. Refer to `docs/TODO.md`, `docs/validation-queue.md` and `docs/ci.md` for **current**, rather than historical, task and gate status.

## Executive assessment

InfinityDB has substantial source, test, publication and release safeguards. Its largest workflow risk is not a lack of test cases or written procedures but **missing low-cost, machine-verifiable checkpoints between existing procedures**: task selection, task retirement, test-design/execution scheduling, generated-data impact analysis and CI result attribution.

Preserve the strict VD/VR drain policy, source uncertainty handling, independent Windows/Linux checkouts, explicitly invoked Git synchronization, and exact-revision release acceptance. Prefer reusing existing audit and validation tools over introducing parallel task registries.

**Recent Git sample:** of the 100 examined commits, 64 were `docs:`, 12 `fix:`, 12 `feat:` and 12 `test:`; 20 commit subjects mentioned retiring or closing work. This is evidence that task-state bookkeeping is a substantial part of the current development cycle, but not evidence that documentation work is intrinsically unnecessary.

## Confirmed findings

### 1. Catalog additions invalidate several dependent checks

Hosted **Source checks** for commit `19713856` failed on Ubuntu/Python 3.11 with **19 failed, 4,166 passed and 947 skipped** tests. Introducing the Template reference changed the published rule identity/count assumptions and affected multiple independent checks:

- An expected record count changed from 498 to 499.
- The rules-interaction review lacked `rule:template-weapons-and-equipment`.
- Deployed-object non-catalog discovery produced two additional unreviewed candidates.
- Frozen explanation-inventory expectations no longer matched the updated catalog.

These were correlated downstream effects of a catalog change rather than 19 independent feature bugs. A previous run for `c451a22d` likewise failed in source checks while installed-wheel and deployment-smoke workflows passed.

**Evidence:** [Source checks run 41915505813](https://github.com/frankysan/InfinityDB/actions/runs/41915505813), [source-checks.yml](../.github/workflows/source-checks.yml), [rules-interaction audit](../tools/audit_rules_interactions.py), [explanation baseline](../tools/report_reference_baseline.py).

**Recommendation:** a read-only *catalog change-impact report*, driven by changed source identities and canonical input diffs, should enumerate dependent review inventories, source audits, database/export checks and relevant API/browser tests before a commit. Begin with existing audit modules, not a new source-of-truth manifest. Report obligations without bypassing VD test design or VR deferred execution.

### 2. Backlog integrity needs coverage beyond numbered V1S entries

The original V1S backlog-checker plan (retired after implementation; current commands are in [the testing guide](testing.md#v1s-backlog-checks)) concentrated on numbered execution-slice declarations. A different, actual checkbox issue appears under the parent **Establish the 1.0 completeness baseline** in the then-current `docs/TODO.md` register: the *Select and pin the intended Army, rules/FAQ/annex and Wiki review inputs* subtask is checked while its nested *Refresh the release-candidate baseline and source occupancy gate* subtask remains unchecked. This conflicts with the [backlog-retirement contract](README.md#backlog-completion-and-retirement).

At the time this report was saved, Phase 1 of `tools/check_v1_backlog.py` was implemented for the V1S register; Linux parity was still tracked separately in its validation obligation, and Phases 2–4 remained proposed. This report does **not** imply those phases are still unimplemented in a future checkout.

**Recommendation:** extend the existing checker or a shared parser to validate checkbox hierarchy across **all** of `docs/TODO.md`. Correct the inconsistent subtree only after confirming the actual intended scope; do not automatically check the incomplete child. Keep numbered-ID reconciliation and broader Markdown hierarchy checks separate internally.

### 3. Test-section registration errors are discovered too late

The project already has [`test_test_section_config_covers_every_test_module_exactly_once`](../tests/test_test_sections.py), which compares all discovered `test_*.py` modules with the maintained [test-sections mapping](../config/testing/test-sections.json). Commit `ad1416a0` fixed missing Chromium verifier registrations.

That structural check currently runs through pytest, so a missing registration may not surface until a comparatively expensive test run. The test-section map contains model, web, browser, build, operations and assets groups.

**Recommendation:** expose a cheap, deterministic, non-pytest validation of test-section mapping as part of an existing fast preflight/lint stage. Reuse `tools/test_sections.py` and its contract; do not create a second registration format. Existing pytest coverage should still verify the checker.

### 4. CI status is SHA-sensitive and some dashboard information becomes stale

[CI policy](ci.md#agent-ci-monitoring-and-repair) already distinguishes queued, running, successful, failed, cancelled, skipped and untriggered checks. Source checks currently run for **pull requests, pushes to `main`, and manual dispatch**; an unassociated development-branch push need not trigger the full matrix.

An open `dev/v1.0.0` pull request was generating CI runs during the investigation. At the sampled time, source runs for `c451a22d` and `19713856` failed, while the corresponding installed-wheel and deployment-smoke workflows passed. A different SHA's success cannot close their failure.

Separately, the then-current V1S-093 task in `docs/TODO.md` retained an older, once-relevant CI run reference (`41858032642`) despite newer hosted attempts. A task should describe **remaining acceptance conditions**; an automated status query should supply the latest SHA/run outcomes.

**Recommendation:** add a concise read-only *development status* command returning local HEAD, dirty paths, remote divergence if known, VD/VR counts/age, worker job IDs, and CI statuses keyed by exact SHA. Distinguish `passed`, `failed`, `pending`, `not triggered` and `superseded`; use JSON for MCP monitoring. Do not mutate TODO files on every run or interpret an empty VR queue as hosted acceptance.

### 5. Repeated full CI executions consume resources and obscure root causes

The three principal workflows—[source checks](../.github/workflows/source-checks.yml), [installed-wheel smoke](../.github/workflows/installed-wheel.yml) and [deployment smoke](../.github/workflows/deployment-smoke.yml)—did not declare a GitHub Actions `concurrency` group when reviewed. Rapid commits to an open pull request can therefore overlap full matrix runs; individual old results still have historical value but may no longer be the next actionable validation.

**Recommendation:** consider `concurrency` with cancellation **only for superseded pull-request runs**, grouped by workflow and PR, while preserving manual `workflow_dispatch`, final-release exact-SHA validation and any intentionally retained CI evidence. First determine how this interacts with required check names and [release evidence collection](ci.md#release-evidence-retention).

Add a per-run failure summary grouped by *underlying changed identity / unmet contract* instead of flooding the handoff with individual assertion failures. Preserve full logs and actual test counts.

### 6. Concurrent agent work requires a lightweight ownership checkpoint

The MCP Git interface already guards unsafe cross-worker operations and uses explicit stage/commit/push calls. The investigation encountered an active, dirty Windows checkout containing source/data work alongside checker implementation; later work continued to evolve independently.

**Recommendation:** before editing and again before staging, compare the planned file set and baseline HEAD with the current checkout, explicitly identify unexpected modified files, and avoid staging unrelated agent/user changes. A read-only `--task-files` or `--scope` check could summarize overlap, but should not impose a global workspace lock or automatically synchronize Git.

### 7. Agent policy is duplicated and difficult to keep synchronized

[`AGENTS.md`](../AGENTS.md) is extensive and detailed workflow rules appear again in multiple agent skills. The [VD/VR policy](validation-queue.md#queue-rules) is already canonical, but repetition invites divergent guidance when rules change.

**Recommendation:** keep a short task-boundary execution contract in `AGENTS.md`: inspect status, drain due VD/VR, select task, implement, register obligations, reconcile previous task, validate and commit. Link to canonical topic owners and retain domain-specific details only where needed. Do not initiate a sweeping documentation rewrite ahead of 1.0.

### 8. Tool sprawl raises discoverability costs

At investigation time `tools/` contained 141 Python files, including 43 `audit_*`, 19 `stage_*`, 14 `verify_*` and four `build_*` modules. Their specialization is often justified, but agents may select the wrong legacy/staging tool or overlook an existing maintained validator.

**Recommendation:** create a compact, generated or curated tool inventory classifying each entry point as authoritative, reusable helper, staging-only or historical. Prefer a common dispatch/impact interface over additional one-off wrappers. A tool inventory must not become a second authority for source rules.

### 9. Distinguish source-suite success from real browser acceptance

In the sampled failed Ubuntu CI run, 947 tests were skipped, many because Playwright was deliberately not installed on the source-check runner. This is consistent with the documented non-Playwright `.[dev,symbols]` CI environment; it is not inherently a defect.

**Recommendation:** every status summary should show **browser acceptance as a separate gate**, recording its actual worker, commit, browser dependencies, result and skip reasons. The source-suite pass count must not be presented as proof of completed Chromium browser coverage.

## Priorities and proposed implementation

| Priority | Improvement | Initial implementation target |
| --- | --- | --- |
| P1 | Broaden backlog + validation-queue integrity | Whole-TODO nested-checkbox checks; VD/VR IDs, next-ID counters, VD→VR links, overdue/due detection |
| P1 | Change-impact preflight | Read-only rule identity delta → dependent audits, frozen inventories and affected tests |
| P1 | Unified development status | Exact-SHA local / worker / CI snapshot with terminal-state and skip distinctions |
| P2 | PR CI run deduplication | Scoped concurrency and useful grouped failure summaries |
| P2 | Agent change ownership | Pre-edit/pre-stage overlap and baseline verification |
| P2 | Instruction consolidation | One concise task-boundary contract referencing canonical docs |
| P2 | Maintained tool discovery | Classified tool inventory and reuse guidance |

### Batch A — Integrity and task bookkeeping

1. Extend the ongoing checker to cover non-V1S task hierarchy.
2. Validate VD/VR queue identity, age, link integrity and threshold triggers using existing queue semantics.
3. Add a cheap test-section configuration check.
4. Fix confirmed invalid TODO nesting through the established task-closeout and validation process.

### Batch B — Development feedback

1. Implement catalog change-impact reporting from existing audits and source deltas.
2. Implement a consolidated read-only development-state interface with exact revision attribution.
3. Support JSON output for MCP and a future lightweight monitoring UI; do not create a parallel completion ledger.

### Batch C — CI efficiency and guidance

1. Evaluate and implement safe PR-only concurrency/cancellation, never weakening release gates.
2. Add concise, root-cause-oriented CI diagnostics and separate browser gate status.
3. Consolidate repeated agent instructions and improve tool discoverability.

## Acceptance principles

- **No silent status changes:** reports recommend; they do not close TODO entries or VRs.
- **No automatic Git mirroring:** Windows and Linux retain independently chosen commits and explicit synchronization.
- **No shortcut around VD/VR:** static non-test integrity checks may run where allowed; authoring and executing regressions still follow the queue.
- **No unsupported success claims:** report exact SHA, evidence inputs, test coverage and skipped/required gates.
- **No duplicate source of truth:** `TODO.md` owns tasks, `validation-queue.md` owns deferred tests, `ci.md` owns hosted checks, and each source/audit retains its canonical owner.
- **Cross-platform validation:** Windows and Linux behavior must be verified before adding a new mandatory check.

## Disposition

This is a **dated analysis report**, not a standing task ledger or an approval to implement every proposal. Fold accepted improvements into their existing canonical owners; once implemented and no longer needed as active rationale, retire this report through Git history rather than continually appending status updates.

**File changes for this report:** Documentation only. The contemporaneous development worktree contained other uncommitted files; those files are unrelated to the findings and must not be staged or altered as part of saving this report.
