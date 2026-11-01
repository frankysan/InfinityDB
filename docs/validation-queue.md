# Phased validation queue

**Project domain:** Project infrastructure

This file is the single active register for validation work deferred under the
[phased development workflow](testing.md#phased-development-and-validation).
It tracks **test design and execution obligations**, not implementation features,
release scope, or source ambiguities. `docs/TODO.md` owns implementation work
and defects; `docs/releasing.md` owns mandatory release acceptance. Keep stable
IDs here and link the owning task instead of duplicating its description.

## Queue rules

- Record every deferred test requirement before ending an implementation pass,
  including changes that need only a later full-suite or browser run. Record
  the observed immediate checks separately; never call an unrun check passed.
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
- **Required behavior:** observable setup, action, expected result, and
  source/edge cases; identify existing tests to extend before adding new ones.
- **Priority/dependency:** risk and linked VR item.
- **Result:** test paths, targeted execution result, and date when designed.

No prospective design items recorded yet. This does **not** certify that prior
work has complete test coverage; existing release and TODO obligations remain.

## Pending deferred execution

Each item records:

- **ID / recorded date / status:** `awaiting-design`, `ready-to-run`,
  `blocked`, or `verified`.
- **Owning work and change:** one distinct implementation change, linked
  TODO section and precise revision/artifact identity.
- **Immediate evidence:** targeted test/lint/data checks already run, with
  pass/fail/skip and date.
- **Deferred checks:** executable test selector(s), sections, browser/manual
  review or broader profile, plus any blocking VD IDs.
- **Result:** executed commands, revision, pass/fail/skip and report location;
  close only after the required checks pass.

No prospective execution items recorded yet. Do not infer that earlier changes
have already passed broader validation.

## Recording template

Copy a new item into the appropriate section above; use the next unused ID.
Avoid creating an empty item for work fully verified during implementation.

```text
- [ ] VD-0001 (YYYY-MM-DD; needs-design): <required assertion/edge case>.
  Work: <TODO anchor>; change: <revision/files>; risk: <level>.
  Existing coverage: <test selector or none>; linked execution: VR-0001.
  Outcome: <test path and targeted run, when available>.

- [ ] VR-0001 (YYYY-MM-DD; awaiting-design): <one implementation change>.
  Work: <TODO anchor>; revision: <commit/artifact>; risk: <level>.
  Immediate: <command and pass/fail/skip>; design: VD-0001.
  Deferred: <exact checks/section/manual acceptance>.
  Outcome: <revision, command, counts and evidence, when run>.
```
