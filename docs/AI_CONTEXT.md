# InfinityDB: AI context

**Project domain:** Project infrastructure

This file is a compact index of **non-obvious current invariants** for coding agents. It is not an
architecture mirror, release diary, or backlog. Before substantial work, use the canonical owners:

- system boundaries and engineering principles: `docs/architecture.md`;
- data semantics/persistence: `docs/data-model.md`;
- application-domain ownership: `docs/application-domains.md`;
- browser visual/interaction rules: `docs/web-design-guidelines.md`;
- curated schemas/review policy: `data/curated/README.md`;
- data/provenance lifecycle: `data/README.md`;
- checks/CI: `docs/testing.md`, `docs/ci.md`;
- unfinished work: `docs/TODO.md`;
- release history: `docs/CHANGELOG.md`.

## Release and planning ownership

Release identity belongs to `pyproject.toml`, the package version, `README.md`, and
`docs/CHANGELOG.md`; active milestone state belongs to `docs/TODO.md`. Do not duplicate either here.
The durable 1.0 definition is the player-data completeness gate in `docs/releasing.md`. Completed
release/audit narrative belongs in the changelog and Git history.

## Core invariants

- Raw upstream data is immutable input. Never rewrite source archives to make normalization easier.
- Ambiguous or unresolved information is preserved and surfaced; it is not silently discarded or
  guessed.
- Maintained aliases/mappings/exceptions belong in validated configuration or curated data, not in
  consumer-specific code.
- Runtime read paths consume materialized application data. They do not reinterpret raw normalized
  tables or working-tree curation on demand.
- Ammunition effect operations belong to reviewed canonical `ammunition:*` facts,
  not to Army source-ID navigation mappings. The initial AP/DA/E/M typed pilot
  is descriptive and non-executable; combined Ammunition components and
  Combined Saving Roll notation are separate source/profile dimensions.
- Combined Saving Roll Criticals are distinct from combined Ammunition
  Criticals. The six reviewed Plasma Hit/Blast profiles have source-exact
  `combined_saving_roll` annotations: one ARM and one BTS roll, plus one
  additional ARM roll for a Critical. Do not infer this from display punctuation
  or transfer it to base `ammunition:*` facts. See `docs/data-model.md`.
- Scenario geometry is maintained semantic data, not diagram pixels. The 1.0 SVG renderer and
  geometry-schema v1 target only the four N5.3 core scenarios. All four core scenario records now
  own their geometry configurations; renderer tests consume those maintained definitions and must
  not maintain a second map-geometry corpus. Semantic point markers retain a `markerType`, whose canonical
  marker metadata may include a physical diameter. N5.3 Domination
  makes the Console diameter rules-relevant by requiring a Console A Marker or same-diameter scenery;
  the ITS token table supplies the explicit 40 mm value. Scenario placement distances are edge-to-edge
  unless a source explicitly names a center/reference point; marker footprint therefore participates in
  “X inches from” placement. Map measurement annotations are reference-based: the renderer derives
  rectangle dimensions, area-size labels, and element-to-table-edge clearances from semantic geometry
  rather than maintaining duplicate numeric measurements. The map API supports `distance_unit=in|cm`;
  inline SVG labels carry canonical inch data attributes and follow the existing in/cm preference
  without a geometry refetch. Table dimensions switch too, but marker diameters remain physical mm.
  Geometry v1 permits asymmetric and multiple Deployment Zone regions and keeps semantic style/marker identities open; SVG renderer
  v1 separately fails closed when it lacks a supported presentation style or canonical marker metadata.
  ITS variation informs extensibility, while ITS-only geometry and the interactive editor remain post-1.0. See
  `docs/data-model.md`.
- Scenario authoring v2 composes shared, explicitly identified Rules/Skills and typed components.
  Export resolves them into self-contained payloads in `rules.db`; runtime must not read curation
  files. Same names do not select/merge definitions. `scope.scenarios` is an explicit activation
  boundary; default core composition excludes scoped records, and scoped records cannot have Army
  links. The shared Specialist baseline uses full Skill-ID arrays plus explicit inclusion deltas;
  rendering consumes resolved qualifiers, not an authoring mini-language. Preserve its Non Specialist
  qualification exception, Annihilation's reviewed-resolution note for the corrected 350-point
  survival bands, and Domination's needs-verification 350-point SWC note. Supplies has no
  placement source issue: its outer Supply Boxes are 8 inches from the table edges at every supported
  game size; the 12-inch mark in the large-table illustration is a guide ruler, not the box offset.
  Stable scenario-set
  identity/revision and source publication revision are separate runtime concepts. Current
  `ScenarioCatalog` detail reads require an explicit supported Army Points value; do not invent a
  default configuration in backend composition. The browser defaults a state-less scenario detail
  visit to 300 Army Points, immediately writes that choice through the common versioned `s=` share-state
  codec, and lets explicit valid shared/legacy state win. Maps render through the canonical SVG endpoint backed by the selected
  maintained geometry. The browser inlines the generated SVG to inherit semantic map colors from
  the current theme; its standalone `<style>` must be removed on injection because of the app CSP,
  with browser styling provided by the external page CSS. Map labels scale with table width without
  changing canonical geometry. Do not recreate scenario geometry or scoring semantics in JavaScript.
  See the scenario model in `docs/data-model.md`.

