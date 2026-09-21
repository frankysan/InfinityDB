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
- [x] Basic Rules
  - [x] Basic Rules overview: game elements, terminology/alignment, labels/traits,
    armies, game states, and game modes
  - [x] Open and Private Information
  - [x] Unit Profile — initial semantic extraction and N5 V5.3 PDF cross-check
  - [x] Army List
  - [x] Orders and the Order Pool
  - [x] Trooper Activation
  - [x] ARO: Automatic Reaction Order
  - [x] Order Expenditure Sequence
  - [x] Initiative and Deployment
  - [x] Game Sequence
  - [x] Loss of Lieutenant
  - [x] Silhouettes
  - [x] Line of Fire
  - [x] Zone of Control
  - [x] Zones, Bases and Silhouettes
  - [x] Coherency
  - [x] Distances and Measurements
  - [x] Replacing Game Elements
  - [x] Rolls
  - [x] Face to Face Rolls
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

### Basic Rules — section complete

Status: core N5.3 wiki/PDF semantic extraction complete for the Basic Rules
section. Embedded FAQ material was observed but not promoted into core findings;
FAQ/errata semantics remain separately scoped under the source rules above.

Primary sources reviewed:

- Wiki: <https://infinitythewiki.com/Basic_Rules> and every Basic Rules page in
  its navigation sequence, reviewed against the live N5.3 / FAQ v0.1 wiki.
- PDF: Infinity N5 V5.3, printed pages 6-26.

The section produced implementation-relevant findings in
`rules-semantics.md` and future-facing findings in `rules-research.md`. The
reconciliation pass also confirmed several existing InfinityDB boundaries and
one presentation mismatch that should be handled later rather than fixed during
this documentation audit.

#### Basic Rules overview, information, and Army Lists

Sources reviewed:

- <https://infinitythewiki.com/Basic_Rules>
- <https://infinitythewiki.com/Open_and_Private_Information>
- <https://infinitythewiki.com/Unit_Profile>
- <https://infinitythewiki.com/Army_List>
- PDF: Infinity N5 V5.3, printed pages 6-11.

Promoted semantics cover the distinction between Labels and Traits, transient
Game States, Army-List disclosure/privacy context, army-specific list membership
and AVA, Cost/SWC context, and the Unit Profile findings already recorded by the
initial pass.

The rules reinforce the current application-model boundary: a Unit can occur in
multiple Army Lists with different list membership and AVA, while the logical
Unit remains a cross-Army InfinityDB identity. Points and SWC also belong to the
selectable option/occurrence context rather than the reusable loadout payload.

#### Orders, activation, AROs, and game sequence

Sources reviewed:

- <https://infinitythewiki.com/Orders_and_the_Order_Pool>
- <https://infinitythewiki.com/Trooper_Activation>
- <https://infinitythewiki.com/ARO>
- <https://infinitythewiki.com/Order_Expenditure_Sequence>
- <https://infinitythewiki.com/Initiative_and_Deployment>
- <https://infinitythewiki.com/Game_Sequence>
- <https://infinitythewiki.com/Loss_of_Lieutenant>
- PDF: Infinity N5 V5.3, printed pages 11-18.

Promoted semantics separate Training from the Orders a loadout generates,
distinguish static order-generation data from the runtime Order Pool, confirm
the Basic Short/Short/Long Skill declaration categories used by the curated
rules layer, and prevent dynamic Loss of Lieutenant effects from being mistaken
for permanent profile characteristics.

A concrete presentation mismatch was found during reconciliation:
`src/infinity_db/web/static/unit.js` currently labels the `tactical` order symbol
as `Tactical Awareness`. The rules define the symbol/profile fact as a
**Tactical Order**; **Tactical Awareness** is the Special Skill that grants an
additional Tactical Order. Keep the source order type and the granting Skill as
separate concepts. This audit records the gap but deliberately does not change
runtime code.

#### Spatial concepts and measurement

Sources reviewed:

- <https://infinitythewiki.com/Silhouette>
- <https://infinitythewiki.com/Line_of_Fire>
- <https://infinitythewiki.com/Zone_of_Control>
- <https://infinitythewiki.com/Zones,_Bases_and_Silhouettes>
- <https://infinitythewiki.com/Coherency>
- <https://infinitythewiki.com/Distances_and_Measurements>
- <https://infinitythewiki.com/Replacing_Game_Elements>
- PDF: Infinity N5 V5.3, printed pages 18-22.

Promoted semantics establish that the `S` value identifies a Silhouette Template
with defined geometry, that rules-table distances are expressed in inches, and
that Coherency is a relationship mechanic centered on a context-defined
Reference Trooper. Detailed LoF/ZoC/zone/replacement geometry remains research
material until InfinityDB has a consumer for tabletop spatial rules.

The measurement audit supports the existing separation between source units and
presentation units. Infinity Army range data may be stored in source-native
metric values while the rules describe tabletop measurements in inches; any
conversion must therefore retain explicit source/unit context rather than
reinterpreting a bare number.

#### Rolls and profile modifiers

Sources reviewed:

- <https://infinitythewiki.com/Rolls>
- <https://infinitythewiki.com/Face_to_Face_Rolls>
- PDF: Infinity N5 V5.3, printed pages 23-26.

Promoted semantics establish that parenthetical values beside a Skill, Weapon,
or Equipment item are scoped to use of that item and that notations such as a
plain MOD, `Attribute=value`, `PS=value`, Burst changes, ReRoll, Special Dice,
Ammunition, Traits, and Saving-Roll changes have different meanings. They must
not be normalized into one generic signed-modifier field. This directly supports
the existing curated parameter-semantics approach and the Skill Modifiers UI.

Normal/Face-to-Face resolution, Success Value limits, Criticals, and related
procedural roll rules are recorded in `rules-research.md` for future rules/help
features rather than modeled as static Army facts.
