# Deferred validation queue

**Project domain:** Project infrastructure

This file is the single active register for **genuinely deferred test work**
under the [development workflow](testing.md#phased-development-and-validation).
It does not require a VD/VR item for every edit. `docs/TODO.md` owns
implementation, `docs/ci.md` hosted CI, and `docs/releasing.md` release gates.
Retain stable IDs for unresolved obligations; avoid duplicated task descriptions.

## Queue rules

The default is to **design, run and review focused tests with the implementation**.
Do not create VD/VR entries for checks already executed and accepted, nor for
hypothetical tests that do not have a concrete acceptance need.

- **Queue only genuinely deferred work.** Create a VD entry when a specific
  required test cannot yet be designed or implemented; create a VR entry when
  a concrete check must run later because its required host, assets, integration
  state or another prerequisite is unavailable. A VR may depend on a VD.
  Give each item an owner/task, the behavior/assertion, intended selector or
  evidence, the relevant revision/inputs, and a **trigger for resuming** it.
  Do not split a coherent test batch into an administrative item per edit.
- **Do not defer required immediate checks.** Correctness, security, schema,
  source-provenance and artifact-integrity risks require applicable focused
  verification before calling the change accepted. If such validation cannot
  run, report the change blocked, not passed. CI and release requirements remain
  under [CI](ci.md) and [releasing](releasing.md).
- **No numeric thresholds, automatic age deadline or drain-to-zero loop.**
  Review pending items when their prerequisite or named trigger is reached,
  when preparing an integration/merge/release involving their changes, or
  when deliberately scheduling a compatible test batch. Dates and ages are
  informational, not reasons to suspend unrelated development. Do not claim
  affected behavior or a release accepted while its required checks remain open.
- **VD is optional delegation, not a test-execution ban.** When a deferred test
  is implemented, it can be run immediately. If it passes the required
  verification, close VD and any linked VR together; otherwise keep the actual
  remaining VR open. Design and execution may be handled by the same agent.
- **Focused first.** Run the smallest risk-based set that covers changed
  behavior and affected cross-layer contracts. Reuse one pinned run for
  compatible outstanding checks; expand to a full suite only for a separately
  justified cumulative, CI or release gate. Verify final outcomes, relevant
  skips, source/asset coverage and revision; dispatch alone is not acceptance.
- **Independent work may continue during any isolated test job.** A focused,
  browser, partial or full Linux run can execute against a pinned, independent
  checkout while unrelated Windows development continues. Do not edit the
  test checkout, shared inputs or artifacts during its run, move its Git HEAD,
  or treat its result as verification of newer edits. Git handoff stays explicit,
  safe and revision-pinned; see [testing](testing.md#parallel-windows-development-and-linux-validation).
  Jobs sharing one mutable checkout cannot be presumed isolated.
- **Retirement and reporting.** Retire a VD when its design is complete and
  its remaining execution is either verified or recorded as VR; retire VR only
  with successful evidence on the intended state. Keep failures and blockers
  visible, with their next action. Update task status and report queue entries
  only when relevant; completed entries belong to Git history, not a second
  diary. Do not carry a locally completed VR merely to await hosted CI.
- **Existing IDs remain valid.** Use the next unused `VD-NNNN` and
  `VR-NNNN` for deferred obligations; never reuse historical IDs. The two
  sections below remain machine-readable by `tools.dev_status`. Record a
  concrete trigger in the entry; status counters no longer define due work.

## Pending test design

A VD entry records its ID/date/status (`needs-design` or `blocked`),
owner, missing assertion, reason/trigger for deferral, relevant revision,
and any linked VR. Design and focused execution may happen in one pass;
close the VD when its test is designed, retaining only actual outstanding
execution in VR.

No pending design entries.

## Pending deferred execution

A VR entry records its ID/date/status (`awaiting-design`,
`ready-to-run` or `blocked`), owning change/revision, concrete deferred
selectors or required evidence, missing prerequisite, execution trigger,
and final outcome. Retire only after verification of the intended state.
Failed, skipped or incomplete checks remain open.

No pending execution entries.

## Next unused IDs

- Design: `VD-0118`; active obligations are listed above.
- Execution: `VR-0148`; active obligations are listed above.

Increment the relevant next-unused ID when adding a task, even if that
task is later removed. Previous completed records remain in Git history.
The 2026-11-02 cumulative local suite evidence is summarized in
[testing.md](testing.md#controlled-chromium-concurrency-and-browser-reuse-benchmark);
mandatory CI and final release acceptance remain separate.

## Recording template

Copy only the relevant entry and use its next unused ID. Completed checks
need no entry. Specify a concrete reason and trigger for deferral.

```text
- [ ] VD-NNNN (YYYY-MM-DD; needs-design): <missing assertion>.
  Work: <task/link>; revision: <commit/artifact>; linked VR: <ID or none>.
  Blocker: <why not designed now>; trigger: <event/prerequisite>.

- [ ] VR-NNNN (YYYY-MM-DD; ready-to-run): <required check>.
  Work: <task/link>; revision: <commit/artifact>; design: <VD or none>.
  Deferred: <selector/command and required evidence>.
  Blocker: <why not run now>; trigger: <event/prerequisite>.
  Outcome: <tested revision, results and coverage when complete>.
```
