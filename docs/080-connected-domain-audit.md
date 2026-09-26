# 0.8.0 connected-data domain audit

**Project domain:** Data processing

This audit defines the semantic/application boundaries for InfinityDB's 0.8.0
**connected game relationships** milestone. It is a design/completeness audit, not a
second rules backlog. Current source semantics remain authoritative in
`docs/rules-semantics.md`, current application storage semantics remain authoritative
in `docs/data-model.md`, and concrete implementation work remains in `docs/TODO.md`.

## Audit question

0.8.0 needs to make already-modeled relationships useful to players without creating
one new catalog for every relationship target. The audit therefore asks two separate
questions:

1. Which source concepts require a stable canonical identity and first-class browser
   surface of their own?
2. Which facts are relationships between identities that InfinityDB already models and
   should therefore be presented on existing Unit, Army, Profile/Loadout, Skill,
   Equipment, Weapon, Trait, or State surfaces?

The decision rule follows the architecture principles: create a new domain only when
an object has independent identity, meaningful attributes/relationships of its own,
and a player-facing reason to browse it independently. Do not create a domain merely
because a foreign key, rule target, source table, or deferred interaction exists.

## Evidence reviewed

The audit combines the maintained Army completeness and relationship audits with the
reviewed rules corpus and current Wiki structure:

- the Milestone 2B source-to-presentation inventory and relationship evidence in
  `docs/data-model.md`;
- the Fireteam semantic audit maintained by `tools/audit_fireteam_semantics.py`;
- the 223-record interaction review and its 115 explicitly deferred interactions in
  `data/curated/rules-interactions/reviews.json`;
- the cross-domain findings in `docs/rules-semantics.md`, including Fireteams,
  Hacking Programs, Reinforcements, deployables, declaration categories, and Quick
  Reference relationships;
- current Infinity Wiki Fireteams Chart / Fireteams rules, Peripheral, Hacking Device,
  and Infinity Reinforcements reference pages.

The deferred-interaction ledger is especially useful as a boundary check. After the
Hacking Program promotion, its 115 remaining entries target 34 distinct generic `rule:*`
concepts, six States, six Attributes, thirteen Skills, three Equipment identities, three
Traits, two Ammunition identities, two Weapons, and one Training identity. Hacking
Programs are now reviewed supporting identities rather than deferred targets; the two
remaining Program-originating White Noise interactions stay deferred because their
zone/Line-of-Fire condition needs richer relation semantics. Most remaining targets do
**not** justify new application domains.

## Domain decisions

### Fireteams: create one new first-class application domain

Fireteams meet every criterion for an independent application domain. The Army source
contains structured Fireteam charts with Army-local team identity, Fireteam type
membership, member rows, min/max requirements, required-choice pools, FTO restrictions,
Wildcard behavior, equivalence labels, Army/chart observations, and Reinforcement
context. The audited snapshot contains 58 source charts, 272 named Fireteams, 444
Fireteam-type memberships, and 1,261 member rows.

A Fireteam is not reducible to a Unit relationship. Distinct member rows can resolve to
the same Unit while preserving subgroup/profile/loadout meaning, FTO eligibility is an
option-level condition, and Reinforcement Fireteams combine section-local composition
with parent-Army type/count limits. The current Wiki also explicitly gives chart notes
precedence over general Fireteam rules and defines FTO/Wildcard semantics in the chart.

Schema 25 introduces that canonical **Fireteams** application domain with Army-context
identity and provenance, and the first 0.8 browser/API slice now presents those authoritative
Army charts directly. The model and presentation preserve chart source context rather than
converting it into a generic army-list legality engine. General Fireteam rules/Level-bonus
reference data remains separate follow-up work.

### Hacking Programs: promote the existing projection to a first-class rules/reference surface

Hacking Programs already have independent identity and structured profile data in the
application database: Devices, targets, declaration types, PS, Burst, and special text.
0.8 now exposes that projection as first-class `/hacking-programs` list/detail identities while
retaining the Hacker Skill table as a linked quick reference. The deferred-interaction ledger
also contains 17 links to 11 distinct Hacking Program
targets, and the current Hacking Device rules define Program access explicitly by
Device.

