# InfinityDB backlog

This is the working backlog for performance work, data-pipeline improvements,
and possible product additions. Items are intentionally grouped by outcome
rather than by implementation layer.

Everything not represented by a checked checkbox is **planned/unimplemented work**,
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

## Version 1.0.0 release requirements

Version 1.0.0 represents the point where InfinityDB is **data-complete for normal Infinity gameplay**.

The defining requirement is that every data point available from the supported Infinity sources that can reasonably be useful to a player is represented by InfinityDB and can be presented in some usable way through the web application.

This does **not** mean that every planned feature, visualization, workflow, or UI refinement must be complete before 1.0.0. A data type may satisfy the 1.0.0 requirement through a basic but functional presentation, provided that the information is accessible, understandable, and correctly connected to the rest of the database.

**ITS-specific content is deliberately outside the scope of version 1.0.0.**

### 1. Player-relevant data completeness

- [ ] Inventory all player-relevant data available from the supported source material and identify any information not currently represented in InfinityDB.
- [ ] Every identified in-scope data point has a maintained representation in the database or another explicitly defined structured data layer.
- [ ] Every represented in-scope data point can be accessed through the web application in some usable form.
- [ ] No player-relevant source information is omitted merely because the final specialized UI for it has not yet been implemented.
- [ ] Data relationships needed to understand or navigate the information are represented explicitly rather than requiring knowledge of source-specific IDs or conventions.

In-scope information includes, where applicable:

- [ ] armies, sectorials, grouping identities, and their relationships
- [ ] units and canonical unit identities
- [ ] troop profiles and profile variants
- [ ] availability and army-specific unit relationships
- [ ] attributes and statistics
- [ ] weapons and ammunition
- [ ] skills
- [ ] equipment
- [ ] hacking programs and related hacking data
- [ ] deployables, peripherals, companions, and other associated game entities
- [ ] Fireteam-related data
- [ ] special army/unit relationships and exceptions represented by curated data
- [ ] other structured gameplay information exposed by Infinity Army
- [ ] rules information needed to understand the above data
- [ ] other player-relevant information discovered during the completeness audit

### 2. Rules knowledge

- [ ] Import or curate the relevant rules content from the supported official PDFs and Infinity Wiki.
- [ ] Every rule, skill, equipment item, weapon trait, state, terminology entry, or other gameplay concept referenced by database content has useful explanatory information available in InfinityDB.
- [ ] Provide concise player-oriented descriptions or summaries where reproducing source text directly is inappropriate or unnecessary.
- [ ] Preserve source/provenance information so users can identify the official material from which a rule summary or interpretation was derived.
- [ ] Rules relationships are represented sufficiently to allow relevant rules information to be surfaced alongside units, profiles, weapons, equipment, skills, and other database entities.
- [ ] Resolve duplicate, renamed, superseded, or differently structured rule concepts from the PDFs and Wiki into a coherent maintained representation.
- [ ] Clearly distinguish InfinityDB summaries or normalized descriptions from verbatim official rules text where applicable.

### 3. Web presentation completeness

For 1.0.0, **availability of the information is mandatory; a specialized or final-form interface is not**.

- [ ] Every in-scope data category has at least one functional presentation in the web application.
- [ ] Users can navigate from the major player-facing entities to their relevant related data.
- [ ] Important data is not accessible only through raw JSON, development tools, database inspection, or undocumented URLs.
- [ ] Generic tables, sections, or detail views are acceptable for 1.0.0 where a richer dedicated interface is planned later.
- [ ] Information needed to interpret another displayed value is either shown directly or reachable through clear navigation.
- [ ] Empty, unavailable, or not-applicable values are represented deliberately rather than silently omitted in ways that could mislead the user.

### 4. Data correctness and provenance

- [ ] Complete a consistency audit across source snapshots, normalized databases, APIs, and browser presentation.
- [ ] Known source quirks and domain-specific corrections are represented explicitly in maintained curated data or documented derivation rules.
- [ ] Derived facts used by the application are reproducible from their documented inputs.
- [ ] Player-facing data can be traced to the source snapshot, curated rule, or derivation responsible for it.
- [ ] Known material discrepancies between Infinity Army, official PDFs, and the Infinity Wiki are documented and handled deliberately.
- [ ] No known defect remains that materially misrepresents a player's unit, profile, weapon, skill, equipment, army relationship, or rule information.

### 5. Explicitly out of scope for 1.0.0

The following do not block version 1.0.0 unless they become necessary to satisfy one of the requirements above:

- ITS-specific rules, missions, season material, classifications, or tournament content
- final-form or specialized UI for every data type
- every planned search, filter, comparison, or visualization feature
- exhaustive performance optimization
- architectural refactors that do not affect correctness or data completeness
- optional cosmetic improvements and additional themes
- speculative future data-model simplification
- features whose sole purpose is administration, development convenience, or deployment ergonomics

These may remain in the general backlog for post-1.0 development.

### 6. Final 1.0.0 completeness audit

Before releasing 1.0.0:

