# Architecture

## Project goals

1. **Database backend:** maintain validated, queryable Infinity data, including
   army-specific variants and the source metadata needed to trace it.
2. **Extensible web UI:** provide a unit explorer and rules-reference catalogs
   through focused API endpoints and views.

## Guiding principles

1. **Accuracy:** use official data sources and strive to represent those
   sources as accurately as possible. When source data is incomplete or
   ambiguous, preserve that uncertainty rather than presenting an unsupported
   conclusion as fact.
2. **Flexibility:** expand the ways users can browse and understand the data
   while keeping the experience simple, fast, and customizable.
3. **Transparency:** keep the project open source under the MIT License and
   clearly distinguish InfinityDB's work from outside data, quoted text, and
   image assets, which remain the property of their respective owners.
4. **Privacy:** collect only the aggregate operational information needed to run
   and improve the service. Do not identify, profile, or persistently track
   visitors.

## Engineering principles

1. **Preserve the source.** Raw upstream data and assets are immutable inputs;
   transformations happen in separate stages.
2. **Never lose information silently.** Merging, normalization, deduplication,
   filtering, and cleanup must preserve provenance and report anything
   discarded, unresolved, or ambiguous.
3. **Code defines behavior; configuration defines maintained knowledge.**
   Domain-specific aliases, mappings, filters, overrides, exceptions, and other
   independently maintained project knowledge should live in validated
   configuration when they can change independently of implementation behavior.
   Generated manifests record provenance/build state rather than maintained
   policy.
4. **One source of truth per build.** Every stage of a build must use the same
   pinned inputs and explicit configuration so the result is reproducible.
5. **Prefer explicit relationships over assumptions.** Model what the source
   actually represents, including many-to-many and source-specific
   relationships, rather than flattening data for implementation convenience.
6. **Make semantic provenance explicit.** Distinguish source-native concepts from
   source-derived facts, InfinityDB-specific abstractions, and presentation-only
   conveniences. When InfinityDB introduces a concept that does not exist in the
   source, document its evidence, derivation, assumptions, and intended scope.
7. **Rules are semantic evidence, not the application schema.** Use the official
   rules to understand, classify, relate, validate, and explain Infinity data,
   but model rules concepts only where they serve InfinityDB's catalog,
   relationship, query, or presentation responsibilities. InfinityDB is not a
   rules engine or an exhaustive replacement for the official rules; procedural
   rules and edge cases may remain cited context without becoming application
   entities or runtime logic.
8. **Build conservatively.** When validation or interpretation is uncertain,
   preserve source or existing valid data rather than guessing or
   destructively correcting it.
9. **Separate stages and responsibilities.** Use the canonical project-domain
   boundaries in `docs/project-domains.md`; acquisition, data processing,
   deployment, web-backend, web-frontend, and project-infrastructure concerns
   should remain independently understandable and testable.
10. **Be deterministic and portable.** Given the same inputs, configuration,
   InfinityDB revision, and declared tool versions, persistent generated artifacts
   must be byte-identical on Windows, Linux, and macOS. Canonical text output uses
   UTF-8 with LF line endings; archive member ordering/metadata and database/export
   ordering must likewise be explicit rather than inherited from the host platform.

These principles are the canonical engineering decision criteria for the
project. `AGENTS.md` contains immediate operational instructions, while
`docs/AI_CONTEXT.md` records durable invariants and non-obvious decisions.

Cross-platform determinism is enforced as an artifact contract, not only as logical
equality. Git attributes protect checksum-bound release files from checkout
rewrites, but generators themselves remain responsible for canonical bytes. Required
CI builds representative Army/rules databases, JSON reports, snapshot/work archives,
and publication metadata on all three supported operating systems and compares their
SHA-256 identities. The cross-platform comparison pins the same exact CPython patch
version on every runner; floating minor-version selectors are not a valid determinism
test because they can resolve to different Python/SQLite toolchains by platform.
Repository-managed text is checked out with LF line endings on every supported platform
so the compared fixtures are byte-identical inputs. Generated SQLite artifacts likewise use
explicit page/file settings, are repacked with `VACUUM`, and normalize SQLite's
transaction-history-only file-change/version-valid-for header counters after the database is
closed. The normalized counters remain equal so SQLite can still trust the in-header database
size; schema/user/application version fields and database contents are not rewritten. Army and
rules exporters keep this canonical finalization enabled by default, including every CLI/release
build. Programmatic callers may explicitly disable only the physical finalization step when a
semantic test needs valid database contents but not byte-level artifact identity.

### Design direction: privacy-preserving observability

Production observability should be aggregate-first and must not require personal or
visitor-identifying data. InfinityDB may collect bounded operational metrics such as
normalized-route request counts, status classes, latency distributions, response sizes,
active-request counts, application/database versions, and host/container resource use.
Routes must be normalized before aggregation (for example `/units/:id`), query strings
must not become metric labels, and all label vocabularies must remain bounded.

Routine monitoring must not collect or retain IP addresses or derived geolocation, user
agents or browser fingerprints, referrers, cookies, session or preference values, query
strings or search terms, persistent visitor identifiers, or other data intended to
correlate requests from the same person over time. InfinityDB therefore deliberately
forgoes unique-visitor counts, returning-user analytics, geographic/demographic reports,
and per-user navigation histories.

Raw request logging is not the normal analytics path. If temporarily enabled to diagnose
a concrete production incident, it must be minimized to the fields needed for that
incident, sanitized where practical, access-restricted, and retained only briefly.
Operational dashboards should derive from aggregate counters/histograms rather than from
long-lived access-log archives.

The production WSGI app implements this policy with a fixed-cardinality shared request
registry. Gunicorn preloads the app before forking workers so counters are shared across the
worker processes; routine Gunicorn access logging is disabled. `/internal/metrics` renders
Prometheus text from the aggregate registry and `/internal/health` provides an uninstrumented
health probe. The public Caddy site rejects `/internal/*`. A separate Caddy listener may expose
only `/metrics` and `/health` on a specifically bound host/LAN interface; it defaults to host
loopback and deployment tooling refuses wildcard metric binds. This narrow facade never publishes
the application port or any other application route. No dynamic identifier, raw URL, query value,
or request header is admitted to the metric label vocabulary.

Data tools are a subsystem of InfinityDB. They remain usable independently for
inspection, validation, and rebuilding snapshots. The standalone scripts in
`tools/` keep their own dedicated regression coverage under `tests/` so their
filesystem safety, URL handling, and cross-platform naming remain validated
independently from the core database and web pipeline.

## Project domains

InfinityDB uses six canonical project domains for engineering ownership and
documentation: **Acquisition**, **Data processing**, **Deployment**, **Web backend**,
**Web frontend**, and **Project infrastructure**. The definitions, boundaries, and
documentation-label convention are maintained in `docs/project-domains.md`.

These domains classify where a change or durable contract belongs; they do not
replace the semantic game-data domains described by the data model. Cross-domain
work should name multiple project domains only when it materially changes the
contract between them.

## Documentation status

This document records both implemented architecture and accepted architectural
direction, but those are not interchangeable:

- **Current** describes implemented repository/application behavior.
- **Design direction** describes an accepted boundary or target shape that is
  not fully implemented yet.
- Concrete implementation work belongs in `docs/TODO.md`; this document should
  not maintain a second backlog.

Unless a paragraph is explicitly marked as design direction or future work,
architectural statements describe the current implementation.

## Semantic provenance and InfinityDB abstractions

Infinity Army and InfinityDB intentionally operate at different scopes. Army
source documents describe one army/list context at a time. InfinityDB combines
those local views into a game-wide reference, so cross-army identities and
relationships are first-class application information. A value selected from one
representative source context must not become a global ownership, identity, or
canonical-value claim merely because it is convenient to display.

Documentation and semantic audits use four provenance categories:

1. **Source-native fact:** an object, value, relationship, or taxonomy represented
   directly by the Army/metadata source. Normalization may change its storage
   shape but not its source meaning.
2. **Source-derived fact:** an interpretation calculated from source-native
   evidence. The derived name or classification belongs to InfinityDB unless an
   upstream contract defines it; inputs, derivation, fallbacks, and assumptions
   must be documented and testable.
3. **InfinityDB abstraction:** an application-level concept introduced to make
   source material comparable or useful across contexts. It may combine several
   source constructs and has no implied upstream object. Its purpose, source
   inputs, derivation, assumptions, and limits must be explicit.
4. **Presentation convenience:** a derived choice used only to render, label,
   navigate, or style information. It has no independent domain meaning and must
   not be reused as evidence for ownership, membership, playability, availability,
   or semantic equivalence.

These provenance categories are separate from the canonicalization categories
defined in `docs/data-model.md`. For example, an InfinityDB abstraction can
contain canonical facts, contextual deltas, and relationships while still being
an InfinityDB-defined concept rather than a source-native one.

Current examples include source-derived army role/playability and
`main_army_id`; the materialized application Army identity/hierarchy,
materialized Skills/Equipment/Weapons catalog identity, the materialized logical
unit, and the browser's `General profile` are InfinityDB abstractions; and
`display_army_id` / `display_faction` are presentation conveniences. For the Army
data model, these categories refer
to Army/metadata provenance; curated rules knowledge retains its own cited
external-source provenance.

## Configuration, curated data, manifests, and generated state

### Current

InfinityDB currently separates executable behavior, maintained project
knowledge, immutable source material, human-reviewed curated data, and
reproducible build output:

```text
code                         = behavior
config/                      = maintained project/domain knowledge
raw source data              = immutable external input
data/manifests/snapshots/    = generated acquisition provenance
data/curated/rules/          = source-controlled human-reviewed rules data
data/curated/rules-interactions/ = maintained rules-interaction review policy
data/curated/identities/     = source-controlled reviewed presentation identities
data/curated/peripherals/    = reviewed Army-to-Peripheral identity mappings
data/curated/snapshot-notes/ = source-controlled human snapshot annotations
data/generated/              = reproducible database/JSON build output
```

`data/generated/infinity.db` and `data/generated/rules.db` are the deliberate tracked
exception within generated output. They are byte-deterministic runtime release artifacts,
committed with the release that serves them so deployment consumes exactly the databases
validated during release preparation. `master.json`, normalized JSON, `infinity.raw.db`, and
other intermediate/generated working products remain ignored.