- Network acquisition is explicit. Normal builds/tests are expected to work without upstream network
  access.
- Persistent generated artifacts are deterministic across supported platforms for the same inputs
  and declared toolchain.
- Slugs are the preferred application-facing identifiers when a domain has a stable slug; numeric
  IDs remain compatibility/provenance forms.
- Browser code renders backend-owned semantics rather than recreating data-model policy.
- Weapon Ammunition navigation maps exact Army metadata identity/name pairs to
  reviewed base reference segments, without client-side parsing or inference from
  Saving Roll notation. The maintained map (version 2) records ordered components
  for the four reviewed combined forms (`AP+DA`, `AP+Exp`, `AP+Shock`, `AP+T2`);
  their API `ammunition_composition` field is only present on exact matching
  source profiles. Alternatives remain unlinked. Curated `ammunitionResolution`
  remains a non-executable, source-cited fact contract: all eleven base
  Ammunition identities are reviewed. PARA's no-PH exception, T2's reduced Wound
  outcome for an *additional Critical roll*, Shock's VITA-1 exception, and Stun's
  Guts/Courage exception cannot be dropped when consuming facts. Smoke/Eclipse
  use separate `facts.visibilityZone` data with distinct MSV behavior; do not
  interpret it as a Saving Roll.
  This is not an effects engine.
  See `docs/data-model.md` and `weapon-ammunition-references.json`.
- Game/reference data is read-only at runtime. Persistent user-authored application data is not part
  of the current model.
- Retained metrics live in a separate private collector with one bounded writable volume; the
  web-facing `app` remains immutable. Collector scrape/start failures do not invalidate a healthy
  application deployment. History migrations are forward-only; rollback preserves the volume and
  older collectors refuse newer formats. The architectural boundary is in
  `docs/architecture.md`; deployment lifecycle, retention, and operator commands are owned by
  `docs/deployment.md`. Do not turn live metrics or retained aggregates into visitor histories.
- Future work belongs in `docs/TODO.md`; do not preserve an obsolete task list in architecture or
  this context file.

## Runtime artifacts

- `data/generated/infinity.db`: tracked Army-derived application runtime database.
- `data/generated/rules.db`: tracked curated-rules runtime database.
- `data/generated/infinity.raw.db`: development/audit archive of normalized source structures; not a
  production dependency.
- `data/manifests/symbol-publication.json`: tracked processed-SVG publication contract and Army
  source binding.
- Raw Army/wiki/PDF/source-symbol archives plus detailed symbol-build state remain local inputs and
  provenance, not deployment requirements.

A release must deploy its tracked runtime databases and processed graphical publication as one
validated set. Production must not substitute a server-side rebuild.

## Army/application identity invariants

- Source IDs are provenance, not a sufficient application ontology. Kobra Pistol
  BS/CC profiles share Weapon source ID `221`; `variantSemantics.sourceMode` enables
  exact-mode curated rules without silently applying CC effects to BS Mode. The
  published Kobra CC reference explains DA Saving Rolls and the unresolved
  Anti-materiel source conflict; it must not be taken as a Trait override.
- `application_armies` is the canonical runtime Army projection. Roles/grouping/playability are
  derived from imported relationships plus reviewed policy, not hard-coded Army ID ranges.
- Canonical source identity `1` is mercenary source provenance; Non-Aligned application grouping is
  distinct (current source grouping identity `901`). Do not merge those concepts.
- Reinforcement Armies retain explicit parent relationships; parentage, grouping, availability, and
  broader faction membership are different relationships.
- `logical_units` groups source Unit representations that InfinityDB has evidence to treat as one
  application Unit. The mapping is materialized at build time and runtime reads reuse it.
- The **General profile** is an InfinityDB application abstraction for source profile data common
  across relevant occurrences. It must not erase materially different source statlines or context.
- Profile and loadout equivalence is semantic and context-aware. Exact source IDs/names remain
  provenance even when application identities merge.
