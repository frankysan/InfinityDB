# InfinityDB backlog

This is the working backlog for performance work, data-pipeline improvements,
and possible product additions. Items are intentionally grouped by outcome
rather than by implementation layer.

Everything not represented by a checked checkbox is **planned/unimplemented work**,
even when its parent task contains completed substeps. This file does not define
current application behavior or claim that an accepted architecture is already
implemented; current behavior belongs in the relevant reference documentation,
while lasting design direction belongs in `docs/architecture.md` or
`docs/data-model.md`, and durable release acceptance criteria belong in
`docs/releasing.md`.

Keep completed substeps while their parent task is still open because they
clarify progress and remaining scope. Once a standalone or parent task is
complete, remove it after any durable outcome is recorded in `CHANGELOG.md`,
architecture/data-model documentation, or another appropriate reference. Git
history retains implementation detail.

## Current milestone

**Milestone 2B — continue the canonical application model and advance 1.0
completeness.** Continue semantic coverage beyond the runtime surface completed
for 0.6.1: broader relationships and source-only catalog/metadata structures,
the `infinity.raw.db` separation, and the source-to-presentation completeness
inventory. Use that inventory as groundwork for the broader web-app consistency
audit. The durable version-1.0 acceptance criteria are maintained in
`docs/releasing.md`.

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
- [ ] Provide a small development CLI for `infinity.raw.db`: inspect a raw row,
  list raw rows by normalized table, and verify that an archive matches its
  frontend sibling's metadata.
- [ ] Define a paired-export replacement policy. The frontend and raw archive
  are currently built as temporary siblings; document and test recovery when a
  process stops between replacing either output.
- [ ] Add database-size reporting to `infinity-db build` so snapshot growth is
  visible in build output and CI.
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

### Active Milestone 2B work

This section contains only active Milestone 2B work. The completed 0.6.1
canonicalization evidence, benchmarks, classifications, and upgrade requirements
remain in `docs/data-model.md` and `docs/CHANGELOG.md`; release procedure belongs
in `docs/releasing.md`.

- [ ] **Audit relationships after entity canonicalization.**
  - [ ] Revisit includes and distinguish visible endpoint data from the independently
    meaningful relationship between those endpoints; use the clean target-resolution audit
    as evidence before materializing canonical include relationships.
  - [ ] Complete the Peripheral rules/identity work described in
    `docs/peripheral-curated-data-design.md`.
    - [ ] Extend the existing curated-rules pipeline with reviewed Doctor, Engineer,
      Cyberplug, and Peripheral skill records plus the five N5.3 Peripheral types; do not
      create a parallel Peripheral rules loader/database.
    - [ ] Design a separate reviewed source-to-Peripheral identity/mapping contract; do not
      overload the current display-identity contract or write Wiki/rules knowledge into Army
      source tables.
    - [ ] Materialize curated-derived controller-eligibility and cross-army Peripheral
      relationships only after the source mapping and rules vocabulary are both validated.
  - [ ] Audit relation/dependency structures.
  - [ ] Audit Fireteam structures.
    - [ ] Treat Fireteam Charts as Army-local relationship/configuration data:
      preserve Fireteam type quotas, named Fireteams, type membership, min/max
      formation constraints, required-choice pools, chart notes, FTO restrictions,
      Wildcards, and bracketed Fireteam-Level equivalence terms without promoting
      them to intrinsic logical-Unit facts.
    - [ ] Resolve FTO eligibility to the applicable source option/loadout identity
      rather than treating a Unit-level Fireteam member match as sufficient; retain
      unresolved/ambiguous source wording instead of guessing.
    - [ ] Interpret the source `required` flag as participation in the chart's
      required-choice set where applicable, not as "every flagged row is mandatory",
      and preserve chart notes because the rules allow them to override general
      Fireteam rules.
  - [ ] Identify normalization-only link structures that do not constitute
    additional player-facing information.
  - [ ] Record any distinct player-relevant relationship not currently
    presentable by the application as a 1.0 completeness gap.