Aliases, mappings, filters, manual overrides, compatibility exceptions, static
asset declarations, and similar maintained domain knowledge belong in
validated, versioned configuration when they can change independently of the
code that interprets them.

`data/curated/` is different from configuration: it contains human-reviewed
information derived from identified external sources and retains source
provenance. `data/curated/rules/` is consumed by the rules-database build, while
`data/curated/rules-interactions/` is project review metadata: it owns the maintained
public-catalog scope for the interaction-review denominator, tracks whether each semantic
identity has had its outgoing interactions audited, and preserves deferred/future candidates
without becoming rules ontology or runtime input. Catalog progress is therefore measured
against the actual public Skill/Equipment/Trait/State identities rather than only against the
subset that already has curated rules records. A maintained release exception may keep an
explicitly vetted catalog identity in that denominator while deferring its canonical definition
to a distinct publication/domain scope; unclassified missing definitions remain pending, and
stale exceptions fail validation once a current definition exists. The maintained primary
catalog denominator established for 0.7.0 includes States; exact source variants and other
independently modeled supporting identities remain separate review identities.
`data/curated/identities/` contains reviewed source-derived presentation
relationships consumed during Army normalization. `data/curated/peripherals/` owns
the independent reviewed mapping from Army-local Peripheral definitions and Unit-backed
Peripheral occurrences to canonical application identities. It is consumed during Army
database export when its pinned snapshot provenance matches the normalized source; the
validated contract is copied into database metadata and runtime queries consume only the
materialized application tables, not the working-tree curated JSON. `data/curated/snapshot-notes/`
is a separate human-annotation contract and is not an application input.

This is not a requirement to make every constant configurable. Values that
define implementation behavior remain in code. Configuration is for maintained
domain knowledge and policy; curated rules data is for human-reviewed
source-derived facts.

`config/validation/source-anomalies.json` records the reviewed normalization
warning ceiling for one exact Army snapshot, including its acquisition date,
archive SHA-256, source-revision counts, and per-warning counts. The comparison
policy remains code: downloader-dated snapshots at or after the baseline may
reduce known warning counts, but a new warning category or growth above a
recorded count is a build regression. Inputs without downloader snapshot
provenance are outside this production-source regression check so synthetic and
investigative normalization remain usable.

`config/identity/source-identities.json` is the first repository-wide example
of the code/config split. It owns maintained logical-identity exceptions for
source unit, army-list, skill, equipment, and weapon IDs plus identity-name
aliases. Generic matching and duplicate-detection algorithms remain code.
Catalog alias-group references are authored as either positive numeric source IDs
or readable source slugs. The checked-in Skill, Equipment, and Weapon groups use
source-label slugs wherever those labels are unambiguous. A slug is resolved from
the complete source metadata catalog, supplemented by catalog rows actually used by
the snapshot, before application grouping; this allows maintained groups to name
valid source identities even when one variant is unused in the current Army lists.
Per-catalog `slug_aliases` may correct a known upstream spelling only at this
authoring/resolution boundary (for example `tinbot-neourocinetics` ->
`tinbot-neurocinetics`); raw source labels remain unchanged for provenance. The
identity policy therefore does not depend on the later application-domain slug
registry. A group that is wholly absent from the available source catalog is inert;
once any group member is present, unknown or ambiguous authored slugs fail
closed. Numeric references remain supported
where source identity or disambiguation matters. Curated rules `armyLinks` now apply
the same authoring principle at the later composition boundary: Skill, Equipment, and
Weapon links may use application-domain slugs, while legacy/source numeric references
remain valid. Unlike identity-manifest source-label slugs, these rules slugs deliberately
refer to the already-grouped application identity and are matched when Army and rules
data are composed at read time. This numeric-or-slug reference shape is the preferred
direction for other maintained/curated JSON references when their owning layer has
enough context to resolve them deterministically.
Current InfinityDB builds derive unit `main_army_id` from the imported Army
metadata faction-parent relationship, with maintained canonical-faction
overrides taking precedence. The former `xx01` arithmetic remains only as a
standalone/legacy normalization fallback when no usable metadata row exists for
the canonical faction.

Source canonical-faction ID `1` and Non-Aligned Armies grouping ID `901` are
kept distinct in identity/grouping semantics. ID `1` remains mercenary source/origin
provenance with no application `main_army_id`; the generic whole-army `xx01`
derivation is explicitly suppressed for that source identity. ID `901` remains
the metadata grouping identity for Non-Aligned armies. The former legacy
`1` -> `901` ownership override remains removed. Separately,
`data/curated/identities/army-display.json` records the reviewed display
relationship from canonical source identity `1` to the source faction slug
`non-aligned-armies`; normalization resolves that slug against the owning Army
faction metadata to display army `901` without changing source membership,
availability, or playability semantics. Canonical source identity `1` remains
numeric in this file because it is provenance identity with no authoritative
source-faction slug to own an equivalent readable reference.

The authored identity configuration is a build input, not a deployed runtime
file. InfinityDB normalization validates it, supplies normalization-time
exceptions, and writes the exact document and its deterministic SHA-256 into
`normalized.json`. Database export revalidates that pinned provenance, rejects
incomplete or conflicting identity metadata, and propagates the same policy to
the frontend and raw database metadata. Repository queries revalidate and
consume the policy pinned into that immutable database snapshot. Unit-detail
queries also derive each profile's `profile_identity` from that pinned policy;
browser grouping consumes the backend-derived identity and backend-derived
`display_name`, so browser assets do not duplicate profile alias, reinforcement-
prefix, or ignored-word rules. The maintained reinforcement prefixes themselves
live in the pinned identity policy under `name_normalization`. This keeps deployments self-contained and prevents later working-tree
configuration changes from silently changing the meaning of an existing
normalized or SQLite snapshot.

Weapon catalog policy now follows the same code/config ownership rule without
becoming deployed runtime state. `config/catalogs/weapon-categories.json` owns
the ordered weapon-family taxonomy, regular-expression patterns, fallback
category, and explicit weapon-reference category decisions.
`config/catalogs/weapon-overrides.json` owns corrections for incomplete or
inconsistent Army weapon metadata, such as missing deployable profiles, known
source naming anomalies, and exact metadata-profile rows that should not become
display weapon modes. Both maintained formats accept a positive numeric source
ID or a source-label slug, with readable slugs preferred. Normalization resolves
those references against the uncorrected source weapon catalog before applying
name/profile corrections; unknown or ambiguous slugs fail in strict resolver
use, while partial synthetic inputs may leave absent maintained references inert.
The original Army metadata envelope remains preserved for source provenance.
Repository/runtime queries therefore do not read the working-tree configuration.
Classification mechanics,
validation, and fallback behavior remain Python code. Actual game-rule facts
such as special weapon statistics, skills, and equipment are not source
corrections and therefore do not belong in these config files. The Armed Turret
special profile is now a cited curated `weapon` record in `rules.db`; the Army
repository exposes only source catalog/profile data, and the application layer
composes the curated special profile when rules data is available.

Weapon range-table columns are also source-derived rather than maintained domain
policy. The browser builds one ordered set of range endpoints from the finite,
positive `max` values in the displayed weapon profiles' imported `distance`
metadata. Centimetre labels use those source endpoints directly and inch labels
use the shared 2.5 cm conversion, so a new source range endpoint is displayed
without updating a hard-coded global range table.

Declaration categories follow the same composition boundary. Army snapshots identify
Skills/Equipment and their usage but do not provide the N5 action/declaration category.
Full curated Skill definitions own an ordered `facts.typeIds` array referencing the
canonical `skillTypes` vocabulary, so every Skill definition can carry multiple
categories regardless of whether it has an Army identity. `declaration-category`
records remain for partial classification of Army Skills without full definitions and
for Equipment; those records use singular `facts.typeId` plus deterministic order.
`SkillCatalog` treats categories from a full Skill definition as authoritative and falls back
to linked declaration records only when no full definition is available; Army-linked fallback
metadata may legitimately disagree with the rules classification. `CatalogRules` composes
Equipment categories from `rules.db`. With rules data available, the Skill list is also
composed from the canonical
Common/Special Skill vocabulary rather than blindly mirroring Army's skill-like source bucket:
reviewed cross-domain/metadata rows are filtered by maintained classification, and rules-native
zero-use Skills remain visible. Without a valid rules database, raw Army Skills remain browsable
with uncited `Unclassified` fallback and no source occurrence is discarded; Equipment receives
no invented category.

Skill-extra distance semantics are split according to source authority. Army
`extras.type` is authoritative for whether an extra is a distance; the repository
therefore marks `DISTANCE` extras directly and does not infer distance meaning from
numeric text. Rule-derived presentation details live in curated skill records.

Current curated rules format v21 makes applicability, review state, contribution role, typed
related-item edges, explicit catalog-variant inheritance, typed exact-source variants, and
cross-domain declaration categories part of the record contract. Each record carries explicit
`scope.game` / `scope.seasons`, review status/date, and a composition role of either
`definition` or `supplement`; source publication provenance remains in collection/source/citation
structures rather than semantic identity. Every semantic ID across current collections must have
exactly one definition. Current supplements retain their own cited contribution instead of being
field-merged by filename, collection ID, effective date, or load order. Runtime composition uses
only `status=current` collections by default. The exact JSON contract and format-version evolution
are maintained canonically in `data/curated/README.md` rather than repeated here.

Related rules concepts use typed one-way edges such as `enters-state`, `reveals-state`,
`has-subtype`, `reduces-modifiers-from`, `restricts-use-of`, `uses-effects-of`, and
`equips-with`. Targets resolve by stable typed semantic ID, not display name. Current edges must
resolve to a current semantic record before `rules.db` can be published, and reverse navigation is
derived rather than authored independently. Composed payloads expose a `display_relations`
projection with direction, resolved endpoints, reviewed player-facing grouping/labels, and a
backend-owned semantic order. Structural edges such as `variant-of` remain available to API
consumers but intentionally receive no generic Related-rules presentation. Relation-vocabulary
meaning and concrete reviewed interactions are documented in `data/curated/README.md` and
`docs/rules-semantics.md`.

