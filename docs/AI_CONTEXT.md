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
  Exact runtime preservation copies the generated databases and complete local
  published symbol inventory on the same Git revision; reproducible rebuilds
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
- GitHub `Source checks` is configured to run the hermetic project checks on clean Windows,
  Ubuntu/Linux, and macOS Python 3.11 runners for pull requests, pushes to
  `main`, and manual dispatch, plus a Linux Python 3.14 compatibility leg. It
  uses the tracked synthetic Army fixture rather than live acquisition or ignored
  graphical assets. Each leg installs the symbol Python dependencies and runs
  pytest, full-tree Ruff linting, and Pyright through `run_checks.py`. Repository
  rules/branch-protection settings, not workflow YAML, determine whether GitHub
  blocks a merge on those checks.
- `Installed wheel smoke` is configured to build and install the wheel in a fresh virtual
  environment, validates installed `infinity-db` / `infinity-army` build commands
  and maintained config resources, then opens the generated Army/rules databases
  through the runtime application outside the checkout.
- `Full-asset checks` is configured as dispatch-only, restricted to `main`, and stages a private
  checksum-pinned published-asset ZIP from the `full-assets` GitHub environment
  before running `run_checks.py --assets required` once that environment is
  configured. It does not upload the
  graphical tree as an artifact, and it intentionally does not rerun the
  network/external-tool-sensitive symbol pipeline from raw inputs.
  Repository environment secrets must be configured before the manual job can
  succeed. See `docs/ci.md`.

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
- Army-list occurrences are authoritative for unit membership and availability.
  List presence, grouping, list kind, canonical ownership, optional availability
  category, and playability are separate semantics.
- The identity configuration does not map canonical-faction source ID `1` to
  `901` as ownership. Normalization preserves ID `1` as mercenary source/origin
  provenance and explicitly leaves `main_army_id` unset for canonical-1 units;
  901 remains the distinct Non-Aligned Armies grouping identity. A separate
  reviewed relationship in `data/curated/identities/army-display.json` derives
  `display_army_id` for presentation; current canonical-1 units display as 901.
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
  availability through the playable child NA2 lists.
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
  faction.
- The backend/API exposes explicit army role/playability semantics derived from
  metadata parent relationships and ordinary-list `reinforcements` links.
  `/api/armies` distinguishes main armies, sectorials, Non-Aligned forces,
  reinforcement lists, and grouping identities; the browser selector
  consumes that contract rather than Army-ID ranges. Grouping identity `901` is
  non-playable.
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
  dynamically. Schema version 12 additionally materializes reusable canonical
  profile payloads scoped to each logical unit plus one occurrence row per
  source profile. AVA, logo, source/profile-group keys, includes, and
  peripherals remain occurrence/source context; WIP, characteristics, skills,
  equipment, weapons, extras, and exact representation values remain in the
  payload and therefore split payload variants when they differ. The repository
  still reads source profile tables until behavioral-equivalence coverage is
  complete. Canonical loadout/unit payload work remains staged behind the same
  field-level invariance and provenance requirements. Legacy rediscovery remains
  only as a database-build compatibility path for older normalized inputs.
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

The current curated-v3 rules contract includes collection/source metadata,
maintained `skillTypes` and `labels` vocabularies with source-specific
`vocabularySources`, typed records, Army links, related-record links, review
state, and citations. Versions 1 and 2 must be migrated before ingestion. The
reserved `rules/example.json` template is excluded from directory ingestion.

The rules database has its own schema/versioning and replacement lifecycle. It
must not import Army JSON data, and Army database construction must not import
rules data. Application/service code may combine the two only through stable
application-level identities.

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
  `DISTANCE` versus text, while curated skill `parameterSemantics` supplies only
  rule-derived sign-display behavior for Super-Jump and Forward Deployment.
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
  occurrences. This is separate from the future canonical logical-unit/delta model.
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
