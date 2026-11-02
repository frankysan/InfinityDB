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
3. Find and extend the existing test harness or verifier. Reuse the project fixtures and browser
   transport; keep API/DOM assertions and real page/module behavior. Avoid a parallel custom test
   framework or a browser-only implementation of backend-owned semantics.
4. Run essential targeted tests first under the
   [phased validation workflow](../../../docs/testing.md#phased-development-and-validation).
   When diagnosing failure, preserve the first useful HTTP, JavaScript, console,
   page-status, or screenshot evidence. Do not silently retry a failed page or
   weaken assertions to hide nondeterminism.
5. Verify the exact requirement in the browser where risk-critical visual
   or interaction evidence cannot safely be deferred. Exercise the affected
   paths at the necessary viewports and themes and compare rendered content
   with API/data assertions. Additional viewport/theme/cross-browser matrices
   should be specified as VD/VR obligations rather than run indiscriminately.
6. Check [the validation queue](../../../docs/validation-queue.md) at start
   and closeout. Queue additional assertions as VD and deferred broader
   browser/module/full-suite execution for the change as VR. Record
   browser prerequisites, exact selectors and intended commit. Prefer a
   [pinned asynchronous Linux worker](../../../docs/testing.md#parallel-windows-development-and-linux-validation)
   for broader real-Chromium runs when installed browser dependencies and
   source inputs are verified; unexpected skips do not satisfy acceptance.
   For a due VR batch, safely fetch/fast-forward the intended committed
   revision on the MCP worker using the authorized explicit Git tools,
   dispatch the pinned test job, then immediately resume independent
   Windows implementation. Do not wait or repeatedly poll.
7. Report actual viewports, interactions, check stages, immediate results,
   and outstanding VR acceptance. Do not conflate focused UI tests with the
   final release browser gate.

## References

- [Web design guidelines](../../../docs/web-design-guidelines.md)
- [Development checks](../../../docs/testing.md)
- [Application domains](../../../docs/application-domains.md)
- [Project domains](../../../docs/project-domains.md)
