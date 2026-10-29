# N5 FAQ v0.1 — ITS applicability triage

**Project domain:** Data processing

**Reviewed:** 2026-10-29. **Scope:** the locally pinned English N5 FAQ
v0.1, `data/pdf/faq/n5-faqs-v0-1-en.pdf` (five file pages, printed
pages 1–4), compared with the maintained
`data/curated/rules/n5-faq-v0.1.json`. This is a source-section
inventory and applicability decision queue, **not** a new gameplay
interpretation or an assertion that every answer is implemented in the
ordinary browser.

The maintained FAQ collection now contains **29** reviewed
`faq-ruling` records with current-source citations: 27 from the
non-ITS sections and two ITS-section answers (the scoped Supplies
carrier and undeployed Ancillary rulings). The other **eight** answers
in the printed ITS section have no standalone curated FAQ ruling. Of
the 29 published rulings, **20** are carried from the English v0.0 FAQ
and **nine** were first recorded in v0.1. The section heading is evidence
of source placement, not proof that an answer can never apply to a
core-rules scenario.

A separate [audit-only question manifest](../config/validation/n5-faq-v0.1-question-inventory.json)
pins all 29 reviewed FAQ identities to their printed English pages (11 on
p. 1, 12 on p. 2, 5 on p. 3, 1 on p. 4), along with the eight deferred
ITS questions. The tracked `test_pinned_faq_v01_question_inventory_is_complete_and_scoped`
checks source citations, v0.0/v0.1 provenance, current rules revision/date
selection and the two scenario-only runtime scopes against a fresh rules
export. The manifest is an **audit gate**, not an additional gameplay
definition or a substitute for a future historical/ITS applicability review.

**Historical v0.0 reconciliation, 2026-10-29:** The earlier English
FAQ contains 28 Q&A blocks on printed pp. 1–3. The audit manifest
independently pins the original pages of all 20 carried-forward published
rulings (ten on p. 1 and ten on p. 2), plus all eight still-deferred
ITS questions (two on p. 2, six on p. 3). Together they account for
all 28 earlier questions, leaving nine v0.1 additions, one of which
is the narrowly scoped Ancillary question. The regression checks both
the independent v0.0 inventory and each published ruling's
`facts.originalPublication` identity/page; current v0.1
`selectedCitation` pages remain separately pinned.

This closes the **question identity and historical page reconciliation**
for the two pinned English FAQ versions. It does not establish exact
publication dates, out-of-scope ITS applicability, or exhaustive
topic-to-browser access.

**Carried-forward answer semantic review, 2026-10-29:** The 20
published v0.0-origin English answers were compared with their
corresponding v0.1 English FAQ passages, including conditions and
exceptions. No material answer change was identified for these 20
rulings. The audit-only manifest now records independent answer-semantic
anchors per question; the
`test_carried_forward_v00_faq_answers_retain_reviewed_v01_semantics`
regression requires exactly those 20 identities, their original v0.0
page and selected current v0.1 page, and every reviewed answer anchor
in curated text. This protects the *meaning* of the currently selected
answers, not exact typography, automatic extraction of source-PDF text,
historical runtime replay, Spanish translation equivalence or the eight
deferred ITS-only questions.

**Carried-forward Spanish cross-check, 2026-10-29:** All 20
published v0.0-origin current answers were independently reviewed
against Spanish FAQ v0.1 printed pp. 1–3. Eight are on Spanish p. 1,
eight on p. 2, and four on p. 3; this differs from the English
printed-page distribution. The audit-only manifest now pins each
Spanish citation page in `historicalV00CarriedSpanishPages`.
`test_carried_forward_v00_faq_bilingual_pages_and_question_scope`
checks all 20 original/selected/corroborating citations, retained
current date and revision gates, the Supplies-only carrier scope,
and no invented contradictory citations. No material contradiction
in the answers was found.

