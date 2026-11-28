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

**Next ID:** `AI-0025`

## Open improvements

### AI-0024 — Profile and reduce avoidable initial browser work

- **Date:** 2026-11-28
- **Area:** Web frontend and Web backend, v1.3.0 performance audit.
- **Evidence:** At `9d7bde00`, three Windows Chrome Explorer journeys passed;
  initial median 667 ms (API 414 ms), next page 367 ms (API 51 ms),
  search 321 ms (API 14 ms, including a deliberate 250 ms UI debounce in
  the total). Single cold/repeat page samples showed additional catalog
  renders after visible-Unit lookup (Mimetism 292/455 ms first/final DOM,
  Combi Rifle 232/338 ms), with decoded detail payloads of 490/277 KB.
  Hardlock fetched four season-policy responses before Season Rules opened.
  Policy requests now start on first expansion; focused Node and desktop/mobile
  Chromium regressions passed. Unit history bodies now render on first opening;
  fixture and published Go-Pod Chromium checks passed. Three Windows Chrome
  cold/repeat Minutemen samples showed zero initial history rows versus 22
  after expansion, and first-open DOM construction took 0.2–0.5 ms (including
  toggle dispatch, excluding paint). No reliable end-to-end latency improvement
  established. The Dragoes comparison had no confirmed change rows.
- **Remaining action:** Benchmark first-open season policy latency separately.
  Profile Explorer interaction overhead separately from intentional debounce
  and automation waits; investigate parallel visible-Unit lookup or targeted
  catalog updates without changing availability semantics. The
  [live-search prefix benchmark](testing-performance.md#bounded-live-search-prefix-benchmark)
  found no material benefit from early limiting; retain the existing ranking.
  The [Unit comparison benchmark](testing-performance.md#unit-comparison-detail-inputs)
  supports history omission and the compact transport view now in use.
  Decoded payloads fell 69–73% against history-free details; server
  latency improved modestly. No additional database projection is justified.
  Extend benchmark
  coverage for these new journeys and repeat the pinned full-stack workload
  before interpreting capacity regressions.
- **Disposition:** proposed.

### AI-0023 — Separate presentation-only sources from database build freshness

- **Date:** 2026-11-26
- **Area:** Runtime build provenance and theme iteration.
- **Issue:** Palette and scenario SVG rendering changes outside the web package
  invalidate the conservative Python input envelope. A palette-only change
  required a complete history-enabled rebuild (289 seconds on Windows).
  Editable theme seeds now live in CSS, so routine color balancing no longer
  requires a rebuild.
- **Proposed:** Audit remaining actual build dependencies and move or explicitly
  exclude presentation-only Python sources from the build envelope while
  retaining static asset revision coverage and genuine data-input checks.
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
