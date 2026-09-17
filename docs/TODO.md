# InfinityDB backlog

This is the working backlog for performance work, data-pipeline improvements,
and possible product additions. Items are intentionally grouped by outcome
rather than by implementation layer.

`TODO.md` is forward-looking. Keep completed substeps while their parent task is
still open because they clarify progress and remaining scope. Once a standalone
or parent task is complete, remove it after any durable outcome is recorded in
`CHANGELOG.md`, architecture/data-model documentation, or another appropriate
reference. Git history retains implementation detail.

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

## Configuration and domain-knowledge manifests

- [ ] Extract hard-coded Infinity-specific aliases, assumptions, corrections,
  and manual mappings from implementation code where they represent maintained
  project knowledge rather than algorithmic behavior.
  - Keep the distinction explicit:
    - `config/` contains InfinityDB-maintained interpretation, correction,
      mapping, and compatibility policy.
    - `data/curated/` contains human-reviewed facts derived from authoritative
      rules sources and retains source/version/citation information.
    - `data/manifests/` contains generated build provenance and state rather
      than hand-authored project knowledge.
    - Code continues to own algorithms, schemas, parser mechanics, generic
      normalization behavior, validation, and application behavior.
  - Require versioned schemas, validation on load, deterministic
    serialization where generated, focused regression tests, and portable
    project-relative paths for important manifests.
- [ ] Add `config/catalogs/weapon-categories.json`.
  - Move the ordered weapon-family taxonomy and regex patterns out of
    `weapon_categories.py`.
  - Move manual weapon-ID category decisions into the same manifest.
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
- [ ] Add `config/symbols/font-aliases.json`.
  - Move Infinity-asset-specific legacy/exported font-reference overrides out
    of `svg_processor.py`.
  - Keep generic CSS family handling, font weight/stretch interpretation,
    cmap-suffix recognition, installed-font discovery, and matching algorithms
    in code.
- [ ] Extend `config/symbols/static-symbols.json` so static symbol declarations
  can own their semantic metadata as well as their source filenames.
  - Support fields such as stable key, source filename, user-facing label, and
    known source names where needed.
  - Generate browser mappings/labels from the symbol build rather than
    maintaining duplicate symbol knowledge in `unit.js`.
- [ ] Treat `army-symbols.js` and `unit-symbol-map.js` as generated publisher
  output, not authored configuration.
  - Generate them from the pinned Army snapshot, symbol configuration, local
    overrides, and the generated symbol-build manifest.
  - Remove legacy migration assumptions such as first-symbol-wins once the new
    symbol publisher becomes authoritative.
- [ ] Review remaining hard-coded domain tables with the same decision rule:
  prefer derivation from authoritative imported data first, a validated
  manifest second, and code only when the value is implementation behavior.
  - In particular, review fixed weapon-range display bands before creating any
    new config; derive them from weapon metadata if that can produce the
    intended UI.
  - Keep API-source table wiring such as `METADATA_TABLES`, schema definitions,
    generic merge/normalization algorithms, Unicode normalization mechanics,
    database behavior, and UI preference mechanics in code.

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

- [ ] Establish a versioned, curated rules-reference overlay from the supplied
  N5 v5.3 rulebook (`data/eng-n5-update-5-3.pdf`, dated 2026-08-10).
  - Store the overlay in its own SQLite database, with independent schema,
    versioning, and atomic replacement. Do not add PDF-derived facts to
    `infinity.db` or `infinity.raw.db`; application code may combine results by
    stable rule identity only after each database is queried independently.
  - Keep it separate from the replaceable Infinity Army snapshot and key its
    entries by canonical rule identity (skill, equipment, ammunition, trait,
    state, Fireteam concept, and glossary term), with rulebook version and
    printed-page citation.
  - Store original, concise editorial summaries and structured facts (labels,
    requirements, effects, restrictions, related rules, and page locators),
    rather than bulk-extracting or serving the copyrighted PDF text or artwork.
    Confirm permissions and attribution/linking requirements before publishing
    any rule-derived prose.
  - Add a coverage report that flags Army metadata items with no matching
    reference entry, ambiguous names/levels/MOD variants, and entries whose
    cited rulebook version is stale. The PDF labels changed text visually, but
    a prior-version comparison is needed before claiming a specific change.
