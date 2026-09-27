# Browser fonts

This directory is the canonical browser-font publication for InfinityDB.

The WOFF2 files are generated from upstream Google Fonts TTF downloads with
`tools/prepare_web_fonts.py`. Source TTFs may be staged in these family directories for
regeneration, but they are gitignored and excluded from wheels/runtime packages. An unpacked
Google Fonts download containing the expected family directories may also be supplied from
any external directory. The helper requires the project's `symbols` optional dependencies.

Runtime roles:

- Audiowide: InfinityDB wordmark/brand text.
- Oxanium: display headings and titles.
- IBM Plex Sans: running text and normal controls.
- IBM Plex Sans Condensed: dense tables and compact structured data.
- IBM Plex Mono: identifiers and developer/diagnostic text.

Each family remains licensed under the SIL Open Font License 1.1. The corresponding
`OFL.txt` is stored beside its published font files and the copyright holders are also
listed in the repository-level `THIRD_PARTY_NOTICES.md`.
