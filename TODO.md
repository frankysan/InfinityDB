# InfinityDB backlog

This is the working backlog for performance work, data-pipeline improvements,
and possible product additions. Items are intentionally grouped by outcome
rather than by implementation layer. Check an item only after its tests and
documentation are complete.

## Next: performance

- [x] Build one private, per-`Database` cached unit graph.
  - Load source units, army memberships, parsed availability filters, unit
    factions, search terms, and logical-unit groups once per database snapshot.
  - Include a `source_unit_id -> logical group` lookup for detail routes.
  - Have `list_units`, `get_unit`, `get_skill`, and catalog-detail routes use
    this shared graph rather than rebuilding it independently.
  - Keep cached graph data immutable, or copy only request-local structures,
    so optional-unit filters cannot mutate state shared by requests.
- [x] Replace catalog-detail pagination through `list_units(limit=500,
  offset=...)` with an internal helper that returns the complete visible-unit
  mapping once.
- [ ] Benchmark cold and warm requests per worker for unit lists, unit details,
  skills, equipment, and weapons. Record median and p95 timings against a
  representative snapshot before and after each performance change.
- [x] Review catalog extra joins. Detail queries previously unioned extra-link
  tables before joining them. Review confirmed SQLite materializes every
  source table and creates an automatic temporary index; rewrite each source
  branch to join its matching extras table through its `(occurrence_id,
  position)` primary key.
- [ ] Evaluate SQLite `immutable=1` for deployed snapshots. Enable it only when
  the process never observes an in-place database replacement.

## Database and data pipeline

- [x] Optimize the JSON-to-SQLite import after benchmarking the following
  measured hot paths (current generated snapshot: 25.2 MB normalized JSON,
  198,647 normalized rows, 13.7 MB frontend DB, and 37.7 MB raw archive):
  - [x] Cache each table's derived column tuple after input validation. It is
    currently scanned once by `validate_input`, again by `create_schema`, and
    again before its frontend insert.
  - [x] Feed `executemany` in bounded batches (especially the raw archive's single
    198k-row list) so serialization and parameter tuples are not all retained
    at once.
  - [x] Build secondary indexes after loading table data, then run `ANALYZE`; keep
    primary keys and foreign-key validation intact. This avoids maintaining the
    read-only indexes during every insert.
  - Generated-snapshot smoke export: 8.45 seconds, 13.4 MB frontend DB, and
    37.7 MB raw archive. Repeat this measurement on CI or a fixed development
    host before treating it as a performance regression baseline.
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
- [x] Add query-plan regression tests for the high-volume `unit_id`, `item_id`,
  and weapon-template lookup paths.
- [x] Run `ANALYZE` after importing and indexing the immutable frontend snapshot,
  then verify `sqlite_stat1` is present. This gives SQLite durable cardinality
  statistics for join-order decisions without adding request-time work.
- [ ] Decide whether dynamic, source-only columns should remain in the frontend
  schema or move exclusively to the raw archive once no runtime query consumes
  them.
- [ ] Establish a migration policy for future persistent user-authored data;
  imported snapshots are intentionally replaced wholesale today.

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
- [x] Send snapshot-aware ETags for successful API responses and expose the
  snapshot revision to the browser refresh check so clients recognize a
  refreshed dataset.

## Potential product features

- [x] Add list and detail pages for traits.
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

## Completed baseline

- [x] Add targeted secondary indexes for unit-detail and catalog reverse lookup
  paths, including weapon-template joins.
- [x] Split lossless `__row_json` records into `infinity.raw.db`; keep the lean
  `infinity.db` for the frontend and deployment image.