### Current: connected-data domains

The 0.8.0 domain audit is maintained in `docs/080-connected-domain-audit.md`. Its
accepted boundary is intentionally narrow: Fireteams become a new first-class
application domain because their Army-local chart identity, composition rules, member
semantics, FTO/Wildcard context, notes, and Reinforcement interaction cannot be reduced
to Unit edges. Hacking Programs are now promoted from their existing structured
application projection to a first-class rules/reference surface without duplicating
that data: Army metadata owns exact Program profiles and baseline Device associations,
while `rules.db` owns reviewed semantic identity/effects and typed rules relationships.

Peripheral/Controller relationships, profile/loadout/unit-option includes, selection
constraints, profile-group dependencies, Reinforcement parentage, and broader
faction/cross-Army membership remain relationships among existing application
identities and are presented through those existing surfaces. Generic rules
concepts, Attributes, Ammunition, and Training may remain supporting link targets unless
a later completeness audit demonstrates an independent player-facing catalog need.
A relationship target is not, by itself, justification for a new domain.

Schema 25 / compatibility revision 33 implements that Fireteam boundary.
`application_fireteam_charts` selects one provenance-bound Army-list source per application
Army; related derived tables preserve type limits, team/type/member structure, logical-Unit
resolution, Army-local FTO loadout eligibility, Wildcard identity, Fireteam-Level equivalence
labels, and rule-bearing chart/team notes. `/api/fireteams` and `/fireteams` now read that
application projection directly and never return to the raw normalized Fireteam tables during
normal serving. Reinforcement parent limits remain separate in
`application_army_reinforcement_parents`, so the projection/browser does not pretend to be an
army-list legality engine or merge Main- and Reinforcement-section member pools. General
Fireteam rules remain rules-domain data: `rules.db` owns `rule:fireteam-general` and
`rule:fireteam-level-bonuses`, while `/api/fireteams` composes their bounded reference payload
with each Army chart. The browser generates type/member guidance, cumulative Level bonuses,
source links, and provenance-aware historical/community terminology from those curated facts;
older compatible deployments without those rules records keep the Army chart and omit only the
reference block.

States are now a first-class rules-backed reference surface (`/states`, `/api/states`) rather
than application/Army catalog rows. `StateCatalog` composes current `state` definitions
directly from `rules.db`, preserving the boundary between static rules identities and any
future per-game runtime state. The same static projection participates in reviewed cross-rule
gameplay relationships without becoming a live game-session state model.
`Super-Jump` and `Forward Deployment` currently use
`variantSemantics.occurrenceParameters` to state how a positive distance sign should be
displayed. Exact source variants use `variantSemantics.sourceVariant`; format v9
introduced numeric `level`, explicit `named`, and numeric
`attribute-replacement` variants. Martial Arts L1-L5 and Strategos L1-L2 are
maintained as reviewed Level variants, BS=12, BS=11, and CC=21 are reviewed
Attribute-replacement variants, and the six non-base TinBot identities are reviewed
named variants. Skill source semantics are composed into detail and Unit API payloads;
Equipment source-specific rules are routed to the matching catalog variant by numeric
Army source ID. Neither path derives rules meaning from display names, and TinBot
occurrence modifiers remain separate from its named source-variant identity.

Army presentation and classification currently combine imported relationships
with merger-derived fields. The source/application scope distinction is important:
Infinity Army presents one concrete Army list at a time, while InfinityDB presents
the whole game and must preserve cross-Army identities and relationships alongside
those list-local occurrences. A source Army list is therefore an occurrence/context
container, not the complete application ontology for faction identity or unit
membership. The explicit application Army identity/hierarchy was introduced in
database schema version 15 from reviewed Army aliases plus the overlapping
`army_lists`/`metadata_factions` evidence. That derived layer owns the canonical
application name/slug, role/playability/grouping, source-ID provenance mapping,
and explicit reinforcement-parent relationships without replacing either source
projection or the broader faction registry. Normal repository serving now reads
that layer for Army identity, source-alias resolution, hierarchy, playability,
unit faction/group presentation, and reinforcement relationships. Concrete
availability still comes from `army_units`; `unit_factions` remains the separate
game-wide declared-membership relation. Unit detail presents that relation explicitly and the
Unit Explorer's `declared_faction_id` filter follows it without reclassifying membership as Army
availability; source faction IDs with no current list remain source-only identities. The only
normal-serving dependency on
`army_lists` is the legacy source-shape `kind` value, retained for API compatibility
and as a reinforcement fallback for incomplete/legacy source relationships.
`metadata_factions` is no longer a normal-serving dependency. Browser code
consumes these backend fields and must not infer faction or reinforcement semantics
from Army ID prefixes or suffixes.

Mercenary units and Non-Aligned Armies are also separate source concepts.
Ordinary unit records declare their normal faction availability through
`factions`. The source additionally contains dedicated mercenary variants that
consistently use canonical faction `1`, an empty `factions` list, a `merc-...`
slug, and army-specific occurrences that supply optional mercenary
availability. Many also use 10,000-offset-style unit IDs, but that numeric
pattern is supporting evidence only. Normalization records mercenary source
roles, army-occurrence availability provenance, and audited mercenary-to-standard
source-unit matches. Generic standard duplicate matching is also audited during
normalization and persisted as `genericUnitMatches`. Database creation consumes
those audits plus configured aliases, performs the reinforcement-only identity
audit using the pinned name-normalization policy, and materializes one
logical-unit relation. The arithmetic duplicate fallback remains only inside the
builder for older normalized inputs that lack the persisted audits. Repository
queries consume the materialized identity and `army_units.availability_kind`;
the old canonical/faction availability inference remains only as a legacy-row
fallback.

### Current: manifests and snapshot notes

InfinityDB now separates generated snapshot provenance from human-reviewed
snapshot annotations:

```text
data/manifests/snapshots/    = generated acquisition provenance
data/curated/snapshot-notes/ = human-reviewed snapshot annotations
```

Generated manifests are not maintained project knowledge. Current Army, wiki, and symbol
acquisition writes version-3 `InfinityDB snapshot provenance`: `snapshot.contentSha256`
identifies normalized member paths plus bytes independently of ZIP container metadata, while
`snapshot.archive.sha256` identifies and verifies the exact immutable ZIP byte stream. Army
manifests additionally record `source.dataChangedOn`, derived from the latest encoded source date
across the contained Army document versions. Legacy version-1 and version-2 manifests remain
readable. Archive-labeled records are immutable/idempotent, paths are portable project-relative
values when available, and generated manifests remain ignored local state. The canonical
field-level contract lives in `docs/data-model.md`; `data/README.md` owns its storage/lifecycle
summary.

Human notes use the separate version-1 `InfinityDB snapshot note` contract and remain
source-controlled interpretation rather than acquisition/runtime input. That older note contract
is intentionally keyed to the exact archive SHA-256 (`snapshot.archive.sha256`), not the newer
logical content hash. Acquisition tooling never creates, rewrites, or deletes those notes.

Symbol refresh orchestration is explicit and snapshot-pinned.
`tools/build_symbols.py` requires either `--snapshot` for an existing immutable
Army archive with generated provenance or `--fetch-snapshot` for an intentional
network refresh when starting a new build. It verifies the selected Army
archive/provenance and keeps that same artifact pinned through the complete
pipeline; normal application/database builds never invoke it or acquire network
data. The orchestrator keeps interactive output compact: the active stage owns
one updating console line while existing verbose stage output is captured
verbatim in a timestamped local log under `data/logs/symbols/` (or an explicit
`--log` path). `--stop-after` exposes snapshot, acquisition, materialization,
preflight, font-audit, deduplication, text-conversion, compression, and
publication checkpoints. After acquisition, `--resume` loads the SHA-bound
current build manifest and immutable snapshots without rediscovery/reacquisition. Resume
verifies an existing raw work tree rather than replacing it; a missing work tree
may be reconstructed only while the manifest is still version 2.

Army-symbol acquisition also writes the version-2
`data/manifests/army-symbol-build.json`. This generated build-state document is
separate from immutable snapshot provenance: it binds the selected Army and
SYMBOLS artifacts and carries the verified Army acquisition pin (source URL,
language, acquisition timestamp, source-document count, and observed source
revisions). It also records every downloaded raw asset by URL/hash/archive path,
preserves every authoritative and audit-only source reference, and stores the
discovery audit counts. Raw assets are resolved in strict order: a matching
Git-ignored local override, an exact-URL entry from the prior validated immutable
symbol snapshot/cache, then upstream network access. The prior build manifest is
the cache index; its referenced symbol archive/provenance and the selected member
hash are validated before reuse. `--refresh-symbols` bypasses the archive cache
without bypassing local overrides. Invalid matching overrides fail rather than
falling through, and unused overrides plus URL/filename collisions are reported.
The downloader remains raw-resolution only; `tools/build_symbols.py` owns the
subsequent versioned processing stages and the publisher alone assigns final
application paths. The terminal build manifest remains ignored local processing/cache
provenance and is not a deployment input. Final publication copies only the Army source
archive name/SHA-256 required for runtime provenance into the tracked
`data/manifests/symbol-publication.json`; deployment binds the tracked `infinity.db`
`snapshotArchiveSha256` directly to that compact publication identity.

### Current: army roles and logical-unit identity

Army role/playability is an InfinityDB source-derived classification built from
source relationships rather than an upstream role/playability taxonomy, numeric
ID patterns, or known identity constants. Self-parented
imported ordinary lists that parent other lists remain main armies. An ordinary
imported list that itself parents ordinary lists but whose metadata parent is a
different identity is a grouping node; metadata-only referenced parents can
also be surfaced as grouping nodes. Their children receive the `non_aligned`
role. Current source data uses imported list `901` for the Non-Aligned Armies
grouping role even though `901` has a real source roster and metadata parent
`900`. Ordinary source documents identify their reinforcement list through the
explicit `reinforcements` field, and reinforcement lists do not participate in
grouping-node discovery. `/api/armies` exposes role and playability separately
from source-list existence; grouping identities are non-playable and cannot be
used as selectable `army_id` values, while their source rows remain preserved.
For current NA2 data, InfinityDB intentionally does not expose a separate playable
roster query for `901`: its roster remains preserved source provenance, and
application availability is consumed through the playable child army lists that
share those units. This endpoint policy does not erase `901` or its relationships
from the game-wide model.

