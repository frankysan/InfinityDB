# V1S backlog checker — implementation plan

**Project domain:** Project infrastructure  
**Status:** Phase 1 is implemented and verified on Windows and pinned Linux.
The Linux CLI passed with 53 declarations and zero warnings; its tests passed
in the cumulative code profile at `1d0d5c19`, recorded in
[testing.md](testing.md#parallel-windows-development-and-linux-validation).
Phases 2–4 remain proposed under V1S-096.
**Scope:** The active `V1S-*` execution slices in [TODO.md](TODO.md#pre-planned-10-execution-slices), their documented completion, and the Git history of removals.

## Goal and constraints

Build a lightweight, read-only checker that reduces silent task skipping and unaccounted completion. It should validate objective backlog structure, make task retirement traceable, and explain why a proposed V1S selection bypasses earlier actionable work.

The checker **must not infer semantic completion** from a passing test, a removed checkbox, a source citation, or the presence of a Git commit. Implementation completeness still depends on the owning task, the [backlog retirement contract](README.md#backlog-completion-and-retirement), [VD/VR queue](validation-queue.md#queue-rules), canonical acceptance evidence, and release gates.

Design constraints:

- Reuse `docs/TODO.md` as the sole active implementation backlog. Do not create another status register or completed-task ledger.
- Preserve retired V1S gaps; missing numbers alone are not errors.
- Remain read-only, deterministic, offline, cross-platform, and usable without ignored local data.
- Prefer Python standard-library parsing, subprocess Git operations with bounded output, and the existing `tools/run_checks.py` integration.
- Distinguish **objective violations** from **advisory heuristics**. Avoid claiming to verify task meaning, upstream authority, or actual test coverage.
- Preserve the existing [selection checkpoint](TODO.md#v1s-work-selection-and-handoff) and the current [VD/VR scheduling contract](validation-queue.md#queue-rules); this plan does not set queue thresholds.

## Proposed architecture

A single module, `tools/check_v1_backlog.py`, with three independent modes:

| Mode | Inputs | Outcome |
| --- | --- | --- |
| Static | Current `docs/TODO.md` | Structural diagnostics; no Git required |
| Closeout | Base revision and target worktree/commit | Removed-ID reconciliation and evidence diagnostics |
| Selection | Proposed V1S ID, active TODO, optional documented override | Earlier-open-task inventory and selection decision |

Emit concise console diagnostics with stable rule codes, file/line references when possible, severity, and suggested correction. Support optional machine-readable JSON for agent/MCP consumers. Use exit code 0 for no hard errors, nonzero for hard failures, and reserve warnings for review rather than treating them as success evidence.

### Parser and scope

- Recognize task **declarations**, not incidental `V1S-123` references in prose, source reviews, commit messages, or links.
- Parse Markdown checkbox indentation and parent-child relationships without assuming every parent is a numbered V1S item.
- Scope IDs to the designated pre-planned 1.0 execution-slice section; do not interpret arbitrary V1S mentions elsewhere as active tasks.
- Retain each declaration's ID, checkbox status, line range, parent hierarchy, section, descriptive text, and optional `Blocked:` / `Deferred:` annotations.
- Be conservative about ambiguous Markdown: report an explicit parse diagnostic rather than silently dropping a task.

## Validation rules

| Rule | Intended behavior | Initial severity |
| --- | --- | --- |
| Duplicate V1S declarations | An active V1S ID may be declared only once | Error |
| Malformed V1S declarations | Detect malformed IDs or invalid task declarations in scope | Error |
| Invalid parent/descendant state | Reject checked parents containing unchecked descendants; respect actual indentation and nesting | Error |
| Unsupported retirement | A removed ID must have a traceable closeout in the relevant commit(s), with identifiable acceptance evidence | Error once baseline is adopted |
| Incomplete blocker/deferment | Explicit `Blocked:` / `Deferred:` entries require a reason, owner or authority, and revisit condition | Warning initially |
| Possible stale task | Flag likely completed descriptions or contradictory status text without automatically retiring them | Advisory |
| Unexplained bypass | A selected task passes earlier actionable IDs without a documented exception | Error in explicit selection mode |

A task is not necessarily blocked because its source semantics remain uncertain: if further bounded investigation is possible, it remains actionable. Ordering is the default review priority, **not** a fabricated dependency between unrelated workstreams.

### Retirement verification

For `--base`, compare declarations from the specified base and target state, then:

1. List IDs removed, added, or changed. Never infer completion merely from a numeric gap.
2. Attribute removals to the commit(s) introducing them, including when the comparison spans multiple commits.
3. Require each retired ID to be mentioned in the responsible commit subject/body, accepting the existing case-insensitive `V1S-123` convention. Recommend a future structured trailer such as `V1S-Closed: V1S-055, V1S-056` without breaking historical commits.
4. Require an acceptance-evidence reference (canonical document, exact verified selector/revision, or documented source-reviewed no-change). Validate reference syntax and identifiable paths where possible, but report semantic adequacy as requiring review.
5. Identify entries accidentally removed or moved outside the register. Do not treat relocation, renumbering, or an explicitly documented scope change as automatically accepted retirement.
6. Distinguish baseline/history unavailable from “clean”; report a clear setup error if the required Git revision or ancestry is missing.

Ensure commit-level comparisons work for ordinary fast-forward development. Specify merge-commit handling explicitly before enforcing the rule in CI; never silently attribute removal to an unrelated later commit.

### Selection verification

Given `--select V1S-NNN`:

1. Confirm that the selected ID is declared and open.
2. Enumerate **all earlier open IDs across workstreams**, not only the current subsection.
3. Classify explicitly annotated blockers/deferments and surface unannotated earlier tasks as actionable candidates for human/agent review.
4. Reject unexplained bypasses. Allow an explicit override with a concrete priority reason, while requiring durable acknowledgement in the appropriate TODO entry or task handoff.
5. Print the earliest actionable candidate and the IDs/ranges intentionally passed over.

This is an invoked **pre-task gate**, not a static CI inference about an agent's intended next action.

## Implementation phases

### Phase 1 — Static backlog integrity

- Implement the scoped parser, source-position diagnostics and static checks.
- Add `tests/test_check_v1_backlog.py` fixtures for duplicate declarations, malformed IDs, valid retirement gaps, nested checkboxes, contradictory parent states and prose references that must not count as declarations.
- Run against the current backlog in **advisory/baseline mode** first; correct legitimate malformed entries without inventing task dispositions.
- Keep the default command independent of a Git checkout.

**Acceptance:** current TODO can be parsed without silently discarded tasks; objective-invalid fixtures fail deterministically on Windows and Linux.

### Phase 2 — Git-aware completion verification

- Implement `--base` / target-state comparison, per-commit attribution and closeout evidence diagnostics.
- Cover valid closeout, missing retired-ID reference, historical naming variations, multiple IDs in one commit, no-op/reorder, missing base and diverged history.
- Keep evidence-presence checks separate from semantic acceptance.
- Initially report historical violations as advisory; turn blocking enforcement on only for newly introduced retirements after a documented baseline.

**Acceptance:** unaccounted removals fail when enforcing, while valid historical retirements and intentional ID gaps pass.

### Phase 3 — Task-selection enforcement

- Implement explicit selection mode, earlier-ID enumeration, blocker/deferment parsing and documented priority overrides.
- Test `V1S-062`-like selection with earlier actionable `V1S-034`–`V1S-052` entries, fully documented blockers, user-priority overrides, and nonexistent/closed IDs.
- Do not infer “blocked” from task age or from a source ambiguity alone.

**Acceptance:** an unexplained skip yields actionable diagnostics; legitimate documented exceptions preserve the earlier tasks in the active backlog.

### Phase 4 — Integration and rollout

- Integrate static checking into the normal documentation-check stage; add a Git-aware CI check with a reliable base revision and sufficient Git history.
- In agent instructions and relevant skills, require explicit selection-mode invocation before autonomous next-task implementation and closeout-mode invocation before task-retirement commits.
- Support concise console and optional JSON output suitable for MCP job reporting.
- Maintain the [VD/VR separation](validation-queue.md): checker implementation test designs and executions follow the existing queue, not a new testing process.
- Document the new commands and baseline policy in the canonical [testing guide](testing.md). Remove this plan once implemented, transferring any lasting contract to the canonical owner.

**Acceptance:** new violations fail objective checks locally and in CI; existing historical cleanup is not misrepresented as successful validation; no network or ignored local files are required.

## Available Phase 1 CLI

From the repository root using PowerShell:

```powershell
.\.venv\Scripts\python.exe -m tools.check_v1_backlog
.\.venv\Scripts\python.exe -m tools.check_v1_backlog --todo docs/TODO.md
```

The Phase 1 command checks only static structure and does not require Git.
Git-aware `--base` closeout and `--select` modes remain unimplemented; their
interfaces and baseline/override semantics must be finalized before they are
documented as available commands.

Example diagnostic:

```text
V1S selection: V1S-062
Earlier open tasks: V1S-034–V1S-052 (review each disposition)
FAIL: selection bypasses earlier actionable work.
Suggested next task: V1S-034
Record a qualifying blocker/deferment or explicit priority override.
```

## Non-goals

- Automatically completing, moving, checking, or deleting TODO entries.
- Treating checkmarks as implementation-progress percentages.
- Replacing source reconciliations, actual regression tests, browser acceptance, CI checks or release gates.
- Creating a task-status database, second historical diary, or new permanent report format.
- Auto-synchronizing Windows/Linux Git checkouts.
- Blocking ordinary CI because a later-numbered task exists; selection checks are meaningful only when a task is actually selected.

## Overall completion criteria

The checker is ready when the current backlog passes static validation; negative tests catch structural and retirement violations; selection mode explains unjustified skips; valid overrides are traceable; errors and warnings are clearly separated; Windows and Linux behavior matches; and the project can run it offline through the established checks.

**Current decision:** The user authorized implementation of this plan. Phase 1
is the current scope; Git-aware closeout, selection enforcement, check-runner/CI
integration and rollout remain unimplemented.
