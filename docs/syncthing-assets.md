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
| `image_overrides/` | `~/syncthing/infinitydb/image-overrides/` (optional) |

**L2 path-cutover boundary:** The
[reader/producer decision package](tooling-and-local-path-cleanup-plan.md#eighteenth-bounded-l2-checkpoint--readerproducer-path-cutover-decision-package-2026-11-13)
proposes `local/data/` source destinations but does **not** migrate
them. The activation tool now supports explicit `--layout local`
verification and preview alongside the default `legacy` layout, as
described below. This reader capability does not change the five current
folders, their IDs, sender roots, receiver permissions or backup policy.
Physical source/Syncthing cutover still needs its own family-specific approval.

The Syncthing folder IDs must match between the devices; their physical
paths need not. The optional Linux receiver uses `image-overrides/` (hyphen),
while the repository destination remains `image_overrides/` (underscore). The
explicit activation tool maps between them; do not rename either to match
its counterpart. Do **not** synchronize the whole repository, the
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
- `verify` validates each selected manifest with the shared provenance
  validator, including exact archive SHA-256 and logical-content SHA-256
  where its version provides one. Supported historical v1/v2 and current v3
  provenance remain readable. Omit `--snapshot` to validate all staged manifests,
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

### Explicit snapshot layouts

[The maintained layout policy](../config/operations/synced-asset-layouts.json)
defines version-1 `legacy` and `local` mappings. Every command accepts
`--layout`; omitting it always selects `legacy`. No environment variable,
embedded producer path or newest-file search selects a different layout.
`INFINITYDB_SYNC_STAGING_ROOT` still selects only the external staging root.
The policy is validated before reading selected inputs or creating destinations;
unknown fields/versions, duplicate JSON keys, unsafe paths and routes outside
their permitted source/destination families are rejected without fallback.

| Snapshot family | Staged source in `local` mode | `local` checkout destination |
| --- | --- | --- |
| Army | `raw/<original basename>.zip` | `local/data/raw/army/<original basename>.zip` |
| Wiki / Human Sphere | `wiki/<original basename>.zip` | `local/data/wiki/<original basename>.zip` |
| Raw symbols | `raw/symbols/<original basename>.zip` | `local/data/raw/symbols/<original basename>.zip` |
| Matching provenance | `snapshots/<original stem>.json` | `local/data/manifests/snapshots/<original stem>.json` |

The `legacy` layout continues to translate the manifest's `data/raw/` or
`data/wiki/` label into the corresponding staged folder, preserving nested
relative paths such as `raw/symbols/`. It rejects a new-layout path instead of
silently switching layouts. The explicitly selected `local` mode selects one
configured family directory plus the original archive basename. Its optional
producer-relative `archive.path` is validated as portable text but is not
followed, even if it names another existing file. Old, new or absent producer
path labels therefore work without modifying provenance. Alternate staged
locations need a reviewed policy change; the tool does not search siblings.
Derived symbol archives are not implicitly selected from other processing roots.

Preview a selected pair on Linux without changing the checkout:

```bash
./.venv/bin/python -m tools.activate_synced_assets verify --layout local --snapshot 'JSON 20260929-114335'
./.venv/bin/python -m tools.activate_synced_assets activate --layout local --snapshot 'JSON 20260929-114335'
```

The R3 snapshot and R4 individual-file mappings permit `--layout local`
**only as a selected, non-destructive capability**. Real source migration
remains unapproved. Use `--apply` with the local layout only in disposable
test checkouts until an independently reviewed source-family copy decision.
None of these commands changes the five Syncthing staging folders.

Snapshot and manifest basenames must agree. Duplicate selections, case-colliding
manifest names and non-lowercase `.json` suffixes fail closed. Full-pair
preflight checks destination conflicts before any activation writes; source
hashes and symlink guards are checked again before each file is activated.
Copy publication never replaces a destination. A late I/O error or source
change may leave an earlier **newly activated file** from that explicit apply:
the pair is not a multi-file transaction. Inspect and retry the same verified
selection; prior conflicting bytes are never overwritten or deleted.

### Individual PDFs and overrides

PDFs and optional override evidence have no mandatory snapshot manifest pin.
The external symbol producer owns override lookup/application; activating these
files does **not** approve new artwork or make it an InfinityDB build input.
The command measures a SHA-256 of its selected staged file but cannot establish
original provenance. These are the two **explicit** file layouts:

| Selection | Staged source | Checkout destination |
| --- | --- | --- |
| Default `--layout legacy` | `pdf/<relative>.pdf` | `data/pdf/<relative>.pdf` |
| Default `--layout legacy` | `image-overrides/<relative>.svg` | `image_overrides/<relative>.svg` |
| Explicit `--layout local` | `pdf/<relative>.pdf` | `local/data/pdf/<relative>.pdf` |
| Explicit `--layout local` | `image-overrides/<relative>.svg` | `local/data/symbols/overrides/<relative>.svg` |

```bash
./.venv/bin/python -m tools.activate_synced_assets activate --file 'data/pdf/rules/n5-rules-v5.3-en.pdf'
./.venv/bin/python -m tools.activate_synced_assets activate --layout local --file 'local/data/pdf/rules/n5-rules-v5.3-en.pdf'
./.venv/bin/python -m tools.activate_synced_assets activate --layout local --file 'local/data/symbols/overrides/Unit/example.svg'
```

These commands are previews. In the local layout, `--apply` remains restricted
to disposable test checkouts until a family-specific M-copy approval. Both
layouts reject a path belonging to the other layout and never search an
alternate checkout/staging root. Nested relative basenames are preserved;
receiver `image-overrides` (hyphen) is **not** renamed. Raw/wiki snapshot ZIPs
must use `--snapshot` and its independent provenance verification. The tool
refuses staged symlinks and differing existing destination bytes, and cannot
replace a tracked published artifact. Independently hash-check selected PDFs
against the reviewed source pins **before any research or publication use**;
read-only activation does not make unpinned staged bytes authoritative.

## MCP worker policy

The `linux-dev` MCP worker runs as `mcpworker`, whereas Syncthing runs as
`infinitydb` and stores the synchronized files under
`/home/infinitydb/syncthing/infinitydb/`. Keep the five Syncthing folders
owned by `infinitydb`, and grant `mcpworker` **read-only** POSIX ACL access
instead of moving files into its home or making either Git checkout shared.
On `devbox` (install the `acl` package first if `setfacl` is unavailable):

```bash
sudo setfacl -m u:mcpworker:--x /home/infinitydb /home/infinitydb/syncthing
sudo setfacl -R -m u:mcpworker:r-X /home/infinitydb/syncthing/infinitydb
sudo find /home/infinitydb/syncthing/infinitydb -type d -exec setfacl -m d:u:mcpworker:r-x {} +
sudo -u mcpworker test -r /home/infinitydb/syncthing/infinitydb/snapshots && echo 'MCP staging: readable'
```

The parent ACLs permit traversal, not browsing the `infinitydb` home.
Recursive access covers existing files; default ACLs on the staging folders
and descendants cover files added by Syncthing later. If Syncthing applies
restrictive source permission bits to new files, recheck effective ACL masks
with `getfacl` and repeat the access test after synchronization. Do not give
the worker write permission to the receive-only staging source.

The activation tool uses `~/syncthing/infinitydb` by default. Configure the
worker's **actual** staging root via a systemd drop-in, avoiding changes to
`HOME` and avoiding symlinks (which the activation safety check rejects):

```bash
sudo install -d -m 755 /etc/systemd/system/mcp-worker.service.d
printf '%s\n' '[Service]' 'Environment=INFINITYDB_SYNC_STAGING_ROOT=/home/infinitydb/syncthing/infinitydb' | sudo tee /etc/systemd/system/mcp-worker.service.d/syncthing-staging.conf >/dev/null
sudo systemctl daemon-reload && sudo systemctl restart mcp-worker.service
```

Restart only when no MCP job is running. After the worker checkout contains
the updated activation tool, run its asynchronous `list` action first, then
`verify` or dry-run `activate` for explicitly selected inputs. The utility
never performs Git operations and never applies activation writes without
`--apply`; any such write requires a specifically requested worker task.
Git synchronization is separately invoked and must never be an implicit side
effect of asset activation.

A verified source archive alone does not prove the checkout is ready for a
particular test. The test's expected source revisions, curated records, and
tracked runtime databases still need to match the selected Git commit.