One **question-context qualification** was found: English v0.0 and
v0.1 ask generally about targeting a Stealth user during multiple
activations that generate AROs, but Spanish v0.1 p. 2 specifically
asks about a Stealth user *outside* the reactive Trooper's Zone of
Control or Hacking Area. Both answers make the ARO Idle when the
Stealth user declares no ARO-enabling Skill. Keep English selected
and record the narrower Spanish context rather than implying an
independent permission for other positions. No published answer,
runtime rule scope or source precedence was changed. This is a
manual bilingual semantic audit of the 20 published carry-forwards,
not exact translation certification or review of the eight deferred
ITS-only questions.

**New v0.1 answer semantic review, 2026-10-29:** The nine
published answers first found in the English v0.1 FAQ were checked
against the pinned English and Spanish v0.1 PDFs. The audit-only
manifest now pins their **nine answer-semantic anchor sets**, distinct
English/Spanish printed-page locations, and v0.1 original publication.
`test_new_v01_faq_answers_retain_reviewed_bilingual_source_semantics`
checks the exact nine new identities, answer meaning, citation pages,
selected source, effective-date/revision gates and the existing narrow
Annihilation scope of the ITS-section Ancillary ruling.

Three differences require explicit classification: the Haris
**three-to-two (EN) versus two-to-two (ES)** example remains a
conflicting numerical citation; Spanish omits English's explicit
**FT Master** qualification without denying it; and the English
**firing a Deployable** question is narrower than Spanish's
**placing Deployables** question, although both forbid vertical
placement. The last two are source wording differences, not
contradictory answers. Keep English selected, preserve both citations,
and do not infer new gameplay or scenario scope. This closes the
bounded nine-answer semantic comparison, **not** general bilingual
equivalence of all historical answers, historical replay, exact
publication dating or deferred ITS season applicability.

**Current-selector cross-topic reconciliation, 2026-10-29:** The
`test_published_faq_all_topic_links_preserve_selected_scope_and_history`
regression checks all 48 topic associations across 42 distinct topics
from the 29 current reviewed rulings. For every topic, it checks exact
runtime membership in four contexts (unscoped, Annihilation, Supplies,
Firefight), retaining selected v0.1 citations, original v0.0/v0.1
provenance and explicitly reviewed applicability. It also checks that
queries for the older 2025-10-15 anchor, the pre-effective 2026-08-31
boundary and N5.2 do not select current FAQ rulings. The two
ITS-section/approved Core-scenario overlaps remain strictly scoped.
This establishes no historical replay or broader ITS applicability;
it does not re-interpret unchanged question text or select answers
from v0.0 for historical users.

**Published FAQ punctuation fidelity, 2026-10-29:** A source-text
check against the pinned English FAQ PDFs found five malformed
possessive apostrophes rendered as question marks in four reviewed
FAQ records: Deployment Phase repositioning, Direct Template Weapon
secondary targets (question and answer), declaration target position,
and separate Surprise Attack MODs. The historical English FAQ v0.0
source title also had a stray replacement question mark. These are
text-encoding artifacts, not new source contradictions. The reviewed
FAQ copy now uses ordinary apostrophes; source identity, page citations,
application dates and rules semantics are unchanged. The regression
`test_published_faq_copy_has_no_corrupted_question_mark_possessives`
verifies all 29 current FAQ questions/answers and pins the repaired
phrases and historical source title. This is **not** a full source
wording/translation certification.

## Source-byte identity and publication boundary

The audit manifest also pins the exact SHA-256, source ID, version,
repository-relative local path and PDF file-page count for the historical
English v0.0 and current English/Spanish v0.1 FAQs. On 2026-10-28, all
three locally available PDFs matched these pins (**3/3**). The focused
`test_pinned_faq_pdf_source_identity_and_available_bytes` checks that
the pins agree with the maintained FAQ source declarations and hashes
the local files when available. A clean checkout without the ignored
source PDFs skips byte verification; a skipped test is not source
authentication. This is an audit-only gate, independent of runtime
publication and the question-level coverage check.

The official September 1, 2026 N5.3 update notice announces a new FAQ.
It does not independently prove the exact publication day of either
FAQ v0.1 PDF. PDF creation metadata, source-update announcement dates,
local acquisition dates and selected applicability dates remain
distinct evidence. The earlier English v0.0 PDF likewise has no
independently established publication day.

