---
name: infinity-browser-acceptance
description: "Use for InfinityDB browser UI changes involving layout, responsive behavior, accessibility, navigation, filtering, themes, or interaction, and when diagnosing flaky or incomplete browser acceptance."
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
3. Find and extend the existing test harness or verifier. Reuse the project fixtures and browser
   transport; keep API/DOM assertions and real page/module behavior. Avoid a parallel custom test
   framework or a browser-only implementation of backend-owned semantics.
4. Run targeted automated tests first using the command and test selectors in
   [development checks](../../../docs/testing.md). When diagnosing failure, preserve the first
   useful HTTP, JavaScript, console, page-status, or screenshot evidence. Do not silently retry a
   failed page or weaken an assertion to hide nondeterminism.
5. Verify the exact requirement in the browser where visual or interaction evidence matters.
   Exercise the affected paths at the planned viewports and themes; compare rendered content with
   API/data assertions when the page presents backend data. Add manual acceptance only for concerns
   automation cannot establish.
6. Run the relevant broader browser/check slice if the shared harness or concurrency behavior
   changed. Report which viewports, interactions, and check stages were actually verified, and
   distinguish automation from manual review.

## References

- [Web design guidelines](../../../docs/web-design-guidelines.md)
- [Development checks](../../../docs/testing.md)
- [Application domains](../../../docs/application-domains.md)
- [Project domains](../../../docs/project-domains.md)
