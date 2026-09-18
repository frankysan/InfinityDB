# InfinityDB backlog

This is the working backlog for performance work, data-pipeline improvements,
and possible product additions. Items are intentionally grouped by outcome
rather than by implementation layer.

Everything represented by an open checkbox is **planned/unimplemented work**,
even when its parent task contains completed substeps. This file does not define
current application behavior or claim that an accepted architecture is already
implemented; current behavior belongs in the relevant reference documentation,
while lasting design direction belongs in `docs/architecture.md` or
`docs/data-model.md`.

Keep completed substeps while their parent task is still open because they
clarify progress and remaining scope. Once a standalone or parent task is
complete, remove it after any durable outcome is recorded in `CHANGELOG.md`,
architecture/data-model documentation, or another appropriate reference. Git
history retains implementation detail.

## Next: performance

- [ ] Benchmark cold and warm requests per worker for unit lists, unit details,
  skills, equipment, and weapons. Record median and p95 timings against a
  representative snapshot before and after each performance change.
- [ ] Evaluate SQLite `immutable=1` for deployed snapshots. Enable it only when
  the process never observes an in-place database replacement.

## Database and data pipeline

- [ ] Establish a reproducible build/export performance baseline on CI or a
  fixed development host. A 2026-09-14 generated-snapshot smoke export measured
  8.45 seconds, 13.4 MB for the frontend DB, and 37.7 MB for the raw archive;
  treat those numbers as provisional until repeated in a controlled environment.
- [ ] Remove redundant whole-document work in the combined build/export path.
  Export validation serializes the complete normalized object to reject invalid
  JSON, while the raw archive serializes every row again and normalization has
  already run `validate_normalized`. Consider a hash-attested validation report
  or an in-memory hand-off that skips only the duplicate build-path pass; the
  standalone `export` command must retain full untrusted-input validation.
- [ ] Evaluate artifact-level deduplication for development builds. The raw
  archive contains 24.9 MB of row JSON, nearly the 25.2 MB normalized input,
  so retaining `normalized.json` and `infinity.raw.db` duplicates the same
  lossless data. Decide whether post-export development workflows need both,
  or document one as a regenerable/transient artifact.
- [ ] Prototype loadout payload templates, following the existing
  `option_weapon_templates` design. In the current snapshot, 52,554
  `option_weapons` links already share 490 payload templates; similarly,
  12,993 loadout-option rows have only 3,045 distinct payloads when their
  army/unit/group/option IDs and position are excluded. A template/link split
  could reduce repeated `name`, points, SWC, mini, and disabled values, but
  must be query-plan and database-size benchmarked before changing the
  read-optimized schema. 2026-09-14 probe: isolating the table and its unit
  index reduced 884,736 bytes to 819,200 bytes (64 KiB, 7.4%), while the
  largest unit-detail loadout query (368 rows) retained indexed access but was
  roughly 14% slower from the extra template primary-key lookup. The checked-in
  `infinity.db` has 3,045 loadout rows whereas `normalized.json` has 12,993,
  so regenerate aligned artifacts before treating this as a whole-database
  decision.
- [ ] Provide a small development CLI for `infinity.raw.db`: inspect a raw row,
  list raw rows by normalized table, and verify that an archive matches its
  frontend sibling's metadata.
- [ ] Define a paired-export replacement policy. The frontend and raw archive
  are currently built as temporary siblings; document and test recovery when a
  process stops between replacing either output.
- [ ] Add database-size reporting to `infinity-db build` so snapshot growth is
  visible in build output and CI.
- [ ] Decide whether dynamic, source-only columns should remain in the frontend
  schema or move exclusively to the raw archive once no runtime query consumes
  them.
- [ ] Establish a migration policy for future persistent user-authored data;
  imported snapshots are intentionally replaced wholesale today.
- [ ] Enforce Army snapshot source-version coherence at both acquisition and
  import boundaries. Pin the reported Army API version for one acquisition,
  verify every downloaded source document uses that same version, and recheck
  before committing the immutable snapshot so an upstream update during a
  sequential download cannot silently create a mixed-version archive. Merge and
  build validation must also reject mixed-version snapshots supplied from other
  sources unless a future explicit reviewed override is designed. Diagnostics
  should list the conflicting versions and affected source documents.
- [ ] Establish a regression baseline for tolerated source-data anomalies. Keep
  current source ambiguities non-fatal where the model intentionally preserves
  them, but record warning categories/counts for a known snapshot and flag new
  categories or unexpected growth on later snapshots. The 2026-09-10 merged
  snapshot audit observed 95 anonymous references, 5 placeholder units, 1
  placeholder catalog value, 14 unresolved Fireteam slugs, and 1 Fireteam member
  outside its army roster; verify these counts from aligned generated artifacts
  before making them an automated baseline.

## Configuration and domain knowledge

- [ ] Extract hard-coded Infinity-specific aliases, assumptions, corrections,
  and manual mappings from implementation code where they represent maintained
  project knowledge rather than algorithmic behavior.
  - Keep the distinction explicit:
    - `config/` contains InfinityDB-maintained interpretation, correction,
      mapping, and compatibility policy.
    - `data/curated/` contains human-reviewed information derived from identified
      external sources. `data/curated/rules/` is the current rules-database
      input; any sibling curated category must have explicitly implemented
      semantics before it is treated as an application input.
    - `data/manifests/` contains generated build/acquisition provenance and
      state rather than hand-authored project knowledge.
    - Code continues to own algorithms, schemas, parser mechanics, generic
      normalization behavior, validation, and application behavior.
  - The non-symbol audit is complete. Remaining maintained domain-name mapping
    work is limited to the unit-symbol semantics already tracked under the
    dedicated symbol-pipeline refactor below.
  - Require versioned schemas, validation on load, deterministic serialization
    where generated, focused regression tests, and portable project-relative
    paths for important configuration/manifests.
- [x] Add `config/catalogs/weapon-categories.json`.
  - Move the ordered weapon-family taxonomy and regex patterns out of
    `weapon_categories.py`.
  - Move manual weapon-ID category decisions into the same configuration.
  - Preserve category-rule order and validate that override targets name a
    declared category.
  - Keep the classifier implementation in Python: override lookup, ordered
    rule evaluation, and fallback behavior remain code.
