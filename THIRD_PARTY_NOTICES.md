# Third-party notices

The MIT License in `LICENSE` applies to InfinityDB's original source code and
original project documentation. It does not automatically apply to third-party
materials that may be downloaded, generated, or included alongside the
application.

## Corvus Belli Infinity materials

InfinityDB can consume Army JSON snapshots and API metadata from the official
[Infinity Army API](https://api.corvusbelli.com/army), and can acquire graphical
assets from Corvus Belli asset hosts for local processing and browser use.
Those data records, names, marks, and artwork remain subject to the rights and
terms of their respective owners. InfinityDB does not relicense them under MIT.

Raw Army and symbol snapshots in `data/raw/`, generated databases in
`data/generated/`, and any locally acquired Corvus Belli-derived graphical
assets published under `src/infinity_db/web/static/` are replaceable data or
assets rather than original MIT-licensed project material. Corvus Belli
graphical assets are not included in InfinityDB source or redistributable
release artifacts by default. Public availability from an asset host is not
treated as permission to redistribute them; include such assets in a wheel,
Docker image, release, or other distributed artifact only when permission for
that distribution form has been established, while retaining any required
attribution.

## Infinity Wiki and rules documents

The optional wiki research material under `data/wiki/` and user-supplied rules
documents under `data/pdf/` are ignored by Git and are not part of the normal
application package or Docker build. Their text, images, and other contents must
not be redistributed as MIT-licensed project material.

Curated facts retain provenance appropriate to the source contract. PDF-derived
facts use document edition/version/date and printed-page citations. Current
wiki-derived record citations use snapshot-local path and snapshot date; legacy
wiki provenance should not be relabeled as an exact timestamped archive/hash
until that provenance is migrated by the downloader/packager and curated-data
work.

## Runtime and deployment dependencies

The optional Python server dependency, development tools, Python base image,
Caddy image, and operating-system packages retain their own licenses and notices.
They are not relicensed by InfinityDB's MIT License. A deployment or derivative
distribution that includes those components should preserve the notices required
by their respective licenses.
