# 0.7.0 player-facing enrichment presentation audit

This audit is the presentation gate for the rules-enrichment work in 0.7.0.
Coverage and schema correctness are necessary but are not sufficient: the added
information must help an Infinity player understand the game data they are
looking at.

The audit deliberately evaluates the existing catalog and Unit experiences
rather than proposing a separate rules-reference application. Supporting rules
identities may remain without standalone pages when a contextual presentation is
more useful.

## Player questions

For each enriched Skill, Equipment item, Weapon, Trait, and representative Unit
occurrence, the browser should make the following questions easy to answer when
the underlying data supports them:

- What is this, and what does it do in play?
- What must be true before I can use it, and what restrictions apply?
- Does this specific Level, named variant, Attribute replacement, or occurrence
  modifier change the base meaning?
- Which Units use it, and in which Army contexts?
- Which related game concepts matter to understanding or using it?
- Where did InfinityDB get this interpretation, and where can I verify it?

The first five questions are player-facing information. The final provenance
question must remain available but should not dominate the normal reading order.

## Review criteria

The release audit checks the following.

**Relevance and hierarchy.** Concise gameplay meaning, Requirements, Effects,
Restrictions, declaration/action category, and applicable variant context should
be scannable before internal IDs or publication mechanics. Do not surface data
merely because it exists; a player-facing element should explain, distinguish,
navigate, or verify something useful.

**Context and scope.** Family rules, exact-source variants, supplements, and
occurrence modifiers must remain distinguishable. An occurrence-specific `(+1B)`,
`(-3)`, reroll, distance parameter, or similar value must not read as a universal
property of the canonical Skill/Equipment identity.

**Relationships.** Reviewed semantic relationships should become navigation or
context when they clarify gameplay. Raw ontology edges are not themselves UI
copy: relationship types need player-language labels, and bookkeeping edges such
as `variant-of` should not be duplicated when the variant presentation already
communicates that relationship.

**Provenance.** Official source links, publication/version, and page/section
references should be easy to reach. Provenance is supporting evidence rather
than the primary explanation of the rule.

**Accessibility and responsive use.** Meaning must survive light/dark themes,
narrow layouts, keyboard navigation, and non-color presentation. Category colors
may reinforce familiar Infinity/Wiki semantics but must always accompany readable
text.

## Initial source-level findings

The first pass over the current browser renderers establishes these concrete
follow-ups.

- **Requirements / Effects / Restrictions were visually indistinguishable.**
  `rules-reference.js` rendered each fact class as an unlabeled bullet list. The
  0.7.0 presentation work now labels these groups explicitly and orders
  Requirements before Effects before Restrictions.
- **Declaration/action categories are too easy to miss.** Skill and Equipment
  categories are currently appended to the metadata/source line. They are useful
  gameplay semantics and should receive a scannable presentation. The stylesheet
  already carries the maintained Wiki category colors; any use of those colors
  must retain text labels.
- **Reviewed related-rule edges are not presented.** Curated rule records carry
  typed forward/reverse relationships, but the current shared renderer does not
  expose them. A follow-up should render the subset that helps players navigate
  States, Peripheral/controller concepts, and similar rule context without
  dumping internal edge names into the UI.
- **Source/applicability context currently precedes the concise summary.** This is
  correct data, but the complete browser audit should determine whether the
  normal reading order should lead with gameplay meaning and move provenance/
  applicability into a secondary position.
- **Exact-source rule detail lives inside usage disclosures.** The typed variant
  label is visible before expansion, while full variant rules appear only after a
  usage section is opened. The complete-data audit must verify that this is
  discoverable for Martial Arts/Strategos Levels, BS/CC Attribute replacements,
  TinBot named variants, and future exact-source semantics.
- **Unit pages navigate to enrichment rather than explaining it inline.** Profile
  Skills, Equipment, and Weapons link to their catalog detail pages, which avoids
  duplicating rules prose. The browser audit should verify that this remains a
  useful interaction for representative play questions and that occurrence
  modifiers stay visible on the Unit where they apply.
- **Catalog list pages remain intentionally terse.** They currently prioritize
  identity and use counts rather than rules summaries. The audit should decide
  whether category/semantic cues improve scanning enough to justify adding them;
  completeness alone is not a reason to make list rows denser.

## Completion

This document records the review method and durable presentation principles.
Active findings and release blockers remain tracked in `docs/TODO.md`.

The 0.7.0 presentation audit is complete only after a representative pass against
the full generated dataset and browser has resolved every issue classified as a
0.7.0 player-relevance or correctness blocker. A field being present in an API
payload is not, by itself, evidence that the player-facing requirement is met.