- [ ] Perform a source-by-source inventory of Infinity Army, the supported official rules PDFs, and the Infinity Wiki.
- [ ] For every discovered player-relevant information type, record where and how InfinityDB represents it.
- [ ] Verify that every in-scope type has a usable web presentation.
- [ ] Verify that referenced rules and game concepts have accessible descriptions or summaries.
- [ ] Review all deliberately omitted source data and confirm that each omission is either non-player-relevant or explicitly outside the 1.0.0 scope.
- [ ] Confirm that remaining TODO items do not represent missing player-relevant data required by this definition of database completeness.

## Milestone sequence

**Milestone 1 — data/wiki/symbol ingestion — completed 2026-09-19.** Army,
wiki-derived curated/rules data, and symbols now have pinned-source acquisition,
explicit provenance, reproducible transformation/publication, live
stage-by-stage acceptance, rollback/reproducibility validation, and guarded
local deployment packaging. Remaining pipeline items below are follow-up
refactoring, coverage, and optimization work rather than Milestone 1 blockers.

- [ ] **Milestone 2 — establish the canonical application model and advance
  1.0 completeness.**
  Begin with conservative semantic deduplication of data InfinityDB already
  possesses. Use that work to distinguish canonical player-relevant facts,
  contextual variation, relationships, provenance, redundant source
  representation, and normalization-only structure. Then use the resulting
  source-to-presentation inventory as groundwork for the broader web-app
  consistency audit. The detailed checklist is maintained below.

General performance and storage experiments remain deferred unless they become
necessary to establish semantic correctness, losslessness, or acceptable
application behavior during this work.

## Deferred performance and storage experiments

These are intentionally deferred until after the canonical-data and web-app
consistency work unless one becomes necessary to unblock that work.

- [ ] Benchmark cold and warm requests per worker for unit lists, unit details,
  skills, equipment, and weapons. Record median and p95 timings against a
  representative snapshot before and after each performance change.
- [ ] Evaluate SQLite `immutable=1` for deployed snapshots. Enable it only when
  the process never observes an in-place database replacement.
- [ ] Compare otherwise equivalent deployment variants backed by SQLite and by
  `normalized.json`, with both variants exposing the same API and representative
  load scenario. Define the JSON variant's startup parsing, indexing, and caching
  semantics before interpreting performance results so the comparison measures
  runtime data models rather than repeated JSON parsing. Evaluate both request
  performance and deployment portability/multi-platform suitability before
  deciding whether a storage/query abstraction is justified.

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

## Milestone 2: canonical data model and application completeness

Milestone 2 begins the version-1.0 completeness effort by clarifying the
application-level meaning of the data InfinityDB already possesses.

The first workstream is semantic deduplication and canonicalization. This is
deliberately performed before the broader web-app consistency audit because it
helps distinguish distinct player-relevant facts from repeated source
representation, normalization artifacts, provenance, and contextual variation.

The detailed design and invariants are maintained in `docs/data-model.md`.

- [x] **Establish the semantic-deduplication baseline.**
  - [x] Add a reproducible development audit that reports repeated profile and
    loadout payloads without modifying the database.
  - [x] Define the exact payload components included in equality comparisons.
  - [x] Separate semantic fields from source identity, context, ordering, and
    provenance fields explicitly rather than by undocumented exclusion.
  - [x] Record representative equality and difference cases as regression
    fixtures/tests.
  - [x] Treat current snapshot counts as diagnostics, not expected constants.

- [x] **Canonicalize profile payloads conservatively.**
  - [x] Inventory every current profile field and nested relationship.
  - [x] Classify each as canonical fact, contextual fact/delta, relationship,
    source/provenance, or normalization-only structure.
  - [x] Prove exact-equality groups before changing storage.
  - [x] Design canonical profile payload + source/context occurrence relations.
  - [x] Preserve genuine AVA, profile-group, army, and source differences
    explicitly.
  - [x] Preserve characteristics, skills, equipment, weapons, extras, includes,
    peripherals, and other gameplay-bearing nested information.
  - [x] Update repository/API assembly to consume the canonical model without
    changing player-visible semantics unintentionally.
  - [x] Add reconstruction/provenance and behavioral regression tests.
  - [x] Re-evaluate and simplify the remaining query-time logical-source profile
    merge/deduplication only where occurrence and availability semantics remain
    unchanged.

- [ ] **Canonicalize loadout payloads conservatively.**
  - [x] Inventory every loadout field and nested relationship.
  - [x] Classify canonical facts versus contextual/source differences.
  - [x] Compare complete loadout meaning, including points, SWC, minis,
    disabled state, skills, equipment, weapons, extras, orders,
    characteristics, includes, and peripherals.
  - [x] Design canonical loadout payload + source/context occurrence relations.
  - [ ] Preserve every genuine army/loadout variation explicitly.
  - [ ] Update repository/API assembly and regression coverage.
  - [ ] Measure database size and query behavior as secondary outcomes, without
    using storage savings as the semantic acceptance criterion.

- [ ] **Extend canonicalization to logical-unit payloads.**
  - [ ] Audit fields across every existing `logical_unit` for invariance.
  - [ ] Promote only facts proven invariant or governed by an explicit reviewed
    semantic rule.
  - [ ] Keep army membership, availability, source variants, and genuine
    profile/loadout differences as explicit context.
  - [ ] Preserve source IDs and full traceability from canonical facts back to
    supporting source occurrences.