- [x] Add `config/catalogs/weapon-overrides.json`.
  - Move known Army metadata corrections such as missing weapon profiles and
    source naming anomalies out of `weapon_profiles.py`.
  - Include an optional reason/source note so corrections remain reviewable
    when a new Army snapshot is imported.
  - Actual game-rule facts are intentionally excluded from this source-correction
    config.
- [x] Move `SPECIAL_WEAPON_DETAILS` out of `weapon_profiles.py` and into cited
  curated rules data.
  - Armed Turret statistics, equipment, skills, CC weapon, Army weapon linkage,
    and stable wiki revision citation now live in the curated N5 rules
    collection and are composed into weapon API responses through `rules.db`.
- [x] Move rule-derived skill declaration categories out of Python and into
  the curated rules layer.
  - N5 declaration categories now live in cited `skill-declaration-category`
    records linked to Army skill IDs, preserving edition/version and printed-page
    citations.
  - `SkillCatalog` composes declarations and ordinary skill rules from `rules.db`;
    the Army repository exposes source skill data only.
  - Skills without a curated declaration record remain `Unclassified` without a
    fabricated source citation.
- [x] Move trait rules-reference knowledge into curated data.
  - Concise summaries, canonical identities, exact aliases/misspellings,
    parameterized source-label prefixes, and citations now live in curated
    `trait` records and are consumed through `rules.db`.
  - [x] Remove the duplicate trait-canonicalization table from
    `catalog-detail.js`; API responses expose canonical trait identity, name,
    and slug while preserving the raw source trait label.
- [x] Review remaining hard-coded domain tables with the same decision rule:
  prefer derivation from authoritative imported data first, validated
  configuration second, cited curated rules third when the value is external
  rules knowledge, and code only when the value is implementation behavior.
  - [x] Derive weapon-range display bands from the sorted union of finite,
    positive `metadata_weapons.distance[].max` values used by the displayed
    weapon profiles. Inch labels are derived from the same centimetre endpoints
    through the existing 2.5 cm conversion; no maintained range-band config is
    needed.
  - [x] Move Armed Turret metadata-profile suppression out of the repository and
    into `config/catalogs/weapon-overrides.json`. Normalization applies the exact
    source-row matchers before metadata rows are materialized, while the original
    Army metadata envelope remains preserved for provenance.
  - [x] Make skill-extra distance typing source-driven and move display-only
    sign conventions into curated skill parameter semantics. Army `extras.type`
    now decides whether an extra is a distance (`DISTANCE` versus `TEXT`), so
    numeric text such as `+5 CC` needs no exception. Curated `Super-Jump` and
    `Forward Deployment` records carry the remaining positive-sign display
    semantics, and browser code consumes the API contract without skill-name
    branches.
  - [x] Move reinforcement-prefix normalization (`REINF` / `REFUERZOS`) into the
    maintained identity policy. Backend unit-detail payloads now expose a
    prefix-stripped profile `display_name` alongside the untouched source `name`
    and normalized `profile_identity`, so browser code no longer carries a
    duplicate reinforcement-prefix regex.
  - [x] Remove the direct `901` Non-Aligned grouping special case. Grouping
    identities are derived structurally from ordinary imported-list hierarchy:
    self-parented parents remain main armies, while imported parents that are
    not self-parented (and referenced metadata-only parents) become non-playable
    grouping nodes. Current source list `901` has metadata parent `900`, parents
    the NA2 child lists, and retains a real source roster; runtime classification
    does not know the numeric ID.
  - [x] Keep non-playable grouping source rosters such as `901` as preserved
    source/provenance data without adding a dedicated application roster API.
    `playable: false` does not imply an empty source list; application unit access
    remains through the playable child army occurrences that carry availability.
  - [x] Revisit unit-symbol semantic name tables during the dedicated symbol
    pipeline refactor rather than moving those mappings into unrelated
    configuration in this branch. The remaining work is tracked under the symbol
    pipeline section below.
  - Keep API-source table wiring such as `METADATA_TABLES`, schema definitions,
    generic merge/normalization algorithms, Unicode normalization mechanics,
    database behavior, distance-unit conversion, range-modifier CSS classes, and
    UI preference mechanics in code.

## Canonical logical-unit model

- [ ] Evaluate a canonical logical-unit payload/delta model.
  - Audit fields for invariance across every materialized logical unit before
    promoting them to shared canonical data.
  - Store army-specific membership/availability, loadout/profile differences,
    and other true variations as explicit deltas rather than repeated full unit
    payloads where this can be done losslessly.
  - Preserve source IDs, exact raw provenance, and reconstructability of the
    imported Army data even when invariant application fields are deduplicated.
  - Treat this as a data-model refactor distinct from the completed maintained-
    domain-knowledge extraction work.

## Army snapshot and symbol pipeline

