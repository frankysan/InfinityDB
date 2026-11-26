# Agent improvement log

**Project domain:** Project infrastructure

This is a short **inbox of unresolved, actionable improvements**, not an
implementation history or a second backlog. Git history preserves retired
entries.

1. Before adding an entry, check for an existing owner in the current
   documentation and [TODO.md](TODO.md). Do not duplicate tracked work.
2. Record only a concrete next action, affected area, supporting evidence, and
   its disposition (`proposed` or `deferred`). Keep uncertain findings explicit.
3. Once implemented, declined, or superseded, **delete the entry in the same
   commit**. When accepted work is transferred to TODO, remove the entry
   after preserving its actionable scope there. Transfer lasting decisions to
   the canonical documentation owner, not an archive of completed log entries.
4. Mention new unresolved items during handoff. Never reuse an assigned ID:
   increment the next-ID marker when creating a new entry.

**Next ID:** `AI-0024`

## Open improvements

### AI-0023 — Separate presentation-only sources from database build freshness

- **Date:** 2026-11-26
- **Area:** Runtime build provenance and theme iteration.
- **Issue:** Palette and scenario SVG rendering changes outside the web package
  invalidate the conservative Python input envelope. A palette-only change
  required a complete history-enabled rebuild (289 seconds on Windows).
- **Proposed:** Audit actual build dependencies and move or explicitly exclude
  presentation-only sources from the build envelope while retaining static
  asset revision coverage and tests for genuine data-input changes.
- **Disposition:** proposed.

### AI-0015 — Publish ITS 18 Use Panoply as a typed scenario Skill

- **Date:** 2026-11-18
- **Area:** ITS 18 Corporate Appropriation Skill presentation.
- **Remaining issue:** ITS 18 still presents Use Panoply in Panoplies prose,
  though the source identifies it as an Attack, Scenario Short Skill. ITS 17
  already has a reviewed typed equivalent.
- **Proposed:** Review and publish an ITS 18 typed Skill without changing its
  behavior; assess cross-season reuse only after fact-level comparison.
- **Disposition:** deferred.
