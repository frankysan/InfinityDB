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
The generated runtime databases `data/generated/infinity.db` and `rules.db` are tracked
and may be redistributed as part of the non-commercial InfinityDB application/release. They
contain or derive from Corvus Belli game data and are not relicensed under InfinityDB's MIT
License. The local terminal symbol-build manifest, raw snapshots, wiki/PDF/source-symbol
archives, and other acquisition/provenance inputs remain ignored local build/research state.

## Infinity Wiki and rules documents

The optional wiki research material under `data/wiki/` and user-supplied rules
documents under `data/pdf/` are ignored by Git and are not part of the normal
application package or Docker build. Their text, images, and other contents must
not be redistributed as MIT-licensed project material.

Curated facts retain provenance appropriate to the source contract. PDF-derived
facts use document edition/version/date and printed-page citations. Archived
wiki-derived records bind to an exact timestamped ZIP/hash and cite snapshot-local
members. Exact pinned `oldid=` revisions remain URL-backed when they are not
members of that archive; they must not be relabeled as archived snapshot members.

## Browser fonts

InfinityDB redistributes a small browser-font publication under
`src/infinity_db/web/static/fonts/`. The published WOFF2 files are generated from
Google Fonts TTF distributions and retain their upstream SIL Open Font License 1.1
terms. They are not relicensed under InfinityDB's MIT License. The complete OFL text
for each family is stored beside the corresponding published font files.

The bundled families are:

- **Audiowide** — Copyright (c) 2012, Brian J. Bonislawsky DBA Astigmatic (AOETI),
  with Reserved Font Names "Audiowide".
- **Oxanium** — Copyright 2019 The Oxanium Project Authors.
- **IBM Plex Sans**, **IBM Plex Sans Condensed**, and **IBM Plex Mono** —
  Copyright © 2017 IBM Corp., with Reserved Font Name "Plex".

`tools/prepare_web_fonts.py` performs only deterministic format conversion and
selection of the browser faces; it does not change the font designs. Upstream TTF
download collections are build inputs rather than repository/runtime assets.

## Runtime and deployment dependencies

The optional Python server dependency, development tools, Python base image,
Caddy image, and operating-system packages retain their own licenses and notices.
They are not relicensed by InfinityDB's MIT License. A deployment or derivative
distribution that includes those components should preserve the notices required
by their respective licenses.
