# N5 source and update history

**Project domain:** Data processing

This is a **discovery index and reconciliation procedure** for InfinityDB 1.0 source
research, not a claim that each historical change has been incorporated or verified.
The currently selected, versioned sources remain the primary evidence for current
rules and profile values. Never turn a dated announcement into a silent rules override.

## Local PDF revision inventory (2026-11-06)

The operator renamed the local PDFs and supplied additional revisions. The
following inventory records measured **file pages and SHA-256**, not acquisition
dates, complete content reviews or verified publication chronology. Version and
language labels follow the supplied filenames; the v5.1.1/v5.2/v5.3 and FAQ
covers also expose their versions as text. The v1/v1.1 cover text is empty, so
those filename labels have not been independently authenticated here. The local
`sources.txt` is an operator index, not a preserved authoritative release record.
PDF creation metadata must not be treated as publication time.

All paths below are under `data/pdf/`. Earlier dated availability statements in
this document and the frozen audit register describe their examination date:
**bilingual v5.1.1 and Spanish v5.2 bytes are now available**. Their arrival
enables historical comparisons; it does not establish any wording transition or
close a source-wide review. No external source was downloaded in this update.

| Local file | File pages | Exact SHA-256 |
| --- | --- | --- |
| `rules/n5-rules-v1-en.pdf` | 191 | `58d6f85e180884f33d8365c13373c6502a436b68e126d528fd44f7af8fec6d8f` |
| `rules/n5-rules-v1-es.pdf` | 198 | `0c2ddea1f511e7e73948886dcc85bbbf5f2559be0889d709a200cf530ecc373f` |
| `rules/n5-rules-v1.1-en.pdf` | 192 | `d4d69c9bac3dff58965312edc56a48f16d5ef65e24a1006f5033b6563bd6a4ec` |
| `rules/n5-rules-v1.1-es.pdf` | 199 | `75d91ad9bf17750941a12526373f4b781a01075af03de283c562204cb9804516` |
| `rules/n5-rules-v5.1.1-en.pdf` | 192 | `d84d3be493403fae4cdfc928fe7fae069384cc8249e828a0cae73d16bab6467c` |
| `rules/n5-rules-v5.1.1-es.pdf` | 199 | `deb05dad454bee95e41804090d2ffd0cb6bab2653fdfb0d2671b353f35052139` |
| `rules/n5-rules-v5.2-en.pdf` | 194 | `643ab0b6d7c3e9e5ffbf668543723161f252367e7788af09ec008be19c17851b` |
| `rules/n5-rules-v5.2-es.pdf` | 202 | `9604185cd5777ccc40d4eefa3f5c3d07243e90e4f8e457afb6d0296067680e5c` |
| `rules/n5-rules-v5.3-en.pdf` | 196 | `53921e91c2d3d62ad5f7125abcd4174b2cf937d45320233eed5b6d301b66af3f` |
| `rules/n5-rules-v5.3-es.pdf` | 204 | `7f564c864c6f26d6b218a0477c8afeba99da5c56e1a5369bb259f423689bb28f` |
| `faq/n5-faq-v0.0-en.pdf` | 4 | `a04c5eb43e7acd7272c794a3e7d4bb5fe2595ec04463778eb73c741feef5d043` |
| `faq/n5-faq-v0.0-es.pdf` | 4 | `615f91953634749a7a196f1f0ee3ea36add81ede5243e092bfdb000bc86ead11` |
| `faq/n5-faq-v0.1-en.pdf` | 5 | `7bf26b7d039db7826ef5500b1a2159fe54855b4e632133cab416becee65b85aa` |
| `faq/n5-faq-v0.1-es.pdf` | 5 | `7c40a9ba25b8f61c4e3f40e43b4b15884dfcf27b623baebfc14b003bbeafbf8a` |
| `its/its-18-rules-v2026.09.01-en.pdf` | 132 | `9e16874924112e62d51acf78d622f5c0cf6196064cc36f003b515de9dc448baf` |
| `its/its-18-rules-v2026.09.11-en.pdf` | 142 | `d1700f7f7ebb6c6bd8c2fbfad927c9eee864d170108941032a37f7673c82597f` |
| `its/its-18-rules-v2026.09.11-es.pdf` | 147 | `df7398f8bc99927dc30c86cf5625cb08f8f38db9f3bbba685223c9c4981fa94d` |