- [ ] Replace the current migration-oriented symbol workflow with one
  reproducible, manifest-backed pipeline tied to a single pinned Army snapshot.
  - [x] Keep acquisition and processing tools independently runnable for
    debugging and targeted maintenance; orchestration must call reusable logic
    rather than duplicate it.
  - [x] Standardize standalone acquisition output through the shared snapshot
    archive helper. Army, wiki, and symbol downloaders stage loose files in a
    temporary directory and persist only complete `JSON YYYYMMDD-HHMMSS.zip`,
    `WIKI YYYYMMDD-HHMMSS.zip`, or `SYMBOLS YYYYMMDD-HHMMSS.zip` archives.
    Timestamp collisions receive `-2`, `-3`, and so on rather than overwriting
    an existing snapshot.
  - [x] Keep `download_army_json.py` explicitly invoked and networked only on
    demand. It already downloads/validates metadata, downloads every faction
    listed by metadata, validates each Army document, stages through temporary
    files, and writes one complete timestamped ZIP snapshot.
  - [x] Make the wiki and current symbol downloaders follow the same durable
    output lifecycle as Army acquisition. The wiki downloader no longer keeps
    a dated unpacked mirror as its primary output, and the symbol downloader no
    longer incrementally fills a long-lived loose destination directory.
  - [x] Add shared, versioned snapshot-provenance and annotation contracts using
    the existing data-path design rather than adjacent sidecars.
    - Army, wiki, and symbol acquisition now write deterministic SHA-256-bound
      provenance under `data/manifests/snapshots/`, with archive-hash
      verification and portable project-relative paths where applicable.
    - Human-authored descriptions, comparison targets, and ordered notable
      changes use the separate versioned contract under
      `data/curated/snapshot-notes/`; acquisition tooling never mutates them.
    - Generated manifests are ignored by Git, excluded from Docker build
      context, retained until explicitly removed, and never replace Corvus
      Belli's source `metadata.json`.
    - Regression coverage validates all three snapshot types, symbol input
      provenance, deterministic serialization, immutable archive-labeled
      records bound to SHA-256, archive verification, and annotation references.
  - [ ] Let future snapshot-comparison tooling write structured generated diff
    data/reports under manifest/report paths while curated snapshot notes remain
    the human interpretation of those results.
  - [ ] Rewrite the wiki downloader/packager provenance handoff together with
    the curated wiki provenance contract.
    - Preserve the current checked-in legacy wiki source identity until an
      authoritative migration can establish which timestamped archive replaces
      it; do not fabricate archive/hash provenance from the date alone.
    - Migrate curated wiki sources to exact recorded `WIKI ...zip` identity/hash
      once the new packager provides that identity.
    - Replace the current mixed `vocabularySources` locator requirement
      (`path`/`snapshotDate`/`heading`/`page`) with source-appropriate provenance
      so wiki vocabulary references do not require a printed-page field merely
      because PDF vocabulary references need one.
    - Update the curated loader/schema, existing v5.3 collection, examples,
      validation tests, and documentation together.
  - [ ] Add a thin `tools/build_symbols.py` orchestrator with mutually exclusive
    offline `--snapshot PATH` and explicit online `--fetch-snapshot` modes.
    Once selected or downloaded, pin archive path/name, SHA-256, language,
    acquisition timestamp, API base URL, and source-document count; every
    downstream symbol stage must consume that same snapshot rather than select
    a newer one independently.
  - [ ] Keep normal project builds offline. Snapshot and symbol refreshes remain
    separate, intentional operations; `--snapshot-only`, `--language`,
    `--data-root`, `--static-root`, `--jobs`, `--image-overrides`,
    `--static-symbols`, `--refresh-symbols`, `--skip-symbol-download`,
    `--skip-compression`, `--keep-work`, and `--dry-run` are candidate
    orchestrator options as those stages are integrated.

- [x] Replace first-logo-per-unit symbol discovery with complete source-semantic
  discovery keyed by source reference/URL rather than unit ID.
  - Treat every `units[].profileGroups[].profiles[].logo` as authoritative for
    unit/profile symbols and every `metadata.json -> factions[].logo` as
    authoritative for faction symbols.
  - Treat `resume[].logo` as a validation/consistency source only; it is not
    complete enough to drive discovery.
  - Recursively audit every source string for SVG references and compare that
    set with semantic discovery. Unknown SVG-bearing fields must be reported
    with their JSON paths and URLs and must not be silently ignored; fail by
    default or require an explicit reviewed allowlist decision.
  - Preserve every reference even when download URLs repeat or visual
    deduplication later collapses assets. One unit may reference several SVGs,
    and several units/profiles may reference one source SVG.
  - [x] Rename/refactor `download_unit_symbols.py` to `download_army_symbols.py`
    so it covers unit/profile and faction assets plus validated maintained
    static symbols, without generating final browser mappings. Preserve its
    timestamped `SYMBOLS ...zip` snapshot output.
  - Preserve the 2026-09-10 snapshot audit as a regression baseline, not a
    permanent source count: 59 JSON documents (`metadata.json` + 58 Army
    documents), 5,020 profile-logo references / 1,033 unique unit SVG URLs,
    58 faction-logo references / 57 unique faction SVG URLs, 1,090 unique SVG
    URLs in total, 4,137 `resume` references / 862 unique resume URLs, and zero
    unknown SVG locations. The old first-logo-per-unit behavior found only 861
    unique unit SVGs, missing 172 distinct SVGs; 136 unit IDs referenced more
    than one profile logo.

- [x] Define the acquisition-only version-1
  `data/manifests/army-symbol-build.json` as the first authoritative
  machine-readable state passed into later symbol processing.
  - [x] Separate `snapshot`, `assets`, and `references`; do not use a
    filename-keyed structure that conflates source assets with their consumers.
  - [x] Snapshot records include the pinned Army artifact identity/hash, the
    corresponding `SYMBOLS ...zip` identity/hash, acquisition timestamp, and
    source-document count.
  - [ ] Enrich the build snapshot record with Army language/API base/version by
    resolving the selected Army snapshot provenance when orchestration is added.
  - [x] Acquisition asset records retain source URL/filename/hash, deterministic
    raw archive path, and source method. Font classification, alias
    normalization, duplicate/canonical identity, conversion, compression, and
    final published path remain later-stage manifest extensions.
  - [x] Reference records retain source document, JSON path, authoritative/audit
    status, reference kind, unit/faction/army IDs and slugs as applicable,
    static semantic keys/categories, and source asset URL.
  - [x] Persistent artifact paths are portable project-relative POSIX-style
    strings where applicable; raw archive member paths are POSIX-relative.

- [ ] Complete the static-symbol and local-override model as maintained project
  knowledge rather than downloader code.
  - [x] `config/symbols/static-symbols.json` already declares the known
    non-API assets: characteristics `cube`, `cube2`, `hackable`, `peripheral`
    and orders `regular`, `irregular`, `tactical`, `lieutenant`, `impetuous`,
    all under the stable Corvus Belli icon base URL.
  - [x] Extend current static declarations with stable key, category, source
    filename, and user-facing label. Add further known source-name metadata only
    when a concrete processing/publishing need appears.
  - [ ] Keep local `image_overrides/` outside version control, organized by
    explicit categories such as `units/`, `factions/`, `characteristics/`, and
    `orders/`. Use stable URL-derived logical names/categories as lookup keys,
    not generated publication filenames.
  - [ ] Resolve each asset strictly in this order: matching local override,
    existing validated immutable symbol snapshot/cache, then upstream network
    download. A valid override suppresses all network access for that asset; an
    invalid matching override is an error and must not silently fall back
    upstream.
  - [ ] Report unused overrides and filename collisions. Preserve provenance
    such as origin URL, resolved local source, source method, source/override
    SHA-256, and whether an upstream download occurred.
  - [ ] Keep corrected derivative SVG content uncommitted unless redistribution
    rights are established. Committed metadata may document recommended local
    overrides and their reasons; `cube.svg` is the known case where the upstream
    asset renders with horizontal raster/mask artifacts.
  - [ ] Run overrides through the normal processing pipeline by default. Add a
    `publish_as_is` escape hatch only if a concrete future use case justifies it.

