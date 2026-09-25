# Third-party notices

The MIT License in `LICENSE` applies to InfinityDB's original source code and
original project documentation. It does not automatically apply to third-party
materials that may be downloaded, generated, or included alongside the
application.

## Corvus Belli Infinity materials

All Infinity artwork, logos, symbols, and game data are the property of Corvus
Belli S.L. and are used with permission for this non-commercial community project.
InfinityDB does not relicense those materials under the MIT License.

On 2026-09-24, Corvus Belli S.L. explicitly granted InfinityDB permission to use
and redistribute the graphical assets requested for this non-commercial community
project: Infinity logos, unit/profile symbols, order icons, and characteristic
icons. The permission covers web hosting, deployment/build packages, public Git
repository inclusion, technical SVG processing such as text-to-path conversion,
compression and renaming, and future mobile applications, provided the original
artwork and meaning remain intact.

That permission is subject to these project-facing conditions:

- Corvus Belli ownership must be clearly attributed.
- The permitted graphical assets remain separate from InfinityDB's MIT-licensed
  original code and documentation.
- The project must remain strictly non-commercial and non-monetized.
- Technical processing may optimize the files but must not alter the original
  artwork or its meaning.

InfinityDB can consume Army JSON snapshots and API metadata from the official
[Infinity Army API](https://api.corvusbelli.com/army), and its symbol pipeline can
acquire source graphics from Corvus Belli asset hosts. The explicit redistribution
permission above applies to the requested graphical assets; it is not a blanket
grant to republish Infinity Army snapshot archives, wiki mirrors, rules PDFs, or
other source/reference collections. InfinityDB therefore keeps raw Army, wiki,
PDF, and source-symbol archives outside the public repository by project policy.

The processed graphical publication used by InfinityDB is tracked in the public
repository and may be included in wheels, Docker images, releases, deployment
packages, or other non-commercial InfinityDB distributions under that permission.
Generated databases, the local terminal symbol-build manifest, raw snapshots, and
other acquisition/provenance inputs remain replaceable local data rather than
original MIT-licensed project material.

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
