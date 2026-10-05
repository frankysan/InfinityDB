# Architecture

**Project domains:** Project infrastructure, Data processing, Web backend, Web frontend, Deployment

This document owns InfinityDB's **system architecture**: engineering principles, subsystem
boundaries, durable cross-layer contracts, and accepted design direction. Detailed data semantics
belong in `docs/data-model.md`; browser component/layout rules belong in
`docs/web-design-guidelines.md`; artifact/provenance lifecycle belongs in `data/README.md`; concrete
unfinished work belongs in `docs/TODO.md`.

Unless a section is explicitly marked **Design direction**, it describes current behavior.

## Project goals

1. Maintain validated, queryable Infinity data while preserving the source/context needed to
   explain where each application fact came from.
2. Provide a fast, read-only web reference that connects Units, Armies, rules concepts, and their
   relationships without requiring users to reason about raw Army storage.
3. Keep acquisition, curation, generation, runtime serving, browser presentation, and deployment
   independently understandable and reproducible.

## Guiding principles

1. **Accuracy.** Prefer official sources and preserve uncertainty when evidence is incomplete or
   ambiguous.
2. **Flexibility.** Add useful ways to browse and understand the data without turning the project
   into a rules engine or list builder by default.
3. **Transparency.** Distinguish InfinityDB code/interpretation from external data, quoted text,
   fonts, and graphical assets.
4. **Privacy.** Collect aggregate operational information only; do not build visitor profiles or
   persistent tracking.

## Engineering principles

1. **Preserve source inputs.** Raw upstream data/assets are immutable inputs; transformations happen
   in separate working/generated layers.
2. **Never lose information silently.** Normalization, deduplication, filtering, and cleanup must
   preserve provenance and surface ambiguity or discarded structure explicitly.
3. **Code defines behavior; validated data defines maintained knowledge.** Aliases, mappings,
   exceptions, curation, and other independently maintained domain decisions should not be buried
   in consumer code. Generated manifests describe provenance/build state, not policy.
4. **One pinned input set per build.** Every generated artifact must be reproducible from explicit
   source identities, curated inputs, configuration, and project revision.
5. **Prefer explicit relationships over conventions.** Do not reconstruct semantic ownership from
   ID ranges, naming conventions, or UI assumptions when the relationship can be stored or derived
   centrally.
6. **Make semantic provenance explicit.** Source-native facts, source-derived facts,
   InfinityDB-owned abstractions, and presentation conveniences are different categories and must
   not be silently conflated.
7. **Rules are semantic evidence, not an application schema.** Model the rules concepts needed to
   explain and connect InfinityDB's reference data; do not attempt to encode the entire game engine.
8. **Build conservatively.** Fail closed on unsupported schema, ambiguous mapping, stale curation,
   or mismatched provenance rather than guessing.
9. **Separate responsibilities.** The project-domain boundaries in `docs/project-domains.md` are
   architectural boundaries as well as planning labels.
10. **Determinism and portability are artifact contracts.** Given the same inputs and declared
    toolchain, persistent generated artifacts must be byte-identical across supported platforms.

## System boundaries

InfinityDB has six engineering domains:

- **Acquisition** fetches immutable Army/wiki/symbol source snapshots and records provenance. It is
  explicit and networked; ordinary builds/tests are not.
- **Data processing** validates, normalizes, curates, derives canonical application identities, and
  produces deterministic runtime artifacts.
- **Web backend** opens validated runtime databases read-only and exposes application-shaped
  repository/API responses. It does not reconstruct build-time policy.
- **Web frontend** renders backend-owned semantics, local presentation preferences, and shareable
  browser state. It does not become a second normalization layer.
- **Deployment** packages one release's application code, tracked runtime databases, and processed
  graphical publication into an immutable production image.
- **Project infrastructure** owns CI, packaging, release orchestration, documentation conventions,
  and cross-platform validation.

The canonical ownership definitions are in `docs/project-domains.md`.

## Semantic provenance

Every nontrivial application fact should fit one of these classes:

- **source-native** — represented directly by an upstream Army/rules/wiki source;
- **source-derived** — deterministically inferred from explicit source relationships;
- **curated/reviewed** — maintained by InfinityDB from cited evidence where the source does not
  provide the needed application structure directly;
- **InfinityDB abstraction** — a project-owned concept introduced to make the combined data useful,
  such as logical Units or the General profile; or
- **presentation-only** — browser grouping, formatting, disclosure, or other UI structure that does
  not create new game semantics.

