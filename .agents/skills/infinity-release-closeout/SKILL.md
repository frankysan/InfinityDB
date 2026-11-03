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
3. Add an Unreleased changelog entry only for a meaningful user/operator-visible outcome. Write
   from the user's or operator's perspective, consolidate related outcomes, and keep implementation
   details in code/tests/history. If the change is internal-only and warrants no entry, state that
   decision in the handoff rather than adding noise.
4. Follow [backlog completion and retirement](../../../docs/README.md#backlog-completion-and-retirement):
   check the entire subtree, required validation and documentation handoff before completion.
   Reopen affected tasks and checked ancestors before corrections or added subtasks;
   create a separate open task for genuinely new scope. After documenting the practical outcome,
   remove completed tasks/subtrees or reduce a completed child of an open parent to brief linked
   context. Rewrite the parent around remaining work; preserve dependencies and unrelated proposals.
   Apply exact project-domain labels to new or materially revised entries.
5. Update `README.md` for user-visible behavior, setup, or major capabilities. Update architecture,
   data-model, AI context, or TODO only when the change affects the responsibilities those documents
   own. Check current schema/compatibility values and rebuild guidance together when either changes.
6. Inspect [the active validation queue](../../../docs/validation-queue.md)
   before and after closeout. Confirm each implementation change has its
   essential checks recorded and concrete missing test designs (VD) or
   deferred broader executions (VR) registered, with selectors, evidence
   requirements and exact commit. A green focused suite is not a reason to
   omit a full-suite or cross-platform obligation still due. Check the
   five-item/seven-day triggers and [pinned asynchronous Linux dispatch](../../../docs/testing.md#parallel-windows-development-and-linux-validation).
   Retire only entries with terminal passing evidence for the intended state;
   allow independent Windows implementation while Linux jobs execute.
7. Run the smallest necessary documentation and immediate code checks from
   [phased development checks](../../../docs/testing.md#phased-development-and-validation).
   Reuse verified focused results rather than repeating entire modules.
8. For an actual release, resolve applicable queued obligations and every
   gate in `docs/releasing.md`, including its project-wide maintained-
   documentation audit. Queue retirement never substitutes for CI.
9. Inspect the final diff and Git status. Preserve unrelated changes; do
   not stage, commit, push, deploy, tag, or publish without authorization.
   Report the queue counts, deferred gates and precise validation status.

## References

- [Documentation map](../../../docs/README.md)
- [Project domains](../../../docs/project-domains.md)
- [Backlog](../../../docs/TODO.md)
- [Changelog](../../../docs/CHANGELOG.md)
- [Release checklist](../../../docs/releasing.md)
- [Development checks](../../../docs/testing.md)