- [ ] Treat timestamped symbol archives as the immutable raw acquisition
  artifacts and keep extraction/work, generated state, reports, overrides, and
  published assets conceptually separate.
  - [x] The current symbol downloader stages a complete run temporarily and
    writes one `SYMBOLS YYYYMMDD-HHMMSS.zip` archive rather than leaving loose
    downloaded SVGs in the destination directory.
  - Use roots equivalent to `data/raw/` for Army `JSON ...zip` snapshots,
    `data/raw/symbols/` for `SYMBOLS ...zip` snapshots, `data/work/symbols/` for
    transient extracted/processed files, generated `data/manifests/`,
    `data/reports/`, local `image_overrides/`, and the final
    `src/infinity_db/web/static/` publication tree.
  - Never rename, rewrite, normalize, compress, or delete a timestamped raw
    archive during later processing. Extract selected archives into temporary or
    work locations when loose SVG files are needed.
  - Reuse validated archived assets/cache before network access where practical;
    explicit refresh creates a new timestamped archive rather than mutating an
    old one. Treat URL-to-filename collisions as errors requiring deterministic
    disambiguation.

- [ ] Consolidate SVG audit, font handling, and complete-set duplicate detection
  around one structured manifest.
  - [ ] Add `config/symbols/font-aliases.json` for Infinity-asset-specific
    legacy/exported font-reference overrides. Keep generic CSS family handling,
    weight/stretch interpretation, cmap-suffix recognition, installed-font
    discovery, and matching algorithms in code.
  - Audit all resolved categories for SVG parse errors, active text, referenced
    fonts, available/missing fonts, alias normalization, and unused declarations.
  - Deduplicate across the full resolved raw set before expensive text-to-path
    conversion: SHA-256 exact groups first, then visual duplicate detection with
    `resvg` using the established production default of 4 jobs.
  - Use deterministic canonical ranking: `no_active_text`, then
    `fonts_available`, then `fonts_missing`, then parse/unknown errors, followed
    by shorter filename and alphabetical source path/name. A failed or
    inconclusive visual comparison keeps an asset unique rather than removing it.
  - Removing a duplicate from active processing must never remove its source
    references; each original URL continues to point at the selected canonical
    asset in the manifest.

- [ ] Keep text-to-path conversion limited to canonical assets that still have
  active text and resolvable fonts.
  - Use persistent `inkscape --shell` workers as the production backend with 4
    jobs, launched directly with `subprocess.Popen()` pipes rather than through
    a shell. Keep one-shot Inkscape as fallback/debugging.
  - Keep `usvg` experimental only; real font-heavy symbol tests produced visible
    differences from the intended rendering.
  - Validate that converted SVGs parse, meaningful active `<text>` is gone,
    empty text placeholders are removed when safe, and namespaces remain valid.
    Failed conversion must not replace or masquerade as a verified canonical
    source.
  - Treat the roughly 8-9 second Windows Inkscape startup cost as an accepted
    external-tool limitation for now. Clean-profile testing did not remove it;
    persistent workers are the mitigation rather than continued startup chasing.

- [ ] Keep `svg_compress.py` reusable while integrating compression into the
  manifest-backed build.
  - Preserve production defaults: `balanced` profile, `resvg` validation,
    precision `p2` first and `p3` rescue, target sizes 32/64, DPR 1/2, maximum
    RMS 0.01, maximum changed fraction 0.01, and pixel-difference threshold 8.
  - Compress canonical assets only. If no lossy candidate passes visual
    validation, retain the validated lossless/path-only output.

- [ ] Refactor `reorganize_symbols.py` from destructive migration tooling into
  a non-destructive publisher.
  - Consume the pinned snapshot, authoritative build manifest, and final
    canonical/compressed asset directory; copy/materialize outputs rather than
    move or delete source/work files.
  - Build a temporary publication tree, validate it, and atomically replace the
    generated published tree only after success so a failed run leaves the prior
    assets intact.
  - The publisher alone defines final application paths after deduplication,
    conversion, compression, and organization. Generate `army-symbols.js` and
    `unit-symbol-map.js` here, not in a downloader, and remove legacy
    first-symbol-wins assumptions once this publisher is authoritative.
  - Preserve stable ID/slug application conventions where practical. The useful
    unit convention is `units/<army-slug>/<unit-id>-<unit-slug>.svg`; faction
    assets should use an ID/slug form such as
    `armies/<faction-id>-<faction-slug>.svg` or the existing compatible format.
    Decide the exact canonical physical naming before changing browser mappings.
  - Permit several source/unit references to map to one canonical physical SVG.

- [ ] Refactor stage scripts into thin CLIs over reusable Python functions and a
  small shared symbol-pipeline utility layer.
  - [x] `snapshot_archive.py` centralizes the timestamped ZIP naming, collision
    handling, and deterministic archive member ordering shared by the Army,
    wiki, and symbol downloaders.
  - `download_army_json.py`: expose snapshot identity/result to callers while
    keeping its standalone CLI and explicit network behavior.
  - `download_army_symbols.py`: own complete discovery, static declarations,
    override/cache/network source resolution, recursive SVG audit, and manifest
    reference/asset updates while retaining complete timestamped archive output.
  - [ ] Make the symbol-downloader input contract match its CLI and tests. Prefer
    the immutable raw Army ZIP as the authoritative input; either fully support
    directory/current merged-master inputs end to end or stop advertising them.
    In particular, do not claim legacy/current `master.json` compatibility unless
    discovery can consume that schema without treating ordinary embedded SVG
    references as unknown fields.
  - `svg_processor.py`: keep font audit, alias normalization, complete-set
    duplicate detection, deterministic representative ranking, persistent
    Inkscape conversion, and reports; add structured manifest updates and
    multi-category processing.
  - `svg_compress.py`: keep the standalone CLI and production validation
    behavior; expose an importable result/update path for orchestration.
  - `reorganize_symbols.py`: become the publisher and final mapping generator.
  - `path_sanitization.py`: remain shared infrastructure for external/mirror
    naming; pipeline-generated asset names should use one host-independent
    policy.
  - Longer-term reusable modules may be split into `snapshot`, `discovery`,
    `manifest`, `downloader`, `audit`, `deduplicate`, `convert`, `compress`, and
    `publish` helpers when that reduces duplication rather than adding ceremony.

