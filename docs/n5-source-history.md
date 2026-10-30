# N5 source and update history

**Project domain:** Data processing

This is a **discovery index and reconciliation procedure** for InfinityDB 1.0 source
research, not a claim that each historical change has been incorporated or verified.
The currently selected, versioned sources remain the primary evidence for current
rules and profile values. Never turn a dated announcement into a silent rules override.

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
   Put intermediate diffs and raw comparison evidence in ignored `docs/audits/`.
   Normal builds/tests must remain offline and must not fetch these sources.

When recording a finding, preserve `source kind`, `URL/path`, `publication or
version ID`, `publication date`, `acquisition date`, `exact revision/commit`,
`hash when bytes exist`, `scope`, `observed value`, and `interpretation/status`.
For a source announcement, record each independent changelog section as a
separate scoped claim; never treat ITS-only changes as core N5 rules.

## Reviewed English N5.3 core PDF identity

**Local verification, 2026-10-30:** The supplied
`data/pdf/rules/n5-rules-v5-3-en.pdf` identifies N5 v5.3 on its cover and
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

## Locally available Reinforcements PDFs

**Availability check, 2026-10-21:** The local files below are present and readable,
but their covers explicitly identify **N4**, not N5. Both contain five file pages.
Their presence does not supply an edition-verified current N5 annex or close the
Reinforcements task in [TODO](TODO.md#rules-and-reference-completeness).

| Local research file | Exact SHA-256 | Reviewed identity |
| --- | --- | --- |
| `data/pdf/rules/reinforcement-rules-en.pdf` | `7c8c93c640e22ce33a8c71069a98f4daff0b1f430548db3c62c70a63252c2ba0` | English N4 Reinforcement Rules – Extra; cover, file page 1 |
| `data/pdf/rules/reinforcement-rules-es.pdf` | `ef2d6c67486e37336900a9e54fcc357bfdef4a185dc559c6ba1279274e6f41bf` | Spanish N4 Reglas de Refuerzos – Extra; cover, file page 1 |

No printed publication/version date was established by this availability check.
PDF creation metadata is not a publication date. Preserve these as historical
comparison inputs; verify the intended N5 source and applicability before curation.
Do not infer current Commlink or Request Reinforcements mechanics from a filename.

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
`data/pdf/its/Its-rules-season-18-en.pdf` identifies itself as version
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

**Unresolved source boundary:** ITS 18 calls for an Annex without supplying a
version identifier in its p. 27 cross-reference. The N5-era official Army updates
confirm maintained source variants but do not identify the governing procedures.
We have not established an official N5-applicable revision of that Annex, nor
an official adoption statement for the N4 text. Do not mark `skill:commlink` reviewed in the 1.0 candidate,
treat the old exception as a current N5 decision, or claim Reinforcements is
obsolete. Verify the annex revision or obtain an explicit ruling before
curating its procedural Skill effects as N5.

## Reviewed 1.0 structured Skill chart provenance

**Scope:** Martial Arts, Booty and MetaChemistry only; this is a completed
source comparison, not a general N5 history-completeness claim. The English
N5.3 rules PDF (`data/pdf/rules/n5-rules-v5-3-en.pdf`, SHA-256
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
English PDF `data/pdf/faq/n5-faqs-v0-0-en.pdf`,
SHA-256 `a04c5eb43e7acd7272c794a3e7d4bb5fe2595ec04463778eb73c741feef5d043`)
and is carried forward without a substantive change to the ruling in
**N5 FAQ v0.1** (selected from 2026-09-01; English PDF
`data/pdf/faq/n5-faqs-v0-1-en.pdf`, SHA-256
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
rows while preserving their raw source fields: **five explained** and
**four partially explained** interpretations. The evidence below distinguishes
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
  now links to both applicable rules and identifies the mismatch; the Army
  marker's intent remains unresolved.
- **WildParrot:** N5.3 pp. 74, 181 explicitly list `Non-Lethal`, and the weapon
  uses E/M Ammunition and operates like an E/M Mine. Army omits that explicit
  Trait; preserve this difference rather than silently adding a property.
- **PT: Endgame/Eraser/Mirrorball:** the April 2025 announcement replaces
  `Technical Weapon` with `BS Weapon (WIP)`; the old term does not occur in the
  supplied N5.3 PDF, but is explicitly defined in N4 v1.1. Endgame also gains
  `Double Shot`, missing from current Army properties; the published PT: Endgame
  reference discloses that difference without rewriting the imported profile.
- **Sepsitor Plus:** N5.3 p. 187 prints `[*]`, referring to the Sepsitor family
  prose on p. 73. Army's omission remains visible. A name-specific matching
  issue in Army is a *hypothesis*, not an observed implementation cause.

This review does **not** change imported source metadata, assume that an
implicit effect is the same as an explicitly listed Trait, or establish
complete special-weapon prose links. The remaining work stays in
`docs/TODO.md`. New generated evidence belongs in ignored `local/audits/`;
legacy `docs/audits/` remains supported.
