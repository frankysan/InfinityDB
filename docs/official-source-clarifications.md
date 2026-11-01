# Official source clarification register

**Project domain:** Data processing
**Maintained owner:** This is the canonical register of known Infinity rules, Army, Wiki, FAQ and scenario-source ambiguities, inconsistencies, and potential official corrections.
**Last reviewed:** 2026-11-01
**Publisher contact:** Not submitted. The entries are *candidate questions*, not claims that Corvus Belli has ruled on them.

## Purpose and maintenance contract

This register collects questions that may eventually be sent to Corvus Belli for clarification, correction or publication harmonization. It records disagreements **between official sources**, **within a single official source**, or **in scope/applicability left genuinely indeterminate** after source review. It also retains locally reconciled publication mistakes until an official correction is confirmed. It is *not* a list of implementation bugs, a substitute for rules curation, or a reason to delay v1.0 automatically.

- **Stable IDs:** Use `SRC-001`, `SRC-002`, etc. sequentially; never reuse or renumber them. Retain closed entries and dated responses. REA, ARMY and other existing issue IDs remain aliases, not replacement IDs.
- **Status vocabulary:** `open — ruling needed` means the gameplay answer is not determined by available authority; `open — correction requested` means the discrepancy exists, though a supported working interpretation is available; `open — source intent unknown` means notation/coverage needs publisher verification; `answered — official` requires a linked dated publisher reply, FAQ, erratum or revised publication. A *locally reviewed* interpretation is never an official answer.
- **Entry fields:** State source/edition/revision and precise location; quote only brief identifying notation when needed; separate confirmed observations from inference; give one clear, answerable publisher question and the present InfinityDB disposition. Follow source supersession and contextual scope rather than resolving by whichever source is newest.
- **When to add an item:** Confirm that the source conflict or missing scope is real and player-relevant; search current official rules/FAQ and known dated corrections; create the next ID and link the existing investigation. If only a defect in InfinityDB is found, record it in `TODO.md` instead. If the apparent issue is already answered, record that resolution with its official citation or omit an unneeded duplicate.
- **After an official response:** Record the exact response/source, date, edition and affected scenarios/profiles, update status, and create any required implementation/testing task in `TODO.md`. Check whether previous interpretations or related entries are superseded; preserve source-native values and prior history. Don't generalize a scenario- or edition-specific ruling.
- **Submission:** These questions have **not** been sent. Before contacting the publisher, reconfirm source revisions, remove superseded questions and group related requests by topic. Do not transmit unpublished, private, or machine-local archives. The questions below are drafts; avoid presuming a particular answer.

`docs/TODO.md` tracks *actions* (including following up with the publisher); this register owns the **question, evidence, ambiguity, and external status**. `docs/data-model.md` and `docs/rules-semantics.md` still own current product behavior and reviewed gameplay interpretation, respectively. Historic `REA-*` audit documents preserve original source review detail without becoming a second active issue ledger.

## Open questions: rules and applicability

### SRC-001 — Charontid Hacking Device Plus: unqualified SR-1

- **Status:** open — ruling needed. **Alias:** Equipment source 101 / extra 344.
- **Evidence:** Pinned Army `601-combined-army.json`, Charontid source Unit 498, loadout options 4 and 9 (raw occurrences 51441/51461), each say `UPGRADE: SR-1` without naming any Hacking Program. N5.3 English/Spanish Hacking rules p. 54 discuss program Upgrades but do not establish the target of this *unqualified* modifier; N5 FAQ v0.1 does not answer it. See [source-owner investigation](data-model.md) and [cross-edition Upgrade research](rules-semantics.md).
- **Question:** Does Charontid Hacking Device Plus `UPGRADE: SR-1` reduce the target's Saving Roll against **every** Hacking Program used through that device which causes a Saving Roll, or only particular programs? If restricted, which?
- **InfinityDB:** Preserves both raw signatures unresolved. The all-programs reading is a plausible working hypothesis, **not an official ruling**.

