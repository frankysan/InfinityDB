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

- The first 27 source answers are already represented as reviewed
  current-source rulings. Their ordinary-browser reachability is
  checked alongside the two narrowly scoped Core-scenario overlaps;
  broader source-semantic and release completeness remain open.
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

**Comparative review, 2026-10-28:** the two Core Killing passages
and bilingual FAQ were checked as above. The source supports considering
Firefight, but does not settle the edition/mission applicability of an
ITS-section answer. The FAQ remains Annihilation-only in InfinityDB.
`test_undeployed_ancillary_does_not_inherit_firefight_killing_scope`
pins the shared Core Killing source scope separately from the effective
FAQ selector for Annihilation, Firefight, other Core scenarios and an
unscoped lookup. Further widening requires an explicit reviewed
applicability decision or official clarification (REA-030).
