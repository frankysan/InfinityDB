# Third-party notices

The MIT License in `LICENSE` applies to InfinityDB's original source code and
original project documentation. It does not automatically apply to third-party
materials that may be downloaded, generated, or included alongside the
application.

## Corvus Belli Infinity materials

InfinityDB can consume Army JSON snapshots and API metadata from the official
[Infinity Army API](https://api.corvusbelli.com/army), and can download unit
symbols from `assets.corvusbelli.net`. Those data records, names, marks, and
artwork remain subject to the rights and terms of their respective owners.
InfinityDB does not relicense them under MIT.

Raw snapshots in `data/raw/`, generated databases in `data/generated/`, and
downloaded symbols under `src/infinity_db/web/static/` are replaceable data or
assets rather than original MIT-licensed project material. Before redistributing
a wheel, Docker image, database snapshot, or bundled symbols, verify that the
source terms permit that use and retain any required attribution.

## Infinity Wiki and rules documents

The optional wiki mirror under `data/wiki/` and user-supplied rules documents
under `data/pdf/` are research material. They are ignored by Git and are not
part of the normal application package or Docker build. Their text, images, and
other contents must not be redistributed as MIT-licensed project material.
Curated facts derived from rules documents must retain their source edition and
printed-page citation.

## Runtime and deployment dependencies

The optional Python server dependency, development tools, Python base image,
Caddy image, and operating-system packages retain their own licenses and notices.
They are not relicensed by InfinityDB's MIT License. A deployment or derivative
distribution that includes those components should preserve the notices required
by their respective licenses.