Mercenary source variants are classified during normalization from their
source-semantic contract (`canonical == 1`, empty declared `factions`,
`merc-...` slug), with schema drift reported instead of guessed. Audited
mercenary-to-standard source-unit matches and explicit army-occurrence
availability provenance are persisted and consumed by repository queries. The
10,000-ID offset is supporting matching evidence only, not the semantic rule.

The legacy `1` -> `901` canonical-faction ownership override remains removed.
ID `1` stays source provenance for mercenary identity and does not receive an
application `main_army_id`; 901 remains a separate Non-Aligned Army grouping
identity. A distinct curated display relationship derives `display_army_id=901`
for canonical-1 units so presentation can use the grouping symbol without
conflating it with ownership or playability. Generic duplicate matching is
persisted during normalization and
reinforcement-to-standard matching is audited during database creation; both
feed the materialized logical-unit identity consumed by repositories.

A logical unit is an InfinityDB application abstraction: Army supplies source-unit
records but no separate upstream `logical_unit` object corresponding to this
relation. Logical-unit identity and the first canonical unit payload layer are
materialized during application database creation. This does **not** merge or rewrite source rows:
source unit IDs, army occurrences, profiles, loadouts, options, and availability
provenance remain attached to their original source unit in build staging and
`infinity.raw.db`. The exporter resolves
configured unit aliases plus persisted generic and mercenary matches and the
database-build reinforcement audit into `logical_units` / `logical_unit_sources`,
then copies the representative-backed general fields onto `logical_units` while
materializing source-attributed aliases, notes, and opaque `spectables` context.
Every source-defined unit still maps to exactly one logical unit. Unit list,
search, and detail general fields now read that canonical layer; alternate
source labels, including the existing derived `Unit <source id>` fallback for a
missing source name, are materialized as traceable search aliases. Lossless source rows
remain available in build staging and `infinity.raw.db` for provenance, validation, and
source semantics that have not been promoted into the published application model; normal
runtime repositories do not read those raw tables.

### Canonical application data and semantic deduplication

InfinityDB separates its **lossless source model** from a **canonical application model**.
Profile and loadout payloads, canonical logical-unit fields and aliases, application Army
identity/hierarchy, application catalog identities, and the reviewed 0.8 relationship layer
are materialized and consumed by normal runtime reads. The remaining source-presentation
work is explicit 0.9 completeness work rather than an unfinished physical source/application
database split.

The merged and normalized source layers remain source-oriented and lossless.
Repeated records in those layers are not inherently defects: repetition may
represent provenance, army context, source-document structure, or the way the
Infinity Army API expresses relationships. Source rows must not be physically
merged merely because their payloads appear equivalent.

The application model has different requirements. It should represent
each distinct player-relevant fact once where that can be established safely,
and represent genuine contextual differences explicitly rather than repeating
complete payloads solely because the same information appeared in several
source documents.

The existing `logical_units` and `logical_unit_sources` relation is the first
application-level identity layer. It establishes which source unit records
represent one logical unit while preserving every source occurrence. Canonical
representative-backed logical-unit fields plus source-attributed alias/note/
`spectables` context are now materialized beside that identity layer. Canonical
profile and loadout payload layers extend the same principle from **identity
deduplication** to **semantic payload deduplication** for unit-detail data.
Application Army identities and application catalog identities extend the model
further into Army/faction presentation and rule-reference catalog serving. Milestone 2B
established the next relationship/storage boundary: include targets, reviewed Peripheral
relationships, selection-safe Unit constraints, and profile-group dependencies are
materialized. Schema 25 / compatibility revision 33 extends that boundary with the
Army-scoped Fireteam application projection, whose repository/API/browser presentation
completes the 0.8.0 connected-data layer. Remaining source/context relationships stay
explicit until their application presentation/model is justified.

Runtime-performance evidence for this work is collected separately from semantic
acceptance. `tools/benchmark_runtime.py` measures representative repository read
paths against an already-built `infinity.db`, reporting cold and warm median/p95
timings. Before/after comparisons are meaningful only when both revisions use the
same database source snapshot and run on the same host under comparable load; the
benchmark is release evidence, never a substitute for equivalence or provenance
checks.

Semantic deduplication must be evidence-driven and lossless:

- exact semantic equality is the first and safest deduplication criterion;
- similarity of names, IDs, or payloads is never sufficient by itself;
- genuine army-, profile-, loadout-, source-, or availability-specific
  differences remain explicit contextual data;
- normalization-only structures must not automatically be interpreted as
  independent player-facing facts;
- source IDs, source rows, army membership, availability provenance, and
  reconstructability remain preserved even when application payloads are
  canonicalized;
- every deduplicated application record must remain traceable to the source
  occurrences that support it.

This canonicalization work is also part of the version-1.0 completeness effort.
Determining whether two source structures represent one fact or several distinct
facts clarifies what information InfinityDB must ultimately expose to players.
The goal is therefore not database-size reduction by itself. Storage and query
improvements are secondary benefits of a clearer semantic model.

The build-time resolver treats those inputs as identity evidence, combines their
transitive connected components, selects one deterministic representative,
validates missing/conflicting references, and persists the resolved mapping.
Explicitly unmatched mercenary or reinforcement records form their own logical
units. Older normalized inputs that lack the persisted generic/mercenary audits
retain the legacy duplicate fallback inside the builder; repository reads do
not rediscover logical identity.

Since schema version 11, the logical-unit ID equals the representative source-unit
ID so existing API IDs and URLs remain stable. `representative_unit_id` is still
stored explicitly, leaving room to decouple application identity from source
identity later without changing provenance. Repository aggregation follows the
mapped source IDs when collecting profiles, loadouts, army occurrences, search
terms, and other source-backed data. It does not pre-aggregate those source
tables into logical copies, because normal and optional-mercenary occurrences
can belong to the same logical unit and army while retaining different
`availability_kind` semantics.

Schema version 12 introduced the derived canonical-profile layer, and schema
version 13 added the corresponding canonical-loadout layer beside the lossless
source tables. Build-time materialization scopes reusable payloads to an existing
`logical_unit` and keeps source/Army context on one-to-one occurrence relations:
profile AVA/logo and loadout points/SWC remain contextual. Schema version 18 adds
the first broader relationship materialization: Profile and Loadout include
attachments remain occurrence-scoped, while their target endpoint resolves to a
canonical loadout payload. Shared top-level Unit-option includes likewise retain
their source parent but resolve the target separately for each Army occurrence.
Reviewed Peripheral identity and relationship data are now materialized separately:
embedded source definitions map to canonical Peripheral entities, Unit-backed Peripherals
reuse logical-Unit identity, and source-context Cyberplug Controller access pools retain
their Army provenance.

Unit-detail repository reads now consume both canonical payload layers. Source
profile/loadout tables remain available in `infinity.raw.db` and build staging for
provenance, source-semantic validation, and deferred source-local/contextual
relationships; they are no longer part of the published application database. Normal
search/filter/catalog reverse reads expand canonical payload occurrences rather than
traversing those legacy payload tables. Compatibility revision 19 also requires
unit-oriented indexes on both canonical occurrence tables so this read-path split does not
regress unit-detail query behavior.

Milestone 2B established the physical application/raw storage split. Export builds a complete
temporary relational staging database, runs source-to-canonical validation there, writes the
normalized source schema plus exact lossless rows to `infinity.raw.db`, then publishes only the
retained application schema. Foreign keys whose targets are raw-only are omitted from the
published schema; retained-to-retained constraints remain enforced. Normal serving and runtime
validation have no dependency on `infinity.raw.db`. The current schema-specific table-role counts
and retained/source-only inventory belong in `docs/data-model.md` and its separation audit rather
than being duplicated here.

### General application-domain identifier contract

Every InfinityDB application domain should expose two interchangeable identity forms
when a stable domain-local slug can be resolved: the numeric application ID and the
canonical slug. Numeric IDs remain valid compatibility and implementation keys; slugs
are the preferred human-facing form. Application-facing repository/API calls, web
routes, filters, cross-links, and maintained references that identify a domain object
should accept either form rather than creating slug-only or numeric-only interfaces.
Generated URLs, browser state, API references, and human-authored configuration should
prefer the slug when it is resolved and unambiguous.

This is a forward-compatible domain rule, not a one-time route migration convention.
When adding a new application domain, establish its canonical numeric identity and
domain-local slug resolver together, then reuse that resolver across all consumers. Do
not create a second ad-hoc slug scheme in a route, filter, JavaScript component, or
curated loader. If a slug is unavailable, collides, or cannot be resolved
deterministically, retain the numeric form and fail closed rather than guessing. Tests
for a new domain should demonstrate that numeric and slug references resolve to the same
application identity. Source-only/provenance layers may continue to use source-native
identifiers where application identity is intentionally not in scope.

### Current: domain-unique application slug layer

Source identity, internal application identity, and public navigation identity are
separate layers. Corvus Belli numeric IDs remain source/provenance references, and
current numeric application IDs remain supported implementation/compatibility keys. InfinityDB-curated concepts use stable typed IDs such as `skill:doctor`
or `rule:peripheral-type:servant`; the prefix identifies the domain and is not a claim
that one slug must be globally unique across unrelated domains.

Schema version 17 / compatibility revision 25 introduces the derived
`application_domain_slugs` registry for the current application-owned `armies`,
`units`, `skills`, `equipment`, and `weapons` domains. Each row retains the numeric
application key, a deterministic normalized candidate, an optional resolved slug,
and a `resolved`, `collision`, or `unavailable` status. Slugs are unique only within
their domain. Candidate generation lowercases, removes Unicode combining marks,
limits output to ASCII letters/numbers with single hyphen separators, and never
invents order-dependent numeric suffixes. Duplicate candidates therefore fail
closed as explicit collision records instead of silently becoming `foo-2`. Because
these domains retain numeric compatibility routes, a digit-only candidate is also
recorded as `unavailable`: the candidate remains visible for diagnostics, but it never
receives a routable `slug` that could shadow the numeric namespace.

