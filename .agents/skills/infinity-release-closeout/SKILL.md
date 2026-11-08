---
name: infinity-release-closeout
description: "Use when closing out a substantial InfinityDB change, reconciling implementation status with the backlog/changelog, preparing release documentation, or performing release-readiness work."
---

# InfinityDB release and documentation closeout

**Project domain:** Project infrastructure

## When to use

- Finish a substantial feature or fix and determine which maintained documentation needs updating.
- Reconcile a completed or deferred work item with the current backlog and Unreleased notes.
- Prepare or review an actual release or release candidate.

Routine implementation and validation should use the relevant feature workflow; this skill owns
closeout and release readiness, not the feature itself.

## Procedure

1. Read the [documentation map](../../../docs/README.md),
   [project-domain rules](../../../docs/project-domains.md),
   [backlog](../../../docs/TODO.md), and [changelog](../../../docs/CHANGELOG.md). For an actual
   release, also follow the complete mandatory [release checklist](../../../docs/releasing.md).
2. Inspect the actual diff and current state. Identify the canonical current-behavior/design owner
   for each durable outcome; update that owner rather than duplicating contracts across documents.
3. Add a changelog entry under the [pending target release](../../../docs/releasing.md#between-releases)
   only for a meaningful user/operator-visible outcome. Write
   from the user's or operator's perspective, consolidate related outcomes, and keep implementation
   details in code/tests/history. If the change is internal-only and warrants no entry, state that
   decision in the handoff rather than adding noise.
4. Follow [backlog completion and retirement](../../../docs/README.md#backlog-completion-and-retirement)
   and the [V1S selection and handoff gate](../../../docs/TODO.md#v1s-work-selection-and-handoff).
   Reconcile the *previously selected* task and entire parent subtree against the
   actual acceptance, remaining dependencies and VD/VR status **before moving on**.
   Reopen affected tasks and checked ancestors before corrections or added subtasks;
   create a separate open task for genuinely new scope. After documenting the practical outcome,
   remove completed tasks/subtrees in the same commit or reduce a completed child of an open parent
   to brief linked context. Record all retired V1S IDs in that Git commit's subject/body.
   If incomplete, rewrite the open task around an actionable remainder or an explicit
   blocker and retry trigger; do not leave stale "finish validation" text.
   Preserve dependencies and unrelated proposals. Apply exact project-domain labels
   to new or materially revised entries.
5. Update `README.md` for user-visible behavior, setup, or major capabilities. Update architecture,
   data-model, AI context, or TODO only when the change affects the responsibilities those documents
   own. Check current schema/compatibility values and rebuild guidance together when either changes.
6. Inspect the [active VD/VR queue](../../../docs/validation-queue.md#queue-rules)
   before and after closeout. Register any concrete missing test design and
   each change's deferred execution with selectors, source/asset coverage and
   exact revision. Apply the canonical scheduling, prerequisite-design and
   retirement rules rather than maintaining another threshold description.
   Never infer broader or hosted acceptance from focused test success.
7. Run the smallest necessary documentation and immediate code checks from
   [phased development checks](../../../docs/testing.md#phased-development-and-validation).
   Reuse verified focused results rather than repeating entire modules.
8. For an actual release, resolve applicable queued obligations and every
   gate in `docs/releasing.md`, including its project-wide maintained-
   documentation audit. Queue retirement never substitutes for CI.
9. After an authorized push, record the exact SHA and available
   workflow runs under [non-blocking agent CI monitoring and repair](../../../docs/ci.md#agent-ci-monitoring-and-repair).
   Continue independent development rather than waiting for CI after
   every commit; revisit outstanding runs at meaningful task
   boundaries. Triage and autonomously fix actionable repository
   failures under the standing development authorization. Only
   require all relevant workflows and dependent jobs to finish
   successfully for a release/merge or other mandatory acceptance
   gate. Distinguish pending/untriggered/skipped CI from success.
10. Inspect the final diff and Git status, including removals/rewrites in
    `docs/TODO.md`. Verify every retired V1S has real completion evidence,
    every incomplete task remains open, and lower-ID tasks passed over have
    an explicit reason. Preserve unrelated changes; do not stage, commit,
    push, deploy, tag, or publish without authorization. Report the selected/
    retired/still-open V1S IDs, queue counts, deferred gates and exact results.

## References

- [Documentation map](../../../docs/README.md)
- [Project domains](../../../docs/project-domains.md)
- [Backlog](../../../docs/TODO.md)
- [Changelog](../../../docs/CHANGELOG.md)
- [Release checklist](../../../docs/releasing.md)
- [Development checks](../../../docs/testing.md)
