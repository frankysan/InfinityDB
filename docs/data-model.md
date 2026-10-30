# Data model

**Project domain:** Data processing

This document owns InfinityDB's **current semantic and persistence model**. It describes what the
source means to InfinityDB, which abstractions the project introduces, how those facts are stored,
and which invariants runtime queries rely on. Historical audit counts, release benchmarks, and
migration chronology belong in Git history or `docs/CHANGELOG.md`, not in this current-state
contract.

Unless explicitly marked otherwise, statements below describe the current repository model.

## Pipeline and persistent artifacts

Army-derived data flows through three conceptual layers:

```text
immutable Army snapshot
        ↓
lossless merged/master representation
        ↓
validated normalized source model
        ↓
SQLite export
        ├─ infinity.db      canonical application/runtime data
        └─ infinity.raw.db  lossless normalized source/audit archive
```

Curated rules data follows a separate path:

```text
reviewed data/curated/rules/*.json
        ↓
validation/composition
        ↓
rules.db
```

The two runtime databases are intentionally separate because Army data and reviewed rules knowledge
have different sources, provenance, and update cadence.

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

### Deployed-object read-model and artifact-gated browser reference

`infinity_db.deployed_object_reference.project_deployed_references` consumes
the validated N5.3 deployed-object audit and produces a **pure, read-only**
reference projection. It currently covers 15 exact Army profiles plus the
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
Unit option in that Army. The pinned-source regression audit in
`tests/test_deployed_object_transitive_includes.py` traverses contextual
Include chains to arbitrary depth, requiring a *unique* intermediate
`loadout_payload_occurrences` row in the same Army and source Unit at
every hop. On the pinned 2026-10-22 database and reviewed delivery origins,
it finds **no additional transitive source-item uses, ambiguous intermediate
targets or cycles**. Synthetic tests ensure new reachable uses, shared
same-context payloads and cycles are detected rather than silently accepted.
Consequently no recursive relations are projected for this snapshot; any new
matches require preserving the full Include path before publishing them.
Unresolved Mine Dispenser subtypes remain unassigned. Objects lacking exact
matches are not claimed to have zero possible users. The read-only
`tools.audit_deployed_object_detail_queue` scan covers deployable, token and
scenery mentions in maintained Weapon/Equipment definition detail fields,
not just summaries. Its only initially unreviewed detail-only finding,
Cube 2.0's Command Token recovery reroll, is source-backed and classified
as automatic Equipment rather than a deployed object; the resulting
review manifest remains distinct from new object/delivery publication.
The separate read-only `tools.audit_deployed_object_delivery_coverage`
compares the 17 published reviewed object identities against their *approved*
delivery origins. All 17 currently have reviewed origins (28 approved delivery
paths in the pinned review); this closes the bounded published-object delivery
queue, **not** the inventory of all possible deployed objects. WildParrot
distinguishes ordinary Place Deployable from Intuitive Attack with a WIP Roll.
Armed Turret has no separate Army auxiliary-profile selector: its approved
delivery path targets the exact reviewed curated object by `originRuleId`,
retaining its S1/S2 Silhouette conflict. Mine Dispenser has neither an exact
reviewed target profile nor a reviewed-only object and remains unresolved.
The audit reports exact Army source-catalog aliases as investigation leads,
**not** evidence of a delivery method, legal roster carrier or equivalence
between distinct Weapon modes. Missing delivery edges are evidence gaps,
not claims that an object cannot be deployed.

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

The release-builder `tools.build_deployed_object_publication` compiles the
validated review and current Army/rules database pair to deterministic
`deployed-objects.json` once during release preparation. Every published object
must carry an explicit `unitUses` list (which may be empty when no exact uses
are established); an omitted list is invalid, not a claim of zero uses. The
runtime loader checks the artifact's Army and rules database SHA-256 hashes and
structural attribute/identity provenance. It does **not** access the raw normalized Army
snapshot, curated JSON, or review files on requests. When the artifact is
present, `/api/deployed-objects` and the `/deployed-objects` browser page
publish its reviewed identities, attributes and delivery source links.
`/api/deployed-objects/{id}` returns one exact reviewed identity.
When it is absent (legacy or not-yet-built release), the API returns 503
rather than reconstructing source assertions from raw tables; a mismatched
artifact fails closed on startup. Auto-discovery applies only to a
**co-located Army/rules database pair**: an explicitly supplied rules database
from another directory is an independent source, so the application does not
attach a release publication from beside the Army database. The deployed-object
API returns 503 in that mixed-source configuration. A mismatched publication
beside a co-located release pair still fails closed on startup.

Release packaging generates this deterministic, Git-ignored publication from
the tracked database pair and reviewed source files immediately before the
Docker build. The image copies it beside both databases; its startup smoke
test verifies source-pair hashes, 17 reviewed objects, the unresolved Mine
Dispenser origin and the HTTP/browser entry points. Hosted release packaging passed on commit `9c9a09f` (2026-10-22);
repeat against the final release candidate. Transitive Includes,
other as-yet-unverified usage contexts, extra objects and full-source
inventory remain v1.0 tasks.
Do not describe these delivery origins or partial reverse uses as proof of
complete Unit ownership, Army List legality or an exhaustive N5.3 model.
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
summaries, citations and routes, copied from `rules.db` at response time.
The API resolves maintained inline references in these summaries to
`summary_tokens` with navigable public references; the browser renders
those tokens rather than exposing raw `[[...]]` source notation.
The Weapon profile displays these in a collapsible **Ammunition effects
(shared rules)** section, while its original PS, Burst, Saving Roll,
Traits and modes remain untouched. The `ammunition_effects` projection
is omitted for unreviewed/mismatched source ammunition; its existence
establishes only reusable component coverage, **not** exception/interaction
completeness. Component texts and citations are never authored in the mapping
or inferred from notation. Combined components remain distinct, not
a resolved attack result.
The Weapon source-review audit has a separate maintained decision file,
`data/curated/weapon-shared-effect-reviews.json`, for individually verified
Weapon profiles whose shared components and published Traits already suffice.
Those approvals are pinned to full Army profile SHA-256 fingerprints and the
official chart page. They are not inferred from the mere presence of an
ammunition link, and a changed profile reopens review. Unreviewed and
mode-specific Weapon behavior remains in the triage; explicitly reviewed
shared-only identities do not require fabricated standalone rule records.
The first reviewed Ammunition effect pilot now lives on canonical `ammunition:*`
records, not on Army mapping entries. The validated, non-executable
`facts.ammunitionResolution` object can describe halving the applicable ARM/BTS
Attribute (AP), two Saving Rolls per hit (DA/E/M), and E/M State outcomes with
failure conditions and eligible target categories. The EXP, PARA, and T2
extensions add three rolls per EXP hit; a PH-6 Saving Roll with no effect
against targets lacking PH and Immobilized-A on failure for PARA; and
separate T2 Wound counts for a failed hit roll versus a failed additional
Critical roll (2 versus 1). Normal and Shock record one Saving Roll and
one Wound per failed roll; Shock's direct-to-Dead outcome applies only to
failed rolls against targets with VITA 1. Stun records the Stunned State
and automatic Guts Roll failure on a failed Saving Roll, except with Courage
or equivalent rules. These facts flow through `rules.db` to Ammunition detail
APIs with the records' existing citations. Smoke and Eclipse instead use a
separate `facts.visibilityZone` shape recording the Circular Zero Visibility
Zone, infinite height, expiration, and the distinction between Smoke's MSV
exception and Eclipse's Reflective blocking of all MSV Levels. This is
visibility reference data, never a synthetic Saving Roll or a guarantee
that a Smoke Template succeeds against all attacks. The
Weapon API separately exposes source-authored profiles and reviewed combined
component IDs. It does **not** merge these facts into an inferred roll result:
Feuerbach's AP+DA source combination remains distinct from its `ARM/2` and `2`
fields, and Plasma Carbine's `ARM and BTS` / `1 and 1` remains a Combined Saving
Roll with Normal Ammunition, never a synthetic composition.

