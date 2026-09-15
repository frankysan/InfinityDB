# Curated reference data

This directory is the only handoff from the local wiki mirror and PDF
documents to project data ingestion. Developers and agents may read the
reference material in `data/wiki/` and `data/pdf/`, then write concise,
human-reviewed facts here as JSON. The application and its build pipeline must
never read those raw reference trees directly.

## Available reference families

The local reference corpus currently includes:

- N5 core rules v5.1, v5.2, and v5.3 in `data/pdf/rules/`.
- N5 FAQ v0.0 and v0.1 in `data/pdf/faq/`.
- ITS Seasons 6 through 18 in `data/pdf/its/` and `data/pdf/legacy/`.
- A 20260915 wiki snapshot containing 589 HTML pages, preserved originals,
  and downloaded assets in `data/wiki/20260915/`.

Core rules can provide curated skills, equipment, weapons, ammunition, traits,
states, attributes, timing, modifiers, deployment, hacking, fireteams, and
interactions. FAQ records should represent dated clarifications or rulings.
ITS records should remain season-scoped and can represent scenarios,
objectives, scoring, deployment, and mission constraints. Wiki pages are
useful for discovery, aliases, cross-links, and concise explanations, but do
not override the applicable official rules or Army data.

## Current v2 contract

Place one collection per subject or release under `data/curated/`, for example
`rules/n5-core-v5.3.json`. Each file must have:

- `format`: `InfinityDB curated reference`
- `formatVersion`: `2`
- `collection`: `id`, `title`, `domain`, `status`, `effectiveFrom`, and
    `authority`
- `sources`: PDF or wiki source records with version, authority, path, and
    source-specific publication metadata
- `records`: concise original summaries with typed `kind`, `id`, `name`,
    `summary`, optional facts/links, and one or more `citations`

Every source reference currently uses `sourceId` and the **printed** `page`
number. Add `locator` or other structured fields when useful, but do not
bulk-copy PDF or wiki text, images, or page markup. Keep core rules,
FAQs/errata, and ITS seasons in separate collections so versions cannot be
blended accidentally.

## Document shape

The current top-level `format`, `formatVersion`, `collection`, `sources`, and
`records` fields are structured as follows:

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

Supported record kinds should include `rule`, `skill`, `equipment`, `weapon`,
`ammunition`, `trait`, `state`, `glossary`, `interaction`, `fireteam`,
`faq-ruling`, `erratum`, `scenario`, `objective`, `mission`, `deployment`,
and `unit-annotation`.

Army links may target existing `skills`, `equipment`, `weapons`,
`ammunition`, `extras`, `characteristics`, `troop_types`, `units`, or profile
occurrences. They annotate Army data; they do not establish list legality or
replace Army-derived statistics.

PDF citations require a positive printed `page`. Wiki citations should instead
use a local path, snapshot date, and optional heading or anchor, for example:

```json
{
    "sourceId": "wiki-20260915",
    "path": "infinitythewiki.com/Camouflaged_State.html",
    "snapshotDate": "2026-09-15",
    "heading": "Camouflaged State"
}
```

Version 1 files are no longer accepted by the loader and must be migrated to
this collection/source/citation structure before ingestion.

The starter file `rules/example.json` is intentionally empty and is never an
ingestion input. Directory ingestion skips that reserved filename. Validate all
real collections with:

```powershell
infinity-db validate-curated data/curated
```

To validate one collection directly, provide its path instead.

Curated files are source-controlled project data. Raw PDFs and wiki snapshots
remain ignored, local-only research material, and are never packaged or served.