- [ ] Add a dated FAQ/errata layer to the rules-reference overlay, starting
  with `data/eng-faqs-n5-v0-1.pdf` (2026-08-25, four printed FAQ pages).
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
  - Define an explicit source-precedence and effective-date policy. ITS Season
    18 says official rules, FAQs, Wiki, errata, and army lists published up to
    one week before an event apply (p. 9); an on-screen answer must show its
    source date/version and never silently blend conflicting documents.
- [ ] Build a versioned ITS reference library, with Season 18 as current
  (`data/its-18-en.pdf`, v2026.09.01) and Season 17 as an archived, selectable
  reference (`data/its-rules-season-17-en-v1.0.2.pdf`, internally v0.2).
  - Keep season content isolated by season and effective date. A user choosing
    a prior event must see its matching scenario, objectives, extras, and FAQ
    rulings—not a mix of Season 17 and Season 18 rules. Retain a curated,
    human-reviewed change log/diff rather than relying on raw PDF text diffing.
  - Treat the official Army app/site as the authority for army-list legality,
    as the ITS rules require. InfinityDB may provide read-only explanation and
    planning support, but must label its snapshot/date and avoid claiming
    tournament validation.
- [ ] Add ITS scenario list and detail pages backed by a curated seasonal data
  model, rather than PDF excerpts.
  - Capture structured, cited scenario facts: objectives and scoring, game
    rounds/end conditions, force/point/SWC/table/deployment configuration,
    deployment map or geometry, exclusion zones, token types/diameters,
    classified-objective setup, reinforcement suitability, tactical-support
    options, and scenario-specific rules/elements.
  - Season 18 supplies Resilience Operations plus 15 standard scenarios and
    five Direct Action scenarios (contents pp. 37-132); Season 17 remains a
    useful historical comparison. Scenario pages should expose the selected
    season prominently and link terms such as CivEvac, Casevac, HVT, Key Ops,
    zones, and tactical elements to the relevant rules/state references.
- [ ] Add mission-aware list capability guidance once saved-list support exists.
  - Derive a transparent checklist from the selected ITS scenario and the
    imported profile data: ITS Specialist Troops (Hackers, Doctors, Engineers,
    Forward Observers, Paramedics, Chain of Command, Specialist Operative),
    relevant equipment/skills, Reinforcement or Team-Ops constraints, and
    scenario interactions. Explain missing capabilities without declaring a
    list illegal or strategically inadequate.
  - Keep temporary scenario-granted skills, designated Troopers, classified
    cards, tactical support, and private information out of static unit
    profiles. They belong to a per-game/session layer, which is not yet part
    of InfinityDB's replaceable imported snapshot.
- [ ] Provide an optional ITS organizer/event companion only after
  user-authored persistent storage and migrations are established.
  - Support season-aware event setup: published scenarios, allowed extras,
    player count/round guidance, pairings, byes, score entry, and a printable
    control-sheet checklist. Do not infer an official ranking submission or
    replace the Online Tournament Manager.
  - Include setup aids from the ITS documents (token sizing, terrain guidance,
    table/deployment configuration, and mission elements), but make event
    organizer choices and any local participant data clearly separate from
    official records.
