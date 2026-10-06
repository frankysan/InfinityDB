# Snapshot notes

**Project domain:** Data processing

`data/curated/snapshot-notes/` is the source-controlled home for human-reviewed
annotations about immutable acquisition snapshots. These files are deliberately
separate from downloader-generated provenance under `data/manifests/snapshots/`.
Acquisition tooling must never create, rewrite, or delete snapshot-note files.

Snapshot notes use the versioned `InfinityDB snapshot note` format. Maintained note files use the
`.json` extension; `README.md` is the only non-JSON file allowed in this directory. Routine project
tests recursively discover and validate every JSON note and reject unsupported stray files. Version 1
is bound to the exact immutable archive bytes by the lowercase SHA-256 stored as
`snapshot.archive.sha256` in generated provenance. It deliberately predates and does
not use the version-2 logical `snapshot.contentSha256` identity:

```json
{
  "format": "InfinityDB snapshot note",
  "formatVersion": 1,
  "snapshotSha256": "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
  "description": "Human-reviewed description of this snapshot.",
  "compareToSha256": "abcdef0123456789abcdef0123456789abcdef0123456789abcdef0123456789",
  "notableChanges": [
    "Describe one notable difference from the comparison snapshot.",
    "Keep entries concise and ordered by importance."
  ]
}
```

Fields:

- `snapshotSha256` is required and identifies the exact archive byte stream.
- `description` is required human-authored context.
- `compareToSha256` is optional and must identify a different snapshot.
- `notableChanges` is required and may be an empty array when no reviewed
  changes have been recorded.

The archive filename is intentionally not part of the note contract. Generated
snapshot manifests retain the current archive name/path label, while the exact
archive hash keeps notes stable if that same file is moved or renamed. Repacked
archives with identical logical contents can have a different archive SHA-256 and
therefore require a distinct version-1 note identity even when their version-2
`contentSha256` is the same. Snapshot notes are not rules-database inputs and are
not currently consumed by the application runtime.