- [ ] **Separate lossless source storage from the application database after
  canonicalization.**
  This milestone refers to the existing `infinity.raw.db`; no additional
  lossless database artifact is planned.
  - [ ] Treat `infinity.raw.db` as the complete lossless normalized Army source/
    provenance store, including source-local identities, source ordering,
    raw fallbacks, and acquisition/audit metadata required to reconstruct
    the imported source.
  - [ ] Inventory every remaining `infinity.db` table and repository/API query and
    classify it as canonical application data, explicit contextual application
    data, or source/provenance-only data.
  - [ ] Move source/provenance-only normalized tables out of `infinity.db` only
    after canonical unit/profile/loadout/relationship/catalog replacements are
    proven complete and reconstruction/provenance tests cover the transition.
  - [ ] Make normal repository/API/web serving independent of `infinity.raw.db`;
    production runtime should require the self-contained canonical `infinity.db`
    plus the existing rules database/assets, while `infinity.raw.db` remains
    a build/audit artifact.
  - [ ] Preserve traceability from every canonical fact and contextual occurrence
    back to supporting raw/source records after the physical database split.
  - [ ] Document the rebuild/migration boundary and verify that removing the
    duplicated source representation reduces physical application-database size
    without using storage savings as the semantic acceptance criterion.

- [ ] **Maintain a source-to-presentation completeness inventory while
  canonicalizing.**
  - [ ] Trace relevant original Army JSON constructs through normalization,
    canonical application meaning, repository/API representation, and web
    presentation.
  - [ ] Record the semantic-provenance category and canonical documentation
    location for every source-derived fact, InfinityDB abstraction, and
    presentation convenience encountered by the inventory.
  - [ ] Classify each construct as explicitly presented, implicitly represented,
    operationally consumed, redundant source representation,
    normalization-only structure, or unrepresented player information.
  - [ ] Add confirmed unrepresented player information to the 1.0 completeness
    backlog.
  - [ ] Do not treat unused tables/columns alone as proof of a completeness gap.

- [ ] **Complete a rules-semantics documentation pass across the current ruleset.**
  Keep page-level progress, source versions, and individual findings in
  `docs/rules-audit.md`; use this backlog only for section-level completion.
  - [x] Establish `docs/rules-audit.md`, `docs/rules-semantics.md`, and
    `docs/rules-research.md`, including the source/finding classification contract.
  - [ ] Audit the wiki/PDF rules sections, using the wiki Main Sections structure as
    the traversal spine and the current PDF/FAQ material for stable citations:
    - [ ] Introduction.
    - [x] Basic Rules.
    - [x] Game States and Glossary.
    - [x] Skills and Equipment.
    - [x] Combat.
    - [x] Ammunition and Weaponry.
    - [x] Fireteams.
    - [x] Command.
    - [x] Movement.
    - [x] Terrain and Scenery Structures.
    - [x] Triumph and Defeat.
    - [x] Setting up the Gaming Table.
    - [ ] Scenarios.
    - [ ] Quick Reference Charts as a validation/completeness pass.
    - [ ] Reinforcements, retaining its distinct rules scope.
    - [ ] ITS FAQ, retaining season/scenario scope rather than treating it as core rules.
  - [ ] Reconcile implementation-relevant findings against Army/API fields, the
    canonical application model, validation, querying/filtering, and browser
    presentation; distinguish source-native concepts from InfinityDB abstractions.
  - [ ] Record verified findings with no current consumer in `docs/rules-research.md`
    instead of forcing premature schema or UI changes.
  - [ ] Re-review the accumulated `rules-semantics.md` and `rules-research.md`
    findings against the architectural rule that rules are semantic evidence,
    not the application schema. Keep material that improves catalog/data
    interpretation, relationships, validation, querying, or presentation (plus
    necessary explanatory context); demote or remove procedural/edge-case detail
    that does not serve InfinityDB's reference responsibilities, without treating
    audit completeness as a requirement to model the complete ruleset.
  - [ ] Complete a final gap analysis and feed confirmed implementation work into
    the existing canonical-model, completeness, and product-feature backlogs.

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
  - [ ] `path_sanitization.py`: remain shared infrastructure for external/mirror
    naming; pipeline-generated asset names should use one host-independent
    policy.
  - [ ] Longer-term reusable modules may be split into `snapshot`, `discovery`,
    `manifest`, `downloader`, `audit`, `deduplicate`, `convert`, `compress`, and
    `publish` helpers when that reduces duplication rather than adding ceremony.

