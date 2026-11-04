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
6. Register concrete boundary tests (source/config, deterministic export,
   API, resolver, browser, parity and failure cases) as VD. **Create/edit
   them during the VD drain but do not execute any tests then**. Existing
   reruns and newly designed tests execute during VR.
7. For browser-facing changes, follow [browser acceptance](../infinity-browser-acceptance/SKILL.md).
   Honor the [strict VD/VR drain loop](../../../docs/validation-queue.md#queue-rules)
   before ordinary implementation. Immediate tests are exceptional and
   require a named safety-critical reason; inspect the diff for missing
   documentation owners and changed behavior.
8. **Before implementation and at closeout**, inspect the
   [active validation queue](../../../docs/validation-queue.md). Register missing
   additional test design as VD and deferred integration/browser/module/full-suite
   execution for this change as VR, with exact selectors and target revision.
   Do not treat targeted green tests as completion of broader verification.
   Batch due VR items on the pinned asynchronous Linux worker when prepared,
   following the [Windows/Linux handoff](../../../docs/testing.md#parallel-windows-development-and-linux-validation).
   When due, perform the separately invoked safe Git handoff steps
   agentically and pin the worker revision. Independent Windows
   implementation may continue **only while a full Linux suite is
   actually running**; focused/partial jobs do not suspend the VR
   drain. Do not force Git changes or hide skipped coverage;
   retire only verified entries. Before selecting another slice, reconcile
   the worked V1S and parent: retire fully verified work in the same
   closeout change, otherwise retain a concrete open action.

## References

- [Architecture](../../../docs/architecture.md)
- [Data model](../../../docs/data-model.md)
- [Application domains](../../../docs/application-domains.md)
- [Project domains](../../../docs/project-domains.md)
- [Development checks](../../../docs/testing.md)
