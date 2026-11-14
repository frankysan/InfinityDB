# Release process

**Project domain:** Project infrastructure

This document is the canonical release checklist for InfinityDB. **Every release**
must pass this checklist unless a step is explicitly inapplicable to that release.
Unfinished **implementation** work belongs in `docs/TODO.md`; release-only
approvals, exact-SHA hosted evidence, tagging, deployment and verification belong
in this checklist. The version-1.0 completeness definition remains here as a
durable acceptance contract. The runbook records release obligations without
making a second TODO-cleanup merge necessary.

A release is not ready merely because its implementation checks pass. The release
gate includes repository state, documentation, release metadata, hosted validation,
and post-release verification.

Commands shown as `python` in this checklist use **the project's virtual
environment**, not system Python: `.\.venv\Scripts\python.exe` in PowerShell
or `.venv/bin/python` on Linux/macOS. Use the repository root as the
working directory and substitute the actual release SHA/tag for placeholders.

## Version 1.0 data-completeness gate

Version 1.0 represents the point where InfinityDB provides a **complete,
usable current reference for normal Infinity gameplay** over its supported
Army data, current rules catalog, FAQ and core scenarios. **Every in-scope
rule or rules-reference concept must have at least one accurate citation to
an applicable current source**, plus a maintained player-oriented explanation
and a usable normal-browser entry or contextual route. A single source is
sufficient; multiple languages, publications, revisions and clause-by-clause
provenance are **not** required for each rule. A specialized or final-form UI
is unnecessary when basic presentation is understandable and navigable.

This is a **record-to-current-source citation and player-facing correctness
gate**, not an exhaustive inventory of every clause, footnote, example or
concept from every available PDF, Wiki revision or Army capture. Supported
Army/profile data and known material gameplay defects still need their normal
correctness and publication checks. Optional discovery of additional source
content, exhaustive cross-source comparison and publisher reconciliation are
post-1.0 research, not conditions for shipping 1.0.

The current core-rules scenarios are part of the 1.0 requirement: they must have a
maintained structured representation and a usable browsable presentation. The implemented bounded
core-scenario model derives from the comparative review of the core scenarios and ITS Seasons 17
and 18 in `docs/architecture.md` and `docs/data-model.md`; final 1.0 completeness review must preserve
that extensibility. ITS-specific missions,
season material, tournament/event tooling, and a complete historical ITS library remain outside the
1.0 requirement unless they are necessary to interpret otherwise in-scope data. Scenario-specific
Skills, Equipment, States, Traits, contextual roles, objective elements, or other named rules
concepts remain in scope when needed by the core scenarios or the general catalog/reference
experience; preserve their scenario/season scope. Core-scenario geometry must also drive the
versioned deterministic SVG renderer so the four supported missions do not depend on manually
maintained diagrams. Geometry schema v1 only needs to cover those core missions; ITS-only map
features and an interactive editor remain outside the 1.0 gate. Final visual polish, every planned
search/filter/comparison feature, exhaustive performance work, additional theme variants beyond
shipped System/Light/Dark, deployment conveniences, and unrelated architectural refactors
likewise do not block 1.0. Accessibility of the shipped themes remains a release check.

The 1.0 release gate requires:

- [ ] Verify the supported Army/profile dataset and enumerate the **maintained
  current rules-reference records**, including general rules, Skills, Equipment,
  weapons, States, Traits, glossary and concepts required by core scenarios.
  Detect missing reference identities from **known application dependencies**,
  not by exhaustive page-by-page scanning of all external sources.
