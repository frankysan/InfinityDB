---
name: infinity-browser-acceptance
description: "Use for InfinityDB browser UI changes involving player-facing copy, layout, responsive behavior, accessibility, navigation, filtering, themes, or interaction, and when diagnosing flaky or incomplete browser acceptance."
---

# InfinityDB browser acceptance

**Project domain:** Web frontend

## When to use

- Change player-facing browser layout, copy, responsive behavior, accessibility, or interaction.
- Add or change a page, browser state, filter, navigation path, theme behavior, or reference card.
- Diagnose browser test timeouts, rendering failures, or inconsistent UI/API behavior.

If the requested feature also changes source semantics, stored data, or API behavior, pair this
workflow with [reference vertical slice](../infinity-reference-vertical-slice/SKILL.md); do not
make frontend acceptance a substitute for backend or data validation.

## Procedure

1. Read [web design guidelines](../../../docs/web-design-guidelines.md) before changing browser
   visuals, layout, responsive behavior, interaction, or player-facing copy. Inspect the existing
   page and shared components to preserve established patterns.
2. State the observable behavior and acceptance conditions. Include relevant states, navigation
   paths, content lengths, input/error states, and representative narrow and wide viewports.
   Consider keyboard use, focus, semantic markup, contrast, and touch behavior where applicable.
3. Specify missing browser assertions and reusable fixtures as VD; only
   author/review them in the dedicated design phase **without running tests**.
   Existing-test reruns and designed tests execute under VR. Reuse the
   browser harness and keep backend-owned semantics separate from DOM checks.
4. Follow the [canonical queue scheduling and retirement rules](../../../docs/validation-queue.md#queue-rules)
   at task start and closeout. Record selectors, viewport/theme coverage,
   browser prerequisites, tested revision and required asset/source evidence.
   Immediate browser checks require a documented correctness-critical reason.
5. During due VR work, follow the [pinned Linux test handoff](../../../docs/testing.md#parallel-windows-development-and-linux-validation),
   including explicit safe Git preparation and skip review. A Linux full-suite
   run in progress uniquely permits independent Windows development; a
   focused or partial job does not.
6. Report actual viewports, interactions, check stages, immediate results,
   and outstanding VR acceptance. Do not conflate focused UI tests with the
   final release browser gate.

## References

- [Web design guidelines](../../../docs/web-design-guidelines.md)
- [Development checks](../../../docs/testing.md)
- [Application domains](../../../docs/application-domains.md)
- [Project domains](../../../docs/project-domains.md)