This evidence now backs the first-class **Hacking Programs** rules/reference surface.
The implementation reuses `application_hacking_programs` and its relationship tables rather
than inventing a parallel dataset. Army metadata owns exact profile fields, targets, declarations,
baseline Device associations, and Upgrade-extra provenance; reviewed `rules.db` records add
semantic identity/effects and typed rules relationships. Baseline Device links are generated from
the source associations, while Upgrade/source-specific availability remains distinct.

### Peripherals and Controllers: no new domain

The canonical Peripheral layer already exists. The application database has reviewed
Peripheral entities/profiles/source mappings plus Controller access and target edges,
and Unit detail payloads already carry Peripheral attachments/access data. The current
Wiki likewise defines Peripheral behavior through the Controller/Peripheral relationship.

0.8.0 now makes these edges navigable from existing Unit/Profile/Loadout surfaces.
Embedded attachments render in their owning Profile/Loadout context; Controller access pools
link to their Unit-backed targets; those target Units expose the reverse Controller occurrences
with Army and profile/loadout context. Creating a second top-level Peripheral catalog would
duplicate the relationship model without adding an independent player-facing identity boundary.
Unit-backed Peripherals continue to resolve to logical Units; non-Unit Peripheral entities
remain relationship endpoints where needed.

### Profile/Loadout/Unit-option includes: no new domain

The application database materializes canonical include targets while retaining the parent
occurrence and quantity/context needed for losslessness. Includes are edges between existing
Profile/Loadout/Unit-option identities. Unit detail now renders Profile and Loadout Includes in
their owning context and shared Unit-option Includes per target Army; each canonical target links
to the rendered Loadout presentation. Shared Unit options deliberately expose only this edge
family here, leaving their broader composite-option semantics for the later completeness review.

No independent "Includes" catalog is warranted.

### Selection constraints and profile-group dependencies: no new domain

The existing 96 Unit selection constraints and 14 profile-group dependency constraints
are relationship objects whose purpose is to explain how existing choices depend on or
exclude one another. Unit detail now renders the reviewed whole-Unit cardinality families with
stable links to affected Units and renders deterministic same-Unit dependency edges with links
to the exact profile groups and option-scoped loadouts. Army relation IDs remain developer
provenance.

The presentation stays descriptive rather than becoming a legality engine. Dependency direction
is normalized, but source selector parameters whose broader list-building meaning is not yet
normalized are shown with their source field names instead of being reinterpreted. No independent
selection/dependency catalog is warranted.

### Reinforcement Sections and parentage: reuse the Army domain

The application Army graph already models Reinforcement Sections and 46 ordinary-parent
links. Reinforcement Sections are scoped pools shared by faction armies, not independent
legal Army Lists, and the rules source remains an explicitly scoped annex. The current
Wiki likewise defines the Reinforcement Section as a section of an Army List, shared by
a faction and constrained by both its own Fireteam chart and the selected parent Army's
allowed Fireteam types/counts.

0.8.0 now exposes Reinforcement parent/child navigation and section context through the
existing Army/Unit surfaces. `/api/armies` and Unit detail carry the canonical application Army
parent/child references, and the Unit browser links those references back to Army-filtered Unit
exploration. No new Reinforcement catalog is required.

### Declared faction membership and cross-Army navigation: reuse Army/Unit identity

The application model already distinguishes concrete Army availability from broader
source-declared faction membership. Unit detail now exposes those declarations independently of
its concrete Army occurrences, and the Unit Explorer accepts `declared_faction_id` as a dedicated
relationship filter over `unit_factions`. This deliberately differs from `army_id`, which remains
a concrete playable-List filter. Source faction IDs with no current Army List remain navigable by
their exact source ID and are not promoted into application Army identities. A separate membership
domain would only duplicate endpoints that already have stable identity.

### Deployable profiles: add a reference projection, not a top-level domain

Deployable defensive profiles describe deployed game elements produced by Weapons or
Equipment. They have meaningful ARM/BTS/STR/S data, but the player-facing identity still
belongs to the originating Weapon/Equipment plus its deployed object. A generated
Deployables reference may be useful, but the audit does not require a separate canonical
catalog merely to share a defensive-profile table.

