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
    - Planned `data/manifests/` contains generated build/acquisition provenance
      and state rather than hand-authored project knowledge.
    - Code continues to own algorithms, schemas, parser mechanics, generic
      normalization behavior, validation, and application behavior.
  - Require versioned schemas, validation on load, deterministic serialization
    where generated, focused regression tests, and portable project-relative
    paths for important configuration/manifests.
- [ ] Replace the legacy mercenary/NA2 ownership shortcut with source-semantic
  army-role and availability modeling.
  - Treat source canonical-faction ID `1` and Non-Aligned Armies ID `901` as
    distinct concepts. ID `1` is mercenary source/origin provenance; 901 is a
    grouping identity for distinct Non-Aligned army lists.
  - [x] Remove the legacy `1` -> `901` canonical-faction override after
    mercenary logical pairing and availability provenance became explicit.
    Canonical source ID `1` now remains source provenance with no application
    `main_army_id`; compatibility revision 12 requires regenerated databases.
  - [x] Replace current-build `xx01` main-army inference with the imported
    metadata faction-parent relationship. Explicit maintained overrides still
    take precedence, while the arithmetic resolver remains only as a
    standalone/legacy fallback for canonical factions without usable metadata.
    Compatibility revision 13 requires regenerated databases.
  - Validate the observed optional-mercenary source contract during
    normalization: `canonical == 1`, empty declared `factions`, and a
    `merc-...` source slug. Report source-schema drift instead of guessing when
    a future snapshot violates or extends that pattern.
  - Do not use the common 10,000-offset unit-ID pattern as the mercenary rule.
    It can support duplicate diagnostics/matching, but the classification must
    come from source semantics.
  - Preserve ordinary `factions` membership as normal availability and
    mercenary-variant army occurrences as optional mercenary availability, even
    when both occur for the same logical unit and army.
  - [x] Persist audited mercenary-to-standard source-unit matches during
    normalization and make repository logical grouping honor those matches when
    present. Explicitly unmatched variants remain separate; older databases
    without the metadata retain the legacy generic-grouping fallback.
  - [x] Persist audited generic standard-unit duplicate matches during
    normalization and make repository grouping treat that audit as authoritative
    when present, including an explicit empty result. Older databases without
    `genericUnitMatches` retain the 10,000-ID/ISC compatibility fallback.
  - Move unambiguous mercenary-variant deduplication into normalization or
    database creation. Merge alternate source records into one logical
    application unit while retaining every source unit ID, source occurrence,
    profile/loadout provenance, and availability reason required by validation
    and `infinity.raw.db`.
  - [x] Replace repository-time `canonical_faction_id == 1` mercenary inference
    with explicit `army_units.availability_kind` provenance for current
    normalized snapshots. Retain the old inference only as a compatibility
    fallback for rows where explicit provenance is absent.
  - Add source-shaped regression fixtures for normal plus optional mercenary
    records (for example the observed Miranda Ashcroft, Yuan Yuan, and Valerya
    patterns), including a case where normal and mercenary occurrences overlap
    the same army.
- [ ] Add `config/catalogs/weapon-categories.json`.
  - Move the ordered weapon-family taxonomy and regex patterns out of
    `weapon_categories.py`.
  - Move manual weapon-ID category decisions into the same configuration.
  - Preserve category-rule order and validate that override targets name a
    declared category.
  - Keep the classifier implementation in Python: override lookup, ordered
    rule evaluation, and fallback behavior remain code.
- [ ] Add `config/catalogs/weapon-overrides.json`.
  - Move known Army metadata corrections such as missing weapon profiles and
    source naming anomalies out of `weapon_profiles.py`.
  - Include an optional reason/source note so corrections remain reviewable
    when a new Army snapshot is imported.
  - Treat actual game-rule facts differently from source corrections: special
    weapon profiles, statistics, skills, and equipment should move into cited
    curated rules data when an authoritative source is available.
- [ ] Move rule-derived skill declaration categories out of
  `skill_categories.py` and into the curated rules layer.
  - Preserve N5 edition/version and printed-page citations.
  - Let application code query validated curated records rather than embed the
    rules facts in Python.
- [ ] Move trait rules-reference knowledge into curated data.
  - Migrate concise trait descriptions, canonical identities, aliases,
    misspellings, and citations from `traits.py`.
  - [x] Remove the duplicate trait-canonicalization table from
    `catalog-detail.js`; API responses expose canonical trait identity, name,
    and slug while preserving the raw source trait label.
