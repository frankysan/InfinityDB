# P3 — Source and publication ownership contract

**Status:** P3.1–P3.4 locally implemented and acceptance-tested,
including exact-context overlays, FAQ isolation and source provenance.
P3.5 multi-season isolation remains open; hosted Source CI acceptance is pending.
**Branch:** `dev/v1.1.0`.
**Domains:** Data processing, Web backend, Web frontend.

This is the ownership contract for separating season-scoped ITS publications from
the N5 core without duplicating rules, breaking source citations, or introducing
a second scenario renderer. It records existing behavior and target decisions;
no database format or serving behavior changes during P3.1.

## Existing source and runtime inventory

The complete build loads reviewed curated Rules and ITS sources, but the
Rules exporter accepts only N5-owned collections. ITS-authored publications
are built independently into `its_18.db` using the same selected source
envelope. The following inventory records the pre-separation source roles:

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
- `n5-its-season-18-2026.09.01.json` — `its`,
  `its-season-18-2026.09.01`, effective 2026-09-01. Contains the
  currently curated **Battleground** mission, its game-size variants,
  objective/scoring rules and geometry. Its scenario set is
  `its-18@2026.09.01`, with source `its-season-18-en-pdf`,
  printed pages 121–123.

Before the P3.4 export split, `rules_n5.db` stored the ITS collection
alongside N5 in its scenario tables. That co-location has been retired:
the selected `rules_n5.db` now owns N5/FAQ/annex data, while
`its_18.db` alone stores ITS Battleground and its season policies.
Both preserve source authority, revision, citation and content digest.

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
3. **ITS seasons:** `its_18.db` will own **all authored ITS 18** mission
   definitions, their geometry and game-size configurations, scenario-set
   membership, season Extras and tournament constraints, and rulings whose
   *publishing authority* is ITS 18. Other seasons get independent ownership;
   no current ITS 18 record is silently treated as timeless N5 core.
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

## Cross-boundary inventory and migration dispositions

- **Spec-Ops:** `n5-core-v5.3.json` now retains only the N5.3
  Special Skills, the core SpecBall procedure and its bilingual
  source discrepancy. ITS 18 official-tournament and TEAM-OPS restrictions
  are owned by `its_18.db`, surfaced only after exact play-context selection
  from the ITS scenario page or policy API. Their season citations no longer
  appear as if they were default N5 Skill restrictions.
- **Reinforcements Extra:** The separate N4-origin annex cites ITS 18 page 27
  for optional-mode availability. Retain its provenance and N4 caveat;
  rehome any ITS-specific availability/event restrictions to ITS 18 without
  certifying N4 procedures as N5 official rules.
- **Shared marker references:** In the complete runtime,
  `ScenarioCatalog` resolves the source metadata for marker diameters
  directly from the registered ITS 18 publication descriptor (p. 17);
  this is **external measurement evidence**, not ownership of the N5
  Domination/Supplies missions. Isolated Rules-only research or future
  configurations without ITS 18 retain the pinned historical citation,
  while an incomplete registered ITS 18 source fails closed. The resulting
  marker sizes and public citation shape remain unchanged.
- **Battleground:** Move `scenario:battleground`, its full scenario
  definition, all 150–400 Army Point configurations, scoring, SVG geometry,
  collection `its-18@2026.09.01`, and PDF pages 121–123 to the ITS owner
  without editing their game semantics.
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
- **No global slug assumption:** Today
  `ScenarioCatalog._records()` rejects duplicate route slugs and resolves
  from one `RulesDatabase`. P3.4 must key catalog resolution by owner and
  publication identity, and P3.5 must prove same-named scenarios across
  seasons remain separately selectable. Existing `/api/scenarios`,
  detail/map routes, explicit `collection`/`revision` selectors and core
  default behavior are the compatibility surface.

## Implementation sequence and acceptance

**P3.2 — Own and build `its_18.db`:** Define the season database's
collections/sources/records, citations, scenario publications and geometry
using the existing scenario model. Add an isolated, deterministic builder
from pinned reviewed ITS inputs. Record source/build provenance and explicit
N5 compatibility. Allow independent developer inspection, but do not
introduce two authoritative serving copies or silently change the current
two-database release until the coordinated registry/cutover.

**P3.3 — Migrate the Battleground pilot:** Reuse its exact curated
definitions and geometry; move season-only Spec-Ops and Extra overlays under
ITS authority. Compare source citations, supported game sizes, JSON
responses, rendered SVG bytes/meaning and no-sidecar operation with the
P2 pinned baseline.

**P3.4 — Centralize resolution:** Introduce the domain-aware backend
registry, validate the selected multi-database set, and update collection
selection, source lookups and FAQ/overlay resolution. Do not rely on
`RulesDatabase.composed_records_by_kind("scenario")` returning every
season; do not silently merge duplicate IDs. Coordinate CLI build,
`--db-dir`, WSGI, Docker, CI and cache revisions in a single explicit
serving cutover, keeping existing public selectors stable.

**P3.5 — Verify isolation and growth:** Test two differently versioned
season publications, including a duplicate scenario slug; no ITS defaults
without selection; no leakage of tournament restrictions to core/free play;
scoped FAQ and source citations survive; mixed/stale sets and unknown
cross-domain references fail closed; local checkout and actual Docker
preserve pinned HTTP, geometry, health and file-contract acceptance.
Season 18 remains the content priority; adding S16/S17 scenarios is later
coverage, not a P3 migration gate.

**P3.1 exit:** Ownership, exceptions, selected publication identity,
source provenance, core-to-season relationship and phased acceptance are
specified. No migrated `its_18.db` or new runtime behavior is claimed.