The implementation must preserve enough provenance to distinguish these categories. The detailed
identity and fact model is owned by `docs/data-model.md`.

## Maintained knowledge, generated state, and runtime artifacts

InfinityDB deliberately separates four kinds of repository data:

- `config/` contains validated maintained policy used by build/normalization logic.
- `data/curated/` contains human-reviewed source-derived knowledge and rules-reference content.
- `data/manifests/` contains publication/provenance state; the tracked symbol publication manifest
  is a release contract, while acquisition/build manifests are normally local generated evidence.
- `data/generated/` contains generated artifacts. `infinity.db` and `rules.db` are deterministic,
  tracked runtime release artifacts; intermediate JSON and `infinity.raw.db` remain rebuildable
  development outputs.

Runtime code must not reach back into raw archives or working-tree curation to reinterpret an
already-built database. Build-time configuration may be packaged for installed build commands, but
opening a runtime database remains independent of repository-relative build policy.

See `data/README.md` and `data/curated/README.md` for the concrete file contracts.

## Application domains

`src/infinity_db/application_domains.py` is the canonical capability registry for player-facing
semantic ownership. Domain identity is separate from presentation shape: a domain may be a catalog,
overview, explorer, scoped view, or embedded vocabulary, and capabilities such as navigation,
search, glossary participation, detail pages, and publication are independent.

Current published top-level domains are Armies, Units, Skills, Equipment, Weapons, Ammunition,
Traits, States, Hacking Programs, Fireteams, Labels, and General Rules. Attributes and scoped Game
terms are published embedded vocabularies. Global search and Glossary are cross-domain projections,
not competing semantic owners.

`docs/application-domains.md` owns the detailed domain/presentation contract.

### Planned scenario domain

Core-rules scenarios are a required first-class application domain for 1.0. The architecture review
covered the four N5.3 core scenarios, the final ITS Season 17 set, and the current ITS Season 18 set.
The comparison is retained in `docs/rules-semantics.md`; it establishes that core-only assumptions
would be too narrow for deployment geometry, scoring cadence, asymmetric sides, Classified
Objectives, scenario elements, and revision/season provenance.

Scenario definitions are curated rules/reference knowledge, not Army-export facts or mutable match
state. Maintained scenario source therefore belongs in validated structured documents under the
rules curation pipeline and is published into `rules.db`, not `infinity.db`. Runtime publication uses
a deliberate hybrid model: stable/queryable identities, provenance, collection membership, and
cross-domain references are relational, while ordered/nested scenario structure is retained as a
validated typed payload rather than flattened into prose or an untyped JSON blob. The exact table
layout is an implementation concern, but the semantic boundary below is fixed before 1.0 work
begins.

A stable scenario identity is independent from both a source publication/revision and membership in
a collection such as core N5.3, ITS Season 17, or ITS Season 18. A publication can revise a scenario
without creating a new conceptual identity, and a season can add, remove, or alter scenario
applicability without mutating that identity. Scenario pages resolve a selected published revision
and expose its provenance explicitly.

The common scenario model includes force/table configuration, sides, deployment and scoring geometry,
objectives and score timing, end conditions, scenario rules/actions, objective/scenery elements, and
typed links to existing canonical rules/catalog entities. Classified Objectives, HVTs, carried
objects, control regions, asymmetric attacker/defender roles, selectable objective sets, seasonal
extras, Reinforcements suitability, and similar mechanics are optional reusable features or
collection-scoped overlays rather than mandatory fields on every scenario. Tournament pairing,
ranking, and mutable in-game state remain outside the scenario definition domain.

Scenario geometry is semantic data. It uses typed regions/points/anchors and parameterized dimensions
for supported table/force configurations, including side-relative transforms and placement/exclusion
constraints. Diagrams are generated presentation, never the canonical geometry. This contract lets
the same scenario data later drive deployment-map generation and other tooling without introducing a
second map representation. Scoring is likewise structured by timing, points/caps, side/applicability,
and typed condition/comparison kinds where known; maintained explanatory text may supplement unusual
procedures without requiring InfinityDB to become a complete game-state rules engine.

## Identifiers and routing

Application-facing identities use stable domain-local slugs where the domain supports them. Numeric
source/application IDs remain accepted where required for compatibility and provenance, but generated
links, share state, and maintained application-facing configuration should prefer slugs.

A domain's central resolver owns slug/numeric resolution. Consumers must not introduce parallel slug
logic or infer routes from labels. Public rules-reference route ownership is derived from the
application-domain registry.

