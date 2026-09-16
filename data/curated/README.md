# Curated data

`data/curated/` contains source-controlled, human-reviewed information derived
from external sources. Curated material is distinct from generated provenance
under `data/manifests/` and from immutable external inputs under `data/raw/`,
`data/wiki/`, and `data/pdf/`.

Subdirectories have explicit ingestion semantics:

- `rules/` contains validated rules-reference collections and is the only
  curated subtree consumed by `infinity-db build-rules`.
- `snapshot-notes/` is reserved for human-maintained descriptions, comparison
  targets, and notable-change notes associated with immutable snapshots. These
  notes are not rules-database inputs and should identify their snapshot by
  SHA-256 so they remain unambiguous if an archive is moved or renamed.

The sections below document the current `curated/rules/` contract.

## Curated rules reference data

This directory is the handoff from local wiki snapshots and PDF documents to
rules-data ingestion. Developers and agents may read reference material in
`data/wiki/` and `data/pdf/`, then write concise, human-reviewed facts under
`data/curated/rules/`. The application and its build pipeline must never read
those raw reference trees directly.

### Available reference families

The local reference corpus may include:

- N5 core rules revisions under `data/pdf/rules/`.
- N5 FAQ revisions under `data/pdf/faq/`.
- ITS seasons under `data/pdf/its/` and `data/pdf/legacy/`.
- Timestamped wiki mirror archives under
  `data/wiki/WIKI YYYYMMDD-HHMMSS.zip`.

Core rules can provide curated skills, equipment, weapons, ammunition, traits,
states, attributes, timing, modifiers, deployment, hacking, fireteams, and
interactions. FAQ records should represent dated clarifications or rulings. ITS
records should remain season-scoped and can represent scenarios, objectives,
scoring, deployment, and mission constraints. Wiki pages are useful for
discovery, aliases, cross-links, and concise explanations, but do not override
the applicable official rules or Army data.

### Current v2 contract

Place one collection per subject or release under `data/curated/rules/`, for
example `rules/n5-core-v5.3.json`. Each file must contain:

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

PDF and wiki provenance are deliberately different. PDF citations require a
positive **printed** `page` number. Wiki citations instead require a
snapshot-local `path` and `snapshotDate`; wiki source records should also retain
the exact timestamped archive path and SHA-256 where available so same-day
snapshots remain distinguishable. Do not bulk-copy PDF or wiki text, images, or
page markup. Keep core rules, FAQs/errata, and ITS seasons in separate
collections so versions cannot be blended accidentally.

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

Army links may target existing `skills`, `equipment`, `weapons`, `ammunition`,
`extras`, `characteristics`, `troop_types`, `units`, or profile occurrences.
They annotate Army data; they do not establish list legality or replace
Army-derived statistics.

A wiki citation currently uses the snapshot date and a path within the selected
mirror, for example:

```json
{
    "sourceId": "wiki-20260915",
    "path": "infinitythewiki.com/Camouflaged_State.html",
    "snapshotDate": "2026-09-15",
    "heading": "Camouflaged State"
}
```

The corresponding wiki `sources` record should identify the exact
`WIKI YYYYMMDD-HHMMSS.zip` archive and its SHA-256 when known. The archive's
generated provenance belongs in `data/manifests/snapshots/`; this curated rules
record only references the source it used.

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

`build-rules` defaults to `data/curated/rules/`; other curated subtrees are not
part of rules ingestion.

Curated files are source-controlled project data. Raw PDFs and wiki snapshots
remain ignored, local-only research material, and are never packaged or served.
