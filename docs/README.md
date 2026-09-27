# Documentation layout

**Project domain:** Project infrastructure

InfinityDB separates maintained repository documentation from local audit evidence.
The distinction is intentional: an audit may produce large, environment-specific working
material, while only the conclusions that must survive a checkout belong in Git.

## Tracked documentation

Files tracked directly under `docs/` are maintained project records. They include:

- authoritative reference documentation such as `architecture.md`, `data-model.md`,
  `deployment.md`, and `testing.md`;
- planning and release records such as `TODO.md`, `CHANGELOG.md`, and `releasing.md`;
- durable release-specific audit or closeout records whose conclusions are useful after
  the original working evidence has been discarded; and
- maintained cross-release trackers such as `rules-interaction-checklist.md`.

Release audit records describe the accepted state at a particular milestone. They do not
override current authoritative reference documentation when the project later changes.
Release-specific audit records should identify their release in both the filename and title.
The current durable audit records are:

- `070-enrichment-presentation-audit.md`;
- `080-connected-domain-audit.md`;
- `080-web-consistency-closeout.md`; and
- `081-release-documentation-audit.md`.

## Local audit workspace

`docs/audits/` is intentionally ignored by Git. Use it for transient or local audit
evidence such as generated matrices, command output, comparison results, working notes,
and environment- or deployment-specific observations. The directory may be deleted and
regenerated without changing the repository.

Do not make builds, tests, CI, or maintained documentation depend on files under
`docs/audits/`. Do not store credentials, secrets, or other sensitive material there merely
because the directory is ignored.

When an audit closes, promote durable outcomes to the appropriate authoritative document.
If preserving the audit decision/history itself has continuing value, write a concise tracked
release-specific audit or closeout record under `docs/`. Raw evidence may remain local.

## Audit workflow

A normal audit therefore has three layers:

1. collect raw/local evidence under `docs/audits/`;
2. make and validate corrections in code, data, or maintained documentation; and
3. retain only durable conclusions in authoritative docs and, when useful, a tracked
   release-specific audit/closeout record.

This keeps the repository useful as long-lived documentation without turning it into an
archive of every intermediate audit artifact.