- [ ] **Audit relationships after entity canonicalization.**
  - [ ] Revisit includes and peripherals and distinguish visible endpoint data
    from the independently meaningful relationship between those endpoints.
  - [ ] Audit relation/dependency structures.
  - [ ] Audit Fireteam structures.
  - [ ] Identify normalization-only link structures that do not constitute
    additional player-facing information.
  - [ ] Record any distinct player-relevant relationship not currently
    presentable by the application as a 1.0 completeness gap.

- [ ] **Audit catalog and metadata overlap.**
  - [ ] Compare Army catalogs, occurrence data, and `metadata_*` collections by
    semantic concept rather than table identity.
  - [ ] Preserve genuinely distinct weapon modes, profile variants, source
    metadata, and gameplay contexts.
  - [ ] Identify player-relevant metadata currently stored but not represented
    through the application.

- [ ] **Maintain a source-to-presentation completeness inventory while
  canonicalizing.**
  - [ ] Trace relevant original Army JSON constructs through normalization,
    canonical application meaning, repository/API representation, and web
    presentation.
  - [ ] Classify each construct as explicitly presented, implicitly represented,
    operationally consumed, redundant source representation,
    normalization-only structure, or unrepresented player information.
  - [ ] Add confirmed unrepresented player information to the 1.0 completeness
    backlog.
  - [ ] Do not treat unused tables/columns alone as proof of a completeness gap.

Completion of every possible deduplication opportunity is **not** itself a
version-1.0 requirement. Canonicalization blocks 1.0 only where unresolved
duplication prevents InfinityDB from establishing data correctness,
distinguishing genuinely different player-relevant facts, or satisfying the
documented completeness requirements.

## Army snapshot and symbol pipeline

Milestone 1 acceptance for the integrated pipeline is complete. The remaining
items in this section are post-milestone maintenance, refactoring, coverage, or
incremental-performance work; they do not block Milestone 2 unless they expose a
new correctness or reproducibility defect.

- [ ] Let future snapshot-comparison tooling write structured generated diff
  data/reports under manifest/report paths while curated snapshot notes remain
  the human interpretation of those results.

- [ ] Refactor stage scripts into thin CLIs over reusable Python functions and a
  small shared symbol-pipeline utility layer.
  - [x] `snapshot_archive.py` centralizes the timestamped ZIP naming, collision
    handling, and deterministic archive member ordering shared by the Army,
    wiki, and symbol downloaders.
  - [x] `download_army_json.py`: expose snapshot identity/result to callers while
    keeping its standalone CLI and explicit network behavior.
  - [x] `download_army_symbols.py`: own complete discovery, static declarations,
    override/cache/network source resolution, recursive SVG audit, and manifest
    reference/asset updates while retaining complete timestamped archive output.
    - [x] Expose current source-semantic discovery and raw network acquisition as
      reusable functions so the standalone CLI and orchestrator share one
      implementation.
    - [x] Resolve raw assets through Git-ignored local overrides, the prior
      validated immutable symbol snapshot/cache, then network, and record the
      chosen source method for every resolved asset.
  - [ ] Make the symbol-downloader input contract match its CLI and tests. Prefer
    the immutable raw Army ZIP as the authoritative input; either fully support
    directory/current merged-master inputs end to end or stop advertising them.
    In particular, do not claim legacy/current `master.json` compatibility unless
    discovery can consume that schema without treating ordinary embedded SVG
    references as unknown fields.
  - [ ] `svg_processor.py`: keep font audit, alias normalization, complete-set
    duplicate detection, deterministic representative ranking, persistent
    Inkscape conversion, and reports. Duplicate/canonical and text-conversion
    state are integrated into the build manifest; multi-category processing
    beyond the current canonical flow remains.
  - [x] `svg_compress.py`: keep the standalone CLI and production validation
    behavior; expose an importable result/update path for orchestration.
  - [x] `reorganize_symbols.py`: become the publisher and final mapping generator.
  - [ ] `path_sanitization.py`: remain shared infrastructure for external/mirror
    naming; pipeline-generated asset names should use one host-independent
    policy.
  - [ ] Longer-term reusable modules may be split into `snapshot`, `discovery`,
    `manifest`, `downloader`, `audit`, `deduplicate`, `convert`, `compress`, and
    `publish` helpers when that reduces duplication rather than adding ceremony.

- [ ] Make every integrated symbol stage idempotent and traceable before adding
  sophisticated incremental caching.
  - [x] Timestamped Army, wiki, and symbol acquisition never overwrites an
    existing archive; same-second collisions receive a deterministic numeric
    suffix.
  - [ ] Changes to an override SHA-256 invalidate downstream processing for that
    asset. Removing an override falls back to validated symbol archives/cache or
    network by the normal resolution rules.
  - [x] Reuse validated archived downloads and rebuild work deterministically.
  - [ ] After the integrated build is stable, consider cache keys based on snapshot
    SHA-256, source SVG SHA-256, processor/tool versions, font-alias config,
    duplicate renderer/settings, conversion backend/settings, and compression
    profile/settings.

