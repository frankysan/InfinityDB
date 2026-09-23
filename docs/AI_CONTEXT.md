# InfinityDB: AI context

Use this document to orient substantial changes. It records durable non-obvious
project decisions, implementation constraints, and historical choices that help
agents work consistently without duplicating the canonical architecture or data
model.

## Documentation hierarchy and status

- `AGENTS.md` contains immediate repository-wide instructions for coding agents.
- Root-level `AGENTS.local.md`, when present, contains intentionally Git-ignored
  user-specific workflow/preferences for that checkout. It is non-authoritative
  for project design and must not replace tracked repository decisions.
- `docs/architecture.md` is authoritative for architecture, engineering
  principles, subsystem boundaries, data-path roles, and lasting design
  direction.
- `docs/data-model.md` is authoritative for normalized data semantics and
  persistence structure.
- `docs/rules-semantics.md` records audited, implementation-relevant game-rule
  semantics and the maintained source/audit baseline. `docs/rules-research.md`
  holds verified findings without a current application consumer.
- This document records non-obvious constraints and decision history that are
  useful during implementation.
- `README.md` is the user-facing project introduction, setup, and operations
  guide.
- `docs/TODO.md` is the maintained backlog of unimplemented work.
- `docs/CHANGELOG.md` records released and unreleased changes.

Before changing a boundary or persistence behavior, read
`docs/architecture.md` and `docs/data-model.md`. Do not maintain a competing
copy of their principles here.

Status must remain explicit. Unqualified descriptions in this document should
refer to current constraints/behavior. Accepted but unimplemented choices are
marked **Design direction**. The decision log may record an accepted decision
before implementation, but the current sections and `TODO.md` remain
responsible for implementation status.

## Semantic provenance rule

Army source material is army/list-local; InfinityDB combines those contexts into
a game-wide model. Never silently promote a representative Army occurrence into
a global fact. Distinguish source-native facts, source-derived facts, InfinityDB
abstractions, and presentation conveniences as defined in `docs/architecture.md`;
`docs/data-model.md` owns their concrete data semantics.

`logical_unit` and the browser's `General profile` are InfinityDB abstractions,
not upstream Army objects. `General profile` is currently synthesized in the
browser from enabled source-backed profile/loadout contexts. `main_army_id` is a
source-derived grouping/application field, while `display_army_id` /
`display_faction` are presentation conveniences. None of those fields may by
itself establish game-wide ownership, army membership, availability, playability,
or canonical equality. Any new or changed InfinityDB abstraction must document
its source inputs, derivation, assumptions/fallbacks, and limits.

## Purpose and subsystem boundaries

InfinityDB builds validated local reference databases from Infinity source data
and serves a read-only browser and same-origin HTTP API.

- `infinity_army_data` interprets, merges, normalizes, and validates Army source
  data independently of the database/web application.
- `infinity_db.database` owns Army SQLite storage and repository queries.
- The separate rules-reference database is built from validated curated rules
  collections, not from raw PDFs or wiki snapshots.
- Trait rule identity is owned by curated `trait` records in `rules.db`: Army
  storage preserves raw trait labels/usage, and the application composes them
  with curated canonical names, aliases, parameterized prefixes, summaries, and
  citations. If `rules.db` is unavailable, raw traits remain usable without
  invented canonical rule knowledge.
- `infinity_db.web` validates HTTP input, serializes repository results, and
  contains the native-module browser UI.
- Read-only application/runtime imports must not pull build-time normalization or
  maintained source-policy configuration merely to open an already-built
  database. Production runtime remains independent of source-checkout `config/`
  paths. Supported installed build/ingestion CLI commands resolve the same
  tracked identity/catalog/anomaly configuration from
  `<sys.prefix>/share/infinity-db/config/` when no source checkout is present.
- Standalone acquisition and processing tools remain explicitly invoked and
  independently testable. Normal builds and tests must not acquire network data
  unexpectedly.
- Deployment remains separate from acquisition, normalization, database
  construction, rules curation, and asset processing.
- Server migration distinguishes exact runtime transfer from rebuildability.
  Exact runtime preservation copies the generated databases, terminal symbol
  build manifest, and complete local published symbol inventory on the same Git
  revision; reproducible rebuilds
  additionally preserve immutable Army/SYMBOLS snapshots, generated provenance,
  `army-symbol-build.json`, and local overrides. Cross-machine SVG regeneration
  is not promised byte-identical because fonts and external processor versions
  remain environment-sensitive; see `docs/server-migration.md`.
- Local tests separate hermetic and full-asset coverage explicitly.
  `run_checks.py --assets off|auto|required` validates the complete generated
  publication inventory (`symbol-inventory.json`, path + SHA-256 for every
  published SVG) before enabling `full_assets`; it separately reports the
  browser-referenced subset derived from current mappings/endpoints. Direct
  pytest is hermetic by default. `auto` may fall back only when the asset tree
  is entirely absent, never when it is partial/corrupt.
  Test stages use pytest-xdist `worksteal` scheduling with `--test-workers auto`
  by default; `--test-workers 0` forces serial execution for debugging. Windows
  benchmarking measured 687 tests at 59.67 s serial, 19.41 s with four workers,
  and 14.13 s with automatic worker selection. Web tests build one template
  database per module and copy it per test so mutating tests remain isolated
  without repeating normalization/export work.
- GitHub `Source checks` is configured to run hermetic checks on clean Windows,
  Ubuntu/Linux, and macOS Python 3.11 runners for pull requests, pushes to
  `main`, and manual dispatch, plus a Linux Python 3.14 compatibility leg. It
  uses the tracked synthetic Army fixture rather than live acquisition or ignored
  graphical assets. Ubuntu/Python 3.11 owns the complete pytest/Ruff/Pyright/
  build/rules gate; the other matrix legs retain pytest plus Army/rules build
  compatibility coverage without repeating lint/type checks. Hosted Windows
  Actions explicitly uses serial pytest (`--test-workers 0`) because automatic
  xdist workers caused a severe runner-specific slowdown; the local default
  remains `auto`. VS Code is configured for workspace-wide diagnostics. GitHub's
  active `Protect main` ruleset requires pull requests,
  resolved review threads, the four source-check matrix jobs,
  `deployment-smoke`, and `installed-wheel` to be current and passing before
  `main` can advance; it also blocks deletion/non-fast-forward updates and has no
  bypass actors.
- `Installed wheel smoke` is configured to build and install the wheel in a fresh virtual
  environment, validates installed `infinity-db` / `infinity-army` build commands
  and maintained config resources, then opens the generated Army/rules databases
  through the runtime application outside the checkout.
- `Full-asset checks` is configured as dispatch-only, restricted to `main`, and stages a private
  checksum-pinned published-asset ZIP from the existing `full-assets` GitHub
  environment before running `run_checks.py --assets required`. It does not
  upload the graphical tree as an artifact, and it intentionally does not rerun
  the network/external-tool-sensitive symbol pipeline from raw inputs. The
  environment exists, but its authorized bundle URL/digest secrets still must be
  configured before the manual job can succeed. See `docs/ci.md`.

## Non-obvious Army data invariants

- Preserve the merged master document losslessly. The normalized layer is
  relational/query-oriented but retains source identities and relationships
  needed for validation and display.
- Unit IDs are global; nested profile, profile-group, and loadout IDs are only
  unique within their army/unit hierarchy. Use the established composite keys.
- Retain source-undefined references as explicit placeholders rather than
  silently discarding them.
- Valid Army API `metadata.json` is required for database creation. It enriches
  catalogs, names, and faction hierarchy but must not create army membership or
  alter source-derived availability.
- Army-list occurrences are authoritative for concrete list membership and
  availability. List presence, grouping, list kind, source canonical/origin
  context, broader declared faction membership, optional availability category,
  and playability are separate semantics.
- The identity configuration does not map canonical-faction source ID `1` to
  `901` as ownership. Normalization preserves ID `1` as mercenary source/origin
  provenance and explicitly leaves `main_army_id` unset for canonical-1 units;
  901 remains the distinct Non-Aligned Armies grouping identity. A separate
  reviewed relationship in `data/curated/identities/army-display.json` derives
  `display_army_id` for presentation; the provenance-only canonical reference remains
  numeric `1`, while the display target is authored as source slug
  `non-aligned-armies` and resolves to 901.
- Source investigation shows ID `1` and ID `901` represent different concepts.
  ID `1` behaves as a mercenary source/origin identity with no army list and no
  ordinary faction membership role; 901 is the Non-Aligned Armies grouping
  identity for distinct child army lists. They must not be conflated.
- Ordinary unit records declare normal faction availability in `factions`.
  Dedicated optional-mercenary source variants consistently use
  `canonical: 1`, an empty `factions` list, a `merc-...` slug, and army-specific
  occurrences that add optional availability. Many use a 10,000-offset-style
  source ID, but numeric offset is diagnostic evidence only, not the semantic
  rule.
- Current normalized snapshots persist generic standard duplicate-unit matches,
  mercenary-to-standard source-unit matches, and explicit
  `army_units.availability_kind`. Database creation consumes the persisted
  identity evidence and materializes `logical_units` / `logical_unit_sources`;
  repository reads consume that relation, while mercenary filtering uses explicit
  availability provenance. The 10,000-ID generic grouping rule remains only as a
  builder compatibility fallback for older normalized inputs without
  `genericUnitMatches`.
- 901 (Non-Aligned Armies) is a non-selectable grouping identity for its child
  9xx armies **and** a real imported Army source list with its own roster. Current
  metadata has `901.parent = 900`; playability must not be inferred from source-list
  existence or roster presence. InfinityDB intentionally has no separate 901
  roster-query surface: preserve that roster as source provenance and consume unit
  availability through the playable child NA2 lists. This endpoint policy does
  not remove 901 or its relationships from the game-wide model.
- The analyzed snapshot gives source list 901 one standard unit (Rumbler
  Spec-Ops) plus the complete 49-variant optional-mercenary pool. Child NA2 lists
  have their own standard rosters plus subsets of that pool.
- The merger's current `army_lists.kind` is derived from source shape: ordinary
  documents containing `reinforcements` become `army`, while reinforcement
  documents without it become `reinforcement`. It is not a source-provided
  main-army/sectorial taxonomy.
