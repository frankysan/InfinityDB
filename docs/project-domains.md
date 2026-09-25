# Project domains

**Project domain:** Project infrastructure

InfinityDB uses a small set of **project domains** to identify which part of the
project owns a change, feature, defect, design decision, or backlog item. These
labels describe engineering and operational responsibility; they are separate
from Infinity game-data domains such as Skills, Equipment, Weapons, Traits, or
States.

The canonical project domains are:

## Acquisition

Owns explicit source acquisition and the tooling that creates or preserves the
source/asset archives used by later stages.

Typical responsibilities include:

- downloading and pinning Infinity Army, wiki, symbol, and other supported source
  material;
- source snapshot/archive creation, naming, provenance, resume behavior, and
  integrity checks;
- source graphical-asset acquisition, preparation, conversion, deduplication,
  compression, and publication inputs;
- acquisition-specific local caches, manifests, reports, and recovery tooling.

The Acquisition boundary ends when a stable source/archive or prepared asset set
is available for downstream use. Normal database builds and the running web
application must not perform implicit acquisition.

## Data processing

Owns curated/source data semantics and the deterministic transformations that
turn acquired or maintained inputs into InfinityDB's generated databases and
other structured application data.

Typical responsibilities include:

- maintained curated data, schemas, aliases, mappings, semantic relations, and
  validation rules;
- Army merge, normalization, identity resolution, enrichment, and provenance;
- rules/reference curation and validation;
- SQLite schema/export behavior and generation of `infinity.db`,
  `infinity.raw.db`, and `rules.db`;
- deterministic generated-data contracts and data-build audits.

This domain includes the meaning and correctness of curated/normalized data, not
only the final export step. Runtime querying of already-built databases belongs
to Web backend.

## Deployment

Owns packaging and operating InfinityDB as a hosted service.

Typical responsibilities include:

- container/runtime packaging and deployment artifacts;
- server install, update, rollback, migration, and deployment verification;
- production configuration, reverse-proxy/service integration, and operational
  maintenance;
- production monitoring, aggregate observability, logging policy, and resource
  health.

CI, local developer checks, release bookkeeping, and repository maintenance do
not become Deployment work merely because they can affect a future deployment;
those normally belong to Project infrastructure.

## Web backend

Owns server-side runtime behavior for the web application and HTTP API.

Typical responsibilities include:

- application startup and runtime database access;
- repository/query logic used by HTTP surfaces;
- route resolution, request validation, API payloads, and server-side response
  behavior;
- backend-owned presentation semantics exposed to the browser;
- runtime caching and other server-side application behavior.

Build-time normalization and database generation belong to Data processing.
Browser rendering and interaction belong to Web frontend.

## Web frontend

Owns the browser UI and all directly user-facing browser behavior and visuals.

Typical responsibilities include:

- HTML, CSS, and browser JavaScript;
- navigation, filtering, preferences, interaction, and client-side state;
- visual presentation, labels, layout, responsive behavior, and theming;
- accessibility and browser-side performance/compatibility;
- user-facing handling of backend/API data.

A change that only alters the data supplied by an API is Web backend; a change
that alters how the browser presents or interacts with that data is Web
frontend. Changes that materially alter both contracts may name both domains.

## Project infrastructure

Owns repository-wide development, validation, release, and contributor support
that is not itself product/runtime behavior.

Typical responsibilities include:

- CI workflows and shared test/check orchestration;
- packaging/versioning and release-process tooling;
- developer utilities such as deterministic work-archive creation;
- repository configuration and contributor/agent policy;
- documentation conventions and other cross-project engineering process.

Tests normally inherit the project domain of the behavior they test. A change to
the test framework, common fixtures, CI execution model, or check orchestration
is Project infrastructure instead.

## Classification rules

Use the domain that owns the behavior or durable contract being changed, not
merely the directory containing the edited file.

- Prefer one primary domain when one responsibility clearly owns the outcome.
- Name multiple domains only when the change materially crosses their contract
  boundary. Do not add secondary labels merely because another layer consumes
  the result.
- Documentation inherits the domain of its subject. Changes to documentation
  policy or structure itself are Project infrastructure.
- Tests inherit the domain of the behavior under test unless the test machinery
  itself is what changed.
- Generated artifacts inherit the domain of the process that defines/builds
  them. Their later packaging or serving does not reclassify the generating
  change.
- Do not use Deployment as a catch-all for CI, release tooling, or developer
  workflow.

## Documentation convention

All new or materially revised documentation about a change, addition, feature,
defect, design decision, or planned work must identify its project domain using
the exact labels above.

For individual backlog or changelog entries, prefix the entry with the domain:

```text
- **Web frontend:** Improve mobile navigation behavior.
- **Data processing + Web backend:** Expose a newly normalized relationship through the API.
```

For a section or document whose scope is consistently owned by one or more
project domains, a section-level declaration may be used instead:

```text
**Project domain:** Deployment
```

or:

```text
**Project domains:** Web backend, Web frontend
```

A section-level declaration covers its contained items unless an item explicitly
states another domain. Historical release notes and untouched legacy backlog
entries do not need a mass retroactive relabel; once an entry is materially
rewritten, apply the current convention.
