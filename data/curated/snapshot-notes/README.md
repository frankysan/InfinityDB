# Snapshot notes

`data/curated/snapshot-notes/` is the source-controlled home for human-reviewed
annotations about immutable acquisition snapshots. These files are deliberately
separate from downloader-generated provenance under `data/manifests/snapshots/`.
Acquisition tooling must never create, rewrite, or delete snapshot-note files.

Snapshot notes use the versioned `InfinityDB snapshot note` format. Version 1 is
bound to the immutable snapshot by its lowercase SHA-256 digest:

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

- `snapshotSha256` is required and is the authoritative snapshot identity.
- `description` is required human-authored context.
- `compareToSha256` is optional and must identify a different snapshot.
- `notableChanges` is required and may be an empty array when no reviewed
  changes have been recorded.

The archive filename is intentionally not part of the note contract. Generated
snapshot manifests retain the current archive name/path label, while the hash
keeps notes stable if an archive is moved or renamed. Snapshot notes are not
rules-database inputs and are not currently consumed by the application runtime.