- [ ] Review remaining hard-coded domain tables with the same decision rule:
  prefer derivation from authoritative imported data first, validated
  configuration second, and code only when the value is implementation behavior.
  - In particular, review fixed weapon-range display bands before creating any
    new config; derive them from weapon metadata if that can produce the
    intended UI.
  - Keep API-source table wiring such as `METADATA_TABLES`, schema definitions,
    generic merge/normalization algorithms, Unicode normalization mechanics,
    database behavior, and UI preference mechanics in code.

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
  - [ ] Add shared, versioned snapshot-provenance and annotation contracts using
    the existing data-path design rather than adjacent sidecars.
    - Store downloader-generated provenance under `data/manifests/snapshots/`.
      Each record binds to one immutable Army, wiki, or symbol archive by
      SHA-256 and may retain archive path/name, snapshot type, acquisition
      timestamp, source/language or base URL, document count, and other
      downloader-known source facts without duplicating Corvus Belli's source
      `metadata.json`.
    - Store human-authored descriptions, comparison targets, and ordered notable
      change notes separately under `data/curated/snapshot-notes/`, also bound to
      the immutable snapshot by SHA-256. Archive filenames are useful labels but
      not the authoritative identity.
    - Decide and implement the generated-manifest persistence policy together
      with the first manifest writer: Git ignore behavior, Docker/package
      exclusion, cleanup/retention, and whether any generated manifest class is
      intentionally version-controlled. Do not infer that policy from today's
      absence of `data/manifests/` ignore rules.
    - Have acquisition tools create/update generated snapshot manifests only;
      generated tooling must never rewrite or overwrite curated snapshot notes.
      Editing curated notes must never mutate the archive or generated
      provenance.
    - Future snapshot-comparison tooling may write structured generated diff
      data/reports under manifest/report paths, while curated notes remain the
      human interpretation of those results.
    - Add schema validation, deterministic generated serialization, archive-hash
      verification, annotation-reference tests, and coverage for all three
      snapshot types.
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

- [ ] Replace first-logo-per-unit symbol discovery with complete source-semantic
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
  - Rename/refactor `download_unit_symbols.py` to `download_army_symbols.py` so
    it covers unit/profile and faction assets plus manually declared static
    symbols, without generating final browser mappings. Preserve its timestamped
    `SYMBOLS ...zip` snapshot output when the discovery behavior is expanded.
  - Preserve the 2026-09-10 snapshot audit as a regression baseline, not a
    permanent source count: 59 JSON documents (`metadata.json` + 58 Army
    documents), 5,020 profile-logo references / 1,033 unique unit SVG URLs,
    58 faction-logo references / 57 unique faction SVG URLs, 1,090 unique SVG
    URLs in total, 4,137 `resume` references / 862 unique resume URLs, and zero
    unknown SVG locations. The old first-logo-per-unit behavior found only 861
    unique unit SVGs, missing 172 distinct SVGs; 136 unit IDs referenced more
    than one profile logo.

- [ ] Define `data/manifests/army-symbol-build.json` as the authoritative
  machine-readable state passed through symbol processing.
  - Separate `snapshot`, `assets`, and `references`; do not use a filename-keyed
    structure that conflates source assets with their consumers.
  - Snapshot records should include the pinned Army archive identity/hash and,
    when applicable, the corresponding `SYMBOLS ...zip` archive identity/hash,
    plus language, acquisition timestamp, API base/version if available, and
    source-document count.
  - Asset records should retain kind, source URL/filename/hash, source-resolution
    method, font classification, alias normalization, duplicate group,
    canonical source identity, conversion backend/status, compression
    profile/status, and final published path.
  - Reference records should retain source document, JSON path, reference kind,
    unit/faction/army IDs and slugs as applicable, and source asset URL.
  - Persistent manifest paths must be portable project-relative POSIX-style
    strings; convert them to native `Path` objects only at filesystem access.

- [ ] Complete the static-symbol and local-override model as maintained project
  knowledge rather than downloader code.
  - [x] `config/symbols/static-symbols.json` already declares the known
    non-API assets: characteristics `cube`, `cube2`, `hackable`, `peripheral`
    and orders `regular`, `irregular`, `tactical`, `lieutenant`, `impetuous`,
    all under the stable Corvus Belli icon base URL.
  - [ ] Extend static declarations with semantic metadata such as stable key,
    source filename, user-facing label, and known source names where needed.
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
    transient extracted/processed files, planned `data/manifests/`,
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
- [ ] Test a full build and container startup in CI, including the requirement
  that deployment images contain only `infinity.db`, not the development raw
  archive.
- [ ] Keep README and architecture-version references synchronized with schema
  and compatibility revisions during every database-format change.

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