Browser URLs and JSON API parameters are separate contracts:

- APIs retain explicit query parameters suitable for programmatic clients.
- Shareable browser presentation state uses the common versioned, scope-bound `s=` token implemented
  by `src/infinity_db/web/static/share-state.js`.
- Legacy explicit browser parameters remain readable compatibility inputs and are canonicalized by
  the owning page; they are not the preferred generated link form.

## Acquisition and snapshot lifecycle

Network acquisition is explicit. Successful downloaders publish immutable timestamped archives only
after validating the acquisition and write generated provenance separately. Ordinary database builds
consume a chosen local snapshot and do not fetch newer data implicitly.

Snapshot provenance distinguishes logical content identity from exact archive-byte identity. The
current Army provenance also records the latest source-data date encoded by the contained Army
versions so the UI can distinguish **source data changed on** from **InfinityDB downloaded on**.

Raw Army/wiki/PDF/source-symbol archives remain local inputs by project policy. They are not runtime
server dependencies and are not committed merely because the processed graphical publication may be
redistributed.

The detailed snapshot/archive contract is owned by `data/README.md`.

## Generated database boundary

InfinityDB serves two tracked runtime databases:

- `data/generated/infinity.db` — canonical application data derived from Army snapshots and reviewed
  source relationships;
- `data/generated/rules.db` — curated rules/reference semantics.

`infinity.raw.db` is a development/audit archive of normalized source structures and is not a
production runtime dependency. Runtime repositories query application tables and materialized
provenance; they do not fall back to raw normalized tables for convenience.

Database validation checks application/schema identity, compatibility revision, and required
metadata before normal reads. Persistent user-authored state is not part of the current runtime
model, so generated databases remain replaceable release artifacts.

Current semantic/storage details are in `docs/data-model.md`.

## Symbol publication boundary

The processed SVG publication under `src/infinity_db/web/static/` is tracked release content and is
bound by `data/manifests/symbol-publication.json`. The manifest owns published paths/hashes, browser
mappings, and the compact Army source identity needed to prove that runtime Army data and symbols
come from the intended source snapshot. Peripheral profile artwork has its own
`peripherals/<main-army>/` publication namespace rather than inheriting parent-Unit filenames.

Raw/source symbol archives, conversion work trees, detailed stage reports, and terminal build state
remain local processing evidence. Production deployment requires the tracked publication, not the
raw symbol pipeline.

Corvus Belli has explicitly permitted InfinityDB to redistribute the processed graphical assets for
this non-commercial project. They remain Corvus Belli property and outside the MIT license; see
`THIRD_PARTY_NOTICES.md`.

## Rules-reference boundary

Curated rules data is built independently from Army data. It may define concise reviewed summaries,
typed identities, aliases, declaration categories, relations, Labels, embedded vocabularies, and
other application semantics needed by the reference UI.

Maintained prose uses typed semantic tokens for supported reference namespaces. Completed review
batches are enforced by `maintained-text-link-reviews.json`: new unlinked semantic candidates are
errors. If a passage is genuinely ambiguous, use an explicit `review-needed` marker rather than
silently choosing a target. Reviewed ordinary-text collisions are passage-fingerprinted so wording
changes reopen review.

Relations are authored once in their semantic direction and may derive reverse presentation edges.
Do not duplicate reciprocal facts merely to make both pages navigable. The rules database remains
semantic/reference data, not a simulation engine.

Detailed schemas and review policy are owned by `data/curated/README.md`,
`docs/rules-semantics.md`, and the generated `docs/rules-interaction-checklist.md`.

## Web backend boundary

The WSGI application is read-only with respect to game/reference data. Its responsibilities are to:

- validate/open the release databases;
- compose repository/domain read models;
- enforce query validation and contextual filtering semantics;
- expose JSON APIs and static/browser routes;
- provide revision-aware caching; and
- collect privacy-preserving aggregate operational metrics.

The backend owns semantic composition used by multiple browser consumers: domain routing,
relationship labels/groups, canonical references, Army/faction presentation identities, contextual
filter coherence, and other data meaning should not be reconstructed in JavaScript.

Unknown resources use normal HTTP not-found behavior, unsupported methods are rejected, invalid
query input is a client error, and database read failures must not expose internal exception detail.
Tests are the executable API contract; architecture deliberately does not duplicate every endpoint
payload field.

## Browser boundary

The browser is a progressively enhanced read-only reference client. It owns presentation state,
responsive composition, accessibility behavior, and local user preferences, while semantic data
comes from backend/application contracts.