### SRC-002 — Silent versus Attribute Immunity; bilingual qualifier

- **Status:** open — ruling needed. **Aliases:** Silent / Immunity (ARM/BTS) source review.
- **Evidence:** N5.3 Silent conditional Dodge MOD and Immunity (ARM)/(BTS) Saving-Roll-triggered Trait protection leave ordering/applicability unclear; Spanish N5.3 p. 182 omits the explicit Face to Face qualification present in the English wording. See [source-review TODO history](TODO.md) and [reviewed data model](data-model.md).
- **Question:** When a Silent weapon would impose its Dodge MOD, does relevant Attribute Immunity prevent that MOD, or only its later Saving-Roll-associated effects? Is omission of the Face to Face qualifier in Spanish intentional?
- **InfinityDB:** Uses the explicitly scoped English text and discloses the unresolved interaction; no blanket Immunity override is inferred.

### SRC-003 — Direct Doctor/Engineer on non-Allied targets

- **Status:** open — ruling needed. **Alias:** REA-038.
- **Evidence:** N5.3 English pp. 90–91 and reviewed Wiki Doctor/Engineer requirements lack a universal Allied-only clause for **direct** use, unlike Allied-only Kits and delegated Servant/Cyberplug treatment (pp. 106–107, 123–124). Engaged and target-State restrictions remain independently applicable. [Detailed investigation](rules-explanation-audit-1.0.md#rea-038---direct-doctorengineer-target-allegiance-is-not-established).
- **Question:** May Doctor or Engineer directly treat an otherwise eligible non-Allied Unconscious/Immobilized target? Does the answer differ for Neutral, Hostile or scenario-designated targets? Confirm distinctions from Kit/Peripheral use and Engaged restrictions.
- **InfinityDB:** Does not infer universal non-Allied eligibility merely from missing Allied wording.

### SRC-004 — Applicability of ITS FAQ scenario-element and Ancillary answers to Core scenarios

- **Status:** open — ruling needed. **Alias:** REA-030.
- **Evidence:** N5 FAQ v0.1 ITS-section answers address scenario-element Marker States and undeployed Ancillary/Killed exceptions; core N5.3 scenarios have distinct scoring conditions. The reviewed Annihilation applicability is limited, not a universal Core/ITS adoption. See [FAQ scope inventory](faq-v0.1-scope-inventory.md).
- **Question:** Which, if any, ITS-section scenario-element Marker-State and undeployed Ancillary Killed rulings also govern the four N5.3 Core scenarios, and under what exact scenario conditions?
- **InfinityDB:** Preserves source-section and scenario-specific applicability; no broad ITS-to-Core inheritance.

### SRC-005 — Special Dice and the Fireteam six-dice reminder

- **Status:** open — correction requested. **Alias:** REA-041.
- **Evidence:** Official Spanish N5.3 p. 75 excludes +1 Special Die from the Burst-6 cap, while its Fireteam reminder p. 140 includes extra dice in a maximum total of six. English N5.3 pp. 75/136 consistently distinguish Burst and Special Dice. [Full discrepancy](rules-explanation-audit-1.0.md#rea-041---spanish-fireteam-dice-reminder-conflicts-with-its-general-sd-rule).
- **Question:** Does a Fireteam at B6 receiving +1 SD roll seven dice and then discard as appropriate, or is there an intended Fireteam-only total-six-dice limit? Which printed Spanish clause should be corrected?
- **InfinityDB:** Follows general Burst/SD distinction; displays the official-source contradiction.

### SRC-006 — Dodge (ARM+3) success/failure condition

- **Status:** open — correction requested. **Alias:** REA-042.
- **Evidence:** Both English and Spanish N5.3 PDFs p. 75 say the +3 ARM/BLI applies whenever Dodge is declared; archived English/Spanish Wiki modifier templates instead require a **failed PH** Dodge Roll. [Full discrepancy](rules-explanation-audit-1.0.md#rea-042---dodge-arm3-has-incompatible-englishspanish-conditions).
- **Question:** Does a Trooper with Dodge (ARM+3) receive the ARM bonus for applicable Saving Rolls following any Dodge declaration, including when its PH Roll succeeded but an Attack still hits, or only when that PH Roll fails?
- **InfinityDB:** Uses the bilingual PDF interpretation; retains a visible Wiki conflict note.

### SRC-007 — Fireteam Morat Level 3 example grants Level 4 bonus

- **Status:** open — correction requested. **Alias:** REA-034.
- **Evidence:** English N5.3 p. 138 and Spanish p. 142 show three matching members in a five-member CORE (Level 3) but include Level 4's +1 BS/CD bonus; their Fireteam level tables reserve it for four matching/equivalent members (English pp. 135–136, Spanish pp. 139–140). [Reviewed interaction](rules-semantics.md).
- **Question:** Should the Morat Case 2 example omit +1 BS/CD, or is a separate exception intended?
- **InfinityDB:** Uses the table's Level 3 bonuses and discloses the incorrect-looking example.

### SRC-008 — Haris FAQ example: English three-to-two versus Spanish two-to-two

- **Status:** open — correction requested.
- **Evidence:** English N5 FAQ v0.1 Fireteam Type/Haris explanation uses a **three-to-two** member transition, while Spanish v0.1 gives **two-to-two**. The Spanish answer also omits an explicit FT Master qualifier in another adjacent question; omission alone is *not* a contradictory answer. [Bilingual FAQ review](faq-v0.1-scope-inventory.md).
- **Question:** What is the intended original Haris size and the exact surviving eligibility when a member is lost? Is the Spanish numerical example a typo? Is the FT Master qualifier in the English answer intended to apply equally in Spanish?
- **InfinityDB:** Keeps the English-selected answer and both source citations; no inference from omission.

### SRC-009 — Fireteam chart references with no exact Army Unit/loadout match

- **Status:** open — source intent unknown. **Alias:** ARMY-01.
- **Evidence:** Pinned Fireteam chart has 11 rows referencing eight exact slugs without corresponding Unit definitions (including three Combined Army Spec-Ops placeholders), ARJUNA matching only a global rather than army-local Unit, and KORSAN FTO notation without a locally FTO-named loadout. See [external-source TODO provenance](TODO.md) and [Fireteam model](data-model.md).
- **Question:** Which missing identities are intentional placeholders versus missing Army Units, and what are the intended army-local ARJUNA and KORSAN FTO eligibility/matching targets?
- **InfinityDB:** Retains chart text and unresolved references; invents neither aliases nor eligible loadouts.

## Open questions: weapons, equipment, and Army source identities

### SRC-010 — Armed Turret E/Mitter Saving Roll count

- **Status:** open — ruling needed. **Alias:** REA-045.
- **Evidence:** Multiple pinned Army captures give Armed Turret weapon 226 / E/Mitter mode **one** BTS/2 Saving Roll, while standalone E/Mitter weapon 25, E/M Ammunition and N5.3 chart (English p. 186; Spanish p. 195) require **two**. No Turret-specific exception found. [Detailed provenance](rules-explanation-audit-1.0.md#rea-045---armed-turret-emitter-disagrees-with-standard-em-saving-rolls).
- **Question:** Is the Turret's one-roll E/Mitter mode intentional, or should it use two BTS/2 Saving Rolls per hit like ordinary E/Mitter?
- **InfinityDB:** Preserves imported Turret mode and warns; does not invent a Turret-only E/M exception.

### SRC-011 — Armed Turret Silhouette S2 versus S1

- **Status:** open — correction requested. **Alias:** REA-037.
- **Evidence:** Detailed N5.3 Armed Turret profile uses S2, but the same PDF's deployable summary and final table show S1 (English/Spanish N5.3 around p. 74 and summary). [Source investigation](rules-explanation-audit-1.0.md).
- **Question:** Is Armed Turret S2 or S1 for placement, geometry, LoF and other Silhouette-dependent rules? Which table/profile is erroneous?
- **InfinityDB:** Preserves the reviewed detailed S2 value with a conspicuous source discrepancy; separate from SRC-010.

### SRC-012 — Mine and Dazer deployable Silhouettes across sources

- **Status:** open — correction requested.
- **Evidence:** Six Mine family profiles show S0 in N5.3 publications versus Army S1; Dazer has a separate cross-publication S0/S1 conflict. S0 itself is a valid 25 mm × 3 mm template (N5.3 p. 18). [Original external-source research](TODO.md) and [Silhouette data model](data-model.md).
- **Question:** Which Silhouette value should be used for each affected Mine profile and for Dazer? Are the Army S1 entries intentional or stale, and should one uniform rule apply to these specific objects?
- **InfinityDB:** Preserves source-specific values and ambiguity; does not infer a universal S0/S1 precedence or geometry change.

### SRC-013 — PARA Mine Army footnote marker

- **Status:** open — source intent unknown.
- **Evidence:** N5.3 Weapon Chart p. 181 and reviewed Wiki use `[*]` (Weaponry reference); pinned Army uses `[**]` (Ammunition reference). The N5.3 legend on p. 176 distinguishes those destinations. [Detailed source history](n5-source-history.md#reviewed-current-source-differences).
- **Question:** Should PARA Mine carry the Weaponry `[*]`, Ammunition `[**]`, or both references in Army's weapon display?
- **InfinityDB:** Preserves both notations and links to both relevant rule owners; no new gameplay effect.

### SRC-014 — Sepsitor Plus footnote missing from Army

- **Status:** open — source intent unknown.
- **Evidence:** N5.3 Sepsitor variants have weapon-specific rules and chart footnotes (p. 73 and weapon chart); pinned Army omits the expected `[*]` on Sepsitor Plus. [Reviewed source history](n5-source-history.md).
- **Question:** Is the missing Sepsitor Plus Army footnote intentional, or should it link to the same weapon-specific explanation as the chart?
- **InfinityDB:** Maintains the existing Sepsitor rules reference without fabricating an Army marker.

### SRC-015 — WildParrot Non-Lethal Trait omitted from Army

- **Status:** open — correction requested.
- **Evidence:** N5.3 p. 74 and pinned Wiki WildParrot show `Non-Lethal`; the pinned Army profile omits the Trait despite E/M Ammunition. [Weapon source review](rules-research.md).
- **Question:** Should WildParrot's Army profile explicitly carry Non-Lethal, or is the difference intended?
- **InfinityDB:** Preserves imported Army data and a cited source note; no unverified Trait insertion.

### SRC-016 — PT: Endgame Double Shot missing from Army notation

- **Status:** open — source intent unknown.
- **Evidence:** The reviewed Endgame program/weapon description and current rules contain Double Shot; pinned Army source does not expose that property. [Source-history review](n5-source-history.md).
- **Question:** Should the Endgame Army weapon/program presentation include the Double Shot property, or is its omission an intentional interface simplification?
- **InfinityDB:** Retains the source-specific notation and linked rules, rather than mutating Army fields.

### SRC-017 — AP Thunderbolt Wiki weapon-chart conflict

- **Status:** open — correction requested.
- **Evidence:** Verified N5.3 printed chart and pinned Army AP Thunderbolt profile conflict with current archived English and Spanish Wiki weapon-chart rows. [Source assessment](rules-explanation-audit-1.0.md) and [publisher-correction TODO](TODO.md).
- **Question:** Can the AP Thunderbolt English and Spanish Wiki entries be aligned with the current official printed and Army profile, or is a newer intentional weapon revision missing from those sources?
- **InfinityDB:** Keeps selected source-backed weapon semantics and the source discrepancy.

### SRC-018 — AP + EXP CC Weapon Spanish Wiki Saving Roll count

- **Status:** open — correction requested.
- **Evidence:** N5.3 English p. 177 and Spanish p. 184, plus pinned Army weapon 227, give three ARM/2 rolls for AP+EXP; archived Spanish Wiki chart gives two. [Rules interaction evidence](rules-interaction-checklist.md).
- **Question:** Should the Spanish Wiki row be corrected from two Saving Rolls to the three in both PDFs and Army?
- **InfinityDB:** Uses the three-roll PDF/Army result and preserves the contradictory published row.

### SRC-019 — Stun Pistol Spanish Wiki chart

- **Status:** open — correction requested.
- **Evidence:** Reviewed Spanish Wiki Stun Pistol chart differs from the aligned N5.3 PDF and pinned Army weapon profile. [Source assessment](rules-explanation-audit-1.0.md).
- **Question:** Which Stun Pistol profile is authoritative for N5.3, and should the Spanish Wiki chart be corrected to match the current PDF/Army data?
- **InfinityDB:** Publishes its reviewed primary-source result and retains the Wiki discrepancy.

### SRC-020 — Flash Pulse Spanish Wiki state and Saving Roll

- **Status:** open — correction requested. **Alias:** REA-027.
- **Evidence:** Spanish Wiki weapon-chart revisions 3987/3988 give two PB/BTS rolls without State: Stunned; English/Spanish N5.3 PDFs and pinned Army weapon 72 specify one PB/BTS roll, Non-Lethal and Stunned. [Exact revision audit](rules-explanation-audit-1.0-sources.md).
- **Question:** Should the Spanish Wiki Flash Pulse row show one Saving Roll and `State: Stunned` as in the N5.3 PDFs and Army?
- **InfinityDB:** Uses one roll and the Stunned outcome; keeps the discrepant historical revisions as evidence.

### SRC-021 — Kobra Pistol CC Anti-materiel and DA roll-count discrepancies

- **Status:** open — correction requested / ruling needed. **Alias:** REA-028.
- **Evidence:** The September 2026 N5.3 update changed Kobra Pistol CC ammunition to DA; generic DA (N5.3 p. 64) requires two Saving Rolls but some printed CC chart cells (pp. 68/182) say one. Pinned Army/current Wiki say two and also show `Anti-materiel` for CC, which the bilingual PDFs omit. BS and CC modes share Army weapon source 221. [History and update evidence](n5-source-history.md).
- **Questions:** (1) Should the printed Kobra CC chart list two DA Saving Rolls? (2) Does **CC mode specifically** have Anti-materiel, and should that Trait be added to the PDFs or removed from Army/Wiki?
- **InfinityDB:** Correctly applies DA's two rolls; treats Anti-materiel as a separate unresolved, mode-specific source conflict.

## Open questions: scenarios and published examples

### SRC-022 — Domination 350-point SWC: English 6 versus Spanish 7

- **Status:** open — ruling needed / correction requested.
- **Evidence:** English N5.3 p. 151, N5.2 p. 150 and archived English Wiki print **6 SWC** at 350 points; official Spanish N5.3 p. 155 prints **7 CAP/SWC** for the identical Domination size. [Scenario model](data-model.md#scenario-model-implemented-core-and-future-extensions).
- **Question:** For a 350-point Core Domination game, is the intended SWC allowance 6 or 7? Which language/source should be corrected?
- **InfinityDB:** Retains 6 from the English source, with a visible `needs-verification` issue rather than silently selecting an erratum.

### SRC-023 — Annihilation 350-point surviving-VP boundaries

- **Status:** open — correction requested; **locally reconciled**.
- **Evidence:** English N5.3 p. 149 prints 85–150 / 176–270 / more than 250 for the surviving-VP scoring bands, leaving a gap and overlap. Spanish N5.3 p. 153 instead prints consistent 85–175 / 176–270 / more than 270. [Reviewed reasoning](rules-semantics.md#rs-scn-ann-001--resolve-the-n53-annihilation-350-point-survival-typo).
- **Question:** Can the English Annihilation 350-point surviving-VP table be corrected to the Spanish 85–175, 176–270 and over-270 bands?
- **InfinityDB:** Uses the independently corroborated Spanish bands and retains the English source-note discrepancy. The *mechanic* is locally resolved; official English publication correction remains open.

### SRC-024 — Army Pheroware retains superseded Technical Weapon terminology

- **Status:** open — correction requested; **mechanics locally resolved**.
- **Evidence:** Corvus Belli's [April 2025 N5 rules update](https://infinityuniverse.com/en/news/infinity-n5-rules-update) explicitly replaces `Technical Weapon` in the Pheroware chart with `BS Weapon (WIP)`. The N5.3 PDF and reviewed Wiki adopt the new term, while pinned Army program/weapon properties retain the historical N4 label. N4 v1.1 p. 43 had defined `Technical Weapon` as using WIP instead of BS. [Verified terminology provenance](n5-source-history.md#n4-terminology-provenance-and-n5-chart-reference-legend).
- **Question:** Should the N5 Army Pheroware weapon/program properties be updated to `BS Weapon (WIP)` to match the explicit N5 update, or is the older label intentionally retained as an interface alias?
- **InfinityDB:** Uses current N5 mechanics and identifies the imported older terminology rather than treating it as a new category or additional rule.

### SRC-025 — Stealth FAQ question scope differs by language

- **Status:** open — source intent unknown; **answers not contradictory**.
- **Evidence:** English N5 FAQ v0.0/v0.1 asks generally about targeting a Stealth user during multiple activations generating AROs; Spanish v0.1 p. 2 expressly frames the question with the Stealth user **outside** the reactive Trooper's Zone of Control or Hacking Area. Both answers give Idle if the active Trooper declares no ARO-enabling Skill. [Bilingual FAQ scope audit](faq-v0.1-scope-inventory.md).
- **Question:** Is the Stealth FAQ intended to address only the stated outside-ZoC/Hacking-Area situation, or should the same answer be applied more broadly under the other usual ARO requirements?
- **InfinityDB:** Retains the English answer with its ordinary rule dependencies; the narrower Spanish question is evidence of a context difference, not a second ruling or automatic general permission.

### SRC-026 — FAQ Deployable wording: firing versus placing

- **Status:** open — source intent unknown; **answers currently consistent**.
- **Evidence:** English N5 FAQ v0.1 asks about **firing a Deployable**, while the Spanish v0.1 asks about **placing Deployables**; both reject the disputed vertical placement. [Bilingual nine-answer review](faq-v0.1-scope-inventory.md).
- **Question:** Is the vertical-position restriction intended for both a Deployable weapon fired into position and a Deployable object placed by a Skill, or only the context literally described by each language?
- **InfinityDB:** Preserves the selected English citation and the actual common answer; does not promote differing question wording into contradictory gameplay answers.

## Intake / future publisher correspondence

When a new candidate is found, add a new numbered section using this compact checklist. Keep the record **even if locally resolved** until official source status is documented.

- **SRC-next — Short descriptive name**
  - **Status:** open — ruling needed / correction requested / source intent unknown; add known REA/ARMY aliases.
  - **Evidence:** precise publication, language, edition, version/revision, page or Army source ID, and conflicting values; links to existing maintained investigations. Explicitly distinguish observations from assumptions.
  - **Question:** a neutral, actionable question with the exact gameplay/profile/scenario boundary.
  - **InfinityDB:** current adopted behavior or unresolved handling; whether players already see the discrepancy.
  - **Official response (later):** date, named source or correspondence reference, answer, affected editions and scope; resulting code/data/test tasks.

**Submission log:** None. No request has been sent or approval to contact the publisher inferred. Maintain source URLs and archived evidence references here, but store any private correspondence and contact details in ignored `local/` until approved for public release.