The registry is the application identity foundation for public routes. Numeric
compatibility remains supported; any later retirement of numeric routes is a separate
post-1.0 policy decision. Existing Army/unit source/display slugs remain source/context data; they
may seed application candidates but are not automatically promoted to permanent
public identifiers. Repository resolution is centralized at the application-domain
boundary. One shared resolver accepts either a source/application numeric reference or a
domain-local slug and returns the current application identity for Armies, Units,
Skills, Equipment, and Weapons. Domain-specific helpers and detail reads reuse that resolver rather than asking
web routes or other consumers to translate slugs first. Slug lookup itself still resolves
only `resolved` registry entries.

Armies, Skills, Equipment, Weapons, and logical Units are additive public consumers of
the registry. Catalog list/detail API payloads expose a resolved application `slug`; Unit
and Army payloads instead expose a distinct `public_slug` so their pre-existing
source/context `slug` fields keep their current meaning. Browser links and Unit-explorer
filter state prefer application slugs while existing numeric references remain valid.
Catalog-list payloads expose each logical Skill/Equipment/Weapon item's materialized
`source_ids`, allowing the browser to recognize accepted non-representative legacy
numeric filters and canonicalize them to the same preferred slug. Skill, Equipment,
Weapon, and Unit detail web/API routes accept either form; Army
selection through the Unit explorer/API accepts either a source/application numeric ID
or the resolved Army public slug and normalizes both to the application Army identity.
Digit-only candidates are rejected by the registry itself and therefore have no public
slug to emit; consumers do not perform their own numeric-shadow suppression. Nested Unit
payload references to Equipment
and Weapons expose the canonical application slug after resolving any source-variant ID
through application catalog provenance; Unit references embedded in catalog, Trait, and
Skill Modifier payloads expose `public_slug` after source/logical Unit identity resolution.
Cross-domain API references follow the same additive rule: existing numeric fields stay
unchanged, while canonical application references gain a readable companion when one is
routable. Scalar Army fields use `main_army_slug` / `display_army_slug`; structured Army
objects retain source/context `slug` and add `public_slug`; Trait usage variants add
`item_slug`; and Skill Modifier rows add `skill_slug`. Source/provenance-only IDs are not
relabeled as canonical slugs.
This migration does not redirect numeric routes or declare derived slugs permanently
frozen; per-domain freezing, reviewed overrides, aliases, and redirect/canonical-URL
behavior remain required before numeric routes are retired or redirected.

Traits share the public slug grammar and fail-closed collision policy but intentionally
do not duplicate their canonical identity in `application_domain_slugs`. Curated Trait
identity is already owned by `rules.db` as a stable typed ID of the form `trait:<slug>`;
that single slug segment is therefore the canonical public route projection and remains
stable when the curated display name changes. With a valid rules database, the public
Trait catalog is rooted in the complete current curated Trait vocabulary, including
canonical Traits with zero Army usage. Raw Army `metadata_weapons.properties` values
then contribute usage to those identities through canonical names, exact curated aliases,
and parameterized source prefixes. That source field is not itself treated as an
authoritative Trait vocabulary: values that resolve to current rules Labels or to generic
signed Skill/Equipment modifier notation remain source-profile properties and do not
create Trait routes. Unresolved raw properties retain a provisional source-derived
identity rather than being silently discarded. Without `rules.db`, the Army Trait catalog
remains source-driven and usable. Application code must not independently normalize an
arbitrary property label into a canonical Trait link, because that would bypass curated
identity and collision resolution.

The current reviewed 2026-09-18 snapshot resolves all initial registry candidates:
57 Armies, 737 logical Units, 88 Skills, 28 Equipment items, and 132 Weapons
(1,042 identities total), with no collisions or unavailable candidates. These counts
are snapshot evidence rather than permanent invariants.

The Peripheral rules/identity work uses this project-wide identity architecture rather
than a one-off slug scheme. The rules side is represented in the current curated
rules collection: Doctor, Engineer, Cyberplug, and Peripheral are canonical Skill records
and the five N5.3 Peripheral types are validated `rule` records with explicit controller-
eligibility facts. The separate `data/curated/peripherals/army-identities.json` contract
owns reviewed `peripheral:*` identities for embedded Army Peripheral definitions, reviewed
source-Unit mappings onto existing logical Units for Unit-backed Peripherals, and
source-context Cyberplug Controller access pools. The current application database consumes
the contract only when its pinned snapshot hash matches, stores the contract/hash in database
metadata, and materializes canonical application relationships so runtime repository reads
never infer identity from Army labels or open curated JSON.

## Snapshot acquisition lifecycle

### Current

Standalone Army, wiki, and symbol acquisition uses one immutable timestamped-archive model.
Downloaders stage loose files temporarily and publish `JSON YYYYMMDD-HHMMSS.zip`,
`WIKI-<language> YYYYMMDD-HHMMSS.zip`, or `SYMBOLS YYYYMMDD-HHMMSS.zip`; same-second
collisions receive `-2`, `-3`, and so on rather than overwriting an existing artifact.

Army acquisition performs two complete API passes over metadata and every Army/Reinforcement
endpoint and publishes only when corresponding responses are byte-identical. Wiki acquisition
likewise fails closed for required crawl content: unresolved required URLs publish neither an
immutable wiki snapshot nor provenance, while optional site chrome/project pages outside the
mirror contract are reported separately. Failed wiki crawls preserve partial work for inspection;
successful crawls remove it after publication. Normal database/application builds never perform
implicit acquisition.

Corvus Belli `metadata.json` remains source data contained in or supplied alongside Army
snapshots; it is not InfinityDB provenance. Current archived wiki-derived curated records bind
to the exact timestamped wiki ZIP/hash and member names, while pinned `oldid=` revisions that are
not archive members remain URL-backed sources.

Generated snapshot provenance semantics are defined in `docs/data-model.md` and summarized with
its storage lifecycle in `data/README.md`. Version 2 introduced the distinction between logical
snapshot-content identity and exact archive-byte identity; version 3 adds the derived Army
source-data change date. Human snapshot notes remain a separate version-1 exact-archive-hash
contract.

### Design direction

Future snapshot-comparison tooling may emit structured generated diff/report data while curated
snapshot notes remain the human interpretation.

## Data flow

The current application data flows are:

```text
Army directory / ZIP
    + required metadata.json
    -> merge + lossless verification
    -> master.json
       + validated identity configuration
    -> normalize + relationship validation
    -> normalized.json + validation report
       + pinned identity document / SHA-256
    -> SQLite importer
       + revalidated pinned identity provenance
    -> full relational staging DB
       -> source/canonical consistency validation
       -> infinity.raw.db (normalized source + exact rows)
       -> infinity.db (self-contained application schema)
    -> repository -> HTTP API -> browser UI

PDF / wiki research sources
    -> human-reviewed cited collections in data/curated/rules/
    -> `infinity-db build-rules`
    -> separate rules.db
    -> rules repository -> HTTP API -> browser UI
```

The two database flows are deliberately independent. `build-rules` consumes
only validated JSON collections under `data/curated/rules/` and skips the
reserved `example.json` template; it never reads PDFs, wiki snapshots, or other
curated subtrees directly. A rules-document update must not rebuild an Army
snapshot, and an Army import must not modify rules data. Where a screen needs
both, the application/service layer joins stable application-level identities
and returns a combined representation; the databases do not import from or
attach to one another.

Asset acquisition and processing is likewise a separate build concern. Current
Army-symbol acquisition is source-semantic and snapshot-pinned: every
`units[].profileGroups[].profiles[].logo` and `metadata.json -> factions[].logo`
reference is authoritative, maintained static declarations are included,
`resume[].logo` is audit-only, and a recursive scan fails closed on unknown
SVG-bearing source fields. URLs are resolved once while every reference is
preserved separately in `army-symbol-build.json`. A referenced network asset
that genuinely returns HTTP 404 is preserved as an explicit unavailable source
record and omitted from the immutable SVG archive; other HTTP/transport failures
still abort acquisition. Acquisition writes version-2
build state. The orchestrator then verifies the immutable `SYMBOLS` archive and
its snapshot provenance, re-hashes every listed member, and rebuilds a derived
`data/work/symbols/<artifact>/raw/` tree rather than modifying the raw archive.
It writes a deterministic structural SVG preflight under `data/reports/symbols/`
and promotes build state to version 3 with the report identity and summary.
Structural preflight covers parse validity, active text, empty text objects, and
font-family declarations. A following installed-font audit reuses the established
CSS/effective-font resolver, applies validated Infinity-specific aliases from
`config/symbols/font-aliases.json`, classifies active-text assets as
`fonts_available` or `fonts_missing`, reports alias normalization and unused
declarations, and promotes the build state to version 4 with both its report and
alias-config identities. Missing/ambiguous effective fonts stop orchestration
before expensive processing. The next integrated stage reuses the established
exact-first visual duplicate detector: byte-identical sets avoid redundant
renders, remaining candidates are compared through decoded RGBA output from the
selected renderer, and inconclusive render failures remain unique. Deterministic
representative ranking prefers `no_active_text`, then `fonts_available`, then
weaker classifications before filename/path tie-breakers. Version-5 build state
records duplicate reports, renderer settings, counts, total source/canonical
loose-SVG byte sizes, reclaimed bytes, and a complete portable
`archivePath -> canonical archivePath` mapping while retaining every acquisition
asset and source reference. The SHA-bound duplicate summary report also records
the percentage size reduction. Canonical text conversion then consumes exactly
that version-5 mapping: only canonical `fonts_available` assets are converted,
canonical `no_active_text` assets are copied forward unchanged, and persistent
`inkscape --shell` workers are the production default. One-shot Inkscape remains
an explicit fallback/debug backend and `usvg` remains experimental.
Temporary conversion copies remove unresolved local `<image>` references before
Inkscape and report every discarded reference while leaving immutable raw inputs
unchanged. This prevents Inkscape from rebasing already-broken raster links
through randomized temporary directories and leaking host-specific paths into
canonical SVG bytes. Converted
outputs are revalidated for parseability and remaining active text before a
version-6 manifest is written. A failed conversion records failed state and
reports but does not replace the prior canonical work tree. Compression then
consumes exactly that version-6 canonical tree through the reusable
`svg_compress.py` engine. Production uses the balanced profile with resvg visual
validation, p2-first/p3-rescue precision, 32/64 CSS-pixel targets at DPR 1/2,
RMS/changed-fraction limits of 0.01, and pixel-difference threshold 8. The
complete balanced output is revalidated and atomically promoted to the derived
`compressed/` work tree; successful state advances to manifest version 7 with
SHA-bound compression reports and settings. The balanced compression report binds
each canonical output path to its SHA-256, so later stages can verify the exact
version-7 bytes. Compression failure leaves prior compressed output and version-6
state intact. Final publication verifies and consumes that hash-bound version-7
compressed work tree, the pinned Army snapshot, and the authoritative build
manifest. It materializes a temporary application asset tree, derives the canonical
Army, Unit/profile, and static mappings from authoritative references plus the
canonical asset mapping, validates the complete result, transactionally replaces the
generated static symbol outputs plus `data/manifests/symbol-publication.json`, and
advances successful state to version 8 with that manifest SHA-bound into build state.
Before replacement, publication compares the existing generated SVG set with the
staged incoming set by path and SHA-256. Added, removed,
changed, and unchanged counts plus path-level differences are recorded in the
publication mapping; symbols present only in the previous publication are preserved in
a timestamped `data/backups/symbols/` backup as part of the same transaction. Failed
publication removes that staged backup while restoring the prior generated tree.
Maintained static-symbol categories remain publication namespaces: order symbols
publish under `orders/`, while characteristic symbols publish under `characteristics/`.
Canonical processing may collapse equivalent assets without discarding their
source references. For unit artwork, source profile slot
`profileGroups[0].profiles[0]` retains the stable
`units/<canonical-army-slug>/<unit-id>-<unit-slug>.svg` browser path. Distinct
later profile-slot artwork is preserved with deterministic one-based
`--<group>-<profile>` suffixes (for example `--2-1.svg`). Distinct artwork for
the same logical unit in a non-owner source army is namespaced with
`--army-<army-id>` before any profile-slot suffix. Exact duplicate slots and
army references continue to share one canonical published file. Conflicting browser lookup
keys still fail rather than using legacy first-symbol-wins behavior. Source
resolution, validation, deduplication, conversion, compression, and publishing
remain distinct stages with provenance recorded rather than inferred from final
filenames.
Manifest promotions are forward-only: an earlier stage helper cannot demote a
later passed build state. Where retry is supported, the stage performs an explicit
in-memory retry transition and replaces persistent state only after the new result
validates.