- Army metadata parent relationships carry useful grouping semantics: standard
  main armies are self-parented, sectorials point to their main army, and NA2
  forces point to grouping identity 901. Ordinary list documents explicitly
  reference their reinforcement list through `reinforcements`.
- Current InfinityDB normalization also uses that metadata parent relationship
  to derive unit `main_army_id`. Explicit maintained canonical-faction overrides
  take precedence; the old `xx01` calculation is retained only for standalone or
  legacy normalization inputs without a usable metadata row for that canonical
  faction. `main_army_id` is derived grouping/application context, not an
  authoritative game-wide ownership or membership relation.
- The backend/API exposes explicit army role/playability semantics derived from
  metadata parent relationships and ordinary-list `reinforcements` links.
  `/api/armies` distinguishes main armies, sectorials, Non-Aligned forces,
  reinforcement lists, and grouping identities; the browser selector
  consumes that contract rather than Army-ID ranges. Grouping identity `901` is
  non-playable.
- Rules semantics refine the `reinforcement` application role: the linked
  identity represents a faction-shared Reinforcement Section/pool attached to an
  ordinary Army List, not a standalone legal Army. For reinforcement rows,
  `playable` means application/browser selectability; preserve the parent Army
  relationship and section-specific profile/AVA occurrence context when
  canonicalizing or presenting the data.
- Mercenary variants are classified during normalization, their source markers
  are validated, audited mercenary-to-standard mappings are persisted, and
  repository queries consume explicit availability provenance. Generic standard
  duplicate matching is also audited and persisted during normalization.
  Database creation additionally persists unambiguous reinforcement-to-standard
  matches using the pinned name-normalization policy. Repository queries do not
  rediscover generic, mercenary, or reinforcement identity at query time.
  Frontend database creation resolves configured aliases
  plus persisted generic, mercenary, and reinforcement evidence into explicit
  `logical_units` / `logical_unit_sources` relations. Source rows remain
  unchanged; every source unit maps to exactly one logical unit, and repository
  reads consume that materialized mapping rather than rebuilding identity
  dynamically. Introduced in schema version 14 / compatibility revision 22, the
  canonical layer materializes representative-backed logical-unit fields plus
  source-attributed
  alias/note/`spectables` context, as well as reusable canonical profile and
  loadout payloads scoped to each logical unit plus one occurrence row per
  source profile/loadout. Profile AVA/logo and loadout points/SWC remain
  occurrence context; source/profile-group keys, includes, and peripherals
  remain occurrence/source context; WIP, characteristics, skills,
  equipment, weapons, extras, and exact representation values remain in the
  payload and therefore split payload variants when they differ. Unit-detail
  profile assembly and normal skill/equipment/weapon search/filter/catalog usage
  now read the canonical profile payload/occurrence layer. Source profile tables
  remain lossless provenance/context for build validation and audit, not normal
  serving. Logical-source profile
  occurrence merging remains separate from canonical payload identity:
  occurrences may collapse only when their effective army occurrence,
  source-local group/profile coordinates, scalar profile facts, type, and
  classification agree; complementary nested items are accumulated and
  restrictive numeric AVA is retained. A canonical payload ID must not be used
  as source-occurrence identity. The loadout materializer follows the same
  logical-unit-scoped, exact-payload approach: `name`, `minis`, `disabled`,
  characteristics, orders, skills, equipment, weapons, extras, and exact
  representation values belong to the reusable payload; points, SWC,
  source/group/option keys, source position, includes, and peripherals remain
  occurrence/source context. Includes and peripherals are deferred because their
  targets are source-local/army-local. Unit-detail loadout assembly now reads
  the canonical loadout payload/occurrence layer while retaining the existing
  logical-source occurrence merge semantics. Normal loadout-name search and
  skill/equipment/weapon search/filter/catalog usage also read the canonical
  payload/occurrence layer; source loadout tables remain lossless provenance/context
  for build validation and audit, not normal serving. Canonical payload identity is
  deliberately not used
  as logical-source occurrence identity because overlapping source records can
  contribute complementary nested loadout relationships. Current production
  evidence shows 31 logical-source loadout occurrence merges and all pairs already
  share one canonical loadout payload; the merge remains occurrence reconciliation,
  not payload identity. Canonical profile/loadout occurrence tables require
  unit-oriented indexes because unit-detail assembly filters them by source unit.
  The logical-unit field audit on the 2026-09-18 production snapshot maps 920
  source-defined units to 737 logical units, including 167 multi-source logical
  units. All 737 representatives are ordinary standard source units; none is a
  reinforcement-only or mercenary-variant row. That representative rule may
  govern canonical display/general fields, but it does not erase source context:
  every multi-source logical unit contributes alternate searchable labels, six
  have source-note variation, and four have a player-facing note only on a
  non-representative reinforcement row. Source faction/Army relationships and
  top-level unit options remain contextual. `spectables` is populated on 30
  source units but only singleton logical units in this snapshot, so it must be
  preserved while its canonical/presentation treatment remains unresolved.
  Schema version 14 materializes representative-backed `name`, `isc`,
  `isc_abbr`, `slug`, `canonical_faction_id`, `main_army_id`, and
  `display_army_id` on the application-owned logical-unit row. The three faction/
  army fields retain contextual/derived/presentation semantics; their placement
  does not make them canonical game-wide relationships. Every source mapping stays
  explicit; non-representative differing labels are source-attributed aliases;
  every non-empty source note remains source-attributed context; and `spectables`
  is preserved as exact opaque source context rather than promoted from
  singleton-only evidence. Top-level `unit_options` remain separate source-context
  payloads and source-local `option_id` is not canonical option identity. A clean
  rebuild of the 2026-09-18 normalized source materializes 737 canonical rows,
  920 source links, 473 alias occurrences (468 distinct logical-unit values), 30
  note occurrences, 30 `spectables` occurrences, and leaves 18 top-level
  unit-option rows contextual. The extra alias preserves the existing derived
  `Unit <source id>` search name for the one non-representative source row whose
  raw name is absent. Unit list/search/detail general fields and unit-label
  search now read the canonical logical-unit layer; source unit rows remain for
  relationships and other runtime paths that have not yet been canonicalized.
  Legacy rediscovery remains only as a database-build compatibility path for
  older normalized inputs.
- The 0.6.1 runtime-surface audit uses SQLite authorizer tracing plus static
  direct-method coverage of the web/catalog helpers. After replacing redundant
  profile/loadout/unit source reads, migrating Army/faction serving to the
  materialized application Army layer, and materializing canonical application
  catalog identities for skills/equipment/weapons, the same 25 probes read 49
  tables / 196 distinct fields: 111 canonical-application fields, 62
  contextual-application fields, and 23 intentional-source fields. No
  replaceable-source or semantic-overlap issue remains in the normal runtime
  surface. Normal serving no longer reads `metadata_factions`,
  `metadata_skills`, or `metadata_equipment`; `army_lists` remains only for its
  source-shape `id`/`kind` compatibility semantics. Fireteams,
  relation/dependency tables, includes/peripherals, and other currently unserved
  source structures are outside the 0.6.1 gate unless later runtime work
  introduces a dependency.
- The 0.6.1 army/faction audit makes the scope boundary explicit: Infinity Army
  is list-local, whereas InfinityDB is game-wide. The reviewed snapshot has 58
  overlapping `army_lists` / `metadata_factions` IDs with identical name/slug
  values, but their semantics differ; reviewed Army aliases produce 57 canonical
  application army identities. `army_units` is concrete list availability, while
  `unit_factions` is a broader declared cross-Army membership relation. Representative
  faction/main/display copies on `logical_units` remain contextual/presentation values
  despite residing on an application-owned row. The latter
  preserves 99 references across 89 source units to faction IDs 203/903/906/907
  that have no current Army list. Source `canonical_faction_id` is origin/context,
  not ownership or availability. Schema version 17 / compatibility revision 25
  now contains the canonical application Army identity/hierarchy as an
  InfinityDB abstraction in `application_armies`, `application_army_sources`,
  and `application_army_reinforcement_parents`. It stores canonical name/slug,
  role/playability/grouping, reviewed source-ID mappings and preferred-source
  provenance, plus explicit reinforcement-parent relationships. Skills,
  Equipment, and Weapons now likewise materialize canonical application catalog
  identities and source mappings in `application_catalog_items` and
  `application_catalog_sources`, while preserving source-specific labels and
  weapon/equipment profile metadata as contextual data. The broader 63-ID
  faction registry, `army_units`, `unit_factions`, and both source projections
  remain separate. Normal serving now consumes the materialized Army and catalog
  layers for application identity/hierarchy, alias resolution, playability,
  faction/group presentation, and catalog detail/list serving without
  collapsing those contexts.
- Skills, Equipment, and Weapons application identities are InfinityDB
  abstractions materialized from normalized catalog rows, reviewed catalog alias
  groups, and metadata enrichment. Catalog identity slug references resolve against
  the complete source metadata catalog plus currently used rows; reviewed
  per-catalog slug aliases may correct upstream spelling at the identity-authoring
  boundary without rewriting raw provenance. `application_catalog_sources` preserves
  each
  contributing source ID/label; detailed `metadata_weapons` modes and profiles
  remain contextual rather than being promoted to invariant catalog facts.
- `tools/benchmark_runtime.py` is the canonical repository-read benchmark for the
  0.6.1 performance gate; `tools/compare_runtime_benchmarks.py` compares archived
  reports. The same-host/same-snapshot 0.6.0-to-0.6.1 release run improved the
  geometric mean of cold medians by 2.33% (Army listing -43.94%, Army-filtered
  units -11.68%) while the cold-p95 geometric mean was effectively flat (+0.52%).
  The audited application database grew 13,557,760 -> 18,108,416 bytes (+33.56%)
  while materialized application layers and retained source/context rows coexist.
- SQLite Army imports replace a complete snapshot. Future user-authored data
  must remain separate from that replaceable imported state.
- Nested queryable values may remain JSON in the frontend DB; exact normalized
  rows, including absent-versus-null distinctions, are preserved in the sibling
  raw archive.
- Increment `DATABASE_COMPATIBILITY_VERSION` whenever existing generated Army
  databases must be rebuilt, even if the SQLite schema version is unchanged.

