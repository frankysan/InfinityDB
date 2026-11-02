# Syncthing-staged development assets

**Project domain:** Project infrastructure

This page defines how a private Linux development worker accesses ignored
InfinityDB source material without synchronizing files into its Git checkout.
Source code, curated data, tracked databases, and branch selection remain Git
responsibilities. Syncthing never updates a checkout or triggers a test.

## Layout and synchronization

Windows is the authoritative **Send Only** Syncthing device; `linux-dev` is
**Receive Only**. Five independent folder IDs/paths are configured as follows:

| Windows repository subdirectory | Linux staging folder |
| --- | --- |
| `data/raw/` | `~/syncthing/infinitydb/raw/` |
| `data/wiki/` | `~/syncthing/infinitydb/wiki/` |
| `data/pdf/` | `~/syncthing/infinitydb/pdf/` |
| `data/manifests/snapshots/` | `~/syncthing/infinitydb/snapshots/` |
| `image_overrides/` | `~/syncthing/infinitydb/image_overrides/` (optional) |

The Syncthing folder IDs must match between the devices; their physical
paths need not. Do **not** synchronize the whole repository, the
`data/generated/` directory (contains tracked release databases),
`data/curated/`, `local/`, `data/work/`, `reports/`, environment
files, virtualenvs, or caches. The Linux source staging directory is outside
`~/InfinityDB`.

Syncthing propagates source deletions, even to a Receive Only folder. Configure
file versioning on the Linux receiving folders and retain backups of immutable
archives. Stop synchronization while repairing any unexpected divergence.
Syncthing service startup on Windows is an independent operational task; a
currently running Windows CLI instance is sufficient for synchronization.

## Explicit checkout activation

Run the commands below **on Linux**, with the InfinityDB repository as the
current directory, after synchronized inputs show Up to Date.

```bash
./.venv/bin/python -m tools.activate_synced_assets list
./.venv/bin/python -m tools.activate_synced_assets verify --snapshot 'JSON 20260929-114335'
./.venv/bin/python -m tools.activate_synced_assets activate --snapshot 'JSON 20260929-114335'
./.venv/bin/python -m tools.activate_synced_assets activate --snapshot 'JSON 20260929-114335' --apply
```

- `list` enumerates staged snapshot manifest names.
- `verify` compares each selected archive's SHA-256 against its staged
  snapshot manifest. Omit `--snapshot` to validate all staged manifests,
  which may require reading large archives.
- `activate --snapshot` verifies the archive, then plans both the archive
  and its matching provenance JSON in the checkout. **It is a dry run unless
  `--apply` is supplied.**
- Default activation uses **copy**, leaving a stable local input if later
  Syncthing updates or deletes a staging file. `--mode symlink` saves disk
  space, but the checkout then follows any future staging changes.
- An existing destination is reused only if it has identical bytes (or
  already matches the requested symlink); conflicting files are never
  overwritten. There is no bulk cleanup, delete or reverse synchronization.

PDFs and local graphical overrides have no mandatory archive manifest pin.
Activate an individual file explicitly; the command measures its SHA-256 but
cannot independently establish original provenance:

```bash
./.venv/bin/python -m tools.activate_synced_assets activate --file 'data/pdf/rules/n5-rules-v5-3-en.pdf'
./.venv/bin/python -m tools.activate_synced_assets activate --file 'data/pdf/rules/n5-rules-v5-3-en.pdf' --mode symlink --apply
```

Paths in `--file` must be relative to the repository and restricted to
`data/pdf/` and `image_overrides/`. Raw/wiki snapshot ZIPs must go
through `--snapshot` to ensure their hashes are verified first.
The tool refuses symlinks within the staging source and destination conflicts.
Existing tracked files are outside its permitted destination paths.

## MCP worker policy

The `linux-dev` MCP worker can execute the tracked module using an
asynchronous script job once its Git checkout contains that module. Run
`list`, `verify` or a dry-run activation first; execute `--apply`
only as a specifically requested worker task. The default staging directory
is based on the worker account's Linux home. No Git fetch, checkout,
commit, push or pull is performed by this utility; Git synchronization is
separately invoked and must never be an implicit side effect of activation.

A verified source archive alone does not prove the checkout is ready for a
particular test. The test's expected source revisions, curated records, and
tracked runtime databases still need to match the selected Git commit.