Production deployment with the processed third-party symbol publication is
fail-closed. The approved SVG publication and
`data/manifests/symbol-publication.json` are tracked release content, so clean
source/package validation verifies the publication directly by path, SVG parseability,
byte count, and SHA-256. The host-side production deployment guard additionally requires
terminal version-8 symbol-build state and verifies its SHA-bound publication manifest
against the tracked file while also checking database/publication provenance. After
Docker builds the application image, the image verifier revalidates the installed
package against that manifest and exercises one served asset from each publication
namespace before Compose may replace the running service. Raw Army/wiki/PDF/source-
symbol archives remain excluded from Git and routine packages; Corvus Belli's explicit
permission covers redistribution of InfinityDB's processed graphical publication for
this non-commercial project, not a change in ownership or MIT-license scope.

## Module boundaries

| Project domain | Layer | Responsibility | Extension point |
| --- | --- | --- | --- |
| Data processing | `infinity_army_data` | Interpret and validate source data | Source-format changes and additional normalization |
| Data processing | `infinity_db.domain_slugs` | Shared domain-local slug normalization, validation, and collision policy | Additional application/public identity domains |
| Data processing | `infinity_db.database.schema` | Table definitions, composite keys, references, schema version | New normalized entities and future migration policy |
| Data processing | `infinity_db.database.application_domain_slugs` | Materialize provisional application-domain slug assignments | Reviewed overrides and future domain expansion |
| Data processing | `infinity_db.fireteam_semantics` | Shared source-label semantics for FTO, Wildcards, Fireteam-Level labels, and chart limits | Future reviewed Fireteam source-shape changes |
| Data processing | `infinity_db.database.fireteam_relationships` | Materialize the Army-scoped canonical Fireteam projection | Fireteam repository/API presentation and future reviewed identity refinements |
| Data processing | `infinity_db.database.importer` | Validate and store a complete snapshot | Alternative storage adapters, such as PostgreSQL |
| Web backend | `infinity_db.database.repository` | Read-only application queries | Unit details, profile comparisons, catalog queries |
| Web backend | `infinity_db.web.app` | Validate HTTP input and serialize query results | Additional routes and API resources |
| Web frontend | `infinity_db.web.static` | UI, shared page-shell components, URL state, loading and error handling | New screens, filters, and catalogs |
| Acquisition | acquisition/asset `tools/` | Explicit source download, snapshot, archive, and asset-processing workflows | New independent source/asset tooling |
| Project infrastructure | shared development `tools/` and `.github/` | Checks, CI, work archives, and repository-wide engineering support | New development/release automation |
| Deployment | deployment scripts, Docker/Compose, server configuration | Package and operate validated application output | Additional deployment targets |

Only the importer consumes normalized JSON. Read-only runtime imports must not
load the importer, Army normalizer, or maintained build-policy configuration as a
side effect; an installed application serving already-built databases is
independent of source-checkout-relative `config/` paths. HTTP routes query the
repository; browser code calls the API. Neither web layer parses raw Army files. Browser
requests live in `api.js`; shared unit-row rendering lives in `unit-list.js`;
page-specific state and rendering live in the corresponding module (for
example, `app.js` or `catalog-detail.js`). The current UI uses native modules
and requires no JavaScript build step. Browser pages execute only same-origin external
modules: the HTTP Content Security Policy explicitly restricts scripts to `self`, and
page-shell templates must not introduce inline script bodies or event-handler attributes.
When Corvus Belli graphical symbols are
published, army and unit symbols are addressed by stable ID-and-slug paths while
JavaScript maps source identities to those paths. The Unit map also records only the
profile-logo overrides whose published artwork differs from a Unit's primary symbol.
Unit-detail responses preserve the contextual source profile-logo URLs as `logo_urls`;
the browser resolves those values through the generated overrides and falls back to the
Unit's primary mapping, allowing secondary artwork to stay attached to its General
profile without making logo context part of canonical gameplay identity. The current
processed publication is fully browser-addressable (806/806 SVGs). Corvus Belli has explicitly
permitted InfinityDB to redistribute the processed graphical publication in the
public repository and release/build packages for this non-commercial project. The
assets remain Corvus Belli property and outside the MIT License. Raw acquisition
archives remain separate build/provenance inputs; see the third-party notices for
the current rights boundary.

Acquisition tools must not become hidden network dependencies of normal builds.
A normal build can consume explicit local snapshots. Network refreshes are
separate, intentional operations.

## Validation and CI policy

Local test execution now separates hermetic and full-asset coverage explicitly.
`run_checks.py --assets off|auto|required` validates the complete published
symbol set before enabling `full_assets` tests; direct pytest excludes those tests
by default. Final publication writes the tracked
`data/manifests/symbol-publication.json`, which binds every published SVG path to its
SHA-256 and owns the Army, Unit/profile, and static symbol mappings used by the
backend. The current processed publication is fully browser-addressable
(806/806 SVGs); the
separate subset check remains part of the publication contract so future preserved
variants cannot weaken full-set validation. A detected
partial/corrupt local asset tree is an error in `auto`/`required`, while a
completely absent tree is valid for hermetic testing.

Hosted CI delegates validation to the same project check runner and controlled fixtures used
locally. Required source CI is network-hermetic with respect to acquisition: it validates the
tracked processed SVG publication directly instead of rebuilding it from Corvus Belli sources or
external rendering tools. Installed-wheel and container smoke checks separately verify packaged
resource paths and deployment behavior. Workflow triggers, platform/interpreter matrices,
required branch checks, hosted worker exceptions, and the supplementary external-bundle asset
workflow are maintained canonically in `docs/ci.md` rather than duplicated here.

## Portability and filesystem policy

Python tooling should support Windows, Linux, and macOS unless a component is
explicitly documented otherwise.

Core pipeline logic should use portable filesystem/process APIs rather than
shell-specific command strings or machine-specific paths. External executable
discovery should be centralized and allow explicit configuration before
platform-specific fallbacks.

Generated asset names and persistent generated-state paths should be
host-independent. Treat filenames as case-sensitive internally and detect
case-only collisions before publishing.

Raw inputs are immutable. Persistent generated files should be built and
validated separately and atomically replace prior output where practical.
Failure should leave the previous valid output usable.

## Browser design system

The WSGI page renderer composes every browser route from a page-specific
document, the shared navigation, and shared header/footer fragments. The page
header receives structured breadcrumb and catalog-tag data from the route; the
footer receives the application version. New pages should use the
`<!-- navigation -->`, `<!-- page-header -->`, and `<!-- page-footer -->`
markers so their shell stays synchronized with existing pages.

Same-origin browser navigation keeps that shared shell mounted and replaces only
`main#main`. The navigation layer synchronizes the document title, description
metadata, body data attributes, and active parent navigation item before loading
the next page module. Transient page modules that own fetches or window-level event
listeners must dispose them on `infinity:beforenavigation`; persistent shell modules
are intentionally exempt because their DOM survives the replacement.

`static/styles.css` is the browser design-system entry point. Its root tokens
define shared color roles, surfaces, borders, spacing, radii, control height,
focus treatment, shadows, and the canonical typography system. Typography has two
orthogonal contracts: semantic font-family roles and a shared size scale. Brand text uses
Audiowide, display headings use Oxanium, normal interface/running text uses IBM Plex Sans,
dense tabular data uses IBM Plex Sans Condensed, and developer/identifier text uses IBM Plex
Mono. Components select `--font-family-brand`, `--font-family-display`,
`--font-family-body`, `--font-family-compact`, or `--font-family-mono`; they must not name
those concrete faces directly. The corresponding WOFF2 files are tracked presentation assets
under `static/fonts/`, remain under their SIL OFL 1.1 licenses, and are generated from upstream
Google Fonts TTF downloads with `tools/prepare_web_fonts.py`. Source TTF collections are not
part of the runtime publication.