## Snapshot acquisition and provenance

### Current

- Army, wiki, and symbol downloaders stage loose files temporarily and persist
  complete timestamped `JSON`, `WIKI`, or `SYMBOLS` ZIP snapshots. Same-second
  name collisions receive `-2`, `-3`, and so on rather than overwriting.
- Raw snapshot archives are immutable after successful acquisition.
- Wiki acquisition fails closed for required content but excludes optional site
  chrome/project targets (`/favicon.ico` and the `Infinity:` project namespace)
  from completeness. Failed/incomplete wiki runs publish no immutable snapshot
  or provenance and preserve their local crawl work under `data/work/wiki/`;
  successful runs remove that work directory after publication.
- Each successful acquisition writes a version-1 generated provenance record
  under `data/manifests/snapshots/`, labeled from the archive filename and
  bound by its immutable SHA-256.
  The record stores snapshot type, archive identity, acquisition time, source
  URL, document count, optional language, and optional input-artifact identity.
- Generated manifest paths are project-relative POSIX paths when the file is
  inside the project root; machine-specific absolute paths are never persisted.
- Generated snapshot manifests are ignored by Git, excluded from Docker build
  context, and retained until explicitly removed. Rewriting different
  provenance for an existing archive-labeled record fails. Identical bytes
  reacquired under a different archive label may have another manifest with the
  same authoritative SHA-256.
- Human-authored snapshot descriptions, comparison targets, and notable-change
  notes use the separate version-1 contract under
  `data/curated/snapshot-notes/`, also keyed to snapshot SHA-256. Acquisition
  tooling must never modify that subtree.
- Corvus Belli's Army `metadata.json` remains source data, not project-generated
  snapshot metadata.
- Army JSON `version` is per-document source provenance, not a snapshot-wide
  version. Observed values support interpreting the middle component as
  two-digit year + ordinal day and the final component as a same-day data
  revision/build, but that interpretation is not a documented upstream
  contract. Preserve the raw value. Legitimate snapshots may contain multiple
  source revisions; distinguish those from InfinityDB `acquiredAt` provenance.
- Army snapshot coherence is verified independently of those revision strings.
  `download_army_json.py` performs two complete passes over metadata and every
  Army/reinforcement endpoint, requires byte-identical responses between passes,
  and writes snapshot files only after verification succeeds. A changed endpoint
  aborts the acquisition rather than publishing a potentially torn snapshot.

### Design direction

- Future comparison tooling may emit structured generated diff/report data while
  curated snapshot notes remain human interpretation.
- Persistent generated project paths should remain portable and case-sensitive
  internally; detect case-only collisions before publishing.

Current curated wiki provenance predates the timestamped ZIP lifecycle. Do not
invent exact archive/hash associations for legacy wiki references. Migrate them
when the wiki downloader/packager and curated provenance contract are rewritten
together.

External executable discovery should use explicit configuration/shared discovery
helpers/`shutil.which()` rather than fixed installation paths. Subprocess-heavy
tools use argument lists, not shell command strings, and process-based
concurrency must remain safe under the Windows `spawn` model.

## Symbol pipeline

### Current

Downloaded Corvus Belli graphical assets remain outside the public repository
unless redistribution permission clearly allows inclusion. Local corrected
image overrides likewise remain ignored unless redistribution status changes.

Army-symbol acquisition is now source-semantic and URL/reference based.
`tools/download_army_symbols.py` discovers every
`units[].profileGroups[].profiles[].logo` plus every
`metadata.json -> factions[].logo`, includes validated maintained static-symbol
declarations, and treats `resume[].logo` as audit-only. A recursive scan of all
source strings fails closed on SVG-bearing fields that are not reviewed semantic
or audit-only locations. A unit may reference several SVGs and several source
references may share one URL; every reference is preserved while each
authoritative URL is downloaded only once.

`tools/build_symbols.py` is the normal orchestration entrypoint for symbol
refreshes. A new build requires either an explicit immutable Army ZIP
(`--snapshot`) with matching generated snapshot provenance or an explicit
network refresh (`--fetch-snapshot`); it never selects a newest snapshot
implicitly. Normal console output is compact and stage-oriented: an interactive
active stage updates one progress line, while the complete verbose transcript is
retained in a timestamped `data/logs/symbols/` log (or an explicit `--log`
path). `--stop-after` exposes every verified stage checkpoint from snapshot
through publication. Once acquisition has created version-2 build state,
`--resume` continues from that exact SHA-bound Army/SYMBOLS pair without
rediscovery or reacquisition. Resume validates the existing raw work tree instead
of rematerializing later-stage work; only version-2 state may reconstruct a
missing raw work tree. For an external Army ZIP whose portable path is not in
the build manifest, supply the same archive again with `--resume --snapshot`.

The raw symbol resolution stage creates one immutable `SYMBOLS ...zip`,
ordinary snapshot provenance, and acquisition-only version-2
`data/manifests/army-symbol-build.json`. That state separates raw assets from
consumers, records Army/SYMBOLS artifact hashes, persists the verified Army
source pin, and records raw asset URL/archive/hash/source-method plus all source
references and discovery counts. The orchestrator then verifies the selected
symbol archive/provenance and every member hash, replaces a derived work tree
under `data/work/symbols/`, and writes a deterministic structural SVG preflight
under `data/reports/symbols/`. The preflight records XML/SVG parse validity,
active-text/text-object counts, and declared font families, promoting build state
to version 3. The next installed-font audit resolves effective text fonts using
the existing CSS/font matcher plus validated tracked aliases from
`config/symbols/font-aliases.json`; it reports available, missing, ambiguous, and
generic references, alias normalization, and unused declarations, then promotes
state to version 4 while binding the audit report and alias-config hashes. Missing
or ambiguous fonts fail orchestration before deduplication/conversion. The
orchestrator then runs exact-first visual duplicate detection with the established
renderer/ranking policy and promotes passed state to version 5. Version-5 state
retains every original asset/reference and adds a complete portable
`archivePath -> canonical archivePath` map plus duplicate report identities,
renderer settings, and total source/canonical loose-SVG byte sizes with reclaimed
bytes. The bound duplicate summary also reports percentage reduction. Individual
render failures remain unique and are reported. Canonical text conversion then
promotes state to version 6: only canonical `fonts_available` SVGs are converted,
canonical no-text SVGs are carried forward unchanged, persistent
`inkscape --shell` is the production default, one-shot Inkscape remains an
explicit fallback/debug backend, and `usvg` remains experimental. Conversion
reports and converter identity are SHA-bound into build state.
Normalization removes unresolved local `<image>` references only from temporary
conversion copies and reports those removals; raw snapshot SVGs remain
unchanged. This is a reproducibility invariant: missing raster references must
not be rebased through randomized temporary directories into canonical or
published SVG bytes. Failed conversion
state is recorded without replacing the prior canonical work tree. Compression
then promotes passed version-6 state to version 7 using the reusable standalone
compressor: balanced profile, resvg validation, p2-first/p3-rescue precision,
32/64 CSS-pixel targets, DPR 1/2, RMS and changed-fraction limits 0.01, and
pixel-difference threshold 8. The complete compressed tree and three compression
reports are validated before atomic promotion. Final publication then consumes the
same pinned Army snapshot, version-7 compressed tree, and authoritative build
manifest; it generates the application asset tree plus `army-symbols.js` and
`unit-symbol-map.js`, writes a complete source/canonical-to-published mapping, and
promotes passed state to version 8. Loaders accept versions 2 through 8 as valid
historical/intermediate state, and earlier version-5 state without size metrics
remains compatible. Promotion helpers are intentionally forward-only: preflight,
deduplication, compression, and publication accept only their immediate source
version, while failed-stage retry is explicit rather than implemented by silently
demoting later passed state. Version 8 is terminal published state. The downloader
still does not generate browser mappings; only the publisher does.

Raw source resolution now follows this implemented order:

```text
matching local override
    -> exact-URL entry from the prior validated immutable symbol snapshot/cache
    -> upstream network
```

Local overrides live under ignored `image_overrides/<category>/` paths using
stable source-derived names. The prior current build manifest indexes the cache;
its referenced symbol archive/provenance and selected member hash are validated
before reuse. `--refresh-symbols` bypasses the prior symbol archive cache but
does not bypass a matching override. An invalid matching override is an error,
not a reason to fall back upstream. Unused overrides and URL/filename collisions
are reported.

### Publication boundary

Symbol publication consumes the same pinned Army/SYMBOLS identities and the
verified version-7 compressed work tree rather than selecting newer snapshots
independently. The publisher alone assigns final application paths and generated
`army-symbols.js` / `unit-symbol-map.js` mappings because only publication knows
the final canonical asset after deduplication/conversion/compression. Successful
publication is version 8 and binds the complete source-to-published mapping plus
the generated browser maps into build state. Unit source profile slot
`profileGroups[0].profiles[0]` retains the stable unsuffixed unit path used by
`unit-symbol-map.js`; distinct later profile slots use deterministic one-based
`--<group>-<profile>` suffixes. Distinct non-owner-army artwork is namespaced
with `--army-<army-id>` before any profile suffix, while exact duplicates continue
to share one canonical published file.

The established processing direction is `resvg` for visual duplicate and
compression validation, persistent `inkscape --shell` workers for text-to-path
conversion, and standalone reusable stages wrapped by a thin orchestrator. The
roughly 8-9 second Windows Inkscape startup cost is an accepted external-tool
limitation; persistent workers are the intended mitigation. Do not restart
startup profiling without new evidence.

## Curated rules-reference constraints

### Current

Raw PDF and wiki research material is not an application input. Human-reviewed
rules collections live under `data/curated/rules/`; `infinity-db build-rules`
defaults to that subtree and does not ingest sibling curated categories.

Current local reference families include N5 core rules revisions, N5 FAQs, ITS
season/historical material, and wiki research. Keep core rules, FAQ/errata
rulings, ITS seasons, historical sources, and wiki-derived material explicitly
scoped so a view cannot silently combine incompatible versions.