- `main_army_id`, broader faction membership, concrete Army-list availability, and display identity
  are not interchangeable. UI code must consume the backend-projected distinction.
- Unit source notes and composite Unit options remain source/context attributed; do not promote a
  source-local restriction or option bundle into global Unit semantics.
- Peripheral identity, Unit-backed Peripheral mappings, Controller access pools, include
  relationships, selection/dependency constraints, and Fireteam membership are explicit application
  relationships. Do not infer ownership from names.
- Fireteam chart limit sentinels are source encoding, not browser semantics. Preserve the raw limit
  for provenance/compatibility and expose the interpreted limit kind from the backend.

## Query-coherence invariant

Profile/loadout-sensitive Unit filters cannot be satisfied by unrelated occurrences on the same
logical Unit. In particular, AVA is contextual to an Army/profile occurrence, while Points and SWC
are loadout facts. When those constraints participate in a query, other selected profile/loadout
criteria must be satisfiable in the same compatible context. Unit-wide option facts remain Unit-wide
because the source does not attach them to a profile group.

- Unit Explorer source-filter overlays are maintained semantics, not source rewrites. Combined source
  Classifications may match multiple public Classification filters, and redundant source
  Characteristics may be hidden from the picker while remaining preserved/queryable.

## Rules/reference invariants

- Curated rules data is independent from Army data and builds into `rules.db`.
- General Rules is a **published** fallback domain for reviewed `rule:*` categories without a clearer
  owner. Fireteam general rules remain owned by Fireteams; profile notation help remains contextual.
- Ammunition and Labels are published top-level reference domains.
- Attributes and scoped Game terms are published embedded vocabularies: searchable/glossary-visible
  without standalone catalog/detail hierarchies.
- Global search and Glossary are projections across canonical domains, not semantic owners.
- Same visible text may legitimately exist in different semantic namespaces. Preserve kind/domain
  identity instead of merging by label.
- Maintained prose must use typed semantic links for supported reference namespaces. The migration
  is complete: reviewed batches reject newly introduced plain semantic candidates.
- Rule-card summaries use topic/mode paragraphs and inline emphasis; source-history notes belong in
  `facts.sourceNotes`. Cosmetic Army Trait-name differences appear only in Developer Mode, never
  as clutter beside canonical player labels. See `docs/web-design-guidelines.md` for the design contract.
- Gameplay distance presentation uses the Army/rules round-trip convention **2.5 cm = 1 inch**, not
  the SI physical conversion. Preserve Army metric storage, typed maintained-rule distances, and
  the `-1/-1` MOV sentinel (stationary) as distinct semantics; render it as an em dash (`—`) and
  never convert the sentinel as a numeric distance.
- Use `[[review-needed:<reason>|...]]` for genuinely ambiguous maintained prose rather than choosing
  a target without evidence. Reviewed ordinary-text collisions are fingerprinted to exact passages,
  so wording changes reopen review.
- Curated relations are authored once in their semantic direction; reverse navigation is derived.
- Reviewed Weapon-family `facts.variantRuleReferences` link *specific Army Weapon slugs* to
  existing reference rules without inheriting the same effect across every variant.
  The source Weapon Chart profile remains authoritative for ammunition and Saving Rolls.
- `docs/rules-interaction-checklist.md` is generated from the current graph and review ledger. Never
  edit it manually.

## Application-domain and browser invariants

`src/infinity_db/application_domains.py` is the canonical capability registry. Published top-level
application domains are Armies, Units, Skills, Equipment, Weapons, Ammunition, Traits, States,
Hacking Programs, Fireteams, Labels, and General Rules. Embedded vocabularies are Attributes and
Game terms.

Browser state rules:

- JSON APIs keep explicit query parameters.
- Canonical shareable browser state uses the common versioned, scope-bound `s=` token.
- Current token scopes cover Unit Explorer, catalog search, Fireteams, Unit Army targeting, global
  search, and Glossary search.
- Legacy explicit browser parameters remain accepted for compatibility and normalize to canonical
  state; do not remove them casually.
- Post-1.0 sharing must remain self-contained and decodable offline; no server-side
  short-link registry or authored-content persistence. A hash alone cannot recover
  arbitrary shared content. See `docs/architecture.md` (stateless sharing) and
  `docs/data-model.md` (player-authored scenarios). The current `s=` codec is unchanged.
- URL-owned state wins for the current view and must not overwrite persistent local Settings.
- `static/preferences.js` owns preference values/persistence; `static/settings.js` alone binds the
  shared Settings controls. Page modules consume state instead of initializing shell controls.