`--font-size-root` is the single base size; fixed `--font-size-*` tiers are expressed in
`rem` so the whole interface scales coherently when that root changes. The root uses a
percentage of the browser default rather than a fixed pixel value so user font-size preferences
remain effective. Fluid title and hero tokens may use viewport interpolation inside `clamp()`,
but their bounds remain `rem`-based. Components must use these shared tokens rather than
literal sizes or page-local clamps. Normal introductory/body copy uses the base tier while
metadata and dense tables use the smaller tiers deliberately. Reuse these tokens and established components
such as `.main`, `.topbar`, `.explorer`, `.button`, and `.page-footer` rather
than introducing page-local visual values. Detail pages use `.main-detail` to
retain the common layout and responsive behavior. Detail renderers also reuse
`.detail-group`, `.detail-section-title`, `.data-surface-header`, `.data-label`,
and `.badge`; use their modifiers for semantic variants instead of duplicating
detail-table geometry or type treatments.

Surface hierarchy uses `.surface` with default, `--subtle`, or `--highlighted`
variants. Tables use the comfortable default or `.data-table--compact` for
detail and usage data; retain those variants instead of adding page-specific
cell padding or header type rules.

Unit-list and general-profile surfaces may use the unit's derived display-faction
colors as accents. Keep those accents within the shared token and gradient
system so catalog-specific styling remains legible and consistent.

Browser preferences are stored locally. User-selected distance-unit, optional-unit,
**Fireteams include Wildcards**, Developer-mode, and cache-bypass values are stored in
browser `sessionStorage`; values loaded from persistent cookies are mirrored there before
use. Disabling persistent settings therefore does not reset them during the current
tab/session. When the user enables
**Remember settings** and accepts the cookie prompt, the same values are mirrored to
one-year SameSite cookies for reuse in later browser sessions; disabling that option
removes the persistent cookies without clearing the current session values. The Settings
sidebar exposes those controls; on compact screens it becomes a top-bar menu beside
Navigation. New sidebar or top-bar menus should use this same inline-sidebar and
compact-dropdown pattern. Developer mode sets `data-developer-mode` on the document
root; use `.developer-only` for inline technical details and `.id-column` for table
columns so they remain hidden in the player-facing view by default.

### Design direction: browser UX and responsibility boundaries

Browser presentation should optimize first for fast lookup, comparison, and scanning
of dense game data. Clarity, hierarchy, legibility, and predictable interaction take
priority over decorative complexity, while avoiding an unnecessarily cramped
interface. Navigation, terminology, controls, tables, cards, badges, and feedback
states should reuse shared patterns rather than creating page-local visual languages.
Secondary provenance and developer information should use progressive disclosure so
technical depth remains available without dominating the normal player view.

Responsive behavior is a content-priority decision rather than simple shrinking.
Phone, compact/tablet, and desktop layouts should deliberately adapt navigation,
filters, tables/statlines, detail groups, and multi-column data. Accessibility is part
of the design contract: semantic HTML, keyboard operation, visible focus, sufficient
contrast, non-color-only meaning, usable touch targets, reduced-motion behavior where
motion exists, and useful screen-reader labels/status announcements are expected.
Faction/army accents and future theme colors must remain subordinate to semantic
meaning so domain state remains understandable regardless of theme, color perception,
or asset availability.

Preserve the current lightweight browser-native architecture unless a concrete
requirement justifies changing it. Native ES modules and the absence of a frontend
build pipeline are deliberate current constraints, not gaps to solve by default.

Python owns imported-data/domain semantics, identity and rules interpretation,
database access/querying, request validation, stable API contracts, application/version
metadata, and HTTP concerns. Domain meaning that would otherwise require JavaScript to
infer IDs, names, source quirks, or rules semantics belongs in backend/API fields.
Browser code owns information presentation, interaction state, responsive/accessibility
behavior, client-side display formatting, theme/UI preferences, and composition of
semantic API data into views. API payloads should expose semantic roles, states,
identities, labels, and relationships rather than CSS classes, literal colors, layout
instructions, or page-specific markup.

The same-origin deployment model remains appropriate. As the web layer is refactored,
separate API handling, page-shell/static delivery, and top-level request dispatch more
clearly on the Python side, and organize browser code around explicit API transport,
preferences/theme state, reusable view/components, and page modules. Browser JSON API
access continues through `api.js`; new page scripts should not accumulate independent
transport or domain-interpretation logic.

### Design direction: theming

Themes use stable semantic identifiers, initially `light` and `dark`, and are implemented
through semantic theme tokens separated from theme-neutral layout/component rules.
Components consume roles such as surfaces, text, borders, actions, focus, status,
shadows, and data emphasis rather than hard-coded light-theme colors. Faction/army
colors remain domain accent tokens layered onto the selected theme with contrast-safe
treatments in each supported theme.

An explicit user theme selection overrides any project/operating-system default and is
stored through the existing Settings preference contract; theming must not introduce a
second persistence mechanism. Resolve the selected theme before first meaningful paint
to avoid navigation/reload flashes. Browser metadata and `color-scheme` behavior should
track the selected theme so form controls, scrollbars, and other user-agent UI remain
coherent. Project-owned graphics should use the same semantic token contract where
practical instead of unnecessary light/dark asset forks. Supported themes must preserve
contrast and distinguishability for status/range colors, links, focus indicators, muted
text, tables, selected rows, dialogs, menus, and faction accents.

## Required Army API metadata

The required API `metadata.json` is a supplemental source snapshot. Its records
are preserved separately and enrich display names for matching army IDs.
Faction records also provide explicit parent relationships, names, and slugs
used for unit presentation and grouping. Metadata never creates an army list or
changes unit membership, which continue to come solely from the army JSON
files. Database builds fail when no metadata snapshot is provided beside,
inside, or explicitly alongside the Army source.

Corvus Belli's `metadata.json` is source data. It is conceptually distinct from
the InfinityDB-generated acquisition provenance written under
`data/manifests/snapshots/`.

## SQLite persistence

SQLite is the initial backend because it runs locally without a separate
service. Schema definitions are separate from ingestion code. The current Army
application database has schema version 25 and database compatibility revision
34; it rejects incompatible databases with a rebuild instruction. The importer
validates a complete relational staging database, publishes a self-contained
application database and a lossless sibling raw archive, creates read-path indexes
after loading, and persists SQLite planner statistics. Migration of
persistent user-authored data is future work; database rebuilds currently
replace a complete imported snapshot.

Rules-reference data uses a distinct SQLite database with its own schema,
compatibility/versioning, importer, and atomic replacement policy. The current `rules.db` schema version is 7 and its database compatibility revision is 8. This database is not an
extension of `infinity.db` or `infinity.raw.db`.

The source-controlled `data/curated/rules/` JSON layer is the only
application-facing representation of facts researched from PDFs or the wiki.
`data/pdf/` and `data/wiki/` remain local reference material and are not opened
by application code; `infinity_db.curated.load_curated_document` validates the
rules intermediary contract before the rules importer consumes it.

The current curated-v21 rules contract stores collection scope, source metadata,
typed records, maintained vocabularies, Army catalog links, typed related-rule edges,
explicit variant inheritance and exact-source variant semantics, composition role, review
state, and source-specific citations. PDF sources carry both the local
reviewed file and official upstream URL; PDF citations use printed pages.
Archived wiki sources carry exact ZIP/hash provenance and citations use archive
members, while pinned historical wiki revisions stay URL-backed.
`vocabularySources` follows the same locator rules.

No collection may silently combine current, historical, FAQ, and season rules.
Curated-rule files older than format v21 must be migrated before ingestion.

## HTTP API

All routes are same-origin and read-only. `GET` returns JSON or a static asset;
`HEAD` returns the corresponding headers without a body.

HTML is revalidated on each request. API representations have
snapshot-specific ETags and short shared-cache lifetimes. Static assets use a
content-derived revision in addition to the semantic application version before
receiving immutable cache headers, so rebuilding frontend files under an unchanged
version cannot strand browsers on an older module graph. Pages compare application,
static, and snapshot revisions with the version endpoint, then reload through a fresh
URL after a code deployment or data refresh.

### `GET /api/version`

Returns `{ "version": "<application version>", "static_revision": "...", "snapshot_revision": "..." }`. The
browser uses it to detect application, browser-static, or imported-snapshot changes.

### `GET /api/armies`

Returns `{ "items": [...] }`. Each item exposes `id`, `name`, `slug`,
legacy source-shape `kind`, explicit `role`, `playable`, `group_id`,
`group_name`, `group_slug`, `parent_army_ids`, and `unit_count`. Roles are
derived from imported source relationships rather than Army-ID ranges or known
identity constants. Self-parented metadata factions that are imported ordinary
army lists are `main`; metadata children of ordinary playable parents are
`sectorial`; children of grouping nodes are `non_aligned`; and lists referenced
by ordinary source `reinforcements` links are `reinforcement`. A referenced
parent is a grouping node when it is absent as an imported ordinary list, or
when it is an imported ordinary list whose own metadata parent is different from
itself. Current source data uses imported list `901` for the Non-Aligned Armies
group, with metadata parent `900` and its own source roster; runtime role
classification does not special-case that ID. Grouping items expose
`playable: false`. `unit_count` counts distinct application logical units with
concrete `army_units` availability after reviewed Army aliases are applied;
multiple source representations of one logical unit do not inflate the
player-facing count.

### `GET /api/units?army_id=101&search=fusilier&limit=50&offset=0`

Returns `{ "items": [...], "total": 0, "limit": 50, "offset": 0,
"availability": {...} }`, where `total` is the number of unique logical units visible
under the currently enabled optional-unit modes. `availability.shown` matches `total`;
`availability.available` counts the same Army/search/catalog query with every valid
availability path considered; and `availability.filtered` is their unique-unit
difference. `availability.categories` reports `shown`/`filtered` explanatory counts for
`standard`, `mercs`, `specops`, `teamops`, and `reinforcement`. Category figures are
derived from non-redundant minimal availability requirements and may overlap, so they
are explanatory rather than additive. Each item has `id`, `name`, `main_army_id`,
`main_faction`, `display_army_id`,
`display_faction`, `army_ids`, and `armies` (`id` and `name` per currently
visible Army availability).
`main_faction` is the source-derived main/grouping context resolved through the
materialized application Army hierarchy, while `display_faction` is the exact
application presentation identity selected by normalized `display_army_id`.
Neither field replaces the unit's game-wide membership relationships. The zero
total above illustrates the response shape.