PDF source records retain the local reviewed file and the official upstream
source URL; PDF citations use printed pages. Archived wiki sources retain exact
ZIP/hash, acquisition timestamp, language, document count, and base URL;
citations use archive members. Exact pinned `oldid=` wiki revisions remain
URL-backed sources with retrieval dates. The checked-in N5 v5.3 collection uses
the authoritative English `WIKI-en 20260918-130233.zip` snapshot.

The wiki downloader is fail-closed for required content, language-scoped, and
preserves incomplete work for inspection without publishing a snapshot.

The current curated-v16 rules contract includes collection/source metadata,
maintained `skillTypes` and `labels` vocabularies with source-specific
`vocabularySources`, typed record contributions, Army links, typed related-record
edges, composition role, review state, exact-source variant semantics, and citations.
Older formats must be migrated before ingestion. The
reserved `rules/example.json` template is excluded from directory ingestion.

The rules database has its own schema/versioning and replacement lifecycle. It
must not import Army JSON data, and Army database construction must not import
rules data. Application/service code may combine the two only through stable
application-level identities. For `armyLinks`, Skill, Equipment, and Weapon IDs may be
positive numeric source references or application-domain slugs; the checked-in N5 rules
use slugs. `rules.db` preserves the authored value and composition code matches it to
the current Army application identity. Numeric-looking strings are rejected so numeric
compatibility references remain unambiguous JSON integers.

## API and UI constraints

- API routes are same-origin and read-only. Validate request input at the HTTP
  boundary and do not expose internal exceptions.
- Prefer additive response changes; do not silently repurpose existing fields.
- Army filtering uses actual `army_units` occurrences, not canonical faction
  references.
- **Design direction:** Army selectors should use explicit backend-provided
  role/playability semantics rather than treating every imported list identity
  as selectable.
- Search/display ordering is case-, accent-, and punctuation-insensitive.
- Browser requests belong in `api.js`; shared unit rows in `unit-list.js`;
  page-specific rendering/state in the corresponding page module.
- Frontend database data is immutable for a running application instance.
  Snapshot-aware ETags and `/api/version` distinguish new imported data from an
  application release.
- Every browser route uses the shared server-rendered page shell. New static
  page documents retain the navigation/header/footer markers expected by
  `_page()`.
- Shared menus use the inline-sidebar / compact-topbar pattern.
- User-selected browser settings persist for the current tab/session through
  `sessionStorage`; values loaded from persistent cookies must be mirrored into the session
  store before use. The **Remember settings** consent path additionally mirrors values to
  one-year SameSite cookies for later sessions; turning persistence off removes those
  cookies but must not reset current-session choices.
- `styles.css` is the design-system source of truth. Reuse established tokens,
  surfaces, table density, detail-group primitives, and badges rather than
  adding page-local equivalents.
- Developer mode is default-off. Technical inline fields use `.developer-only`
  and ID table columns use `.id-column`.

## Style and change discipline

- Target Python 3.11, four-space indentation, and Ruff rules `E`, `F`, `I`,
  `UP`, `B` with 100-character lines except reviewed SQL strings.
- Prefer explicit small functions and clear transformations over clever
  abstractions. Preserve source field names unless a deliberate mapping is
  documented.
- Update focused tests with behavior changes. Standalone scripts in `tools/`
  require dedicated regression coverage for filesystem/URL/portability logic.
- Run substantive Python tests/lint through the project virtual environment,
  preferably via `<venv-python> tools/run_checks.py --profile code`; the default
  Ruff target set includes the maintained symbol toolchain as well as application
  code and tests.
- Update `README.md` for user-visible behavior/setup/capabilities, canonical
  architecture/data-model docs for their respective decisions, `TODO.md` for
  concrete future work, and `CHANGELOG.md` under `Unreleased` for meaningful
  changes.
- Keep `__version__` at the released value until an explicit release. While
  unreleased work exists, the browser footer uses `__display_version__` with
  the `+dev` suffix.
- Every release follows the canonical `docs/releasing.md` checklist. A project-wide
  documentation audit is a mandatory release gate and must review the complete maintained
  documentation corpus rather than only the files touched by that release.

## Decision log

- 2026-09-18: CI/testing design separates required hermetic source checks from
  explicit full-asset integration. Clean public CI must not depend on ignored
  Corvus Belli graphical assets or live acquisition; full-asset runs require a
  validated complete asset set and must not redistribute it. Installed-package,
  deployment, and cross-platform checks are separate validation layers.
- 2026-09-12: Database builds require validated Army API metadata. The importer
  enforces this too, so metadata-free normalized data cannot bypass the build
  command and become a database.
- 2026-09-12: SQLite is a local replaceable imported snapshot, not a home for
  user-authored persistent data. User-owned migrations are deferred until that
  requirement exists.
- 2026-09-12: The browser has no frontend build tool; native modules keep local
  deployment and maintenance simple.
- 2026-09-12: The browser shell is centrally rendered from navigation, header,
  and footer fragments. CSS tokens/shared components are the extension point for
  visual consistency.
- 2026-09-13: Settings uses the shared sidebar/compact-topbar menu pattern. Unit
  catalog accents may draw from named main-army colors only through the shared
  design system.
- 2026-09-14: PDF/wiki-derived rules references use their own SQLite database,
  independently versioned from the replaceable Army JSON snapshot.
- 2026-09-16: Engineering principles are canonical in `docs/architecture.md`.
  Maintained domain knowledge belongs in validated configuration where
  appropriate; generated project paths remain deterministic and portable.
- 2026-09-16: The `1` -> `901` canonical-faction ownership override was moved
  into validated identity configuration. Subsequent source investigation on
  2026-09-17 found that the two IDs represent different domain concepts.
- 2026-09-17: After mercenary logical pairing and availability provenance moved
  to explicit normalized metadata, the legacy `1` -> `901` override was removed.
  Canonical source ID `1` now remains mercenary provenance with no application
  `main_army_id`; 901 remains the distinct NA2 grouping identity. Army database
  compatibility revision 12 requires rebuilding existing generated snapshots.
- 2026-09-16: Army-linked symbol discovery is reference/URL based, uses one
  exact pinned Army snapshot, audits unknown SVG locations, and leaves final
  canonical application paths/mappings to the publisher. This records design
  direction; the integrated manifest-backed pipeline is not yet implemented.
- 2026-09-16: Army JSON, wiki, and symbol acquisition use complete timestamped
  ZIP snapshots rather than long-lived unpacked download directories.
- 2026-09-16: Snapshot metadata follows the existing data-path model instead of
  introducing editable sidecars beside raw archives: generated acquisition
  provenance belongs under `data/manifests/snapshots/` and human notes under
  `data/curated/snapshot-notes/`.
- 2026-09-17: The snapshot-provenance and snapshot-note contracts were
  implemented. Army, wiki, and symbol acquisition now write deterministic
  SHA-256-addressed provenance records, while curated snapshot notes remain a
  separate source-controlled human layer that acquisition tooling never edits.
- 2026-09-18: Army source-version investigation showed that mixed top-level
  `version` values are stable source revisions, not evidence of a torn snapshot.
  The 2026-09-10 and 2026-09-18 acquisitions were byte-identical and both split
  36 documents at `7.26246.158` / 22 at `7.26246.159`. Snapshot coherence will
  therefore be based on source stability across acquisition, while snapshot date
  and per-document data revision remain separate provenance concepts.
- 2026-09-18: The exact 2026-09-18 Army snapshot is the reviewed
  normalization-anomaly baseline: 116 warnings across five categories. The
  tracked validation config treats those counts as ceilings for downloader-dated
  snapshots at or after that date. Decreases are allowed; new categories or
  count growth fail the InfinityDB application build before SQLite export.
  Synthetic/ad-hoc inputs without downloader snapshot provenance and the
  standalone `infinity-army` pipeline are deliberately outside this baseline.
- 2026-09-21: Maintained Weapon category/correction references now accept numeric
  source IDs or deterministic source-label slugs, and all 16 tracked references use
  readable slugs. Resolution happens against the source weapon catalog before source
  corrections are applied; numeric authoring remains available for ambiguity/provenance.
  The curated display-identity target similarly uses the source faction slug
  `non-aligned-armies`, while canonical source identity `1` remains numeric because no
  authoritative source-faction slug owns that provenance identity.
- 2026-09-17: Weapon catalog policy was split from implementation code.
  `config/catalogs/weapon-categories.json` owns ordered weapon-family matching
  and explicit category decisions; `config/catalogs/weapon-overrides.json` owns
  Army-source name/profile corrections and exact non-display metadata-profile
  matchers. Normalization consumes those validated build inputs and materializes
  their effects; the runtime repository does not load catalog configuration.
- 2026-09-17: The remaining hard-coded-domain audit classified weapon range bands
  as derivable presentation data, not configuration. Weapon detail rendering now
  derives ordered range endpoints from imported profile `distance[].max` values.
  Distance-skill handling is now source-driven: Army `extras.type` determines
  `DISTANCE` versus text, while curated skill `variantSemantics.occurrenceParameters`
  supplies only rule-derived sign-display behavior for Super-Jump and Forward Deployment.
  Reinforcement prefix normalization is now pinned in the identity config and
  unit-detail profile display names are backend-derived. Remaining audit targets
  are now limited to symbol-semantic name tables reserved for the symbol-pipeline
  refactor; the former direct `901` grouping special case is derived from the
  metadata/playable-list hierarchy instead.
- 2026-09-17: Special weapon game-rule facts moved out of
  `infinity_army_data.weapon_profiles`. The Armed Turret special profile is a
  cited curated `weapon` record linked to Army weapon ID 226; repository reads
  expose raw Army catalog data and the application composes the special profile
  from `rules.db` when curated rules are available.
- 2026-09-17: Skill declaration categories moved out of Python into cited
  curated `skill-declaration-category` records linked to Army skill IDs. The Army
  repository exposes raw skill data only; `SkillCatalog` composes declaration
  categories and ordinary curated skill rules from `rules.db`, with uncited
  `Unclassified` as the fallback when no curated declaration is available.
- 2026-09-16: Rules ingestion is scoped to `data/curated/rules/`. Other curated
  categories may have separate future semantics but are not implicitly rules
  database inputs.
- 2026-09-16: Documentation distinguishes current implementation, accepted
  design direction, and planned/unimplemented backlog so future architecture is
  not presented as existing behavior.