- [ ] Standardize symbol-pipeline reports around detailed machine/human outputs
  plus one concise build summary.
  - [ ] Preserve/report discovery counts, unknown SVG references, font audit,
    missing fonts, unused font declarations, SVG parse errors, duplicate groups,
    duplicate-render errors/separation/summary, text-to-path results/summary,
    compression report/candidates/run metadata, overrides used/unused, raw-cache
    hits, network downloads, manual static assets, canonical counts, published
    asset counts, application-mapping counts, and per-stage/total runtime.
  - [ ] Existing report filenames from the plan may be retained where useful:
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
  - [ ] Snapshot/discovery tests: metadata/faction validation, complete archive,
    snapshot identity/hash, all profile/faction logos, multiple logos for one
    unit, one logo shared by units, duplicate URLs, static declarations,
    override suppression of network, override over cache, invalid/unused
    overrides, filename collisions, unexpected SVG fields, and proof that
    `resume` is not required for complete discovery.
  - [ ] SVG fixtures: exact duplicate, XML-different visual duplicate, no-text,
    normal text, alias-font, missing-font, empty-text cleanup, and troublesome
    real-world conversion cases.
  - [x] Publisher tests: several references to one canonical asset, deterministic
    unit/profile/army paths, category-specific static assets, strict v7-to-v8
    publication, compressed-input hash verification, reconciliation/backups, and
    failed publication preserving the prior static tree.
  - [ ] Run core portability coverage on Windows, Ubuntu/Linux, and macOS when CI
    permits: project-relative path generation, path sanitization, executable
    discovery including `.exe`/`.cmd`, subprocess argument construction without
    shell quoting, temp files, case-only collisions, snapshot ZIP handling,
    override lookup, static-symbol manifest loading, atomic replacement, and
    Windows `spawn` compatibility. External-tool integration tests may be
    conditional when Inkscape, `resvg`, or SVGO are unavailable.
  - [ ] Add a shared utility layer for executable discovery, native/project-relative
    path conversion, atomic writes, subprocess invocation, and platform-neutral
    generated filenames before orchestration otherwise duplicates those rules.

## Continuous integration and validation

- [ ] Finish non-blocking CI hardening documented in `docs/ci.md`. The core
  validation layers are implemented; these remaining follow-up items are
  post-Milestone-1 hardening and do not block the Milestone 2 consistency audit.
  - [x] Repair the deployment-smoke runtime import boundary. Read-only runtime
    database/web imports no longer pull the database exporter, Army normalizer,
    or weapon-policy configuration from source-checkout-relative paths.
  - [x] Package configuration intentionally required by supported installed CLI
    build/ingestion operations through the shared
    `<sys.prefix>/share/infinity-db/config/` resource contract and verify it from
    outside the checkout.
  - [x] Add explicit `--assets off|auto|required` handling to `run_checks.py`.
    Required CI defaults to `off`; `auto` uses full-asset tests only when a
    validated complete set exists and fails on detected partial/corrupt state;
    `required` fails unless the complete set validates.
  - [x] Split asset-dependent pytest coverage into an explicit full-asset marker
    while making normal tests hermetic through project-owned fixtures or injected
    temporary static roots. Test absent/present asset behavior deliberately so a
    clean source archive passes without third-party graphical assets.
  - [x] Make local production deployment fail closed unless a complete published
    symbol set is bound to terminal v8 build-manifest state, then revalidate the
    installed Docker package and representative symbol routes before activation.
  - [x] Make version tests independent of incidental Git-checkout state. Test the
    `+dev` display suffix with controlled repository/version inputs rather than
    requiring source archives or detached release trees to contain Git metadata
    and be ahead/dirty.
  - [x] Make the normal Ruff stage cover the complete maintained `tools/` tree
    rather than a hand-maintained script allow-list.
  - [x] Add Pyright as a normal `run_checks.py` type stage over maintained
    `src/` and `tools/` code so editor-visible type regressions fail required CI.
  - [x] Install the real `symbols` Python dependency set in required source CI and
    exercise fontTools, tinycss2/cssselect2, and Pillow with synthetic fixtures.
  - [x] Add focused regression tests for standalone tools, allowing conditional
    external-tool integration where appropriate.
  - [ ] Integrate curated snapshot-note validation into routine project checks so
    every checked-in file under `data/curated/snapshot-notes/` is validated even
    when no downloader or comparison workflow happens to load it.
  - [x] Add clean-checkout Linux source CI that drives the normal check runner in
    hermetic asset mode, using the tracked synthetic Army fixture for the Army
    database build and the tracked curated collections for `rules.db`.
  - [ ] Configure GitHub repository rules/branch protection to require the
    `Source checks` result for protected merges when branch protection is enabled;
    workflow YAML alone does not enforce merge blocking.
  - [ ] Establish and retain release evidence for the configured GitHub Actions
    workflows. Before claiming a release has passed hosted CI, record successful
    `Source checks`, `Installed wheel smoke`, and `Deployment smoke test` runs
    for the release commit or tag. Local results and workflow definitions are not
    substitutes for those hosted executions.
  - [x] Add an installed-wheel smoke job that builds/installs the wheel in a clean
    environment and validates supported imports, startup, CLI/resource packaging,
    and generated test databases without repository-relative assumptions.
  - [x] Expand hermetic CI across Windows, Ubuntu/Linux, and macOS at Python 3.11;
    add a Linux Python 3.14 compatibility leg without multiplying the entire
    operating-system matrix.
  - [ ] Complete optional/manual full-asset CI for a validated complete symbol set.
    - [x] Add a dispatch-only `Full-asset checks` workflow restricted to `main`
      that stages a checksum-pinned private published-asset bundle through the
      `full-assets` environment, runs `--assets required`, and never uploads the
      third-party graphical tree as a workflow artifact.
    - [x] Add safe private-bundle staging with HTTPS-only download, digest/size
      checks, traversal/symlink/case-collision guards, and published-contract
      validation before replacing ignored local assets.
    - [ ] Configure the repository `full-assets` environment with an authorized
      `FULL_ASSET_BUNDLE_URL` and `FULL_ASSET_BUNDLE_SHA256`, then record one
      successful manual run.
  - [ ] Keep live Army/wiki/symbol acquisition and expensive performance/capacity
    checks explicit, manual, or scheduled rather than dependencies of required
    source CI.

