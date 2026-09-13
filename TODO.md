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

- [ ] Provide a small development CLI for `infinity.raw.db`: inspect a raw row,
  list raw rows by normalized table, and verify that an archive matches its
  frontend sibling's metadata.
- [ ] Define a paired-export replacement policy. The frontend and raw archive
  are currently built as temporary siblings; document and test recovery when a
  process stops between replacing either output.
- [ ] Add database-size reporting to `infinity-db build` so snapshot growth is
  visible in build output and CI.
- [ ] Add query-plan regression tests for the high-volume `unit_id`, `item_id`,
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

- [ ] Add a benchmark/health-check command that validates the frontend database,
  confirms its expected raw archive when requested, and reports schema and
  compatibility revisions.
- [ ] Test a full build and container startup in CI, including the requirement
  that deployment images contain only `infinity.db`, not the development raw
  archive.
- [ ] Keep README and architecture-version references synchronized with schema
  and compatibility revisions during every database-format change.
- [ ] Consider snapshot version headers or ETags for HTTP responses so clients
  can recognize a refreshed dataset.

## Potential product features

- [ ] Saved army lists, favourites, and personal notes stored separately from
  the replaceable imported snapshot.
- [ ] Unit comparison view for profiles, loadouts, weapons, skills, and
  equipment across selected units or armies.
- [ ] Rich unit filtering: troop type, classification, availability, points,
  SWC, weapons, equipment, skills, and characteristics.
- [ ] Deep-linkable, shareable search and filter state for catalog and unit
  views.
- [ ] Rules-reference cross-links from profiles, loadouts, skills, equipment,
  and weapon traits to their catalog detail pages.
- [ ] Army-list builder/export integration once user-authored data storage and
  migrations are established.
- [ ] Data-review screens in Developer mode: normalization warnings, source
  record links through `infinity.raw.db`, and unresolved placeholder records.
- [ ] Snapshot comparison view showing additions, removals, and changed unit or
  rules records between two generated databases.

## Completed baseline

- [x] Add targeted secondary indexes for unit-detail and catalog reverse lookup
  paths, including weapon-template joins.
- [x] Split lossless `__row_json` records into `infinity.raw.db`; keep the lean
  `infinity.db` for the frontend and deployment image.