- 2026-09-17: Generic standard-unit duplicate matching moved from repository-time
  10,000-ID arithmetic into a normalization audit persisted as
  `genericUnitMatches`. Database creation treats the persisted audit as
  authoritative, including an empty result; older normalized inputs without the
  key retain the builder's arithmetic fallback. This intermediate persistence
  step required no SQLite schema or compatibility revision by itself.
- 2026-09-17: Unit `main_army_id` derivation moved from the ordinary `xx01`
  Army-ID convention to imported metadata faction parents for current
  InfinityDB builds. Explicit maintained overrides still win; `xx01` remains
  only as a legacy/standalone fallback when metadata cannot resolve the
  canonical faction. Database compatibility revision 13 requires rebuilding
  existing generated Army databases.
- 2026-09-17: Army role/playability moved to an explicit source-derived
  backend/API contract. Metadata parents classify main, sectorial, and
  Non-Aligned forces; explicit ordinary-list `reinforcements` links classify
  reinforcement relationships. Grouping identity 901 is exposed as
  non-playable and browser selectors no longer infer roles from Army-ID ranges.
- 2026-09-17: Army grouping identities are derived structurally rather than by
  recognizing ID `901`. Current source `901` is itself an imported ordinary army
  list with metadata parent `900`; it parents the NA2 child lists and has a real
  source roster. Imported parents that are not self-parented become non-playable
  grouping nodes, while self-parented parents remain main armies. Source-list
  existence, roster semantics, hierarchy role, and application playability are
  separate concepts.
- 2026-09-17: Non-playable grouping rosters do not get a dedicated application
  query surface. The 901 source roster remains preserved for provenance, while
  application unit availability is reached through the playable child NA2 army
  occurrences. This remains separate from canonical logical-unit payload/context modeling.
- 2026-09-18: Unit presentation identity is separate from ownership. Reviewed
  source-derived mappings live under `data/curated/identities/`; normalization
  pins that curated document/hash and derives `display_army_id`. The current
  mapping displays canonical source identity 1 with grouping identity 901 while
  leaving `main_army_id`, list membership, and 901 playability unchanged.
- 2026-09-17: Mercenary source identity and Non-Aligned Army grouping are
  separate. ID `1` is retained as mercenary source provenance; 901 groups NA2
  army lists. Dedicated mercenary variants are identified by source semantics,
  not numeric ID arithmetic. Classification, persisted mercenary-to-standard
  matching, and explicit availability provenance are now normalized before
  repository use.
- 2026-09-17: Logical-unit identity is materialized during frontend database
  creation. Configured aliases and persisted generic, mercenary, and
  reinforcement matches are build-time identity evidence; the exporter resolves
  their transitive components into `logical_units` and `logical_unit_sources`.
  Source/profile/loadout/occurrence rows remain keyed to original source units
  for provenance, and repository reads consume the materialized relation. Legacy
  identity discovery is retained only behind the builder for older normalized
  inputs.
- 2026-09-19: Local production deployment with symbols is fail-closed. `deploy.sh`
  requires a terminal v8 `army-symbol-build.json` whose SHA-bound inventory and
  browser maps match the local publication, verifies the complete published set,
  then validates the exact built image in `--published-assets` mode before Compose
  activation. Redistributable-image verification remains the inverse contract and
  rejects third-party graphical trees.
- 2026-09-19: Deployment artifact transfer is also commit-bound.
  `tools/send_deployment_artifacts.py` sends only the ignored runtime databases,
  terminal symbol manifest/inventory, and published SVG trees over one staged SSH
  session, and refuses a remote checkout whose commit or tracked state differs from
  the clean local checkout. Tracked browser maps travel through Git, not the artifact
  transfer, so exact commit identity is part of the transfer contract.
- 2026-09-20: Production deployment has two explicit data modes.
  `install-or-update.sh` is the server-rebuild path and may replace generated runtime
  databases from server-local raw source. `deploy-transferred.sh` is the no-rebuild
  path for the commit-matched artifact bundle produced by
  `send_deployment_artifacts.py`; it must preserve that transferred database/symbol
  pairing. `deploy-local-test.sh` reuses the no-rebuild path under a separate Compose
  project, binds only to `127.0.0.1`, and disables production image pruning.
  `stop-local-test.sh` is the matching teardown path: it always targets only the
  `infinitydb-test` Compose project and retains its named volumes by default.

- 2026-09-20: Containerized deployments preserve the checkout-derived browser display
  version explicitly instead of copying Git metadata into the image. `deploy.sh`
  computes `__display_version__` in the source checkout and passes it into the Docker
  build as `INFINITY_DB_DISPLAY_VERSION`; installed/containerized code prefers that
  value when rendering the browser footer. The package/API `__version__` remains the
  released semantic version and is not changed by this deployment metadata.
- 2026-09-20: Human-authored catalog identity overrides may use either positive
  numeric source IDs or readable source-label slugs. The checked-in Skill, Equipment,
  and Weapon identity groups now use readable source-label slugs throughout. Slug
  references are resolved before application catalog grouping and therefore do not
  depend on the later public application-slug registry. A group wholly absent from a
  source snapshot is inert; once any member is present, unknown or ambiguous slugs
  fail closed. Numeric references remain valid for compatibility, provenance, and
  collision disambiguation. Apply this numeric-or-slug authoring convention to other
  maintained/curated JSON reference fields only where their owning layer can resolve
  the domain deterministically.
- 2026-09-21: Milestone 2B include relationships now use canonical target identities
  without assuming the attachment itself is payload-invariant. The production
  relationship audit resolves all 2 Profile, 949 Loadout, and 35 shared Unit-option
  includes, but 23/186 affected canonical Loadout payloads have contextual include
  variants. A valid loadout target can also become a different canonical payload in a
  different Army context even when the parent Profile payload remains identical. Schema
  version 18 / compatibility revision 26 therefore materializes
  `profile_occurrence_includes` and `loadout_occurrence_includes` as contextual parent
  relationships whose targets are canonical loadout payloads, while
  `unit_option_include_targets` expands the shared source relationship per target Army
  occurrence. Source target coordinates remain provenance rather than application
  identity.
- 2026-09-21: Curated N5 `armyLinks` for Skills, Equipment, and Weapons now use
  readable application-domain slugs instead of opaque numeric source IDs. The curated
  v3 validator accepts either a positive integer or a domain slug for those entities,
  rejects numeric-looking slug strings, and retains numeric compatibility. `rules.db`
  stores the authored reference without importing Army data; Skill/Catalog composition
  checks both source-ID and application-slug forms so grouped identities such as Martial
  Arts, Strategos, BS Attack, CC Attack, and Armed Turret resolve through the same
  logical identity used by public routes.
- 2026-09-21: Centralize dual-ID resolution in the Army repository.
  `application_domain_id()` is the shared resolver for the registry-backed Army, Unit,
  Skill, Equipment, and Weapon domains; domain-specific resolver helpers delegate to it,
  and detail reads accept numeric/source IDs or stable slugs directly. Web detail routes
  parse numeric route syntax but no longer resolve slugs before calling the repository.
- 2026-09-21: Treat dual numeric/slug identity as the default contract for every
  application domain once a stable domain-local slug can be resolved. Application-facing
  repository/API calls, routes, filters, cross-links, browser state, and maintained
  references should accept either the numeric application ID or canonical slug; producers
  should prefer slugs for human-facing and human-authored output while retaining numeric
  compatibility. New domains must establish one central resolver and reuse it across all
  consumers rather than inventing local slug schemes. Unresolved/colliding slugs fall back
  to numeric identity and must not be guessed. Source/provenance-only references are outside
  this rule until explicitly mapped to an application identity. Armies now follow the
  same contract for Unit-explorer/API filtering while retaining their source/context slug
  separately from the application `public_slug`.
- 2026-09-20: Domain-unique application slugs now have a derived persistence
  layer. Schema version 17 / compatibility revision 25 materializes
  `application_domain_slugs` for Armies, logical Units, Skills, Equipment, and
  Weapons. Each identity retains a deterministic candidate plus `resolved`,
  `collision`, or `unavailable` status; collisions never receive positional numeric
  suffixes. The current 2026-09-18 snapshot resolves all 1,042 initial identities.
  Source slugs/numeric IDs remain context/provenance and curated IDs such as
  `skill:doctor` remain typed internal identities. Skills are the first additive
  public-route consumer: resolved non-numeric Skill slugs are emitted in API/browser
  links and accepted by web/API detail routes while numeric routes remain valid.
  Numeric-only candidates stay on the numeric compatibility form, and no redirect or
  permanent slug-freeze promise is made until the later freezing/alias migration.
- 2026-09-21: Equipment is the second additive public-route consumer of the
  application-domain slug registry. Equipment catalog/detail API payloads and nested
  Unit equipment references expose resolved non-numeric application slugs, browser
  links prefer them, and `/equipment/{slug}` plus `/api/equipment/{slug}` resolve to
  the canonical application Equipment identity. Numeric Equipment routes remain valid,
  source-variant IDs are resolved through the application catalog provenance mapping
  before slug lookup, and numeric-only slug candidates remain on the compatibility
  numeric form.
- 2026-09-21: Weapons are the third additive public-route consumer of the same
  application-domain slug registry. Weapon catalog/detail API payloads and nested Unit
  weapon references expose resolved non-numeric application slugs, browser links prefer
  them, and `/weapons/{slug}` plus `/api/weapons/{slug}` resolve to the canonical
  application Weapon identity. Existing numeric Weapon routes remain valid, curated
  source-variant IDs resolve through application catalog provenance before slug lookup,
  and numeric-only candidates stay on the compatibility numeric form.
- 2026-09-21: Logical Units are the fourth additive public-route consumer. Existing
  Unit `slug` remains source/context data, while player-facing Unit payloads expose a
  separate resolved `public_slug`. Unit list/detail, catalog usage, Trait usage, and
  Skill Modifier links prefer that application slug; `/units/{slug}` and
  `/api/units/{slug}` resolve through the registry while numeric Unit routes remain
  valid. Source Unit references are resolved to their logical application Unit before
  slug lookup, and numeric-only candidates remain on numeric compatibility URLs.
