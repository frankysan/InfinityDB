# Release process

This document is the canonical release checklist for InfinityDB. **Every release**
must pass this checklist unless a step is explicitly inapplicable to that release.
Version-specific release requirements belong in `docs/TODO.md`; they extend this
process rather than replacing it.

A release is not ready merely because its implementation checks pass. The release
gate includes repository state, documentation, release metadata, hosted validation,
and post-release verification.

## 1. Confirm release scope

- [ ] Confirm the target version and the intended release scope.
- [ ] Complete the release-specific requirements recorded in `docs/TODO.md`.
- [ ] Resolve known release-blocking defects. Explicitly defer non-blocking work to
  `docs/TODO.md` rather than leaving its status ambiguous.
- [ ] Confirm that any schema, compatibility, data-rebuild, deployment, or asset
  consequences are understood before preparing the release metadata.

## 2. Audit all project documentation

A **project-wide documentation audit is mandatory for every release**. Do not limit
this review to files changed since the previous release. The purpose is to catch
stale statements that survived earlier work or became inaccurate through cumulative
changes.

Review the complete maintained documentation corpus, including `README.md`, all
tracked Markdown under `docs/` and `data/`, `THIRD_PARTY_NOTICES.md`, and project
development guidance such as `AGENTS.md`. Use `git ls-files "*.md"` as the baseline
inventory rather than relying on memory.

During the audit:

- [ ] Verify that unqualified descriptions of current behavior match the repository.
  Planned or partially implemented behavior must be labelled as design direction or
  future work.
- [ ] Verify current version references, release dates, schema/compatibility revisions,
  supported source/version statements, commands, paths, filenames, workflow names,
  and deployment instructions. Historical values may remain when clearly identified
  as historical evidence.
- [ ] Review `docs/architecture.md` and `docs/data-model.md` against the implemented
  architectural and semantic boundaries, including any new InfinityDB-specific
  abstractions and their derivation/provenance rules.
- [ ] Review `docs/testing.md`, `docs/ci.md`, `docs/deployment.md`, and
  `docs/server-migration.md` against the actual validation and operational workflows.
- [ ] Review `docs/TODO.md`: remove completed standalone work after recording its
  durable outcome in the appropriate reference documentation or changelog, and make
  remaining work accurately describe what is still unimplemented.
- [ ] Review `docs/AI_CONTEXT.md` for durable, non-obvious invariants that changed
  during the release, without duplicating ordinary reference documentation.
- [ ] Check documentation links and references to renamed, removed, or superseded
  files and sections.
- [ ] Search deliberately for stale references to the previous release and previous
  schema/compatibility values. Inspect every match rather than replacing historical
  evidence mechanically.
- [ ] Resolve contradictory or duplicated descriptions by updating the canonical
  document and linking to it from secondary documentation where appropriate.

The audit is complete only when stale documentation discovered during the review has
been corrected in the release preparation, or is explicitly retained and labelled as
historical context.

## 3. Prepare release notes and metadata

- [ ] Review the complete `Unreleased` section of `docs/CHANGELOG.md` as one release:
  merge overlapping entries, remove implementation-only detail, and make upgrade
  consequences explicit.
- [ ] Move the finalized entries to a section for the target version and release date.
- [ ] Update the package/application version consistently in `pyproject.toml` and
  `src/infinity_army_data/__init__.py`.
- [ ] Update the current-release statement in `README.md`.
- [ ] Re-run the documentation audit checks affected by those release-metadata edits.

Do not change the released version early merely to mark work in progress; development
checkouts use the existing `+dev` display-version mechanism until release preparation.

## 4. Run release validation

- [ ] Run the complete local validation suite with `python tools/run_checks.py --all`.
- [ ] When the release is intended for a local/full-asset deployment, validate the
  complete published asset set with the `required` asset mode as documented in
  `docs/testing.md`.
- [ ] Run any additional release-specific acceptance, benchmark, migration, or
  reproducibility checks required by `docs/TODO.md` or the affected subsystem docs.
- [ ] Confirm the required hosted workflows are green for the exact release commit.
  `Source checks`, `Deployment smoke test`, and `Installed wheel smoke` provide the
  normal clean-source/package/deployment evidence; use `Full-asset checks` where the
  release scope requires that private asset-backed validation. See `docs/ci.md` for
  the authoritative workflow contract.
- [ ] Confirm the working tree contains only the intentional release-preparation
  changes before creating the release commit.

If any release-preparation edit is made after validation, rerun the affected checks;
rerun the full gate when the edit can affect executable, generated, packaged, or
deployment behavior.

## 5. Tag and publish

- [ ] Create the final release commit only after the checklist above is green.
- [ ] Create the version tag `v<version>` at that exact commit.
- [ ] Push the release commit and tag, then verify that the remote tag resolves to the
  intended commit.
- [ ] Retain the required hosted-workflow evidence for that release commit/tag.

A published release tag is immutable project history. Correct a material release
error with a subsequent release rather than silently moving a published tag.

## 6. Deployment and post-release verification

For releases that are deployed to the hosted InfinityDB instance:

- [ ] Deploy using the appropriate documented workflow in `docs/deployment.md`; do
  not mix server-rebuild and transferred-artifact deployment modes.
- [ ] Verify the deployed application reports the intended release version and source
  snapshot.
- [ ] Smoke-test the release's principal changed user-facing paths in the deployed
  application.
- [ ] Confirm required database/schema rebuilds and published assets are actually the
  release-matched versions.
- [ ] Confirm rollback remains available before considering deployment acceptance
  complete.

Record durable release outcomes in the changelog/reference documentation. Detailed
check logs and one-off acceptance evidence should remain in their normal reports, CI,
or Git history rather than turning `docs/TODO.md` into an archive of completed
release checklists.
