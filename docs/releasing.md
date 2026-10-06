# Release process

**Project domain:** Project infrastructure

This document is the canonical release checklist for InfinityDB. **Every release**
must pass this checklist unless a step is explicitly inapplicable to that release.
Active version-specific implementation/release blockers belong in `docs/TODO.md`;
they extend this process rather than replacing it. Long-lived acceptance definitions,
such as the version-1.0 completeness gate below, remain in this document.

A release is not ready merely because its implementation checks pass. The release
gate includes repository state, documentation, release metadata, hosted validation,
and post-release verification.

## Version 1.0 data-completeness gate

Version 1.0 represents the point where InfinityDB is **data-complete for normal
Infinity gameplay**. Every player-relevant data point available from the supported
Infinity sources that can reasonably be useful to a player must be represented in a
maintained structured layer and accessible through the web application in a usable
form. A specialized or final-form UI is not required when a basic presentation makes
the information understandable and navigable.

The current core-rules scenarios are part of the 1.0 requirement: they must have a
maintained structured representation and a usable browsable presentation. The planned model is
defined by the completed comparative review of the core scenarios and ITS Seasons 17 and 18 in
`docs/architecture.md` and `docs/data-model.md`, so the 1.0 implementation must preserve that
extensibility rather than introducing a simpler core-only representation. ITS-specific missions,
season material, tournament/event tooling, and a complete historical ITS library remain outside the
1.0 requirement unless they are necessary to interpret otherwise in-scope data. Scenario-specific
Skills, Equipment, States, Traits, contextual roles, objective elements, or other named rules
concepts remain in scope when needed by the core scenarios or the general catalog/reference
experience; preserve their scenario/season scope. Final visual polish, every planned
search/filter/comparison feature, exhaustive performance work, optional themes, deployment
conveniences, and unrelated architectural refactors likewise do not block 1.0.

The 1.0 release gate requires:

- [ ] Inventory player-relevant information from Infinity Army, supported official
  rules PDFs, and the Infinity Wiki, and identify any in-scope information not yet
  represented by InfinityDB.
- [ ] Represent every identified in-scope data point in the database or another
  explicitly defined maintained structured layer, including the relationships needed
  to understand it without relying on undocumented source-ID conventions.
- [ ] Provide a usable web presentation for every represented in-scope data category;
  important information must not be available only through raw JSON, developer tools,
  database inspection, or undocumented routes.
- [ ] Cover, where applicable, armies/sectorials/grouping identities, units and
  canonical identities, profiles and variants, availability, attributes/statistics,
  weapons/ammunition, skills, equipment, hacking data, deployables/peripherals/
  companions, Fireteams, maintained exceptions, other structured Army gameplay data,
  and the rules information needed to interpret those concepts.
- [ ] Import or curate useful explanatory rules knowledge for every referenced skill,
  equipment item, weapon trait, state, terminology entry, or other gameplay concept,
  using concise player-oriented summaries where direct reproduction is inappropriate.
- [ ] Preserve rules/source provenance so users can identify the official material
  behind summaries or interpretations; distinguish InfinityDB summaries and
  abstractions from verbatim/source-native facts.
- [ ] Resolve duplicate, renamed, superseded, or differently structured rules concepts
  into a coherent maintained representation with sufficient relationships to surface
  relevant rules alongside the entities that use them.
- [ ] Represent empty, unavailable, and not-applicable values deliberately rather than
  silently omitting them where that could mislead users.
- [ ] Complete a consistency audit across source snapshots, normalized databases,
  canonical application data, APIs, and browser presentation. Known source quirks,
  corrections, derivations, and material cross-source discrepancies must be explicit,
  reproducible, and traceable.
- [ ] Resolve any known defect that materially misrepresents a player's unit, profile,
  weapon, skill, equipment, army relationship, or rule information.

Immediately before 1.0, perform a final source-by-source completeness audit. Record
where each discovered player-relevant information type is represented, verify every
in-scope type has a usable web presentation and required rules context, review every
deliberate omission, and confirm that no remaining backlog item represents missing
player-relevant information required by this definition.

## 1. Confirm release scope

- [ ] Confirm the target version and the intended release scope.
- [ ] Complete the release-specific requirements recorded in `docs/TODO.md`.
- [ ] For releases with a maintained rules-interaction review target, run the interaction
  audit with both `--check-output docs/rules-interaction-checklist.md` and
  `--require-release <version>`, then resolve every pending entity for that release. Deferred
  candidates explicitly targeting later releases remain tracked and do not block the current
  release.
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
- [ ] Verify new or materially revised change/feature/design/backlog documentation uses
  the canonical project-domain labels from `docs/project-domains.md`, including
  multi-domain labels only where responsibility genuinely crosses a boundary.
- [ ] Review `docs/testing.md`, `docs/ci.md`, `docs/deployment.md`, and
  `docs/server-migration.md` against the actual validation and operational workflows.
- [ ] Review `docs/TODO.md`: remove completed standalone work after recording its
  durable outcome in the appropriate reference documentation or changelog, and make
  remaining work accurately describe what is still unimplemented.
- [ ] Review `docs/AI_CONTEXT.md` for durable, non-obvious invariants that changed
  during the release, without duplicating ordinary reference documentation.
