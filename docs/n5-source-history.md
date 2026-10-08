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
