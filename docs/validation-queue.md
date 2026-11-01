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

- [ ] **VD-0001** (2026-11-01; needs-design): Extend source-56
  Minelayer variant validation with negative cases that mutate the
  extra ID, raw type/value, `count` (including boolean), effect kind
  and action scope, asserting each malformed curated document is
  rejected. Separately check that an ordinary unparameterized
  Minelayer occurrence does not receive an inferred numeric count
  and that the source's one profile-level owner is retained.
  Work: [Rules variant source reconciliation](TODO.md#rules-and-reference-completeness);
  change: `dev/v1.0.0` after `16653b16`, files
  `src/infinity_db/curated.py` and `data/curated/rules/n5-core-v5.3.json`.
  Existing coverage: essential exact-signature and 15-owner test in
  `tests/test_audit_source_variant_inputs.py`; current closed
  validator accepts only `267/TEXT:2`. Risk: moderate;
  linked execution: VR-0003. Outcome: test design deferred.

- [ ] **VD-0002** (2026-11-01; needs-design): Add negative
  curated-source validation cases for Chain of Command
  `375/TEXT:Non Specialist`: altered extra ID, raw value/type,
  effect kind/scope and `excluded` (including a non-boolean).
  Assert only the exact source-26 annotation is accepted.
  Work: [Rules variant source reconciliation](TODO.md#rules-and-reference-completeness);
  change: `dev/v1.0.0` after `980fb6b3`; existing coverage:
  `test_chain_of_command_non_specialist_matches_exact_source_owners`
  and the closed curated validator. Risk: moderate; linked
  execution: VR-0004. Outcome: design deferred.

- [ ] **VD-0003** (2026-11-01; needs-design): Add a pinned
  Army-to-filter parity check for Chain of Command (Non Specialist):
  the 11 exact options must never qualify through Chain of
  Command alone, while other qualifying Specialist Skills remain
  independently valid in the supported contexts. Keep candidate
  Unit aggregation distinct from per-profile qualification.
  Work: [Specialist Troops filter](TODO.md#rules-and-reference-completeness);
  change: `dev/v1.0.0` after `980fb6b3`; existing coverage:
  `test_specialist_candidates_ignore_non_specialist_chain_but_keep_other_skills`
  uses synthetic variants. Risk: moderate; linked execution:
  VR-0004. Outcome: design deferred.

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

- [ ] **VR-0003** (2026-11-01; awaiting-design): Publish
  source-56 Minelayer (2) deployment item-count semantics using
  `267/TEXT:2`, without changing deployed-object identities.
  Work: [Rules variant source reconciliation](TODO.md#rules-and-reference-completeness);
  revision: `dev/v1.0.0` working tree based on `16653b16`;
  risk: elevated for coordinated generated publication.
  Immediate: `tools.stage_minelayer_count` stage/promote with
  exact curated/Army/PDF fingerprints and 17 unchanged objects;
  stored pair SHA-256: rules
  `4e9c3493338ec4bf3067ab3838f0ca5bda9879469f9f506c6749854175b6453f`,
  objects `9db94143da110c3ff86703a2cf40c4f3f8e77100004b0da5094520488a9835d2`.
  `test_minelayer_two_deployment_count_matches_pinned_source`
  **1 passed**; `test_current_dodge_reviewed_extra_effects_keep_exact_source_types`
  **1 passed**; `test_pinned_publication_is_deterministic_and_source_complete`
  **1 passed**. Rules stage, publication `--check`, and targeted
  Ruff **PASS** (2026-11-01). The generic v9 refresh declined to run
  because its schema-version precondition was not met, before any
  artifact mutation; the guarded script was used instead.
  Design: VD-0001, nonessential additional negative/edge coverage.
  Deferred: targeted completed design tests and a cumulative
  `tools/run_checks.py --stage test` / normal mandatory CI and
  release gates on the final reviewed state. Outcome: awaiting design
  and broader execution; immediate publication integrity verified.

- [ ] **VR-0004** (2026-11-01; awaiting-design): Publish
  source-26 Chain of Command (Non Specialist) as a typed
  `specialist-qualification-exclusion` on the exact
  `375/TEXT:Non Specialist` source extra.
  Work: [Rules variant source reconciliation](TODO.md#rules-and-reference-completeness);
  revision: `dev/v1.0.0` working tree based on `980fb6b3`;
  risk: elevated for the synchronized curated/rules/publication
  migration, and moderate for scenario Specialist qualification.
  Immediate: staged and promoted with
  `tools.stage_chain_of_command_non_specialist` under ignored
  `local/chain-of-command-non-specialist-20261101/` using pinned
  Army/PDF/source checks and retained rollback. All 17 deployed
  objects unchanged. Focused source-26 owner regression **1 passed**,
  rules-database exact map **1 passed**, Specialist filter
  independent-qualifier test **1 passed**, deployed-publication
  determinism test **1 passed**. Publication `--check`, rules
  stage and targeted Ruff **PASS**. Staged SHA-256: rules
  `eb6b83fe9554a0b9aaad52caa7012bc57e4e3f59aa40e45baedc9fb29d8ea3cf`;
  publication
  `f18996a7034ac5d84844912d53c38f80bc688e3ba18162058407f5cc339ee606`.
  Design: VD-0002 and VD-0003, both nonessential further coverage.
  Deferred: their designed cases plus one cumulative
  `tools/run_checks.py --stage test` and normal mandatory
  CI/release gates against the reviewed state. Outcome: awaiting
  design and broader verification; publication integrity
  immediately validated.

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