- [ ] Audit normal player-visible browser copy against `docs/web-design-guidelines.md`: titles,
  introductions, navigation, controls, badges, and empty/error/loading states should use player/game
  language rather than implementation or maintainer-workflow vocabulary, and data-review-only
  surfaces should not be discoverable through the normal player journey.
- [ ] Check documentation links and references to renamed, removed, or superseded
  files and sections.
- [ ] Search deliberately for stale references to the previous release and previous
  schema/compatibility values. Inspect every match rather than replacing historical
  evidence mechanically.
- [ ] Resolve contradictory or duplicated descriptions by updating the canonical
  document and linking to it from secondary documentation where appropriate.

The audit is complete only when stale documentation discovered during the review has
been corrected in the release preparation, or is explicitly retained and labelled as
historical context. Raw evidence belongs under `docs/audits/`. Do not create a permanent
release-specific audit document by default: promote lasting conclusions into the canonical
document owner, record release outcomes in `CHANGELOG.md`, and let Git history preserve the
review narrative. Keep a tracked audit/closeout file only when it contains unique rationale that
will actively guide later work.

## 3. Prepare release notes and metadata

- [ ] Review the complete `Unreleased` section of `docs/CHANGELOG.md` as one release:
  make its `Player summary` concise and player-visible only, merge overlapping detailed entries,
  remove implementation-only detail, and make upgrade consequences explicit.
- [ ] Move the finalized entries to a section for the target version and release date.
- [ ] Update the package/application version consistently in `pyproject.toml` and
  `src/infinity_army_data/__init__.py`.
- [ ] Update the current-release statement in `README.md`.
- [ ] Re-run the documentation audit checks affected by those release-metadata edits.

Do not change the released version early merely to mark work in progress; development
checkouts use the existing `+dev` display-version mechanism until release preparation.

## 4. Run local release validation

- [ ] Rebuild and validate any release runtime database whose source/curated inputs changed,
  then ensure `data/generated/infinity.db` and `data/generated/rules.db` are the intended
  tracked release artifacts.
- [ ] Run `python tools/verify_deployment_assets.py` and require the tracked Army database,
  rules database, processed SVG publication, and publication snapshot provenance to pass as one
  release set.
- [ ] Run the complete local validation suite with `python tools/run_checks.py --all`.
- [ ] When the release is intended for a local/full-asset deployment, validate the
  complete published asset set with the `required` asset mode as documented in
  `docs/testing.md`.
- [ ] Run any additional release-specific acceptance, benchmark, migration, or
  reproducibility checks required by `docs/TODO.md` or the affected subsystem docs.
- [ ] Confirm the working tree contains only the intentional release-preparation
  changes before creating the release commit.

If any release-preparation edit is made after validation, rerun the affected checks;
rerun the full gate when the edit can affect executable, generated, packaged, or
deployment behavior.

## 5. Land the release commit, verify hosted CI, and tag

- [ ] After the local release checklist is green, create the release-preparation commit and land
  it on protected `main` through the normal pull-request workflow. The resulting `main` revision is
  the candidate release commit; if the repository uses a merge or squash commit, use that resulting
  commit rather than assuming the branch-head SHA is the release SHA.
- [ ] Confirm the required hosted workflows are green for that exact candidate release commit,
  including the `Source checks` cross-platform deterministic-output comparison. `Source checks`,
  `Deployment smoke test`, and `Installed wheel smoke` provide the normal
  clean-source/package/deployment evidence. Source checks validate the tracked processed SVG
  publication with required asset coverage; use `Full-asset checks` when release evidence should
  also cover the configured checksum-pinned external bundle. See `docs/ci.md` for the authoritative
  workflow contract.
- [ ] If a hosted failure requires any code, data, generated-artifact, or documentation change, land
  a new candidate release commit and repeat the affected local and hosted validation. Do not tag the
  superseded candidate.
- [ ] For the exact hosted-green candidate SHA, prepare the retained workflow evidence and annotated
  tag message. The outputs belong under ignored `reports/`; do not commit them back into the release
  candidate:

  ```text
  python tools/prepare_release_ci_evidence.py --repository OWNER/REPO --commit <release-sha> --tag v<version> --json-output reports/release-ci-v<version>.json --tag-message-output reports/release-tag-v<version>.txt
  ```

  The command must verify successful `Source checks`, `Installed wheel smoke`, and
  `Deployment smoke test` runs for that exact SHA. Add `--include-full-assets` when this release's
  retained evidence should also require the optional checksum-pinned `Full-asset checks` workflow.
  Set `GITHUB_TOKEN` when authenticated GitHub API access is required or desirable for rate limits.
- [ ] Create an **annotated** version tag at that exact commit using the generated evidence message:

  ```text
  git tag -a v<version> <release-sha> -F reports/release-tag-v<version>.txt
  ```

  The annotation is the durable hosted-CI evidence record; a lightweight tag does not satisfy this
  release contract.
- [ ] Push the tag, then verify that the remote annotated tag resolves to the intended commit and its
  annotation contains the expected three hosted workflow records.

A published release tag is immutable project history. Correct a material release
error with a subsequent release rather than silently moving a published tag.

## 6. Deployment and post-release verification

For releases that are deployed to the hosted InfinityDB instance:

- [ ] Deploy the tagged self-contained release using the workflow in `docs/deployment.md`;
  production must not rebuild or substitute runtime databases after the tag is validated.
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