All eleven published base Ammunition identities now carry reviewed typed
facts, but the contract is deliberately non-executable: it does not model
critical attack resolution generally, Smoke/Eclipse Face to Face adjudication,
all conditional immunity/target interactions, or combined-Ammunition
precedence. This is not yet a complete curated Ammunition effect/relation model or a
general combined-Ammunition evaluator. Conditional State outcomes are also
published as authored `causes-state` rules-graph links for E/M, PARA, Shock,
and Stun. The curated validator requires the set of targets on these links to
match `facts.ammunitionResolution.stateEffects` exactly; target/attribute
restrictions and Saving Roll failure conditions remain in the typed facts,
not on the simple relation edge. Both directions of each link are available in
reference pages. Nine roll-bearing base Ammunition records now also carry
`criticalAdditionalSavingRolls: 1`. This represents the single extra Saving
Roll from a Critical, not a multiplicative roll count per combined component.
Smoke and Eclipse retain only visibility-zone facts and no Saving Roll facts.
For the five reviewed Combined Ammunition forms (four AP-based plus
`N+E/M`), the component mapping still publishes identities only: it does not
add, multiply, or adjudicate those rolls. `N+E/M` is explicitly printed in the
N5.3 Combined Ammunition example (p. 67) and mapped from exact Army source ID 5,
not inferred from the `+` in its name. E/M CC Weapon retains two BTS/2 Saving
Rolls per hit and no additional ARM Saving Roll; its standalone Property
explains Normal's potential Wounds alongside E/M's conditional State effects.
The imported Armed Turret E/Mitter mode remains a separate source profile
listing one BTS/2 Saving Roll, and is not rewritten to match the generic E/M
Ammunition facts. Both English and Spanish N5.3 charts give the standard
E/Mitter two Saving Rolls; the conflict is confirmed and visibly noted in the
curated Armed Turret reference (REA-045), not reclassified as an authorized
special rule.
The additional roll retains applicable constituent effects; T2's
`woundsPerFailedSave.criticalAdditionalRoll` remains distinct from its regular
hit effect. Combined Saving Rolls (including Plasma's ARM/BTS case) have a
different extra-roll target rule and remain outside this fact pilot.
The other Ammunition effects, complete combined Critical interactions,
and broader semantic relationships still require source review.

The separate reviewed Combined Saving Roll projection now pins the six
Plasma Carbine, Plasma Rifle, and Plasma Sniper Rifle Hit/Blast source profiles
(including the source spelling of each name). Only exact source ID, mode,
Ammunition identity, and Saving Roll fields receive
`combined_saving_roll: {kind, rolls, critical}` in the Weapon API. The pinned
N5.3 rule specifies one additional **ARM** Saving Roll for a Critical, on top
of the ARM and BTS Saving Rolls from the hit. This is a reviewed source-profile
annotation, not a roll evaluator, an Ammunition effect, or an inferred
`ammunition_composition`. Other Weapon Saving Roll notations remain untouched.
Full cross-source Combined Saving Roll coverage and immunity interactions remain
open. A full identity/transport parity gate in
`tests/test_ammunition_publication_parity.py` separately asserts that all
16 explicitly reviewed Army Ammunition source ID/name pairs (11 base and five
combined) resolve to the same 11 canonical `ammunition:*` records, with
unchanged citations/summaries, navigable component identities, at least one
actual Weapon profile for each source identity, and unchanged imported
Saving Roll fields. All five combinations also have HTTP Weapon-detail
coverage. The independent pinned N5.3 p. 67 check establishes printed
examples for AP+DA, AP+Exp, and N+E/M; the other two combinations are
verified against exact Army metadata and public profiles instead. This is
a completeness gate for the *reviewed map*, not coverage of all source
Ammunition IDs, combined effect precedence, full Critical mechanics, or
a future Weapon comparison view.

**Weapon Properties (current):** InfinityDB maintains a separate, descriptive
`weapon-property:*` vocabulary in `config/catalogs/weapon-properties.json`.
It does not redefine Ammunition, Traits, source Army `properties` (Traits), or
weapon-specific rules. Each entry has a player-readable explanation and an
explicit list of canonical rule-record origins (with their role and domain),
or an exact official source section when there is no standalone canonical
rules record. Reviewed memberships pin Weapon source ID, exact source name,
mode, Ammunition source ID/name, Saving Roll fields, and source Traits.
The runtime projection only attaches a Property to a profile matching that
whole signature; weapon names and punctuation are never parsed to grant
mechanics. Properties are displayed on matching Weapon profiles and indexed
as embedded Glossary/global-search concepts, without a separate top-level
catalog or a new rule evaluator. Twelve reviewed definitions currently cover
Plasma, Viral, Breaker, K1, MULTI, Monofilament, Silenced, the four
AP-based combinations and the distinct `N+E/M` source combination.
Standalone E/M remains canonical Ammunition, not a duplicate Weapon Property.
Curated rules prose can link explicitly to
`[[weapon-property:...]]`: the rules exporter validates each target against
the maintained registry, and the runtime resolves it to a Glossary entry and
summary preview without creating a second canonical rules record. Source
profiles, Ammunition composition, Combined Saving Roll, and Traits remain
independent. This maintained configuration is included in installed packages,
following the existing runtime catalog-configuration pattern.

A bounded Immunity cross-reference now publishes `skill:immunity`'s validated
`facts.immunityInteraction` (N5.3 Wiki Immunity `oldid=3643`). It describes
covered Ammunition as Normal, the loss of special effects and Saving Roll
modifiers, the default additional Critical Saving Roll (unless the defender has
Immunity (Critical)), and the Comms Attack/Non-Lethal/Stunned exceptions. These
facts belong to Immunity, **not** to the ordered Combined Ammunition mapping:
checking whether a defender's particular Immunity covers an entire attack or
one or more constituent effects remains unimplemented. Five `reviewedCombinedCases`
now give **rule-derived, conditional** examples: Immunity (ARM) against source
IDs 10 (AP+DA) and 13 (AP+Exp), plus Immunity (AP) against AP+DA and
the exact non-Comms E/M CC Weapon's Immunity (BTS) interaction.
The AP case records its ignored AP component and surviving DA effect, retaining
two full-ARM rolls (three on Critical), instead of collapsing to Normal.
Each example preserves before/after hit and Critical counts with source IDs,
components and explicit evidence status. They are stored on Immunity rather
than on the Ammunition navigation mapping. No roll counts, State outcomes, or
immunities are projected into individual Weapon profiles. A separate
`reviewedVulnerabilityCases` entry records the **explicit** Vulnerability (Viral)
versus Immunity (Enhanced) example (Wiki Vulnerability `oldid=3156`): the rule
matches a weapon whose *name* contains Viral, not an Ammunition component.
This example adds no weapon-name parsing at runtime. An independent, explicit
`reviewedWeaponCases` entry records the pinned Immunity (BTS) versus Flash Pulse
example (Wiki Immunity `oldid=3643`, Weapon Chart `oldid=4083`): Stun becomes
Normal, but Non-Lethal and Stunned on a failed Saving Roll remain. Flash Pulse
has its own cited Weapon reference and semantic links; none of these cases
executes a Weapon profile calculation. The **printed** N5.3 p. 96 Example 3 is now a separate authored
`skill:immunity.facts.immunityInteraction.reviewedSavingRollCases` entry:
Plasma Rifle versus Immunity (Enhanced) retains one ARM and one BTS
Saving Roll because the weapon has Normal Ammunition and a Combined
Saving Roll, **not** Combined Ammunition. This exact-source example has
its own closed validation contract, a linked player-facing Immunity
interaction, and regression against the pinned PDF, Army Plasma profile
and existing Combined Saving Roll map. It is not added to the
`reviewedCombinedCases` component examples or as an inferred
`immunity_result` on Weapon profiles. A fourth combined case is now explicitly bounded to
`weapon:e-m-cc-weapon`: the N5.3 p. 177 non-Comms CC Weapon uses
Army Ammunition source ID 5 (`N+E/M`) with BTS/2 × 2; p. 67 and
Immunity (BTS) p. 95 support a **rule-derived** one-roll Normal
BTS result (two for Critical without Immunity (Critical)). This
case is stored on `skill:immunity`, not the source Ammunition map
or Weapon profile. The checked-in `rules.db` and regenerated
deployed-object publication were promoted together, with all
17 reviewed deployed objects unchanged and a recovery backup.
A separate **standalone E/Mitter** `reviewedWeaponCases` entry
fixes the exact source weapon ID 25 and E/M ID 14, with the
original BTS/2 × 2 and conditional Immunity (BTS) one-BTS-roll
result. The surviving **Non-Lethal** Trait and absence of E/M State
effects are shown only as source-backed player guidance. The
Armed Turret source weapon 226's conflicting one-roll E/Mitter
mode remains untouched and explicitly excluded (REA-045).
The **fifth** combined case is the exact non-Comms
`weapon:silenced-pistol` AP+Shock/BTS/2 profile (Army Ammunition
source ID 30). A defender with Immunity (AP) ignores AP's halving,
retaining the one-roll Shock effect at full BTS, including its
VITA=1 failed-roll Dead condition. Silent (-6) remains a
separately conditional Trait. The Army profile and Ammunition
component mapping remain unchanged; this is not a generalized
partial-Immunity algorithm.
The **sixth** combined case is narrowly scoped to the
`weapon:ap-t2-cc-weapon` non-Comms source profile (Army
Ammunition ID 40). With Immunity (AP), the one ARM/2
Saving Roll becomes one full-ARM roll (one extra on Critical),
but T2's failure consequences stay distinct: **2 Wounds**
on a failed hit roll, **1 Wound** on a failed extra Critical
roll. The new `failedRollWounds` member is validated against
canonical `ammunition:t2` facts; it is not an arbitrary
combat computation. The independent Anti-materiel Trait and
the original Army ARM/2 profile are preserved.
The ten reviewed interactions are a curated reference, not a
runtime Weapon-resolution engine. Coordinated `rules.db` and
deployed-object publication remain synchronized; 17 reviewed
deployed objects are unchanged. Other component Immunities, Comms
Attack coverage, BTS conditions and unreviewed combinations
remain unresolved.

The Perimeter Trait likewise does not imply Boost. A WildParrot uses
Perimeter deployment followed by E/M Mine behavior with a visible Token/Model;
its specific rules are separately curated, and missing Army Trait notation is
not manufactured from the printed rulebook.

Current runtime database versions:

- Army application database schema: **25**;
- Army application compatibility revision: **34**;
- rules database schema: **8**;
- rules database compatibility revision: **10**.

`data/README.md` owns source/snapshot format versions, while `data/curated/README.md` owns the
curated-rules format version. Schema and compatibility validation is fail-closed. Incompatible
generated databases are rebuilt; there is no in-place migration contract for current generated
Army/rules databases.

## Semantic provenance

A field or relationship must be understood by provenance class before it is deduplicated or
presented.

### Source-native facts

These are represented directly by Army or another cited source: source IDs, names, profile values,
loadout costs, Army-list membership, source extras, notes, Fireteam rows, and similar material.
InfinityDB may normalize their representation but must preserve their source coordinates and meaning.

### Source-derived facts

These are deterministic interpretations of explicit source relationships, such as Army grouping or
role derived from metadata parents and reinforcement links. The derivation is application logic, but
the evidence remains source-owned.

### Curated/reviewed facts

These are human-reviewed project data derived from official sources where the application needs a
stable relationship the upstream data does not directly supply. Examples include identity aliases,
legacy Army presentation records, Peripheral mappings, historical relationship endpoint evidence,
maintained rules summaries, and typed rules relationships.

### InfinityDB abstractions

These are application concepts introduced to make multiple source views coherent. They must not be
presented as if they were source-native. Important examples are:

- logical Units spanning equivalent source representations;
- the General profile abstraction;
- canonical profile/loadout payload identities;
- application-domain slugs; and
- cross-domain composed reference projections.

### Presentation-only structure

Browser grouping, card/disclosure structure, responsive layout, visual labels, and other display
conveniences are not game-data semantics unless backed by a data-model contract.

## Identity model

InfinityDB keeps **source identity**, **application identity**, **relationship context**, and
**presentation identity** separate.

### Army identities and roles

`application_armies` is the canonical runtime Army projection. Army-list source records and metadata
factions are evidence used to build that projection; they are not interchangeable identities.

Current roles include main, sectorial, non-aligned/grouping, and reinforcement. Role/grouping is
derived from imported relationships and reviewed policy rather than ID ranges. In particular:

- source identity `1` remains mercenary source provenance;
- current Non-Aligned application grouping is represented separately (source grouping identity
  `901` in the current snapshot);
- reinforcement lists retain explicit parent relationships; and
- a grouping identity may exist in source metadata/source lists without being independently playable.

Playability, catalog/discontinued status, grouping, parentage, concrete roster availability, broader
faction membership, and browser display identity are separate facts.

`main_army_id` is a compatibility-named application grouping field, not authoritative roster
membership. `display_army_id` is the reviewed presentation identity used for faction symbol/styling
where it differs from source/main grouping. Browser code consumes these projections rather than
special-casing Army IDs.

### Logical Units

A logical Unit groups source Unit representations that reviewed/source-derived evidence says are the
same application Unit. Build-time identity processing materializes that mapping; runtime queries do
not recompute it from names or ID arithmetic.

The logical Unit layer owns game-wide Unit identity and aliases while preserving every source
occurrence needed for Army/profile/loadout context. A reinforcement or optional-mercenary source
representation can therefore belong to the same logical Unit without erasing its distinct
availability path.

Configured aliases remain maintained policy and are pinned into generated metadata; they are not
rewritten into source rows.

### Spec-Ops and TEAM-OPS source-choice charts

Army `spectables` is source-native *choice inventory*, not a configured roster or a Trooper's
selected upgrades. Each source Unit's chart is stored unchanged in `logical_unit_spectables`;
`Database.get_unit()` exposes it under `source_charts`, scoped by exact
`source_unit_id` and carrying source name and Army source-version/file provenance.
Source names resolve through the materialized logical-Unit/alias projection by exact
source Unit identity; normal chart serving does not read the raw `units.name` copy.
The projection retains the two independent `table` and `specball` collections,
source order, and every attribute in compound entries. Source catalog IDs are
resolved to available names and stable public routes; unresolved extras retain their
numeric source IDs and are not silently dropped. Raw `q` values and individual
MOV components are shown as source notation because the source payload alone does
not justify interpreting all of them as modifiers or final statline values.

The Unit detail page provides an ordinary read-only reference with relevant core
Skill links. It does not apply upgrades, validate a list, equate Spec-Ops to
ITS TEAM-OPS, or interpret the in-game Initial/Enhanced Profile transition.
The separate configurable-list/session feature remains deferred.

### General profile

The **General profile** is an InfinityDB abstraction for profile information that can safely be shown
once for a logical Unit rather than repeated for every Army occurrence. It is not an upstream Army
entity.

Only semantically compatible profile data may be consolidated. Materially different statlines,
profile identities, classifications, characteristics, or other contextual facts remain distinct.
Source profile IDs/names remain available as provenance even when multiple occurrences share one
application payload identity.

### Unit and General-profile symbols

Every published logical Unit has exactly one effective graphical symbol. A General profile inherits
that Unit symbol unless InfinityDB can resolve one distinct profile symbol for its normalized profile
identity. Raw Army `logo` values remain occurrence-level provenance and are not themselves the
semantic assignment. The tracked publication retains every authoritative profile-logo resolution as
evidence, including logos that are primary for one source Unit representation, because source Units
can later collapse into one logical Unit while their distinct General profiles remain meaningful.

Army profiles explicitly identified as Peripherals publish into a dedicated
`peripherals/<main-army>/<peripheral-name>.svg` namespace when that profile name is Peripheral-only,
including Units whose primary profile is itself a Peripheral. The Peripheral name comes from Army's
Peripheral metadata when it can be matched without guessing. Main-army folders follow the same
faction-parent hierarchy used by Unit symbol publication. Peripheral is contextual Army metadata,
not a global property of a profile name. When the same physical symbol is evidenced under the same
profile name in both Peripheral and normal Unit contexts, InfinityDB treats that name as mixed-role:
its artwork stays Unit-owned under `units/`, including any additional contextual variants of that
name. Byte-identical occurrences therefore resolve to one Unit-owned symbol, while genuinely
distinct artwork remains preserved as separate Unit-profile assets. Likewise, if Army reuses parent
Unit artwork for a Peripheral occurrence, the physical asset remains Unit-owned. Distinct physical
assets for Peripheral-only names remain preserved as context-suffixed Peripheral variants rather
than being silently discarded.

The tracked symbol publication may promote a cross-Unit profile-symbol consensus when one
published symbol is a strict majority across distinct parent Unit symbols for that profile identity
and is observed as a non-Unit override against at least two different parent Unit symbols. Repeated
Army occurrences of the same Unit count once. This permits
InfinityDB to repair repeated Army assignment errors without treating a single Army-specific
variant as a global graphical identity. Ambiguous contextual evidence falls back to the Unit
symbol rather than exposing multiple effective symbols for one General profile.

### Profile and loadout payloads

Profiles and loadouts are treated as structured semantic payloads rather than deduplicated by display
name alone.

- A **profile payload** owns profile statistics and profile-scoped categorical facts.
- A **loadout payload** owns shared loadout content such as weapons, equipment, skills, Orders,
  and includes. Points and SWC belong to `loadout_payload_occurrences`, so equivalent content can
  be shared without erasing Army-specific prices.
- Context tables connect those canonical payloads back to source Unit, Army, profile-group, and
  loadout occurrences.

Exact structural equality is useful evidence but does not by itself justify semantic identity when
source context says two records mean different things. Conversely, equivalent payloads may be shared
when the contextual relationships remain explicit.

### Rule-variant usage index — accepted design direction (not implemented)

**Project domains:** Data processing, Web backend, Web frontend

The planned cross-Army index answers **which Units can field a reviewed
Skill/Equipment variant**. It is a read-only projection of existing identity,
payload and occurrence relationships, not a second source of Skill definitions,
a loadout builder, or a record of randomized game results. The index is not
generated or served yet; see `docs/TODO.md`.

**Rule identity and variant identity.** The primary grouping key is the
published canonical rules identity (for example `skill:martial-arts`),
resolved through reviewed source-to-application catalog membership and the
corresponding rules reference. A variant key additionally records explicitly
reviewed, typed differences: Level, MOD, named parameter, and any applicable
source-scoped restrictions. The typed signature is deterministic and
source-bound; distinct modifiers such as `+1 SD` and `+1B` cannot be merged.
A shared family does not imply that all of its variants are equivalent. Retain
the source catalog ID, raw variant/extras and rule citations as provenance.

**First verified exact-source pilot (Martial Arts L1-L5):** Army Skill source
IDs `19`, `20`, `21`, `22`, `23` share one published application Skill
but each resolves to `skill:martial-arts-l1` through
`skill:martial-arts-l5`, respectively. Each reviewed N5.3 record has
`variantSemantics.sourceVariant = {"kind": "level", "value": N}`, a
`variant-of` link to `skill:martial-arts`, and N5.3 p. 100 provenance.
The separate Army Martial Arts chart confirms L3 `+1 SD`, L4 `+1B`
and L5 both. Current direct source relationships in the pinned Army
snapshot do not attach additional extras to these five Skills; the
repository checks this against the source-only `infinity.raw.db`
tables as well as `infinity.db` catalog/usage projections and
`rules.db` variants. This is a **source/semantic regression contract**,
not a generated occurrence index or a guarantee for other source
Skill families.

**Additional verified exact-source families:** Strategos source Skill IDs
`69`/`70` are discrete Levels 1/2 (N5.3 p. 113); BS Attack
`278`/`279` replace BS with 12/11 (p. 39), and CC Attack `274`
replaces CC with 21 (p. 51). The reviewed source variant maps and
current direct Army occurrences agree; these source Skills have no
separate occurrence extras in the pinned snapshot. Source family identity
is not an additional Level or an Attribute replacement.

The reviewed TinBot Equipment family has six exact-source named
variants (N5.3 p. 127 and preserved Wiki provenance):
`169` Firewall, `188` Neurocinetics, `193` Albedo,
`244` Discover, `247` ECM Guided and `248` Repeater. The
current Army application catalog contains **only 169, 244, 247 and 248**
of those six named variants; `188` and `193` retain reviewed definitions but
have **no direct source occurrence in this pinned snapshot**. Do not
promote their rules definitions into current Unit-use counts. Unlike
Level/Attribute replacement source Skills, TinBot variants can carry
distinct occurrence-level extras such as listed MODs. N5.3 p. 127 calls its example `TinBot: Guided (-6)`,
while the reviewed source-specific variant is named `ECM Guided`;
keep that label distinction visible rather than deriving a new
source identity or conflating the two names automatically. Preserve each
actual source extra's ID/type/value and direct owner context. No MOD
may be inferred just from the `named` variant label, and TinBot's
Fireteam-sharing behavior does not create direct Skill/Equipment
occurrences for every eligible Fireteam member. The reconciliations are
enforced by `tests/test_other_source_variant_provenance.py`; they
do not implement or populate the eventual usage index.

**Remaining source-parameter inventory (pinned Army source and current
generated rules database):** `tools/audit_source_variant_inputs.py` produces a
deterministic, read-only JSON inventory from `infinity.db`,
`infinity.raw.db` and `rules.db`
(`python -m tools.audit_source_variant_inputs`). It inspects exact
source IDs, direct profile/loadout/Unit-option relationship rows,
ordered extra IDs/types/values, raw occurrence values and reviewed
source-variant mappings. It does **not** calculate Unit usage.

The following baseline uses the current **tracked**
`data/generated/rules.db` alongside the paired pinned Army
application/raw databases. The tracked artifact now includes the
reviewed Mimetism, Berserk, Dodge and Surprise Attack occurrence-parameter mappings.
This baseline contains **96 Skill** source identities across
**33,153 direct rows** and **34 Equipment** source identities across
**5,427 direct rows**:

- Skills: 10 reviewed exact-source IDs without occurrence extras;
  44 family-only IDs; 1 reviewed distance-parameter source
  (Forward Deployment, `161`); 3 reviewed numeric-parameter
  sources (Mimetism `28`, Berserk `24` and Surprise Attack `191`); 1 reviewed
  extra-parameter source (Dodge `40`); and **37** IDs with
  unresolved occurrence parameters.
- Equipment: 1 reviewed exact-source ID without occurrence extras;
  19 family-only IDs; and 14 IDs with unresolved occurrence parameters.
  Four currently published Equipment source IDs have reviewed
  exact-source variant definitions, but three of those have extras
  that remain **separately unresolved** as typed usage-index parameters.
- `TEXT` extras occur across 39 Skill source IDs and 14 Equipment
  source IDs. `DISTANCE` occurs across 5 Skill source IDs;
  Forward Deployment `161` is the only source with exclusively
  `DISTANCE` extras and matching reviewed distance semantics.
  Dodge `40` and Super-Jump `74` mix `TEXT` with `DISTANCE`;
  Dodge's exact observed signatures are reviewed; Super-Jump, Jump
  `263`, and Climb `271` are not certified at the same level.
  Do not infer coverage from source type or player-facing prose.

These statuses are conservative **per-source-ID audit flags**.
A flagged source may also have valid, unparameterized occurrences,
and reviewed family rules remain available. An exact reviewed
source variant with an unreviewed occurrence extra is *not*
a reviewed combined variant. In particular, Booty/MetaChemistry
`ReRoll`, Mimetism `-3/-6`, TinBot `-3/-6`, and Hacking
Device `UPGRADE` source text must not be promoted to typed
variant keys on string parsing alone. The audit retains separate
signatures for each extra combination and detects source
drift via `tests/test_audit_source_variant_inputs.py` **when the
paired, Git-ignored raw Army archive is available**. This source-only
provenance suite explicitly skips in clean CI; ordinary CI success
does not revalidate these occurrence counts. See
[the raw-archive test contract](testing.md#full-army-source-archive-provenance-tests)
and [CI policy](ci.md#source-checks). This is a
snapshot-characterization gate, not a source completeness,
historical correctness or usage-index claim. Further parameter
reviews should extend explicit typed semantics and tests, not
relax these unknown/exclusion boundaries.

**Numeric Skill MOD evidence (first bounded review):** The local English N5.3
PDF confirms that Mimetism's bracketed `-3`/`-6` is a negative
modifier to **enemy** BS Attacks requiring LoF and Discover (p. 102),
not to the Mimetism user's own roll or to CC Attacks. The pinned Army
source Skill ID `28` has exactly 1,612 direct relationships with
`extra_id=6` (`TEXT: -3`) and 392 with `extra_id=7`
(`TEXT: -6`), with 2,004 relationships total. Berserk source
Skill `24` includes 243 direct `TEXT: +3` relationships
(`extra_id=1`) and three `TEXT: +6` relationships
(`extra_id=2`); its bracketed positive MOD applies to the owner's
Berserk CC Attack (p. 86), which also explicitly permits applicable
+1 SD during its Long Skill. Dodge source Skill `40` includes
613 direct `TEXT: +3` relationships (`extra_id=1`),
seven `TEXT: +6` relationships (`extra_id=2`) and separate
`DISTANCE` extras; generic negative Skill MOD behavior (p. 23),
Dodge's own situational -3 PH conditions, and successful Dodge
movement (p. 79) must remain separate.

`tests/test_audit_source_variant_inputs.py` pins these
source-signature facts and guards against conflating the three
rules. The curated grammar now **accepts explicit reviewed**
`variantSemantics.occurrenceParameters` `numeric-mod` entries
alongside the existing distance type. A numeric-MOD entry binds
source-extra IDs, exact `TEXT` values and signed numeric values
to a specific Skill family, modifier owner, target and applicable
actions; see `data/curated/README.md` for the validated grammar.
`RulesDatabase.skill_numeric_mod_semantics()` exposes this typed
metadata separately from the existing distance-only display API.
The inventory verifies *every* extra signature against exact
source IDs/types/values before classifying it as reviewed; even a
reviewed family definition does not automatically certify an
unmapped extra. A future occurrence with multiple extras must
have **every** component reviewed before becoming countable.

**Reviewed Dodge source-variant reconciliation:** The N5.3 curated
Skill ID `40` now has 14 distinct, **single-extra** signatures
across **2,382** direct Army source relationships. The existing
`numeric-mod` entry owns `+3` (613 uses) and `+6` (7 uses)
on its PH Roll. A separate, exact-source `reviewed-extra` map
now distinguishes:

- `TEXT: -3/-6` (source extra IDs 6/7; 30/1 uses): a
  **negative MOD to the opponent** in a Dodge Face to Face Roll,
  not the Dodge user's situational -3 PH penalty;
- `DISTANCE: +2.5/+5/+7.5` cm (IDs 11/23/260; 633/808/4
  uses): a successful Dodge's movement bonus, equivalent to
  +1/+2/+3 inches under the project's 2.5-cm conversion;
- `TEXT: PH=9/10/11/12/13` (IDs 46/32/27/250/52;
  110/3/151/6/5 uses): the PH Attribute used **for Dodge**
  rather than an additional +PH MOD;
- `TEXT: +1SD` (ID 308; 9 uses): one extra Dodge Roll die
  under N5.3 p. 75; no increase in Burst or additional Disposable use;
- `TEXT: ARM +3` (ID 379; 2 uses): +3 ARM for Saving Rolls
  after declaring Dodge, not +3 PH. Follow the English and Spanish
  N5.3 PDF text; preserve the separately documented Wiki conflict.

The test baseline rejects invented composite signatures: none of
the 2,382 source occurrences contains multiple extras. The
new `RulesDatabase.skill_reviewed_extra_semantics()` query
exposes this reviewed typed evidence separately from the legacy
distance-only display query and `skill_numeric_mod_semantics()`.
Source ID `40` is now `reviewed-extra-parameter` in the
tracked `rules.db` and in a freshly exported database from
curated sources. With the Surprise Attack review below, both inventories
report **3 reviewed-numeric, 1 reviewed-extra, and 37 unresolved** Skill source IDs.
The inventory is read-only and does not overwrite either database.
`tests/test_audit_source_variant_inputs.py` checks the tracked
artifact and independently exports current curation into a
temporary rules database to verify the exact source signatures.
Certification is per observed source signature, not a new
player-visible variant index or a game-state simulator.

**Reviewed Surprise Attack occurrence MODs (2026-10-30):** Source Skill
`191` has 767 direct relationships, all with one exact extra: `TEXT: -3`
(ID 6, 762 rows) or `TEXT: -6` (ID 7, 5 rows). The family record now maps
these signed values to `surprise-attack-target-face-to-face-aro`, with the
Skill holder as owner and the attacked opponent as target. The new scope
is accepted only on the Surprise Attack family link; it cannot be mixed
with Mimetism's BS Attack/Discover scopes or a positive owner-roll MOD.
The owning rule continues to require Marker/Hidden Deployment at the
start of the Order, an eligible Attack and the Active Turn. Attribute-specific
variants and non-stacking exceptions are not inferred from these two
unqualified extras. The existing multiple-attacker FAQ is unchanged.
See [source review](n5-source-history.md#reviewed-surprise-attack-occurrence-modifiers).

Both the tracked v9 artifact and fresh curated exports classify this exact
source ID as `reviewed-numeric-parameter`. The guarded paired refresh permits
only occurrence-parameter additions in explicitly named existing family records;
every other row, schema object, Restriction and deployed-object payload must
remain identical. It does not populate the future Unit-use index or make the
parameter metadata part of the distance-only display API.

Do **not** parse a variant from a display string, strip punctuation, infer a
parameter from a shared family name, or count an unresolved variant as a
verified specific one. Missing/ambiguous variant semantics remain explicitly
unresolved and are excluded from **variant-specific** totals, while their
reviewed family membership may still be reported separately.

**Occurrence provenance.** Resolve an actual Army membership through
`application_army_sources`, `army_units`, and
`logical_unit_sources`; only a concrete list occurrence is evidence that the
Unit can be selected in that application Army. Keep the original
`(source_army_id, source_unit_id)` and `availability_kind`. For each
direct source Skill/Equipment relationship retain its owning layer and full
source key:

- profile: `(army_id, unit_id, group_id, profile_id)`;
- loadout: `(army_id, unit_id, group_id, option_id)`;
- Unit-wide option: `(unit_id, option_id)`, attributed to an application Army
  **only** where actual list membership and compatible context establish it.

Preserve the source relationship's `occurrence_id`, position, quantity,
extras and raw value for evidence, with the appropriate
`profile_payload_occurrences` or `loadout_payload_occurrences` join.
The reusable payload's item position identifies its relationship *within*
that payload. Neither the item position, numeric payload ID nor source
`occurrence_id` is a portable cross-snapshot semantic identifier. Use the
existing logical-Unit-scoped payload hash to identify equivalent payload
content **within the pinned source/build context**, while retaining distinct
Army/profile/group/option paths and contextual AVA, Points and SWC.

**Counting policy.** Publish clearly named measures rather than one
unspecified “occurrences” count:

- **Unique Units (global):** count distinct `logical_unit_id` for the exact
  reviewed rule/variant, across all eligible concrete Armies.
- **Unique Units per Army:** count distinct
  `(application_army_id, logical_unit_id)` for that rule/variant. A Unit
  legitimately available in two Armies counts once **in each Army**, but
  only once in the global count.
- **Distinct profile/loadout contexts:** count the corresponding
  `(application_army_id, logical_unit_id, owner_kind, payload_identity,
  exact_variant_signature)` once within each owner kind; report profile and
  loadout counts separately. Multiple rows/positions or source
  representations pointing to the same semantic payload do not inflate
  these totals. Each context still exposes *all* original source paths,
  group IDs and option-specific AVA/Points/SWC for drilldown.
- **Source relationship rows:** a separate provenance/debug measure, never
  the player-facing Unit denominator. Multiple same-variant rows may be
  preserved here even when they yield one Unit/context membership.

Variant membership is formed as a **set**, not a sum across profile Skills,
loadout Skills, Army-specific copies, or source IDs merged into one canonical
catalog family. Profile and loadout scopes remain distinct because a
loadout-only variant does not apply to every loadout, and Unit-wide options
are not implicitly assigned to every profile. Includes and Peripherals
require separately validated, explicitly labelled inheritance/relationship
paths; do not expand or multiply them into direct usage. Metadata-only
catalog definitions, chart outcomes available only after a Booty or
MetaChemistry roll, disabled/unavailable alternatives without concrete
membership, and broader declared faction membership alone are **not**
direct occurrences. An included target must not be silently promoted to a
selectable standalone option.

The generated index must retain pinned Army snapshot/build provenance and
rules-source/revision provenance. A source update, unresolved application
catalog mapping, contradictory variant parameter or unsupported relationship
shape must fail closed or remain flagged, not silently change totals. Public
links must resolve the canonical rule/variant and the actual Unit, Army and
compatible profile/loadout context; identifiers in this section describe
join semantics, not new public routes. Validate duplicate-source, reused
payload, repeated-row, cross-Army, shared-family/different-Level,
profile-versus-loadout and unresolved-variant fixtures before publishing.

### Application catalog identities and slugs

Skills, Equipment, Weapons, and other application domains may group multiple source IDs/labels into
one canonical browsing identity. Source membership remains materialized so filters and usage queries
match every member of the application identity.

Where a domain has a stable slug:

- generated application-facing links and maintained references prefer the slug;
- numeric IDs remain accepted for compatibility/provenance;
- the domain's central resolver owns both forms; and
- consumers must not derive slugs independently from labels.

Rules/reference semantic IDs (`skill:...`, `equipment:...`, etc.) remain distinct from public route
slugs even when they correspond one-to-one.

**Reviewed metadata-only Weapon publication:** The upstream `weapons` table
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

### Structured Skill reference charts

**Current.** Martial Arts, Booty and MetaChemistry use generated Army tables,
projected through Skill detail `structured_reference`; curated Skill records
own their rules explanations and citations. Original Army row values remain
intact. Martial Arts hides the PS MOD column when every value is absent,
while retaining the separate Burst and Special Dice meanings.

Booty exposes typed `conditional_outcomes` for rolls 12, 16, 18 and 20,
separating TAG and other-Troop-Type results. MetaChemistry exposes typed
`outcome_components` for its five combined results (16–20), distinguishing
Attribute modifiers, MOV values, Skills and parameters. Unsupported compound
or conditional syntax fails closed instead of merging effects as free text.

Reviewed outcomes carry additive canonical `public_reference` links only when
the destination resolves uniquely. Booty's HMG uses the reviewed Heavy Machine
Gun alias; parameterized Skill/Equipment outcomes retain their printed variants
while linking to the owning family. MetaChemistry's six Skill occurrences link
to five families, preserving Immunity (ARM)/(Enhanced). Attribute modifiers
and MOV remain typed text. These are reference projections, not selected random
results, permanent Unit-profile changes or an executable effects engine.

Source/version, PDF pages, exact Wiki revisions and historical FAQ comparison
belong to [the reviewed chart provenance](n5-source-history.md#reviewed-10-structured-skill-chart-provenance).
Repeatable API/browser verification belongs to
[testing](testing.md#10-martial-arts-booty-and-metachemistry-structured-chart-parity).

### Reviewed Restrictions Chart projection

**Current.** The N5.3 p. 194 Restrictions Chart has one reviewed
source-only manifest at
`config/validation/restrictions-source-chart.json`. Its six ordered
subjects and 14 negative conditions are projected reproducibly to
`src/infinity_db/web/static/restrictions-reference.json` by
`tools.audit_restrictions_source_chart`. The packaged JSON is the
runtime read model for the normal
[General Rules Restrictions section](/rules#restrictions); the browser
does not inspect maintained configuration or infer rules semantics.

Each condition retains a source action and scope, player-readable
description, optional exact destination link and original
`targetRecordId`; chart subjects retain reviewed `ownerRecordId`
when available. Skill, Equipment and State pages render matching
negative conditions with links to the exact chart row, using this
published read model rather than interpreting generic canonical
relations. TAG/VH/REM are unlinked source Troop Type selectors,
not new domain identities.
Mounted Motorcycles cannot Jump **upwards** or use ladders; Irregular
and REM restrictions concern **selection** as Lieutenant, not use of
Lieutenant skills. An absent source-negative relation does **not**
establish permission; neither this reference nor existing broad
`restricts-use-of` edges evaluate live action legality.
Source/manifest/PDF checks, static byte parity and browser acceptance
are documented in [testing](testing.md#n53-restrictions-chart-source-and-browser-reference).
The maintained typed condition model is implemented separately from the
generic relation graph. Irregular Training occurrence ownership has
also been verified: source Order types live at specific Army loadout/
Unit-option occurrences, not in a generic Unit Skill array.
`SkillCatalog.enrich_unit()` attaches the reviewed
`training:irregular` reference to matching Order occurrences.
The tracked Army database regression verifies that real Irregular
loadouts retain this association without asserting Unit/profile-wide
Training ownership. A Unit-level reverse link remains intentionally
absent until an option-scoped source/provenance requirement is established.
The existing generic relation graph is unchanged.

The separate typed model in
`src/infinity_db/restriction_conditions.py` compiles the reviewed
finite source chart into **14 negative constraints** with five
operation kinds: `state-entry`, `skill-declaration`,
`terrain-traversal`, `directional-skill-movement` and
`army-role-selection`. Each operation includes the reviewed target
record when available and only its valid qualifiers: ladders are
terrain traversal without a Skill target, Jump has `direction=upward`,
and Lieutenant is an Army `role=lieutenant` selection. Subjects have
source selectors or existing canonical owners; the three Troop Type
selectors have no canonical record IDs. The deterministic browser JSON
retains the previous fields and adds `subjectKind` and the typed
`operation` object for exact source semantics and future integration.
The legacy two-field `record_relations` graph cannot express these
conditions. The separate v9 `restriction_constraints` table and API
now carry all 14 source-scoped prohibitions without changing that graph.
A consumer audit confirmed that its seven absent conventional edges
are **six TAG/VH/REM source-only Troop Type restrictions** (no
canonical owner identity) and **one mounted Motorcycle ladder
traversal** (no Skill target). All seven are published in both the v9
API and normal browser reference; target-based contextual links
cover the canonical destination pages. The two broader legacy
edges retain source-qualified display labels. No unsupported
generic edge, Troop Type record or ladder Skill was added, and no
Unit/profile permissions are inferred.

### Restriction persistence and version-aware API (v9 locally promoted)

**Implemented; v9 database and paired publication promoted in the development checkout, not deployed.**
`src/infinity_db/restriction_storage.py` defines a separate `restriction_constraints` SQLite table without
rewriting `record_relations` or its API. The table retains source ID,
printed page, pinned PDF fingerprint, source-order position, source
subject and kind, nullable canonical owner/target IDs, negative
`polarity=prohibition`, action, operation kind, scope and JSON
qualifiers. Source-only TAG/VH/REM selectors have NULL owner IDs;
ladder traversal has no canonical target. The compiler validates all
14 facts against the maintained source before storage, and the table
rejects duplicate conditions and positive polarity. No Unit-level
eligibility or action-legality conclusion is produced.

The additive **`GET /api/restrictions`** contract returns
`formatVersion: 1`, `available`, `source` (ID, printed page,
PDF SHA-256), `polarity: prohibition`, ordered `items`, and
`evaluationSupported: false`. Each item contains `subject`,
`subjectKind`, nullable `ownerRecordId`, `action`,
`operation: {kind, qualifier}`, nullable `targetRecordId`,
`scope` and `polarity`. Optional `subject` and `record_id`
filters are conjunctive and reject invalid identifiers. On a
v8/compatibility-10 database, the endpoint returns
`available: false`, `source: null`, `items: []` rather than
fabricating a complete restriction set from generic relations.
On v9/compatibility-11, it reads only the materialized table, with
`available: true`. Zero matches never establishes legality.
The **current browser still consumes the static Restrictions
publication**; it does not require the new endpoint.

`RulesDatabase.validate()` now accepts only the exact schema /
compatibility pairs **(8, 10)** and **(9, 11)**. For v9, it
also verifies all fourteen source-ordered conditions, negative
polarity, qualifiers, source selectors and consistent provenance;
unsupported versions and mixed pairs fail closed. The **default**
`build-rules` path remains v8/compatibility-10, preserving normal
build outputs. Supplying the optional
`--restrictions-manifest config/validation/restrictions-source-chart.json`
produces deterministic v9/compatibility-11 data using the reviewed
curated records. For safety, this opt-in CLI path refuses the default
tracked `data/generated/rules.db` output: select a staging file.

The v9 build is byte-deterministic in tests, and read-only HTTP
checks confirm both v8-unavailable and v9-available responses,
filtering, backward-compatible Skills/Equipment responses, and
unchanged legacy relations. The application also accepts the original
v8 snapshot as a rollback source.

**Local release-pair promotion (2026-10-30):**

`tools.build_deployed_object_publication --stage-restrictions-v9`
generated both artifacts in a new ignored `local/` directory
after verifying the official PDF, curated review hashes, original
v8 release pair, complete 14-condition model, and unchanged
legacy relations. The staged **v9/compatibility-11** rules database
has SHA-256
`554bbefc90fa20d5181cd563979b581f5e42f3bfeca1bcbd30cfac1921de5498`.
Its matching deployed-object publication SHA-256 is
`1b2fc051f81eef42af104b52058d22c011d22b8819c67d4b6a9624b5662f82e2`.
All 17 reviewed objects, unresolved deliveries and review
fingerprints remained unchanged; only the rules database fingerprint
in the publication changed. The staged source report is
`local/restrictions-v9-n53-20261030-reviewed/staging-report.json`.

`--promote-restrictions-v9` applied the verified pair to the local
checkout with guarded replacements and post-promotion application
startup and provenance verification. The original paired v8
database/publication bytes are preserved under
`local/restrictions-v8-recovery-ut9_clv3/` on the development
machine. The **tracked rules database now uses v9**; the co-located
ignored publication has been rebuilt accordingly. The normal
`build-rules` command deliberately still creates standalone
v8-compatible databases, so reproducing the tracked v9 release
artifact requires the explicit reviewed manifest and coordinated
publication workflow. Do not overwrite either artifact individually.

**CI release-image acceptance passed on 2026-10-30** for commit
`b7230761`: Source checks, Installed wheel smoke and Deployment
smoke all succeeded with the promoted v9 rules database and its
generated deployed-object publication. That verifies the release image, **not** a hosted deployment.
The subsequent v8 overlay-image rollback and v9 forward-image CI
rehearsal passed at `663a345` (2026-10-30), using a freshly
rebuilt source-equivalent v8 pair. Rehearsal does not verify byte
identity with the retained original v8 backup or exercise live-host
rollback. The hosted operational test remains open.

**Legacy relationship consumer review:** the reviewed Motorcycle →
Jump and Irregular → Lieutenant graph edges are retained as
`restricts-use-of` for old API consumers, without adding or
removing any `record_relations` rows. Their shared player-facing
`display_relations[].presentation.label` strings are now
**source-scoped** in both directions: Motorcycle only prohibits
upward Jump while mounted (horizontal/downward Jump remain
unrestricted *by that rule*), and Irregular Training disqualifies
Lieutenant **selection** rather than all use of a Skill.
`src/infinity_db/rule_relations.py` owns the two exact
source-target presentation overrides; other uses of
`restricts-use-of` retain generic labels. Both v8 and v9
projection tests verify this backward-compatible structural
contract. The 14 typed source restrictions, not these generic
graph edges, remain the source of conditional semantics; the seven
source-only/unrepresentable generic edges are not manufactured.

**Reviewed PDF source pins (2026-10-30):** All 12 PDF source declarations
in the tracked v9 database now carry reviewed byte fingerprints for six
documents: English/Spanish N5.3 core, English/Spanish FAQ v0.1, historical
English FAQ v0.0 and English ITS Season 18. After the English core refresh,
a guarded paired refresh permitted only the nine remaining NULL-to-hash
cells. Every other stored row and the complete database schema, including
indexes, remained identical, as did typed Restrictions and reviewed objects.
Two independent exports were byte-identical. The rules SHA-256 is
`4a7da9a6237bca26ccfd453fc07d7e40b5e57a59b92da6b84de3ac4b9ab7b255`;
the matching ignored publication SHA-256 is
`b680f0bf1e55d119fc0590ea35a04fc917eafc22244715ef64a6bcc1e8b8131d`.
These current fingerprints include the subsequent Surprise Attack
occurrence-metadata refresh described above.
The original matched v9 pair is retained under ignored `local/`; the retained
local audit evidence records its recovery location. The publication changes only
its rules-database and curated-source fingerprints. This is local provenance
acceptance, separate from final release and hosted deployment gates.

The API, schema and rollback contract remains covered by
`tests/test_restriction_storage_candidate.py` with both
versions tested independently of the tracked database version.

## Availability and membership

InfinityDB distinguishes several relationships that source data often places near each other:

- **Army-list availability** — the Unit/profile/loadout occurs in a concrete Army list;
- **optional availability kind** — standard, mercenary, Spec-Ops, Team Operations, reinforcement,
  or other explicitly normalized availability path;
- **broader declared faction membership** — source-declared game-wide faction relationship that may
  exist even without a current selectable Army list;
- **main/grouping identity** — application grouping context;
- **display identity** — browser presentation context.

`army_units.availability_kind` is persisted application data. Runtime optional-unit filtering consumes
that classification rather than reconstructing it from source IDs.

Unit-list counts and roster membership operate on logical Units with concrete application Army
availability, so duplicate source representations do not inflate player-facing totals.

## Context-coherent filtering

Profile/loadout-sensitive filters must be satisfied in one compatible occurrence context.

- AVA belongs to an Army/profile occurrence.
- Points and SWC belong to loadout occurrences.
- Troop Type, Classification, Characteristics, profile Skills/Equipment and other profile facts stay
  with their owning profile/profile group.
- Loadout-local Weapons/Equipment/Skills stay with the loadout.
- Unit-option facts remain Unit-wide when the source does not attach them to a profile group.

When AVA/Points/SWC participates in a query, another selected profile/loadout criterion cannot be
satisfied by an unrelated option elsewhere on the same logical Unit. This prevents semantically
impossible cross-option matches.

Unit Explorer filter vocabulary may also apply a maintained application overlay without rewriting
the source facts. A combined source Classification can participate in more than one public
Classification filter, while source Characteristics that duplicate a canonical current Skill can be
omitted from the picker as redundant. The original category/characteristic rows remain preserved
and direct identifiers remain queryable for compatibility and provenance.

AVA preserves `Total` as a first-class display/exact-filter value. Negative ancillary/source AVA
sentinels are not ordinary player-facing AVA values. SWC preserves ordinary costs separately from
bonus/non-cost source forms such as `+1`, `+1.5`, or `-`; numeric ranges apply only where numeric
ordering is meaningful.

## Source-specific Unit information

Some source material is useful but cannot safely be promoted to game-wide Unit facts.

### Source notes

Non-empty source Unit notes are retained with source Unit identity, representative/source status,
and applicable Army contexts. The application may present those notes on the logical Unit while
keeping attribution visible.

### Composite Unit options

Top-level source options that combine multiple loadouts remain source-context bundles. InfinityDB
preserves their cost, miniature count, Order contribution, included loadouts, and source/Army
context. Source-local option IDs are not canonical cross-Army identities unless separately reviewed.

The paired raw database preserves normalized source fields that are not yet published
through these bundles (for example, direct Unit-option Skills/Equipment/Weapons,
and profile/group notes). The source-to-presentation audit keeps such fields
classified as potential presentation gaps even when empty in the selected source
snapshot, and separately reports **how many source values are actually populated**.
Newly populated fields must be reviewed before a data-completeness claim; absence
in one pinned snapshot does not justify permanently excluding their semantics.

### Source-field occupancy and publication limits

`tools/audit_source_presentation.py` assigns a presentation/scope policy to
every normalized source field, while its paired-raw-database inspection checks
whether potential gaps actually contain values. The 2026-10-15 pinned
Army-source assessment covered **70 source tables and 441 fields**. Of these,
**39 fields** were still classified as
`unrepresented_player_information`, but **none contained populated values**
in that source generation. The seven direct composite Unit-option
Skills/Equipment/Weapons/Characteristics relationship and extras tables had
no rows; neither the 4,748 source profile groups nor the 5,020 source
profiles supplied notes. These are **snapshot occupancy observations**, not
evidence that future source data will always be empty or that their meaning
can be dropped from the normalization model.

The current published application nevertheless has **18 composite
Unit-option occurrences** on seven distinct Unit identities, including
linked loadouts/Orders, and **30 source Unit-note occurrences** on 28
logical Units. These use *other* represented tables. Do not conflate
an empty direct Unit-option Skill/Equipment table with an absent
composite Unit option, or empty Profile notes with missing source Unit
notes. The separate source audit also records two explicit post-1.0
scope decisions: Spec-Ops/Team-Ops option charts belong to
list/session configuration; raw `loadout_options.disabled` and `minis`
flags have no established immutable player-reference interpretation.
Neither decision authorizes silently dropping those source fields.

Before 1.0 release acceptance, rerun the audit against the **release-matched
`infinity.db` and `infinity.raw.db` pair** using the opt-in
`--source-occupancy-gate` through the normal checks runner; see
[release validation](releasing.md#4-run-local-release-validation).
It fails if raw evidence is missing, the database pair is inconsistent,
or any unrepresented field becomes populated. The synthetic fixtures in
`tests/test_audit_source_presentation.py` intentionally populate some
potential gaps to verify detection; their occupied counts are **not**
current Army-source counts. Required clean CI omits the raw archive and
cannot alone certify this source-to-presentation completeness gate.

### Selection and dependency constraints

Reviewed source selectors and same-Unit profile/loadout dependencies are materialized only when their
meaning can be represented without inventing list legality. Opaque source selector parameters remain
provenance rather than being treated as a complete list-builder rules engine.

## Peripherals and Controllers

Peripheral source encodings are normalized through a separate reviewed identity contract because
Army represents the concept through multiple shapes.

Current application semantics distinguish:

- embedded Peripheral entities/profiles;
- standalone Unit-backed Peripherals that reuse logical Unit identity;
- source mappings from Army coordinates to those canonical targets; and
- Controller access pools, which represent eligibility/selection rather than fixed ownership.

Peripheral subtype classification may link to canonical reviewed rules identities. A mapping that
cannot be supported by the pinned source evidence remains review work rather than being inferred by
name.

Runtime Unit detail consumes the materialized application relationships and never opens the curated
Peripheral JSON directly.

## Fireteams

Fireteam charts are Army-local structured source data. InfinityDB materializes one canonical
application chart per supported Army/source context while preserving:

- chart/type limits, including the raw Army value for provenance while projecting explicit
  `maximum`, `unavailable`, or `unlimited` application semantics before browser use;
- member requirements;
- Wildcards and parenthetical source terms;
- source notes;
- resolved logical Unit targets;
- FTO-eligible loadout references; and
- source provenance.

Reinforcement parent limits remain separate through the application Army graph rather than being
silently merged into a child chart. General Fireteam rules/Level bonuses live in curated rules data
and are composed by the Fireteams application surface; they are not source Army chart rows.
Fireteam Level curated facts allow an optional `sourceNotes` list for
provenance and rules-publication conflicts. These notes are displayed as
secondary text without affecting Level requirements or bonuses.

The chart read model exposes `wildcards_excluded` for the reviewed complete
observations `No Wildcards` and `No Wildcards Special Fireteam` (ignoring case,
whitespace and a terminal full stop or exclamation mark). The backend decodes
these explicit exclusions from the preserved observation; it does not infer
restrictions from arbitrary prose. `false` means no recognized exclusion,
not approval of Wildcard eligibility. The browser omits combined Wildcard rows
from excluded teams and retains a separate Wildcard card when no team can
display the pool. The source-separated view preserves every original chart row.

Each member also exposes `reference_issues` with stable codes and player-readable
messages derived from the persisted resolution and Army-local FTO loadout links.
An unresolved or ambiguous Unit, a global-only match, and a missing Army-local
FTO option remain distinct. A global Unit link is reference navigation, not
proof of Army-local eligibility. These issues are visible in ordinary member
rows, including combined Wildcards, alongside the original `comment` as a chart
annotation. Technical resolution/ID columns remain developer-only. Original
annotations supplement the legacy `equivalence_labels` projection; they do not
create new aliases or automatically interpret additional conditions. That field
and its persisted table retain their names for compatibility, but contain ordered
parenthetical source terms, not independently verified equivalence rules. Normal
charts label them **Chart terms**, alongside the exact original **Chart note**.
Parentheses alone do not establish a counts-as rule, profile eligibility or Skill
entitlement. In the pinned Shindenbutai source, Shizoku's `(Strategic Deployment)`
note matches the option carrying Skill 251, distinct from its two FTO options.
The Varuna Div names match Army-local ORC/Machinist loadouts; Triad/Triada terms
retain their chart context, including Reinforcement-only source rows. These
descriptive correspondences do not add generic eligibility relations or a rules
engine. See [annotation validation](testing.md#fireteam-annotation-applicability).

`parent_charts` retains each Reinforcement Section's source-backed parent Army
reference, selected chart source and independent type-limit projection. A
`selectable` flag reuses the ordinary Fireteam Army picker eligibility; grouping
parents remain represented without a chart link. Normal Reinforcement pages show
these parent limits, including zero/unavailable values, separately from Section
members. An absent chart and an existing chart with no limits are distinct; neither
becomes a zero limit. Parent links use canonical public slugs and shared Fireteam
state. This is contextual reference information, not combined roster validation.

## Relationship model

Application relationships should be materialized where their semantics are understood and useful.
Source storage links that exist only to express normalization shape are not automatically player
relationships.

Important current relationship families include:

- logical Unit ↔ source occurrence;
- Army grouping/parentage and Unit availability/membership;
- Profile/Loadout/Unit-option include relationships;
- selection/dependency constraints;
- Peripheral/Controller relationships;
- Fireteam membership/equivalence/Wildcard context; and
- typed rules/reference relations.

Historical source endpoints that no longer resolve in the current Army snapshot are handled by a
separate snapshot-bound review contract. That evidence can classify a source relation as stale; it
must not create a false alias to a current Unit.

## Rules/reference model

Curated rules collections are versioned and built into `rules.db`. The rules layer is
semantic/reference data, not mutable game state. `data/curated/README.md` owns the current curated
format and validation contract.

A semantic record has a stable typed ID such as `skill:move`, `state:targeted`, or
`ammunition:shock`. Current composition is contribution-based:

- exactly one current `definition` contribution owns the canonical identity;
- optional supplements can add scoped reviewed facts/citations/relations;
- historical/superseded collections remain source evidence but are excluded from normal current
  composition; and
- applicability/review/source provenance remains explicit.

### Dated FAQ/errata layer (published reviewed subset)

FAQ rulings use independent `faq-ruling:*` semantic identities. The base
Rule/Skill/State definition is not rewritten when a later FAQ clarifies it.
The existing collection/definition boundary retains the source document's
identity, authority, effective date, citations and history; individual
rulings add a required validated `facts` contract (see
`data/curated/README.md`): question, answer, affected `topicIds`,
original publication identity/version/date/page, exact applicability by
rules revision plus effective date and optional ITS season revision/scenarios,
selected official citation with editorial selection reason, explicit
conflicting citations and predecessor `supersedes` IDs.

**Source precedence is applicability-first, not newest-first.** Core
definitions remain authoritative baseline material. Only a ruling explicitly
reviewed for the requested rules revision, effective date, and applicable
season/scenario may be considered as an additional clarification; newer
documents cannot retroactively or globally override unrelated source
contexts. Cross-posted/carried-forward answers preserve one identity and
original publication date, not duplicate FAQ entities. Disagreements are
separate evidence with a reviewed source choice and explanation. An explicit
supersession has effect only where applicability overlaps and the cited
predecessor has been verified; it must not delete historical evidence.

Currently `curated.py` validates this **authoring contract** for FAQ
definitions, and the rules exporter validates FAQ links across collections:
current canonical topic and scenario targets, retained historical FAQ
predecessor identities, consistent cross-posted original provenance,
acyclic supersession and overlapping revision/date/season/scenario scopes.
Supersession is explicit and limited to potentially overlapping contexts;
a later document date by itself still grants no precedence.

The **read-model and explicit-context API foundation** now selects only
reviewed, current FAQ identities matching topic ID, exact rules revision,
date, optional season ID/revision and optional scenario. It requires that
the chosen source, original publication and current collection already
exist on the requested date. An active scoped successor suppresses an
applicable predecessor only for the same topic; recency alone does not.
The result retains independently cited answer/provenance/conflict evidence
and matched applicability, separate from the unmodified base Rule/Skill.

`RulesDatabase.faq_rulings_for_topic` and `GET /api/faq-rulings` provide
that projection. The API requires `topic_id`, `rules_revision`, and
`as_of`, with optional paired `season_id`/`season_revision` and
`scenario_id`; it never defaults to the newest publication.

Twenty-nine reviewed FAQ entries are now published from
`data/curated/rules/n5-faq-v0.1.json`: nine first recorded in v0.1 and
twenty **carried forward from v0.0**. Each carried ruling retains original
English v0.0 source/version/page separately from the currently selected
English v0.1 page, and a corroborating Spanish v0.1 citation. The
v0.0 record date 2025-10-15 is the associated official update anchor;
the exact PDF publication day is not independently verified. All
currently selected rulings require explicit N5.3 applicability, and
the stable ruling ID is reused across the cited publications.
The shared browser presentation now covers affected Equipment,
Scenario, Skills, Traits, States, General Rules and Hacking Programs,
with Fireteam FAQs appearing on the Fireteams page rather than a
competing rule route. A single topic may have multiple applicable
clarifications, and the same ruling may be discoverable from
several referenced topics without cloning its identity.
The N5.3 Basic Rules `rule:deployment-phase` is now a canonical
General Rules identity, cited to N5.3 printed p. 15. The v0.0-origin
FAQ about repositioning before Roll/measurement is attached to that
general rule, not to a specific Deployment Skill, and remains a
separate dated explanatory overlay. Existing Skill/Army data are unchanged.

The Annihilation-only Ancillary ruling is a conservative InfinityDB
applicability selection, not a claim that the ITS-section FAQ explicitly
names Annihilation. N5.3 uses the same Killing clause for Annihilation
(p. 150) and Firefight (p. 155), but FAQ v0.1 (English/Spanish printed
p. 4) does not name either Core mission. Shared Killing wording and the
FAQ's generic scenario-objective language do not justify adding
Firefight to the selected scope. Widening requires scenario-specific
source support and a reviewed applicability change. The source label
`2026-09-01` is the project-documented announcement-era anchor, not
a separately established document publication date. The Fireteam Type ruling
uses the consistent English HARIS three-to-two-member example. The contradictory
Spanish v0.1 count is published as separate conflict evidence; an official
correction remains open.

**1.0 historical applicability decision (2026-10-29):** The 1.0 FAQ
read model remains a **current N5.3 reference**, not a historical
replay service. The 20 answers carried forward from v0.0 preserve
their earlier source identity but are selected from v0.1 and reviewed
only for N5.3 from the 2026-09-01 announcement-era reference anchor.
Nine answers first appear in v0.1. An older
`facts.originalPublication.publishedDate` is **not** an applicability
grant. The selector independently requires that the selected source
anchor, original source anchor, collection effective date and
ruling-specific applicability window all permit the requested date,
and that the rules revision, season and scenario match. A date supplied
to the explicit-context API is therefore a **filter over published,
reviewed current selections**, not a request to reconstruct the rules
and FAQ available at that historical instant.

Historical FAQ replay and user-selectable date/season controls in the
browser are **post-1.0**. They require separately authored and reviewed
v0.0 source selections and applicability for the actual historical N5
rules revision(s), compatible historical topic/Scenario identities,
source-specific effective-date evidence or clearly marked anchors,
and explicit version/season context for the reader. Historical
collections must remain independent of current canonical composition.
Do not backdate a v0.1 selected citation, copy N5.3 applicability
into N5.2, claim a source's PDF creation day is a publication day, or
derive historical supersession from recency. The same stable FAQ ID
may carry distinct reviewed historical contributions; duplicate
current definitions are not an acceptable replay mechanism.

This decision does not close the remaining 1.0 **current** FAQ
source/errata coverage, source-conflict disclosure or final
source-to-browser acceptance. Full ITS season-revision coverage and
historical mission libraries are outside the 1.0 completeness gate.
The separately published Season 18 Battleground pilot does not make
the remaining ITS catalog a requirement. The generic supplement
mechanism must not auto-attach a ruling to a core topic by name or
by a newer collection date.

### Domain ownership

The application-domain registry determines which semantic records receive player-facing routes.
Skills, Equipment, Weapons, Ammunition, Traits, States, Hacking Programs, Labels, and selected
General Rules are route-backed reference concepts. Attributes and scoped Game terms are embedded
vocabularies. Fireteam general rules remain owned by the Fireteams surface.

A semantic identity may exist without a dedicated detail route. Search/Glossary/presentation code
must preserve kind/domain and not merge same-name concepts from different namespaces.

Cross-domain discovery may additionally use reviewed `facts.relatedCategories` category slugs.
This adds navigation only: it does not change the record's canonical kind/domain, primary category,
or typed rules relationships.

For Traits, `config/catalogs/trait-wiki-references.json` maintains exact canonical
`trait:*` identities, names and reviewed official Wiki heading URLs. The Trait detail API
adds `wiki` only when both the ID and name match a published curated Trait; raw Army
Trait aliases and unreviewed source labels do not acquire inferred links.
Trait detail pages expose the reviewed `wiki` field through a player-visible
Official Infinity Wiki link, separate from the developer-only source metadata.
Other catalog pages retain their existing developer-only source presentation.
These links are navigation metadata and do not supersede pinned rules citations.

### Declaration categories and exact source variants

Declaration/action categories are composition metadata rather than standalone public rule records.
Skills, action-like Equipment, and Hacking Programs reuse canonical declaration identities while
preserving source spelling in source storage.

Exact source variants may belong to a family through typed `variant-of` semantics while retaining
their own source-specific facts. Family grouping must not imply that every Level/named variant has
identical rules. When the authoritative rule is naturally level-based, a family definition may also
carry reviewed `facts.levels` entries so the browser can present the level differences as one
comparison surface instead of duplicating near-identical rule cards.

### Typed relations

Rules relations are authored once in the semantic direction and validated against current semantic
IDs. Reverse navigation is derived for presentation. The relation vocabulary includes, among others,
state entry/cancellation, effect reuse/override/negation, modifier interactions, use restrictions,
enabling, triggers, Equipment grants, and Peripheral eligibility.

The edge states the relationship; exact numeric or conditional details remain in the owning rule
facts. Backend composition owns direction-aware labels/grouping for player presentation so browser
JavaScript does not maintain a second ontology.

### Maintained text

Maintained prose supports typed semantic reference tokens and typed distance values. Completed review
batches cover the supported namespaces and reject new plain semantic candidates. Ambiguous text uses
an explicit `review-needed` marker; confirmed ordinary-language collisions are stored as exact
passage fingerprints so changed wording reopens review.

The maintained policy is documented in `data/curated/README.md`.

## Scenario model (implemented core and future extensions)

### Current scenario foundation

All four N5.3 core scenarios use authoring definition v2. They compose explicit shared definitions
by typed identity inside the rules collection; display names never select or merge definitions.
`scenario_components.py` validates references, applicability, component kinds, override fields, and
cycles before the normal scenario/geometry validators check the resolved payload. Inline v1 payloads
remain readable for compatibility. Runtime export materializes the composed v1-shaped payload into
`rules.db`; runtime queries never need the authoring library or working-tree curation.

Rules and Skills are separate normal semantic records. Scenario Rules use `facts.category:
scenario-rule`, ordered `effects`/`restrictions`, and optional `definesSkills` references. Hack
Consoles and Pick Up Supply Boxes are scoped Skill definitions with the same `typeIds`, `labelIds`,
Requirements, Effects, Restrictions, and citation contract used by other Skills. Including the owning
Rule derives the scenario Skill list. `scope.scenarios` explicitly limits applicability; these
definitions have no Army links and are excluded from default core composition. Contextual composition
selects them with an explicit scenario slug or typed ID. Same-name functions may have distinct IDs;
no name-based deduplication or implicit season/revision fallback occurs.

The collection's versioned `scenarioComponents` library owns reusable typed `setup`, `geometry`,
`objective`, and `end-condition` payloads with citations and explicit scenario applicability. Setup
inclusions may override named game-size `swc`/`minimumVictoryPoints` fields by exact Army Points.
The common deployment rows, standard Annihilation/Firefight geometry, three-round ending, all-Null
ending, and minimum-VP ending are shared. Domination retains its explicit 350-point 6 SWC override.
Objective definitions use the same reference mechanism; geometry titles come from the including
scenario as presentation metadata. Unsupported fields and mismatched component kinds fail closed.
References are collection-local; cross-collection historical/season selection remains future work.

**Scenario marker sizes** are a derived, read-only setup projection:
`placement.marker_dimensions` enumerates only marker types actually present
in the selected configuration's validated geometry, with occurrence count,
physical diameter in **millimeters**, and a source citation. The existing
`marker_diameter_mm()` registry owns physical sizes; neither table
dimensions (inches/centimeters) nor apparent SVG scale change the footprint.
The pinned N5.3 Core PDF pp. 151 and 153 identifies the Console A and
Supply Box markers. The separately pinned official ITS Season 18 document
(version 2026.09.01, printed p. 17, token diameter chart) supplies their
numerical sizes: Console 40 mm, Supply Box 25 mm. This ITS citation supplies
physical marker metadata only, **not** ITS-specific scenario rules. Domination
has four Consoles and Supplies three Supply Boxes for every supported Army
Points setting; Annihilation and Firefight have no placed scenario-marker
instances. The map's SVG circles retain the same fixed-mm metadata, and
the player-facing setup note keeps that physical measurement distinct from
scoring-area geometry, map drawing scale, and configurable game distances.
Do not invent dimensions for unreviewed marker types.

**Domination Console placement** is another derived *map-only* projection.
The pinned N5.3 English scenario map (printed p. 152) locates each Console
at the center of its scoring Quadrant. The renderer recognizes only the
complete four-Quadrant/four-Console arrangement and verifies that all four
centers coincide before drawing placement rulers. It measures directly
from each Console **center** to its nearest horizontal and vertical table
edges, not from the marker circumference. For the 24 × 32, 32 × 48 and
48 × 48 inch tables, the corresponding nearest horizontal/vertical
edge distances are **6/12**, **8/18**, and **12/18** inches. Measurements
use the normal in/cm game-distance conversion, independently of physical
40 mm Console diameters. The existing four scoring rectangles remain
intact: they define gameplay scoring regions, not small placement zones.
The renderer omits only their redundant dimension annotations in this
recognized setup, retaining all semantic source geometry, marker centers,
zone boundaries, and deployment-depth measurements. No curated data or
generated-database contract changes are required.

The validated foundation accepts a Side with multiple Deployment Zone
element references and different objective `sideIds` (needed by
`Crossing Lines` and `Critical Intervention` respectively); both survive
normal catalog detail projection. This does **not** mean current geometry
v1 can render ITS-only radius/Safe Areas, or that the system models
Classified Objective choices, `Double Bind`'s selectable objective sets, or
multiple active season revisions. Those remain future opt-in features and
cannot be inferred from core scenario records.

Specialist Troops uses one **unscoped, InfinityDB-owned General Rules
presentation** of the shared Rule `rule:specialist-troops:standard`, published
at `/rules/specialist-troops-standard` and in global search/Glossary.
Its source citations remain the scenario sections in N5.3, not a claim that
the official core rules define a universal Specialist Troop attribute.
`facts.specialists.anyOfSkills` is the standard qualifier list as complete
Skill IDs. Scenarios explicitly include the same Rule and author only
`addSkills` and `removeSkills` differences; only the selected scenario
determines whether a Trooper qualifies. General Rules details derive
**Used by** links from actual scenario inclusions, rather than maintaining a
second relationship list. Resolution rejects unknown, duplicate, conflicting,
or non-baseline removals and produces an effective qualifier list without changing the baseline.
Doctor/Engineer Peripheral restrictions and the Chain of Command (Non Specialist) qualification
exception are maintained once. That exception affects qualification through Chain of Command,
without disqualifying a Trooper that has another qualifying Skill. This is a reference list and
exception statement; the catalog does not evaluate game state or assign permanent profile roles.

The Unit Explorer's optional `specialist` filter selects either `standard`
(the InfinityDB general reference) or a named core scenario with a reviewed
Specialist inclusion (`domination`, `supplies`, `firefight`). The API
resolves the effective qualifier list from `rules.db` (including any
scenario-specific add/remove overrides), then checks the current Army Skill
occurrences via the existing Skill catalog. Chain of Command occurrences
marked **Non Specialist** are excluded only as qualification through that
Skill; another qualifying Skill still counts. Filtering is at the logical
Unit level: a match means **at least one** profile, loadout, or Unit option
contains a qualifying Skill, not that every profile or Army list is a
Specialist, nor that currently selected Army contexts are all eligible.
This candidate-set filter intersects with other logical Unit filters,
respects existing availability flags, and does not persist new Unit facts.
Unsupported scenario names fail as invalid query selections; a missing
reviewed baseline or Skill identity fails closed instead of silently
inventing eligibility.

`RulesDatabase.scenario_reference()` reads the composed scenario, its included Rule records, and
its derived Skill records from `rules.db`. `ScenarioCatalog` builds the current player-facing backend
read models on that boundary: list entries retain maintained scenario-set order and publication/source
identity, while detail reads require one exact supported Army Points value. The selected detail projects
only that game-size row, its referenced geometry, applicable scoring awards and source issues, and the
composed scenario Rule/Skill records; it does not choose a default game size or evaluate match state.
Component IDs/citations are retained in `componentSources`.
Scoped Rule/Skill records include backend-resolved scenario names. The shared Skill-card renderer
presents their ordinary rule-detail fields and renders Specialist qualifier references as a list.
Normal browsing/search/glossary calls retain the default unscoped composition; scenario-only content
does not become universal core help. The Orders/AROs reference similarly
keeps its 57-row Core projection immutable: an optional current Core scenario
selection provides a separate `scenario` response member, derived from
`RulesDatabase.scenario_reference().skills` and exact `n5-core`
publication membership. Domination's Hack Consoles and Supplies' Pick Up
Supply Boxes are Short Skills only in those selected scenarios, with
references back to their actual rendered scenario Skill cards. The main
projection does not inherit scenario-only or season-specific actions. `/api/scenarios` exposes the current collection without choosing
a game size. `/api/scenarios/<slug>` requires one explicit `army_points` query value, rejects
unsupported values instead of substituting another configuration, and projects maintained-text
tokens/public references in the selected scenario context. `/scenarios` and `/scenarios/<slug>`
publish the list and selected detail with deterministic maps; browser Army Points selection defaults
to 300 and uses the common versioned share-state contract. The API remains configuration-explicit.

The resolved mission owns ordered sides, all six Army Points/SWC rows, deployment references into
its geometry, objectives/awards, Rule inclusions, Skills, end conditions, and source issues. Every
geometry-supported Army Points value has exactly one game-size row, and every objective covers
those values. Deployment regions resolve in the selected geometry with multiple regions per side
supported; objective side applicability remains explicit.

Scoring awards may use inclusive integer `numeric-range` conditions (an unbounded upper limit is represented
by `maximum: null`) or `reviewed-prose` conditions with semantic maintained-text tokens. The initial
numeric metrics are killed enemy Army Points and surviving Victory Points. Each objective declares
its scoring timing, `exclusive` or `cumulative` aggregation, and Objective Point cap. This records
reference semantics without evaluating match state. Exclusive numeric ranges must not overlap unless
a `needs-verification` source issue names that objective and Army Points row. A `needs-verification`
issue preserves unresolved uncertainty; it does not select a winning band or authorize a rules
correction. A `reviewed-resolution` source note instead records an explicit maintained interpretation
of a known source discrepancy and cannot excuse overlapping ranges.

The Annihilation 350-point surviving-Victory-Points column on page 149 prints inconsistent boundaries:
85–150 awards 1 Objective Point, 176–270 awards 3, and more than 250 awards 4. InfinityDB treats the
two boundaries as typographical errors because the surrounding game-size progression and corresponding
enemy-kills column both use contiguous bands. The maintained reviewed ranges are therefore 85–175,
176–270, and more than 270, with a `reviewed-resolution` source note preserving the printed discrepancy
and the reason for the correction. Its end conditions distinguish the third-Game-Round limit from the Tactical Phase all-Null check,
which finishes at the end of that Player Turn. Printed pages 149–150 cite the full pilot.

Domination adds geometry-referenced scoring conditions: `dominated-region-comparison` compares
each player's dominated-region count with the opponent (`equal` or `greater`), with an optional
minimum own count; `element-status-count` awards the declared points per matching marker element.
The current marker-status vocabulary is `hacked` or `controlled`. Referenced regions/markers must exist with the right
geometry kind in every Army Points configuration covered by the award. These conditions record
the reference rule; they do not evaluate ownership, control, or live game state.

An end-of-round objective may declare `maximumPointsPerRound` separately from its whole-mission
`maximumPoints` cap. Domination awards 1 point for a tie with at least one dominated Quadrant, or 2
for more Quadrants, capped at 2 per round and 6 over three rounds. It separately awards 1 point per
Hacked Console held at game end, capped at 4. All six game-size rows own literal
`minimumVictoryPoints` values (38, 50, 63, 75, 88, 100). The `minimum-victory-points` end condition
requires every row to have that field and distinguishes a Tactical Phase check from completion
at the end of that Player Turn. Its reviewed text preserves the strict below-threshold trigger
and non-Null Trooper basis.

Supplies adds `element-status-comparison`: `greater` compares the player's matching-marker count
with the opponent, while `all` requires every referenced marker to match for that player. Its
three end-of-game objectives remain additive: 2 points per controlled Supply Box (cap 6), 2 for
more than the opponent, and 2 extra for all boxes. Each condition references the same three
maintained Supply Box marker IDs. Carrying is insufficient on its own: control requires a Model
carrier that is non-Null and not in Silhouette contact with an enemy Model. Pickup alternatives,
one-box carrying capacity, Model-only carrying, persistent tokens, and deployment restrictions
remain cited ordered rules; live carriers and control are not stored or evaluated. Supplies
reuses the literal minimum-VP rows and typed end-condition contract, with 7 SWC at 350 points.

Firefight adds `metric-comparison` conditions, currently supporting strict `greater` comparisons
with the opponent for surviving Specialist Troops, killed enemy Specialist Troops, killed enemy
Lieutenants, and killed enemy Army Points. Its four end-of-game awards are 2, 1, 3, and 4 points
respectively; tied metrics do not satisfy a strict-greater condition. Metrics do not imply a
match-state evaluator or derive Specialist eligibility from static Unit/Profile flags.

Its Reinforced Tactical Link, Designated Landing Area, Specialist eligibility, and Killing
procedures remain ordered, semantically linked mission rules. Lieutenant identity is Open
Information; the first-round table requirement and Tactical Phase replacement procedure are
mission-local overlays. The Combat Jump +3 PH modifier and Airborne Deployment permission remain
mission-local too; neither canonical Skill definition is rewritten. Firefight retains the three-
round limit and all-Null ending, with no minimum-VP field on its game-size rows. Printed pages
155–156 cite the mission reference and maps.

Source notes/issues target exactly one `objectiveId`, `gameSizeField` (`swc` or
`minimumVictoryPoints`), or non-empty `geometryElementIds` list and name their applicable Army
Points. Geometry references must resolve in every applicable configuration. `needs-verification`
marks unresolved source uncertainty; `reviewed-resolution` records a maintained interpretation after
review. Only an objective-scoped `needs-verification` issue may acknowledge an otherwise-invalid
overlap, while game-size, geometry, and reviewed-resolution notes cannot excuse one. Domination
preserves the English N5.3 value of 6 SWC at 350 points from printed page 151,
with a game-size `needs-verification` note because Spanish N5.3 printed page 155
instead has 7 CAP/SWC for that same Domination row. This is an unresolved
official cross-language conflict, not merely a possible progression exception.
The ordinary 350-point Domination setup visibly flags the SWC cell as
source-disputed, with a keyboard-accessible in-page link to the full
`needs-verification` note under Source notes. This warning is sourced
from the existing game-size issue and is absent for other point values
and other scenarios. The issue stays unresolved pending a future official
clarification; neither edition is silently treated as an erratum.
Printed English pages 151–152 cite the mission rules.

Supplies uses the written placement consistently at every game size: printed page 153 places the
outer boxes `8 inches` from the table edges. Re-review of the 300–400-point illustration on page 154
shows that its `12 inches` mark belongs to a guide ruler; the Supply Box marker itself is visibly
closer to the edge and is consistent with the written 8-inch position. The maintained geometry
therefore keeps the outer markers 8 inches from their respective edges without a source issue.

Console setup, Hack Consoles, Specialist eligibility and the Peripheral restriction, base overlap,
and the Shasvastii exception remain ordered, semantically linked mission rules. Scenario Skills and the shared Specialist Rule now have distinct scoped identities; these rules
do not grant permanent
Unit/Profile capabilities.

Nested mission prose participates in the same syntax, target-resolution, and reviewed-link audits
as other maintained rules text. The existing rules record payload remains the canonical composed
scenario structure, while rules schema/compatibility **8/10** adds relational scenario publication
indexes. `scenario_collections` owns stable set identity, `scenario_collection_revisions` maps an
exact set revision to its source collection, `scenario_publications` stores deterministic composed
content identity, and `scenario_memberships` preserves ordered membership separately from scenario
identity. Source/citation provenance continues to use the existing collection/source/citation tables.
Rebuild `rules.db` after curation changes using the existing rules-build workflow.

`RulesDatabase.resolve_scenario_publication()` is the central selection boundary. A scenario may be
resolved by stable collection ID plus exact collection revision; omitting a revision considers only
publications backed by `current` source collections. Historical revisions require an explicit
collection/revision pair. Unknown selections return no match, malformed or ambiguous selections fail
explicitly, and no other season/revision is substituted. The player-facing `/scenarios` catalog and
detail pages consume `ScenarioCatalog` through the JSON API, require an explicit Army Points selection,
and render the selected maintained geometry through the deterministic SVG endpoint.

**Explicit published-set selection:** `ScenarioCatalog.list_scenarios(collection=...,
revision=...)` and `get_scenario(..., collection=..., revision=...)` filter current
composed scenario publications by the exact stable scenario-set ID and revision. The public
`GET /api/scenarios`, `GET /api/scenarios/:slug?army_points=...`, and
`GET /api/scenarios/:slug/map.svg?army_points=...` endpoints accept the same optional
`collection` and `revision` parameters **only as a pair**. Unknown pairs give an
empty list or HTTP 404 for detail/map; malformed/partial/repeated selectors give HTTP
400. Omitted selectors keep the legacy current-catalog behavior. This prevents an
explicit ITS season request from silently returning N5 Core information. The API
currently exposes only modeled **current** publications; the existing
`RulesDatabase.resolve_scenario_publication` historical membership lookup is not
yet a historical compositional detail/map API.

**Current publication boundary:** There are two current curated Scenario
collections: `n5-core@5.3` (four Core missions) and
`its-18@2026.09.01` (one reviewed ITS Season 18: Overheat mission,
**Battleground**). The ITS mission is published through the same
collection-aware catalog/detail and SVG map projection, using six supported
Army Points sizes (150/200/250/300/350/400), a three-Sector end-of-game
geometry/scoring model, and the English ITS source's printed pp. 121–123.
`GET /api/scenarios?collection=its-18&revision=2026.09.01` returns
Battleground; the default unqualified catalog remains the four N5 Core
missions. Unknown exact collection/revision pairs remain empty or not found,
rather than silently returning Core content.

Other Season 18 missions, including Crossing Lines, Akial Interference
and Area of Interest, are **not** published as selectable/renderable scenario
definitions. This bounded ITS publication does not imply a complete
Season 18 library, historical-season UI, Classified Deck, or general
tournament tooling, and does not expand the mandatory 1.0 scope beyond
the four Core missions. Browser selection state uses the common versioned
share-state token; legacy explicit `army_points` input remains readable.
Broader geometry/element vocabularies, source discrepancies and remaining
in-scope Core acceptance stay under the
[1.0 backlog](TODO.md#rules-and-reference-completeness).

The implemented geometry v1 foundation is deliberately small and strict. A standalone document uses
`InfinityDB scenario geometry` format version 1, canonical inch table dimensions, ordered unique
element IDs, and `rectangle`, `line`, `marker`, or `label` elements. Coordinates may be absolute
inches or table-relative edge/center anchors with offsets. Element `style` and marker `markerType`
values are stable kebab-case semantic identities, not a closed list owned by the v1 SVG renderer.
An optional ordered `annotations` layer
references those semantic elements rather than restating their geometry. Geometry v1 currently supports
derived rectangle `dimension` annotations and `area-size` annotations; both calculate their displayed
measurement from the referenced rectangle, so a map cannot silently disagree with maintained zone
dimensions. Rendered measurement text carries the canonical inch value in
`data-distance-inches` or `data-distance-size-inches`, separate from the user-facing display unit.
The map API accepts optional `distance_unit=in|cm`, using the Infinity distance convention
of 1 inch = 2.5 cm. The browser updates inlined annotations when the existing unit preference
changes, without altering the inch viewBox or stored geometry. Marker `data-diameter-mm`
remains unconverted physical metadata.
It also supports `element-edge-distance` annotations for markers and rectangles: the
displayed distance is derived from the target element's nearest physical boundary and selected table edge,
while an optional signed offset controls only where the dimension line is drawn. Scenario source language
such as “X inches from” is interpreted edge-to-edge unless the source explicitly names a center/reference
point. `marker` stores a semantic center point with a stable `markerType`; per-instance radius is not
duplicated in geometry because known marker types resolve to canonical marker metadata. That footprint is
used when deriving marker clearances. Physical diameter is semantic when it defines the represented game object,
not merely SVG styling. N5.3 Domination requires each Console to be represented by a Console A Marker
or scenery of the same diameter, indirectly making that canonical footprint part of the scenario rules.
The ITS token-diameter table provides the explicit numeric dimensions used by the core fixtures:
**Console 40 mm** and **Supply Box 25 mm**. Validation rejects unsupported fields, invalid anchors,
duplicate IDs, non-finite values, unsupported element kinds, and geometry that resolves outside the
table. Geometry itself does not require symmetric regions or one Deployment Zone per side. The SVG
renderer owns its narrower presentation capability: it maps the current semantic style identities to
CSS, requires canonical physical metadata for markers it renders, and raises an explicit render error
for a valid future style or marker it cannot faithfully project instead of substituting a generic
appearance or size. It uses the inch dimensions directly as its `viewBox`; it does not infer rules or
geometry from diagrams.

Domination exercises the rectangle annotation boundary: its Deployment Zones have derived depth
dimensions and its four Quadrants have derived width × height labels. Supplies exercises the point
boundary: the outer Supply Boxes are maintained at their semantic coordinates while the SVG derives
their `8″` distance to the left/right table edges. These annotations are map presentation metadata
referencing semantic geometry, not a second copy of scenario measurements.

The initial core-map acceptance corpus covered Annihilation, Domination, Supplies, and Firefight at
each distinct N5.3 table/deployment configuration (24×32 with 8-inch Deployment Zones, 32×48 with
12-inch Deployment Zones, and 48×48 with 12-inch Deployment Zones). It confirmed that v1 needs only
rectangular regions, dividing lines, semantic point markers, labels, and table-relative anchors for
the core maps. All four scenarios now own those configurations in maintained curated definitions,
and renderer acceptance tests consume that maintained geometry directly instead of keeping a second
fixture-only map corpus.

### Scenario publication model and remaining design direction

Scenarios are curated rules/reference data published through the rules pipeline. Their
maintained representation is validated structured JSON; their runtime representation is a deliberate
hybrid in `rules.db`. High-stability/queryable facts are relational, while nested ordered structures
whose shape legitimately varies by scenario remain validated typed payloads. Runtime code must never
parse PDF prose, image geometry, or display HTML to recover scenario semantics.

Current publication separates Scenario identity, publication/revision and collection
membership. The vocabulary below describes those implemented boundaries and the
accepted direction for broader applicability/configuration; optional Reinforcements
and collection-feature fields still require implementation before use:

- **Scenario identity:** stable InfinityDB slug/name for the conceptual mission. Reuse across seasons
  does not duplicate the identity.
- **Publication/revision:** authoritative source collection, source version/revision, language,
  reviewed citation, publication date when known, and deterministic content identity. A hotfix or
  revised mission document creates a new publication revision, not a new scenario identity.
- **Collection membership:** membership in a source set such as core N5.3 or an ITS season, including
  collection-local category/ordering and applicability. Membership may change between revisions of a
  season.
- **Scenario applicability/configuration:** supported Army Points/SWC, table dimensions, round count,
  minimum-VP/end thresholds, side configuration, and feature flags such as Reinforcements or
  collection-specific options. These values can vary by game-size row without changing identity.

Published scenario revisions compose typed components. The following accepted
design vocabulary includes implemented setup, geometry, objectives, Rules/Skills
and endings alongside **future extensions** for unsupported radius/circle geometry,
Classified Objective choices and collection-specific options. The current supported
subset is described above; this list does not claim those extensions are implemented:

- **Sides and roles:** symmetric Side A/B by default, with named asymmetric roles and role-assignment
  procedure when required. Objectives/rules may be scoped to a side or role.
- **Geometry:** a table-local coordinate system plus typed points, lines, rectangles/strips, circles
  or radius regions, quadrants/sectors, and derived/side-relative regions. Dimensions, anchors,
  transforms, exclusion areas, and placement constraints remain numeric semantic data rather than
  pixels from a source diagram.
- **Elements and tokens:** objective/scenery element types and instances with placement, ownership or
  alignment, interaction/lifecycle capabilities, and representation metadata. Carrying, destruction,
  activation, control, and state-like markers are modeled only where the scenario definition needs
  them; live ownership/carrier/state during a match is not persisted by the scenario catalog.
- **Objectives and scoring:** ordered objective groups with side/applicability, timing such as
  immediate/end-of-round/end-of-game, Objective Points, caps, and typed condition/comparison forms.
  Game-size-dependent thresholds are data. Unusual resolution procedure may retain reviewed prose in
  addition to typed facts rather than forcing a universal executable scoring language.
- **Classified Objectives and reusable features:** optional configuration for counts, Common/Private
  use, points, exclusions, substitutions/alternate use, and scenario-specific interactions. HVTs,
  Specialists, carried objectives, control areas, selectable objective sets, and season extras follow
  the same optional-feature principle.
- **Scenario actions and rules:** local Skills/AROs/interactions, requirements, effects, roll/MOD
  metadata, timing hooks, and rule overrides where structurally useful. Existing Skills, Equipment,
  States, Traits, Labels, General Rules, and other canonical entities are referenced by typed ID
  rather than copied into scenario-local identities.
- **End conditions:** round/time limits, Retreat-related behavior, all-Null/minimum-VP conditions, and
  explicit scenario overrides. Definition data records the condition; match-state evaluation remains
  outside the 1.0 catalog/reference responsibility.

Publication materializes relational indexes/foreign keys for identity, provenance, collection
membership, slugs and canonical entity references. Add further indexes only for concrete
cross-scenario query needs. The validated
component payload remains the canonical ordered scenario structure consumed by the backend. Browser
code receives composed presentation data and must not reinterpret score conditions, geometry, or
source-specific feature semantics.

The geometry component is also the sole semantic input for scenario-map generation. The 1.0 renderer
and geometry-schema v1 only need to cover the four N5.3 core scenarios: Annihilation, Domination,
Supplies, and Firefight. A renderer may project that geometry to SVG/other presentation formats, but
map-specific coordinates must not become an independent maintained source.

That v1 compatibility boundary must not be mistaken for a core-only architecture. The reviewed ITS
variation remains design evidence: geometry identities and primitives must not assume symmetric
roles, one Deployment Zone per side, rectangular-only regions, fixed marker vocabularies, or one
collection's styling. ITS-only constructs may remain unsupported by schema v1 and should fail
explicitly rather than be approximated; later versioned extensions should add those capabilities
without redefining the core semantic concepts. Likewise, future ITS support extends
publication/collection and optional-feature data rather than creating an ITS-only scenario schema.

### Post-1.0 player-authored scenarios (design direction)

A scenario creator/editor should support **new blank scenarios** and **derivatives of
published scenarios** using the same validated, typed scenario components and
geometry/map projection as the curated catalog. Authors may select preset
Deployment Zone/table maps; assemble preset rule groups or individual Rules/Skills;
add or modify scenario elements, sides/roles, setup, objectives, scoring methods,
end conditions, and custom additions; or author their own components. Presets are
starting points, not frozen inherited behavior. A customized official scenario is
an explicitly labeled *player variant*, never a new official source revision.

The proposed portable scenario definition has explicit identity boundaries:

- A versioned, canonical serialization envelope, including required InfinityDB
  schema/codec version and reference-data or ruleset revision for reproducible
  interpretation. It contains the actual authored changes/content, not only a hash.
- Stable references to official scenario/rule/skill/element identities plus
  deterministic local overrides/additions. Missing or superseded referenced
  content must be surfaced, not rebound silently by title or current-version guess.
- Authored entities carry a local, scenario-scoped namespace; display text does
  not confer official provenance, canonical rule identity, or execution semantics.
- Composition records ordered components where order matters and uses canonical
  ordering for sets/other unordered fields. Avoid redundant copies of reference
  records when a stable reference and revision suffice.

**Custom typed rules are the difficult boundary.** Provide a small, explicitly
versioned and validated vocabulary for fields InfinityDB can honestly represent:
applicability/side, action or trigger, timing, target, scope, quantities/units,
conditions/comparisons, modifiers, scoring, and referenced States/Skills/Rules.
Typed components and custom scenario Skills may reuse existing schema concepts,
but a locally invented rule is not an official Skill or an executable program.
Author-defined prose remains first-class for rules outside the supported typed
vocabulary, marked **descriptive/not machine-evaluated** rather than mis-parsed
or falsely validated. No arbitrary code/evaluation, external URL execution, or
silent conversion of unsupported user clauses into executable behavior. Explicit
schema extensions and migration are needed before claiming support for novel
mechanics. The editor may check structural validity without adjudicating a game.

The authored definition should live in transient browser state and travel via a
self-contained share URL or user-initiated export/import file; no server storage,
user uploads, or automatically persisted authored scenarios. Reconstructing from
URL data and the packaged reference revision must work offline. See the
stateless-sharing decision in `docs/architecture.md`; this is a post-1.0 goal,
not an extension of the 1.0 publication or database completeness gate.

## SQLite storage contract

Army export first loads normalized source data into validated relational staging, then writes two
permanent siblings:

### `infinity.db`

The self-contained application/runtime database. It contains the source/context rows still needed by
application behavior plus materialized canonical tables, mappings, provenance, and indexes. Source-
only normalized tables are physically absent.

Normal repository/API/web serving opens only this Army database plus `rules.db`.

### `infinity.raw.db`

The development/audit sibling. It contains all normalized source tables as queryable relational
structures plus exact normalized row JSON so absent-vs-null and source-only data remain recoverable.
It is not deployed.

### Shared metadata and integrity

Both Army siblings retain the generated metadata needed to bind them to the source/configuration
that produced them. Important metadata includes source snapshot identity, validated identity-policy
hashes, publication/raw table boundaries, deterministic application-content identity, and the
shared `export_pair_sha256` fingerprint for the complete application/raw export generation. The
pair fingerprint includes source-only normalized rows, so a partially published raw archive cannot
silently masquerade as the companion of an older application database.

When the Army database is built from a ZIP snapshot, `snapshotArchiveSha256` records that exact
archive identity. Deployment compares it with the Army source identity in the tracked symbol
publication manifest so Army data and graphical publication cannot silently come from different
snapshots.

`PRAGMA application_id`, `PRAGMA user_version`, and the InfinityDB compatibility revision are
validated before normal reads. Export validates integrity, writes planner statistics, and performs
canonical physical finalization for deterministic release bytes. Semantic tests may explicitly skip
only the physical finalization step; they do not bypass schema/input/integrity validation.

Builds publish generated database destinations only after temporary artifacts validate. The raw
archive is replaced first and the application database last, making the application replacement the
publication commit point. The exact interruption/recovery lifecycle is owned by `data/README.md`.

Each new Army staging, raw-archive, application, and rules database creates its schema and inserts
rows within one explicit write transaction, after deterministic connection configuration. This
avoids a separate disk commit per schema statement while retaining integrity checks and canonical
finalization. A SQLite connection context manager does not itself begin a transaction for schema
DDL; the rules schema script starts its transaction internally because `executescript` commits any
previously pending transaction.

## Snapshot provenance

Army, wiki, and symbol acquisition uses generated snapshot provenance records described in
`data/README.md`.

The current provenance model distinguishes:

- logical snapshot content SHA-256 (normalized member paths + member bytes);
- exact archive SHA-256;
- acquisition timestamp;
- source URL/language/document count where applicable; and
- for Army snapshots, the latest source-data date encoded by supported Army source version strings.

`data/README.md` owns the current provenance-format version and compatibility rules.

Acquisition time answers when InfinityDB downloaded the snapshot. `source.dataChangedOn` answers when
the contained Army source data most recently reports changing. Those dates must not be substituted
for each other.

Human snapshot notes are separate curated annotations bound to immutable source identity. Acquisition
tools never rewrite them.

## Army source revision interpretation

Corvus Belli Army document `version` values are source revisions, not InfinityDB snapshot versions.
InfinityDB may derive a latest encoded source date only from version shapes it explicitly recognizes;
unsupported values must remain visible rather than guessed. A snapshot can be acquired long after
its newest source revision, so the provenance model stores both concepts.

The browser's normal freshness wording uses the source-data change date when available. Exact
acquisition/archive identity remains Developer/provenance information.

## Required Army metadata

Army database builds require the supplementary Army `metadata.json`. It is preserved through the
merge/normalized pipeline and exported to metadata tables.

Metadata provides, among other things, faction/grouping relationships and weapon/profile reference
information. Army list files remain authoritative for concrete Unit membership/availability; a
metadata identity does not create an Army roster by itself.

Current build validation rejects normalized Army data without valid required metadata.

## Application query model

Runtime repositories query canonical/materialized application structures and compose contextual
source detail as needed. They must not infer semantics from raw IDs or reach into `infinity.raw.db`.

Examples:

- Unit lists operate on logical Unit identity and materialized Army availability.
- Unit detail returns one logical Unit with source/Army/profile/loadout context preserved.
- catalog filters resolve canonical application identity and match all materialized source members.
- rules-backed States and other rules-only concepts are read from `rules.db`; their presence does
  not imply mutable in-game state in `infinity.db`.
- search and Glossary project canonical domain identities rather than creating another identity
  namespace.

The HTTP/browser layer may change presentation without changing these semantic ownership rules.

## Audit and validation tools

Current semantic contracts are executable through focused audit tools rather than copied as
historical inventories into this document. Important examples include:

- `tools/audit_database_separation.py` — application/raw table boundary;
- `tools/audit_runtime_database_surface.py` — runtime repository access boundary;
- `tools/audit_unit_semantics.py` — logical Unit/source semantics;
- `tools/audit_profile_semantics.py` and `tools/audit_loadout_semantics.py` — profile/loadout payload
  boundaries;
- `tools/audit_army_faction_semantics.py` — Army/grouping/faction semantics;
- `tools/audit_peripheral_semantics.py` — Peripheral mappings/access pools;
- `tools/audit_relationship_semantics.py` — source/application relationship interpretation;
- `tools/audit_fireteam_semantics.py` — Fireteam chart semantics;
- `tools/audit_source_presentation.py` — source-to-player-presentation coverage;
- `tools/audit_semantic_deduplication.py` — canonicalization evidence;
- `tools/audit_enrichment_coverage.py` and `tools/audit_rules_interactions.py` — rules/reference
  coverage and interaction review; and
- `tools/audit_maintained_text_links.py` — maintained-prose semantic-link completeness.

Generated reports and one-off audit measurements belong under ignored report/audit workspaces. Only
durable semantic conclusions belong in this document.