## Distribution, documentation, and test reproducibility

- [ ] Reduce duplicated normative documentation after correcting the audit
  drift. Keep imported-data/identity contracts authoritative in
  `docs/data-model.md`, filesystem/provenance layout in `data/README.md`,
  architecture rationale in `docs/architecture.md`, and concise invariants in
  `docs/AI_CONTEXT.md`; replace repeated contract text with links where practical.
  As part of this pass, remove stale statements that call the already-implemented
  `army-symbol-build.json` or snapshot-manifest work merely planned/future work.

## Broader web-app consistency audit

- [ ] Perform a systematic end-to-end consistency audit after the canonical-model
  groundwork above is sufficiently established. This remains an audit and bounded
  correctness-fix effort rather than a visual redesign or broad frontend
  restructuring project.
  - [ ] Establish one pinned production audit baseline before inspecting behavior:
    the Git commit, Army snapshot/provenance, generated `infinity.db` and
    `rules.db`, terminal symbol manifest/inventory, and locally published symbol
    set. Verify that the runtime database and symbol publication derive from the
    same Army snapshot. Record the evidence and audit results in a durable audit
    document (for example, `docs/audits/web-consistency-YYYY-MM.md`); do not mix
    production observations with synthetic test fixtures.
  - [ ] Create and maintain an explicit audit matrix for each concept, recording
    its source meaning, storage representation, canonical/application
    interpretation, API representation, browser consumers, existing coverage,
    and audit result. Cover logical/source unit identity; army hierarchy, role,
    and playability; faction/display identity; optional availability;
    names/slugs; profiles and loadouts; catalog/rules enrichment; distance/range
    semantics; symbols; source/wiki/rules provenance;
    filtering/search/sorting/counts; and deep-link identifiers.
  - [ ] Begin with the army/unit identity and availability vertical slice. Trace
    `main_army_id` and `display_army_id`, faction grouping, role/playability,
    mercenary and reinforcement availability, logical identity, and their unit
    explorer/detail consumers from storage through the API to the browser.
  - [ ] Audit the backend and API contracts before browser presentation. Trace
    generated database rows through the canonical/application model, repository
    queries, and application-level composition (including `SkillCatalog`,
    `TraitCatalog`, and `CatalogRules`) to the JSON API. Add focused contract
    coverage wherever intentional behavior is not sufficiently pinned.
  - [ ] Audit browser semantic ownership. Inventory domain interpretation in
    browser modules, beginning with `unit.js`, the army selector, catalog detail
    modules, symbol lookup, rules links, and optional-unit filtering. Keep display
    formatting in JavaScript, but expose game/data semantics through the backend
    API when duplicate interpretation could disagree. Route JSON API access
    through `api.js` to match the documented boundary; static/HTML fetches are not
    part of that API-transport requirement.
  - [ ] Perform route-by-route parity checks for the Unit explorer and details;
    Skill Modifiers; Skills, Equipment, Weapons, and Traits list/detail pages;
    shared navigation/settings; and version refresh. Compare API output with
    rendered behavior, including filtering, result counts, ordering, labels,
    deep-link state, cross-links, optional-unit behavior, source/rules links,
    catalog-item unit usage, and symbol identity. Use a deliberate manual browser
    pass unless lightweight browser automation is added for a concrete audit need.
  - [ ] Treat Fireteams as preserved source data whose 1.0 presentation remains a
    separate implementation task. Verify their imported data is retained, record
    the current absence of a Fireteam repository/API/browser surface, and feed
    confirmed player-relevant Fireteam information into the 1.0 completeness
    backlog.
  - [ ] Exercise degraded states deliberately: rules database available versus
    unavailable; clean redistributable source checkout without graphical assets;
    complete local published assets; unknown unit/catalog/trait IDs; empty search
    or filter results; invalid query parameters; missing catalog enrichment;
    stale version/snapshot detection; and database/symbol snapshot mismatch.
  - [ ] Verify the three supported runtime contexts independently: a clean source
    checkout without redistributed Corvus Belli graphics, local development with
    explicitly supplied generated artifacts, and production deployment that fails
    closed for incomplete or mismatched databases/assets. Passing one context does
    not establish the others.
  - [ ] Fix discovered inconsistencies incrementally and add focused regression
    coverage where practical. Record intentional deferrals in the audit document
    and TODO rather than silently leaving them unresolved. Keep CI hardening,
    unrelated storage experiments, the Changes page, visual theming, and broader
    UI restructuring outside this audit unless required for a minimal correctness
    or 1.0-completeness fix.
  - [ ] Close with a second source-to-storage-to-browser matrix pass, complete
    normal project checks, and full-asset validation against the pinned production
    publication when it is available. Update canonical documentation, `TODO.md`,
    and `CHANGELOG.md` for material findings before starting the later
    visual-design, frontend-architecture, or theming work.