- 2026-09-21: Unit explorer Skill, Equipment, and Weapon filters are public-identity
  consumers too. Browser filter option/state values prefer resolved application-domain
  slugs and preserve numeric query values only for compatibility. Repository filtering
  resolves either form to the logical application catalog identity, then expands that
  identity to all materialized source IDs before matching canonical profile/loadout/unit-
  option occurrences. A grouped filter must therefore match every represented variant
  (for example any TinBot source variant) rather than only the numeric representative.
  Catalog-list payloads expose those materialized `source_ids`, and the browser uses them
  to canonicalize accepted legacy source-ID query values to the preferred application
  slug so selector state and backend filtering cannot diverge.
- 2026-09-21: Armies now consume the same dual identifier contract. `/api/armies`
  exposes an additive `public_slug` while retaining the existing Army `slug` as source/
  context data. Unit-explorer and `/api/units` Army filters accept either a source/
  application numeric ID or the application Army public slug, normalize through one
  repository resolver, reject grouping-only identities after resolution, and prefer the
  public slug in browser query state while preserving numeric compatibility.
- 2026-09-21: Numeric-shadow handling is owned by the application-domain slug registry.
  Digit-only candidates remain visible as `candidate_slug` for diagnostics but are stored
  as `unavailable` with no routable slug because they would collide with numeric
  compatibility routes. `application_slug()` therefore returns only actually routable
  public identifiers, and downstream consumers no longer repeat `slug.isdigit()` guards.
  Trait slug assignment remains independent because Trait routes do not share a numeric
  application-ID namespace.
- 2026-09-21: Cross-domain API references now follow an additive slug-companion policy.
  Existing numeric fields remain stable; canonical application references gain readable
  companions when routable. Unit Army scalar references use `main_army_slug` /
  `display_army_slug`, structured Army references use `public_slug`, Trait usage variants
  use `item_slug`, and Skill Modifier rows use `skill_slug`. Source/context-only IDs remain
  numeric-only rather than being relabeled.
- 2026-09-21: Trait public identity is aligned with the shared slug policy without
  duplicating curated rules identity into the Army database. Curated Traits already own
  stable typed IDs in `rules.db`; a simple `trait:<slug>` ID projects directly to the
  public Trait route and remains stable across display-name changes. Trait list/detail
  payloads expose `slug` explicitly. Uncurated raw Traits use the complete Army Trait
  catalog's shared normalization/collision pass, and application cross-links must reuse
  that assigned slug rather than normalize individual labels independently. Qualified
  typed IDs are not flattened implicitly into route slugs.

- 2026-09-20: Peripheral rule semantics belong in the existing curated v3
  `data/curated/rules/` -> `rules.db` pipeline, with the N5 rulebook as primary
  rules authority, the pinned Wiki archive as discovery/secondary provenance,
  and FAQ rulings kept as dated clarification records. Reviewed Army-local
  Peripheral-to-canonical-entity/profile mappings are a separate future curated
  identity contract; Wiki/rules knowledge is never written into Army source
  tables. The current 2026-09-18 Army audit finds 279 army-local definitions, 56
  names, 818 resolved loadout attachments, no profile attachments, all 279
  definitions attached somewhere, 41 names with multiple raw identities, three
  names with `mercs` variation, and 22 canonical loadout payloads with differing
  semantic attachment signatures.
- 2026-09-22: The Peripheral rules-side foundation is implemented in that existing
  curated v3 pipeline. Doctor and Engineer are reviewed `short-skill` records;
  Cyberplug and Peripheral are reviewed `automatic` records; Servant, Synchronized,
  Control, Ancillary, and Cyberplug are validated `peripheral-type` rule records.
  Controller eligibility uses only the reviewed `not-stated`, `hasSkill`, and
  `anyOf(hasSkill...)` grammar, with referenced Skills resolved inside the collection.
  This deliberately does not canonicalize any Army-local Peripheral definition.
- 2026-09-22: The separate Peripheral source-identity contract is now defined at
  `data/curated/peripherals/army-identities.json`, with its own validator/CLI. It owns
  reviewed `peripheral:*` entities, optional `peripheral-profile:*` records, exact
  `(sourceId, armyId, peripheralId)` mappings, expected source names, and review reasons.
  Entity `typeId` is optional so reviewed cross-Army identity can precede rules-type
  classification; when present it is restricted to the five curated Peripheral types. Profile
  modes are only `connected`/`autonomous`; `mercs` is rejected as identity data. The
  checked-in current-snapshot contract contains zero mappings intentionally. Population
  and coverage review must happen before any derived application relationship is built.
- 2026-09-22: The first reviewed Peripheral identity population covers the entire embedded
  `peripherals` mechanism for the pinned 2026-09-18 snapshot: all 279 definitions map to 56
  canonical `peripheral:*` entities. The identity boundary is intentionally conservative: one
  canonical entity per exact source-definition name, no cross-name merging, and no canonical
  `peripheral-profile:*` records in this pass. Rules type is taken from the matched Army profile's
  explicit `Peripheral` Skill subtype extra, not controller heuristics or display-name inference.
  Unit-backed Peripheral identities and concrete Controller relationships remain a separate pass.
- 2026-09-22: Peripheral source review distinguishes two Army mechanisms. The `peripherals`
  catalog plus explicit attachments and hidden disabled profile groups is the embedded mechanism;
  the 2026-09-18 snapshot has all 279 definitions in that form, so same-name enabled/disabled
  matching is not a Cyberplug discriminator. Independently listed Peripherals instead appear as
  ordinary `army_units` whose profiles explicitly carry the Army `Peripheral` Skill. The Skill's
  source extra is direct subtype evidence: extra 41 is `Servant` and extra 374 is `Cyberplug`.
  Slave Drones (unit 526) and Reinforcement Slave Drones (unit 1617) prove that selectable
  Unit-backed Peripherals are not Cyberplug-exclusive; Sartroid Ranters/Puzzlers (1885/1886)
  expose the Cyberplug subtype and Connected/Autonomous profiles through the same Unit-catalog
  mechanism. Cyberplug-skilled Controllers are audited independently, and same-Army subtype
  candidates plus raw relation/dependency adjacency remain review evidence rather than automatic
  Controller mappings.

- 2026-09-22: **Release direction through 1.0.** Milestone 2B shipped in 0.6.3:
  canonical relationships, the raw/application split, and the Army completeness
  inventory are validated. 0.7.x adds rules/context to existing data; 0.8.x
  exposes connected game relationships; 0.9.x closes remaining player-facing gaps and
  focuses on search/navigation/mobile/accessibility/themes; 1.0.0 is the player-data-
  complete reference gate defined in `docs/releasing.md`. Minor-release scope is directional,
  while the 1.0 acceptance criteria are durable.
- 2026-09-21: **Design direction — 0.7.0 is the rules-enriched catalog-data
  release.** Use the completed N5.3 Wiki/PDF/FAQ audit to enrich data InfinityDB
  already exposes with concise original summaries, authoritative links/citations,
  reviewed semantic labels, variant-aware meaning, and explicit related-catalog
  relationships. Supporting rules identities may be added when needed to explain
  an existing item without requiring a new standalone browser catalog. Keep
  semantic identity, publication provenance, and applicability scope independent.
  The 0.7.0 gate does not require a complete scenario/ITS library, rules engine,
  live game-state model, organizer tooling, or standalone UI for every supporting
  rules domain; remaining gaps must be classified explicitly rather than silently
  treated as covered.
- 2026-09-21: Cube and Cube 2.0 are canonical N5 Automatic Equipment whose Army
  Unit Profile occurrence is encoded only by the dedicated Cube/Cube 2.0 symbols;
  they are not listed in the profile's textual Equipment block. Treat this as a
  source-presentation encoding, not an Army-versus-rules classification conflict.
  Preserve the symbol/source occurrence and resolve it to the canonical Equipment
  identity without inventing a textual source row.

### Milestone 2B Peripheral identity boundary (2026-09-22)

- Embedded Army `peripherals` rows use reviewed `peripheral:*` identities; current snapshot
  coverage is 279/279 definitions -> 56 entities.
- Standalone Unit-backed Peripherals must reuse existing logical-Unit identity rather than
  creating parallel Peripheral entities. The reviewed contract v2 adds 17 source Unit mappings
  -> 10 logical Units, including Reinforcement variants, with type taken from the source
  `Peripheral` Skill subtype.
- Concrete Cyberplug Controller links remain unresolved: Units 507/1884 can see same-Army
  Ranters/Puzzlers candidates, but the current relation/dependency data does not select a
  specific pairing. Same-Army co-occurrence is not sufficient to materialize a relationship.
- 2026-09-22: Reviewed Cyberplug Controller relationships are access/selection pools, not fixed
  Controller ownership. The current Army snapshot contains four Cyberplug-capable loadout
  occurrences (Med-Tech Obsidon in Armies 601/605 and two Gearhead options in Army 605), and the
  same Army contexts expose Sartroid Ranters/Puzzlers as the two Unit-backed
  `Peripheral (Cyberplug)` logical Units. The source relation/dependency tables contain no edge
  assigning a specific Sartroid to a specific Controller. Curated Peripheral identity format v3
  therefore records reviewed `controllerAccess` pools from source-context Controller occurrences
  to canonical logical Units and validates Controller name/type/target-pool drift separately.

- 2026-09-22: Milestone 2B Peripheral identity/relationship research is now materialized in
  the Army application database. Schema 23 / compatibility revision 31 retains the reviewed
  Peripheral contract/hash into database metadata and persists 56 current embedded entities,
  279 source-definition mappings, 17 Unit-backed source mappings to 10 logical Units, four
  Cyberplug Controller access occurrences, and eight access-pool edges to canonical Ranters/
  Puzzlers targets. Repository Unit details expose embedded Peripheral attachments,
  Unit-backed `peripheral_type_ids`, and per-profile/loadout `peripheral_access` targets.
  Runtime reads do not open `data/curated/peripherals`; database validation rechecks the
  materialized rows against retained source context. Cyberplug access remains a selection pool,
  never fixed ownership.

### Milestone 2B relation/dependency audit boundary (2026-09-22)

