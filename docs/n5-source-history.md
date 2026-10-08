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
  `Throwing Weapon` does not occur in the supplied N5.3 PDF; Army retains the
  N4-defined term. This establishes historical terminology provenance, not an
  inferred additional N5 Trait.
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
  `Double Shot`, missing from current Army properties; that separate difference
  remains open for presentation.
- **Sepsitor Plus:** N5.3 p. 187 prints `[*]`, referring to the Sepsitor family
  prose on p. 73. Army's omission remains visible. A name-specific matching
  issue in Army is a *hypothesis*, not an observed implementation cause.

This review does **not** change imported source metadata, assume that an
implicit effect is the same as an explicitly listed Trait, or establish
complete special-weapon prose links. The remaining work stays in
`docs/TODO.md`. Generated reports belong in ignored `docs/audits/`.
