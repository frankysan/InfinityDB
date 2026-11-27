# Weapons and deployed-object data model

**Project domain:** Data processing

This document owns exact Weapon-profile/source identity, profile
citations, source-reviewed Ammunition/Property projections and
deployed-object delivery and ownership. The [Rules model](data-model-rules.md)
owns canonical semantic definitions; [rules semantics](rules-semantics.md)
owns rule interpretations, including conditional Immunity and Saving Roll
examples. [Official source clarifications](official-source-clarifications.md)
owns unresolved questions. These are descriptive read models, never
a combat resolution or roster-legality engine.

For weapon families such as Mines, a shared curated rule describes only the common
mechanics. The individual Army weapon profile identifies ammunition, PS, Saving Rolls,
and Traits; the corresponding ammunition, State, and Trait rules determine the
weapon-specific effects. Attaching `weapon:mines` to a weapon
does not create a generic "ordinary Mine" weapon or make the variants interchangeable.
Variant-specific effects require their own source-derived weapon profile and, where
necessary, curated exceptions or relationships. A reviewed family clause is not
evidence that every named weapon variant has complete rules coverage.
An Army Weapon source ID can also cover multiple modes (Kobra Pistol: source `221`,
BS Mode and CC Mode). Curated source rules may target an exact source ID *and*
mode, but must attach to that one profile only, not to the parent Weapon/source
variant or sibling modes. Mode qualifiers describe identity, not permission to
resolve a disputed Trait automatically.

## Weapon profile row and API contract

Army `metadata_weapons` rows are source profiles, not normalized weapon behaviors.
The catalog API preserves each profile's source ID and mode as row identity, including
mode-specific rows, and exposes the source-backed ammunition ID and label, type, Burst,
Damage, Saving, Saving count, profile text, Traits, and range bands. It does not merge
sibling modes into one profile.

Burst, Damage, Saving, and Saving count remain source values rather than parsed
numbers or enums. Profile text remains source text; Traits and distance bands are
decoded into lists/maps without interpreting their rules. A source `distance = null`
currently projects as `ranges: {}`; this means no range bands were supplied to the
projection, not an adjudication of weapon reach. The browser omits the range table
when there are no bands. Blank or sentinel Saving values may display as `--`, a
presentation fallback that does not change the source value or establish a game
effect. Conditional wording and other source sentinels are not evaluated.

The existing exact-profile enrichments remain narrow and source-pinned, including
reviewed Ammunition composition and Combined Saving Roll annotations. No generic
condition or sentinel field is needed for the current profile model. Any future
structured status must follow a source-reviewed distinction; display punctuation
alone is not evidence for new semantics.

For reviewed profile-only Weapons, complete builds embed Weapon Chart
citations (introduced in Rules v12/compatibility 14, retained in current v24). The relational
`weapon_chart_profile_citations` table is keyed by exact Weapon/source-profile ID
and a non-null mode key (`''` for an unqualified mode, `mode:<name>` otherwise);
read projections restore the original nullable mode. A source-FK-backed metadata
row pins the current primary PDF identity, page range, reviewed decision SHA-256,
selected Army byte identity and the complete reviewed profile inventory. Each
Weapon also retains its canonical slug/name and complete Army profile fingerprint.
The embedded reader validates source/page integrity, a deterministic content
digest, exact profile fingerprints and complete modes against the selected Army.
It does not read curation or the original JSON at runtime. The tracked
complete Rules publication requires these embedded citations; the old loose
`weapon-profile-sources.json` is not a serving dependency. A mismatched
embedded source is rejected. Explicit low-level historical fixtures can still
report `profile_citations_available: false` for absent citations. Each Weapon profile has a
`profile_citations` list: an empty list means no reviewed profile-chart
citation was attached, not that no shared rule has a source. The browser
shows the chart citation or an explicit unavailable notice when the
publication is missing. This is a locator for the corresponding chart
entry, not a claim that Army and print values agree or an Ammunition rule.

## Weapon Chart footnote references