## Visual design, frontend architecture, and theming

- [ ] Define and document InfinityDB's visual-design and UI/UX guiding
  principles before larger presentation changes.
  - [ ] Optimize first for fast lookup, comparison, and scanning of dense game data;
    prefer clarity, hierarchy, and legibility over decorative complexity while
    avoiding an unnecessarily cramped interface.
  - [ ] Keep navigation, page hierarchy, terminology, controls, tables, cards,
    badges, and feedback states predictable across catalog and detail views.
    Extend shared design-system primitives instead of giving individual pages
    their own visual language.
  - [ ] Use progressive disclosure for secondary, provenance, and developer-only
    information so technical depth remains available without overwhelming the
    default reading flow.
  - [ ] Treat responsive behavior as a content-priority decision rather than simple
    shrinking. Define deliberate phone, tablet/compact, and desktop behavior for
    navigation, filters, tables/statlines, detail groups, and multi-column data.
  - [ ] Treat accessibility as part of the design contract: semantic HTML, complete
    keyboard operation, visible focus, sufficient contrast, non-color-only
    meaning, useful touch targets, reduced-motion support where motion exists,
    and sensible screen-reader labels/status announcements.
  - [ ] Keep theme and faction/army accent colors subordinate to semantic meaning.
    Source/domain state must remain understandable regardless of selected theme,
    color perception, or whether a particular graphical asset is available.
  - [ ] Preserve the current lightweight/browser-native direction unless a concrete
    requirement justifies changing it. New visual work should not implicitly
    introduce a frontend framework or build pipeline.
  - [ ] Once agreed, record durable principles in the canonical architecture/design
    documentation and keep this TODO focused on remaining implementation work.

- [ ] Define a clearer backend/frontend responsibility boundary and reflect it
  in source organization without changing the current same-origin deployment
  model merely for architectural fashion.
  - [ ] Backend Python owns imported-data/domain semantics, identity and rules
    interpretation, database access/querying, request validation, stable API
    contracts, application/version metadata, and HTTP concerns. Domain meaning
    that would otherwise require browser code to infer IDs, names, source quirks,
    or rules semantics belongs in backend/API fields.
  - [ ] Frontend code owns information presentation, interaction state, responsive
    behavior, accessibility behavior, client-side display formatting, theme/UI
    preferences, and composition of semantic API data into views. It must not
    duplicate maintained domain interpretation already represented by the
    backend contract.
  - [ ] Keep API payloads semantic rather than presentational: expose roles, states,
    identities, labels, and relationships rather than CSS class names, literal
    colors, layout instructions, or page-specific markup.
  - [ ] Split the current Python web layer so API handling, shared page-shell/static
    delivery, and top-level request dispatch are visibly separate concerns.
    Keep existing URLs and the shared shell contract stable while doing so.
  - [ ] Organize the browser side around explicit shared layers (API transport,
    preferences/theme state, reusable view/components, and page modules) so page
    scripts stop accumulating cross-cutting behavior. Continue routing browser
    HTTP access through `api.js` rather than ad hoc `fetch()` calls.
  - [ ] Preserve native ES modules and the no-frontend-build-tool decision for now;
    source-tree separation should improve ownership and maintainability without
    requiring bundling/transpilation.
  - [ ] Add focused contract/regression coverage as responsibilities move so a
    frontend refactor cannot silently recreate backend domain logic, and backend
    changes cannot silently break established browser contracts.