- [ ] Make every integrated symbol stage idempotent and traceable before adding
  sophisticated incremental caching.
  - [x] Timestamped Army, wiki, and symbol acquisition never overwrites an
    existing archive; same-second collisions receive a deterministic numeric
    suffix.
  - Changes to an override SHA-256 invalidate downstream processing for that
    asset. Removing an override falls back to validated symbol archives/cache or
    network by the normal resolution rules.
  - Reuse validated archived downloads and rebuild work deterministically.
  - After the integrated build is stable, consider cache keys based on snapshot
    SHA-256, source SVG SHA-256, processor/tool versions, font-alias config,
    duplicate renderer/settings, conversion backend/settings, and compression
    profile/settings.

- [ ] Preserve conservative failure behavior throughout symbol processing.
  - Partial/invalid snapshot acquisition must not continue or replace prior
    snapshots/publication.
  - Unknown SVG source locations require explicit review.
  - Invalid matching overrides fail; failed network downloads leave existing
    archives untouched and prevent creation/publication of an incomplete
    replacement snapshot.
  - SVG parse/font errors are retained and reported rather than discarded.
  - Duplicate-render uncertainty keeps assets unique.
  - Text conversion failure retains the verified source rather than claiming a
    successful replacement.
  - Compression falls back to a validated lossless/path-only asset.
  - Publication failure leaves the previous published tree intact.

- [ ] Standardize symbol-pipeline reports around detailed machine/human outputs
  plus one concise build summary.
  - Preserve/report discovery counts, unknown SVG references, font audit,
    missing fonts, unused font declarations, SVG parse errors, duplicate groups,
    duplicate-render errors/separation/summary, text-to-path results/summary,
    compression report/candidates/run metadata, overrides used/unused, raw-cache
    hits, network downloads, manual static assets, canonical counts, published
    asset counts, application-mapping counts, and per-stage/total runtime.
  - Existing report filenames from the plan may be retained where useful:
    `symbol-discovery.csv`, `unknown-svg-references.csv`, `svg-font-report.csv`,
    `missing-fonts.csv`, `unused-font-declarations.csv`, `svg-parse-errors.csv`,
    `duplicate-groups.csv`, `duplicate-render-errors.csv`,
    `duplicate-separation.csv`, `duplicate-summary.csv`,
    `svg-text-to-path-report.csv`, `text-conversion-summary.csv`,
    `compression-report.csv`, `compression-candidates.csv`, and
    `compression-run.json`.

- [ ] Add focused end-to-end and cross-platform regression coverage for the
  integrated Army/symbol pipeline.
  - [x] Dedicated Army, wiki, and symbol downloader tests cover their timestamped
    archive naming and deterministic archive contents.
  - Snapshot/discovery tests: metadata/faction validation, complete archive,
    snapshot identity/hash, all profile/faction logos, multiple logos for one
    unit, one logo shared by units, duplicate URLs, static declarations,
    override suppression of network, override over cache, invalid/unused
    overrides, filename collisions, unexpected SVG fields, and proof that
    `resume` is not required for complete discovery.
  - SVG fixtures: exact duplicate, XML-different visual duplicate, no-text,
    normal text, alias-font, missing-font, empty-text cleanup, and troublesome
    real-world conversion cases.
  - Publisher tests: several references to one canonical asset, faction assets,
    deterministic paths, no destructive raw/work mutation, and failed build
    preserving the prior static tree.
  - Run core portability coverage on Windows, Ubuntu/Linux, and macOS when CI
    permits: project-relative path generation, path sanitization, executable
    discovery including `.exe`/`.cmd`, subprocess argument construction without
    shell quoting, temp files, case-only collisions, snapshot ZIP handling,
    override lookup, static-symbol manifest loading, atomic replacement, and
    Windows `spawn` compatibility. External-tool integration tests may be
    conditional when Inkscape, `resvg`, or SVGO are unavailable.
  - Add a shared utility layer for executable discovery, native/project-relative
    path conversion, atomic writes, subprocess invocation, and platform-neutral
    generated filenames before orchestration otherwise duplicates those rules.

- [ ] Preserve the intended normal workflow once orchestration exists:
  `Army snapshot -> discover API symbols -> add static symbols -> audit unknown
  SVG sources -> resolve override/archive-cache/network -> write complete symbol
  snapshot -> extract/work classify fonts -> deduplicate -> select canonical ->
  convert text -> compress -> publish -> generate mappings -> validate -> report`.
  Offline rebuilds use known timestamped archives; fresh acquisition is an
  explicit separate mode.

## Distribution, documentation, and test reproducibility

- [ ] Align all documentation and packaging language with the current
  third-party graphical-asset redistribution policy.
  - State explicitly that Corvus Belli graphical assets are **not bundled with
    InfinityDB source code or redistributable releases by default**. Public
    availability from Corvus Belli asset hosts is not treated as permission to
    redistribute the files, and InfinityDB's MIT License does not relicense
    them.
  - Keep raw symbol snapshots, processed symbols, locally corrected derivatives,
    and locally published runtime copies ignored/uncommitted unless explicit
    redistribution permission covering the intended distribution form has been
    established.
  - Distinguish local application publication from redistribution: the symbol
    pipeline may acquire/process/publish assets into a local installation's
    runtime static tree, while source archives, wheels, GitHub releases, Docker
    images distributed by InfinityDB, and similar prebuilt artifacts must exclude
    those graphical assets under the current rights assumption.
  - [x] Correct current wording that implies bundled assets in `README.md`,
    `docs/architecture.md`, `docs/deployment.md`, and
    `THIRD_PARTY_NOTICES.md`; keep historical CHANGELOG entries intact when they
    accurately describe past behavior. Use `docs/AI_CONTEXT.md` and the existing
    symbol-pipeline rights invariant as the policy baseline rather than creating
    a competing rights contract.
  - Document how a clean/local deployment obtains required runtime symbols
    separately from the source/release artifact, and make that acquisition step
    explicit rather than solving the problem by committing or redistributing the
    third-party artwork.