The two unchanged N4 Reinforcements PDFs remain separately inventoried under
[Locally available Reinforcements PDFs](#locally-available-reinforcements-pdfs).
The seven filename substitutions preserve the selected source identities:

| Former filename | Current filename |
| --- | --- |
| `n5-rules-v5-3-en.pdf` | `n5-rules-v5.3-en.pdf` |
| `esp-n5-update-5-3.pdf` | `n5-rules-v5.3-es.pdf` |
| `n5-rules-v5-2-en.pdf` | `n5-rules-v5.2-en.pdf` |
| `n5-faqs-v0-1-en.pdf` | `n5-faq-v0.1-en.pdf` |
| `esp-faqs-n5-v0-1.pdf` | `n5-faq-v0.1-es.pdf` |
| `n5-faqs-v0-0-en.pdf` | `n5-faq-v0.0-en.pdf` |
| `Its-rules-season-18-en.pdf` | `its-18-rules-v2026.09.01-en.pdf` |

The six already selected PDF identities still match their maintained byte pins.
Existing citations continue to use ITS **2026.09.01**, including its 132-page
layout. The additional **2026.09.11** English/Spanish covers explicitly state
that version and September 11 update date; their PDF creation metadata is
September 24. These are separate events. The newer files are research inputs,
pending a content/citation review before changing the selected ITS revision.

The locator migration verified all **14 curated PDF declarations** against
their paths, page counts and existing hashes. Two independent v9 exports were
byte-identical; comparison of the complete schema and all **16 SQLite tables**
allowed only the 14 declared `sources.local_path` changes. Both dependent
publications retained their content with updated source fingerprints, using
rollback-protected replacement. The documentation stage passed (Markdownlint,
41-file local link check and static backlog integrity).
Broader source-dependent regressions passed without skips on Windows under
retired VR-0116; the pinned Linux full-assets suite also passed. Linux's missing
source-PDF cases remain skips and were checked independently on Windows for this
bounded obligation. See the [cross-host local acceptance](v1.0-source-coverage-audit.md#v1s-082-bounded-source-review-attribute-definitions-and-dash-prerequisites-2026-11-06).
Hosted CI and final source-wide acceptance remain separate.

## PDF revision-difference intake (2026-11-06)

**Project domain:** Data processing

The new, read-only `tools.audit_pdf_revision_deltas` compares **11 adjacent
revision pairs**: four N5 core transitions in **each** of English and Spanish,
FAQ v0.0 to v0.1 in each language, and ITS Season 18 English 2026.09.01 to
2026.09.11. It requires exact bytes matching the existing ignored
`local/research/pdf/revision-inventory.json` hashes, excludes cover pages, and compares
normalized extracted tokens using nine-token windows. The historical
2026-11-06 results were saved in `local/audits/pdf-deltas-2026-11-06.json`;
new runs default to a fresh UTC run directory under
`local/audits/pdf-revision-deltas/`. Each report is a
**candidate-triage index**, not a line-by-line certified change log: tables,
diagrams, column order, typography, bilingual translations and scenario
applicability require human inspection. Layout shifts produce false positives,
and matches cannot establish semantic equivalence.

### Reviewed revisions and historical correction

- **N5 core v1 -> v1.1:** Both languages show extensive content changes; Jump,
  Climbing Plus and Speedball are prominent extraction candidates. They require
  scoped older-versus-newer semantic comparison before identifying any missing
  current-rule correction.
- **N5 core v1.1 -> v5.1.1:** Small, concentrated differences include the
  Climbing Plus diagram/example in both languages and the Spanish WildParrot
  Disposable value. On physical PDF p. 74, **Spanish v1.1 lists
  `Desechable (3)`**, whereas English v1.1 lists **Disposable (1)**; Spanish
  v5.1.1 changes to **`Desechable (1)`**, aligning with English v5.1.1.
  This is a **historically corrected bilingual profile discrepancy**; it does
  not justify a new current-source SRC entry or retroactive edits to preserved
  v1.1 evidence. The revised Climbing Plus diagrams warrant visual geometry
  inspection before declaring what gameplay correction they make.
- **N5 core v5.1.1 -> v5.2:** Both languages contain broad changes and page
  reflow. The automated report identifies candidates, **not** a reviewed
  exhaustive version changelog or newly confirmed contradiction.
- **N5 core v5.2 -> v5.3:** The change signatures in both languages include
  Infinity Spec-Ops/SpecBall and numerous amended mechanics. Current N5.3
  selection and the reviewed 26 English plus Spanish-specific update subjects
  remain governed by the [N5.3 reconciliation](rules-explanation-audit-1.0-n5.3-reconciliation.md);
  these token diffs do not reclassify existing SRC entries or prove review
  coverage of every changed clause.
- **FAQ v0.0 -> v0.1:** Added text in each language is consistent with the
  previously recorded **nine new, 20 carried-forward** answers. The maintained
  [FAQ question/scope inventory](faq-v0.1-scope-inventory.md) remains the
  semantic authority. Existing Haris, Stealth and Deployable bilingual
  questions (SRC-008/025/026) remain open; no duplicate intake was created.

### ITS 18 hotfix: three confirmed scenario changes

The **2026-09-24** official [English September hotfix
announcement](https://infinityuniverse.com/en/news/its18-hotfix-september)
and [Spanish announcement](https://infinityuniverse.com/es/news/its18-hotfix-september)
identify **The Dig, Double Bind and Crossing Lines**. Direct examination of
both local English PDFs and the later Spanish PDF confirms these versioned
changes, rather than merely the 132-to-142-page reflow:

- **Crossing Lines:** English 2026.09.01 physical p. 64 excludes only Secure
  HVT; 2026.09.11 pp. 65–66 explicitly excludes HVT deployment **and** the
  Classified Deck. Spanish 2026.09.11 pp. 65–66 agrees.
- **Double Bind:** English 2026.09.01 pp. 71–72 states at most one Antenna may
  be destroyed per turn. English 2026.09.11 pp. 74–75 additionally nullifies
  damage to any other Antenna in that turn and permits Engineer/GizmoKit
  targeting; Spanish 2026.09.11 pp. 74–75 corroborates both. The announcement
  also names Main Objective choice timing; that clause needs separate
  old/new bilingual acceptance before migration.
- **The Dig:** English 2026.09.01 pp. 74–77 uses activated Consoles, permits
  Hyperthermal Tech only outside 8-inch spacing limits and has the earlier
  analysis/neutralization sequence. English 2026.09.11 pp. 78–80 instead
  scores own Player Tokens on Consoles, reduces both placement spacings to
  **4 inches for 150-point games**, uses the **Analyze Hyperthermal Tech**
  Skill, replaces an opponent's Console token and requires the player's own
  token on a Tech for Neutralize. Spanish 2026.09.11 pp. 78–80 agrees
  (10 cm / 20 cm distances).

The later ITS covers say **2026.09.11**, but the PDFs' September 24 creation
metadata and official September 24 hotfix announcement are separate provenance
facts; do not invent an effective date for each clause. The currently
published **Battleground pilot** still deliberately pins
`its-18@2026.09.01`. No updated source declarations, citations, scenarios,
runtime interpretations or database artifacts were promoted in this audit.
The [ITS library backlog](TODO.md#its-scenarios-and-game-tools)
owns bilingual .11 adoption, version-specific published scenario/citation
reconciliation and any full-season review.

**Disposition:** Confirmed historical supersession and a later ITS hotfix are
**not automatically simultaneous-source contradictions**. No new unresolved
source conflict was sufficiently substantiated to allocate SRC-034, and none
of SRC-001–033 was closed. A complete bilingual N5 rule-by-rule, FAQ replay,
ITS season-wide semantic or diagram-only audit remains outside the automated
triage; new player-relevant disagreements go to
[the canonical clarification register](official-source-clarifications.md).

## Official N5 publication index

The following dated Corvus Belli English-language posts were identified from the
[official Rules news archive](https://infinityuniverse.com/en/news?category=Rules).
They are **URL-backed** source references, not locally archived, content-hashed
publications. Recheck the archive for additional relevant posts during later audits;
this index is not a guarantee that every N5 change was publicly announced.

| Published | Post | Relevant scope |
| --- | --- | --- |
| 2025-01-09 | [N5: What's new?](https://infinityuniverse.com/en/news/n5-what-is-new) | Edition-introduction explanations; N4-to-N5 context, not current source text |
| 2025-03-18 | [Army update – March 2025](https://infinityuniverse.com/en/news/army-update-march-2025) | Imperial Service and other Army profile updates |
| 2025-04-03 | [Infinity N5: Ruleset update](https://infinityuniverse.com/en/news/infinity-n5-rules-update) | Rules changes and separate Army changes; includes an April 4 Army-fixes appendix |
| 2025-04-24 | [Rules update v5.1.1](https://infinityuniverse.com/en/news/infinity-n5-update-5-1-1) | PDF corrections and explicit N5 version-numbering explanation |
| 2025-05-05 | [Infinity N5 – English Wiki](https://infinityuniverse.com/en/news/infinity-n5-wiki) | Wiki release and contextual reference features, not a gameplay changelog |
| 2025-07-28 | [Army Update – July 2025](https://infinityuniverse.com/en/news/army-update-july) | Army profile changes, including Iguana/Gator Mine Dispensers |
| 2025-10-02 | [Army Update – October 2025](https://infinityuniverse.com/en/news/army-update-october-25) | Returning N5 sectorials and adjusted Army profiles |
| 2025-10-15 | [Army Update October 2025 – Part 2](https://infinityuniverse.com/en/news/army-update-october-2025-part2) | Distinct rules PDF v5.2, FAQ v5.0.0, and Army update scopes |
| 2026-05-27 | [Army Update – May 2026](https://infinityuniverse.com/en/news/army-update-mazebreaker) | Mazebreaker/Corregidor Army profile and sectorial updates |
| 2026-09-01 | [ITS Season 18 + N5.3 Rules Update](https://infinityuniverse.com/en/news/infinity-rules-update-5-3) | Separate N5.3 rules, Army, and ITS Season 18 announcements |

The N5.3 post explicitly identifies Kobra Pistol ammunition as Shock in BS Mode
and DA in CC Mode. It does **not** resolve the printed-versus-Army CC Saving Roll
count discrepancy. The April 2025 update includes both a dated post and a later
appendix: preserve that distinction when associating events with snapshots.

## Unmatched N5 announcements and historical gaps (V1S-012; 2026-11-03)

This is a **historical provenance/disposition register**, not a
new source acquisition, an exhaustive line-by-line audit of all
official posts, or a list of confirmed current defects. The links
and announcement dates in the index above identify the reported
events, but an official claim of a past change is **not** proof of
the current value, the exact transition time or a missing
InfinityDB record. Track announcements by independent rules,
Army/profile, FAQ and ITS scope.

| Announcement group | What can currently be used | Unmatched historical boundary / disposition |
| --- | --- | --- |
| **2025-01-09 N5 introduction** | Official overview of N4-to-N5 changes | No frozen, comparable N4 rule/Army corpus is selected; do not infer a per-profile N4-to-N5 change or a current N5 omission from a primer |
| **2025-03-18 Army** | Dated Imperial Service and cross-faction additions, removals, costs, Fireteam and equipment changes | No pinned immediately preceding and following March Army API snapshots; the September 2026 Army source can show a current profile, not when the named March modification occurred |
| **2025-04-03 rules and April 4 Army-fixes appendix** | Separate published rules changelog and Army change list; the appended April 4 corrections (including Jump/Super-Jump profiles) are a **second dated event** | The local v5.1/v5.2/v5.3 PDFs do not by themselves provide a complete version-specific before/after for every April claim; no matched pre-/post-April Army member pair was verified; do not absorb the April 4 appendix into April 3 chronology |
| **2025-04-24 v5.1.1** | Official minor PDF correction list, including Climb geometry and Jet Propulsion examples; official explanation of N5 version numbering | No **byte-verified local v5.1.1 PDF** was selected for full exact-version comparison (the available files include v5.1, v5.2 and v5.3). A later text/example that agrees does not prove the complete v5.1.1 transition or graphic equivalence |
| **2025-05-05 English Wiki announcement** | Dated announcement of Wiki availability and individual preserved English oldid histories | No complete May 5 Wiki capture; exact oldid timestamps substantiate *individual* pages, not same-day whole-Wiki coverage or retrospective equivalence |
| **2025-07-28 and 2025-10-02 Army updates** | Official dated profile/sectorial change descriptions, including N5-era Reinforcement variants | No pinned pre-/post-update Army snapshot pairs or exhaustive item-to-current-Unit audit; absence of a named historical option in a current snapshot is not automatically a data-ingestion defect |
| **2025-10-15 rules/FAQ and Army changes** | English N5 v5.2 and FAQ v0.0 can support **selected** later-v5.3 comparison; the original 28 FAQ Q&As are independently inventoried | PDF availability does not independently fix the FAQ upload date or provide contemporaneous October Army before/after data; distinct rule, FAQ, ITS and roster contexts must stay separate |
| **2026-05-27 Mazebreaker/Corregidor Army changes** | Dated report of Corregidor division/availability changes and named Dodge (ARM+3)/AP Red Fury changes; current N5.3 and September Army inputs support selected present-state identities | No pinned before/after May Army export; a later repeated announcement is not evidence for a second new Weapon/Skill or a missing current profile; specific division/Fireteam/Unit relationships still require their own source and browser gate |
| **2026-09-01 N5.3 rules, Army, FAQ and ITS** | The 26 English rule items, four additional Spanish-list subjects, 20 Army items and nine added FAQ Q&As have **bounded current-state** dispositions in the [reconciliation](rules-explanation-audit-1.0-n5.3-reconciliation.md#current-reconciliation-inventory-2026-10-29) | No pre-notice Army snapshot, no earlier Spanish N5.2 PDF, and no authenticated original September 18 Wiki ZIP. Source-variant history, exact FAQ upload date, full source-wide/normal-browser coverage and frozen-release acceptance are **not** established by these selected-item reviews |

**Known unresolved comparisons, not generic defect counts:**
The September 18 Army captures are themselves after the
September 1 notice; the selected September 25/29 Army bytes
cannot create a pre-notice delta. The missing original
September 18 English Wiki capture has an expected hash but
no recovered bytes; the selected September 26 replacement
and exact oldid histories prove only their own page provenance.
The Spanish N5.2 rulebook is unavailable; the v5.3 Spanish
PDF supports current bilingual comparisons, not every older
Spanish wording transition. English v5.3 PDF creation
metadata dated August 10, the September 1 update post,
September ZIP acquisition dates and the selected FAQ
date anchor are **different dates for different events**.

**Keep genuine source disputes separate:** the bilingual
N5.3-versus-Army/Wiki Kobra CC profile, Dodge (ARM+3)'s
PDF-versus-Wiki condition, and the announcement's “Breaker
Sniper” label versus the published Breaker Marksman are
already explicitly reviewed/disclosed. The source conflicts
can be real even without a historical transition archive;
they do not justify inventing a missing Weapon/Unit or
silently rewriting imported Army data. Earlier March/April/
July/October/May announcements also contain unpaired
historical profile claims; classify these as **insufficient
historical evidence**, not individually confirmed catalog
defects until a specific current source/publication mismatch
is independently demonstrated.

**Next handling:** keep the initial publication list
non-exhaustive and use the [comparison procedure](#cross-source-reconciliation-procedure)
for any newly discovered official post. An item can advance
to a verified historical delta only with matched exact
source/version identities on both sides; a current gameplay
defect requires separate source-to-storage/API evidence.
V1S-013–022 own broader current-source omissions and their
publication disposition, while V1S-081–095 own the frozen
release gates. No live article was imported into curated
gameplay data by this review.

## Selected Army input for 1.0 (V1S-001; 2026-11-03)

The intended Army input for the current 1.0 completeness review is the
**English September 29, 2026 snapshot**:
`data/raw/JSON 20260929-114335.zip` (59 JSON documents: `metadata.json` and
58 faction documents). Its generated version-3 provenance manifest is
`data/manifests/snapshots/JSON 20260929-114335.json`. The exact archive
SHA-256 is
`f103a7afd02e68d845cc9ce38b1948f46914676bbc6a5e6b790d0a04148b6c75`;
the separately calculated logical content SHA-256 is
`cc2212506489d4c9cc88936219131c6c645c20362219f6751fe1e0d3ef3102b3`.
This selection is also the Army archive identity in the tracked
`data/manifests/symbol-publication.json`.

The manifest records acquisition at **2026-09-29T11:43:35+02:00** from
`https://api.corvusbelli.com/army`, with source
`dataChangedOn=2026-09-03`. The 58 faction documents have the embedded
versions `7.26246.158` (36) and `7.26246.159` (22); these versions and
the source-data date are **not** independently established publication dates
for every profile. The September 25 archives also report identical
archive/content hashes; this does not establish a before/after update.
The selected ZIP's SHA-256 was verified from the staged bytes on
`linux-dev` using the read-only
`tools.activate_synced_assets verify --snapshot "JSON 20260929-114335"`
at `dd071c4d` (job `linux-dev:81e892a77b864c298b6603bff55344a6`).
The source ZIP and acquisition manifest remain ignored external inputs.

This is the **selected review baseline**, not final frozen-release acceptance
or proof that the source has not changed upstream since acquisition.
Do not silently fetch or swap in a newer snapshot. A deliberately approved
source change must reopen affected coverage and rebuild the matched Army/rules
artifacts. The current database/publication identity checkpoint is below;
frozen-candidate rechecks remain in V1S-081 and V1S-084. Source-wide and
browser acceptance remain open.

### Current matched artifacts (V1S-003; 2026-11-03)

At Windows development HEAD `e74b5cb148312e26acf0892d15502ecfd337459e`,
the existing selected Army archive above is paired with these **current
development** identities (SHA-256 of exact local bytes):

- Tracked `data/generated/infinity.db`: `8a5840d1ff632e89de26210ee7bcb47e54c6579c15b5c3436e226702e872d7c8`
  (8,392,704 bytes).
- Tracked schema-v9 `data/generated/rules.db`: `c016006b7eae19e80969f432a590b802bf989b5831bd6cfd1c1f26765bb3800c`
  (1,265,664 bytes).
- Generated, ignored `data/generated/deployed-objects.json`: `f1885134b54633bde8fa2f3512ca16c2dc81d39e780ea0be26f9ca06a3617a9a`
  (1,970,911 bytes).
- Tracked `data/manifests/symbol-publication.json`: `92a27c349c6ac23d81de138ee7bff5d196f0f83caa5846417ebd1d89427a3eb5`
  (478,720 bytes; its Army archive pin matches above).

The ignored paired `infinity.raw.db` is a **development audit artifact**,
not a deployed database; its local hash is not part of release identity.
Read-only `tools.build_deployed_object_publication --check` passed for the
current Army/rules/deployed-object triplet. The baseline reporter with
`--army-archive "data/raw/JSON 20260929-114335.zip"` passed its source
and publication checks and enumerated 23 category rows and 126 source
groups; all still require review. No application model, API, or browser
contract changed in this identity-recording slice.

At the later frozen candidate, remeasure hashes **at that exact commit**
and rerun both checks, source occupancy, matched database/export
identities and release gates. Do not assume this development-state
fingerprint survives subsequent rules/Army curation or that byte-equal
SQLite output is guaranteed across operating systems. A changed source,
pair or projection reopens affected review; V1S-081/084 and final browser
acceptance must use the final release candidate.

### Army source occupancy and canonical payloads (V1S-013; 2026-11-03)

The selected September 29 Army ZIP and the unchanged tracked
`data/generated/infinity.db` were audited against the matched ignored
`data/generated/infinity.raw.db` at development revision
`b893f3fc76906beaf921b85f2ee6740d55d1203e`.
The read-only source-presentation auditor's strict
`--require-no-occupied-gaps` gate passed: **70 normalized source
tables, 441 source fields, and zero occupied values in all 39 fields
classified as potentially unrepresented**. Its maintained policy
reported **zero confirmed schema-level gap families** and **two
intentional semantic scope decisions**. The paired-raw evidence
was available; this was not a skipped clean-checkout verification.
Reports are stored under ignored `local/audits/v1s-013-*.json`.

The independent current application/payload audits yielded:

- **Unit identity and availability:** 920 source Unit rows resolve to
  737 canonical logical Units, including 167 multi-source logical
  identities. There are no invalid representative picks; 133
  Reinforcement and 49 mercenary variants remain nonrepresentative
  source contexts. All 167 repeated logical Units have alternate
  general labels, four have additional nonrepresentative note deltas,
  and the canonical model retains 473 alias occurrences, 30 note
  occurrences and 30 Spec-Ops/TEAM-OPS chart occurrences. Eighteen
  composite Unit-option rows occur across seven logical Units; two
  repeated-Unit collections vary and must retain their Army context.
  The separate Army/faction audit successfully distinguished
  source-list availability from broader declared membership and
  checked the derived application Army identity/mapping contract.
- **Attributes and Profiles:** 5,020 source/profile occurrences
  resolve to 1,108 canonical profile payloads, with 636 payloads
  reused. The source-identity audit recorded 23 source-key semantic
  variations, 297 AVA variations and three logo variations;
  these remain represented per occurrence, not overwritten by the
  representative Unit.
- **Loadouts and costs:** 12,993 source/loadout occurrences resolve
  to 3,448 canonical payloads, with 2,022 reused. The audit found
  16 source-key semantic variations, two points variations and one
  SWC variation. Ordered item/extra relationships and occurrence
  costs remain separate from the shared payload identity.
- **Explicit exclusions:** the 30 selection-chart payloads remain
  visible as source-backed **read-only references**; configuring
  a legal Army List/session is not part of the immutable Unit
  reference model. Source-client `disabled`/`minis` fields
  retain their original data but no speculative roster-builder
  semantics are inferred.

This verifies **schema field occupancy and the audited canonical
projection contracts**, not the material correctness of every
source clause, link or UI page. An unpopulated candidate field
does not prove that all relationship types are complete. In
particular, V1S-014 owns Included option targets and
Peripheral/controller relations, V1S-015 owns Fireteam and
Reinforcement reachability, and V1S-016–022 own cross-source and
normal-browser dispositions. The independent reference-baseline
report still enumerates **23 category rows and 126 source groups
requiring review**; they were not accepted by this slice.
Final frozen-candidate occupancy and data-pair checks remain
V1S-081–095.

The source-presentation, logical-Unit, profile, loadout and
faction audits all exited successfully. Focused Windows tests:
source-presentation **12/12**, Unit semantics **4/4**,
profile semantics **5/5**, loadout semantics **5/5** and
faction semantics **4/4** (**30/30** total). During inspection,
the faction auditor's default JSON stdout was found to fail
under Windows CP1252 when source names contain Ō; a small
CLI-only fix now escapes non-ASCII on stdout, retaining
UTF-8 in file reports. Its new limited-console regression
passed; no Army/rules database, API or browser files changed.
Broader execution for this tooling fix is tracked as
VR-0052 in the active [validation queue](validation-queue.md).

### Army Includes and Peripheral relationships (V1S-014; 2026-11-03)

A read-only comparison on the selected September 29 Army export
at `adea76c1df0d6d370db7ce54093c122c548f4b59`
confirmed the exact application/raw database pair. The legacy
relationship, Peripheral and normalization auditors expected a
single combined schema; current `infinity.db` intentionally omits
source-only normalized tables, while `infinity.raw.db` omits
application projections. Their initial direct attempts against
either file therefore failed on missing tables, **not because
source relationships were missing**. The bounded paired-audit
helper `tools.paired_audit_connection` now opens the application
database read-only, verifies the raw sibling's shared export
metadata/fingerprint and exposes required raw tables through
temporary SQLite views. It preserves the combined-schema
fixture contract, denies an unmatched pair and writes to
neither input. The source-variant and browser runtime models
are unchanged.

- **Includes:** all **949** source Loadout Include edges,
  **2** Profile Includes and **35** shared Unit-option Include
  edges resolve to their respective Army-specific canonical
  targets. The selected source has **zero missing targets,
  cross-logical targets or fallback raw-only values**. The
  same-parent canonical payload comparison correctly preserves
  **23** Loadout Include signature variants across Army
  occurrences: those are contextual information, not
  duplicates to collapse globally.
- **Peripheral definitions and attachments:** **279**
  army-local definitions represent **56 names** and exactly
  **818** option/Loadout attachments; all resolve to a source
  definition with no missing ID or raw fallback. The selected
  source has no profile-level attachments or ambiguous global
  Unit-option Peripheral warnings. **22** reused canonical
  Loadout payloads have semantically differing Peripheral
  attachment signatures; the Army/Loadout occurrence remains
  the owner, not a single canonical payload-wide set. Names
  and `mercs` are diagnostic identity candidates, **not**
  global Peripheral IDs.
- **Controller ownership:** the Army source supplies
  source-local attachment/access information, but does
  not by itself authorize a rules-derived Controller.
  The published current pair has no reviewed
  `application_peripheral_controller_access` rows,
  which is explicitly checked by the normal Unit
  browser acceptance. The API's bidirectional
  Controller/Peripheral linking behavior is separately
  covered using a reviewed synthetic relationship
  fixture; the absence of an inferred live Controller
  link is intentional, not proof of a missing source
  attachment.
- **Structural indirection:** the normalization audit
  confirmed **eight** Army filter-link tables with
  **15,072** rows and **52,554** source weapon-option
  occurrences mapping to **490** templates, with
  **zero dangling template references**. The seven
  canonicalization/provenance link families are retained
  as infrastructure, not extra gameplay relationships.

**Separate historical relation boundary:** the broader source
relation audit enumerates **126** constraints. Its maintained
historical endpoint review for retired Unit IDs
`165, 613, 749, 1503, 1509` is explicitly pinned to
a different source archive
(`858309ea44b6a07f0aadb7bf2856d6c0dfdcb75dbe587b85997ed46c4780e3a3`)
from the selected current archive
(`f103a7afd02e68d845cc9ce38b1948f46914676bbc6a5e6b790d0a04148b6c75`).
Applying it directly **still fails closed**. The new
opt-in `tools.audit_relationship_semantics
data/generated/infinity.db --current-only` reports
**eight unresolved constraints referencing those five
source IDs**, without borrowing the prior historical
review; the other **118** relation structures are
canonically resolved. Those eight require source-exact
historical review before being called verified stale,
rather than an invented Unit link or an assumed current
roster defect. This does **not** reopen the independently
resolved Includes/Peripheral attachment identities.
Further cross-source relation review remains in the
1.0 source-gap and release acceptance gates (V1S-016–022).

Focused Windows validation for this bounded implementation:
paired-export adapter **3/3**, existing relationship
semantics **7/7**, Peripheral semantics **6/6**,
normalization semantics **3/3**, normal Unit browser
relationship cohort **1/1** (four source-backed Unit
routes at desktop/mobile widths), and bidirectional
Controller API contract **1/1**: **21/21** passing.
The actual read-only paired-source auditors all exit
successfully in their applicable current-state modes.
This is not a final frozen candidate, a complete Army
List/roster builder, or proof of an N5 gameplay rule from
Peripheral naming alone. Broader committed-state
Linux/CI validation is queued under VR-0053.

### Fireteam, Reinforcement and normal navigation (V1S-015; 2026-11-03)

**Current-source disposition:** the selected Army snapshot's chart, Section
and parent/Unit navigation data reaches the existing publication and ordinary
browser without a newly confirmed missing relationship. The checked application
Army DB is the tracked `data/generated/infinity.db` (SHA-256
`8a5840d1ff632e89de26210ee7bcb47e54c6579c15b5c3436e226702e872d7c8`),
paired with the September 29 source ZIP already pinned above. This is a
read-only development-state review at `6810c6c30db51c79e091704567d08bdfe521ea84`,
not final release or independent roster-legality acceptance.

- **Chart occupancy/availability:** all **58** raw Army-list contexts map
  through the application provenance graph to **57** published Fireteam
  charts (one intentionally shared Back-up chart). All **268** teams
  and **1,249** member rows agree with the raw archive through the
  selected source SHA-256, original chart description, types,
  `min`/`max`/`required`, Wildcard/observation/annotation and
  source-name fields. There are **438** team-type memberships:
  99 CORE, 157 HARIS and 182 DUO. These are descriptions of
  available source composition, **not** complete Army-list legality.
- **Unresolved chart identities remain visible:** **1,237** member
  rows resolve Army-locally and **12** are non-local/unresolved:
  11 exact-slug unresolved placeholders, and one ARJUNA
  global-but-not-Army-local match. In total **13** chart rows
  carry reviewed reference notices; the ARJUNA case has
  overlapping source/context warnings. FTO membership resolves
  **195/197** marked rows; KORSAN REINF. has no matching
  Army-local FTO option and ARJUNA has a source-context mismatch.
  Neither missing local identity nor FTO option is invented.
  These remain publisher-side ambiguity `SRC-009`, not an
  unannounced set of made-up playable units or loadouts.
- **Section-to-parent graph and limits:** **11** application
  Reinforcement Section charts have **46** parent relationships.
  The public chart API marks **45** of those parent-chart
  destinations selectable and retains one as unavailable.
  In **10** parent relationships the source limit disallows
  CORE; in **nine** of those the Section also advertises CORE
  teams. The ordinary Fireteam reference shows the parent
  restriction separately from the Section's team membership,
  including zero/unavailable versus unlimited and absent-chart
  states. No automatic cross-section roster choice follows.
  Main-Section and Section eligibility are not merged.
- **Normal navigation:** Army-overview cards expose their
  applicable parent/child anchors in the regular page
  (keyboard-operable); missing, nonplayable and legacy
  targets do not acquire false links. The selected
  Reinforcement Unit detail links its visible parent Army
  contexts without Developer mode. Fireteam pages show
  source member annotations, parent links, type-limit
  badges and the full verified/not-verified row notices.
  Nine affected charts retain warnings even after Wildcard
  insertion. Original parentheses, type/Fireteam labels
  and FTO markers remain source context rather than
  inferred `Counts as` or guaranteed FTO eligibility.
- **Source authority:** N5.3/ITS references to
  Reinforcements do not independently adopt the N4-origin
  procedural annex. The optional-mode disclosure decided
  in V1S-008 remains unchanged. Static Army catalog and
  Section associations are supported without asserting
  optional Extra legality or interactive roster building.

**Focused checks:** at `6810c6c3`, the pinned raw-chart/public
API test module passed **4/4**, and the Fireteam semantic audit
module **4/4**. Normal Chromium passed **90/90** cases:
33 Section-to-parent links and keyboard navigations across
11 Sections × three viewports; 27 chart-source uncertainty
cases; 24 source-annotation/Wildcard cases; two Army overview
source-link cases; two nonplayable/missing-target fail-closed
cases; one normal Unit parentage case, and one absent-parent
chart safeguard. Total **98 passed, zero skipped/failed**
across these focused selectors. The read-only Fireteam
semantic audit independently exited 0 and saved its
ignored JSON report to `local/audits/v1s-015-fireteam.json`.

**Decision:** no code, data, browser or schema repair is
warranted for the checked current-source projection. The
source ambiguity register `SRC-009` remains open for
publisher clarification and is not reclassified as a
proven InfinityDB bug. In-scope source-wide semantics and
unverified publisher rules are separately owned by
V1S-016–022; final frozen-release browser, accessibility,
full-suite and CI gates are still outstanding.

### Selected rules, FAQ, Wiki and annex evidence (V1S-002; 2026-11-03)

The 1.0 current-reference review selects these **existing local inputs**;
no source was downloaded or silently updated in this pass:

- **Core rules (primary):** English `data/pdf/rules/n5-rules-v5.3-en.pdf`
  and Spanish `data/pdf/rules/n5-rules-v5.3-es.pdf`, both identified
  by their covers as **N5 v5.3**. Exact byte pins and page counts are
  recorded in the [English core identity](#reviewed-english-n53-core-pdf-identity)
  and [remaining PDF identities](#remaining-reviewed-pdf-identities).
  N5 v5.2 English remains comparison evidence, not current authority.
- **FAQ (primary within applicability):** English
  `data/pdf/faq/n5-faq-v0.1-en.pdf` and Spanish
  `data/pdf/faq/n5-faq-v0.1-es.pdf` (both cover v0.1).
  English `data/pdf/faq/n5-faq-v0.0-en.pdf` is pinned historical
  comparison material, not a second current FAQ. All three byte pins
  are in the PDF register and the
  [question-level scope inventory](faq-v0.1-scope-inventory.md).
  ITS-only questions remain separately scoped.
- **Current-capture Wiki research:** English
  `data/wiki/WIKI-en 20260926-200832.zip` (812 members; acquired
  2026-09-26T20:08:32+02:00) and Spanish
  `data/wiki/WIKI-es 20261009-211304.zip` (786 members; acquired
  2026-10-09T21:13:04+02:00). Their generated snapshot manifests
  pin respectively SHA-256
  `c0fe18c165473e3f273efd58aa7ecb0ea0d94ee274189de9361aad175b3de987`
  and `8e4d40f0ad60d9a42c276f90a07253d8bcdbb61ed7839506cf9f91b7c8270be4`.
  Captures do **not** establish a single Wiki publication/effective date.
- **Exact-revision Wiki research:** English
  `data/wiki/WIKI-en-history 20260928-165727.zip` (3,592 members;
  acquired 2026-09-28T16:57:27+02:00), and Spanish
  `data/wiki/WIKI-es-history 20261009-215316.zip` (3,290 members;
  acquired 2026-10-09T21:53:16+02:00). Their manifest SHA-256 values
  are `d49db0515420af297a7349201e8bb7750ecb422048d32bb494273ee1cea78a5d`
  and `ce588e4f7cb70b84ca115a63f66c3c227a0d7f91d89969caa9a1d46e94d9489b`.
  Exact oldid/timestamp evidence remains per page, not per capture.
- **Reinforcements annex (historical only):** The byte-pinned
  `data/pdf/rules/reinforcement-rules-en.pdf` and
  `data/pdf/rules/reinforcement-rules-es.pdf` both explicitly identify
  **N4** on their covers. The
  [annex inventory](../config/validation/reinforcements-source-inputs.json)
  retains the hashes, unknown publication dates and historical-only
  applicability; neither provides verified N5-native annex authority.
  Optional legacy reference and SRC-030 remain separately governed.
- **Supplementary current-season scope:** The existing
  `data/pdf/its/its-18-rules-v2026.09.01-en.pdf` has cover version
  `2026.09.01` and a pinned hash in the PDF register. Its ITS-only
  provisions do not broaden the 1.0 core-reference gate.

Official publication-change evidence is the **2026-09-01** English
[N5.3 update notice](https://infinityuniverse.com/en/news/infinity-rules-update-5-3)
and same-date [Spanish notice](https://infinityuniverse.com/es/news/infinity-rules-update-5-3).
The English notice has separate 26-rule and 20-Army subjects; Spanish
contains four additional language-specific rule subjects. These are
**dated URL-backed announcements**, not local byte-pinned PDFs or
standalone gameplay authority. Earlier official N5 notices remain in
the [publication index](#official-n5-publication-index) for historical
change reconciliation. The v5.3 PDF creation metadata is dated
2026-08-10, while FAQ v0.1 creation metadata is dated 2026-08-25;
**neither is independently established publication time**. The
September 1 announcement date and acquisition dates must not be
substituted for a document's effective date.

All selected local PDF/Wiki/annex hashes were remeasured against the
existing maintained pins on 2026-11-03. The read-only
`tools.audit_1_0_reference_inputs` completed successfully with the
selected English/Spanish Wiki captures and histories, English core
and FAQ files (results under ignored
`local/audits/v1s-002-source-evidence.*`). These are source
**identity and scope selections**, not exhaustive clause equivalence,
Wiki historical completeness, Army-change reconciliation or browser
acceptance. A later explicitly approved acquisition reopens affected
review; V1S-081 performs final frozen-candidate input confirmation.

## Historical Army evidence

The community-maintained
[`massayoshi/infinity-army-backup`](https://github.com/massayoshi/infinity-army-backup)
repository is an **unofficial backup of public Army API data**. Its `n5/` directory
contains a general `army.json` and per-faction directories with multiple
**version-named** JSON snapshots (as well as mutable convenience files).
Consequently, it can corroborate how Army data changed within N5; it is not an
official clarification, guaranteed complete changelog, or source of current authority.
The project's README describes personal backup use and disclaims affiliation with
Corvus Belli. Keep these research inputs outside published assets and databases
unless rights and project policy explicitly permit their use.

For a historical comparison, record at least the repository commit SHA, the
version-named file path, embedded Army version, faction identity, SHA-256 of the
actual JSON bytes, and the commit's date. **Do not** infer a publication date from
the version string, a Git commit timestamp, or the mutable `<faction>.json` alias
alone. Do not assume the archive captures every intervening Army state.

## Cross-source reconciliation procedure

For each suspected discrepancy or missing rule:

1. **Identify the claim and scope**: domain, Unit/Weapon/Skill/mode, current game
   edition, rules/Army/FAQ version, ITS season when applicable, and intended date.
2. **Check the current source values** in the pinned Army API snapshot and the
   exact rules PDF printed page/chart; inspect any relevant FAQ/errata and annex.
3. **Check the exact Wiki revision**, not just the current live page, and distinguish
   its revision ID/time from the archive acquisition date.
4. **Search the official update history** for a named change or clarification. Record
   the post date, URL, specific section, and whether it describes Army, rules,
   FAQ, or ITS. An announcement is change evidence, not automatic supersession.
5. **Compare older N5 states** where they exist: earlier PDFs/FAQs, older Wiki
   `oldid` revisions, and historical Army API snapshots. Use full identity/mode
   alignment rather than name-only matching. Track additions, removals, renamed
   entities, notation changes, and actual gameplay changes separately.
6. **Classify the outcome** as current agreement, reviewed equivalent notation,
   historical supersession, genuine unresolved cross-source conflict, or insufficient
   evidence. If sources conflict, retain each original value and citation; do not
   silently select one based only on recency.
7. **Promote only reviewed findings** to maintained data and durable contracts.
   Put intermediate diffs and raw comparison evidence in ignored `local/audits/`.
   Normal builds/tests must remain offline and must not fetch these sources.

When recording a finding, preserve `source kind`, `URL/path`, `publication or
version ID`, `publication date`, `acquisition date`, `exact revision/commit`,
`hash when bytes exist`, `scope`, `observed value`, and `interpretation/status`.
For a source announcement, record each independent changelog section as a
separate scoped claim; never treat ITS-only changes as core N5 rules.

## Reviewed English N5.3 core PDF identity

**Local verification, 2026-10-30:** The supplied
`data/pdf/rules/n5-rules-v5.3-en.pdf` identifies N5 v5.3 on its cover and
contains 196 file pages. Its SHA-256 is
`53921e91c2d3d62ad5f7125abcd4174b2cf937d45320233eed5b6d301b66af3f`,
matching the previously reviewed Restrictions source manifest.
Both `n5-core-v5.3-pdf` declarations, in the Core and Hacking Programs
collections, now carry this byte pin. The source-evidence auditor reports
`declared-hash-match` against the supplied file and displays the actual pin
status in Markdown as well as JSON.

The pin identifies the local review input; source-section coverage and the
final 1.0 input freeze remain separate gates. Publication-date metadata and
gameplay content retain their previous values. The tracked v9 rules database
and paired deployed-object publication were refreshed together; see
[the artifact contract](data-model.md#restriction-persistence-and-version-aware-api-v9-locally-promoted).

## Remaining reviewed PDF identities

**Project domain:** Data processing

**Local verification, 2026-10-30:** The remaining selected PDF declarations
now carry byte pins. The supplied files identify the following versions on
their covers; page counts below are file pages, not printed citation pages.

| Source ID | Cover version | File pages | SHA-256 |
| --- | --- | --- | --- |
| `n5-core-v5.3-es-pdf` | N5 v5.3 | 204 | `7f564c864c6f26d6b218a0477c8afeba99da5c56e1a5369bb259f423689bb28f` |
| `n5-faq-v0.1-en-pdf` | FAQ v0.1 | 5 | `7bf26b7d039db7826ef5500b1a2159fe54855b4e632133cab416becee65b85aa` |
| `n5-faq-v0.1-es-pdf` | FAQ v0.1 | 5 | `7c40a9ba25b8f61c4e3f40e43b4b15884dfcf27b623baebfc14b003bbeafbf8a` |
| `n5-faq-v0.0-en-pdf` | FAQ v0.0 | 4 | `a04c5eb43e7acd7272c794a3e7d4bb5fe2595ec04463778eb73c741feef5d043` |
| `its-season-18-en-pdf` | 2026.09.01 | 132 | `9e16874924112e62d51acf78d622f5c0cf6196064cc36f003b515de9dc448baf` |

The Spanish core and ITS hashes match the frozen S17/S16 entries in the
[audit source register](rules-explanation-audit-1.0-sources.md).
The three FAQ hashes match the independently reviewed
[question inventory](../config/validation/n5-faq-v0.1-question-inventory.json).
All 12 declarations for the six selected PDF identities, including the English
core above, are now pinned consistently across collections. This adds nine
previously absent fingerprints; the ITS collection already carried its pin.
No publication-date anchor, historical/current applicability or gameplay text
changed. These are local byte-identity checks, separate from live authority,
source-section coverage and the final release input freeze.

## Reviewed Surprise Attack occurrence modifiers

**Project domain:** Data processing

**Pinned-source review, 2026-10-30:** English N5.3 printed p. 114 and
Spanish printed p. 88 agree that the profile's Surprise Attack negative
MOD applies to the attacked target's Face to Face ARO Roll. The attacker
must begin the Order in Marker form or Hidden Deployment, declare an eligible
Attack and be in the Active Turn. An explicitly named Attribute restricts
the MOD to that Attribute; these cases are not inferred from unqualified
`-3/-6` extras. The exact PDF byte identities are recorded above.

The English history archive `WIKI-en-history 20260928-165727.zip`
(SHA-256 `d49db0515420af297a7349201e8bb7750ecb422048d32bb494273ee1cea78a5d`)
contains `_history/oldid/3943.html`, identifying
[Surprise Attack revision 3943](https://infinitythewiki.com/index.php?title=Surprise_Attack&oldid=3943).
Its marked N5.2 replacement agrees on Face to Face ARO Rolls; the retained
original text refers more broadly to Skill Rolls and is historical evidence,
not the selected scope. The existing multiple-attacker FAQ (English v0.0
p. 1; English/Spanish v0.1 p. 2) keeps each attacker's modifier separate.
No FAQ date gate or gameplay interpretation changed.

The paired September 29 Army application/raw databases contain 767 direct
Skill-191 rows: 762 with extra 6 (`TEXT: -3`) and five with extra 7
(`TEXT: -6`). Every observed signature has exactly one extra and no raw
override. The curated family now binds these exact IDs/types/values to the
conditional target scope; unrelated or future signatures remain unresolved.
This is a review of pinned local evidence, not a live publication refresh,
historical Army delta, Unit-use count or complete variant-index acceptance.

## Locally available Reinforcements PDFs

**Availability check, 2026-10-21:** The local files below are present and readable,
but their covers explicitly identify **N4**, not N5. Both contain five file pages.
Their presence does not supply an edition-verified current N5 annex or
establish N5-era applicability for these N4 documents.

| Local research file | Exact SHA-256 | Reviewed identity |
| --- | --- | --- |
| `data/pdf/rules/reinforcement-rules-en.pdf` | `7c8c93c640e22ce33a8c71069a98f4daff0b1f430548db3c62c70a63252c2ba0` | English N4 Reinforcement Rules – Extra; cover, file page 1 |
| `data/pdf/rules/reinforcement-rules-es.pdf` | `ef2d6c67486e37336900a9e54fcc357bfdef4a185dc559c6ba1279274e6f41bf` | Spanish N4 Reglas de Refuerzos – Extra; cover, file page 1 |

No printed publication/version date was established by this availability check.
PDF creation metadata is not a publication date. Preserve the N4 edition as
verified **source provenance**; the optional N5-era Extra is now documented
through a separately labelled N4-origin reference, without claiming those
procedures were officially revised or adopted unchanged for N5. Do not infer
an N5-specific Commlink or Request Reinforcements rule from a filename.

**Offline identity verification, 2026-10-30:** Both files still match the
reviewed hashes above. The audit-only
[source inventory](../config/validation/reinforcements-source-inputs.json)
now pins these N4 identities for `tools/audit_1_0_reference_inputs.py`.
Its version-3 report distinguishes verified historical bytes, missing ignored
files and unresolved N5 authority. A mismatch fails rather than assigning the
reviewed edition to changed bytes. This verifies availability/identity only;
it neither refreshes official online authority nor adopts N4 procedures in N5.
Publication dates remain unestablished. See [validation](testing.md#10-source-evidence-baseline).

**ITS Season 18 applicability check, 2026-10-28:** The locally archived official
`data/pdf/its/its-18-rules-v2026.09.01-en.pdf` identifies itself as version
**2026.09.01**, last updated September 1, 2026 (file page 1). Its printed
page **27** explicitly offers **Reinforcements** as an optional Tournament
Extra and refers readers to the **Reinforcements Annex**. This is positive
evidence that the Extra remains an available current ITS mode, not evidence
that the existing N4 Annex's Commlink or Request Reinforcements mechanics
were adopted unchanged in N5. The core N5.3 Game Modes table (p. 6)
also names games with Reinforcements but does not supply their procedures.

- Current official ITS Extra listing:
  <https://infinityuniverse.com/games/infinity/its/tournament/e6ae05f22-we-are-back>
- Official N4-era Reinforcements PDF:
  <https://downloads.corvusbelli.com/infinity/rules/reinforcement-rules-en.pdf>
- Explicitly N4-scoped Wiki annex revision:
  <https://infinitythewiki.com/index.php?title=Infinity_Reinforcements&oldid=3614>

**Additional N5-era official Army evidence, checked 2026-10-28:**
Corvus Belli's [March 18, 2025 Army update](https://infinityuniverse.com/en/news/army-update-march-2025)
modifies Reinforcement variants (for example Azra'il, Vector and Nightshade).
The [October 2, 2025 N5 Army update](https://infinityuniverse.com/en/news/army-update-october-25)
explicitly describes recovered profiles as adapted to N5 and includes
Reinforcements profiles, such as Aquila Guard and Swiss Guard. The
[October 15, 2025 follow-up](https://infinityuniverse.com/en/news/army-update-october-2025-part2)
also adjusts Reinforcement variants. These establish that official N5 Army
data continued to include Reinforcements; they do **not** supply an
annex version, Commlink's precise N5 effects, or legal roster composition
semantics. The 2026-10-28 Wiki check found an N4 Annex label.

**Unresolved source boundary, with usable optional reference:** ITS 18 calls
for an Annex without identifying its edition; N5-era Army updates support
Reinforcement profiles without establishing a new procedural text. The separate
`reinforcements-extra-n4-reference` collection publishes an explicitly
**N4-origin** account at `/rules/reinforcements-extra`, `/skills/commlink`
and `/skills/request-reinforcements` for players choosing the optional mode.
Its reviewed source/interaction coverage does **not** claim that Corvus Belli
reissued or adopted every N4 procedure unchanged for N5. The historical
0.7.0 exception remains part of the historical interaction scope; the distinct
1.0 candidate now includes the optional references. Seek an edition-verified
Annex or official adoption ruling and recheck any differences before promoting
legacy procedures to N5-native authority. Do not call the Extra obsolete.

## Reviewed 1.0 structured Skill chart provenance

**Scope:** Martial Arts, Booty and MetaChemistry only; this is a completed
source comparison, not a general N5 history-completeness claim. The English
N5.3 rules PDF (`data/pdf/rules/n5-rules-v5.3-en.pdf`, SHA-256
`53921e91c2d3d62ad5f7125abcd4174b2cf937d45320233eed5b6d301b66af3f`)
is the current core-rules baseline. The independently retained English Wiki
revision archive is `data/wiki/WIKI-en-history 20260928-165727.zip`
(SHA-256 `d49db0515420af297a7349201e8bb7750ecb422048d32bb494273ee1cea78a5d`).
Its `_history/index.json` supplies revision timestamps and exact
`_history/oldid/*.html` members. The archive's **2026-09-28 acquisition date**
is not the date of the Wiki rule text.

The latest revisions represented in that archive are:

- **[Booty, oldid 3852](https://infinitythewiki.com/index.php?title=Booty&oldid=3852)**
  (2025-10-28 16:18:36 UTC; archived member SHA-256
  `6d3cb26f768299ba7329ec55fd61f798b8d7abd83320f410ad97c403ea4360eb`).
  Reviewed N5-era revisions: 3061, 3099, 3447, 3848, 3852.
- **[Martial Arts, oldid 3707](https://infinitythewiki.com/index.php?title=Martial_Arts&oldid=3707)**
  (2025-06-20 15:00:31 UTC; archived member SHA-256
  `5634bc1537910e90afa0b99364791923860e5d3dbd3d4bef411632e05518bc3c`).
  Reviewed N5-era revisions: 3098, 3216, 3444, 3705, 3707.
- **[MetaChemistry, oldid 3855](https://infinitythewiki.com/index.php?title=MetaChemistry&oldid=3855)**
  (2025-10-28 16:20:37 UTC; archived member SHA-256
  `a4c068f202cbe786cf7df49778eab864055b93ccaa283ec9fdec6045dca83dd4`).
  Reviewed N5-era revisions: 3100, 3101, 3855.

The **16 Booty outcomes, 5 Martial Arts levels and 12 MetaChemistry outcomes**
retain their game-relevant values throughout these inspected N5-era Wiki
revisions, in the archived latest pages, and in the N5.3 PDF
(Booty printed pp. 86-87, Martial Arts pp. 100-101, MetaChemistry p. 101).
Army's compact `+1SD` notation and the Wiki/PDF `+1 SD` denote the
same bonus, but **+1 SD and +1B remain different rules**. Martial Arts L3
grants the former, L4 the latter, and L5 both; the PDF's additional-die,
discard, target-allocation and Disposable-use qualifications apply.
Booty and MetaChemistry are optional, additive Deployment Skills, not
replacements for existing equipment/Skills. Booty resolves after Model
placement; MetaChemistry specifies **immediately** after placement and
**one roll**. Booty results 12/16/18/20 retain TAG-specific branches,
and MetaChemistry results 16-20 retain both typed components/parameters.

**Changes to context, not chart values:** Martial Arts revision 3705
(2025-06-20) introduced the clarifying Sibylla advice about assigning
the extra die when Burst is distributed; 3707 corrected example
formatting around `+1 B`. Booty revision 3848 and MetaChemistry
revision 3855 (2025-10-28) expose the October 2025 Deployment
repositioning FAQ alongside their otherwise unchanged charts. Booty
revision 3852 relabels the FAQ heading. Do not interpret an embedded
FAQ block as a new chart-specific rule or as evidence that the chart
itself was revised on the FAQ's publication date.

The general Deployment repositioning ruling appears in **N5 FAQ v0.0**
(version-associated update anchor 2025-10-15; exact PDF publication day unverified;
English PDF `data/pdf/faq/n5-faq-v0.0-en.pdf`,
SHA-256 `a04c5eb43e7acd7272c794a3e7d4bb5fe2595ec04463778eb73c741feef5d043`)
and is carried forward without a substantive change to the ruling in
**N5 FAQ v0.1** (selected from 2026-09-01; English PDF
`data/pdf/faq/n5-faq-v0.1-en.pdf`, SHA-256
`7bf26b7d039db7826ef5500b1a2159fe54855b4e632133cab416becee65b85aa`).
Both cite **printed p. 1, file page 2**. The rule constrains repositioning
after a Roll or measurement of the affected game elements, with the
Fireteam Coherency Check as an example. Neither FAQ establishes a
separate Booty/MetaChemistry roll mechanic. The archived Wiki's embedded
FAQ still names **v0.0.0 (October 2025)**; it must not be cited as the
later v0.1 publication even when the ruling agrees.

The FAQ's BS Attack clarification also says that `+1 SD` does not
normally apply to Long Skills. N5.3's **Berserk** rule on printed p. 86
explicitly permits `(+1 SD)` during that Long Skill. Preserve the
specific Berserk exception; do not interpret the general FAQ sentence
as removing Martial Arts' distinct CC modifiers.

This comparison does not infer that the Wiki revisions were edited for
the 2026-09-01 N5.3 update. No selected archived page has a revision
dated after 2025. The dated N5.3 announcement, rules PDF, FAQ update,
Wiki revision timestamps and September archive acquisition are separate
events. The existing Army-chart tests pin published source rows, not
complete historical Wiki content; this research does not change the
Army import or introduce game-session roll selection.

## Reviewed 1.0 Weapon Trait evidence boundary

The read-only `tools/audit_weapon_trait_cross_sources.py` retains nine historically
reviewed N5 v5.3 Weapon Trait identities against archived `Weapon_Chart` Wiki
revision `4083` (exact payload hash in `config/validation/weapon-trait-wiki-review.json`).
After correcting the tall Cybermine cell extraction, **eight** PDF/Army Trait
candidates remain; Cybermine now compares as a **reviewed notation equivalent**.
For the nine retained cases, the current Wiki agrees with the PDF for seven, Army
for Kobra Pistol (CC Mode), and **both** for Cybermine. These are corroboration
counts, not winning votes. Cybermine's printed chart on p. 181 and Mines prose
on p. 72 both explicitly identify its Comms Attack. Older report evidence still
records the prior extraction truncation; the current audit does not hide either
source's actual notation.
The archive's Kobra entry includes a separately identified superseded profile,
which cannot override the current one.

The [April 2025 N5 rules update](https://infinityuniverse.com/en/news/infinity-n5-rules-update)
explicitly replaced `Technical Weapon` with `BS Weapon (WIP)` in the
Pheroware chart and revised Endgame. The v5.3 PDF and archived Wiki reflect
this; current Army properties still carry `Technical Weapon`. The
[September 2026 N5.3 update](https://infinityuniverse.com/en/news/infinity-rules-update-5-3)
changes Kobra Pistol's ammunition to Shock (BS) and DA (CC). The explicit
DA rule (N5.3 p. 64) requires **two Saving Rolls per hit**; the PDF's one-roll
CC Mode chart cells (pp. 68, 182) remain contradictory, while Army and Wiki
show two. **Anti-materiel** is a separate open question: Army/Wiki show it,
the PDF omits it, and DA alone does not imply it.

The exact-PDF-pinned `semanticReview` results in
`config/validation/weapon-trait-wiki-review.json` classify all nine comparison
rows while preserving their raw source fields: **eight explained** and
**one partially explained** interpretation. The evidence below distinguishes
historical terminology, the chart legend, and current-source differences.

### N4 terminology provenance and N5 chart-reference legend

The official **Infinity N4 v1.1** rulebook (printed p. 43, *Types of Weapons*)
defines `Technical Weapon` as a BS Weapon using **WIP** instead of BS, and
`Throwing Weapon` as a BS Weapon using **PH** instead of BS. Its Weapon Chart
also prints those terms (notably printed pp. 164 and 170). These are genuine
N4 terms, providing an evidenced historical origin for their persistence in
Army's N5 properties; the N5.3 PDF instead uses `BS Weapon (WIP)` and
`BS Weapon (PH)`. Do not treat this as proof that every older profile is
otherwise mechanically identical to its N5 counterpart.

**N4 provenance:** *Infinity N4 Rulebook*, v1.1, supplied as
`infinity-rules-en-v1-1.pdf`, SHA-256
`48d822684ba1cd7a2a1e11571a836f0223928a50229e03837cf57da2674d28d0`;
printed pp. 43 and 171. This is a **prior-major-edition comparison source**,
not an N5 authority and not a source file to publish with InfinityDB.

Both the **N4 chart legend** (printed p. 171) and the **N5.3 chart legend**
(printed p. 176) explicitly define the reference markers:

- `[*]`: additional explanation in **Weaponry**.
- `[**]`: additional explanation in **Ammunition**.
- `[***]`: additional explanation in **Skills and Equipment**.

The legend determines the *section category* in that publication; the specific
rule target still depends on the weapon, mode, and relevant text. These markers
are cross-references, **not gameplay Traits**. Under the N5.3 legend, the
Army `[**]` versus PDF/Wiki `[*]` for PARA Mine denotes Ammunition versus
Weaponry, not merely different spellings. Whether Army intends the same legend
still needs verification. Preserve both source values.

### Reviewed current-source differences

- **Cybermine:** PDF pp. 72, 181 confirm `Comms Attack`. The corrected seven-line
  chart extraction includes `Deployable` and `[*]` and matches Army after the
  maintained spelling and State notation equivalences; this is not a missing rule.
- **Drop Bears (BS Mode):** N5.3 pp. 71, 181 use `BS Weapon (PH)`. The term
  `Throwing Weapon` does not occur in the supplied N5.3 PDF; the imported Army
  BS profile contains **both** `BS Weapon (PH)` and the older N4-defined
  `Throwing Weapon`. The curated Drop Bears reference now explains both distinct
  placement modes and links the historical label to its N5 classification,
  without introducing an additional gameplay effect or mutating Army metadata.
- **PARA Mine:** N5.3 p. 181 prints `[*]`, with the Mines-specific rules on
  p. 72; Army prints `[**]`. The N5.3 legend makes these Weaponry versus
  Ammunition references respectively. The reviewed `weapon:para-mine` card
  now links to both applicable rules and identifies the mismatch; why Army
  uses `[**]` remains unresolved under SRC-013.
- **WildParrot:** N5.3 pp. 74, 181 explicitly list `Non-Lethal`, and the weapon
  uses E/M Ammunition and operates like an E/M Mine. Army omits that explicit
  Trait; preserve this difference rather than silently adding a property.
- **PT: Endgame/Eraser/Mirrorball:** the April 2025 announcement replaces
  `Technical Weapon` with `BS Weapon (WIP)`; the old term does not occur in the
  supplied N5.3 PDF, but is explicitly defined in N4 v1.1. Endgame also gains
  `Double Shot`, missing from current Army properties; the published PT: Endgame
  reference explains that it may add +1 Burst during the Active Turn by using
  both `Disposable (2)` charges and discloses the difference without rewriting
  the imported profile.
  Whether Army's omission is intentional remains open under SRC-016.
- **Sepsitor Plus:** N5.3 p. 187 prints `[*]`, referring to the Sepsitor family
  prose on p. 73. The curated `weapon:sepsitor-plus` record cites the legend,
  chart and Weaponry rules and discloses Army's omission; why Army omits the
  marker remains unresolved under SRC-014. A name-specific matching issue in
  Army is a *hypothesis*, not an observed implementation cause.

This review does **not** change imported source metadata, assume that an
implicit effect is the same as an explicitly listed Trait, or establish
complete special-weapon prose links. The remaining work stays in
`docs/TODO.md`. New generated evidence belongs in ignored `local/audits/`;
legacy `docs/audits/` evidence should be moved to `local/archive/`.
