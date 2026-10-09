# Rules explanation audit 1.0: N5.3 reconciliation

**Project domains:** Acquisition, Data processing, Web backend, Web frontend

This follow-up appendix belongs to the [audit](rules-explanation-audit-1.0.md).
Source identifiers and exact artifact hashes are in the
[provenance manifest](rules-explanation-audit-1.0-sources.md).
Research date: 2026-10-09; examined commit
`c5400ab1b950990fdacc509be91c110fe85431fb`. No corrections were implemented.

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
| N53-09 / EN 9, ES 9 | Dodge armor modifier | S1 p. 75 grants ARM +3 whenever that Dodge is declared; S14 Spanish detailed MODs 4012 still conditions it on failed PH, in an older May-update paragraph | No complete modifier baseline; this is an ARM effect, not +3 to the Dodge PH roll | REA-026/042; Discrepancy; Spanish PDF unavailable, source decision needed |
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

These are not duplicates of the nearby shared bullet. Previous Spanish PDFs are
unavailable, so present Spanish Wiki annotations cannot prove the historical
Spanish PDF delta. S14 member/revision hashes are in the source manifest.

| ID / exact S13 rules ordinal | Subject | Previous/current clauses and representation | Findings / status / unresolved evidence |
| --- | --- | --- | --- |
| ESX-01 / 17 | Stealth alignment | S14 `es/Sigilo` 4004 has N5.3 annotation restricting reactions to Basic Short Movement/Idle without LoF, with Deployable/Sixth Sense/combat exclusions; compare S1 p. 113 and `skill:stealth` | REA-016; Partially verified; current selected alignment checked, previous/current Spanish PDF absent and combined activation explanation incomplete |
| ESX-02 / 19 | Jet Propulsion wording | Notice explicitly identifies an English-only change. S3 p. 112 versus S1 p. 113 permits repeated direction changes mid-air; S14 `es/Super-Salto` 3964 retains older landing-oriented wording | `skill:super-jump` family lacks actionable Jet Propulsion operation, REA-032; Partially verified; do not extend bracket-distance rule to every Jump |
| ESX-03 / 23 | MSV3 turn limit | S14 `es/Visor_Multiespectral` 4013's N5.3 clause agrees with S1 p. 125's Active-Turn-only attack on Camouflage without prior Discover; `equipment:multispectral-visor`'s L3 explanation has the turn qualification | REA-015; Partially verified; additional Spanish wording about disclosure to other Troopers needs ordinary save/revelation scope review; not blanket permission to remain a Marker after an attack |
| ESX-04 / 28 | AP+T2 CC property | S14 `es/Tabla_de_Armas` 3987 and S1 p. 177 show Anti-materiel on AP+T2 CC; source profile context agrees | `trait:anti-materiel`, AP/T2 component explanations; Partially verified; no new defect, but pre-change and current Spanish PDF not checked; unrelated Kobra uncertainty remains REA-028 |

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

## Implementation and completion handoff

The independent errors found here are REA-039/040/043/044; allegiance is an
unresolved decision REA-038 and the additional bilingual conflicts REA-041/042.
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