- [ ] Use the rulebook to complete the existing Skills, Equipment, Weapons,
  Ammunition, and Traits reference pages.
  - The current catalogs expose Army metadata, reverse unit uses, and only a
    small set of concise Trait descriptions. The v5.3 rules provide structured
    labels, requirements, effects, restrictions, levels, and interactions for
    common/special skills (pp. 75-118), equipment (pp. 119-127), and weapon
    and ammunition rules (quick-reference chart from p. 176).
  - Add cited, concise summaries and cross-links between a rule, its variants,
    relevant states, ammunition, traits, and unit/loadout uses; make MOD scope
    explicit so profile annotations such as `(+1B)`, `(-3)`, `PH=`, rerolls,
    and Special Dice are not mistaken for universal unit statistics.
- [ ] Add a rules glossary and profile-notation help layer to unit details.
  - Explain the existing profile fields and symbols in context: training/order,
    troop type, classification, ISC, Hackable, Peripheral, equipment versus
    BS weapons, melee weapons, and the profile/loadout separators (rulebook
    pp. 7-9 and glossary p. 173). Use tooltips or a linked glossary rather than
    making every profile row denser.
  - Make terminology such as Trooper, Peripheral, Marker, Token, Deployable,
    Null State, Ally/Enemy/Hostile, and Victory Points discoverable wherever
    it changes how profile data should be read.
- [ ] Turn the existing Fireteam eligibility and list/detail-page backlog into
  a rule-aware Fireteams feature.
  - The imported schema already retains `fireteams`, types, members, and
    descriptions, but the browser does not expose them. Present each army's
    current Army-data chart as authoritative, with membership restrictions,
    min/max requirements, FTO/wildcard notes, and source-data provenance.
  - Pair it with concise v5.3 general rules: formation/coherency, leader,
    integrity, active/reactive behavior, Fireteam levels, and bonuses
    (pp. 132-136). Clearly separate general rules from army-specific chart
    exceptions and warn that Infinity Army is the current chart authority.
- [ ] Add a Game States reference catalog and contextual state links.
  - The rulebook defines activation, effects, cancellation, and Null-State
    status for states on pp. 157-172, while InfinityDB currently has no state
    catalog. Create cited state pages and link them from skills, equipment,
    weapon traits, and future Fireteam guidance.
  - Surface interactions that affect the existing UI's concepts, especially
    marker forms, Hidden Deployment, Suppressive Fire, Isolated, Unconscious,
    Possessed, and Peripherals; do not infer a unit's current in-game state
    from its static Army profile.
- [ ] Add a weapon-and-ammunition quick-reference view built from existing
  weapon profiles plus a curated rules overlay.
  - Existing weapon pages already show profiles, traits, ranges, and special
    weapon data. The v5.3 weapon chart supplies the player-facing reading
    model—range bands, PS, Burst, ammunition, saving-roll attribute/count,
    and traits (p. 176 onward)—and the rules explain their game effects.
  - Normalize display of multi-mode/multi-ammunition profiles, link
    ammunition names and traits to their effects, and provide a unit-neutral
    comparison/filter view. Validate it against Army metadata; do not copy the
    chart wholesale into the application.
- [ ] Add optional play-aid pages for core procedures, distinct from the unit
  database: order expenditure/ARO sequence, modifiers, movement/combat
  resolution, command tokens, and Fireteam quick reference. The rulebook
  explicitly organizes these as repeatable game flows (basic rules pp. 6-74,
  command pp. 128-131, quick-reference charts pp. 176-195); concise,
  cited checklists would make the existing catalog more useful at the table.
- [ ] When a saved army-list builder is introduced, use the rules reference to
  add game-mode and list-review guidance—not hidden-information disclosure.
  The v5.3 game modes specify table/deployment/points/SWC guidance (p. 6) and
  the rules distinguish private from open list information (p. 7). Keep any
  share/export view privacy-aware and treat the Army app/data as authoritative
  for list legality.
- [ ] Add fuller rules summaries for skills, equipment, ammunition, and
  remaining traits.
- [ ] Add a curated Infinity Wiki URL mapping for traits when authoritative links are available.
- [ ] Show unit Fireteam eligibility on the unit-details page.
- [ ] Add Fireteam list and detail pages.
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