- Theme preference defaults to System and resolves before first paint through the synchronous
  `theme-startup.js` bootstrap. Theme persistence remains owned by `preferences.js`; Settings owns
  user selection. Do not move theme resolution back into page modules or defer initial resolution
  until after stylesheet paint.
- Soft-navigation page code must dispose transient listeners/requests when content is replaced.
- Browser display should use backend-provided canonical references/relationship labels instead of
  inventing semantic mappings in JavaScript.
- Normal player-facing copy describes Infinity concepts and user-visible outcomes, not InfinityDB's
  storage, pipeline, provenance, or maintainer workflow. Data-review-only surfaces must not be
  discoverable through ordinary player navigation; genuine source uncertainty remains visible but is
  phrased as uncertainty rather than an internal review instruction. `docs/web-design-guidelines.md`
  owns the complete browser-language contract.

Browser visual/layout and copy implementation must follow `docs/web-design-guidelines.md`,
especially semantic table columns, bounded overflow, progressive disclosure, Developer-mode
additive columns, reusable surfaces, player-facing language, and separation of theme tokens from
component geometry.
CSS source ownership is `foundation.css` (font and theme-neutral tokens), one semantic palette file
per explicit theme under `themes/`, `components.css` (shared layout/components), and
`page-overrides.css` (late page-specific exceptions). `/static/styles.css` is a server-composed
stable entry point; do not add a CSS build step or link the source parts directly from page templates.

## Snapshot and symbol invariants

- Snapshot provenance distinguishes logical content SHA-256 from exact archive SHA-256;
  `data/README.md` owns the current provenance format and compatibility details.
- Army provenance records `source.dataChangedOn` separately from acquisition time. Player-facing
  freshness uses the source-data change date; acquisition time is provenance.
- Snapshot archives normalize member metadata/order and are deterministic for identical inputs.
- `tools/build_symbols.py` is the maintained symbol orchestration entry point. Local build state is
  resumable/forward-only; final production publication is represented by the tracked publication
  manifest, not by terminal local build state.
- Peripheral-only profile artwork publishes under
  `peripherals/<main-army>/<peripheral-name>.svg`; when one physical symbol proves that a profile
  name is used in both Peripheral and normal Unit contexts, that mixed-role name stays Unit-owned
  in every context. Source-reused parent Unit artwork also stays Unit-owned, while distinct
  same-name Peripheral-only artwork is retained as contextual variants.
- `unitProfileLogoToPublishedPath` is occurrence evidence, not an override-only table: retain every
  authoritative Army profile-logo resolution so logical-Unit consolidation can still distinguish a
  genuine General-profile symbol from the Unit fallback.
- Image overrides replace an upstream symbol identity within the same symbol category, not only
  one URL occurrence. Exact upstream-equivalent assets inherit the same override; conflicting
  non-identical overrides for one upstream identity fail acquisition. The build manifest retains
  `upstreamSha256` separately from the effective asset SHA-256 so this equivalence survives caches.
- The processed SVG publication is redistributable under Corvus Belli's explicit non-commercial
  permission but remains outside InfinityDB's MIT license.

## Validation and release invariants

- Use the project virtual environment when available.
- `tools/run_checks.py` is the canonical local orchestrator. For ordinary patch work, focused tests
  are appropriate; the full release gate is run explicitly by the maintainer/CI when required.
- Required hosted CI covers source/build checks, cross-platform deterministic outputs, installed
  wheel behavior, and deployment smoke. See `docs/ci.md` for current workflow/ruleset details.
- A release requires a project-wide documentation audit, release-matched runtime artifacts, hosted
  checks green for the exact release commit, an immutable version tag, and post-deployment smoke
  verification where deployed.
- Hosted release evidence is retained without mutating the validated release commit: prepare the
  exact-commit workflow evidence after CI is green, then create an annotated `v<version>` tag whose
  message records the required GitHub Actions run identities/URLs. Lightweight release tags do not
  satisfy the release-evidence contract.
- `scripts/install-or-update.sh` hands off to the installer from the target release before checkout.
  Historical upgrade exceptions and operator commands are owned by `docs/deployment.md`.

## Change discipline

When a change alters a durable contract:

- update the canonical owner, not every document that happens to mention the topic;
- keep `AI_CONTEXT.md` to non-obvious invariants and links;
- add unfinished work only to `docs/TODO.md`;
- add meaningful user/operator outcomes to `docs/CHANGELOG.md` under `Unreleased` during normal
  development;
- update README only for public capabilities/setup/major workflow changes; and
- prefer a small explicit compatibility layer to silently breaking old identifiers, URLs, or source
  artifacts.

For repository-wide agent workflow and write-safety rules, see `AGENTS.md`.
