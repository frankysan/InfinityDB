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
./.venv/bin/python -m tools.activate_synced_assets activate --file 'data/pdf/rules/n5-rules-v5.3-en.pdf'
./.venv/bin/python -m tools.activate_synced_assets activate --file 'data/pdf/rules/n5-rules-v5.3-en.pdf' --mode symlink --apply
```

Paths in `--file` must be relative to the repository and restricted to
`data/pdf/` and `image_overrides/`. Raw/wiki snapshot ZIPs must go
through `--snapshot` to ensure their hashes are verified first.
The tool refuses symlinks within the staging source and destination conflicts.
Existing tracked files are outside its permitted destination paths.

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