- [ ] Make asset-dependent tests hermetic. Replace assumptions that ignored,
  locally generated Corvus Belli SVG trees already exist with project-owned test
  fixtures or an injectable temporary static root. Test the absence/presence
  behavior deliberately so a clean source archive can pass the suite without
  third-party graphical assets.
- [ ] Make version tests independent of incidental Git-checkout state. Test the
  `+dev` display suffix with controlled repository/version inputs instead of
  requiring every source archive or detached release tree to contain Git metadata
  and be ahead/dirty.
- [ ] Expand the normal project check runner to cover the complete maintained
  standalone-tool surface. Lint all maintained scripts under `tools/` and add
  focused regression tests for currently uncovered tools such as
  `svg_processor.py`, `svg_compress.py`, and `snapshot_archive.py`, allowing
  conditional external-tool integration where appropriate.
- [ ] Integrate curated snapshot-note validation into routine project checks so
  every checked-in file under `data/curated/snapshot-notes/` is schema-validated
  even when no downloader or comparison workflow happens to load it.
- [ ] Reduce duplicated normative documentation after correcting the audit
  drift. Keep imported-data/identity contracts authoritative in
  `docs/data-model.md`, filesystem/provenance layout in `data/README.md`,
  architecture rationale in `docs/architecture.md`, and concise invariants in
  `docs/AI_CONTEXT.md`; replace repeated contract text with links where practical.
  As part of this pass, remove stale statements that call the already-implemented
  `army-symbol-build.json` or snapshot-manifest work merely planned/future work.


## Visual design, frontend architecture, and theming

- [ ] Define and document InfinityDB's visual-design and UI/UX guiding
  principles before larger presentation changes.
  - Optimize first for fast lookup, comparison, and scanning of dense game data;
    prefer clarity, hierarchy, and legibility over decorative complexity while
    avoiding an unnecessarily cramped interface.
  - Keep navigation, page hierarchy, terminology, controls, tables, cards,
    badges, and feedback states predictable across catalog and detail views.
    Extend shared design-system primitives instead of giving individual pages
    their own visual language.
  - Use progressive disclosure for secondary, provenance, and developer-only
    information so technical depth remains available without overwhelming the
    default reading flow.
  - Treat responsive behavior as a content-priority decision rather than simple
    shrinking. Define deliberate phone, tablet/compact, and desktop behavior for
    navigation, filters, tables/statlines, detail groups, and multi-column data.
  - Treat accessibility as part of the design contract: semantic HTML, complete
    keyboard operation, visible focus, sufficient contrast, non-color-only
    meaning, useful touch targets, reduced-motion support where motion exists,
    and sensible screen-reader labels/status announcements.
  - Keep theme and faction/army accent colors subordinate to semantic meaning.
    Source/domain state must remain understandable regardless of selected theme,
    color perception, or whether a particular graphical asset is available.
  - Preserve the current lightweight/browser-native direction unless a concrete
    requirement justifies changing it. New visual work should not implicitly
    introduce a frontend framework or build pipeline.
  - Once agreed, record durable principles in the canonical architecture/design
    documentation and keep this TODO focused on remaining implementation work.

- [ ] Define a clearer backend/frontend responsibility boundary and reflect it
  in source organization without changing the current same-origin deployment
  model merely for architectural fashion.
  - Backend Python owns imported-data/domain semantics, identity and rules
    interpretation, database access/querying, request validation, stable API
    contracts, application/version metadata, and HTTP concerns. Domain meaning
    that would otherwise require browser code to infer IDs, names, source quirks,
    or rules semantics belongs in backend/API fields.
  - Frontend code owns information presentation, interaction state, responsive
    behavior, accessibility behavior, client-side display formatting, theme/UI
    preferences, and composition of semantic API data into views. It must not
    duplicate maintained domain interpretation already represented by the
    backend contract.
  - Keep API payloads semantic rather than presentational: expose roles, states,
    identities, labels, and relationships rather than CSS class names, literal
    colors, layout instructions, or page-specific markup.
  - Split the current Python web layer so API handling, shared page-shell/static
    delivery, and top-level request dispatch are visibly separate concerns.
    Keep existing URLs and the shared shell contract stable while doing so.
  - Organize the browser side around explicit shared layers (API transport,
    preferences/theme state, reusable view/components, and page modules) so page
    scripts stop accumulating cross-cutting behavior. Continue routing browser
    HTTP access through `api.js` rather than ad hoc `fetch()` calls.
  - Preserve native ES modules and the no-frontend-build-tool decision for now;
    source-tree separation should improve ownership and maintainability without
    requiring bundling/transpilation.
  - Add focused contract/regression coverage as responsibilities move so a
    frontend refactor cannot silently recreate backend domain logic, and backend
    changes cannot silently break established browser contracts.

