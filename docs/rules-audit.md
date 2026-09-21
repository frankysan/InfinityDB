# Rules semantics audit

This document is the coverage ledger for InfinityDB's systematic audit of the
Infinity ruleset. The goal is not to reproduce the rules. The goal is to identify
source-authoritative semantics that improve data interpretation, normalization,
validation, relationships, querying, filtering, or presentation.

Implementation-relevant findings move to `rules-semantics.md`. Verified findings
without a current consumer go to `rules-research.md`. Page-level coverage stays
here so `TODO.md` can remain a milestone-level backlog.

## Source baseline

The initial audit baseline is:

- Core rules: `data/pdf/rules/n5-rules-v5-3-en.pdf`, Infinity N5 V5.3. Use the
  printed page number for citations.
- FAQ: `data/pdf/faq/n5-faqs-v0-1-en.pdf`, N5 FAQ v0.1. FAQ findings remain
  separate from base-rule findings.
- Wiki: <https://infinitythewiki.com/>. Record the canonical page URL and the
  rules/FAQ version shown by the page when reviewed.
- Local wiki snapshot: `data/wiki/20260915/`. It predates the current N5.3 wiki
  update and must not be assumed to contain the latest wording for pages changed
  by N5.3. Refresh or explicitly mark the older snapshot when stable local wiki
  provenance is required.
- ITS material remains season-scoped and must not be silently merged into core
  rules semantics.

The live wiki currently reports N5.3 and FAQ v0.1 on current rules pages such as
`Unit_Profile` and `Basic_Rules`. The `Main_Sections` index has carried older
notice metadata, so it is used as navigation topology rather than as the version
authority for every linked page.

## Source and interpretation rules

- Prefer current official rules material when it supersedes an older local copy.
- Use the wiki for traversal, canonical page identity, cross-links, redirects, and
  current clarifications. Use the PDF for stable edition/version and printed-page
  citations.
- Keep core rules, FAQ/errata, Reinforcements, ITS season rules, and historical
  material explicitly scoped.
- Where sources appear to disagree, record the discrepancy and scope instead of
  silently combining them.
- Infinity Army remains authoritative for current unit availability and list
  legality. Rules sources explain semantics; they do not replace Army source data.
- Summarize and structure rules facts. Do not copy large portions of copyrighted
  rules text or artwork into tracked project files.

## Finding workflow

For every audited page or PDF section:

1. Record the page/section and source version.
2. Extract terms, finite value sets, relationships, invariants, notation, and
   scope rules that may affect InfinityDB.
3. Classify each concept as source-native, InfinityDB abstraction, or
   InfinityDB-derived interpretation.
4. Reconcile relevant findings against Army/API data and the current application
   model. Ask whether information is already preserved, flattened, ambiguous, or
   absent.
5. Record consequences for processing, validation, querying/filtering, or
   presentation.
6. Put immediately useful semantics in `rules-semantics.md`; put verified but
   currently unused findings in `rules-research.md`.
7. Do not implement schema/code/UI changes opportunistically during the audit.
   Feed confirmed gaps back into the normal project backlog.

A normal finding records:

- a stable local finding ID;
- canonical term(s) and rules scope;
- concise semantic statement;
- wiki URL and reviewed rules/FAQ version;
- PDF document/version and printed page, when applicable;
- related Army/API fields or InfinityDB domains, when known;
- processing, validation, query/filter, and presentation implications;
- unresolved ambiguity or follow-up work.

## Audit order

The wiki Main Sections page is the traversal spine. `Game States and Glossary` is
intentionally audited immediately after Basic Rules because its terminology,
labels, traits, and states provide vocabulary reused by later sections. Quick
Reference Charts are primarily a validation/completeness pass after the prose
rules have been audited.

- [ ] Introduction
- [ ] Basic Rules
  - [ ] Basic Rules overview: game elements, terminology/alignment, labels/traits,
    armies, game states, and game modes
  - [ ] Open and Private Information
  - [x] Unit Profile — initial semantic extraction and N5 V5.3 PDF cross-check
  - [ ] Army List
  - [ ] Orders and the Order Pool
  - [ ] Trooper Activation
  - [ ] ARO: Automatic Reaction Order
  - [ ] Order Expenditure Sequence
  - [ ] Initiative and Deployment
  - [ ] Game Sequence
  - [ ] Loss of Lieutenant
  - [ ] Silhouettes
  - [ ] Line of Fire
  - [ ] Zone of Control
  - [ ] Zones, Bases and Silhouettes
  - [ ] Coherency
  - [ ] Distances and Measurements
  - [ ] Replacing Game Elements
  - [ ] Rolls
  - [ ] Face to Face Rolls
- [ ] Game States and Glossary
- [ ] Skills and Equipment
- [ ] Combat
- [ ] Ammunition and Weaponry
- [ ] Fireteams
- [ ] Command
- [ ] Movement
- [ ] Terrain and Scenery Structures
- [ ] Triumph and Defeat
- [ ] Setting up the Gaming Table
- [ ] Scenarios
- [ ] Quick Reference Charts
- [ ] Reinforcements
- [ ] ITS FAQ
- [ ] Final cross-section reconciliation and gap analysis

## Completed page notes

### Basic Rules / Unit Profile

Status: initial semantic extraction complete.

Sources reviewed:

- Wiki: <https://infinitythewiki.com/Unit_Profile>, reviewed against the live
  N5.3 / FAQ v0.1 page.
- PDF: Infinity N5 V5.3, printed pages 8-9.

Findings promoted to `rules-semantics.md` cover Unit/Unit Profile/Trooper
structure, common versus option-specific profile data, Trooper Characteristics,
ISC, Attribute absence, VITA versus STR, AVA, Peripheral/Controller semantics,
and profile notation.

The Troop Type restrictions shown from the Unit Profile page are retained in
`rules-research.md` until their broader restrictions-chart and application use
are audited.