- The schema-19 snapshot has 126 normalized relations, 250 relation members, and 14 dependency
  rows. 118 relations resolve every Unit endpoint through logical-Unit identity. The other eight
  contain one of five relation-only source placeholder IDs (165, 613, 749, 1503, 1509). Independent
  archived Army evidence identifies these as retired Sun Tze v.2, Achilles, Achilles v2
  (Corintian Armor), Boarding Action Sheskiin, and Adil Mehmut (Special Division) source Units.
  The identification is historical evidence, not a logical-Unit alias to the relation partner.
- Same logical Unit is not evidence that a relation is normalization-only. Ninety-seven resolved
  relations collapse to one logical-Unit endpoint set, including ordinary/Reinforcement selection
  constraints that remain player-relevant after identity canonicalization. Twenty-one resolved
  relations span multiple logical Units. Profile/group/options/perParent/min/minDependant
  selectors remain source-local semantics pending review.
- Reinforcement Section parent context is already complete in the application layer: 46/46
  source ordinary-Army links materialize canonically with no missing or unexpected edges. The 12
  source reinforcement lists reconcile to 11 application Reinforcement identities because the
  reviewed 998/999 alias shares application identity 999.
- The resolved relation graph now has an explicit structural semantic classification. Of 118
  fully resolved relations, 81 are same-logical cross-context exactly-one constraints, 21 are
  cross-logical shared-cardinality constraints, 14 are single-logical profile/dependency
  constraints, and two are single-logical cardinality constraints (the current Post-Human
  2..3 pool). The eight relations containing unresolved source placeholders stay unclassified.
  This is a relation-level classification: member/dependency selectors remain contextual and do
  not become logical-Unit facts.
- Ninety-five resolved relations are selector-free; 23 carry member/dependency selectors. The
  Army relation field named `profile` cannot currently be normalized as one foreign-key domain:
  current values mechanically match profile-group IDs in some rows, profile IDs in others, option
  IDs in others, and multiple domains where numeric coordinates overlap. Preserve it as an opaque
  source selector until its grammar is resolved; do not rename it to a canonical profile FK.
- 2026-09-22: Schema 23 / compatibility revision 31 materializes 96 fully resolved selection-safe
  Army-context constraints. The application layer contains 81 same-logical cross-context
  exclusivity constraints, 13 cross-logical shared-cardinality constraints, and two single-logical
  cardinality constraints, with 197 member rows. The additional cross-logical row is Jaan Staar /
  Kiiutan: both source selectors identify the selectable active profile in each Unit's only
  selectable profile group, so the source max-1 relation is roster-selection-equivalent at Unit
  level. Constraint members preserve both `source_unit_id` and canonical `logical_unit_id`. The 14
  same-logical dependency relations whose `profile` selectors unambiguously match Army-local
  profile-group coordinates remain materialized as `group_dependencies`, preserving source relation
  cardinality, `perParent`, dependency `group`, `min`, `minDependant`, and validated option
  selectors. Seven Traktor Mul / Dozer / Kuryer rows and the Kuang Shi / Celestial Guard bridge
  remain source/context-only because their selector coordinates are not safe whole-Unit semantics.
  The eight historical-placeholder relations are now independently identified and reviewed as
  stale source constraints. Their endpoints have no current Army/profile/loadout occurrence, so
  they are not canonicalized to current Units and are not materialized as current constraints.
  `data/curated/relationships/historical-unit-endpoints.json` pins that review to the 2026-09-18
  snapshot; relation-audit reuse fails closed on snapshot drift.

### Milestone 2B Fireteam audit boundary (2026-09-22)

- Fireteam Charts are Army-local relationship/configuration data, not intrinsic logical-Unit facts.
  The pinned snapshot has 58 source charts, 272 teams, 444 type memberships, and 1,261 members.
  Preserve team/type membership, min/max, `required`, member wording/comments, chart notes,
  Wildcards, FTO restrictions, and bracketed Fireteam-Level equivalence in source Army context.
- Raw Fireteam `spec` currently uses 0=unavailable, 256=unlimited, and other positive values as
  finite maxima. Reinforcement Section specs cannot be used alone: 29 Section type memberships
  occur with an own-spec value of zero. The 12 source Reinforcement charts collapse to 11
  application Sections and 46 parent links; nine playable parent/type combinations are blocked by
  the parent quota, all vanilla CORE cases. Keep Section member eligibility separate from the
  selected parent Army's permitted type/count limits, and never merge Main/Reinforcement pools.
- Unit resolution is too coarse for Fireteam member identity. The snapshot has 1,246 Army-local
  member resolutions and 15 non-local/unresolved rows. Eight teams contain distinct member rows
  resolving to the same source Unit (for example Scylla/Charybdis, Scarface/Cordelia, Zoe/Pi-Well),
  proving subgroup/profile/loadout context can remain player-relevant after Unit canonicalization.
- FTO eligibility must resolve against Army-local loadout options. 195/197 FTO-bearing member rows
  resolve deterministically. Keep the two source anomalies explicit: Ank's Arjuna FTO row resolves
  by source slug only to ordinary Arjuna context; Melek's Korsan row says FTO but the Reinforcement
  Unit exposes no FTO-marked loadout. Do not invent either mapping. Generic FTO may match numbered
  variants; explicit FTO-N requires that variant.
- `required=true` denotes required-choice participation, not that every flagged member is mandatory.
  There are 219 such rows across 84 teams; preserve min/max independently. Preserve the one Army
  chart description and four team observations verbatim because chart notes can override/specialize
  general rules. Wildcards (52 teams / 51 Armies) have no Fireteam type rows. Bracketed equivalence
  wording appears on 406 member rows (453 references / 146 labels) and must not feed Unit identity.
- `tools/audit_fireteam_semantics.py` is the deterministic read-only evidence tool for this boundary.
  First-class Fireteam repository/API/browser presentation remains a separate 1.0 completeness task.

### Milestone 2B normalization-link boundary (2026-09-22)

- Do not infer player-facing meaning from the existence of a join table. The eight source
  `army_*` catalog joins flatten Army `filters.*` lookup/index arrays and are normalization-only
  source-presentation structure. The pinned snapshot contains 15,072 such rows. Preserve them for
  source fidelity, but their dedicated web presentation is not a completeness requirement.
- The source `option_weapons` / `option_weapon_templates` split has one normalization-only storage
  edge: synthetic template identity plus `template_id`. The 52,554 option-weapon occurrences reuse
  490 templates with no dangling or unreferenced template rows. The rejoined option-to-weapon
  occurrence remains semantic/source data and must stay reconstructable.
- Source-to-canonical mappings and canonical payload-occurrence links are not independent gameplay
  relationships, but do **not** classify them as disposable normalization. They preserve identity
  evidence, traceability, and contextual deltas needed by the application model and by a future
  frontend/`infinity.raw.db` split.
- Attachment/relationship joins (extras, includes, Army/faction membership, Peripherals, Fireteams,
  relation/dependency constraints, and similar scoped links) remain semantic unless a separate audit
  proves otherwise. `tools/audit_normalization_links.py` is the deterministic evidence tool for
  this boundary.

### Milestone 2B application/raw database separation boundary (2026-09-22)

- Schema 23 / compatibility revision 31 completes the application/raw physical split. Export first
  builds the complete normalized + derived relational model in a temporary staging database
  and runs all source-to-canonical consistency validation there. Only after those checks
  pass is the published application subset copied to `infinity.db`.
- `infinity.raw.db` is the existing lossless normalized Army source/provenance sibling; no second
  raw artifact is planned. It now stores all 70 normalized source tables as queryable relational
  tables **and** exact JSON for every imported normalized row in `__infinity_raw_rows`, under the
  same pinned metadata as `infinity.db`.
- The logical inventory remains 28 canonical application tables, 40 contextual application tables,
  and 47 source/provenance-only normalized tables. Published `infinity.db` contains only
  `__infinity_metadata` plus the 67 retained application tables; the 47 source-only tables are
  physically absent. Foreign keys targeting raw-only tables are omitted from the published schema,
  while retained-to-retained foreign keys remain enforced.
- Normal repository/API/web serving and runtime `Database.validate()` do not open
  `infinity.raw.db` and have zero raw-only table reads. Source-dependent semantic checks
  remain mandatory during staging validation rather than being weakened or deleted. Runtime
  validation also verifies a deterministic SHA-256 over the complete published application-
  table contents so post-build drift is detected even for values that can no longer be
  re-derived without raw source tables.
- `tools/audit_database_separation.py` fails closed if the published table inventory,
  raw relational/lossless equivalence, metadata pairing, runtime surface, foreign-key
  boundary, or runtime-validation independence drifts. The rebuilt reviewed production
  database confirms the storage estimate: `infinity.db` fell from 18,108,416 to
  8,138,752 bytes, a 55.06% reduction. Storage savings remain evidence rather than the
  semantic acceptance criterion.

### Milestone 2B source-to-presentation completeness boundary (2026-09-22)

- `tools/audit_source_presentation.py` is the maintained Army source-to-presentation
  inventory. It covers all 70 normalized source tables / 441 source fields and assigns
  semantic-provenance plus presentation-status classifications; schema growth must fail
  closed until new source constructs are reviewed.
- The first complete pass records 10 confirmed gap families: Fireteams, includes,
  Peripheral/Controller links, selection/dependency relationships, Reinforcement parentage,
  declared faction membership, source-attributed Unit notes, top-level composite Unit
  options, Structure/Wounds labeling, and structured Hacking/Martial Arts/Booty/
  MetaChemistry reference data. Their roadmap homes are 0.7.x, 0.8.x, and 0.9.x rather
  than Milestone 2B implementation.
- Keep `spectables` and loadout `disabled` / `minis` in an explicit semantic review queue;
  preserve the source values and do not invent presentation semantics before the domain
  meaning/scope is resolved.
- Milestone 2B shipped in 0.6.3. The next active milestone is 0.7.0 rules-enriched
  catalog data, not further canonicalization.

## 0.7.0 rules-enrichment contract foundation (2026-09-23)

- Curated rules format v6 requires every record to declare `scope.game`, a non-empty
  `scope.seasons` list, and a review object containing `status` (`draft` or `reviewed`)
  plus `reviewedOn`, together with a composition role of `definition` or `supplement`.
  Applicability, review state, and contribution semantics are therefore explicit
  build-time contract fields rather than optional free-form metadata.