- [ ] Introduce first-class customizable theme support, with Light and Dark as
  the initial themes and an extension contract that does not require component
  rewrites when more themes are added later.
  - Refactor the CSS token model into semantic theme tokens versus theme-neutral
    layout/component rules. Components should consume tokens such as surfaces,
    text, borders, actions, focus, status, shadows, and data emphasis rather than
    hard-coded light-theme colors.
  - Keep faction/army colors as domain accent tokens layered onto the selected
    theme. Define contrast-safe treatments for both Light and Dark rather than
    assuming the current accent/background pairings work unchanged in both.
  - Define a stable theme identifier/preference contract (`light` and `dark`
    initially), and decide/document default startup behavior such as following
    the operating-system preference versus a fixed project default. An explicit
    user selection must take precedence over the default.
  - Integrate the theme selector with the existing Settings/preferences model.
    Theme changes apply immediately; persistence follows the existing
    remember-settings consent policy rather than creating an unrelated storage
    mechanism.
  - Resolve and apply the selected theme before first meaningful paint to avoid
    a light-to-dark or dark-to-light flash during navigation/reload.
  - Replace hard-coded light-only browser metadata/assumptions with theme-aware
    `color-scheme` behavior so form controls, scrollbars, and other user-agent UI
    remain coherent with the selected theme.
  - Keep the InfinityDB logo and other project-owned themed graphics driven by
    the same semantic token contract where practical; do not fork separate
    light/dark asset files when CSS-variable theming is sufficient.
  - Audit status colors, range-modifier colors, links, focus indicators, muted
    text, tables, selected rows, dialogs, menus, and faction accents for contrast
    and distinguishability in every supported theme.
  - Add regression coverage for preference initialization/switching/persistence
    and representative core pages in both themes. Consider targeted visual
    regression screenshots at compact and desktop widths once the theme tokens
    stabilize.

- [ ] Refactor the frontend design-system structure after the principles and
  theme contract are agreed.
  - Review the current monolithic `styles.css` and separate foundational tokens,
    theme values, shared components/layout, and page-specific exceptions where
    doing so improves ownership without requiring a CSS build step.
  - Inventory repeated or one-off component styles and either promote recurring
    patterns to shared primitives or remove unnecessary variants. Avoid adding
    new page-local copies during the transition.
  - Define which responsive/layout behaviors are shared primitives versus
    intentional page-specific composition, and document the small set of
    supported density variants rather than allowing arbitrary per-page spacing.
  - Keep existing shared shell, navigation, detail-group, table-density, badge,
    and settings patterns working during the migration; visual cleanup should be
    incremental rather than a simultaneous rewrite of every page.

## Reliability and operations

- [ ] Establish production load monitoring and a repeatable capacity test for
  the Docker deployment.
  - Record host and container CPU, memory, swap, disk-space/inode, disk-I/O,
    and network utilization; retain Docker restart/OOM events and Caddy and
    Gunicorn error logs. Alert on sustained CPU saturation, memory pressure or
    OOM kills, low disk space, elevated 5xx responses, and failed health checks.
  - Publish Caddy access-log metrics (request rate, status code, latency, and
    active connections) and application metrics for dynamic API latency. Keep
    dashboards split between static assets and `/api/` requests.
  - Define a representative load-test scenario: browse the unit list, search,
    open unit/catalog details, and fetch API endpoints using a current
    production-like SQLite snapshot. Include a warm-cache steady-state run and
    a short burst run; do not benchmark only the health endpoint.
  - Establish a baseline at 2 Gunicorn workers x 4 threads, then test 4 x 4
    only with a matching 4-vCPU/4-GiB container allocation. Record p50/p95/p99
    latency, request/error rate, CPU, memory, and SQLite/disk behavior at each
    concurrency level.
  - Set an explicit scale trigger (for example, a sustained p95 latency or
    error-rate SLO breach while CPU is not otherwise constrained). Prefer
    multiple immutable app replicas behind Caddy over unbounded worker growth;
    re-run the test before changing worker counts or deployment resources.
- [ ] Add a benchmark/health-check command that validates the frontend database,
  confirms its expected raw archive when requested, and reports schema and
  compatibility revisions.
- [ ] Complete deployment validation coverage.
  - [x] Build and package `rules.db` alongside `infinity.db` for the Docker
    deployment. The image explicitly configures the rules path, so a missing or
    invalid `rules.db` now fails worker startup instead of silently shipping a
    reduced feature set; local/development auto-discovery remains optional.
  - [x] Test a full synthetic Army/rules build and production container startup
    in CI. The deployment smoke workflow validates both runtime databases,
    requires `/app/data/` to contain only those intended database artifacts,
    exercises the read-only/non-root Gunicorn startup and health check, and
    rejects ignored Corvus Belli graphical-asset trees in redistributable
    images.
  - [ ] Test local asset publication separately from distributable-image
    construction so a local installation can exercise acquired symbols without
    weakening the release-image redistribution boundary.

## Potential product features

- [ ] Expand the existing versioned curated rules-reference infrastructure with
  substantially broader N5 v5.3 coverage from
  `data/pdf/rules/n5-rules-v5-3-en.pdf` (dated 2026-08-10).
  - [x] Keep curated rules in their own source-controlled JSON layer and
    independent `rules.db`; do not add PDF-derived facts to `infinity.db` or
    `infinity.raw.db`.
  - Expand canonical rule identities across skills, equipment, ammunition,
    traits, states, Fireteam concepts, glossary terms, and other useful rule
    domains, retaining rulebook version and printed-page citation.
  - Store original, concise editorial summaries and structured facts (labels,
    requirements, effects, restrictions, related rules, and page locators),
    rather than bulk-extracting or serving copyrighted PDF text or artwork.
    Confirm permissions and attribution/linking requirements before publishing
    any rule-derived prose.
  - Add a coverage report that flags Army metadata items with no matching
    reference entry, ambiguous names/levels/MOD variants, and entries whose
    cited rulebook version is stale. A prior-version comparison is needed before
    claiming a specific change between rulebook revisions.
- [ ] Add a dated FAQ/errata layer to the existing rules-reference system from
  current material under `data/pdf/faq/`.
  - Model each ruling as a question, concise answer, rule/topic links,
    applicable scope, document version/date, and source-page citation; do not
    flatten it into the base-rule summary. This preserves the distinction
    between a rule and a later clarification, and permits an answer to be
    superseded cleanly.
  - Prioritize links to features already represented by the app: deployment
    and private-information handling; BS Attack/MOD and template behavior;
    hacking Firewall; Marker, Camouflage, Peripheral, and State interactions;
    Coordinated Orders; and Fireteam creation/bonuses/integrity. The FAQ also
    contains scenario-specific rulings, so scope them to the relevant ITS
    season and mission rather than presenting them as universal core rules.
  - Define an explicit source-precedence and effective-date policy. An on-screen
    answer must show its source date/version and never silently blend conflicting
    documents.