- [ ] Make every integrated symbol stage idempotent and traceable before adding
  sophisticated incremental caching.
  - [ ] Changes to an override SHA-256 invalidate downstream processing for that
    asset. Removing an override falls back to validated symbol archives/cache or
    network by the normal resolution rules.
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
  - [ ] Snapshot/discovery tests: metadata/faction validation, complete archive,
    snapshot identity/hash, all profile/faction logos, multiple logos for one
    unit, one logo shared by units, duplicate URLs, static declarations,
    override suppression of network, override over cache, invalid/unused
    overrides, filename collisions, unexpected SVG fields, and proof that
    `resume` is not required for complete discovery.
  - [ ] SVG fixtures: exact duplicate, XML-different visual duplicate, no-text,
    normal text, alias-font, missing-font, empty-text cleanup, and troublesome
    real-world conversion cases.
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

The implemented CI contract is documented in `docs/ci.md`. Remaining backlog
work is limited to:

- [ ] Integrate curated snapshot-note validation into routine project checks so
  every checked-in file under `data/curated/snapshot-notes/` is validated even
  when no downloader or comparison workflow happens to load it.
- [ ] Retain release evidence for the configured hosted workflows. Before
  claiming a release has passed hosted CI, record successful `Source checks`,
  `Installed wheel smoke`, and `Deployment smoke test` runs for the release
  commit or tag.
- [ ] Complete optional/manual full-asset CI administration by adding authorized
  `FULL_ASSET_BUNDLE_URL` and `FULL_ASSET_BUNDLE_SHA256` secrets to the existing
  `full-assets` environment, then record one successful manual run.

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
    its semantic-provenance category, source meaning/evidence, storage
    representation, derivation or canonical/application interpretation, API
    representation, browser consumers, canonical documentation location, existing
    coverage, and audit result. Cover logical/source unit identity; army hierarchy, role,
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

The accepted UX, backend/frontend responsibility, and theming direction is
maintained in `docs/architecture.md`. This backlog contains only implementation
work against that contract.

- [ ] Refactor the web layer toward the documented backend/frontend responsibility
  boundary without changing the current same-origin deployment model.
  - [ ] Split API handling, shared page-shell/static delivery, and top-level request
    dispatch into visibly separate Python concerns while preserving existing URLs.
  - [ ] Organize browser code around explicit API transport, preferences/theme
    state, reusable view/components, and page modules; keep JSON API access routed
    through `api.js`.
  - [ ] Add focused contract/regression coverage as responsibilities move so domain
    interpretation cannot silently migrate back into browser code.

- [ ] Implement first-class Light and Dark themes using the semantic theme contract
  documented in `docs/architecture.md`.
  - [ ] Separate semantic theme tokens from theme-neutral layout/component rules
    and remove remaining hard-coded light-theme assumptions.
  - [ ] Decide and document the default startup behavior (for example, operating-
    system preference versus a fixed project default); an explicit user choice wins.
  - [ ] Add the theme selector to Settings, resolve the selected theme before first
    meaningful paint, and keep persistence on the existing preference contract.
  - [ ] Audit contrast and distinguishability for status/range colors, links, focus,
    muted text, tables, dialogs, menus, and faction accents in both themes.
  - [ ] Add regression coverage for initialization, switching, persistence, and
    representative core pages in both themes.

- [ ] Add a project favicon derived from `infinitydb-logo.svg` and keep it legible
  in light and dark browser chrome where practical.

