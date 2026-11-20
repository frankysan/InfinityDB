---
name: agent-improvements
description: "Implement one actionable improvement, or one coherent related batch, from InfinityDB's agent improvement log. Read every open item before selecting; investigate, edit, test, and retire resolved entries in the same commit."
argument-hint: "[optional AI-XXXX or focus]"
user-invocable: true
---

# Address agent improvements

**Project domain:** Project infrastructure (the selected change may belong to any project domain).

Use when asked to **work through the agent improvement log**, resolve an improvement, or select the next improvement autonomously. This is an **implementation skill**, not a log-summary or planning exercise. One invocation completes **one item or a closely related batch**, not the entire inbox.

## Invocation

- `agent-improvements` — inspect **all** open entries and choose a ready item or related batch.
- `agent-improvements AI-0014` — prioritize the named entry; still inspect every open entry for dependencies, overlaps, and a sensible batch.
- An optional topic or component narrows selection without bypassing the full-inbox review.
- Where supported, invoke as `$agent-improvements` (Codex) or `/agent-improvements` (Copilot).

## Select work from the actual inbox

1. Inspect the authorized checkout, branch, HEAD, working-tree state, `AGENTS.md` and `AGENTS.local.md` if present. Respect existing edits and assignments. Read the **entire current** [agent improvement log](../../../docs/AGENT_IMPROVEMENTS.md), including every entry under *Open improvements* and its disposition; paginate if needed. Do not select from remembered IDs, a partial excerpt, Git history, or a cached list.
2. For **every open item**, establish its remaining action, evidence, affected code/tests/docs, current disposition, and apparent prerequisites. Check for overlap with other entries, already-implemented work, and an existing canonical [TODO](../../../docs/TODO.md) or documentation owner. Read only the relevant owner docs and source/test paths needed to verify candidates; do not undertake a full-repository audit.
3. Choose **one executable item**, or **several items sharing the same component, fix, test fixture, or validation path**. Prefer the batch that meaningfully improves correctness, unblocks current work, or reduces repeated effort with a small coherent diff. Consider readiness, evidence availability, impact, dependency order, and validation cost; do not simply pick the oldest or lowest ID. Honor a user-selected ID/focus unless doing so would be unsafe or blocked.
4. Treat `deferred` as a real constraint: consider it, but do not promote it merely for convenience. Select it only if its prerequisite or reason for deferral is now resolved, or the user explicitly changes its priority. Do not conflate adjacent items that require independent semantic review. State the selected IDs and reason briefly, then **proceed with implementation**, not another proposal.
5. If the preferred item is genuinely blocked, record the specific missing source, decision, permission, tool, or validation dependency and choose the next ready candidate from the reviewed inbox. If none is executable, report the blockers and leave unresolved entries open; do not create speculative changes or mark work complete.

## Implement and close the selected batch

1. Trace the actual cause and existing implementation. Follow [documentation ownership](../../../docs/README.md), the repository's compatibility and source-provenance rules, and the relevant domain skill (for example [source reconciliation](../infinity-source-reconciliation/SKILL.md) or [browser acceptance](../infinity-browser-acceptance/SKILL.md)). For visual changes read `docs/web-design-guidelines.md`; for source-backed rules verify the required original evidence. Do not silently infer missing facts.
2. Implement the **smallest complete fix** with appropriately focused regression tests. Preserve unrelated behavior, avoid extra process or abstractions, and run the checks justified by the affected layers via [testing guidance](../../../docs/testing.md). Distinguish passed, failed, blocked, and unrun checks; use the [validation queue](../../../docs/validation-queue.md) only for a concrete blocked obligation.
3. Reconcile each worked log entry **in the same change**:
   - **Complete, declined, or superseded:** delete its entire entry; Git history is the completion record.
   - **Accepted but still outstanding in the canonical TODO:** transfer its actionable scope and evidence to [TODO.md](../../../docs/TODO.md), then delete the inbox entry.
   - **Partially implemented or still blocked:** leave it open and update its remaining issue, evidence, disposition and next action; do not claim closure.
   - Keep the `Next ID` marker monotonic; never recycle retired IDs or create a completed-items archive. Record any **new, genuinely separate** opportunities using the log's existing format and duplicate check.
4. Update the canonical current-state documentation **only if behavior or a durable decision changed**. Review the task-related Git diff and run focused checks before accepting. Follow [AGENTS.md](../../../AGENTS.md) for staging, commit, authorized push and hosted CI follow-through. No force-push, branch switch, merge, release or production deployment is authorized by this skill.
5. Report the IDs selected, why they belonged together, the files/behavior changed, the final disposition of each selected log entry, exact test/check outcomes, commit/push state, and blockers that remain. Do not present pending CI as passed.

**Stop after the coherent batch is delivered.** A later invocation reads the **whole inbox anew** and chooses its next batch from the then-current repository state.