- [ ] Give each in-scope rule/reference identity **at least one** applicable,
  current, inspectable source citation and a usable maintained representation.
  A source/version mismatch or uncited record is a gap; a second or third
  corroborating citation is optional. Preserve relationships needed for normal
  comprehension without inventing unsupported gameplay effects.
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
- [ ] Ensure **interactions actually represented in the current application**
  explain their material conditions and exceptions correctly, with at least one
  applicable current citation where they assert a rules outcome. Preserve the
  [curated interaction explanation standard](../data/curated/README.md#explaining-rules-interactions)
  for authored interaction explanations; do not require discovering and
  implementing every possible interaction from the source corpus.
- [ ] Preserve rules/source provenance so users can identify the official material
  behind summaries or interpretations; distinguish InfinityDB summaries and
  abstractions from verbatim/source-native facts.
- [ ] Resolve duplicate, renamed, superseded, or differently structured rules concepts
  into a coherent maintained representation with sufficient relationships to surface
  relevant rules alongside the entities that use them.
- [ ] Represent empty, unavailable, and not-applicable values deliberately rather than
  silently omitting them where that could mislead users.
- [ ] Check the **selected supported-source-to-record-to-browser path** for
  in-scope references and relevant generated artifacts. Verify cited source
  versions, stored identities and normal routes, and keep already known
  material limitations or contradictions honestly disclosed. Do not require
  a source-wide omission inventory or cross-edition discrepancy hunt.
- [ ] Resolve any known defect that materially misrepresents a player's unit, profile,
  weapon, skill, equipment, army relationship, or rule information.

**Discovering or resolving official source discrepancies is not a 1.0
requirement.** Open entries in the
[SRC clarification register](official-source-clarifications.md) may remain
unanswered or uninvestigated. When a meaningful disagreement is *already
known* and affects a published rule, disclose the selected current source,
published interpretation and relevant uncertainty accurately; do not claim
that sources agree. A known incorrect player-facing statement still needs
correction. No publisher response, cross-language comparison, new source
reconciliation, or comprehensive discrepancy inventory is required for 1.0.
Keep such research and publisher requests as optional post-1.0 work.

The 1.0 baseline audit covers **current maintained rule/reference
identities** with at least one applicable current citation each, accurate
normal-browser reachability and known material defects. Confirm the supported
Army dataset and core scenarios remain usable. Do **not** infer missing rules
from unchecked source pages or require whole-source/whole-record semantic
sign-offs, exhaustive omission disposition, or a new cross-publication study.

## 1. Confirm release scope

- [ ] Confirm the target version and the intended release scope.
- [ ] Complete the release-specific requirements recorded in `docs/TODO.md`.
- [ ] Resolve all design/execution obligations in the
  [validation queue](validation-queue.md) for this release's changes. Deferred
  local testing never replaces the required CI and final candidate checks.
- [ ] For releases with a maintained rules-interaction review target, run the interaction
  audit with both `--check-output docs/rules-interaction-checklist.md` and
  `--require-release <version>`, then resolve every pending entity for that release. Deferred
  candidates explicitly targeting later releases remain tracked and do not block the current
  release.
- [ ] Resolve known release-blocking defects. Explicitly defer non-blocking work to
  `docs/TODO.md` rather than leaving its status ambiguous.
- [ ] Confirm that any schema, compatibility, data-rebuild, deployment, or asset
  consequences are understood before preparing the release metadata.

## 2. Review release-relevant documentation

Review documentation affected by the changes being released. A full
project-wide document audit is **not** a recurring release gate: reserve it
for architectural migrations, renamed subsystems or a known inconsistency
that cannot be reviewed narrowly.

- [ ] Reconcile implemented behavior and current setup/CLI/deployment guidance
  in the authoritative documentation owners.
- [ ] Review the pending changelog, current-release README statement, and any
  version, source/publication or schema information affected by this release.
- [ ] Update cross-references to changed or retired paths; run the documentation
  checks (Markdown lint, local links and backlog integrity).
- [ ] Review player-facing text and accessibility when the release changes those
  surfaces. Preserve licensing/provenance obligations.
- [ ] Keep genuinely unfinished implementation work in `TODO.md`, not
  post-merge administrative closeout commits.

A broader documentation inventory is appropriate when the change warrants
it, not as a default gate for metadata-only releases. Do not create an
additional release audit diary: Git history and the canonical documents
supply the record.

## 3. Prepare release notes and metadata

### Between releases

**Project domains:** Project infrastructure, Web backend, Web frontend

Once a development branch has an agreed release target, record implemented
changes directly under a version-specific pending heading in `docs/CHANGELOG.md`:

```markdown
## [1.0.1] - Unreleased
```

- The pending heading is the maintained record of the branch's target version.
  For example, `dev/v1.0.1` targets `1.0.1`. Confirm the agreed target when
  starting work; do not choose a new target from the change's apparent size.
- Keep one pending release section at the top, followed by dated release
  history. Add meaningful implemented outcomes to that target as work lands,
  using the writing rules below. Planned or deferred work stays in `docs/TODO.md`.
- Use a generic `## [Unreleased]` section only while no release target has
  been agreed. Once the target is known, rename that section to the named
  pending heading, retaining its entries. Do not keep a parallel generic
  bucket for changes already assigned to the target.
- If the agreed target changes, rename the pending heading and reconcile its
  entries with the new scope. Move unimplemented or deferred work to the
  backlog; retain implemented changes that remain in the branch. Do not
  silently relabel dated release history.
- Keep `Unreleased` in place of the date until release preparation. The
  browser presents the target as, for example, **Version 1.0.1 — Unreleased**,
  without a release date. Naming the target does not change the package
  version, establish a release date, or imply CI, tagging or deployment acceptance.
- At release preparation, replace `Unreleased` with the agreed release date
  and apply the version/metadata checklist below. After release, start a
  pending section for the next agreed target when its first meaningful
  implemented change lands; use the generic fallback if that target is unknown.

Empty pending sections need no filler and are omitted from the browser page.
Historical generic `Unreleased` headings remain supported for compatibility.

### Writing release notes

**Changelog entry discipline (also applies during development):** Introduce
the features and changes implemented in each release, with the **end-user
perspective first and the developer/maintainer perspective second**. The
v1.0.0 entry in `docs/CHANGELOG.md` is the style example for future entries.

- Use **past tense for completed changes**, including the Player summary and
  implemented changes in pending release sections: “Added the ability to …”,
  “Expanded …”, “Clarified the use of …” or “Corrected …”. Use **present tense
  for ongoing behavior, capabilities, requirements and compatibility** in the
  version being described. Mix tenses within an entry when their meanings
  differ: “Retired loose deployed-object JSON serving. Current images require
  database-embedded deployed objects; older releases remain recoverable through
  their matching retained images.” Use past tense for behavior that applied
  only before the change. Describe release outcomes rather than imperative
  browsing instructions or a general feature guide. Planned work belongs in
  the backlog, not the changelog.
- Lead with the capability, correction or practical effect for players or
  operators. Name the affected feature and explain what was added, changed
  or fixed in language accessible without internal development context.
  Retain canonical project-domain labels, but keep implementation mechanics
  out of the player-facing explanation.
- Begin with a concise `Player summary` containing only player-visible or
  player-useful outcomes (use `No player-facing changes.` for operator-only
  releases). Follow with `Added`, `Changed` and `Fixed` as applicable, then
  `Upgrade notes` for operator requirements. Keep the summary brief without
  imposing that brevity on the detailed entries.
- Preserve enough detail to introduce each meaningful feature or correction:
  concrete capabilities, choices, representative examples, important
  conditions, scope limits and unresolved source disagreements. Keep distinct
  features identifiable rather than collapsing them into vague claims such
  as “Expanded rules references” or “Improved usability”.
- Consolidate overlapping entries and remove repetition while retaining
  useful information. Omit commit-by-commit history, test counts, internal
  refactors, audit bookkeeping and bare schema versions. Include technical
  detail when it explains a user/operator consequence, such as an upgrade
  requirement or compatibility limit; place that detail after player outcomes.

Review the pending release's entries together before finalization.
`docs/CHANGELOG.md` contains release content, not maintainer
instructions, because the web application parses it to render **What's changed**.

### Finalize release notes and metadata

- [ ] Confirm the pending heading names the agreed target version.
- [ ] Cross-check the pending release against substantive player/operator changes in Git
  history since the previous release and the last changelog update. Restore
  missing outcomes, but do not turn commits, tests or internal refactors into
  individual release-note entries.
- [ ] Review the complete pending section of `docs/CHANGELOG.md` as one release:
  use past tense for completed changes and present tense for ongoing behavior
  in that version, with an end-user-first perspective. Keep its `Player summary`
  concise and player-visible only, and retain concrete feature and correction
  detail below it. Merge overlapping entries, remove implementation-only
  detail, and make upgrade consequences explicit.
- [ ] When substantially rewriting or consolidating existing notes, compare
  against the pre-rewrite version in Git history. Verify that distinct
  capabilities, meaningful fixes, examples and important qualifications
  survived the rewrite; restore useful detail lost through over-compression.
- [ ] Replace the target section's `Unreleased` status with the agreed release date.
- [ ] Update the package/application version consistently in `pyproject.toml` and
  `src/infinity_army_data/__init__.py`.
- [ ] Update the current-release statement in `README.md`.
- [ ] Freeze the README/changelog for the target released version before the final
  planned merge. The text describes the version being shipped; publication
  evidence remains the tag, exact-SHA CI and production verification in this
  checklist. Do not create a second merge merely to rewrite the TODO.
- [ ] Re-run the documentation audit checks affected by those release-metadata edits.

Do not change the released version early merely to mark work in progress; development
checkouts use the existing `+dev` display-version mechanism until release preparation.

## 4. Run local release validation

Run **one relevant acceptance set**, rather than repeating the whole
development suite and an isolated preflight merely because a release is due:

- [ ] Check that the intended release inputs and runtime data match. When
  Army/rules/curation or published assets changed, rebuild with the current
  supported pipeline and validate source identity, citations, SQLite schema,
  derived publications and source/asset pairing. Until P2 replaces the
  publication pipeline, use its existing matched-artifact checks rather than
  hand-editing a tracked release database.
- [ ] Run `python -m tools.verify_deployment_assets` for the actual published
  database and SVG set. Invalid/stale release artifacts are blockers.
- [ ] Run changed-behavior focused tests and relevant lint/type/docs checks.
  Run a broader test set only for a genuine cross-cutting risk or an explicit
  release-specific acceptance requirement. A successful, equivalent hosted
  Source matrix counts as the cumulative run; **do not automatically run the
  same full suite locally and again in preflight**.
- [ ] Run `python -m tools.release_metadata` **after finalizing** the target
  version, README and dated `docs/CHANGELOG.md` heading. `Unreleased` is
  valid during development but **not** for this release gate.
- [ ] Confirm the intended changes to user-facing routes work, with focused
  browser checks when UI/navigation/layout changed. A large multi-browser or
  whole-site matrix is optional unless a specific product risk justifies it.
- [ ] Confirm the release commit contains only intentional changes and that
  required pending test obligations for the release are resolved.

The [Source workflow](ci.md#risk-based-source-validation) retains its
change-aware hosted validation: one complete Linux suite with cross-platform
build/determinism checks for executable or unknown changes, and focused
reuse for eligible narrow updates.
Installed-wheel and Docker smoke run as separate hosted checks on the final
release SHA; they need not be reproduced locally when they already cover the
exact intended artifact. Check newly changed components after any correction;
a metadata-only adjustment does not invalidate an unrelated completed suite.

## 5. Land the release commit, verify hosted CI, and tag

### Development freeze and release-only handoff

The approved merge should include the **final** version, dated changelog,
README and affected documentation. After merging, verify CI, tag and deploy;
do not create another routine PR just to mark release-only checklist items
complete. Historical v1.0 V1S-093–095 handoff details remain in Git history
and the 1.0 acceptance records.

- [ ] Merge the approved, locally verified candidate through the intended
  PR workflow. The resulting `main` SHA (which may differ from the branch
  tip after a merge/squash) is the candidate for tagging.
- [ ] Verify that the latest **Source checks**, **Installed wheel smoke** and
  **Deployment smoke test** workflows on this **exact SHA** are successful.
  Source acceptance requires each applicable matrix job and its deterministic
  output check, or a demonstrably valid focused baseline-reuse path. The
  Docker workflow builds and smoke-tests the current immutable image; no
  v8 rollback rehearsal is required.
- [ ] The four-platform **Cross-browser compatibility** workflow is **opt-in
  for v1.1.0 onward**: dispatch it for changes whose browser compatibility
  risk warrants the extra coverage. The existing v1.0.x tag contract still
  requires all four successful jobs. Also run optional `Full-asset checks`
  only for a release that needs the external checksum-pinned bundle.
- [ ] If a required check fails, repair on the development branch and
  produce a new approved SHA. Re-run only affected local checks, but obtain
  exact-SHA hosted evidence for the corrected candidate before tagging.
- [ ] Run the release-evidence collector, substituting the exact target
  SHA, version and a fresh UTC run ID. New release evidence belongs under
  ignored `local/validation/project-infrastructure/release-ci/<UTC-run-id>-<short-SHA>/`:

  ```text
  python -m tools.prepare_release_ci_evidence --repository OWNER/REPO --commit <release-sha> --tag v<version> --json-output local/validation/project-infrastructure/release-ci/<UTC-run-id>-<short-SHA>/evidence.json --tag-message-output local/validation/project-infrastructure/release-ci/<UTC-run-id>-<short-SHA>/annotated-tag.txt
  ```

  The collector rejects both files if either already exists or the two output
  selections resolve to the same file. Re-running a completed check requires a
  fresh evidence directory; never delete earlier accepted evidence merely to
  reuse its name. Older explicit `reports/` paths remain readable and usable
  for their historical records. If output fails midway, inspect any newly
  created partial file before retrying; the two writes are not one atomic
  filesystem transaction.

  Use `--include-cross-browser` when the optional browser matrix is selected
  for v1.1+; `--include-full-assets` when its independent bundle check is
  selected. Run it from the checkout at the **exact final release SHA**:
  the collector rejects a mismatched HEAD, still-`Unreleased` metadata,
  mismatched package/tag versions, and incomplete Source jobs. It enforces
  v1.0.x browser requirements automatically even when optional browser
  coverage is omitted for v1.1+.
- [ ] Create and push the **annotated** tag on the verified `main` SHA:

  ```text
  git tag -a v<version> <release-sha> -F local/validation/project-infrastructure/release-ci/<UTC-run-id>-<short-SHA>/annotated-tag.txt
  ```

  Verify the remote tag points to the intended SHA and preserves its
  verified workflow evidence. A published tag is immutable; correct a
  release defect with a subsequent version rather than moving the tag.

## 6. Deployment and post-release verification

Deployment is a separate **operator-authorized** action. The tagged,
self-contained image contains the already-verified databases and static assets;
the production host must not substitute newly built data.

- [ ] Deploy the selected immutable release through
  [deployment instructions](deployment.md), without a fresh application/data
  rebuild on the server.
- [ ] Confirm `/health`, `/api/version`, the release tag/version and
  expected runtime snapshot and static revision. Use the available paired
  database/source verifier when the release changes data publications.
- [ ] Smoke-test the main application route and the release's changed
  player-facing paths. Browser coverage should reflect affected UI,
  navigation and accessibility—not a compulsory 21/81-page acceptance
  matrix for every deployment.
- [ ] Investigate a failed health, identity or changed-route check before
  claiming the deployment accepted. Git tags and previously built images
  provide the normal recovery baseline; rollback *rehearsal*, old-schema
  compatibility images and mandatory prior-image inventory are not routine
  release gates.

Record concise release outcomes in the changelog or normal release/deployment
records. Keep detailed operational reports under ignored `local/`,
not a second tracked release checklist.