- [ ] Refactor the frontend design-system structure after the theme contract is
  implemented: separate foundational tokens, theme values, shared components/layout,
  and page-specific exceptions where that improves ownership without adding a CSS
  build step. Promote recurring patterns to shared primitives and preserve the
  established shared shell, navigation, detail, table-density, badge, and Settings
  behavior during the migration.

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
- [ ] Split the growing pytest stage into marker-based local sections (for example
  data/model, web/API, build/ingestion, operations/tooling, and assets) so
  developers can run the relevant slice during iteration. Keep the complete suite
  as the authoritative final gate; the 2026-09-20 local full run is 606 tests and
  takes roughly 73 seconds on the primary development machine.

## Public-identifier follow-up

- [ ] Before retiring or redirecting numeric routes, define and implement the
  per-domain slug-freezing, reviewed-override, alias/redirect, and canonical-URL
  compatibility policy documented as future work in `docs/architecture.md`.

## Potential product features

- [ ] Expand the existing versioned curated rules-reference infrastructure with
  substantially broader N5 v5.3 coverage from
  `data/pdf/rules/n5-rules-v5-3-en.pdf` (dated 2026-08-10).
  - [ ] Expand canonical rule identities across skills, equipment, ammunition,
    traits, states, Hacking Programs, Fireteam concepts, glossary terms, and other
    useful rule domains, retaining rulebook version and printed-page citation.
  - [ ] Reconcile N5 weapon-profile presentation terminology with the current
    Combat rules. Army metadata still exposes the source field as `damage`, but
    N5 V5.3 defines that value as Possibility of Survival (PS); the web weapon
    profile currently labels it `DAM`. Preserve source provenance while exposing
    the rules-native `PS` term to users, and cover both ranged and melee profiles.
  - [ ] Add reviewed Hacking Program identities plus explicit Hacking Device ->
    Program and Upgrade-Program relationships. Keep Hacking Area, Firewall,
    Supportware, and target/state effects as rules-derived semantics rather than
    inferring a complete hacking graph from Army Equipment names.
  - [ ] Reconcile the existing declaration-category records with the current N5
    V5.3 Skills and Equipment rules before expanding that dataset: remove stale
    category names/mappings, refresh printed-page citations, and generalize the
    link contract so actions supplied by Equipment are not represented as Skills.
    Preserve Army-derived compatibility/source shapes such as `Regular` appearing
    in skill-like data without treating those shapes as the rules-domain
    classification; `Regular`/`Irregular` remain Training semantics in InfinityDB.
    Validate authored category names against the canonical `skillTypes` vocabulary
    and resolve links against the correct Army catalog domain.
  - [ ] Model Ammunition rules as first-class cited identities and relationships.
    Distinguish the eleven base Ammunition types from source-defined combined
    forms, preserve component relationships for combined Ammunition, and keep
    Ammunition composition separate from Combined Saving Roll notation. Link
    state/Attribute/Saving-Roll effects explicitly instead of deriving them from
    Ammunition display names.
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
- [ ] Improve General profile versus Army-profile stat-difference signposting.
  - [ ] Keep the existing indicator on an Army-profile stat when it differs from
    the General profile.
  - [ ] Also mark the General profile stat with a small superscript `*` and a
    descriptive tooltip whenever one or more Army profiles differ from it.
- [ ] Build a rule-aware Fireteams feature covering both unit eligibility and
  army Fireteam list/detail views.
  - [ ] The imported schema already retains `fireteams`, types, members, and
    descriptions, but the browser does not expose them. Present each army's
    current Army-data chart as authoritative, with membership restrictions,
    min/max requirements, FTO/wildcard notes, and source-data provenance.
  - [ ] Pair it with concise general Fireteam rules while clearly separating general
    rules from army-specific chart exceptions and retaining Infinity Army as the
    current chart authority.
  - [ ] Make historically/community-significant Fireteam vocabulary discoverable
    without presenting it as current N5 terminology. In particular, map historical
    official `Linkable` and community `pure Fireteam` usage to the current
    chart-eligibility / Fireteam-Level concepts with provenance-aware aliases/help.
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
    comparison/filter view. Preserve the field-specific meaning of `+`: Ammunition
    composition and Combined Saving Rolls are separate rules operations. Validate
    the view against Army metadata; do not copy source charts wholesale into the
    application.
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