**Player-facing provenance correction, 2026-10-29:** The FAQ section
now identifies 2026-09-01 as the selected **reference date** and
explicitly states that it is an announcement-era anchor, not a verified
PDF publication day. Individual FAQ cards label the API's existing
`selected_source.published_date` as a **source date anchor**, retaining
the selected version, exact PDF page citation, and original v0.0
provenance. The field name and selector remain unchanged for
compatibility; historical replay is not newly enabled. Chromium and
JavaScript render regressions pin the distinction. No change to
question/answer text or scenario applicability was made.

## Historical applicability decision (1.0 boundary)

**Reviewed 2026-10-29:** All 29 current rulings have selected English
v0.1 citations and N5.3 applicability from the project's
2026-09-01 announcement-era reference anchor; the 20 v0.0-origin
citations are retained as historical **provenance only**. None
supplies a reviewed v0.0-selected historical read-model contribution.
Neither the date anchor nor the source-PDF metadata independently
establishes an exact FAQ upload or effective date.

The selector's four independent date gates are (1) selected source
date anchor, (2) original source date anchor, (3) owning collection
effective date and (4) ruling applicability `effectiveFrom` /
`effectiveUntil`, followed by exact rules revision and any
season/scenario restrictions. A historical query must not substitute
the earlier original citation for the selected v0.1 citation.
The `test_current_faq_temporal_gates_are_independent_for_all_published_rulings`
regression checks each gate separately for all 29 current rulings,
including the two scenario-specific Core overlaps, with synthetic
in-memory date shifts only; it does not publish a historical edition.

