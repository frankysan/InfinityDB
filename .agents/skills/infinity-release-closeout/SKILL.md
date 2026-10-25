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
3. Reconcile backlog status: remove or mark only work that the delivered change truly completes,
   preserve real remaining dependencies, and keep future design explicitly distinguished from
   implemented behavior. Apply exact project-domain labels to new or materially revised entries.
4. Add an Unreleased changelog entry only for a meaningful user/operator-visible outcome. Write
   from the user's or operator's perspective, consolidate related outcomes, and keep implementation
   details in code/tests/history. If the change is internal-only and warrants no entry, state that
   decision in the handoff rather than adding noise.
5. Update `README.md` for user-visible behavior, setup, or major capabilities. Update architecture,
   data-model, AI context, or TODO only when the change affects the responsibilities those documents
   own. Check current schema/compatibility values and rebuild guidance together when either changes.
6. Do not convert ideas in `local/thoughtspace.md` under **Proposed** into tasks, commitments, or
   implementation without explicit user approval. Do not rewrite, reorder, or silently edit
   thoughtspace content.
7. For an actual release, complete every applicable gate in `docs/releasing.md`, including its
   project-wide maintained-documentation audit; a recent diff review alone is not sufficient.
   Run the smallest relevant documentation and code checks from
   [development checks](../../../docs/testing.md), and record precise results.
8. Inspect the final diff and Git status. Preserve unrelated changes; do not stage, commit, push,
   deploy, tag, or publish without explicit authorization. Report any release gate or validation
   that remains incomplete.

## References

- [Documentation map](../../../docs/README.md)
- [Project domains](../../../docs/project-domains.md)
- [Backlog](../../../docs/TODO.md)
- [Changelog](../../../docs/CHANGELOG.md)
- [Release checklist](../../../docs/releasing.md)
- [Development checks](../../../docs/testing.md)
