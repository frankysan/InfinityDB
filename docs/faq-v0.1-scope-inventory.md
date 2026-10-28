# N5 FAQ v0.1 — ITS applicability triage

**Project domain:** Data processing

**Reviewed:** 2026-10-28. **Scope:** the locally pinned English N5 FAQ
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
in the printed ITS section have no standalone curated FAQ ruling. The section heading is evidence of
source placement, not proof that an answer can never apply to a
core-rules scenario.

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
  to `scenario:supplies` (and its carrying rule), with printed FAQ
  English/Spanish p. 3 citations. Core N5.3 Supplies p. 153 independently
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
  kill-count rule.

## Release implications

- The first 27 source answers are already represented as reviewed
  current-source rulings; their API/browser completeness remains a
  separate acceptance task.
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

**Next validation:** extend ordinary Supplies browser acceptance
to verify that the contextual FAQ appears only when the Supplies
scenario is selected; separately review the undeployed Ancillary
ruling before expanding it beyond Annihilation.