**1.0 choice:** Keep the existing explicit-context API and current
player-facing source-date explanation; historical edition replay,
version/season/date picker UI and reconstruction of older rule/FAQ
combinations are deferred. Such support first requires independently
reviewed earlier rule-revision compatibility, historical selected
source/citation, scoped effective dates, retained topic identities,
and conflict/supersession review. The ongoing 1.0 current-source
completeness and discoverability gate remains open. See
[the authoritative data model](data-model.md#dated-faqerrata-layer-published-reviewed-subset).

## Printed ITS section — uncovered questions

All source pages here are the **printed FAQ page numbers**, not the
five-page PDF file's indices.

- **Printed p. 3 — Neutral HVT and movement.** The source says HVTs do
  not block movement. **Disposition:** ITS/scenario-specific; review
  scenario identity and browser need before publication.
- **Printed p. 3 — Spotlight for Telemetry and HVT: Designation.**
  The source asks whether successful Rolls count without applying
  Targeted State. **Disposition:** ITS Classified Objectives; defer
  from the four core-scenario baseline pending explicit ITS scope.
- **Printed p. 3 — Area of Interest / Activate Communication Antenna
  AROs.** The source distinguishes first-Short-Skill and activation
  timing for opposing Hackers. **Disposition:** ITS-specific scenario
  mechanics; defer from core scope.
- **Printed p. 3 — Crossing Lines / Superior Deployment.** The source
  exempts Netrods and Imetrons from the scenario rule.
  **Disposition:** ITS-specific; defer from core scope.
- **Printed p. 3 — Akial Interference / failed Emit selection.** The
  card may be selected again after a failed Roll.
  **Disposition:** ITS-specific; defer from core scope.
- **Printed p. 3 — Akial Interference / Predator objective.** Kills
  preceding the card being drawn do not count.
  **Disposition:** ITS-specific; defer from core scope.
- **Printed p. 3 — Akial Interference / tracking used cards.** The
  source permits players to choose their own tracking method.
  **Disposition:** ITS-specific operational detail; defer from core
  scope.
- **Printed p. 4 — Crossing Lines / Impetuous Activation.** Movement
  targets the nearest enemy Deployment Zone; distance can be
  measured when uncertain. **Disposition:** ITS-specific; defer
  from core scope.

## Already published from the ITS section

- **Printed p. 3 — carrying a scenario element into Marker State:**
  `faq-ruling:scenario-element-carrier-marker-state` now applies only
  to `scenario:supplies` (and its carrying rule). Its original English
  FAQ v0.0 wording is on printed p. 2; the current English/Spanish v0.1
  citations remain on printed p. 3. Core N5.3 Supplies p. 153 independently
  says that only Models, not Markers, can carry Supply Boxes. Unscoped
  and unrelated scenario queries must not select this ruling. This is
  **not** a global Marker State restriction for other scenarios.
- **Printed p. 4 — undeployed Peripheral (Ancillary), Killed
  objectives:** existing
  `faq-ruling:undeployed-ancillary-not-killed`, currently selected
  for `scenario:annihilation` and `rule:scenario:killing`, with
  `scenarioIds: ["scenario:annihilation"]`. The FAQ question refers
  generically to scenario objectives; its exact applicability beyond
  Annihilation remains **review-needed**, not an inferred universal
  kill-count rule. The comparative review of pinned N5.3 English
  **Annihilation p. 150** and **Firefight p. 155** confirms that both
  scenarios publish the same Killing wording (Dead State, end-of-game
  Null State, and undeployed Troopers). Firefight also scores Killed
  Specialist Troops, Lieutenants and Army Points. This is real
  scenario-specific overlap, but the **English and Spanish FAQ v0.1
  p. 4** exception is placed under ITS and identifies neither Core
  mission. Identical Killing wording alone does not establish official
  cross-publication applicability. The generic Peripheral rules
  (N5.3 pp. 106–108) establish the equipment's deployment and points
  treatment, but not a mission-specific Killed exception. Keep the
  reviewed Annihilation-only InfinityDB selection as a conservative
  publication decision, not an explicit assignment in the FAQ itself.
  Firefight remains unselected pending scenario-specific source evidence
  and a reviewed applicability change; do not silently broaden it.

## Fireteam bilingual source qualification

**Checked 2026-10-29:** English FAQ v0.1 p. 3 says that the Fireteam
Charts' minimum membership requirements apply at creation, explicitly
adding that **FT Master has its own overriding rules**. Spanish FAQ
v0.1 p. 3 confirms the creation-only minimum, but omits the FT Master
qualification. The underlying N5.3 Fireteam Integrity rule (English
p. 134) and the maintained `skill:ft-master` restriction independently
support the exception. Because Spanish does not negate the exception,
the maintained `faq-ruling:fireteam-required-member-lost` retains
English as selected source and `conflictingCitations: []`, with the
omission recorded in `selectionReason`. This differs from the
actual numerical contradiction in the adjacent **Fireteam Type / Haris**
example, which remains an explicit conflicting citation. No effective
date, source selection, gameplay semantics or scenario scope changed.

## Release implications

- The 27 general answers and the two narrowly reviewed Core-scenario
  overlaps are all represented as reviewed current-source rulings.
  All 29 English selected answers and their corroborating Spanish
  source pages have completed bounded semantic/source review. The
  48 authored topic associations have verified current API and
  normal browser entry points; the remaining release-candidate
  acceptance is separate from the source-inventory reconciliation.
- The Supplies carrier clarification has a reviewed, scenario-scoped
  FAQ record and a focused API selection regression. The other eight
  ITS-section answers remain uncurated until their own season/scenario
  scope is approved.
- Do not promote the remaining ITS-specific scenario and Classified
  Objective rulings to generic N5 help just because the FAQ document
  belongs to N5 v0.1.
- These dispositions do not resolve the separate **Commlink /
  Reinforcements Annex** edition boundary. The FAQ v0.1 does not
  provide Commlink mechanics or an annex adoption statement.

**Browser acceptance, 2026-10-28:** `test_verify_scenario_faq_browser.py`
verifies the live scenario page at 1440px and 390px. It confirms that
the Supplies clarification and citation are visible, that Annihilation
keeps its own Ancillary clarification, and that Domination/Firefight
display no FAQ section. Navigation reuses the same page to detect
stale FAQ content. The source-isolated API regression also pins
Supplies selection. This acceptance is not a general FAQ
source-coverage or cross-scenario applicability certification.

**Published-ruling browser reachability, 2026-10-29:** The source-driven
`test_every_published_faq_has_a_normal_browser_entry_point` asserts
that the maintained 29-record set is exactly covered by 25 normal
player-facing topic/scenario routes. A fresh curated rules export and
the current local Army database back WSGI-routed Chromium at 1440 and
390 px. All **8/8 grouped tests passed**, checking each ruling's
question, answer, selected FAQ citation, and authored topic at its
normal entry point. Covered paths include Skills, Equipment, Traits,
States, Hacking Programs, General Rules, Fireteams and the two approved
Core scenario overlaps. The separate scenario navigation regression
retains Domination/Firefight non-selection. This certifies bounded
current-publication browser delivery, **not** full historical
applicability, all source wording, general discoverability through
search, manual visual acceptance or hosted release parity.

**All authored-topic browser coverage, 2026-10-29:** Extending
the first-entry-point gate, the tracked
`test_faq_browser_routes_cover_every_published_topic_association`
now verifies an exact one-to-one inventory of all **48 (topic, FAQ)
associations across 42 unique topics**: 29 primary FAQ entries and
19 additional authored-topic entries. The secondary route map covers
existing Skills, Traits, Equipment, States, General Rules, Fireteams
and both published Core Scenarios. On the shared Fireteams/Scenario
pages, the owning topic's FAQ is displayed without creating a
duplicate route for the embedded rule. The paired
`test_every_additional_faq_topic_link_is_visible_from_its_normal_page`
runs Chromium at 1440 and 390 px and verifies each additional card's
question, answer and selected citation. This complements the
48-edge applicability-first API test, which independently verifies
topic matching and scenario/date/revision scope. It does not establish
user navigation clicks or search rankings, hosted release parity, or
unpublished ITS applicability.

**Player-facing source-discrepancy acceptance, 2026-10-29:**
`test_fireteam_faq_discloses_real_source_conflict_not_language_omission`
uses the normal Fireteams page and fresh rules export in Chromium
at 1440 and 390 px. Exactly one of the 29 curated rulings has
`conflictingCitations`: the English-selected three-to-two Haris
example versus the Spanish two-to-two count. The visible FAQ card
labels its selected English v0.1 citation and 2026-09-01 source-date
anchor, and an expandable disclosure reveals the English selection
rationale and separate Spanish printed p. 3 link.
The adjacent required-member ruling retains the FT Master exception
without a false contradictory-source warning. All primary/secondary
FAQ route gates also assert English selected source, v0.1 version
and date-anchor labels. No gameplay, source precedence, date gates
or new ITS scope was changed. Final 1.0 release-candidate parity and
manual visual/touch review remain outstanding.

**Release-artifact parity follow-up, 2026-10-29:** The normal FAQ
tests and browser gate build a fresh rules database, so they do
not establish that the tracked `data/generated/rules.db` is
release-matched. A new explicitly enabled release-only test compares
all 29 stored ruling records and all 168 current topic/scenario
query contexts against a fresh curated export, while also checking
the closed earlier-date and wrong-revision boundaries. Initial
read-only validation at `f1dbf187` failed with **28 record-field
differences** and **134 read-model projection differences**, including
an older historical FAQ citation title. After regenerating the tracked
rules database on 2026-10-29, a direct invocation of the opt-in parity
function **passed**, covering all 29 identities and 168 read-model
topic/scenario contexts. No curated gameplay or source authority
changed. A subsequently attempted **release-pair browser fixture**
failed at application startup: the existing ignored
`data/generated/deployed-objects.json` still pins the *old*
rules-database SHA-256. This is intentional release integrity
enforcement, not a FAQ selector failure. Regenerate and check that
dependent publication before rerunning the opt-in tracked-database
FAQ Chromium gates; final 1.0 candidate/browser acceptance is still
open. See the [repeatable candidate check](testing.md#10-four-core-scenario-browser-acceptance).

**Comparative review, 2026-10-28:** the two Core Killing passages
and bilingual FAQ were checked as above. The source supports considering
Firefight, but does not settle the edition/mission applicability of an
ITS-section answer. The FAQ remains Annihilation-only in InfinityDB.
`test_undeployed_ancillary_does_not_inherit_firefight_killing_scope`
pins the shared Core Killing source scope separately from the effective
FAQ selector for Annihilation, Firefight, other Core scenarios and an
unscoped lookup. Further widening requires an explicit reviewed
applicability decision or official clarification (REA-030).
