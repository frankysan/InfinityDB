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

1. Find relevant canonical documentation using the
   [documentation map](../../../docs/README.md).
   Consult [project-domain rules](../../../docs/project-domains.md),
   [backlog](../../../docs/TODO.md) and [changelog](../../../docs/CHANGELOG.md)
   only where the task affects those owners. An actual release must follow
   the [release checklist](../../../docs/releasing.md).
2. Inspect the actual diff and current state. Identify the canonical current-behavior/design owner
   for each durable outcome; update that owner rather than duplicating contracts across documents.
3. Add a changelog entry under the [pending target release](../../../docs/releasing.md#between-releases)
   only for a meaningful user/operator-visible outcome. Write
   from the user's or operator's perspective, consolidate related outcomes, and keep implementation
   details in code/tests/history. If the change is internal-only and warrants no entry, state that
   decision in the handoff rather than adding noise.
4. When completing or modifying a **tracked backlog task**, apply
   [backlog completion and retirement](../../../docs/README.md#backlog-completion-and-retirement)
   to the affected task and parent. Remove fully completed work in the same
   commit; leave a concrete, actionable remainder when blocked. Use the
   historical [V1S selection gate](../../../docs/TODO.md#v1s-work-selection-and-handoff)
   only if a numbered V1S task is explicitly reopened; list retired V1S IDs
   in that commit. Unrelated small work does not require V1S bookkeeping.
5. Update `README.md` for user-visible behavior, setup, or major capabilities. Update architecture,
   data-model, AI context, or TODO only when the change affects the responsibilities those documents
   own. Check current schema/compatibility values and rebuild guidance together when either changes.
6. Consult the [deferred-validation queue](../../../docs/validation-queue.md#queue-rules)
   only if a specific required check remains blocked or unrun. Record the
   revision/inputs, selector, owning change and resumption trigger. Normal
   focused checks run during implementation, without separate VD/VR entries.
   Never infer broader or hosted acceptance from a focused pass.
7. Run the smallest necessary documentation and immediate code checks from
   [phased development checks](../../../docs/testing.md#phased-development-and-validation).
   Reuse verified focused results rather than repeating entire modules.
8. For an actual release, resolve applicable required deferred checks and
   follow [risk-based release acceptance](../../../docs/releasing.md),
   including review of **affected documentation**, not a blanket audit of
   all project files. Queue retirement never substitutes for hosted CI.
9. After an authorized push, record the exact SHA and available
   workflow runs under [non-blocking agent CI monitoring and repair](../../../docs/ci.md#agent-ci-monitoring-and-repair).
   Continue independent development rather than waiting for CI after
   every commit; revisit outstanding runs at meaningful task
   boundaries. Triage and autonomously fix actionable repository
   failures under the standing development authorization. Only
   require all relevant workflows and dependent jobs to finish
   successfully for a release/merge or other mandatory acceptance
   gate. Distinguish pending/untriggered/skipped CI from success.
10. Inspect the final diff and Git status. For modified backlog tasks,
    verify the corresponding acceptance and same-change closeout. Preserve
    unrelated edits and respect separate deployment/tag/release approval.
    Report changed files, actual checks, remaining blockers and exact revision;
    include V1S IDs or deferred-queue status only when relevant.

## References

- [Documentation map](../../../docs/README.md)
- [Project domains](../../../docs/project-domains.md)
- [Backlog](../../../docs/TODO.md)
- [Changelog](../../../docs/CHANGELOG.md)
- [Release checklist](../../../docs/releasing.md)
- [Development checks](../../../docs/testing.md)
