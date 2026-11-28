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

For exploratory visual and interaction work, use the connected
[MCP browser workflow](../infinity-mcp-workspace/SKILL.md#interactive-browser-investigation)
when its origin policy permits. Inspect actual UI state, styles and screenshots,
then use the tracked browser harness for reproducible regression coverage.

## Procedure

1. Read [web design guidelines](../../../docs/web-design-guidelines.md) before changing browser
   visuals, layout, responsive behavior, interaction, or player-facing copy. Inspect the existing
   page and shared components to preserve established patterns.
2. State the observable behavior and acceptance conditions. Include relevant states, navigation
   paths, content lengths, input/error states, and representative narrow and wide viewports.
   Consider keyboard use, focus, semantic markup, contrast, and touch behavior where applicable.
3. Implement missing assertions and reusable fixtures alongside the UI
   change, then run the relevant focused browser tests on the available
   authorized host. Reuse the browser harness; keep backend-owned semantics
   separate from DOM checks.
4. Use the [deferred-validation queue](../../../docs/validation-queue.md#queue-rules)
   only when a concrete required check cannot yet be designed or executed.
   Record the missing selector, viewport/theme coverage, revision, prerequisites
   and resumption trigger; there is no mandatory separate design phase.
5. When a pinned Linux job is useful, follow the
   [Linux validation protocol](../../../docs/testing.md#parallel-windows-development-and-linux-validation).
   Independent Windows work can continue during a focused **or** full run
   only when the worker checkout and mutable inputs are isolated.
6. Report viewports, interactions, actual results, relevant skips and any
   genuinely deferred acceptance. Focused UI tests are not the final release gate.

## References

- [Web design guidelines](../../../docs/web-design-guidelines.md)
- [Browser acceptance](../../../docs/testing-browser.md)
- [Development checks](../../../docs/testing.md)
- [Application domains](../../../docs/application-domains.md)
- [Project domains](../../../docs/project-domains.md)
