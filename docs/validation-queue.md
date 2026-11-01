# Phased validation queue

**Project domain:** Project infrastructure

This file is the single active register for validation work deferred under the
[phased development workflow](testing.md#phased-development-and-validation).
It tracks **test design and execution obligations**, not implementation features,
release scope, or source ambiguities. `docs/TODO.md` owns implementation work
and defects; `docs/releasing.md` owns mandatory release acceptance. Keep stable
IDs here and link the owning task instead of duplicating its description.

## Queue rules

- Separate the four activities: **essential test creation** and
  **essential targeted execution** happen within the implementation pass;
  **additional test design** is deferred as VD; **broader test execution**
  is deferred as VR. A design pass may run newly written tests for sanity
  without turning into a general execution pass. See
  [testing.md](testing.md#phased-development-and-validation).
- Before ending an implementation pass, record every concrete missing
  regression **design** as VD and each change's deferred broader **execution**
  as VR, including changes needing only an existing full-suite or browser run.
  Record exact immediate test selectors and results separately. Never call an
  unrun check passed or defer a required safety, migration or publication gate.
- Design items are `VD-0001`, `VD-0002`, etc. Each ID is one independently
  actionable test requirement, not one test function or a speculative idea.
  Count open `needs-design` IDs toward the **5-requirement design threshold**.
- Execution items are `VR-0001`, `VR-0002`, etc. Each item represents one
  distinct implementation change awaiting deferred verification, including
  changes whose required test design is unfinished. Count distinct open
  implementation changes, not files, tests, commits, or repeated runs, toward
  the **5-change execution threshold**. Combine multiple checks for the same
  change under one VR item. Link any blocking VD IDs.
- When design reaches 5, the next pass handles test design only. When execution
  reaches 5, the next pass handles test execution only, after required test
  design is ready. If both thresholds are reached, design goes first wherever
  it blocks execution. Do not start another ordinary implementation pass until
  the due pass is addressed. A critical gate or an overdue item takes priority.
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
  Store bulky reports under ignored `local/`; record only commands, summary,
  and evidence pointers here. Prune verified records after the relevant
  acceptance has been recorded and the milestone is closed; keep IDs stable,
  never reuse them.

## Pending test design

Each item records:

- **ID / recorded date / status:** `needs-design`, `blocked`, or `designed`.
- **Owning work and change:** link to `docs/TODO.md` section and relevant
  commit, branch, or tracked files.
- **Required behavior:** a concrete *additional* observable setup, action,
  expected result and edge/negative case; identify existing tests to extend.
  Essential direct coverage belongs in the implementation pass, not the VD
  queue. Do not create a VD item just to rerun an existing test.
- **Priority/dependency:** risk and linked VR item.
- **Result:** new or modified test selectors, their individual design-sanity
  results, and date. Broader regression execution remains in VR.

No prospective design items recorded yet. This does **not** certify that prior
work has complete test coverage; existing release and TODO obligations remain.

## Pending deferred execution

Each item records:

- **ID / recorded date / status:** `awaiting-design`, `ready-to-run`,
  `blocked`, or `verified`.
- **Owning work and change:** one distinct implementation change, linked
  TODO section and precise revision/artifact identity.
- **Immediate evidence:** direct existing or newly created regression
  selector(s), required risk-critical lint/data/schema/publication checks,
  pass/fail/skip and date; note why any full module was immediately necessary.
- **Deferred checks:** existing module suite selectors, integration/browser
  acceptance or full profiles, plus any blocking VD IDs. Defer only checks
  that do not undermine the correctness/safety of the current implementation.
- **Result:** executed commands, revision, pass/fail/skip and report location;
  close only after the required checks pass.

- [ ] **VR-0001** (2026-11-01; ready-to-run): Source-only
  Neurocinetics `+1B` occurrence review and pinned regression.
  Work: [Rule-variant usage index](TODO.md#rules-and-reference-completeness)
  (source-ID 109 under the unresolved-parameter inventory);
  revision: `dev/v1.0.0`, working tree based on `75a618bc`,
  `tests/test_audit_source_variant_inputs.py`,
  `docs/TODO.md`, `docs/data-model.md`. Risk: low
  (test and docs only; no schema, runtime, curated record or generated artifact
  change). Immediate: focused test **1 passed**; full affected
  `tests/test_audit_source_variant_inputs.py` **50 passed**;
  Ruff targeted **PASS**, docs **PASS**, `git diff --check HEAD`
  **PASS** (2026-11-01). Design: none pending.
  Deferred: one ordinary full project test run against the
  cumulative implementation state, before the next mandatory merge/release
  acceptance. Exact check: `tools/run_checks.py --stage test`.
  Outcome: awaiting run; the later typed source-109 migration is tracked
  separately as VR-0002. This entry records the earlier source-only review.

- [ ] **VR-0002** (2026-11-01; ready-to-run): Publish typed source-109
  Neurocinetics `+1B` in the curated rules, matched v9 `rules.db`,
  and deployed-object publication, without changing the 17 objects.
  Work: [Rule-variant usage index](TODO.md#rules-and-reference-completeness);
  revision: `dev/v1.0.0` working tree based on `7cb11e9b`.
  Risk: elevated for artifact synchronization (therefore guarded staging,
  pinned-source verification, rollback, and immediate rules/publication checks).
  Immediate: staged and promoted using `tools.stage_neurocinetics_burst`
  from ignored `local/neurocinetics-burst-n53-20261101/`;
  rules sha256 `9f8b482413d39fd7596da4aec63f0a9c2d14525e01c635965763fdec44e7fa08`,
  objects sha256 `3d02fbda90f39b35e33cbaf74300309ecbc969867e1725d41570bb04f50eaa72`;
  source-variant tests **51 passed**, curated negative mutations
  **7 passed**, rules database **166 passed**, deployed-object publication
  **12 passed**; rules stage **PASS**, targeted Ruff **PASS**, Pyright
  **0 errors**, Markdownlint/docs links **PASS**, diff check **PASS**.
  A stale exact-set expectation in the rules database suite was corrected
  and all 166 tests then passed. The three promoted file hashes were
  independently reverified. Design: none pending; tests implemented
  in this pass.
  Deferred: ordinary full project test run (`tools/run_checks.py --stage test`)
  against the cumulative state and the regular mandatory hosted CI/release
  acceptance. Outcome: awaiting broader verification.

## Recording template

Copy a new item into the appropriate section above; use the next unused ID.
Avoid creating an empty item for work fully verified during implementation.

```text
- [ ] VD-0001 (YYYY-MM-DD; needs-design): <required assertion/edge case>.
  Work: <TODO anchor>; change: <revision/files>; risk: <level>.
  Existing coverage: <selector or none>; linked execution: VR-0001.
  Outcome: <new test selector and its design-sanity result, when available>.

- [ ] VR-0001 (YYYY-MM-DD; awaiting-design): <one implementation change>.
  Work: <TODO anchor>; revision: <commit/artifact>; risk: <level>.
  Immediate: <essential created/existing test selector and result;
    required validators and results; reason for any expanded run>.
  Design: VD-0001 or none.
  Deferred: <existing module/full-suite/integration/manual checks>.
  Outcome: <tested revision, command, counts and evidence, when run>.
```