Weapon Chart footnote markers `[*]`, `[**]` and `[***]` identify
Weaponry, Ammunition and Skills/Equipment respectively, not Traits or
new gameplay properties. The current browser projection in
`src/infinity_db/web/static/weapon-footnotes.js` uses reviewed exact catalog slugs,
domain and source mode. Retain raw source labels in Developer Mode.
Only reviewed source-scoped links acquire a destination; unresolved
markers retain their source section/locator or disclosed uncertainty.
Do not infer mechanics from punctuation, create a Trait from a marker
or apply one mode's reviewed target to its sibling. Chest Mine BS Mode's
exact target remains unverified; known PARA Mine and Sepsitor Plus
discrepancies retain SRC-013/SRC-014. See
[the visual presentation contract](web-design-guidelines.md#curated-rules-text-hierarchy).

## Reviewed metadata-only Weapon publication

The upstream `weapons` table
describes usage-derived source catalog entries; `metadata_weapons` also contains
official profiles with no current Unit use. Those unreferenced profiles are
**not** published wholesale. Build-time policy in
`config/catalogs/metadata-only-weapons.json` explicitly identifies approved
source IDs, names, categories and complete profile signatures (Ammunition,
modes, ranges, Traits, Saving Rolls). When present, a matching metadata-only
profile receives an ordinary `application_catalog_items` identity and
`application_catalog_sources` provenance, without creating a synthetic
upstream `weapons` row or Unit use. A changed profile fails the build instead
of silently adopting new rules. Absent profiles in older snapshots are skipped;
source entries already present in the upstream `weapons` table are not
duplicated. The first reviewed case is Breaker Marksman Rifle (source 225);
its numeric and slug routes share one application identity, with zero Unit
usage until an actual source relationship exists. A curated weapon rule records
the printed profile's provenance and the different English update-notice label.
Do not infer a Breaker Sniper Rifle from that notice.

## Ammunition, Saving Rolls and Properties

Weapon Ammunition navigation is a reviewed *projection*, not executable Ammunition
composition. `config/catalogs/weapon-ammunition-references.json` pins exact Army
metadata Ammunition IDs and names to canonical published base Ammunition references.
The repository preserves the source metadata ID as `ammunition_source_id` in each
Weapon profile; the catalog API attaches ordered `ammunition_parts` only when both
that ID and its name match the reviewed map. A base type links to one reference;
source-defined `AP+DA`, `AP+Exp`, `AP+Shock`, `AP+T2`, and `N+E/M` link their reviewed
components separately. Version 2 of the maintained mapping also records those
ordered components as canonical `ammunition:*` IDs; the validator requires exact
agreement with the linked display segments and literal `+` separators. The
Weapon API exposes `ammunition_composition: {kind: "combined", components: [...]}`
only for an exact Army source ID/name pair with published reference targets.
Single Ammunition profiles do not receive a synthetic composition. Alternative
(`/`), absent, or mismatched values remain source text; they are not guessed
from punctuation. Saving Roll notation (`ARM/2`, `x2`, etc.) remains a distinct,
unchanged source field and is never interpreted as Ammunition composition.
For exact reviewed source ID/name pairs, Weapon profiles additionally expose
`ammunition_effects`: ordered canonical `ammunition:*` IDs, names, current
summaries, citations and routes, copied from `rules_n5.db` at response time.
The API resolves maintained inline references in these summaries to
`summary_tokens` with navigable public references; the browser renders
those tokens rather than exposing raw `[[...]]` source notation.
The Weapon profile displays these in a collapsible **Ammunition effects
(shared rules)** section, while its original PS, Burst, Saving Roll,
Traits and modes remain untouched. The `ammunition_effects` projection
is omitted for unreviewed/mismatched source ammunition; its existence
establishes only reusable component coverage, **not** exception/interaction
completeness. Component texts and citations are never authored in the mapping.

The Weapon source-review audit has a separate maintained decision file,
`data/curated/weapon-shared-effect-reviews.json`, for individually verified
Weapon profiles whose shared components and published Traits already suffice.
Those approvals are pinned to full Army profile SHA-256 fingerprints and the
official PDF SHA-256 and chart page range. They are not inferred from the mere
presence of an ammunition link, and a changed profile reopens review. Unreviewed and
mode-specific Weapon behavior remains in the triage; explicitly reviewed
shared-only identities do not require fabricated standalone rule records.
The separate generated profile-citation publication materializes only
the current profile-only decisions; later published family rules do not
become synthetic profile rules.

Canonical `ammunition:*` records own `facts.ammunitionResolution`,
conditional State effects, Wound counts and Critical additional Saving
Roll metadata. Smoke/Eclipse instead use `facts.visibilityZone`, with
optional reviewed opposition facts and an exact Face to Face rule link;
they do not synthesize Saving Rolls. Validated `causes-state` relation
targets match the typed conditional State effects. Conditions stay in
the owning facts, not on an unconditional graph edge. The individual
effects and reviewed examples belong in curated records and
[rules semantics](rules-semantics.md), not a duplicate gameplay model.

The Weapon API separately exposes source-authored profiles and reviewed combined
component IDs. It does **not** merge these facts into an inferred roll result:
Feuerbach's AP+DA source combination remains distinct from its `ARM/2` and `2`
fields, and Plasma Carbine's `ARM and BTS` / `1 and 1` remains a Combined Saving
Roll with Normal Ammunition, never a synthetic composition.

Critical adds one additional applicable Saving Roll, not one per component.
T2's failed extra Critical roll has a distinct Wound count. Combined
Ammunition mapping publishes ordered identities, not an executable
combination/precedence algorithm. Combined Saving Rolls are a distinct
exact-source annotation (Plasma's additional Critical ARM roll).
Armed Turret E/Mitter's one BTS/2 source roll remains unmodified despite
the printed two-roll discrepancy; retain that source conflict.

### Exact Combined Saving Roll annotations in Rules v15

The editable `config/catalogs/weapon-combined-saving-rolls.json`
retains the three source-reviewed Plasma weapons and six exact
Weapon-profile/mode annotations. Rules v15 (compatibility 17) embeds
them in `weapon_combined_saving_roll_profiles`, keyed by
`(weapon_id, mode)`. Each row retains the authored name, mode order,
source Ammunition ID/string, Saving Roll text and count string;
`combined_saving_roll_metadata` pins the selected Army database SHA,
current N5.3 core PDF source ID/SHA, printed page 67, and the
reviewed Critical extra-ARM-roll fact. The content fingerprint
verifies the complete mode inventory.

The build validates that all six exact source signatures match the
selected Army Weapon catalog, without deriving any rule from punctuation.
Source-only and unexplained Weapon modes do not acquire an annotation.
The read model preserves the pre-v15 signature dictionary and existing
`combined_saving_roll` API payload. `CatalogRules` reads the persisted
annotations from the selected Rules database; historical source-only
paths retain their validated JSON adapter. This is a reviewed
reference annotation **not** an executable saving-roll calculator,
Ammunition composition parser or generic Critical rule expansion.

### Reviewed Ammunition identities and composition links in Rules v16

`config/catalogs/weapon-ammunition-references.json` remains the
editable reviewed source map. The Rules v16/compatibility-18
schema embeds its 16 exact Army Ammunition source ID/name pairs
in `weapon_ammunition_links`; ordered
`weapon_ammunition_segments` retain literal display text and
optional links to N5 `ammunition:<slug>` records, while
`weapon_ammunition_components` holds the ten separately reviewed,
ordered relationships for the five combined identities. Composite
foreign keys bind all linked IDs to their existing N5 rule
records; source-collection context, selected Army SHA, primary N5
source identity and SHA, row counts, map format/version, and a
deterministic fingerprint live in
`weapon_ammunition_reference_metadata`.

Build and read checks require the complete exact mapping,
current canonical target kinds, reproducible segment spelling/order,
and matching Army metadata ID/name pairs. They deliberately **do
not** parse the `+` separator into gameplay effects, compute
Saving Rolls or use Weapon names to infer source identifiers.
The `WeaponAmmunitionReferences` resolver reads the same mapping
from SQLite in v16 and returns unchanged `ammunition_parts`,
`ammunition_effects` and `ammunition_composition` API fields.
Pre-v16 archived releases and explicit source-only review tools continue
to use their matching maintained JSON adapter; the current runtime reads
the embedded projection.

### Reviewed Weapon Properties in Rules v17

The authored `config/catalogs/weapon-properties.json` retains
12 distinct application-owned Weapon Properties; these do **not**
become official N5 Ammunition, Traits or Skills. The Rules v17/compatibility-19 storage stage introduced their exact slug, name, summary
and authored order in `weapon_properties`. Ordered
`weapon_property_origins` retain domain, role, optional current
canonical rule-record foreign key and optional exact source-section
string; they do not infer references from source text.

`weapon_property_profiles` preserves each reviewed exact Army
Weapon ID, nullable mode, name, Ammunition source ID/name, Saving
Roll field and count. Ordered `weapon_property_profile_traits`
retain the unmodified printed Trait strings, including annotation
markers, without reinterpreting them. A non-null `mode_key`
distinguishes NULL from named modes for unique source signatures.
`weapon_property_metadata` binds the selected Army database SHA,
current N5.3 primary PDF source identity/SHA, row counts,
maintained format/version and a fingerprint of the complete
ordered source publication. Relational records keep canonical-rule
and source collection ownership explicit.

Build and read validation check the reviewed inventory,
current rule origins, source-profile/mode identities and the
exact selected Army Weapon fields; mismatched, missing or corrupted
source facts fail closed. The `WeaponProperties` resolver reads
the embedded SQLite model, preserving its existing exact-match guard,
Glossary/search links, origin previews and Weapon detail payload.
Historical schemas and explicit source-review calls keep the
validated JSON adapter; current serving uses the embedded projection.

Weapon Properties are application-owned `weapon-property:*` references
and not official Traits, Skills or Ammunition. They retain reviewed
origins, exact profile membership and Glossary/search identity.
`[[weapon-property:...]]` references validate and resolve to the
embedded Glossary vocabulary; no separate canonical rule is manufactured.
See [the reviewed rules semantics](rules-semantics.md).

## Deployed-object read-model and artifact-gated browser reference

The complete Rules publication embeds normalized object identities,
attributes, source evidence, delivery and Unit-use relationships, bound
to the selected Army database. Adjacent `deployed-objects.json` cannot
enable a catalog or recover a missing/corrupt projection. The standalone
JSON publication/migration tooling is retired. Validation guards exact
object/source identity, attribute evidence, reviewed delivery edges and
source-scoped direct/Include Unit ownership before storage and after
reading. A self-referential Rules hash is invalid.

`infinity_db.deployed_object_reference.project_deployed_references` consumes
the validated N5.3 deployed-object audit and produces a **pure, read-only**
reference projection. The reviewed inventory includes exact Army profiles and the
curated Armed Turret and Deployable Cover records. An Army reference key
includes **catalog, source ID and mode**; reviewed-only object keys use their
curated rule IDs. These are deterministic identities within the pinned source,
not guarantees that upstream Army IDs never change between snapshots.
The projection separately exposes raw source profile text and individual
ARM/BTS/STR/S attribute states: `known`, `unreported`, or `disputed`.
Every present value retains provenance; a disputed Silhouette retains both
conflicting source values, and missing Scenery attributes remain `null`
rather than becoming zero. Exact reviewed delivery paths point *toward* the
shared object reference; Mine Dispenser's unresolved loadout-specific Mine
subtype remains explicitly unresolved. These edges establish **delivery
origins only**. The release builder separately matches reviewed delivery origin
slugs through `application_domain_slugs` and exact
`application_catalog_sources` IDs to the published
`profile_payload_occurrences`/`loadout_payload_occurrences` with their
corresponding item rows. Each `unitUses` occurrence preserves the Army,
source Unit, group, profile or option ID, source catalog item ID/position,
logical Unit slug and reviewed delivery method. It represents a source item
listed in a source profile/loadout, **not** a deployed object already on the
table or a derived Army List legality claim. Direct source `unit_option_*`
rows are separately classified as Unit-wide options, with `armyId` and
`groupId` kept `null`. One-level reviewed delivery uses also traverse
`profile_occurrence_includes`, `loadout_occurrence_includes` and
`unit_option_include_targets` to exact included loadout payload rows.
Include occurrences retain parent profile/option ID, Include position,
target payload ID and target label. Unit-option Include targets expose
`targetArmyId` as **target provenance**, not membership of the parent
Unit option in that Army.

Include paths must resolve uniquely within Army/source Unit context,
preserving exact occurrences, quantity, target and intermediate identities.
The transitive Include audit (`tests/test_deployed_object_transitive_includes.py`) checks arbitrary depth for further reachable
uses, missing/ambiguous targets and cycles. Do not synthesize a recursive
path that loses owner context. Missing exact matches are not proof of
zero possible users.

WildParrot distinguishes Place Deployable
from WIP-based Intuitive Attack; Armed Turret uses the reviewed curated
object by `originRuleId` and retains the S1/S2 dispute. Mine Dispenser
has no exact resolved subtype and remains an unresolved delivery.
Source-catalog aliases alone cannot establish delivery methods, carrier
legality or equivalence between Weapon modes. Missing evidence is not proof
an object cannot be deployed.

The source-schema review distinguishes direct source Unit ownership from
catalog availability and reusable metadata. Army-local `profile_*` and
`option_*` item occurrences, plus source-wide `unit_option_*` occurrences,
are eligible for reviewed reverse uses; Army-level `army_weapons` and
`army_equipment` catalogs are not carriers. Army option Weapons are reached
through `option_weapons` and `option_weapon_templates`; the template alone
does not establish Unit ownership. The three source Include contexts may
reference exact option targets, with Unit-wide Include targets retaining
unknown parent Army membership. `metadata_weapons` describes source profiles
and modes, not carrier assignments. A schema-level regression guards these
known structural context roles against silent additions; it cannot establish
whether an unreviewed rule, mode or source-text mention represents another
deployed object.

Every published object carries an explicit `unitUses` list, possibly
empty when no exact uses are established. The API catalog and exact-ID
endpoint expose those same facts; an absent embedded model gives 503,
and invalid Army binding fails closed on startup. Requests do not open
raw archives or curated review files.

The maintained `tools.data.audit_deployed_object_inventory` and storage,
source and browser regression tests verify the reviewed inventory and
delivery origins. A delivery edge is not a deployed object already on
the battlefield, a carrier-legality verdict or an exhaustive model of
N5.3 objects. The
[historical deployed-object review](https://github.com/frankysan/InfinityDB/blob/a7fc1900d73e4bc9b44561c20b04e58e73fbb8b6/docs/data-model.md#deployed-object-read-model-and-artifact-gated-browser-reference)
retains the dated inventory, migration evidence and detailed individual
Immunity examples. Unresolved Mine Dispenser subtype, S1/S2 Armed
Turret dispute and other source questions retain their published scope.
