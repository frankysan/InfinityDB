# Dual-identifier sanity audit — 2026-09-21

## Status

**Open. The unresolved items in this audit block the planned 0.6.2 release.**

This audit checks the project-wide application of InfinityDB's domain identifier
contract after the initial public-slug migration. For a domain with a stable
application slug, numeric application/source references remain supported for
compatibility and provenance, but application-facing lookups should accept the
numeric or slug form and generated references should prefer the slug.

Traits are intentionally different: curated `trait:<slug>` identities already
own their stable public slug and do not have a parallel numeric application
identity that should be duplicated into the Army-domain slug registry.

## Scope

The review covered the current player-facing identity domains and the places
where their identifiers cross layer boundaries:

- Armies, Units, Skills, Equipment, Weapons, and Traits;
- web/API detail routes and Unit-explorer filters;
- repository/application lookup methods;
- generated browser links and query-string state;
- cross-domain API references;
- maintained/curated JSON references;
- slug-registry fallback behavior and representative regression coverage.

The purpose was not to remove numeric IDs. Numeric IDs remain required for
SQLite keys, source provenance, compatibility, and unambiguous fallback. The
audit instead asks whether application-facing consumers can use either stable
identifier form and whether InfinityDB consistently prefers the readable form.

## Confirmed aligned behavior

The migration is directionally sound and the main public surfaces already obey
the intended contract:

- Skill, Equipment, Weapon, and Unit detail routes accept numeric compatibility
  identifiers or domain-local slugs, while generated detail links prefer slugs.
- Army filters accept application/source numeric IDs or public Army slugs, and
  generated Unit-explorer state prefers the public slug.
- Skill, Equipment, and Weapon Unit-explorer filters accept numeric IDs or
  slugs at the backend and expand grouped application identities to all
  represented source variants. This fixes grouped identities such as TinBot.
- Maintained rules `armyLinks` use application-domain slugs for Skills,
  Equipment, and Weapons while retaining numeric compatibility in the format.
- Catalog identity authoring supports reviewed source-label slugs, including
  explicit maintained aliases for source spelling corrections without rewriting
  source provenance.
- Trait public identity remains correctly owned by the rules/trait identity
  layer rather than being duplicated into `application_domain_slugs`.

## Gaps to close before 0.6.2

### 1. Repository lookup methods are consistently dual-ID — closed

Closed on 2026-09-21. The repository now owns one shared application-domain
reference resolver for Armies, Units, Skills, Equipment, and Weapons. It accepts
source/application numeric IDs or stable public slugs and normalizes them to the
application identity before the consumer-specific read proceeds.

`application_army_id()`, `application_unit_id()`, and `application_catalog_id()`
reuse that resolver, and `get_unit()`, `get_skill()`, `skill_source_ids()`, and
`get_catalog_item()` accept either supported form directly. The web detail routes
therefore only parse numeric route syntax; they no longer perform slug-to-ID
resolution themselves.

### 2. Legacy grouped source IDs do not fully canonicalize browser filter state

The backend can resolve a source-variant numeric filter such as a TinBot source
Equipment ID to the logical TinBot application identity. The browser's
`normalizeCatalogFilterState()` can only match the application item IDs present
in the catalog response, however. A legacy URL containing a non-representative
source ID can therefore filter correctly while the corresponding select control
appears unselected and the URL is not upgraded to the preferred slug.

The API/browser contract needs enough source-to-application identity information
to canonicalize any accepted legacy numeric filter to the same public slug.

### 3. Cross-domain API references need a consistent slug companion policy

Several payloads still expose numeric application/source references without the
corresponding readable application identity. Examples that need review include
Unit Army references such as `army_ids`, `main_army_id`, and `display_army_id`,
Trait variant `item_id` references, and Skill Modifier `skill_id` references.

Numeric fields should remain for compatibility and provenance. Where such a
field represents a canonical application identity with a stable slug, the API
should also expose the slug or a structured reference that makes both forms
available. Source/context-only IDs must not be relabeled as canonical slugs.

### 4. Numeric-only slug candidates are marked resolved too early

The slug registry may currently return a digit-only value such as `"100"` with
status `resolved`, even though routes must interpret that token as numeric ID
100. Consumers consequently repeat `not slug.isdigit()` checks before emitting a
slug.

A registry/resolver state described as resolved should mean that the slug is
actually usable as the domain's public alternate identifier. Numeric-shadowing
candidates should be made unavailable/fallback at the owning identity layer so
consumers do not each need to rediscover the routing ambiguity.

### 5. Remaining maintained JSON references still use opaque entity IDs

After excluding actual numeric values such as `formatVersion`, the current
maintained files still contain 18 entity references that are good candidates
for the numeric-or-slug authoring convention:

- 8 `weapon_id` references in `config/catalogs/weapon-categories.json`;
- 8 `weapon_id` references in `config/catalogs/weapon-overrides.json`;
- 2 display-identity references in
  `data/curated/identities/army-display.json`.

Each owning build layer needs a deterministic resolver before these are changed.
Numeric references remain a valid fallback for ambiguity/provenance. Unit and
Army source-identity groups are not part of this count: those numeric references
participate in constructing source/logical identity and are intentionally kept
as provenance-level IDs for now.

### 6. The contract lacks one project-wide invariant regression

Existing tests cover individual routes and resolver behaviors, but there is no
single contract suite that exercises the general rule across every registered
application domain. Future domains could therefore implement only part of the
contract without an obvious failure.

Add parameterized/invariant coverage that proves, where applicable:

- numeric application IDs and public slugs resolve to the same identity;
- accepted source numeric IDs resolve to that same application identity;
- generated public references prefer the slug when one is usable;
- unavailable/colliding/numeric-shadow slugs fall back to numeric identity;
- legacy numeric filter state canonicalizes to the preferred slug;
- unknown or ambiguous slugs fail closed.

## Accepted numeric-only uses

The dual-ID contract does not mean every integer in the project should become a
slug. The following remain legitimate numeric uses unless their owning model is
redesigned deliberately:

- SQLite primary/foreign keys and internal joins;
- raw/source IDs retained for provenance and source-context relationships;
- identity-construction mappings where the source numeric identity itself is the
  reviewed input, including the current Unit/Army source identity groups;
- non-identity numeric data such as versions, counts, ordering, ranges, pages,
  quantities, and schema values;
- fallback identifiers when no unambiguous routable slug exists.

## Required closure order

Before starting the 0.6.2 release checklist:

1. **Closed:** centralize application-domain reference resolution and make
   repository/detail lookups dual-ID where the domain supports stable slugs;
2. canonicalize legacy grouped source-ID filters into preferred slug browser
   state;
3. define and apply the cross-domain API slug-companion policy;
4. move numeric-shadow handling into the slug registry/resolver boundary;
5. migrate the remaining maintained Weapon/display references after adding
   deterministic owning-layer resolvers;
6. add project-wide dual-identifier invariant tests and rerun the sanity audit.

Only after those items are green should the normal release process in
`docs/releasing.md` begin, including its separate project-wide documentation
audit.
