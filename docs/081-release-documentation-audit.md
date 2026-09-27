# 0.8.1 release documentation audit

**Project domain:** Project infrastructure

This is the durable documentation closeout for the 0.8.1 maintenance release. Raw command
output, comparison notes, and other transient evidence belong under the gitignored
`docs/audits/` workspace; this record keeps only conclusions that remain useful after release.

The audit follows the project-wide release requirement in `docs/releasing.md`. It reviewed the
maintained repository documentation against the post-0.8.0 implementation rather than only
checking files changed during 0.8.1.

## Scope reviewed

The pass covered:

- `README.md`, `THIRD_PARTY_NOTICES.md`, `AGENTS.md`, and the documentation-layout policy;
- all tracked Markdown under `docs/` and the maintained Markdown contracts under `data/`;
- deployment, server migration, CI, testing, release, and generated-artifact workflows;
- current Army/rules database schema and compatibility revisions;
- snapshot-provenance v3 and its version-1/version-2 compatibility contract;
- the tracked runtime-database and symbol-publication deployment boundary;
- browser-font storage, licensing, packaging, and semantic typography roles; and
- Hacking Program declaration-category semantics and the Skill-style presentation contract.

Historical release notes and prior release-specific audit records were retained when they were
clearly labelled as historical evidence.

## Confirmed current contracts

### Release deployment

A tagged checkout is self-contained for runtime deployment. The release owns the exact
`data/generated/infinity.db`, `data/generated/rules.db`, processed SVG publication, and
`data/manifests/symbol-publication.json` that production uses. Raw acquisition archives and the
terminal `army-symbol-build.json` remain local development/provenance inputs. Deployment verifies
that the tracked Army database and symbol publication name the same exact Army source archive
SHA-256 before an image can activate.

The application database remains schema 25 / compatibility revision 33. The rules database
remains schema 7 / compatibility revision 8. No database rebuild is required solely for the
0.8.1 code/UI changes reviewed by this audit.

### Snapshot freshness

New acquisition manifests use `InfinityDB snapshot provenance` format version 3. Army snapshots
record `source.dataChangedOn`, derived from the latest supported date encoded in the contained
Army source-version strings. Version-1 and version-2 manifests remain readable. Player-facing
freshness uses the Army-data change date; the later InfinityDB acquisition timestamp remains
Developer-mode provenance.

### Browser typography

The browser owns a tracked, redistributable WOFF2 publication under
`src/infinity_db/web/static/fonts/`. Audiowide is the brand face, Oxanium the display face,
IBM Plex Sans the normal body/UI face, IBM Plex Sans Condensed the compact/table face, and
IBM Plex Mono the diagnostic/identifier face. The font files remain under their upstream SIL
Open Font License terms and are not relicensed under InfinityDB's MIT License. Upstream TTF
collections are regeneration inputs rather than runtime/repository publication content.

The size system has one browser-relative root and rem-based canonical tiers. Fluid display sizes
may use viewport interpolation inside `clamp()`, but components consume semantic size/family
tokens rather than defining local font systems.

### Hacking Programs

Hacking Programs preserve Army's exact profile fields and raw declaration strings in source
storage, including the legacy `entire order` value. The composed application contract maps those
values onto the same canonical declaration-category identities used by Skills, so current
presentation uses **Long Skill**, **Short Skill**, and **ARO**. Program profile data and curated
rules meaning are presented as one Skill-style detail card rather than competing profile/rules
surfaces.

## Corrections made by this audit

The audit corrected four documentation inconsistencies:

- the README's server-migration description still referred generically to transfer/rebuild
  requirements even though released-server migration now consumes tracked release artifacts;
- the server-migration guide's warning about redistributing symbol-processing system fonts was
  ambiguous after InfinityDB intentionally began redistributing OFL-licensed browser fonts;
- `data/README.md` described the processed-SVG redistribution permission but did not state the
  equivalent tracked-runtime-database release boundary explicitly; and
- the 0.8.1 changelog lacked upgrade notes explaining that the new tracked database model does
  not itself require rebuilding databases and that older snapshot manifests remain supported.

The legacy symbol-publication provenance helper remains documented as a one-time migration for
pre-contract publications rather than as an ongoing production dependency.

## Audit checks

Relative Markdown links across the maintained documentation corpus resolve to existing repository
paths. Searches for the retired transferred-artifact deployment workflow found only historical
changelog material. Active deployment/reference documentation consistently treats
`army-symbol-build.json` as local processing provenance rather than a production input.

References to 0.8.0 were retained where they identify the released connected-data milestone or
historical audit/release evidence. The current package version and README current-release line
remain 0.8.0 intentionally until the release-metadata step described by `docs/releasing.md`.

The release-artifact verifier also passed against the audited work state: both runtime databases
were valid and snapshot-matched, with 806/806 published SVGs and 806/806 browser-referenced SVGs
verified against the tracked publication manifest.

## Remaining release preparation

This audit closes the documentation-correctness pass, not the release itself. Before tagging
0.8.1, finalize `Unreleased` into the dated 0.8.1 changelog section, update the package/application
version and README current-release line together, rerun documentation checks affected by those
metadata edits, and then execute the complete local and hosted release validation defined by
`docs/releasing.md`.