- [ ] Introduce first-class customizable theme support, with Light and Dark as
  the initial themes and an extension contract that does not require component
  rewrites when more themes are added later.
  - [ ] Refactor the CSS token model into semantic theme tokens versus theme-neutral
    layout/component rules. Components should consume tokens such as surfaces,
    text, borders, actions, focus, status, shadows, and data emphasis rather than
    hard-coded light-theme colors.
  - [ ] Keep faction/army colors as domain accent tokens layered onto the selected
    theme. Define contrast-safe treatments for both Light and Dark rather than
    assuming the current accent/background pairings work unchanged in both.
  - [ ] Define a stable theme identifier/preference contract (`light` and `dark`
    initially), and decide/document default startup behavior such as following
    the operating-system preference versus a fixed project default. An explicit
    user selection must take precedence over the default.
  - [ ] Integrate the theme selector with the existing Settings/preferences model.
    Theme changes apply immediately; persistence follows the existing
    remember-settings consent policy rather than creating an unrelated storage
    mechanism.
  - [ ] Resolve and apply the selected theme before first meaningful paint to avoid
    a light-to-dark or dark-to-light flash during navigation/reload.
  - [ ] Replace hard-coded light-only browser metadata/assumptions with theme-aware
    `color-scheme` behavior so form controls, scrollbars, and other user-agent UI
    remain coherent with the selected theme.
  - [ ] Keep the InfinityDB logo and other project-owned themed graphics driven by
    the same semantic token contract where practical; do not fork separate
    light/dark asset files when CSS-variable theming is sufficient.
  - [ ] Audit status colors, range-modifier colors, links, focus indicators, muted
    text, tables, selected rows, dialogs, menus, and faction accents for contrast
    and distinguishability in every supported theme.
  - [ ] Add regression coverage for preference initialization/switching/persistence
    and representative core pages in both themes. Consider targeted visual
    regression screenshots at compact and desktop widths once the theme tokens
    stabilize.

- [ ] Refactor the frontend design-system structure after the principles and
  theme contract are agreed.
  - [ ] Review the current monolithic `styles.css` and separate foundational tokens,
    theme values, shared components/layout, and page-specific exceptions where
    doing so improves ownership without requiring a CSS build step.
  - [ ] Inventory repeated or one-off component styles and either promote recurring
    patterns to shared primitives or remove unnecessary variants. Avoid adding
    new page-local copies during the transition.
  - [ ] Define which responsive/layout behaviors are shared primitives versus
    intentional page-specific composition, and document the small set of
    supported density variants rather than allowing arbitrary per-page spacing.
  - [ ] Keep existing shared shell, navigation, detail-group, table-density, badge,
    and settings patterns working during the migration; visual cleanup should be
    incremental rather than a simultaneous rewrite of every page.

## Reliability and operations

- [ ] Establish production load monitoring and a repeatable capacity test for
  the Docker deployment.
  - [ ] Record host and container CPU, memory, swap, disk-space/inode, disk-I/O,
    and network utilization; retain Docker restart/OOM events and Caddy and
    Gunicorn error logs. Alert on sustained CPU saturation, memory pressure or
    OOM kills, low disk space, elevated 5xx responses, and failed health checks.
  - [ ] Publish Caddy access-log metrics (request rate, status code, latency, and
    active connections) and application metrics for dynamic API latency. Keep
    dashboards split between static assets and `/api/` requests.
  - [ ] Define a representative load-test scenario: browse the unit list, search,
    open unit/catalog details, and fetch API endpoints using a current
    production-like SQLite snapshot. Include a warm-cache steady-state run and
    a short burst run; do not benchmark only the health endpoint.
  - [ ] Establish a baseline at 2 Gunicorn workers x 4 threads, then test 4 x 4
    only with a matching 4-vCPU/4-GiB container allocation. Record p50/p95/p99
    latency, request/error rate, CPU, memory, and SQLite/disk behavior at each
    concurrency level.
  - [ ] Set an explicit scale trigger (for example, a sustained p95 latency or
    error-rate SLO breach while CPU is not otherwise constrained). Prefer
    multiple immutable app replicas behind Caddy over unbounded worker growth;
    re-run the test before changing worker counts or deployment resources.
- [ ] Add a benchmark/health-check command that validates the frontend database,
  confirms its expected raw archive when requested, and reports schema and
  compatibility revisions.
  
## Potential product features

- [ ] Expand the existing versioned curated rules-reference infrastructure with
  substantially broader N5 v5.3 coverage from
  `data/pdf/rules/n5-rules-v5-3-en.pdf` (dated 2026-08-10).
  - [x] Keep curated rules in their own source-controlled JSON layer and
    independent `rules.db`; do not add PDF-derived facts to `infinity.db` or
    `infinity.raw.db`.
  - [ ] Expand canonical rule identities across skills, equipment, ammunition,
    traits, states, Fireteam concepts, glossary terms, and other useful rule
    domains, retaining rulebook version and printed-page citation.
  - [ ] Store original, concise editorial summaries and structured facts (labels,
    requirements, effects, restrictions, related rules, and page locators),
    rather than bulk-extracting or serving copyrighted PDF text or artwork.
    Confirm permissions and attribution/linking requirements before publishing
    any rule-derived prose.
  - [ ] Add a coverage report that flags Army metadata items with no matching
    reference entry, ambiguous names/levels/MOD variants, and entries whose
    cited rulebook version is stale. A prior-version comparison is needed before
    claiming a specific change between rulebook revisions.
