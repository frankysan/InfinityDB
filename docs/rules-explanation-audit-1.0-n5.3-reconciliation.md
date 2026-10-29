# Rules explanation audit 1.0: N5.3 reconciliation

**Project domains:** Acquisition, Data processing, Web backend, Web frontend

This follow-up appendix belongs to the [audit](rules-explanation-audit-1.0.md).
Source identifiers and exact artifact hashes are in the
[provenance manifest](rules-explanation-audit-1.0-sources.md).
Research date: 2026-10-09; examined commit
`c5400ab1b950990fdacc509be91c110fe85431fb`. Supplementary Spanish PDF
(S17) and Wiki history (S21) verification on 2026-10-09 updates the evidence
without changing rule/data implementations.

**Historical assessment:** The comparison tables and their status totals describe
that examined baseline, with explicitly dated follow-ups below. They are not a
current defects list: many listed explanations and references have since been
published. Use [TODO](TODO.md#rules-and-reference-completeness) for remaining
work and the canonical data/semantic documents for current behavior. Preserve
the original source identities, counts and unresolved disagreements rather than
reclassifying historical rows as current approvals.

## Current reconciliation inventory (2026-10-29)

This section is a **current disposition overlay**, not a revision to the
2026-10-09 comparison or its fixed denominators. It reconciles the English
notice's 26 numbered rule changes, the four additional Spanish-only subjects,
20 separate Army changes and nine added FAQ rulings. A completed *selected
change* is not whole-record, cross-source, or release-browser acceptance.
The owning 1.0 work and release criteria remain in
[TODO](TODO.md#source-inventory-and-gap-batches) and
[releasing](releasing.md#version-10-data-completeness-gate).

### English rules changelog: 26 subjects

- **12 source-backed changes rechecked or clarified in current maintained
  data:** N53-03 (Berserk/Prone), N53-06 (Firewall),
  N53-10 (PARA CC weapon MOD versus ammunition save), N53-13
  (Impetuous/Prone), N53-14 (Minelayer), N53-15 (Cyberplug),
  N53-16 (Protheion), N53-19 (Deployable Cover), N53-21
  (Peripheral/Fireteam Integrity), N53-22 (Camouflaged ARO declarations),
  N53-24 (five Null States), N53-25 (Breaker Marksman publication).
  Some needed only a regression or a verified *no-data-change* result.
  These are the focused N5.3 items documented in TODO, not a claim of
  full-source acceptance. In particular, N53-03 still has a shorter
  contradictory/omissive Prone summary in the source itself.
- **9 selected rule clauses verified at the original audit baseline:**
  N53-04 (Climb/Cover), N53-08 (Trench-Hammer), N53-11
  (Speedball PH), N53-12 (Aerial/Boost), N53-17 (Strategos L2),
  N53-18 (Super-Jump distance), N53-20 (Hacking Device category),
  N53-23 (IMM-B Hacking example) and N53-26 (Thunderbolt grouping).
  Carry their original *selected-clause* scope forward; do not infer
  complete records, rules interactions or browser verification.
- **2 current implementations locally accepted, hosted release still pending:**
  N53-05 (Guts geometry) and N53-02 (Spec-Ops/SpecBall).
  The maintained `rule:guts-roll` evaluates Line of Fire only from
  the positions where attackers actually attacked (N5.3 p. 38)
  and sends an already-outside Trooper Prone on a failed Guts Roll.
  Both a fresh curated export and the tracked rules database pass
  the public API regression. The ordinary Guts reference card
  passes Chromium checks at 1440/390/320 px for the exact geometry,
  fallback, Prone link, citation and layout. This closes the
  **bounded local publication check**, not general Guts adjudication
  or hosted release-candidate acceptance. N53-02's core N5.3 p. 98
  `skill:infinity-spec-ops` and `skill:request-specball` procedure
  is **already published**, with pickup, placement, once-per-game
  and Initial/Enhanced Profile transition effects. Its Combat Jump,
  Speedball distinction, source discrepancy and ITS Season 18
  TEAM-OPS boundary are explicit. Historical 2026-10-14 responsive
  browser acceptance passed 24/24 checks; the current API/route
  regression confirms the two Skills remain accessible. The
  **Spec-Ops and SpecBall choice charts** have now been traced to
  the pinned September 29 Army snapshot: 30 distinct source Units,
  split into 15 Spec-Ops and 15 TEAM-OPS. Both kinds contain a
  four-option SpecBall list; their own selection tables contain eight
  and ten entries respectively. Options can contain multiple source
  attributes, so they cannot be flattened or treated as a configured
  Unit. The existing `logical_unit_spectables` store preserves the
  payloads exactly; a source-archive/database parity regression
  verifies all 30. The Unit API and ordinary Unit page now expose
  the choice charts with source Unit/version provenance, resolved
  catalog names and routes, preserved option groupings, and raw
  source-notation values for ambiguous modifiers. A focused
  Chromium test covers desktop/mobile presentation and links.
  Final hosted release acceptance remains open. The interactive
  list/session configurator is still deferred, not part of the
  read-only reference contract. See the scoped
  [TODO](TODO.md#source-inventory-and-gap-batches).
- **2 changes with disclosed official-source disagreements:**
  N53-07 (Kobra CC) preserves a proven DA two-save correction and an
  unresolved Anti-materiel disagreement between Army/Wiki and both PDFs.
  N53-09 (Dodge ARM+3) presents the bilingual PDF reading and discloses
  the contradictory English/Spanish Wiki notes. An external publisher
  ruling is not required for release *if* the selected behavior,
  conflicting sources and uncertainty remain clearly available.
- **1 not applicable:** N53-01 is editorial blue-annotation guidance,
  not a missing player-facing gameplay identity.

The 12 + 9 + 2 + 2 + 1 grouping accounts for all **26 English items**;
it is **not** a replacement for the historical 9/12/4/1 source-assessment
counts above.

### Additional Spanish, Army and FAQ subjects

- **ESX-01 to ESX-04 (four items):** retain the historical partially
  verified boundaries. ESX-01 (Stealth) is **locally accepted for
  current-rule publication**: English p. 112 and Spanish p. 114 agree
  on LoF-dependent reactions to Cautious Movement, Idle and Basic
  Short Movement, Combat Instinct/Sixth Sense and Deployable
  exceptions, and the CC Attack/Dodge/Reset/Engaged-usable choices
  after Silhouette contact. The already maintained Skill covers
  the main scope and FAQ mixed activation; its explicit contact
  choices now appear in the owner card and pass bilingual current-PDF,
  curated and 1440/390/320 px Chromium checks. ESX-02 (Jet
  Propulsion) is also **locally accepted for current-rule publication**:
  English N5.2 p. 112 has the older before-landing text, English
  N5.3 p. 113 explicitly permits repeated changes of direction and
  heading in mid-air, and Spanish N5.3 pp. 116-117 keeps less
  explicit wording but shows freely varied trajectories. The
  maintained `skill:super-jump` card now makes the repeated-change
  permission specific to the Jet Propulsion variant, with a
  bilingual source-context note, citation, and focused source/browser
  regressions. No general Super-Jump distance, declaration type, or
  once-per-Order permission changed. ESX-03 (MSV3 disclosure/turn
  scope) is **locally accepted for current-rule publication**:
  English N5.3 p. 125 and Spanish p. 131 restrict attack-without-
  Discover to the user's Active Turn; the English rule retains
  ordinary Camouflaged cancellation, while Spanish clarifies the
  attack does not itself reveal the target to the rest of the army.
  The maintained Level 3 owner distinguishes the attacking user's
  exception from ordinary State cancellation (pp. 158/163) and
  retains Mimetism, LoF, and source-language qualifications.
  Pinned source tests and 1440/390/320 px Chromium checks pass;
  do not infer a Reactive-Turn bypass or blanket Marker immunity.
  ESX-04 (AP+T2 CC Anti-materiel) is likewise **locally accepted
  for current-rule publication**: English N5.3 p. 177 and Spanish
  p. 184 agree on PS 8, B1, AP+T2, one ARM/2 Saving Roll, and
  Anti-materiel plus CC. The existing published weapon profile,
  `weapon-property:ap-t2`, and AP/T2 Ammunition references already
  retain the printed facts. Bilingual source/API checks and
  1440/390/320 px Chromium weapon-page acceptance pass; no
  production-data edit or extra Saving Roll was warranted.
  All four ESX subjects now have **current-rule local acceptance**.
  The absent *earlier* Spanish PDF still prevents a proven Spanish
  historical before/after delta **for all four items**, and hosted
  release acceptance remains separate. Do not infer historical
  equivalence or unrestricted Super-Jump distance.
- **ARMY-01 to ARMY-20 (20 items):** the current post-notice
  snapshot and selected identities were inspected in the original
  audit, but no pinned pre-notice Army snapshot was available.
  All 20 **historical** dispositions therefore remain *partially
  verified*. A current-only snapshot supports present-state
  publication checks, not a claim about what changed. Selected
  **ARMY-02–16** source-pair chart coverage is now locally accepted:
  the pinned September 29 ZIP, built database and public Unit API
  agree on all **30** distinct source Unit identities (15 Spec-Ops
  and 15 TEAM-OPS) and their full grouped choice payloads. Every
  source chart preserves version/file provenance, source order,
  eight Spec-Ops or ten TEAM-OPS selection options and four
  separate SpecBall choices. All 30 ordinary Unit pages pass
  Chromium at 1440/390/320 px (90 page/viewport checks) for
  chart counts, source IDs, links and horizontal overflow.

  Shared-source membership is preserved rather than inferred:
  Treitak Spec-Ops (1919) occurs in Combined Army and Morat, while
  Morat TEAM-OPS (1933) is Morat-specific; Chandra and ALEPH
  TEAM-OPS occur in three ALEPH source members, all `7.26246.159`.
  Ŝtormo (1923/1937) occurs in O-12, Starmada and Torchlight
  Brigade; Kaizoku (1924/1938) in JSA, Shindenbutai and Ōban.
  Rumbler Spec-Ops (1925) appears in six NA2 members (umbrella
  plus Druze, Ikari, StarCo, Dahshat and White Company), while
  NA2 TEAM-OPS (1939) appears in the five sectorials, not the
  umbrella member. Duplicated source-choice payloads agree.
  Hatail (1908/1909) is a separate Tohaa pair; its active/inactive
  Symbiont Armor profiles, like Intel's Full Power/Battle Ravaged
  profiles, are not interchangeable chart selections.

  **ARMY-17–20** now have **selected current-state local acceptance**
  independently of the Spec-Ops charts. Ioann Bann (#1940) retains
  Dogface/Dog-Warrior profiles and maximum-one Varangian Duo
  membership in both O-12 and Starmada source Fireteam charts;
  the Fireteam API and both ordinary chart pages agree. Najjarun
  (#314) exposes shared Deactivator (Equipment 238) across all
  three native loadouts in Haqqislam, Hassassin Bahram and Qapu
  Khalqi. Sāchā (#1874) exposes AVA 1 in four selected faction
  contexts spanning Army revisions `7.26246.158` and `.159`;
  its Unit page now has separate numeric-AVA acceptance: AVA 1
  is visible in each of the four Army profile sections through
  keyboard expansion and Army-specific links at 1440/390/320 px
  (15 page/viewport checks). It is not a General-profile Attribute.
  Racerbot (#1905) preserves
  both native Equipment 246 and legacy Skill 266 source provenance
  (Bangbomb extra 310) while publishing one deduplicated
  Equipment reference. Source/API tests and the four Unit pages
  pass Chromium at 1440/390/320 px; Ioann's two Fireteam chart
  pages pass at the same widths (18 page/viewport checks).
  No production-data changes were required.

  A subsequent **ARMY-01 current-state source/chart recheck**
  covers all 58 raw Army contexts and their 57 application chart
  contexts (including the empty grouping chart), 268 teams and
  1,249 member rows. Source hashes, ordered types, type limits,
  member bounds, required-choice flags and annotations match the
  public API. Contracted Back-up source contexts 998 and 999 have
  identical charts and share one application identity. All 56
  playable source-separated charts pass local Chromium checks
  at 1440/390/320 px (168 page/viewport cases) for visible limits,
  types, requirements, equivalence labels, chart/team notes and
  horizontal overflow. Rendered whitespace is normalized only for
  browser comparison; exact source text is preserved in the API.
  Private evidence is under `local/audits/army01-browser-20261029/`.
  The review
  also found and corrected combined-view Wildcard rows appearing
  under explicit `No Wildcards` observations in Invincible Army
  and Next Wave. Both charts and their Settings toggle now have
  local Chromium acceptance, including the separate-pool fallback.
  This does not approve arbitrary note interpretation or legality.

  These bounded checks do **not** approve every profile, option
  cost, faction availability, Fireteam chart, or historical Army
  delta. ARMY-01's unresolved member/FTO references, member-note
  interpretation, Reinforcement parent applicability and remaining
  ARMY-02–20 roster/profile semantics remain open; final hosted
  release-browser acceptance is separate. Keep unavailable
  pre-change evidence as a provenance limitation, not a
  present-state defect.
- **FAQ-01 to FAQ-09 (nine added rulings):** compared against v0.0
  and v0.1; this does not independently approve every affected
  owner page or applicability. FAQ-09's undeployed Ancillary
  *Killed* interpretation is explicitly under the ITS heading.
  Its application to core Annihilation/Firefight remains unproven:
  do not publish that scope without scenario-specific evidence.
  The FAQ v0.1 publication date is also not established.

### Remaining release gates (not counted as additional change items)

1. **Source and scope:** freeze the intended Army/rules/FAQ/Wiki
   input identities; record PDF hash/publication boundaries and
   any missing pre-change or N5 Reinforcements evidence. Resolve
   supported-current semantics first, disclose genuine source
   conflicts, and do not treat missing historical sources as
   confirmed implementation defects.
2. **Coverage:** complete the source-section-to-maintained-layer,
   API and ordinary browser inventory, including all four core
   scenarios and cross-references. The frozen 367-record audit and
   the 198/198 interaction checklist are bounded evidence, not a
   completeness certificate. Verify the remaining N53-02/05,
   ESX and relevant Army/FAQ source-to-player cases.
3. **Publication and acceptance:** regenerate the release-matched
   `infinity.db` / `rules.db` pair and dependent publications,
   check source occupancy and API/route consistency, run targeted
   regressions and the user/CI full checks, then perform final
   responsive and hosted release-browser acceptance. Prior local
   passes do not certify a future release candidate.

Keep this overlay updated as these gates close; retain the original
source comparison tables unchanged for provenance.

## Denominator and interpretation

The [English notice S11](https://infinityuniverse.com/en/news/infinity-rules-update-5-3)
dated September 1, 2026 contains **26** bullets under **N5.3 RULES CHANGELOG**
and **20** under **ARMY UPDATE CHANGELOG**. The
[Spanish notice S13](https://infinityuniverse.com/es/news/infinity-rules-update-5-3)
contains **30** rules bullets and the same 20 Army subjects. Four additional
subjects occur only in the Spanish list, including a change explicitly limited
to the English rulebook. The union is **30 rules change records**, not 26.

The tables give an exact heading/bullet locator for the original description;
short subject aliases avoid republishing the announcement. Read the linked
original bullet for its exact wording. Clause comparisons below derive from
S1/S3 PDFs, S2/S15 FAQs, S6 profiles and specified Wiki payloads, rather than
assuming a notice proves implementation. Compound bullets retain their original
denominator: N53-02 has two features; N53-25 has three weapons.

- **Verified:** the selected change and relevant current representation were
  compared successfully. It is not full-record or browser acceptance.
- **Partially verified:** some substantive evidence compared, with a specified
  remaining mechanics, provenance, explanation or historical-baseline gap.
- **Discrepancy:** inspected sources or represented claims disagree, or current
  source content is preserved but inaccessible. An incomplete explanation alone
  remains Partially verified. Neither status authorizes choosing an unresolved rule.
- **Not applicable:** editorial source notation does not require gameplay data.
- **Unverified:** no adequate clause/profile comparison. No item is silently
  promoted from name presence to Verified.

English 26: **9 Verified, 12 Partially verified, 4 Discrepancy, 1 Not applicable**.
Four additional Spanish subjects: **4 Partially verified**. Union 30:
**9 Verified, 16 Partially verified, 4 Discrepancy, 1 Not applicable, 0 Unverified**.
Army 20: **20 Partially verified**, separately. FAQ additions: **9 compared**,
eight outside ITS and one under ITS; not nine new core-rulebook amendments.

## English rules list

EN is the ordinal in S11's rules heading; ES is the matching S13 rules ordinal.
All page numbers are printed pages. A correct selected clause does not imply
that the rest of its card has adequate explanation; related gaps remain listed.

| ID / exact notice locator | Subject | Previous and current primary evidence | InfinityDB representation and player explanation | Finding / status / remaining question |
| --- | --- | --- | --- | --- |
| N53-01 / EN 1, ES 1 | Blue annotation | S1 cover explains blue additions/changes; S3 is the earlier edition | No gameplay identity required; this is source-reading guidance | Not applicable; preserve version identity, do not use color as a source citation |
| N53-02 / EN 2, ES 2 | Spec-Ops / SpecBall | S3 lacks these headings; S1 p. 98 adds the Skill and complete request/token procedure. S16 pp. 26, 28 separates ordinary Spec-Ops from TEAM-OPS | `skill:infinity-spec-ops` exists but request procedure is deferred, not adequately explained; Season 18 ordinary ban is supported only in that scope | REA-040; Partially verified; source existence verified, full procedure/reference missing; do not make TEAM-OPS permission universal |
| N53-03 / EN 3, ES 3 | Berserk / Prone | S3 p. 29 restricts Jump transitions; S1 p. 29 adds Berserk, but S1 p. 169's State summary still lists Jump alone | `skill:berserk`, `state:prone` need the operative transition exception together | REA-015/021; Discrepancy; retain internal summary omission, apply no blanket ban on all CC Skills |
| N53-04 / EN 4, ES 4 | Climb / Cover | S3 p. 32 emphasizes vertical surfaces; S1 pp. 32-33 applies denial while performing Climb/hanging; the new example ends horizontally without that Order's Cover | `skill:climb` correctly denies Cover during Climb; compare declaration context rather than only final orientation | Verified; selected change represented; complete geometry examples remain pending |
| N53-05 / EN 5, ES 5 | Guts geometry | S3 p. 38 uses end-position language; S1 p. 38 evaluates the positions from which attacks were made | General baseline lacks a complete linked Guts explanation; not established by incidental references on other cards | REA-026; Partially verified; publish conditions and movement choices before broad links |
| N53-06 / EN 6, ES 6 | Firewall category | S3 p. 55 says Equipment; S1 p. 55 says Automatic Equipment; S2 p. 1 ties Device benefit to being enabled | No adequate canonical Firewall owner; `skill:hacker`, Devices and Programs are insufficient substitutes | REA-018; Partially verified; category/source verified, contextual explanation missing |
| N53-07 / EN 7, ES 7 | Kobra modes | S3 p. 68 differs from S1 p. 68; S1 p. 182 visually shows BS SHOCK and CC DA, yet CC one-save/no Anti-materiel. S6 221 has CC two saves/Anti-materiel | `weapon:kobra-pistol` preserves mode distinction and source uncertainty; DA interpretation and Anti-materiel need separate decisions | REA-028/031; Discrepancy; do not equate resolving DA saves with settling Anti-materiel |
| N53-08 / EN 8, ES 8 | Trench-Hammer charges | S3 p. 68 has Disposable (3); S1 p. 68 and S6 177's BS/CC modes omit it | `weapon:trench-hammer` does not impose the old charge limit; selected modes agree | Verified; no new defect; full weapon/profile audit remains separate |
| N53-09 / EN 9, ES 9 | Dodge armor modifier | S1 and S17 p. 75 agree on the unconditional ARM/BLI +3 when the Dodge is declared; English Wiki 2026-09-26 and Spanish Wiki 2026-10-09 (S14/S21 revision 4012) both retain a failed-PH condition | Dodge now explains ARM Saving Roll +3 for profiles with this modifier; never +3 Dodge PH or all Dodges | REA-026/042; two-PDF versus two-Wiki-language conflict remains visible on the card; external source correction unresolved |
| N53-10 / EN 10, ES 10 | PARA profile modifier | S1 p. 75 distinguishes the opponent's Face-to-Face penalty from the PH-6 PARA Saving Roll | `ammunition:para`, `skill:dodge` and PARA-weapon profile context need that distinction in the common modifier reference | REA-026; Partially verified; selected rule checked, explanation missing; never apply the profile penalty to every save |
| N53-11 / EN 11, ES 11 | Speedball landing | S3 p. 84 PH 14 becomes S1 p. 84 PH 15; S2 retains Controlled Jump exclusion | `skill:request-speedball` has PH 15; landing clause correct | Verified; REA-007/026 separately retain FAQ context and uncompleted pickup/item lifecycle review |
| N53-12 / EN 12, ES 12 | Aerial / Boost | S3 p. 86 lacks the exception; S1 p. 86 explicitly excludes triggering Boost | `skill:aerial` and `trait:boost` explain the exception instead of inferring ordinary approach behavior | Verified; preserve positive explanation pattern |
| N53-13 / EN 13, ES 13 | Impetuous restriction | S1 p. 97 adds the end-of-Order Prone restriction to S3 p. 97's phase restrictions | `skill:impetuous` has phase-level restriction but no sufficient end-of-Order explanation alongside `state:prone` | REA-015; Partially verified; check scope of the added sentence, do not spread phase-only Cover restrictions to every Order |
| N53-14 / EN 14, ES 14 | Minelayer placement | S3 p. 101 versus S1 p. 102 expands the Perimeter check to Equipment as well as weapons | `skill:minelayer`'s generic placement explanation lacks the explicit enemy-in-area condition and profile exceptions | REA-023; Partially verified; do not infer a blanket Repeater ban without checking Perimeter/Indiscriminate applicability |
| N53-15 / EN 15, ES 15 | Cyberplug profiles | S3 p. 106 versus S1 p. 107: choose usable profile at Order/ARO start, at most one Connected Cyberplug | `skill:peripheral` subtype identity does not explain profile selection and delegated roll ownership | REA-017/038; Partially verified; coordinate with recovery and preserve delegation's explicit Allied condition |
| N53-16 / EN 16, ES 16 | Protheion MODs | S3 p. 108 versus S1 p. 109 explicitly applies opponent negative Face-to-Face MODs | `skill:protheion` omits this qualifier and overkill ceiling | REA-008; Partially verified; clause checked, usable conditional explanation pending |
| N53-17 / EN 17, ES 18 | Strategos L2 transfer | S3 p. 112 transfer wording versus S1 p. 113 includes Trooper and its Peripherals, consistently with L1 | `skill:strategos-l2` represents the transferred group including Peripherals | Verified; do not generalize to every Command Token transfer |
| N53-18 / EN 18, ES 20 | Super-Jump distance | S3 p. 112 bracket modifier versus S1 p. 113 limits its distance replacement to Short Skill Jump | `skill:super-jump` represents that limit, rather than doubling/replacing every movement distance | Verified; Jet Propulsion operation remains REA-032 and ESX-02 |
| N53-19 / EN 19, ES 21 | Deployable Cover properties | S3 p. 121 Disposable (1); S1 p. 122 Disposable (2), Perimeter and ZoC placement | `equipment:deployable-cover` correctly states ZoC but omits explicit Disposable (2)/Perimeter and the PS cap's operative value/condition; no named metadata profile was located to supply those properties | REA-023/036; Partially verified; current explanation incomplete, not contradicted; review property presentation together with the cap |
| N53-20 / EN 20, ES 22 | Device category | S3 p. 122 versus S1 p. 123 consistently labels listed Hacking Devices Automatic Equipment | Current Device summaries and Program table separation agree with that category | Verified; `skill:hacker` and Device context still depend on REA-018; this is not complete Hacking acceptance |
| N53-21 / EN 21, ES 24 | Peripheral / integrity | S3 p. 133 versus S1 p. 134 adds Controller departure rules; S1 p. 107 supplies Ancillary exception | `skill:peripheral`, subtype cards and `rule:fireteam-general` do not adequately explain common departure versus Ancillary | REA-017/020; Partially verified; explain member versus leader and subtype exceptions together |
| N53-22 / EN 22, ES 25 | Camouflaged AROs | S3 p. 156 versus S1 p. 157 changes restriction to declaration, with its permitted ARO list | `state:camouflaged` lacks a complete operative list/lifecycle explanation; presence of Discover links is insufficient | REA-015; Partially verified; preserve State-specific declaration permission and subsequent revelation |
| N53-23 / EN 23, ES 26 | IMM-B Hacking example | S3 p. 164 has no corresponding example; S1 p. 165 contrasts Reset -3 with unmodified Hacking defense and the attack Program's own values | `state:immobilized-b`, `skill:reset` and Program statlines agree with the selected example | Verified; REA-014 still covers combined States and MOD ceilings; do not universalize one Program's profile |
| N53-24 / EN 24, ES 27 | Null vocabulary | S1 p. 174 explicitly enumerates five Null States, beyond S3 p. 173's Label heading | `term:null-state`/Label summaries need the canonical list and links; individual State presence is not list completeness | REA-026; Partially verified; compare Dead, Sepsitorized, Unconscious, Disconnected, Possessed and their individual exceptions |
| N53-25 / EN 25, ES 29 | Three new profiles | S1 visually checked p. 180 adds Breaker Marksman; p. 185 has no Breaker Sniper. S6 225 agrees with S14's Marksman equivalent; AP Red Fury 229 and AP Thunderbolt 230 agree with current source profiles | 229/230 publish correctly; 225 survives in metadata but public numeric/slug getter has no item. English notice's Sniper label cannot establish a separate weapon | REA-044; Discrepancy; derived terminology reconciliation supported by profile/range identity, targeted publication still needed |
| N53-26 / EN 26, ES 30 | Thunderbolt grouping | S1 p. 186 groups Thunderbolt and AP Thunderbolt; S6 207/230 and maintained weapon categories agree | Public database places both in Thunderbolts; no missing category inferred | Verified; complete profile/UI acceptance remains separate |

## Additional Spanish-list subjects

These are not duplicates of the nearby shared bullet. Current Spanish PDF S17
is now available and checked for selected clauses; **previous Spanish N5.2 PDF**
remains unavailable, so these are not independently verified historical Spanish
PDF deltas. S14 current-member and S21 oldid hashes are in the source manifest.

| ID / exact S13 rules ordinal | Subject | Previous/current clauses and representation | Findings / status / unresolved evidence |
| --- | --- | --- | --- |
| ESX-01 / 17 | Stealth alignment | S14 `es/Sigilo` 4004 has N5.3 annotation restricting reactions to Basic Short Movement/Idle without LoF, with Deployable/Sixth Sense/combat exclusions; compare S1 p. 113 and `skill:stealth` | REA-016; Partially verified; previous Spanish baseline and combined activation explanation incomplete; S17 is available but this clause was not compared in the supplementary check |
| ESX-02 / 19 | Jet Propulsion wording | Notice explicitly identifies an English-only change. S3 p. 112 versus S1 p. 113 permits repeated direction changes mid-air; S14 `es/Super-Salto` 3964 retains older landing-oriented wording | `skill:super-jump` family lacks actionable Jet Propulsion operation, REA-032; Partially verified; do not extend bracket-distance rule to every Jump |
| ESX-03 / 23 | MSV3 turn limit | S14 `es/Visor_Multiespectral` 4013's N5.3 clause agrees with S1 p. 125's Active-Turn-only attack on Camouflage without prior Discover; `equipment:multispectral-visor`'s L3 explanation has the turn qualification | REA-015; Partially verified; additional Spanish wording about disclosure to other Troopers needs ordinary save/revelation scope review; not blanket permission to remain a Marker after an attack |
| ESX-04 / 28 | AP+T2 CC property | S14 `es/Tabla_de_Armas` 3987 and S1 p. 177 show Anti-materiel on AP+T2 CC; source profile context agrees | `trait:anti-materiel`, AP/T2 component explanations; Partially verified; no new defect, but previous Spanish PDF and the S17 AP+T2 chart row were not rechecked in this supplementary pass; unrelated Kobra uncertainty remains REA-028 |

## Army update, separately scoped

Exact source: S11's **ARMY UPDATE CHANGELOG**, ordinal 1-20; S13 has matching
Army ordinals. S6 is a post-notice snapshot, not a verified pre/post diff. All
20 rows are **Partially verified**: current selected identities/profile context
were inspected, but no pre-September-1 snapshot was pinned and no complete
chart/profile/browser approval is claimed. Army Unit IDs are source identities,
not invented curated rule IDs. Numeric profile, roster and chart changes belong
to Army acceptance; the Spec-Ops rule/ITS scope independently remains REA-040.

For rows 02-16 the inspected claim is the paired Unit presence and applicable
faction member, not every customization cost, option or Fireteam exception.
The full native objects were available; no complete table comparison was
performed. Chart constraints and player-visible paths remain pending.

| ID / ordinal | Subject alias | S6 member / version / selected source Unit IDs | Representation/explanation disposition and pending comparison |
| --- | --- | --- | --- |
| ARMY-01 / 1 | Team charts | Native faction chart context and the paired Units below; both snapshot versions | Full Spec-Ops/TEAM-OPS chart membership/limits not approved; REA-020/040; compare all affected charts with an earlier pinned snapshot |
| ARMY-02 / 2 | Indigo pair | `101-panoceania.json` / `7.26246.158` / 1912, 1926 | Both Units found; option/chart acceptance pending |
| ARMY-03 / 3 | Confessor pair | `103-military-orders.json` / `7.26246.158` / 1913, 1927 | Both Units found; option/chart acceptance pending |
| ARMY-04 / 4 | Gui Feng pair | `201-yu-jing.json` / `7.26246.158` / 1914, 1928 | Both Units found; option/chart acceptance pending |
| ARMY-05 / 5 | Intel pair | `301-ariadna.json` / `7.26246.158` / 1915, 1929 | Both Units found; option/chart acceptance pending |
| ARMY-06 / 6 | Husam pair | `401-haqqislam.json` / `7.26246.158` / 1916, 1930 | Both Units found; option/chart acceptance pending |
| ARMY-07 / 7 | Vortex pair | `501-nomads.json` / `7.26246.158` / 1917, 1931 | Both Units found; option/chart acceptance pending |
| ARMY-08 / 8 | Nexus pair | `601-combined-army.json` / `7.26246.158` / 1918, 1932 | Both Units found; option/chart acceptance pending |
| ARMY-09 / 9 | Treitak pair | `601-combined-army.json` and `602-morat.json` / `7.26246.158` / 1919, 1933 | Spec-Ops and Morat Team found; compare distinct faction contexts |
| ARMY-10 / 10 | Corax pair | `603-shasvastii.json` / `7.26246.158` / 1920, 1934 | Both Units found; option/chart acceptance pending |
| ARMY-11 / 11 | Blur pair | `605-next-wave.json` / `7.26246.158` / 1921, 1935 | Both Units found; option/chart acceptance pending |
| ARMY-12 / 12 | Chandra pair | `701-aleph.json` / `7.26246.159` / 1922, 1936 | Both Units found; option/chart acceptance pending |
| ARMY-13 / 13 | Stormo pair | `1001-o-12.json` / `7.26246.159` / 1923, 1937 | Both Units found; option/chart acceptance pending |
| ARMY-14 / 14 | Kaizoku pair | `1101-jsa.json` / `7.26246.159` / 1924, 1938 | Both Units found; option/chart acceptance pending |
| ARMY-15 / 15 | Hatail pair | `801-tohaa.json` / `7.26246.159` / 1908, 1909 | Both Units found; option/chart acceptance pending |
| ARMY-16 / 16 | Rumbler pair | `901-non-aligned-armies.json` and `902-druze.json` / `7.26246.159` / 1925, 1939 | Spec-Ops and NA2 Team found; not a complete NA2-sectorial matrix |
| ARMY-17 / 17 | Ioann / charts | `1001-o-12.json` / `7.26246.159` / 1940 | Unit present; affected sectorial memberships and changes not independently approved; REA-020 context |
| ARMY-18 / 18 | Najjarun loadout | `401-haqqislam.json` / `7.26246.158` / 314 | Shared profile Equipment 238 resolves to Deactivator in metadata; it applies across the three native options. Selected current loadout confirmed; earlier loadout and complete public explanation pending. The separate option weapon 222 lookup is not evidence against Deactivator |
| ARMY-19 / 19 | Sāchā availability | `1003-torchlight-brigade.json` / `7.26246.159`, `107-kestrel-colonial-force.json`, `204-invincible-army.json`, `304-usariadna.json` / `7.26246.158` / 1874 | Selected profiles show AVA 1; faction-wide before/after change and browser approval pending. Accent-aware ID lookup avoided a false name-search absence |
| ARMY-20 / 20 | Racerbot classification | `101-panoceania.json` / `7.26246.158` / 1905 | Native profile contains Equipment 246 and legacy Skill 266, both Bangbomb with extra 310. Maintained skill-source classification maps the latter to Equipment; source bucket alone is not a regression. Full deduplicated public presentation and prior snapshot comparison pending |

## FAQ comparison and ITS boundaries

S15 v0.0 has **28 Q&A blocks**; S2 v0.1 has **37**. All pages of both were
read. Nine additional blocks below account for the difference. The 28 common
blocks had no material answer change observed; layout/page moves and compound
question punctuation are not separate new rulings. A question-mark count
(29 versus 39) would be the wrong denominator. Existing FAQ context is inventoried
in the [coverage appendix](rules-explanation-audit-1.0-inventory.md#faq-coverage-disposition).
S2's publication date remains unverified; creation metadata is not release date.

| ID | S2 printed page / added subject | Selected ruling compared / affected identities | Explanation or scope still pending |
| --- | --- | --- | --- |
| FAQ-01 | 1 / declaration detail | Target position chosen in Resolution before range measurement; declaration/attack baselines | REA-026; complete player-facing sequence review |
| FAQ-02 | 1 / Device Firewall | Device benefit requires Device not disabled; `skill:hacker`, Device families | REA-018; canonical baseline and disabled-State exceptions |
| FAQ-03 | 1 / vertical placement | Deployable placement cannot use vertical surfaces; placement Equipment/weapons | REA-023; valid/fallback/contact geometry cases |
| FAQ-04 | 2 / Controller unable to act | Peripheral can perform the declared Skill although its Controller cannot; subtype applicability retained | REA-017; not a universal permission to ignore all Controller requirements |
| FAQ-05 | 2 / coordinated SD | Special Dice under Coordinated Orders; common Burst reference | REA-021/026; explain Burst versus Special Dice distinctly |
| FAQ-06 | 2-3 / concealed object in Cover | A hit can force disclosure for the represented object's save even in Total Cover; disclosure does not itself guarantee the object was hit | REA-015; Marker/geometry procedure and ESX-03 scope |
| FAQ-07 | 3 / reduced membership | Fireteam Type does not change merely because members are lost | REA-020; formation versus continuing integrity |
| FAQ-08 | 3 / required members | Minimum/required member conditions at creation, with Fireteam Master exception | REA-020; source-specific chart/master conditions |
| FAQ-09 | 4 / undeployed Ancillary | Under the ITS heading, undeployed Ancillary not counted Killed | REA-030; core-scenario applicability unresolved; do not import an ITS scoring ruling as ordinary State recovery |

S16 pp. 26, 28-29 independently verifies Season 18's ordinary Spec-Ops ban,
TEAM-OPS Extra and separate Tacball material. That does not publish the entire
ITS season or add TEAM-OPS to the four supported core scenarios. The notice's
season overview, mission additions and digital publication format are ITS
publication context, not additional N5.3 rulebook bullets. Historical ITS,
Reinforcements annex and Spanish FAQ remain outside completed source verification.

## Declaration-category source-heading reconciliation (2026-10-16)

This is a **selected source-to-metadata correction**, not the
367-record explanation-audit signoff. N5.3 English pp. 39, 51, 77,
79, 92 and 103 were checked against the actual heading and declaration
line, not merely a page containing an example of the Skill:

- **BS Attack:** Short Skill / ARO, p. 39. Both declaration identities
  migrate from p40 to p39; the full Skill and BS=11/BS=12
  variant records now cite the owning heading.
- **CC Attack:** Short Skill / ARO, p. 51. Both declaration identities
  migrate from p45 to p51; the full Skill and CC=21 variant
  record now cite the owning heading.
- **Discover:** Basic Short Skill / ARO, p. 77. Both declaration
  identities migrate from p78 to p77; its full Skill citation
  now points to the definition rather than the continuation example.
- **Dodge:** Short Skill / ARO, p. 79; unchanged.
- **Forward Observer:** Short Skill / ARO, p. 92; unchanged.
- **Morpho-Scan:** Short Skill, p. 103, **not** Basic Short Skill
  and **not** ARO. The former basic-short-skill:p103 identity is
  replaced by short-skill:p103; the incorrect aro:p103 identity
  is retired. The full Skill was already correctly typed and now
  also cites the primary PDF. Its target's option to declare Reset
  as an ARO does not make Morpho-Scan an ARO.

The exact page is part of a declaration identity. The **frozen
367-record inventory retains all eight original S-tier identities**
as historical audit evidence; it is not rewritten or silently
renumbered. The eight original ARO/Basic identities correspond to
seven current records: five AROs, Discover's Basic Short Skill and
Morpho-Scan's Short Skill. Other affected Short Skill page citations
were corrected separately. The crosswalk above records the retired
and successor IDs and the changed source pages. This does **not** promote those original inventory records to
full material-mechanics acceptance or validate all 60 declaration
metadata identities. BS=11/BS=12/CC=21 source values remain subject to
their own Army-profile variant audit; a corrected BS/CC action citation
is not evidence for a numerical replacement.

Regression tests compare the complete current mappings with the
N5.3 headings and verify downstream declaration projections. The
remaining declaration families, exceptional ARO permissions and final
browser/completeness gate must be evaluated independently.

## Deployment and Long Skill source-heading reconciliation (2026-10-16)

A second bounded audit inspected all six currently published Deployment
mappings and all five original Long Skill mapping records against the
heading declarations of the pinned English N5.3 rulebook. It corrects
source provenance, not Skill mechanics or Army profile data.

- Infiltration is a Deployment Skill at p. 97 (previously p. 89);
  Impersonation at p. 96 (previously p. 93); Hidden Deployment at
  p. 95 (previously p. 94).
- Climb and Jump are separate Long Skill headings at pp. 32 and 34.
  Their former shared p. 25 declaration identity was retired and
  replaced by one page-scoped record per Skill.
- Combat Jump remains Long Skill p. 89, while Parachutist is
  Long Skill p. 105; the former combined p. 89 record was split.
- Forward Deployment p. 92, Minelayer p. 102, Sapper p. 111,
  Triangulated Fire p. 118 and Berserk p. 86 were checked and
  retained. Sapper correctly has both Deployment and Long Skill
  classifications.

The seven affected full Skill records now cite their correct N5.3
headings in addition to any existing source revisions. There are
**61 current declaration-category records**, up from 59, because
the two shared-source records were split. This is an additive
current-data change, not a revision of the historical denominator:
the **367-record original audit inventory stays frozen** and retains
its original identifiers and S-tier dispositions. Climbing Plus
and Super-Jump can modify how Climb and Jump are declared; these
conditional enhancements are not modeled as universally available
Basic Short Skill declarations here.

Source-pinned regression tests check the twelve owning heading
declarations and one-to-one source mappings; the rebuilt database
and eight representative published Skill pages were also checked
in responsive browsers. Automatic and remaining Short Skill
category mappings, numerical Army replacement values, conditional
permissibility, and whole-corpus acceptance remain open.

## Five incorrect Automatic/Deployment mappings (2026-10-16)

The pinned English N5.3 PDF explicitly labels five Skills as
**Deployment Skill, Optional**, although the additional declaration
metadata classified them as Automatic:

- Booty: p. 86; removed from the shared Automatic p. 87 entry.
- Decoy: p. 90; retired the lone Automatic p. 89 identity.
- MetaChemistry: p. 101; removed from Automatic p. 98.
- Remdriver: p. 110; removed from Automatic p. 110.
- Strategic Deployment: p. 112; removed from Automatic p. 112.

Each now has one page-specific Deployment declaration identity and
a primary-source PDF citation on the owning Skill, preserving the
earlier Wiki revision evidence. Its underlying Skill type and
gameplay mechanics were already correct; this fixes the independent
declaration-category projection only. Existing unrelated Automatic
mappings in the shared records remain intact.

This bounded correction increases the **current** declaration-category
record count from 61 to 65, and the exported rules DB from 461 to 465.
It does not modify or increase the frozen 367-record explanation-audit
baseline or retroactively grant complete clause acceptance. The other
Automatic/Short Skill page and ownership mappings still require
individual source verification. The retained historical
Automatic p. 93 mapping to Regular is also pending classification
against the canonical Training rather than being removed without
a source/consumer audit.

A pinned-source test proves the five exact heading/declaration pairs,
a curated test prevents reintroduction of the Automatic mappings,
and browser checks verify all five public Skill category badges.

## Automatic heading pages and Regular ownership (2026-10-16)

Fourteen Automatic Skill mappings pointed to stale printed pages
in the pinned English N5.3 PDF, even though their type was correct:

- Surprise Attack p. 88 to 114; Chain of Command p. 90 to 87;
  No Wound Incapacitation p. 91 to 104; G: Jumper p. 94 to 93.
- Hacker p. 95 to 54; Immunity p. 96 to 95; Natural Born
  Warrior p. 101 to 103; Remote Presence p. 102 to 110;
  Sixth Sense p. 112 to 111.
- Lieutenant p. 113 to 99; Super-Jump p. 114 to 113;
  Regeneration p. 116 to 109; Terrain and Total Reaction
  p. 118 to 116.

Each mapping now cites the actual heading, reusing existing
page groups where appropriate. Hacker gained a new p. 54 group;
obsolete empty groups p. 94, p. 96 and p. 101 were removed.
Owning Skill citations were added/corrected while preserving
other-source references and distinct Immunity examples.

The Automatic p. 93 record additionally linked Regular as if it
were a Skill. Regular is actually a Training Characteristic,
represented by the canonical training:regular record (N5.3 p. 11).
The invalid link was removed without altering Training or Order
semantics. The current declaration catalog has **28 Automatic
groups and 63 declaration-category records**, and rules.db has
**463 total records**. No gameplay mechanics were changed.

This is source/projection reconciliation, not acceptance of all
Automatic conditional activation effects. The original
367-record audit inventory remains frozen. Remaining Short Skill,
numeric Army replacement, and wider corpus acceptance work
still needs independent evidence.

## Short Skill headings and named Army replacement values (2026-10-16)

The eleven current **Short Skill** declaration entries were checked
against their actual headings in the pinned English N5.3 rules
(pp. 39, 51, 79, 90-92, 103, 111, 121 and 123-124). The only
incorrect source citation was Sensor, which was labelled p. 112 in
both the page-scoped declaration and Skill definition. The actual
Sensor/Short Skill heading is on **p. 111**. Both references have
been corrected, retaining the previous Wiki revision.

The separately curated BS=11, BS=12 and CC=21 records were also
cross-checked against the **2026-09-29 11:43:35 Army snapshot**,
JSON 20260929-114335.zip (SHA-256
f103a7afd02e68d845cc9ce38b1948f46914676bbc6a5e6b790d0a04148b6c75).
All three exact ID/name pairs appear in its official source Skill
dictionaries and in concrete unit-option loadouts:

- BS=11: source Skill ID 279, two loadout occurrences.
- BS=12: source Skill ID 278, nine loadout occurrences.
- CC=21: source Skill ID 274, six loadout occurrences.

These are **17 faction-file occurrences**, not 17 distinct units or
independent official named core-rule entries. Examples include
Polaris Team (BS=11), Streloks (BS=12), and Swiss Guard (CC=21).
The numerical values are source-defined by the **Army variant
names**, while their action mechanics link back to the core
BS Attack (p. 39) and CC Attack (p. 51) definitions. N5.3 p. 75
provides general MOD/value notation context, not separate BS=11,
BS=12 or CC=21 entries. No separate mechanics or source-invented
modifier were introduced.

Tests pin the variant identity/parent-action associations regardless
of local archive availability. A source-provenance test validates
the exact ignored archive checksum, dictionary entries, and 17
loadout occurrences **when the private archive is installed**;
it skips in environments without that local evidence. The frozen
367-record historical inventory is unchanged. This closes the
bounded Short Skill heading and three named source-identity checks,
but **does not** close conditional declaration semantics or the
full 1.0 whole-corpus gate.

## Conditional movement declarations (2026-10-16)

N5.3 p. 88 allows Climbing Plus to make Climb a Basic Short Skill
only when declared first; p. 113 establishes the corresponding
exception for Super-Jump and Jump. Both helper Skills remain
Automatic, while Climb (p. 32) and Jump (p. 34) remain Long.
There is no general category reclassification or universal ARO.

The Climbing Plus record now cites the primary PDF alongside its
Wiki revision and covers declared trajectory, 360-degree LoF,
vertical underside base contact and Impetuous use. Super-Jump
now expressly covers the second MOV value when Move follows,
trajectory/LoF, Impetuous use, automatic Prone cancellation
when Jump is declared and mid-air redirection limited to the
named Jet Propulsion profile variant. Existing once-per-Order
and no Partial Cover restrictions are preserved.

Pinned PDF and curated tests plus a 6/6 responsive browser check
provide bounded evidence for these two exceptions. The frozen
367-record inventory and other 1.0 acceptance tasks remain open.

## Reactive combat Automatic Skill provenance (2026-10-16)

Three source-verified Automatic Skill exceptions remain distinct:
Guard (N5.3 p. 95, Optional) permits CC Attack without
Silhouette contact when the target is in LoF and ZoC.
Neurocinetics (p. 104, Obligatory) reduces BS Weapon Burst to 1
in the Active Turn, permits full Burst against one target in
the Reactive Turn, and applies Burst modifiers only then.
Total Reaction (p. 116, Optional) permits full Burst, including
Burst modifiers, specifically during BS Attack AROs against one
of the Troopers activated by the Order.

The existing curated mechanics and types agree with these clauses.
Direct pinned N5.3 citations were added to Guard and Neurocinetics,
preserving the previously recorded Wiki revisions. Total Reaction
already had both primary and Wiki citations. Source-pinned and
curated tests now guard each classification and heading.

This bounded verification does not establish any combined effect
between these Skills, remove the separate Aerial restriction
on Guard, or close all reactive/Automatic exceptions. The
original 367-record explanation audit remains frozen.

## Guard versus Aerial exception (2026-10-16)

The pinned English N5.3 PDF establishes a three-source
interaction: Guard (p. 95, Optional Automatic) permits CC Attack
inside LoF and ZoC without Silhouette contact; Aerial (p. 86,
Obligatory Automatic) explicitly prohibits Guard against an
Aerial target unless it is Unconscious; Unconscious State
(p. 172) disables Automatic Special Skills while active.
Guard's permission to ignore contact does not override the
separate Aerial prohibition. Against an Unconscious target,
the prohibition is lifted but Guard still requires LoF and ZoC.

The curated outcome and Aerial-owned restricts-use-of relation
were already correct. Added p. 86 PDF provenance to Aerial and
both exception and Unconscious citations to Guard. Linked
clarifications explain the prohibition and limited exception.
Historical Wiki sources, Skill types, existing relations and
gameplay mechanics were preserved.

Pinned PDF and curated tests cover the three clauses. Two
Skill pages passed 6/6 responsive browser cases at 1440, 390
and 320 px, with no page errors or overflow. This bounded
exception acceptance does not close other ARO permissions,
Automatic interactions, or the whole-corpus 1.0 gate.
The historical 367-record inventory remains frozen.

## Stealth counters and outside-LoF reaction scope (2026-10-16)

Pinned English N5.3 p. 112 explicitly exempts Troopers with
Combat Instinct and Sixth Sense from Stealth's reaction
suppression. Combat Instinct p. 88 separately ignores Surprise
Attack MODs, but does not grant special outside-LoF reaction
permission. Sixth Sense p. 111 allows a 360-degree LoF arc and
outside-LoF reaction **only for Attacks directed at the user**,
not non-Attack movement. The general Zone of Control reaction
trigger on p. 20 still requires a valid ARO and eligible action.

The existing source-native inverse relations from Combat Instinct
and Sixth Sense to Stealth remain unchanged. Combat Instinct
gained primary N5.3 citations (pp. 88, 112, 20) while retaining
its pinned Wiki revision; Sixth Sense gained the Stealth/ZoC
citations alongside its existing FAQ and Wiki provenance.
Player-facing clarifications now distinguish cancellation of
Stealth protection from granting LoF or waiving reaction
requirements. No rule mechanism or ARO engine was introduced.

Source-pinned and curated regression tests passed; the three
published Skill pages passed 9/9 headless Chrome cases at
1440/390/320 px, checking rendered content and no script errors
or overflow. This verifies the selected counter-Skill boundary,
not every possible Stealth/mixed-activation exception. The
frozen 367-record inventory remains unchanged.

## Look Out! as an exceptional allied ARO (2026-10-16)

N5.3 English p. 81 permits a Trooper with LoF to an enemy
declaring or performing an Order to declare Look Out! as
an ARO. The Reactive Player selects other allied Troopers
immediately; those allies may make Dodge (PH-3) Rolls to
adjust LoF/facing without displacement and are counted
as having declared an ARO. The source example explicitly
includes an ally outside the enemy's LoF and ZoC. They
cannot already have declared another ARO. Their Dodge
roll is normally unopposed, but may be Face to Face when
subject to an Attack that Dodge can oppose.

The prior curated explanation omitted selection timing,
special ARO eligibility and roll opposition. The owning
record now cites N5.3 p. 81 directly, preserving its Wiki
revision, No Roll ARO category and Dodge-modifier relation.
This grant is restricted to the specified Dodge action.

Pinned PDF and curated tests plus 3/3 browser checks
at 1440/390/320 px pass. The frozen 367-record audit
is not changed or marked complete. Other conditional
ARO permissions and numerical variants remain open.

## Reload, Baggage and Place Deployable ARO timing (2026-10-16)

Pinned English N5.3 p. 83 defines Reload as Short Skill/ARO.
The user needs an expended/Unloaded item, remains subject to
ordinary ARO eligibility, and must be inside an eligible
allied Baggage holder's Zone of Control. Its effect is limited
to one allied Trooper per Order and does not restore already
deployed items. Baggage p. 120 supplies a separate automatic
recovery effect in the States Phase; that is not a new
Reload declaration in the current Order.

Place Deployable p. 82 permits Short Skill/ARO placement but
requires LoF to the Active Trooper during the Reactive Turn.
When an item also has Perimeter, the source permits placement
fully inside ZoC with a passable path instead of Silhouette
contact. The exception changes placement geometry, not ARO
eligibility. The item is placed at the Conclusion of the Order,
with activation and its own reactions only in later Orders.
The existing FAQ ruling about an occupied placement location
remains separate and unchanged.

The existing categories, constraints, interaction relations and
underlying mechanics already matched the official source.
Added primary N5.3 citations to Reload (p. 83) and Baggage
(p. 120) and clarifications to Reload and Place Deployable,
preserving historical Wiki and FAQ provenance. Regression tests
check category, constraints, source clauses and complementary
timing. The published Reload and Place Deployable Skill pages
passed 6/6 responsive browser checks at 1440/390/320 px.
The frozen historical 367-record inventory is unchanged.
This is selected ARO/timing acceptance, not whole-corpus 1.0.

## Discover retry and ARO reveal sequence (2026-10-16)

Pinned English N5.3 p. 77 defines Discover as a Basic Short
Skill/ARO with a mandatory LoF to the target. The same
Trooper cannot declare Discover against the same target
twice in one Order. After failing to Discover a Marker,
that Trooper cannot retry the **same Marker** until the
next Player Turn, regardless of whether it represented
Camouflage or Impersonation. An allied Trooper may try
independently; the original Trooper may target a different
Marker. Once a revealed Trooper enters a Marker State again,
it counts as a different Marker for this restriction.

The earlier curated wording incorrectly qualified the failure
lockout as if it applied only to IMP-1/IMP-2 Markers, and
did not explicitly state the LoF requirement. The corrected
facts now use the general Marker rule and explain the
Discover + Attack procedure: if the Camouflaged target
declares a revealing ARO, the Discover Roll is unnecessary;
otherwise the Roll must succeed before resolving the
Attack. The owning p. 77 PDF citation, older Wiki source,
Basic Short Skill/ARO classification and reveal relations
are preserved. No other Skill mechanics changed.

Pinned-source and curated regression tests plus 3/3
responsive browser checks at 1440/390/320 px passed.
The frozen 367-record historical inventory remains
unchanged, and whole-corpus 1.0 acceptance is still open.

## Cautious Movement and Stealth ARO suppression (2026-10-16)

The pinned N5.3 English rulebook (p. 32) defines Cautious
Movement as a Long Skill, with its ordinary no-ARO effect
depending on the beginning **and** ending positions being
outside the LoF and ZoC of all enemy Models and Markers.
A Hackable Trooper in Model form must additionally avoid
enemy Hacker Hacking Areas at both endpoints; a non-Hackable
Trooper does not grant AROs from that Hacking Area condition
alone. Hidden Deployment units are neither Models nor Markers
for this LoF/ZoC reaction rule. These are conditional
endpoints, not unconditional reaction immunity.

N5.3 p. 112 separately permits a Stealth user in the Active
Turn to declare Cautious Movement within enemy ZoC/Hacking
Areas, still granting reactions to enemies with LoF.
Combat Instinct and Sixth Sense negate Stealth protection,
and Deployable equipment follows independent triggering
rules. The curated Cautious Movement record retains its
Long Skill classification, existing restrictions and
historical Wiki reference. It gained explicit primary
PDF provenance and four source-scoped explanations; no
new mechanics, relation types, or ARO engine were added.

Two pinned-source/curation tests passed. Its published page
also passed 3/3 headless browser checks at 1440/390/320 px.
The original 367-record audit remains frozen and does not
become accepted on the strength of this bounded verification.

## Alert! and automatic Conclusion timing (2026-10-16)

Pinned English N5.3 p. 77 identifies Alert! as an Optional,
No Roll **Automatic Skill**, not an ARO. The current Trooper
must not have been activated by an Order **or an ARO** in
the same Order. The Trooper or an allied Trooper inside its
ZoC must have been the target of an Attack. At Conclusion,
**after Saving Rolls**, eligible Troopers may turn on the
spot to change their LoF angle without displacement,
additional Rolls or generating new AROs.

The existing curated clarification incorrectly said Alert!
requirements were checked "when it is declared"; the
automatic rule is not declared. Its corrected explanation
and requirement explicitly exclude previous AROs, preserve
the original source-reviewed requirement and turn clauses,
and separate this effect from the declared allied Dodge
ARO of Look Out!. The record retains its Automatic type,
Optional/No Roll labels and historical Wiki reference,
while adding N5.3 p. 77 as direct provenance.

Both curated and pinned-PDF tests passed. A newly built
rules DB was checked in the browser at 1440, 390 and 320
px: 3/3 Skill page checks passed for the Automatic badge,
the new scope and timing clauses, and no page errors or
horizontal overflow. This is bounded acceptance; the
frozen 367-record inventory is unchanged and full 1.0
corpus acceptance remains open.

## Cyberplug Controller ARO split (2026-10-16)

Pinned English N5.3 pp. 107-108 distinguish activating a
Connected Peripheral (Cyberplug) from having the Controller
perform an independent reaction. During an Active Turn, the
Controller still activates but resolves the shared action as
Idle; an enemy with a valid ARO can target that Controller,
and an attack against the Idling Controller is a Normal Roll
(p. 108, example 1). The Connected Peripheral's separate
attack does not oppose an attack targeting the Controller.

During the Reactive Turn, selecting a Connected Cyberplug
causes the Controller to declare the ARO but perform Idle;
the other Autonomous Cyberplug may react independently.
Alternatively, the Controller performs its own ARO while
both Cyberplugs operate as Autonomous, each subject to
ordinary ARO eligibility (pp. 107-108, examples 2-3).
Neither choice creates an ARO without a qualifying trigger.

The prior REA-017 subtype model and relationships already
represented this correctly. Two clarifications were added to
the Cyberplug subtype; no activation engine, profile mode,
Army source, or shared Peripheral rule was changed.
Two source/curation regressions and responsive browser
checks provide bounded verification. The frozen 367-record
inventory and the whole-corpus acceptance gate remain open.

## Speculative Attack Circular Template ARO sequence (2026-10-16)

Pinned English N5.3 p. 48 establishes four procedural steps:
designate the Main Target; choose a legal Circular Template
impact point affecting it; determine all other affected Troopers
and their ARO eligibility; then measure range, apply MODs and
make the Rolls. The Main Target and point may be outside
the shooter's LoF, but valid trajectory, impact position,
Burst 1 and the printed MOD restrictions remain mandatory.

The official example confirms that a target behind a wall
may declare Dodge against a template that affects it, with
a -3 Dodge MOD for lacking LoF to the attacker. That Dodge
opposes the Speculative Attack Roll Face to Face. The attacker
uses Range and Speculative Attack -6, not target Mimetism or
Cover MODs. The rule does not grant reactions to unaffected
Troopers or waive ordinary eligibility for unrelated actions.

The existing curated Long Skill and modifier relations already
matched this outcome but omitted the template-to-ARO order.
Added three clarifications and N5.3 p. 48 primary provenance,
preserving the original reviewed requirements, effects,
restrictions and Wiki citation. Two pinned-source/curated
tests and 3/3 responsive browser checks passed. The frozen
367-record inventory and whole-corpus 1.0 gate remain open.

## Suppressive Fire State and G: Jumper activation (2026-10-16)

English N5.3 p. 85 defines the Suppressive Fire Long Skill
as the action that enters the State. Its G: Jumper clause
explicitly preserves a Proxy's Suppressive Fire when another
Proxy activates. The normal automatic cancellation triggered
by the original Trooper's declaration of an Order does not
mean that a separate Proxy's activation removes the State.

N5.3 p. 171 separately defines the State's reactive benefit:
the chosen weapon uses SF Mode and may fire Burst 3 during
a valid BS Attack ARO, directed at only one target even
against multiple activated enemies. A different ARO, use
of an ineligible weapon, and the other named cancellation
conditions still terminate the State. The State does not
grant an unrestricted ARO or change the underlying weapon
PS and Ammunition.

The curated State already modeled the B3, single-target,
and cancellation restrictions. Added the missing G: Jumper
exception and the declaration-versus-ARO distinction to
the owning Long Skill record, plus pinned English N5.3
pp. 85/171 citations. Existing Wiki provenance, metadata
types, and relations remain intact. Two focused source and
curation tests passed. Both published Skill/State pages
passed 6/6 headless browser checks at 1440/390/320 px.
This is bounded acceptance; the frozen 367-record inventory
and final whole-corpus 1.0 gate remain open.

## Hacking Area citation and split ARO windows (2026-10-16)

Pinned English N5.3 p. 55 defines Hacking Area and its
ARO eligibility, not p. 56 as previously cited. Page 56
instead contains HoloMask/Repeater equipment rules. The
source citation on the owning Hacking Area rule was corrected
to p. 55, preserving the archived Wiki provenance. Page
57 now has a separate citation for its two worked examples.

In the p. 57 Active Hacker example, the enemy Hacker can
declare an ARO through Hacking Area while the Active Hacker
is outside ordinary LoF and ZoC. Enemy Heavy Infantry
outside both has no ARO to the first Idle, but receives a
Reset ARO when the second Short Skill targets it with
a Comms Attack. In the Camouflaged example, an enemy
Hacker can delay an ARO against a Marker inside Hacking
Area, declaring a reaction in that example only when
the Marker reveals itself with the second Short Skill.
A potential target or hidden identity alone does not
confer unrestricted permission to react or hack.

The existing Hacking Area derivation, Repeater links,
enemy-Repeater limitations, and HoloMask exceptions
remain unchanged. Two curated and SHA-256-pinned PDF
tests confirm the citation and bounded procedures.
A fresh rules DB rendered the published page at
1440/390/320 px. The initial browser run missed body text
at 390 px despite HTTP 200; three subsequent complete
runs passed all widths (9/9 cases), so that intermittent
condition is not treated as a confirmed product defect.
The original 367-record audit remains frozen, and full
1.0 corpus acceptance is still open.

## Army BTS=3 loadout-only replacement presentation (2026-10-16)

The currently built Army Skill dictionary includes four
`Attribute=value` source names: BS=11 (279), BS=12 (278),
CC=21 (274), and BTS=3 (280). The first three are already
curated as source-specific BS/CC Attack Skill variants.
The fourth is **not an N5 Skill**. It is classified as
`attribute-override` by
`config/catalogs/skill-source-classifications.json`,
and its absence from the rules-backed Skills catalog
is correct.

The built Army data associates BTS=3 with three distinct
Corregidor Alguacil Gatta loadout payloads. Its shared
Unit Profile has BTS 0; those loadouts carry the BTS=3
source occurrence. Previously, the Unit page rendered
each occurrence in the Skills row as a link to
`/skills/bts-3`, although the catalog deliberately
does not expose that Skill route.

Unit presentation now consults the existing maintained
source classifications and groups BTS=3 in a separate
loadout **Attribute overrides** row, rendered as text.
Raw Army occurrences, profile attributes, other loadout
items, and the rules-backed Skills catalog remain intact.
No Skill/ARO types or new rules mechanics are introduced.

A synthetic regression verifies classification-driven
separation and frontend nonlink presentation; existing
tests continue to protect catalog exclusion. Browser
acceptance on the real Gatta Unit page passed at
1440/390/320 px (3/3), checking all three occurrences,
no broken Skill links and no horizontal overflow.
The count is derived from the currently built Army
data, not an independent frozen Army archive.
The original 367-record audit and final 1.0 acceptance
gate remain open.

## Implementation and completion handoff

The independent errors found here are REA-039/040/043/044; allegiance is an
unresolved decision REA-038 and the verified Spanish PDF/Wiki source
conflicts REA-041/042. S17 independently confirms the one-save Flash Pulse
profile (REA-027), the bilingual Level 3 Fireteam example (REA-034), and the
within-PDF Armed Turret Silhouette conflict (REA-037).
Existing IDs retain their original subject; a second observation on Prone or
Camouflaged extends REA-015 rather than creating duplicate findings.

First adjudicate REA-038's allegiance wording and source policy. In parallel,
REA-043 and source-confirmed recovery/Intuitive Attack clauses can be corrected
without widening allegiance. Keep data and presentation acceptance separate,
use common modifier/placement/Fireteam baselines, and preserve explicit subtype
exceptions. The [completion gate](rules-explanation-audit-1.0-inventory.md#audit-completion-gate)
requires remaining record/source checks even after every finding is closed.
An unresolved upstream source may receive a documented scoped disposition;
exhaustive history and every combat combination are not release requirements.
