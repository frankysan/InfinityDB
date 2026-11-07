---
name: infinity-source-reconciliation
description: "Use when reviewing Infinity or Army rules sources, reconciling conflicting N5/N5.3 evidence, curating a rules interaction, or checking an official update. Preserve exact source identity, scope, citations, and uncertainty."
---

# Infinity source reconciliation

**Project domain:** Data processing

## When to use

- Review a rules, FAQ/errata, Army, or Wiki discrepancy.
- Curate or revise a source-backed rules explanation, interaction, or reference.
- Assess what an official update changes and which maintained records it affects.

Do not use this workflow as a substitute for implementing a database pipeline or browser feature;
hand those parts to the appropriate workflow after the source semantics are clear.

## Procedure

1. For autonomous "next task" work, apply the
   [V1S selection checkpoint](../../../docs/TODO.md#v1s-work-selection-and-handoff)
   before choosing a convenient source family: check earlier open tasks,
   record justified blockers/priority exceptions and report what was bypassed.
   Then identify the exact question, game edition, source scope and affected
   InfinityDB identity. Distinguish an Army profile/mode from a parent weapon
   or similarly named record.
2. Establish the applicable pinned sources before interpreting them. Keep source version,
   publication date, acquisition identity, and archived member/revision distinct. For N5, follow
   the reconciliation order and source-history policy in
   [N5 source history](../../../docs/n5-source-history.md#cross-source-reconciliation-procedure).
3. Prefer the applicable versioned official publication, FAQ/errata, and pinned Army source.
   Consult the exact Wiki revision and historical evidence where required. Treat dated official
   update posts as supplementary evidence; do not let a blog post replace a versioned rules PDF,
   FAQ, or Army data.
4. Record evidence at the granularity needed to reproduce the conclusion: printed PDF page,
   exact Wiki revision or archived member, source identity, and the relevant official update URL
   and date. Do not bulk-extract or reproduce copyrighted text or artwork.
5. Compare claims without silently resolving conflicts. Classify what is directly stated,
   source-derived, curated interpretation, or still unknown. Keep core rules, FAQ/errata,
   season-specific material, and historical evidence separate; preserve exceptions and exact
   applicability.
6. Before editing maintained prose, follow the semantic-token and explanation contracts in
   [curated-data guidance](../../../data/curated/README.md) and
   [rules semantics](../../../docs/rules-semantics.md). Explain conditions, the baseline mechanic,
   modifying rule, exceptions, outcome, and source certainty. Use an explicit review-needed marker
   when identity or meaning is genuinely ambiguous.
7. Report the supported conclusion, unresolved conflicts, source citations, and essential
   focused validation. Do not turn a reviewed descriptive fact into an executable game mechanic
   or infer legality from a source relationship.
8. Check the [canonical VD/VR queue](../../../docs/validation-queue.md#queue-rules)
   at entry and closeout. For a changed maintained source or regression
   contract, register missing assertions as VD and deferred source-audit or
   cumulative execution as VR; pure read-only review needs no artificial
   queue entry. Author tests only in VD without running them, and execute
   due VR work through the [pinned Linux protocol](../../../docs/testing.md#parallel-windows-development-and-linux-validation).
   Before moving to the next source, reconcile the reviewed V1S entry:
   retire a fully evidenced review or keep its unresolved action/authority
   open. Completing source review does not resolve an unknown upstream effect.

## References

- [N5 source history](../../../docs/n5-source-history.md)
- [Rules research](../../../docs/rules-research.md)
- [Rules semantics](../../../docs/rules-semantics.md)
- [Data model](../../../docs/data-model.md)
- [Curated data contracts](../../../data/curated/README.md)