- [ ] Add a dated FAQ/errata layer to the existing rules-reference system from
  current material under `data/pdf/faq/`.
  - [ ] Model each ruling as a question, concise answer, rule/topic links,
    applicable scope, document version/date, and source-page citation; do not
    flatten it into the base-rule summary. This preserves the distinction
    between a rule and a later clarification, and permits an answer to be
    superseded cleanly.
  - [ ] Prioritize links to features already represented by the app: deployment
    and private-information handling; BS Attack/MOD and template behavior;
    hacking Firewall; Marker, Camouflage, Peripheral, and State interactions;
    Coordinated Orders; and Fireteam creation/bonuses/integrity. The FAQ also
    contains scenario-specific rulings, so scope them to the relevant ITS
    season and mission rather than presenting them as universal core rules.
  - [ ] Define an explicit source-precedence and effective-date policy. An on-screen
    answer must show its source date/version and never silently blend conflicting
    documents.
- [ ] Build a versioned ITS reference library from material under
  `data/pdf/its/` and `data/pdf/legacy/`, keeping the current season distinct
  from archived seasons.
  - [ ] Keep season content isolated by season and effective date. A user choosing
    a prior event must see its matching scenario, objectives, extras, and FAQ
    rulings rather than a mixture of seasons. Retain a curated, human-reviewed
    change log/diff rather than relying on raw PDF text diffing.
  - [ ] Treat the official Army app/site as the authority for army-list legality.
    InfinityDB may provide read-only explanation and planning support, but must
    label its snapshot/date and avoid claiming tournament validation.
- [ ] Add ITS scenario list and detail pages backed by a curated seasonal data
  model, rather than PDF excerpts.
  - [ ] Capture structured, cited scenario facts: objectives and scoring, game
    rounds/end conditions, force/point/SWC/table/deployment configuration,
    deployment map or geometry, exclusion zones, token types/diameters,
    classified-objective setup, reinforcement suitability, tactical-support
    options, and scenario-specific rules/elements.
  - [ ] Scenario pages should expose the selected season prominently and link
    season-specific terms to the relevant rules/state references.
- [ ] Add mission-aware list capability guidance once saved-list support exists.
  - [ ] Derive a transparent checklist from the selected ITS scenario and the
    imported profile data: ITS Specialist Troops, relevant equipment/skills,
    Reinforcement or Team-Ops constraints, and scenario interactions. Explain
    missing capabilities without declaring a list illegal or strategically
    inadequate.
  - [ ] Keep temporary scenario-granted skills, designated Troopers, classified
    cards, tactical support, and private information out of static unit
    profiles. They belong to a per-game/session layer, which is not yet part of
    InfinityDB's replaceable imported snapshot.
- [ ] Provide an optional ITS organizer/event companion only after
  user-authored persistent storage and migrations are established.
  - [ ] Support season-aware event setup: published scenarios, allowed extras,
    player count/round guidance, pairings, byes, score entry, and a printable
    control-sheet checklist. Do not infer an official ranking submission or
    replace the Online Tournament Manager.
  - [ ] Include setup aids from ITS documents while keeping organizer choices and
    local participant data clearly separate from official records.
- [ ] Use curated rules coverage to complete the existing Skills, Equipment,
  Weapons, Ammunition, and Traits reference experience.
  - [ ] Add cited, concise summaries and cross-links between a rule, its variants,
    relevant states, ammunition, traits, and unit/loadout uses; make MOD scope
    explicit so profile annotations such as `(+1B)`, `(-3)`, `PH=`, rerolls,
    and Special Dice are not mistaken for universal unit statistics.
- [ ] Add a rules glossary and profile-notation help layer to unit details.
  - [ ] Explain the existing profile fields and symbols in context: training/order,
    troop type, classification, ISC, Hackable, Peripheral, equipment versus
    BS weapons, melee weapons, and profile/loadout separators. Use tooltips or a
    linked glossary rather than making every profile row denser.
  - [ ] Make terminology such as Trooper, Peripheral, Marker, Token, Deployable,
    Null State, Ally/Enemy/Hostile, and Victory Points discoverable wherever it
    changes how profile data should be read.
- [ ] Build a rule-aware Fireteams feature covering both unit eligibility and
  army Fireteam list/detail views.
  - [ ] The imported schema already retains `fireteams`, types, members, and
    descriptions, but the browser does not expose them. Present each army's
    current Army-data chart as authoritative, with membership restrictions,
    min/max requirements, FTO/wildcard notes, and source-data provenance.
  - [ ] Pair it with concise general Fireteam rules while clearly separating general
    rules from army-specific chart exceptions and retaining Infinity Army as the
    current chart authority.
- [ ] Add a Game States reference catalog and contextual state links.
  - [ ] Create cited state pages and link them from skills, equipment, weapon
    traits, and future Fireteam guidance.
  - [ ] Surface interactions that affect the existing UI's concepts, especially
    marker forms, Hidden Deployment, Suppressive Fire, Isolated, Unconscious,
    Possessed, and Peripherals; do not infer a unit's current in-game state
    from its static Army profile.
- [ ] Add a weapon-and-ammunition quick-reference view built from existing
  weapon profiles plus curated rules data.
  - [ ] Normalize display of multi-mode/multi-ammunition profiles, link ammunition
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