Keep the deployed-object profile distinct from the carrier/loadout and preserve known
source discrepancies such as Armed Turret Silhouette provenance. This work can follow
the core 0.8 structural relationship surfaces unless it becomes necessary to resolve a
specific connected-data gap.

### Generic rules concepts, Attributes, Ammunition, Training: supporting identities, not 0.8 domains

The deferred interaction ledger contains many targets such as Cover, Guts Roll,
Face-to-Face Roll, Marker form, Wound, Attributes, Ammunition, and Training. These are
valid rules concepts, but the existence of a deferred edge is not sufficient reason to
create a browser domain for each category.

When 0.8 work needs one of these endpoints, prefer a maintained supporting rules identity
and linkable contextual presentation. A broader glossary/concepts surface may be assessed
in the 0.9 completeness/search phase after the structural application relationships are
usable. This keeps 0.8 focused and avoids turning InfinityDB into an exhaustive rules
ontology.

## 0.8.0 implementation order

Schema 25 / compatibility revision 33 completed step 1 below, and the Army-scoped browser/API
plus rules-backed generated Fireteam quick reference complete step 2. Step 3 is complete:
Peripheral/Controller, include, selection/dependency, Reinforcement-parent, and broader declared
faction/cross-Army relationships are all presented through existing application identities.
Hacking Programs complete step 4 by promoting the existing structured projection without a
parallel dataset. Step 5 is also complete: the maintained source-presentation audit reports only
the two already-scoped 0.9 gaps (`unit_notes` and composite `unit_options`), while the interaction
audit reports all 14 0.8 supporting identities reviewed with no pending 0.8 review. The 0.8
connected-data implementation contract is therefore complete; release validation remains the
normal release-process concern.

The audit establishes this order for the connected-data milestone:

1. **Fireteams — Data processing:** materialize a first-class canonical Fireteam
   application projection from the audited Army chart semantics, including Army and
   Reinforcement context, member resolution, FTO semantics, min/max/required-choice
   structure, Wildcards/equivalence labels, observations, and source provenance.
2. **Fireteams — Web backend + Web frontend:** add Army-scoped browsing/detail APIs and
   player-facing Fireteam views, generated general Fireteam bonus/rule context, and links
   to member Units/options without implementing list legality.
3. **Existing application relationships — Web backend + Web frontend:** present
   Peripheral/Controller links, include edges, selection/dependency constraints,
   Reinforcement parentage, and broader faction/cross-Army relationships using their
   existing canonical endpoints.
4. **Hacking Programs — Data processing + Web backend + Web frontend:** promote the
   existing structured Program projection to first-class navigable rules/reference
   identities and connect reviewed Device/Skill/program relations.
5. Re-run the source-presentation and interaction audits. Any remaining 0.8 relationship
   gap must either fit an established domain/edge family or receive an explicit boundary
   decision before a new domain is introduced.

## Explicit non-goals

The audit does not expand 0.8.0 into:

- an army-list legality engine;
- a live game-state model;
- a separate catalog for every relationship type or source join;
- a complete ontology of generic rules concepts;
- ITS/scenario objective modeling beyond preserving scoped references already required by
  maintained data; or
- a redesign of existing Skill/Equipment/Weapon/Trait/State identity.

These boundaries keep the release aligned with the public roadmap: 0.8 connects the data;
0.9 closes remaining presentation/search gaps; 1.0 completes the maintained player-data
reference.

## Source references

External source structure was rechecked on 2026-09-26 against the current N5.3 Wiki:

- Fireteams Chart: <https://infinitythewiki.com/Fireteams_Chart>
- General Rules of Fireteams: <https://infinitythewiki.com/General_Rules_of_Fireteams>
- Peripheral: <https://infinitythewiki.com/Peripheral>
- Hacking Device: <https://infinitythewiki.com/Hacking_Device>
- Infinity Reinforcements: <https://infinitythewiki.com/Infinity_Reinforcements>
- Weapon Chart / deployable profiles: <https://infinitythewiki.com/Weapon_Chart>

These pages are evidence for semantic boundaries, not runtime dependencies. InfinityDB's
pinned Army/Wiki snapshots and maintained curated data remain the reproducible build inputs.
