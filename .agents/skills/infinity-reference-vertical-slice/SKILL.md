---
name: infinity-reference-vertical-slice
description: "Use when adding or changing an InfinityDB reference capability that may span curated or source data, generated databases, backend/API responses, and browser presentation. Keep layer ownership and published semantics consistent."
---

# InfinityDB reference vertical slice

**Project domains:** Data processing, Web backend, Web frontend

## When to use

- A new or changed reference needs more than one layer, from maintained facts through a player-facing
  API or page.
- A source relationship, curated rule, or derived fact must become discoverable in the application.
- Existing data, API, and browser representations disagree about identity, scope, or provenance.

For a browser-only visual or interaction change, use
[browser acceptance](../infinity-browser-acceptance/SKILL.md) instead. For a data-only pipeline
change, use [Army data pipeline](../infinity-army-data-pipeline/SKILL.md).

## Procedure

1. For autonomous task selection, first apply the
   [V1S selection checkpoint](../../../docs/TODO.md#v1s-work-selection-and-handoff),
   not just the most recently active workstream. Disclose earlier open IDs and
   their blockers or justified priority exceptions. Then read
   [architecture](../../../docs/architecture.md),
   [data model](../../../docs/data-model.md), [application domains](../../../docs/application-domains.md),
   and [project domains](../../../docs/project-domains.md). Name the owning application domain and
   engineering layer(s); do not add layers that the requirement does not need.
2. Establish the semantic contract first: source identity and scope, provenance class, maintained
   versus generated facts, unresolved cases, and the precise user task. Use
   [source reconciliation](../infinity-source-reconciliation/SKILL.md) if evidence or meaning is
   unsettled.
3. Trace the existing path and reuse its canonical model, registry, resolver, API shape, and shared
   presentation components. Stable domain slugs are preferred in application-facing links and
   state; retain numeric compatibility through the central resolver.
4. Keep responsibilities at their boundary:
   - validated configuration and curated data own maintained policy and reviewed meaning;
   - build/export code materializes validated application data and provenance;
   - the backend queries materialized data and exposes application-shaped responses;
   - the browser renders backend-owned semantics and user interaction, not a second normalization
     or semantic-resolution layer.
5. Implement the smallest complete slice. Preserve exact source/profile/mode identity, ordering,
   scope, citations, and unknown/disputed status. Do not imply a legal roster, deployed state, or
   calculated game outcome unless the maintained contract explicitly supports it.
6. Specify concrete source/config, export, API, resolver, browser,
   parity and negative-case assertions as VD; record this change's deferred
   execution (including existing tests) as VR. Tests are authored/reviewed
   **without execution** in VD; VR owns execution and evidence.
7. For browser-facing changes, follow [browser acceptance](../infinity-browser-acceptance/SKILL.md).
   Follow the [canonical queue rules](../../../docs/validation-queue.md#queue-rules)
   before implementation and at closeout. Pin Linux runs using the
   [Windows/Linux validation protocol](../../../docs/testing.md#parallel-windows-development-and-linux-validation);
   never force Git handoff, hide skipped coverage, or treat dispatch as success.
8. Before selecting another slice, reconcile the worked V1S and parent:
   retire fully verified work in the same closeout change, otherwise retain
   a concrete remaining action or blocked dependency. Update only the
   canonical documentation owners for changed behavior.

## References

- [Architecture](../../../docs/architecture.md)
- [Data model](../../../docs/data-model.md)
- [Application domains](../../../docs/application-domains.md)
- [Project domains](../../../docs/project-domains.md)
- [Development checks](../../../docs/testing.md)