- [ ] Build a versioned ITS reference library from material under
  `data/pdf/its/` and `data/pdf/legacy/`, keeping the current season distinct
  from archived seasons.
  - Keep season content isolated by season and effective date. A user choosing
    a prior event must see its matching scenario, objectives, extras, and FAQ
    rulings rather than a mixture of seasons. Retain a curated, human-reviewed
    change log/diff rather than relying on raw PDF text diffing.
  - Treat the official Army app/site as the authority for army-list legality.
    InfinityDB may provide read-only explanation and planning support, but must
    label its snapshot/date and avoid claiming tournament validation.
- [ ] Add ITS scenario list and detail pages backed by a curated seasonal data
  model, rather than PDF excerpts.
  - Capture structured, cited scenario facts: objectives and scoring, game
    rounds/end conditions, force/point/SWC/table/deployment configuration,
    deployment map or geometry, exclusion zones, token types/diameters,
    classified-objective setup, reinforcement suitability, tactical-support
    options, and scenario-specific rules/elements.
  - Scenario pages should expose the selected season prominently and link
    season-specific terms to the relevant rules/state references.
- [ ] Add mission-aware list capability guidance once saved-list support exists.
  - Derive a transparent checklist from the selected ITS scenario and the
    imported profile data: ITS Specialist Troops, relevant equipment/skills,
    Reinforcement or Team-Ops constraints, and scenario interactions. Explain
    missing capabilities without declaring a list illegal or strategically
    inadequate.
  - Keep temporary scenario-granted skills, designated Troopers, classified
    cards, tactical support, and private information out of static unit
    profiles. They belong to a per-game/session layer, which is not yet part of
    InfinityDB's replaceable imported snapshot.
- [ ] Provide an optional ITS organizer/event companion only after
  user-authored persistent storage and migrations are established.
  - Support season-aware event setup: published scenarios, allowed extras,
    player count/round guidance, pairings, byes, score entry, and a printable
    control-sheet checklist. Do not infer an official ranking submission or
    replace the Online Tournament Manager.
  - Include setup aids from ITS documents while keeping organizer choices and
    local participant data clearly separate from official records.
- [ ] Use curated rules coverage to complete the existing Skills, Equipment,
  Weapons, Ammunition, and Traits reference experience.
  - Add cited, concise summaries and cross-links between a rule, its variants,
    relevant states, ammunition, traits, and unit/loadout uses; make MOD scope
    explicit so profile annotations such as `(+1B)`, `(-3)`, `PH=`, rerolls,
    and Special Dice are not mistaken for universal unit statistics.
- [ ] Add a rules glossary and profile-notation help layer to unit details.
  - Explain the existing profile fields and symbols in context: training/order,
    troop type, classification, ISC, Hackable, Peripheral, equipment versus
    BS weapons, melee weapons, and profile/loadout separators. Use tooltips or a
    linked glossary rather than making every profile row denser.
  - Make terminology such as Trooper, Peripheral, Marker, Token, Deployable,
    Null State, Ally/Enemy/Hostile, and Victory Points discoverable wherever it
    changes how profile data should be read.
- [ ] Build a rule-aware Fireteams feature covering both unit eligibility and
  army Fireteam list/detail views.
  - The imported schema already retains `fireteams`, types, members, and
    descriptions, but the browser does not expose them. Present each army's
    current Army-data chart as authoritative, with membership restrictions,
    min/max requirements, FTO/wildcard notes, and source-data provenance.
  - Pair it with concise general Fireteam rules while clearly separating general
    rules from army-specific chart exceptions and retaining Infinity Army as the
    current chart authority.
- [ ] Add a Game States reference catalog and contextual state links.
  - Create cited state pages and link them from skills, equipment, weapon
    traits, and future Fireteam guidance.
  - Surface interactions that affect the existing UI's concepts, especially
    marker forms, Hidden Deployment, Suppressive Fire, Isolated, Unconscious,
    Possessed, and Peripherals; do not infer a unit's current in-game state
    from its static Army profile.
- [ ] Add a weapon-and-ammunition quick-reference view built from existing
  weapon profiles plus curated rules data.
  - Normalize display of multi-mode/multi-ammunition profiles, link ammunition
    names and traits to their effects, and provide a unit-neutral
    comparison/filter view. Validate it against Army metadata; do not copy
    source charts wholesale into the application.
- [ ] Add optional play-aid pages for core procedures, distinct from the unit
  database: order expenditure/ARO sequence, modifiers, movement/combat
  resolution, command tokens, and Fireteam quick reference. Use concise cited
  checklists rather than source excerpts.
- [ ] When a saved army-list builder is introduced, use the rules reference to
  add game-mode and list-review guidance—not hidden-information disclosure.
  Keep any share/export view privacy-aware and treat the Army app/data as
  authoritative for list legality.
- [ ] Add a curated Infinity Wiki URL mapping for traits when authoritative
  links are available.
- [ ] Create a unit-model image repository.
- [ ] Add a per-user model-collection tracker.
- [ ] Saved army lists, favourites, and personal notes stored separately from
  the replaceable imported snapshot.
- [ ] Unit comparison view for profiles, loadouts, weapons, skills, and
  equipment across selected units or armies.
- [ ] Rich unit filtering: troop type, classification, availability, points,
  SWC, weapons, equipment, skills, and characteristics.
- [ ] Deep-linkable, shareable search and filter state for catalog and unit
  views.
- [ ] Rules-reference cross-links from profiles, loadouts, skills, equipment,
  and traits to their catalog detail pages.
- [ ] Army-list builder/export integration once user-authored data storage and
  migrations are established.
- [ ] Data-review screens in Developer mode: normalization warnings, source
  record links through `infinity.raw.db`, and unresolved placeholder records.
- [ ] Low priority: provide access to prior imported-data versions when JSON
  source files change. Existing archived JSON ZIP files and Army snapshots are
  sufficient for recovery until this is needed.
- [ ] Low priority: add a JSON-snapshot comparison page showing added, removed,
  and updated data between two snapshots.
- [ ] Low priority: optionally highlight added, removed, and updated data
  elsewhere in the application when comparing snapshots.
