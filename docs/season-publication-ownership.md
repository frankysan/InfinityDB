# Season source and publication ownership

**Project domains:** Data processing, Web backend, Web frontend

The selected runtime registers one current ITS 18 publication (2026.09.11).
Other seasons remain unregistered. The phased P3 implementation
and its exact-SHA acceptance results remain in Git history and
[testing evidence](testing.md), not in this ownership contract.

This document defines the current boundary between N5 core and
season-scoped ITS publications, including source authority, citation
ownership, exact selection and cross-domain applicability. It does not
serve as a migration checklist or release-acceptance record.

**Implemented source-family behavior:** Routine player-facing ITS selection
chooses a season and automatically uses its explicitly declared current
revision. Superseded facts and exact provenance remain in the single curated
source-family file, but historical revisions are not separately selectable or
required as runtime publications. Future history/replay support is deferred;
see [the data model](data-model.md#accepted-authoring-direction-one-source-family-version-tagged-facts).

## Existing source and runtime inventory

The complete build loads reviewed curated Rules and ITS sources, but the
Rules exporter accepts only N5-owned collections. ITS-authored Season 18
facts project the current revision into `its_18.db`. Their current
authority is:

- `n5-core-v5.3.json` — `core-rules`, `n5-core-v5.3`, effective
  2026-08-10. Owns canonical N5 rules and four core scenario definitions:
  Annihilation, Domination, Supplies and Firefight. Scenario publication
  selection is `n5-core@5.3`.
- `n5-faq-v0.1.json` — `faq`, `n5-faq-v0.1`, effective
  2026-09-01. Owns reviewed N5 FAQ rulings and selected official citations,
  including rulings narrowly applicable to core Supplies or Annihilation.
- `n5-hacking-programs-v5.3.json` — `hacking-programs`,
  `n5-hacking-programs-v5.3`, effective 2026-08-10. These are N5
  reference definitions, not ITS-season-owned material.
- `reinforcements-extra-n4-reference.json` — `annex`, a qualified
  N4-origin optional-mode reference in N5 context. It cites N5 and ITS 18
  as evidence for availability, but explicitly does not establish that its
  older mechanics are universally binding in N5 or a given ITS event.
- `data/curated/its/n5-its-season-18.json` — `its`, a single
  source-family file with current collection `its-season-18-2026.09.11`
  (effective 2026-09-24) and twenty reviewed hotfix missions, including
  Battleground, B-Pong, Akial Interference, Evacuation, Neutralization,
  Provisioning, Area of Interest, Data-Harvest, Last Launch, Corporate
  Appropriation, Outbreak and Critical Intervention. The original
  2026.09.01 Battleground facts, policies, citations, source descriptors
  and original file digest are retained as tagged historical evidence.

The selected `rules_n5.db` owns N5/FAQ/annex data. `its_18.db` owns
the current ITS 18 mission publication. A shared scenario slug across
seasons does not merge records; historical source citations remain distinct.

## Ownership decisions

1. **N5 core:** `rules_n5.db` owns canonical N5 rules, skill/equipment/
   weapon definitions, Orders/AROs, core game-mode definitions, scenario
   component vocabulary, core scenario publications, and reviewed source
   relationships. N5 Hacking definitions remain core even when authored in a
   separate curated collection.
2. **Official N5 FAQ:** `rules_n5.db` owns rulings published under the N5
   FAQ authority. Scenario-specific `applicability.scenarioIds` does **not**
   change ownership. In particular, the Supplies marker-state and
   Annihilation Ancillary rulings stay N5 FAQ-owned.
3. **ITS seasons:** each registered ITS season owns its current mission
   definitions, geometry, game-size configurations, scenario membership,
   Extras and tournament constraints. `its_18.db` publishes twenty
   reviewed hotfix missions; historical Battleground facts remain in
   curated revision tags, not a runtime database. Other seasons get
   independent ownership; no current ITS 18 record is timeless N5 core.
4. **Optional/historical annexes:** The N4-origin Reinforcements reference
   remains separately qualified N5-context reference material until its
   source-ownership and procedural revision can be independently established.
   The ITS 18 choice to enable/limit the Extra belongs in ITS 18, not in an
   unconditional change to the annex's mechanics.
5. **Shared components:** Reuse the existing
   `scenario_components`, `scenario_definition`, `scenario_mission` and
   `scenario_geometry` parsers/renderers. Shared N5 definitions remain
   N5-owned; ITS publications reference them by explicit typed identity.
   ITS-local rule text, objectives, scoring and geometry remain ITS-owned.
   Reuse of a concept or source PDF does not duplicate the canonical
   definition.
6. **Citations and source identity:** A publication owns its selected
   citations and source records, not all material ever found in the cited PDF.
   Preserve source ID, version, page/heading, language, official URL, recorded
   source SHA-256 and the source collection's identity/effective date.
   Identical *source descriptors* may be needed in independent stores, but
   they must not create duplicate rule ownership or disagree about provenance.
   No source is selected merely because its publication date is newest.

**Season applicability versus publication ownership are independent axes.**
A core N5 rule can be restricted by ITS 18; an N5 FAQ may be applicable to a
specific mission; an ITS ruling may refer to an N5 Skill. The owner is chosen
from the authored rule/publication's authority, while applicability is an
explicit context-scoped relation resolved at read time.

**Accepted future extension, not current behavior:** Reuse reviewed scenario
and Skill *definitions* across seasons through exact version-pinned
memberships and limited, validated contextual overrides. Season publications
continue to own their source evidence, applicability and assembled results;
referencing another definition does not transfer or erase that provenance.
Resolved records remain self-contained in each season's SQLite artifact.
The [data-model decision](data-model.md#accepted-cross-season-scenario-and-skill-reuse-not-yet-implemented)
owns the composition contract; ITS 17 migration is blocked on implementing it.

## Cross-boundary ownership

- **Spec-Ops:** `n5-core-v5.3.json` now retains only the N5.3
  Special Skills, the core SpecBall procedure and its bilingual
  source discrepancy. ITS 18 official-tournament and TEAM-OPS restrictions
  are owned by the selected ITS revision and appear in separate play-context
  cards on ITS scenario pages. The policy API resolves them by exact context.
  Their season citations no longer
  appear as if they were default N5 Skill restrictions.
- **Reinforcements Extra:** The separate N4-origin annex cites ITS 18 page 27
  for optional-mode availability. Retain its provenance and N4 caveat;
  rehome any ITS-specific availability/event restrictions to ITS 18 without
  certifying N4 procedures as N5 official rules.
- **Shared marker references:** In the complete runtime,
  `ScenarioCatalog` resolves the source metadata for marker diameters
  directly from the registered ITS 18 publication descriptor (p. 18);
  this is **external measurement evidence**, not ownership of the N5
  Domination/Supplies missions. Isolated Rules-only research or future
  configurations without ITS 18 retain the pinned historical citation,
  while an incomplete registered ITS 18 source fails closed. The resulting
  marker sizes and public citation shape remain unchanged.
- **Battleground:** `its_18.db` publishes the current 2026.09.11
  `scenario:battleground` with source citations on pp. 129–131.
  Earlier pp. 121–123 citations and original geometry remain tagged in
  the source-family file for future historical research, not player selection.
- **Core scenarios:** The four `n5-core@5.3` missions and their reusable
  N5 component definitions remain in `rules_n5.db`. A later ITS season may
  independently publish a mission with the same typed scenario ID; do not
  force a globally unique slug or copy a core publication into ITS to make
  navigation work.
- **FAQ:** The selected N5 FAQ remains N5-owned; there is no reviewed
  ITS-authored FAQ publication. General N5 rulings remain applicable to a
  registered season, but a core-scenario-scoped FAQ does not follow an
  independently published ITS mission merely because it uses the same
  `scenario_id`. A ruling explicitly selecting an ITS season and revision
  remains eligible only for that exact context. HTTP selection of a season
  requires a registered revision and a real member mission when
  `scenario_id` is given. Source dates, source selection, conflicts,
  supersession and source citations retain their existing constraints.

## Stable selection and identity contract

- **Core default:** No season selection continues to mean the N5 core
  scenario set. Do not default to the newest ITS season or infer a season
  from the current date.
- **Explicit season:** Resolve using the tuple
  `(scenario_collection_id, collection_revision, scenario_id)`, for example
  `(its-18, 2026.09.01, scenario:battleground)`. Preserve the associated
  authored `publication_collection_id` and content digest, not merely
  `scenario:battleground` or route slug `battleground`.
- **Cross-domain references:** Conceptually reference an owning domain and
  typed ID: `(rules-n5, skill:...)`,
  `(rules-n5, faq-ruling:...)`, or
  `(its-18, 2026.09.01, scenario:...)`. Expose stable typed references in
  the backend registry; physical database paths and SQLite `ATTACH`
  mechanics must not leak into UI or HTTP contracts.
- **Compatibility:** ITS data declares its supported N5 rules/source
  revision explicitly. Selected sets validate compatibility and resolve all
  references without creating shadow core definitions. Keep version and
  effective-date identities distinct: `5.3`, `0.1`,
  `2026.09.01` and `2026-09-01` serve different purposes.
- **Fail closed:** Unknown season, revision, scenario or cross-domain ID
  cannot fall back to another collection, an archived publication or a
  similarly named core record. Ambiguous identities require exact selection.
- **No global slug assumption:** The publication registry keys ITS
  resolution by owning season, revision and record identity. Synthetic
  same-slug scenarios in different seasons are separately selectable.
  Existing `/api/scenarios`, detail/map routes, explicit
  `collection`/`revision` selectors and core default behavior remain
  the compatibility surface.

## Future season expansion

Additional actual ITS seasons require independently reviewed source
publications, an explicit registry entry and matched build/package inputs.
Season 18 is the current content priority; Seasons 16 and 17 remain future
coverage, not a precondition for the existing runtime contract. The
synthetic multi-season test proves isolation only, not the correctness
of any uncurated season. See the [ITS database](its-season-database.md)
for the maintained storage and selection contract.
