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

**Next ID:** `AI-0022`

## Open improvements

### AI-0001 — Verify exact page pins for remaining ITS 18 scenario Skills

- **Date:** 2026-11-17
- **Area:** ITS 18 curated scenario Skill citations.
- **Remaining issue:** The 26 scenario Short Skills now have structured
  Requirements/Effects and standard cards, but some still cite the reviewed
  mission page range rather than the exact action page.
- **Proposed:** Verify action-level pages against the original source before
  narrowing those citations; never infer a precise page.
- **Disposition:** proposed (structured facts and rendering already completed).

### AI-0014 — Centralize historical ITS scenario inventory test expectations

- **Date:** 2026-11-18
- **Area:** ITS 17 scenario publication tests.
- **Remaining issue:** Each new reviewed mission requires editing duplicated
  scenario counts and membership lists in multiple tests.
- **Proposed:** Use one independent, reviewed expected-membership fixture while
  retaining per-scenario identity, source, geometry, and isolation assertions.
  Do not derive the expected set from the source being tested.
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

### AI-0016 — Rebaseline the retired-revision runtime snapshot

- **Date:** 2026-11-19
- **Area:** `tests/fixtures/runtime-semantic-baseline-v1.json` and
  `tools/verify_checkout_server.py`.
- **Remaining issue:** The maintained baseline requests retired
  `its-18@2026.09.01` Battleground and gets an intentional 404 under
  latest-only serving, preventing the 41-probe comparison.
- **Proposed:** Review and refresh the snapshot against the accepted
  latest-only API while keeping explicit rejection tests for retired revisions.
- **Disposition:** proposed.
