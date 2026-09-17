# Curated data

`data/curated/` contains source-controlled, human-reviewed information derived
from external sources. Curated material is distinct from immutable external
inputs under `data/raw/`, `data/wiki/`, and `data/pdf/`, and from generated
provenance under `data/manifests/`.

## Current curated data

`rules/` contains validated rules-reference collections and is the only curated
subtree currently consumed by application build tooling. `infinity-db
build-rules` defaults to `data/curated/rules/`.

The sections below document the implemented `curated/rules/` contract.

## Other curated categories

`data/curated/snapshot-notes/` defines the current versioned contract for
human-maintained snapshot descriptions, comparison targets, and notable-change
notes associated with immutable snapshots by SHA-256. Those notes remain
separate from generated snapshot provenance and are not rules-database inputs.
Acquisition tooling never writes or consumes this subtree; see
[`snapshot-notes/README.md`](snapshot-notes/README.md).

## Curated rules reference data

This directory is the handoff from local wiki/PDF research to rules-data
ingestion. Developers and agents may read reference material in `data/wiki/`
and `data/pdf/`, then write concise, human-reviewed facts under
`data/curated/rules/`. The application and its build pipeline never read those
raw reference trees directly.

### Available reference families

The local reference corpus may include:

- N5 core rules revisions under `data/pdf/rules/`.
- N5 FAQ revisions under `data/pdf/faq/`.
- ITS seasons under `data/pdf/its/` and `data/pdf/legacy/`.
- Wiki research snapshots under `data/wiki/`; the current downloader writes
  `WIKI YYYYMMDD-HHMMSS.zip` archives.

Core rules can provide curated skills, equipment, weapons, ammunition, traits,
states, attributes, timing, modifiers, deployment, hacking, fireteams, and
interactions. FAQ records represent dated clarifications or rulings. ITS records
remain season-scoped and can represent scenarios, objectives, scoring,
deployment, and mission constraints. Wiki pages are useful for discovery,
aliases, cross-links, and concise explanations, but do not override applicable
official rules or Army data.

### Current v2 contract

Place one collection per subject or release under `data/curated/rules/`, for
example `rules/n5-core-v5.3.json`. Each file contains:

- `format`: `InfinityDB curated reference`
- `formatVersion`: `2`
- `collection`: `id`, `title`, `domain`, `status`, `effectiveFrom`, and
  `authority`
- `sources`: PDF or wiki source records with version, authority, a local path or
  URL, and source-specific publication metadata
- `vocabularySources`: source references for maintained skill-type and label
  vocabularies
- `skillTypes`: declared skill-type vocabulary
- `labels`: declared label vocabulary
- `records`: concise original summaries with typed `kind`, `id`, `name`,
  `summary`, optional facts/links, and one or more `citations`

Record citations distinguish PDF and wiki sources. PDF citations require a
positive **printed** `page` number. Wiki record citations require a `path` and
`snapshotDate`; the corresponding source may identify a preserved local mirror
or an exact pinned revision URL.

`vocabularySources` is currently a legacy exception: each entry is required to
contain `sourceId`, `path`, `snapshotDate`, `heading`, and a positive `page`,
regardless of the cleaner source-specific record-citation model. The checked-in
v5.3 collection therefore carries wiki path/date provenance together with page
numbers for vocabulary definitions. Treat that as current schema behavior, not
as the intended general rule for wiki provenance.

Do not bulk-copy PDF or wiki text, images, or page markup. Keep core rules,
FAQs/errata, and ITS seasons in separate collections so versions cannot be
blended accidentally.

### Document shape

The main collection structure is:

```json
{
    "format": "InfinityDB curated reference",
    "formatVersion": 2,
    "collection": {
        "id": "n5-core-v5.3",
        "title": "N5 Core Rules v5.3",
        "domain": "core-rules",
        "status": "current",
        "effectiveFrom": "2026-08-10",
        "authority": "primary"
    },
    "vocabularySources": {
        "skillTypes": [],
        "labels": []
    },
    "skillTypes": [],
    "labels": [],
    "sources": [
        {
            "id": "n5-core-v5.3-pdf",
            "kind": "pdf",
            "title": "N5 Core Rules",
            "version": "5.3",
            "publishedDate": "2026-08-10",
            "localPath": "data/pdf/rules/n5-rules-v5-3-en.pdf",
            "pageCount": 196,
            "sha256": "...",
            "authority": "primary"
        }
    ],
    "records": [
        {
            "id": "rule:camouflaged-state",
            "kind": "state",
            "name": "Camouflaged State",
            "aliases": ["Camouflage"],
            "summary": "Concise human-written summary.",
            "scope": {"game": "N5", "seasons": ["current"]},
            "facts": {
                "category": "state",
                "timing": ["States Phase"],
                "effects": [],
                "requirements": [],
                "restrictions": [],
                "interactions": ["rule:discover", "rule:surprise-attack"]
            },
            "armyLinks": [{"entity": "skill", "id": 42}],
            "relatedRecords": ["rule:camouflage", "rule:marker-state"],
            "citations": [
                {"sourceId": "n5-core-v5.3-pdf", "page": 113, "section": "States"}
            ],
            "review": {"status": "reviewed", "reviewedOn": "2026-09-15"}
        }
    ]
}
```

Supported record kinds include `rule`, `skill`, `equipment`, `weapon`,
`ammunition`, `trait`, `state`, `glossary`, `interaction`, `fireteam`,
`faq-ruling`, `erratum`, `scenario`, `objective`, `mission`, `deployment`, and
`unit-annotation`.


Weapon records may use `facts.specialProfile` for rulebook-defined deployable
profiles that are not fully represented by Army weapon metadata. The special
profile stores ordered stat name/value pairs, equipment, skills, and a CC weapon;
the application composes it into the existing weapon-reference API only when a
validated `rules.db` is available.

Trait records may use `facts.sourceIdentity.prefixes` for source labels whose
parameter value is part of the Army text, for example `Disposable (2)` mapping
to the canonical `Disposable (X)` record. Exact alternate spellings and
misspellings belong in the normal `aliases` array. This is source-identity data;
the matching algorithm remains application code.

Army links may target existing `skills`, `equipment`, `weapons`, `ammunition`,
`extras`, `characteristics`, `troop_types`, `units`, or profile occurrences.
They annotate Army data; they do not establish list legality or replace
Army-derived statistics.

A wiki record citation currently uses the snapshot date and a path within the
selected mirror, for example:

```json
{
    "sourceId": "wiki-20260915",
    "path": "infinitythewiki.com/Camouflaged_State.html",
    "snapshotDate": "2026-09-15",
    "heading": "Camouflaged State"
}
```

The checked-in `n5-core-v5.3.json` wiki `sources` record still identifies the
legacy unpacked mirror at `data/wiki/20260915/`. That provenance predates the
current timestamped-ZIP downloader and must not be rewritten to an exact
`WIKI ...zip` archive/hash unless a migration can establish which archive was
actually used.

### Design direction — wiki provenance migration

When the wiki downloader/packager and curated provenance contract are rewritten,
migrate wiki sources to exact recorded timestamped archive identity/hash and
make vocabulary provenance source-specific instead of requiring the current
mixed wiki/page locator. Generated acquisition provenance belongs under
`data/manifests/snapshots/`; curated rules will reference the source
identity they actually used rather than duplicating downloader state.

Version 1 curated-rule files are no longer accepted by the loader and must be
migrated to the v2 collection/source/citation structure before ingestion.

The starter file `rules/example.json` is intentionally empty and is never an
ingestion input. Directory ingestion skips that reserved filename. Validate all
rules collections with:

```powershell
infinity-db validate-curated data/curated/rules
```

To validate one collection directly, provide its path instead. Build the rules
database with:

```powershell
infinity-db build-rules
```

Curated rules files are source-controlled project data. Raw PDFs and wiki
snapshots remain ignored, local-only research material, and are never packaged
or served.