- Semantic record identity, applicability, and source/publication provenance remain
  separate. `RulesDatabase` returns collection metadata with each record; citations
  continue to carry source title/version/URL and location.
- Army-linked rule lookup consumes only `current` collections by default. Historical
  or superseded collections may coexist in `rules.db` and can be requested explicitly,
  but they must not affect normal catalog enrichment merely because they were loaded.
- Current multi-publication composition is additive and fail-closed: every semantic ID
  must have exactly one definition, while additional current publications may contribute
  scoped supplements. Supplement fields are not merged into the definition and no
  precedence is inferred from load order, collection ID, or effective date.
- Related-item navigation uses typed one-way semantic edges. Current targets must resolve
  to current semantic IDs before export; `rules.db` derives reverse links from inbound
  edges so reciprocal rows are not authored independently. The initial typed relation
  set covers state entry/reveal and Peripheral subtype/controller-eligibility edges.
- Skill, Trait, Equipment, and Weapon detail pages share one rules-reference renderer.
  It displays existing curated summaries/classifications and source citations as links;
  this is presentation of maintained enrichment, not a new source of rule semantics.

## 0.7.0 variant-aware rules contract (2026-09-23)

- Curated rules format v6 and `rules.db` schema/compatibility 4 make rule inheritance
  across canonical Army catalog families explicit. Every Army-linked Skill, Equipment,
  or Weapon definition declares `variantSemantics.inheritance` as `family` or `source`;
  application catalog grouping alone is never evidence that rule facts are shared.
- `family` contributions may be presented at the canonical catalog level. `source`
  contributions require exactly one numeric Army source identity and exactly one typed
  `variant-of` relation to a same-kind family definition; composition attaches those
  rules only to the matching source variant. This is the required pattern for exact
  Levels and named source variants whose rules differ.
- Army routing belongs to definition contributions. Supplements inherit the definition's
  routing and may not declare their own `armyLinks`; this prevents a scoped supplement
  from silently changing family-versus-source applicability during composition.
- Occurrence parameters remain independent of source-variant identity. Format v6 moves
  the existing distance display semantics out of `facts` into
  `variantSemantics.occurrenceParameters`; raw Army extras remain occurrence-scoped.
  Only the audited `army-extra` / `distance` parameter is standardized initially.
  Unknown MOD/value spellings must remain opaque until reviewed rather than being
  generalized into universal base-rule facts.
- Skill/Equipment/Weapon detail APIs retain canonical family rules separately from
  source-specific variant rules, and the browser renders exact variant rules inside the
  corresponding usage variant.

## 0.7.0 Training classification (2026-09-23)

- `Regular` and `Irregular` are rules-domain Training, not rule-defined Skills;
  Army skill-like compatibility occurrences remain source data, not proof of
  rules-domain classification.
- Reviewed Training records are keyed to `regular`/`irregular` generated Order
  occurrences at the loadout level and retain publication/citation provenance.
  No application-wide or Unit-wide Training is inferred, and Tactical/Lieutenant
  Order generation and temporary state effects remain distinct.
- This additive kind uses curated format v7 and the existing rules DB schema 5;
  published application DB schema and source normalization are unchanged.

## 0.7.0 declaration-category reconciliation (2026-09-23)

- Curated rules format v7 and `rules.db` schema/compatibility 5 replace the former
  Skill-only `skill-declaration-category` record kind with generic
  `declaration-category` records. They may classify Army Skills or Equipment while
  preserving the catalog domain of the referenced item.
- The six maintained N5.3 categories are Automatic, Deployment, Basic Short Skill,
  Short Skill, Long Skill, and ARO. `facts.typeId` must resolve to the canonical
  `skillTypes` vocabulary; deterministic display order is 10/20/30/40/50/60. `Entire
  Order` is not a seventh category.
- The focused reconciliation corrected BS Attack/CC Attack/Dodge/Forward Observer,
  Doctor/Engineer, Cyberplug/Paramedic, Parachutist, Triangulated Fire, and Berserk, and
  added Equipment-domain Short Skill classifications for Deactivator, GizmoKit, and
  MediKit.
- Declaration records are composition metadata, not ordinary rule-summary records.
  Skills without a reviewed declaration retain the uncited `Unclassified` fallback;
  Equipment receives no invented fallback category.

## 0.7.0 typed exact-source semantics (2026-09-23)

- Curated rules format v17 and `rules.db` schema/compatibility 7 require every
  `inheritance: source` definition to declare typed `variantSemantics.sourceVariant`.
  Supported kinds are numeric `level`, explicit `named`, and numeric
  `attribute-replacement`; family records may not declare source-variant metadata.
- Martial Arts source IDs 19-23 are reviewed Level 1-5 variants of the canonical
  `martial-arts` Skill family. Strategos source IDs 69-70 are reviewed Level 1-2
  variants of `strategos`. The family remains the browsing identity while exact source
  occurrences retain the Level that controls applicable rules.
- `RulesDatabase.catalog_source_variant_semantics()` exposes exact-source semantics.
  `SkillCatalog` attaches them as `source_variant` to matching Skill variants and Unit
  occurrences, while `CatalogRules` does the same for Equipment/Weapon usage variants.
  Browsers may label variants from structured data rather than inferring semantics from
  display-name suffixes.
- BS Attack source IDs 278 (`BS=12`) and 279 (`BS=11`), plus CC Attack source
  ID 274 (`CC=21`), are reviewed numeric Attribute replacements and are exposed
  through the same `source_variant` path. The UI renders their target/value from
  structured data rather than parsing the display name.
- TinBot is the first production use of the v9 `named` exact-source variant kind.
  Equipment IDs 169 (Firewall), 188 (Neurocinetics), 193 (Albedo), 244 (Discover),
  247 (ECM Guided), and 248 (Repeater) retain source-specific curated rules under the
  canonical TinBot browsing family. Their occurrence extras remain independent raw
  modifier data and are not interpreted by the named-variant classification.
- This does not classify generic parenthetical MOD syntax. PH replacement forms, bare
  signed values, rerolls, and Special Dice remain opaque until the owning rule supplies
  reviewed target/operation semantics; source-variant identity and occurrence parameters
  remain separate axes.
  
## 0.7.0 enrichment coverage audit (2026-09-23)

- `tools/audit_enrichment_coverage.py` is the maintained gate for measuring how much of
  the currently exposed Skill, Equipment, Weapon, Trait, and State application surface is
  actually enriched by the selected `rules.db`. It consumes a specific generated
  `infinity.db` plus `rules.db`; it does not infer coverage from curated JSON alone.
- The audit follows the same composition paths as the API: `SkillCatalog` for Skills,
  `CatalogRules` for Equipment/Weapons (including public catalog slugs before rules
  composition), and `TraitCatalog` for Traits. This intentionally catches enrichment
  that exists in rules storage but is not surfaced through the application contract.
- Gap codes currently cover missing rule definitions, unreviewed current contributions,
  missing citations, citation sources explicitly tied to an older N5 revision than
  their current collection, ambiguous family or exact-source routing, unresolved
  surfaced rule IDs, and related catalog/trait targets that do not resolve to an
  exposed identity. Rules-only Training/etc. relation targets are counted as supporting identities rather
  than false UI gaps. States are first-class audited surfaces through `StateCatalog`.
- Default JSON detail lists include only catalog items with gaps;
  `--include-complete` emits the full inventory. Report format v3 includes the rules-backed
  States catalog and also consumes the maintained
  `data/curated/enrichment-coverage/classifications.json` release-scope policy. Every known
  gap code must have an explicit classification and reason; item/relation overrides may mark
  reviewed exceptions as `intentional-omission`, `supporting-identity`, or
  `later-product-work`. Overrides that no longer match the selected database pair fail closed.
  Current defaults conservatively classify detected exposed-surface gaps as
  `release-blocker`, while non-UI rules-only relation targets are classified separately as
  supporting identities. This policy is release-planning metadata, not a second rules
  ontology; semantic classifications remain owned by canonical application identity plus
  curated rules data.

- Rules-interaction relationships are a core 0.7.0 product feature. Author semantic
  edges once, derive reverse navigation in `rules.db`, and present useful context from
  both endpoints. Multispectral Visor/Mimetism is the first production example: MSV authors
  `reduces-modifiers-from` toward Mimetism and the reverse relationship is derived for the
  Mimetism surface. Curated v11 extends the same graph with `negates-effects-of` and
  `ignores-modifiers-from`: Sixth Sense and Combat Instinct negate Stealth, while Combat
  Instinct ignores Surprise Attack MODs. Curated v12 adds `modifies-rolls-for` and
  `restricts-use-of`; Sensor uses them together with `reveals-state` and
  `ignores-modifiers-from` so its interactions are navigable from Discover, Camouflage,
  Camouflaged State, Hidden Deployment State, and Mimetism. Curated v13 adds
  `applies-effects-to` and `imposes-modifiers-on`; Reflective and Albedo use them toward
  Marksmanship and Multispectral Visor. Natural Born Warrior then reuses
  `ignores-modifiers-from` toward Martial Arts and Surprise Attack, with reverse navigation
  derived on both affected Skills while generic signed CC/weapon MOD semantics remain
  intentionally unmodeled. Curated v14 adds `overrides-effects-of`: No Cover takes precedence over Limited Cover when both restrictions apply, with the inverse relation derived automatically. Curated v15 adds `cancels-state`: Doctor and Engineer author cancellation edges toward reviewed States, and the new rules-backed State pages expose the derived reverse navigation. Curated v16 adds `causes-state`: Forward Observer causes Targeted, Reset cancels Targeted/IMM-B, and Targeted itself projects roll/restriction interactions to BS Attack, Discover, Reset, Cautious Movement, and Stealth. Curated v17 adds `enables-use-of`: reviewed Camouflaged and Hidden Deployment States satisfy Surprise Attack's documented state/form prerequisite, while Stealth uses the same relation toward Cautious Movement for its scoped ZoC/Hacking Area exception; remaining declaration requirements stay on the target rules. The same v17 contract now also models reviewed self-recovery without a grammar change: Dodge cancels IMM-A while IMM-A modifies that Dodge Roll; Reset cancels IMM-B and Isolated while those States modify the corresponding Reset Rolls. Keep this separate from 0.8 structural application
  relationships.