Current persistent preferences are local browser settings such as distance units, Developer mode,
and optional availability defaults. Shareable page state is URL-owned and must not overwrite the
recipient's saved preferences. A page may seed missing share state from preferences, but explicit
URL state wins for that view. Preference values and persistence are owned by `static/preferences.js`;
the shared Settings controls and their browser events are bound by `static/settings.js`. Page modules
consume preference state but do not initialize or read those shared controls directly. Reusable
distance formatting is separate from both concerns in `static/distance.js`.

Browser JSON access is routed through `static/api.js`, which owns application endpoint shapes and
delegates same-origin request mechanics to `static/api-transport.js`. Transport does not import
preference/UI modules; page modules pass presentation-derived request state explicitly. Page-specific
modules are named for and loaded only by the pages that own them; shell-only or server-rendered pages
must not load an unrelated page module just to obtain shared behavior.

Reusable browser view primitives that encode shared presentation contracts live in
`static/view-components.js`. They own generic behaviors such as mutually exclusive page-state panels
with `aria-busy` synchronization and the canonical table-viewport wrapper; they must not absorb
domain interpretation or page-specific state.

Soft navigation must preserve the shared shell while disposing transient page listeners/requests
before replacing content. Release/static/snapshot revision changes trigger a clean reload rather than
mixing incompatible module/data generations.

Visual/component rules, responsive table behavior, typography, Developer-mode presentation, and
accessibility are owned by `docs/web-design-guidelines.md`.

### Design direction: theming

The current CSS token layer should continue moving toward a first-class semantic theme system rather
than page-local colors or layout exceptions. Light/Dark selection and any later themes are design
direction, not current user-facing behavior. Components must not encode a specific palette as game
semantics. Concrete unfinished theming work is tracked only in `docs/TODO.md`.

## Privacy-preserving observability

Production observability is aggregate-first. InfinityDB may collect bounded metrics such as
normalized-route request counts, status classes, latency/response-size histograms, active requests,
and build identity. Query strings, search terms, IP addresses, user agents, referrers, cookies,
persistent visitor IDs, and other per-person tracking data are not analytics inputs.

The preloaded Gunicorn application uses a fixed-cardinality shared request registry.
`/internal/metrics` and `/internal/health` are not public application routes; the public Caddy site
blocks `/internal/*`. An optional separate Caddy listener may expose only `/metrics` and `/health`
on loopback or an explicitly configured trusted LAN address. Deployment refuses wildcard metrics
binds.

Temporary raw request logging is an incident-diagnostic exception, not the normal analytics path,
and should be minimized and short-lived.

## Determinism, portability, and validation

Supported development/runtime Python begins at 3.11. Maintained tooling supports Windows, Linux,
and macOS; production deployment is Linux/container based.

Persistent generators own canonical bytes: UTF-8/LF text, deterministic ordering and JSON
serialization, normalized archive metadata, and canonical SQLite finalization. Git attributes protect
tracked checksum-bound files from checkout rewriting, but are not a substitute for deterministic
generators.

`tools/run_checks.py` is the canonical local check orchestrator. Hosted CI validates source/build
behavior across supported platforms, compares representative deterministic-output hashes, tests an
installed wheel outside the checkout, and smoke-tests the production container. See
`docs/testing.md` and `docs/ci.md`.

## Deployment architecture

Release tags are self-contained for runtime deployment. A normal server update:

1. resolves the target release tag;
2. hands off to the installer shipped by that target release;
3. checks out the tag;
4. uses the tracked `infinity.db`, `rules.db`, processed SVG publication, and publication manifest;
5. builds/verifies an immutable application image; and
6. activates it while retaining configured rollback images.

Production does **not** rebuild Army/rules databases from raw inputs. Historical upgrade exceptions
and exact operator commands belong in `docs/deployment.md`.

## Documentation ownership

Architecture intentionally does not contain a second backlog, release diary, benchmark history,
endpoint field manual, web-style guide, or data-model audit log. Use:

- `docs/data-model.md` for data semantics and persistence;
- `docs/application-domains.md` for player-facing semantic ownership;
- `docs/web-design-guidelines.md` for browser design contracts;
- `data/README.md` / `data/curated/README.md` for artifact and curation contracts;
- `docs/testing.md` / `docs/ci.md` for validation mechanics;
- `docs/deployment.md` for operations;
- `docs/TODO.md` for unfinished work; and
- `docs/CHANGELOG.md` / Git history for historical implementation outcomes.
