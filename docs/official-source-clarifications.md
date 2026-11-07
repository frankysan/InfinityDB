# Official source clarification register

**Project domain:** Data processing
**Maintained owner:** This is the canonical register of known Infinity rules, Army, Wiki, FAQ and scenario-source ambiguities, inconsistencies, and potential official corrections.
**Last reviewed:** 2026-11-05
**Publisher contact:** Not submitted. The entries are *candidate questions*, not claims that Corvus Belli has ruled on them.

## Purpose and maintenance contract

This register collects questions that may eventually be sent to Corvus Belli for clarification, correction or publication harmonization. It records disagreements **between official sources**, **within a single official source**, or **in scope/applicability left genuinely indeterminate** after source review. It also retains locally reconciled publication mistakes until an official correction is confirmed. It is *not* a list of implementation bugs or a substitute for rules curation. Open SRC entries **do not block v1.0 by themselves**: source-aware player disclosure remains mandatory, but obtaining a publisher ruling does not. Confirmed InfinityDB defects and misleading presentation are separate release blockers under [the release gate](releasing.md#version-10-data-completeness-gate).

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

### SRC-027 — Journalist (+3) on Tohaa Diplomatic Delegate option

- **Status:** open — source intent unknown. **Alias:** Army Skill source `272`, extra `1/TEXT:+3`.
- **Evidence:** Pinned N5 Army `801-tohaa.json`, TOHAA DIPLOMATIC DELEGATES, unit 658, DIPLOMATIC option 3, occurrence 68471, includes the sole `Journalist (+3)` annotation among **93** direct Journalist occurrences. The N5.3 English rules p. 99 (reviewed Wiki Journalist `oldid=4086`) already assign **+3 allied / -3 enemy Guts Roll MODs** within Zone of Control and separate campaign-only **+3 CUBEVAC / Promotion** bonuses, with non-stacking restrictions; they do not define a profile-specific `Journalist (+3)` variant or extra skill use. A [February 2025 community discussion](https://forum.corvusbelli.com/threads/does-the-journalist-l1-3-apply-to-objective-rolls-in-its-16.43426/) identified the same Tohaa annotation and rejected an inferred ITS objective-roll bonus, but contains **no official ruling**. Historic profile sources still display `Journalist L1 (+3)`; this suggests possible legacy labeling, not established publisher intent.
- **Question:** Is the Tohaa Diplomatic Delegate's `Journalist (+3)` notation a legacy display artifact to be removed, or does it grant a rule effect beyond Journalist's printed N5.3 Guts/CUBEVAC/Promotion MODs? If it grants another effect, specify its roll, targets, condition, and stacking behavior; does any of it apply to ITS objective interactions?
- **InfinityDB:** V1S-059's source review is complete (2026-11-04): the pinned raw-source audit reconfirmed the sole `1/TEXT:+3` extra at occurrence 68471 among 93 Journalist rows, and N5.3 p. 99 gives no profile-specific modifier. **No typed extra effect is justified.** Keep the literal Army option qualifier unresolved and the existing N5.3 Journalist family effects published exactly once, without another Guts/campaign bonus, objective modifier, or general Attribute MOD. The raw-source regression guards the exact owner and fail-closed classification; await official correction or clarification.

### SRC-028 — Confessor Heavy Spec-Ops: Terrain (Total) apparently attached to Religious Troop

- **Status:** open — correction requested; **likely upstream field-assignment mistake, not a new game rule**. **Alias:** Army Skill source 83 / extra `33/TEXT:Total` on unit 1927.
- **Evidence:** Pinned Army `103-military-orders.json`, revision `7.26246.158`, in snapshots dated 2026-09-10, 2026-09-25 and 2026-09-29, has one Confessor Heavy Spec-Ops profile in CONFESSOR TEAM OPS (unit 1927, group 2, profile 1) with unqualified Terrain (source 58) followed by `Religious Troop (Total)` (source 83, extra 33; raw occurrence 5240). The *same* unit's Confessor-1 light profile has `Terrain (Total)` and unqualified Religious Troop, and its Blueberry SpecBot also has `Terrain (Total)`. The separate CONFESSOR SPEC-OPS unit (1913) has `Terrain (Total)` and unqualified Religious Troop on both Initial/Enhanced profiles. Across the pinned Army source, extra 33 qualifies **918** Terrain occurrences but only this **one** Religious Troop occurrence among **498** direct Religious Troop rows. The reviewed Religious Troop definition has no `Total` variant.
- **Question:** Was extra 33 (`Total`) mistakenly assigned to the Religious Troop entry rather than the preceding Terrain entry on CONFESSOR HEAVY SPEC-OPS, and should that profile be corrected to `Terrain (Total)` plus ordinary `Religious Troop`?
- **InfinityDB:** The V1S-053 raw-profile review is complete (2026-11-04): the pinned source audit reconfirmed 498 Religious Troop occurrences, exactly one `33/TEXT:Total` qualifier on occurrence 5240, and the existing comparator regression. Preserve that literal Army extra as an **unreviewed occurrence parameter** without creating a Religious Troop variant, transferring the extra in stored imported data, or granting additional Religious Troop effects. `Terrain (Total)` remains a strongly supported **proposed source correction**, not a publisher-confirmed erratum. SRC-028 stays open for upstream correction.

### SRC-029 — Doctor/Engineer (ReRoll -3) lacks explicit N5 WIP scope

- **Status:** open — source intent unknown; **not** an established rules contradiction. **Alias:** Army Skill sources `49` (Engineer) and `53` (Doctor), extra `366/TEXT:ReRoll -3`.
- **Evidence:** Pinned September 29 Army source has **six** Engineer `ReRoll -3` profile occurrences (Sophotects and Chief Mech-Engineer Chung-Hee Jeong, including Reinforcement profiles), alongside **three** Doctor `ReRoll -3` profile occurrences (Bipandra). The N5.3 English rules, pp. **90–91**, describe `Doctor (ReRoll WIP=X)` and `Engineer (ReRoll WIP=X)` as failed Skill Roll rerolls using an *explicit bracketed WIP value*, with the later Command Token reroll excluded from the Skill-specific replacement. The Army `ReRoll -3` string instead supplies a signed `-3`, not an explicit `WIP=X` value. The 2026-09-29 Army Engineer inventory has 389 direct occurrences and 15 qualified ones; the sole `ReRoll -3` signature is source extra 366. The [official Engineer Wiki](https://infinitythewiki.com/Engineers), reviewed 2026-11-05, retains a **historical original** `Engineer (ReRoll -X)` passage prescribing a negative WIP MOD and marks the `ReRoll WIP=X` rewrite as the **PDF 5.2 October 2025** update. This supports a plausible *legacy-notation origin*, not permission to reapply the superseded rule to current N5.3 Army qualifiers. The newer edition's exact intent still needs correction or clarification.
- **Question:** Does the Army `ReRoll -3` notation mean the Engineer/Doctor reroll is made at the Trooper's ordinary WIP with a -3 MOD, an alternative fixed WIP value, or another defined effect? Does it apply only to the Skill-granted reroll, and does the N5.3 Command Token exception continue to exclude it?
- **InfinityDB:** Preserve the literal `366/TEXT:ReRoll -3` source qualifier, retain the separately reviewed base Doctor/Engineer mechanics, and leave the specific occurrence parameter unreviewed. Do not transform `-3` into a fixed replacement WIP, a blanket WIP MOD, or an additional reroll until its exact scope is supported.

### SRC-030 — Which Reinforcements Annex procedures govern optional N5 games?

- **Status:** open — source intent unknown. **Aliases:** optional Reinforcements Extra / RS-RF-SECTION-001, RS-RF-COMM-001 and RS-RF-REQ-001.
- **Evidence:** The pinned English N5.3 Core Rules p. 6 includes games with Reinforcements, and ITS Season 18 (v2026.09.01, p. 27) explicitly offers the Reinforcements Extra and refers to an Annex. However, the [official live Wiki Annex](https://infinitythewiki.com/Infinity_Reinforcements) still labels its detailed instructions as originating in **N4**; the [official English Annex PDF](https://downloads.corvusbelli.com/infinity/rules/reinforcement-rules-en.pdf) is likewise the earlier edition. The September 29 N5 Army snapshot still supplies Section pools and Commlink (+1)/(+2) occurrences, but those facts do not independently establish the applicable N5 procedural text. A public official-source search on 2026-11-03 did not establish a separately versioned N5 Annex or an explicit adoption notice; absence from that search is **not** proof no such publication exists. See [reviewed semantics](rules-semantics.md#rs-rf-section-001--reinforcement-eligibility-is-army-list-sectionoccurrence-context) and [current implementation](TODO.md#100--current-reference-completeness-gate).
- **Question:** For optional Reinforcements Extra play in N5, including ITS Season 18 where selected, which **Annex edition and effective date** governs? Are the N4-origin Main/Reinforcement Section construction rules (including the 100-point/2-SWC allocation), Commlink maximum-Trooper-count bonuses, Request Reinforcements timing and deployment procedure all adopted unchanged, or are there N5-specific replacements or exceptions? Please identify the authoritative document or ruling for any changes.
- **InfinityDB:** Publishes a separately labelled **N4-origin optional reference** with explicitly scoped Commlink (+1)/(+2) source semantics, Section/parent Army navigation and source citations. It does **not** present the historical procedures as an independently verified N5 rewrite or perform roster-legality calculations. The clearly disclosed optional reference is usable for agreed play while source adoption remains unresolved.

### SRC-031 — Lieutenant Order Count: English double-negative versus Spanish non-Null

- **Status:** open — correction requested; **probable English copy error, not a new gameplay exception**. **Alias:** V1S-032B Game Sequence source review.
- **Evidence:** In the pinned N5.3 English Core PDF **p. 17**, Order Count / Lieutenant Special Order, the eligibility clause for an on-table Lieutenant literally says `not in a non-Null State`. The corresponding Spanish N5.3 Core PDF **p. 17** says `Teniente en estado no Nulo` (non-Null), consistent with English/Spanish Order Count Regular/Tactical Order clauses on p. 17, English Order Pool p. 12 and Loss of Lieutenant p. 18. The English double negative would misleadingly require a Null State if read literally. This is a bilingual printed-wording inconsistency, not evidence of a distinct Lieutenant exception; no publisher correction is confirmed by this review.
- **Question:** Should N5.3 English p. 17 Lieutenant Special Order / Order Count say that the deployed Lieutenant **is not in a Null State**, matching the Spanish rule and the surrounding Order generation rules? Please identify any intended exception if the English double negative is deliberate.
- **InfinityDB:** Preserve both exact source phrases as conflicting provenance. Use the corroborated **deployed, non-Null Lieutenant** requirement in the published Game Sequence reference, with source-version disclosure rather than silently following the inverted English sentence. Do not grant Orders to Null Lieutenants or generalize the proposed copy correction into an official ruling. Source-pinned bilingual regression: `tests/test_phase_source_review.py`.

### SRC-032 — CC Attack (+1 Dam) on current Reinforcement profiles

- **Status:** open — source intent unknown. **Alias:** Skill source 240 / extra `4/TEXT:+1 Dam`; V1S-056.
- **Evidence:** Pinned September 29, 2026 Army raw source lists precisely two `CC Attack (+1 Dam)` direct occurrences: REINF: SHONA CARANO, Special Instructor and Aristeia! Swordmaster, unit 1639, source profile occurrence 13859 (Code: Capital / Army 199), and REINF: CHAKSA AUXILIARS, unit 1675, occurrence 69477 (Deras kaar / Army 899). Both are profile-owned, not Army-wide effects. English N5.3 p. 37 defines Possibility of Survival (PS) and notes that *lower* numerical PS is more lethal; pp. 51–52 describe CC Attack, and p. 75 explains modern Skill modifier notation but never defines `+1 Dam`. These sources do not establish a translation between legacy Damage notation and current PS or an additional-Wounds effect. See the [bounded V1S-056 review](v1.0-source-coverage-audit.md#cc-attack-source-240-occurrence-review-v1s-056-2026-11-04).
- **Question:** In the N5 Army profiles for these two Reinforcements, what exactly does `CC Attack (+1 Dam)` change under N5 rules: weapon PS (and, if so, in which numerical direction), Wounds inflicted, another attack statistic, or only an obsolete display string? Is there an official updated notation for both occurrences?
- **InfinityDB:** Preserve the literal raw qualifier and its exact source owners, but do not turn it into a positive numerical PS adjustment, a negative PS adjustment or additional Wounds without authority. No global CC Attack modifier, Weapon override or proposed gameplay ruling is published. The exact owner/signature boundary is guarded by `tests/test_audit_source_variant_inputs.py::test_cc_attack_source_240_exact_signatures_and_damage_owners`.

### SRC-033 — Infiltration (ReRoll) without the rulebook's PH=X parameter

- **Status:** open — source intent unknown; **not** an established permission to use an unspecified replacement PH. **Alias:** V1S-050 / Army Skill source `47`, extra `277/TEXT:ReRoll`.
- **Evidence:** In the pinned September 29, 2026 Army source, **216** direct Infiltration occurrences comprise **17** occurrences with five explicitly reviewed `PH=X` values, **five** bare `ReRoll` occurrences and **194** unqualified instances. The five bare extras are profile-owned: CORREGIDOR BANDITS unit 400, occurrences **44546** (Corregidor/Army 502) and **74177** (StarCo/905); DASYUS unit 587, occurrences **61511** (ALEPH/701) and **65105** (OSS/703); and REINF: DASYUS unit 1727, occurrence **67248** (Ank Program/799). Each has the sole source extra `277/TEXT:ReRoll` with **no PH=X**. N5.3 English p. **97** defines the specific Infiltration reroll as `ReRoll PH=X`, applying the named PH to the **PH-3** Roll and accepting the second result; Spanish N5.3 p. **97** likewise requires `ReRoll FIS=X`. English N5.3 pp. **68, 75** independently allow a generic bracketed `ReRoll` to reroll one die when using the named Skill. The [official Infiltration Wiki](https://infinitythewiki.com/Infiltration) retains the explicit `PH=X` form; the pinned English FAQ v0.1 provides no rule resolving this notation mismatch. The generic and Skill-specific texts therefore leave the intended bare-Infiltration reroll parameter/application unclear, without proving an upstream mistake.
- **Question:** Is the Army `Infiltration (ReRoll)` notation for Bandits/Dasyus intended to use the general one-die `ReRoll` modifier on the Trooper's ordinary PH-3 Infiltration Roll, or is it an incomplete `Infiltration (ReRoll PH=X)` entry? If it requires `X`, what exact PH applies to these profiles? Does the player have to accept the second Roll?
- **InfinityDB:** Preserve all five source-owned `277/TEXT:ReRoll` qualifiers without a typed gameplay effect, while retaining the five separately reviewed fixed-PH values (**17** occurrences). Do not invent a replacement PH, silently assume generic reroll precedence over the specific Infiltration wording, or change the Unit's PH. V1S-050's exact owner and negative-typing regressions guard this boundary; the source/season decision remains open until a verified official correction or clarification.

### SRC-034 — Engineer contact requirement omitted from Spanish N5.3 PDF

- **Status:** open — possible language-edition omission; no alternate rule or intent established. **Alias:** V1S-082 pilot.
- **Evidence:** `data/pdf/rules/n5-rules-v5.3-en.pdf` (SHA-256 `53921e91c2d3d62ad5f7125abcd4174b2cf937d45320233eed5b6d301b66af3f`), p. **91**, explicitly requires Silhouette contact for Engineer. `data/pdf/rules/n5-rules-v5.3-es.pdf` (SHA-256 `7f564c864c6f26d6b218a0477c8afeba99da5c56e1a5369bb259f423689bb28f`), p. **98**, has no such requirement in the Ingeniero Requirements section; the page layout was visually checked. English Wiki revision **3980** (2025-10-31, `data/wiki/WIKI-en-history 20260928-165727.zip::_history/oldid/3980.html`, SHA-256 `1b865c651eacfb12e96d413d1d3048ca9e4b1696507b6d1cf9712401ddbf348e`) and Spanish Wiki revision **3823** (2025-11-26, current capture `data/wiki/WIKI-es 20261009-211304.zip::es/Ingeniero`, SHA-256 `fcb061fb360efd1fde552a56583a5e1ceb35313f950bd8f6d91f4574a810a8d2`; exact history member in `data/wiki/WIKI-es-history 20261009-215316.zip`, SHA-256 `063b05c98db95867f8a1f6535a5c9aa376fc6fea048477fd81afe517fd702029`) both include contact. Those Wiki revisions predate the v5.3 PDFs and do not resolve the same-version PDF difference. The current curated/generated `skill:engineer` record retains the English-backed requirement and does not cite the Spanish PDF. No FAQ citation was selected for this record.
- **Question:** Is the missing contact requirement on Spanish N5.3 p. 98 an editorial omission, and should the Spanish v5.3 rule require the same Silhouette contact as English p. 91? Please clarify or correct the Spanish publication.
- **InfinityDB:** Retain the English-backed contact requirement without inferring that Spanish permits remote use or silently dropping the condition. Keep this language-edition discrepancy unresolved; do not change gameplay semantics until an authoritative correction or clarification is available.

## Intake / future publisher correspondence

When a new candidate is found, add a new numbered section using this compact checklist. Keep the record **even if locally resolved** until official source status is documented.

- **SRC-next — Short descriptive name**
  - **Status:** open — ruling needed / correction requested / source intent unknown; add known REA/ARMY aliases.
  - **Evidence:** precise publication, language, edition, version/revision, page or Army source ID, and conflicting values; links to existing maintained investigations. Explicitly distinguish observations from assumptions.
  - **Question:** a neutral, actionable question with the exact gameplay/profile/scenario boundary.
  - **InfinityDB:** current adopted behavior or unresolved handling; whether players already see the discrepancy.
  - **Official response (later):** date, named source or correspondence reference, answer, affected editions and scope; resulting code/data/test tasks.

**Submission log:** None. No request has been sent or approval to contact the publisher inferred. Maintain source URLs and archived evidence references here, but store any private correspondence and contact details in ignored `local/` until approved for public release.
