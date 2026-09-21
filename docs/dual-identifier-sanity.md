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

### 2. Legacy grouped source IDs canonicalize browser filter state — closed

Closed on 2026-09-21. Public Skill, Equipment, and Weapon catalog-list payloads
now expose the materialized `source_ids` accepted for each application item. The
Unit explorer uses those aliases when a numeric filter is loaded, so an accepted
non-representative source ID resolves to the same select option and is rewritten
to the preferred application slug.

This keeps numeric compatibility without leaving the browser in a mismatched
state where the backend filter is active but the corresponding selector appears
unselected. Only materialized source IDs that the repository actually accepts
are exposed; unused metadata-only alias candidates are not advertised as valid
filter references.

### 3. Cross-domain API references use an additive slug companion policy — closed

Closed on 2026-09-21. Existing numeric fields remain intact for compatibility and
provenance, while references that resolve to canonical application identities gain a
routable slug companion. Scalar Unit Army references use `main_army_slug` and
`display_army_slug`; structured Army references add `public_slug` because their existing
`slug` is source/context data. Trait usage variants add `item_slug`, and Skill Modifier
rows add `skill_slug`. Unit references embedded in these payloads continue to use
`public_slug`.

The policy is deliberately additive and semantic rather than mechanical. Source/context-
only IDs do not gain invented application slugs, and plural `army_ids` are already paired
with the structured `armies` list whose entries now carry both numeric `id` and
`public_slug`, avoiding a redundant positional `army_slugs` array.

### 4. Closed: numeric-shadow handling belongs to the registry

The application-domain slug registry now treats a digit-only candidate such as
`"100"` as `unavailable` because the public route must interpret that token as numeric
ID 100. The diagnostic `candidate_slug` is retained, while persisted `slug` remains null.

`resolved` therefore means that the alternate identifier is actually routable. Shared
public-reference enrichment can trust `application_slug()` directly and no longer repeats
consumer-side `slug.isdigit()` suppression. Trait slug assignment is intentionally
unaffected because Traits do not share these numeric compatibility routes.

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
2. **Closed:** canonicalize legacy grouped source-ID filters into preferred slug browser
   state;
3. **Closed:** define and apply the cross-domain API slug-companion policy;
4. **Closed:** move numeric-shadow handling into the slug registry/resolver boundary;
5. migrate the remaining maintained Weapon/display references after adding
   deterministic owning-layer resolvers;
6. add project-wide dual-identifier invariant tests and rerun the sanity audit.

Only after those items are green should the normal release process in
`docs/releasing.md` begin, including its separate project-wide documentation
audit.