- Omit `army_id` to browse all source-defined units, deduplicated by global ID.
- Concrete Army-list availability comes from `army_units`; the response's
  `army_ids` / `armies` fields report that availability after optional-mode
  filtering. `unit_factions` separately preserves broader declared game-wide
  faction membership. Canonical/source-origin and main/display fields do not
  replace either relationship.
- `main_army_id` is a source-derived application grouping field. Current
  InfinityDB builds derive it from imported metadata faction parents, with
  explicit maintained overrides taking precedence. It is not authoritative for
  army membership, availability, or game-wide ownership; the field name is a
  compatibility term rather than a complete ontology. The `xx01` derivation is
  retained only for standalone/legacy normalization without usable metadata.
  Canonical source ID `1` remains mercenary source provenance and therefore has
  no application `main_army_id`; Non-Aligned grouping uses the separate metadata
  identity `901`.
- `main_faction` and each army occurrence's `faction` are resolved from the
  materialized application Army hierarchy. Sectorial/non-aligned Armies use their
  canonical group; reinforcement Armies use the common canonical group implied by
  their explicit parent relationships when that group is unambiguous.
- `display_army_id` normally mirrors `main_army_id`, but reviewed source-derived
  exceptions come from curated identity data. Browser symbol/styling code resolves
  that ID through the application Army mapping and contains no special-case Army IDs.
- Search matches accent- and punctuation-insensitive, case-folded name
  substrings, including Unicode.
- Results sort by display name after case-folding, removing diacritics, and
  ignoring punctuation and other non-alphanumeric characters; unit ID breaks
  ties for stable pagination.
- Current normalized snapshots persist audited generic and mercenary unit
  matches. Database creation consumes those audits, configured aliases, and its
  reinforcement-to-standard audit to materialize the transitive logical-unit
  relation. The old 10,000-ID/ISC calculation is retained only as a build-time
  compatibility fallback for older normalized inputs. Configured identity
  aliases remain pinned project policy rather than normalized source facts;
  repository reads use the materialized mapping rather than reconstructing
  logical groups.
- `limit` defaults to 50 and must be between 1 and 200; `offset` defaults to 0
  and must be a nonnegative SQLite integer.
- `search` is limited to 200 characters. Invalid or repeated unit query
  parameters return HTTP 400 with `{ "error": "..." }`. Unknown army IDs return
  an empty list.
- Optional `skill_id`, `equipment_id`, and `weapon_id` parameters narrow
  results to units with matching catalog items in a profile, loadout, or unit
  option. Each accepts the current application-domain slug or a legacy numeric
  source/application ID. Filtering resolves the reference to the logical catalog
  identity and matches every materialized source member of that identity, so grouped
  items such as TinBot behave as one filter. The browser explorer writes slugs when
  available and keeps numeric values only as compatibility fallbacks.
- Unknown resources return 404; unsupported methods return 405; database read
  failures return 503 without exposing internal exception details.

#### 0.9 Unit Explorer filtering and extended-result contract

The 0.9 Unit Explorer extends the existing backend-owned filter contract rather than
introducing a second browser-only interpretation of profile/loadout data. Categorical filters
resolve stable public identities where available, and every user-visible filter has a defined
URL representation so a filtered view can be shared and reproduced. Troop Type,
Classification, and Characteristics use public slugs with numeric IDs retained as compatibility
fallbacks.

AVA, points, and SWC support exact matching or an inclusive bounded range through `ava`,
`ava_min`, `ava_max`, `points`, `points_min`, `points_max`, `swc`, `swc_min`, and `swc_max`.
AVA exact matching accepts ordinary values from `0` through `99` and `total`; ranges cover
ordinary numeric AVA only. Negative source values used for subordinate/ancillary profiles are
not exposed as ordinary AVA filter values. Points use nonnegative integer exact/range values.
SWC exact matching accepts ordinary numeric costs, bonus tokens such as `+1`/`+1.5`, and `-`;
SWC ranges apply only to ordinary nonnegative numeric costs and deliberately exclude bonus and
non-cost tokens.

The backend retains the owning semantic context while evaluating contextual numeric filters:
AVA belongs to an Army/profile occurrence, while points and SWC belong to loadout occurrences.
When any AVA/points/SWC constraint participates in a query, other selected profile/group/loadout
criteria must be satisfiable in the same source Army/profile-group/loadout context. Profile-level
facts apply to the loadouts in their profile group; loadout-level facts remain loadout-local.
Unit-option facts remain Unit-wide because the source model does not attach them to a profile
group. This prevents a weapon or other loadout-specific fact from one option from satisfying a
points/SWC constraint that is true only for an unrelated option. Focused repository/API tests
pin exact/range inclusivity, special AVA/SWC values, and the loadout-coherence rule.

The Unit list will gain an optional extended presentation mode. Its purpose is to expose enough
profile context to evaluate filtered results without opening every Unit detail page: base
statistics, troop type, classification, characteristics, and Army-specific AVA. The existing
Army-availability symbols remain the ownership/availability anchor; per-Army AVA may be placed
beneath or visually combined with those symbols once the final responsive treatment is chosen.

Multi-profile Units cannot be represented faithfully by collapsing all profile statistics into
one extended row. The current presentation direction is to show subordinate profile rows beneath
the main Unit row, indented or otherwise visually attached to the parent. That layout remains a
presentation hypothesis until checked against representative multi-profile Units; the durable
constraint is that profile-specific statistics and classification must remain visibly associated
with the profile that owns them. Advanced-filter expansion is a natural way to enable extended
mode, but whether that mode is URL/share state or a local display preference is intentionally
left open until the UI interaction is finalized.

### `GET /api/units/{unit_id}`

Returns one logical unit, including its general data and the profiles,
loadouts, availability, skills, equipment, and weapons that apply to each army
where it occurs. `source_notes` preserves every non-empty note with its source
Unit label, source Unit ID, representative status, and applicable Army contexts;
it does not promote a source-specific restriction into general Unit data.
Each Army occurrence's `composite_options` preserves its source-context bundle:
cost, miniature count, order contribution, and resolved included loadouts. The
response retains source variants separately rather than treating source-local
option IDs as canonical identities. The
response includes the same `main_faction` object used by unit summaries; each
army occurrence also includes its derived `faction` object or null. Profile
records include a backend-derived `profile_identity` used by the browser to
group equivalent labels under the identity policy pinned into
the database. A reinforcement-only source variant is folded into a uniquely
matching standard unit. Current mercenary availability is evaluated from explicit normalized
`availability_kind` source-occurrence provenance at repository-query time. Unknown unit IDs return 404.

### `GET /api/skill-extras`

Returns `{ "items": [...] }` of distinct skill/extra combinations whose imported
Army extra has `type = DISTANCE`, together with the units using each combination.
When curated rules define skill parameter semantics, each item also carries the
corresponding `parameter_semantics` display hint. The Skill Modifiers browser
page consumes this endpoint.

### `GET /api/search?q={name}`

Returns `{ "items": [...] }` for a non-empty name search spanning every
player-facing database domain: Armies, Units, Skills, Equipment, Weapons, Traits,
States, Hacking Programs, and Fireteam charts. Each result carries its explicit
`domain`, display `name`, and a route-backed `href`; consumers do not infer a target
surface from a label. The endpoint composes the existing domain read models so public
slugs, rules-only identities, and Army-scoped Fireteam charts remain resolved by their
own canonical owners rather than by a separate search identity scheme.

### Rules-reference endpoints

`GET /api/skills`, `GET /api/equipment`, and `GET /api/weapons` return
`{ "items": [...] }` for their searchable catalogs. Catalog records combine
equivalent source labels where appropriate and include an ID, display name, and
reference link when the metadata snapshot provides one.

`GET /api/skills/{id-or-slug}`, `GET /api/equipment/{id-or-slug}`, and
`GET /api/weapons/{id-or-slug}` return one catalog item and its distinct usage variants.
Skill, Equipment, and Weapon slugs are resolved through the application-domain slug
registry; existing numeric IDs remain accepted for compatibility.
Each variant includes the relevant extras and logical units that use it. Weapon
details additionally include metadata weapon profiles, such as ammunition,
traits, and range data, when present in the supplied metadata snapshot.
Metadata weapon/equipment profiles retain the raw `traits` value. The application
composition layer also exposes `trait_references`: each reference preserves the
raw `label` and, when a matching curated Trait record is available in `rules.db`,
adds that record's canonical `name` and stable Trait-catalog `slug`. Exact source
aliases/misspellings and parameterized source-label prefixes are curated rule
data rather than Python tables. Raw properties that instead match the curated
Labels vocabulary, or generic signed modifier notation for a known Skill/Equipment,
remain visible source text but receive no Trait slug. Without a valid `rules.db`,
raw Army property labels remain browsable and linkable but no curated
canonicalization or summary is invented. Browser rendering consumes these
backend-derived references and does not canonicalize property text or generate
Trait slugs independently.

Skill list/detail responses obtain declaration categories from current curated
`declaration-category` records in `rules.db`. Equipment detail responses use the same
record kind for Equipment actions such as Deactivator, GizmoKit, and MediKit. Category
records themselves are composition metadata and are not emitted as ordinary `rules`;
other curated records remain available through that field. If rules data is unavailable
or a Skill has no curated declaration, the Skill API reports an uncited `Unclassified`
category; Equipment has no invented fallback.

`GET /api/traits` returns the canonical current Trait vocabulary from `rules.db`
when available, enriched with matching raw Army usage; canonical zero-use Traits remain
visible. If no rules database is supplied, the endpoint falls back to the raw Army
property-derived catalog. `GET /api/traits/{slug}` returns a Trait's usage grouped across
skills, equipment, and weapons and, for a curated identity, its cited rule record and
concise summary.

Future implementation work is tracked in `docs/TODO.md`; this document records
current architecture and clearly labeled lasting design direction rather than
maintaining a second backlog.
