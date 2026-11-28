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

## Mandatory pre-merge release sign-off

**Do not merge a development branch until every applicable item below is
accepted for the final candidate.** These are release gates, not development
backlog tasks. Use the detailed procedures in sections 1–4 below and retain
one concise record of the candidate SHA, check results and any reviewed skips
under ignored `local/validation/`. A failure requires a correction and renewed
affected acceptance before the merge.

- [ ] **Scope and correctness:** All promised release work and required
  validation are complete; known player-impacting defects are resolved and
  genuinely deferred non-blockers remain in `TODO.md`.
- [ ] **Player-facing copy:** Review normal-mode pages, messages, empty/error
  states and release notes. Everything visible to players is useful and
  comprehensible without development context. Put technical IDs, internal
  diagnostics, audit status and source-review tooling behind Developer Mode;
  keep gameplay-significant caveats, accurate source citations, and necessary
  attribution visible in normal mode.
- [ ] **Finalized release references:** Every maintained current-state document,
  version string, help/about surface and changelog presents the target as the
  **current, fully released version**. No "candidate", "pending release",
  "not yet released" or post-merge documentation work remains. Dated historical
  evidence retains its original version and truth; deployment verification
  remains an operational action, not a qualifier added to the release text.
- [ ] **Changelog accuracy:** Compare `docs/CHANGELOG.md` with the actual
  changes since the **last tagged release**. Include every meaningful shipped
  player/operator capability, correction and compatibility/deployment impact;
  remove claims about unfinished, deferred or unchanged behavior. Keep the
  player summary concise without losing substantive details below it.
- [ ] **Local full-suite validation:** The complete local pytest suite runs
  with `--assets required` and passes, including required browser tests.
  Review and explain skips, and pass Ruff, Pyright, docs/link/backlog,
  build/rules checks and finalized release metadata. A green hosted Source
  workflow does **not** replace this local release gate.
- [ ] **Publication integrity:** The tracked Army/Rules/ITS runtime set and
  graphical assets are source-matched and pass deployment artifact validation.
- [ ] **Real Docker test deployment:** Deploy the candidate into the isolated
  `infinitydb-test` Docker Compose stack, not just a built-image verifier.
  Confirm health, version/runtime identity, representative changed routes,
  Caddy and metrics-history behavior, and no interaction with production.
- [ ] **Browser and accessibility acceptance:** Exercise materially changed
  player journeys in ordinary mode, including relevant desktop/mobile,
  keyboard, touch, loading/error and shared-link behavior. Record manual
  assistive-technology acceptance where needed.
- [ ] **Merge-ready Git/CI:** The candidate tree is clean, all changes are
  intentional, and the required PR Source, installed-wheel and Docker smoke
  checks (and chosen additional browser checks) have passed for the candidate
  SHA. Obtain merge approval; after the merge, verify the resulting exact
  `main` SHA again before tagging, using fresh CI or verified identical-tree reuse.

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
- [ ] Verify that all maintained current-state documentation, generated version
  surfaces, README, release-notes page, and package/API metadata present the
  agreed target as the **current, released version**. Do not merge statements
  describing this target as an unreleased candidate or awaiting a later
  documentation update. Preserve truthful dated historical evidence.
- [ ] Update cross-references to changed or retired paths; run the documentation
  checks (Markdown lint, local links and backlog integrity).
- [ ] Review normal-mode player-facing pages and controls for copy intended for
  the player, not the developer. Technical identifiers, source-audit progress,
  diagnostic fields, internal processing terminology and development guidance
  belong in Developer Mode or outside the site. Preserve gameplay-significant
  ambiguity, accurate source provenance, attribution and necessary accuracy
  notices in ordinary mode rather than hiding important warnings.
- [ ] For changed interactive surfaces, exercise keyboard/focus, screen-reader
  labels where relevant, touch, responsive layouts, loading/error messages and
  shared-link navigation; include manual assistive-technology acceptance when
  automation cannot establish usability. Compare both Developer Mode states
  so hidden technical content remains accessible to maintainers without
  leaking into the default player view.
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
- Group multiple player-facing changes or additions in the same feature area
  under one descriptive, bold parent bullet with a single level of sub-bullets.
  Apply this to the Player summary and, where useful, within each detailed
  section; keep Added, Changed and Fixed distinct. Name groups for the player
  journey or reference area (for example Search and Glossary, Armies and Units,
  or Performance improvements), not the implementation layer. Retain domain
  labels on detailed child entries. Leave unrelated or standalone outcomes as
  individual bullets; do not flatten distinct improvements into one vague item.
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
- [ ] Identify the **last tagged release** as the comparison baseline.
  Review the Git diff, relevant commits and shipped application/data changes
  from that tag through the intended release SHA against `docs/CHANGELOG.md`.
  Restore missing meaningful player/operator outcomes, remove claims not
  supported by the shipped changes, and include material behavior,
  compatibility, data and deployment consequences. Do not turn individual
  commits, tests, audits or internal refactors into release-note entries.
- [ ] Review the complete pending section of `docs/CHANGELOG.md` as one release:
  use past tense for completed changes and present tense for ongoing behavior
  in that version, with an end-user-first perspective. Keep its `Player summary`
  concise and player-visible only, and retain concrete feature and correction
  detail below it. Group related player-facing outcomes into feature-area
  sub-lists. Merge overlapping entries, remove implementation-only
  detail, and make upgrade consequences explicit.
- [ ] When substantially rewriting or consolidating existing notes, compare
  against the pre-rewrite version in Git history. Verify that distinct
  capabilities, meaningful fixes, examples and important qualifications
  survived the rewrite; restore useful detail lost through over-compression.
- [ ] Replace the target section's `Unreleased` status with the agreed release date.
- [ ] Update the package/application version consistently in `pyproject.toml` and
  `src/infinity_army_data/__init__.py`.
- [ ] Update the current-release statement in `README.md`; verify
  `What's changed`, version/footer copy and other maintained references against
  the finalized version and date.
- [ ] Freeze README, changelog, affected reference documents and version
  metadata **as though the target release were already published** before the
  final planned merge. Do not add "release candidate", "not deployed" or
  "awaiting merge" qualifications to these release descriptions. Publication
  evidence remains the exact-SHA hosted checks, tag and operational verification
  later in this checklist; do not create a second merge just to repair prose.
- [ ] Re-run the documentation audit checks affected by those release-metadata edits.

Do not change the released version early merely to mark work in progress; development
checkouts use the existing `+dev` display-version mechanism until release preparation.

## 4. Run local release validation

This is a **mandatory local release gate**, separate from development's
risk-based selection and from hosted CI. Run it against a clean, pinned
candidate checkout with the required graphical assets available. The final
release cannot be approved on focused tests alone.

**Freeze release-facing content before expensive acceptance:** finish the dated
changelog, README, version metadata, deployment instructions and release-tooling
changes; pass the cheap metadata, documentation and affected tooling checks first.
Then run the mandatory full suite and isolated Docker acceptance once against
the stable candidate. Re-run affected gates if the candidate changes.

- [ ] Verify the complete tracked Army/Rules/ITS set, inputs, source identity,
  citations, SQLite schema and published SVGs. Rebuild from the supported
  pipeline if inputs changed; never hand-edit a release database. Run
  `python -m tools.verify_deployment_assets` and resolve all failures.
- [ ] **Pass the complete local pytest suite with required assets**, including
  browser coverage that is available on the selected test host. Save the
  transcript, test counts, host, SHA and skip reasons. Required cohorts cannot
  be silently skipped; review platform-specific and opt-in skips rather than
  treating them as successful tests. For source-backed tests requiring the
  legacy raw SQLite archive, run `python -m tools.testing.prepare_source_audit`
  from the checkout root before the suite. It uses the pinned Army ZIP and
  complete runtime build provenance, verifies the published export generation,
  and writes only ignored local audit artifacts. A prior audit directory
  with a different or unverifiable generation is retained separately.
  An ordinary standalone normalization/export is not a matched release pair.

  Follow the [validation host policy](testing.md#validation-host-selection):
  Linux is the default for complete release suites; Windows supplies focused
  or platform-specific evidence when needed.

  Linux (an explicitly synchronized, SHA-pinned checkout):

  ```sh
  .venv/bin/python tools/run_checks.py --stage test --assets required --test-workers 8 --test-dist browserlanes --browser-slot-count 4 --browser-lane-count 4 --split-scenario-faq --report
  ```

  Windows fallback (from the repository root, only when justified):

  ```powershell
  .\.venv\Scripts\python.exe tools\run_checks.py --stage test --assets required --test-workers 8 --test-dist browserlanes --report
  ```

- [ ] Run the [tracked-database FAQ parity gate](testing-data.md#release-tracked-faq-parity)
  after rebuilding the matched release databases. Set
  `INFINITYDB_RELEASE_FAQ_PARITY=1` for the 17 opt-in API/browser cases;
  the ordinary full suite skips them.

- [ ] Pass Ruff, Pyright, Markdownlint, document links, backlog checks and the
  maintained Army/Rules build stages using the canonical runner, plus the
  finalized release-metadata gate:

  ```powershell
  .\.venv\Scripts\python.exe tools\run_checks.py --stage lint --stage docs --stage type --stage build --stage rules --report
  .\.venv\Scripts\python.exe -m tools.ci.release_metadata
  ```

- [ ] Verify changed player journeys with Developer Mode **off** first, then
  check the availability of intentional technical detail in Developer Mode.
  For relevant UI changes, cover narrow/wide viewports, keyboard, touch,
  loading/error behavior and shared links. Record any required manual
  accessibility acceptance and resolve material findings.
- [ ] **Perform an isolated Docker test deployment** of the candidate release
  on a Docker Linux host. The supported local Compose stack uses the actual
  tracked runtime and symbol publication, builds both application and
  metrics-history images, verifies the images and starts app/Caddy. Docker
  image verification or a green hosted smoke job alone is **not** a substitute
  for the running local deployment. The public Caddy listener requires the
  `localhost` host name; `/health` is exposed by the loopback metrics listener:

  ```sh
  sh ./scripts/deploy-local-test.sh
  .venv/bin/python -m tools.ci.verify_running_deployment
  docker compose -p infinitydb-test ps
  ```

  Verify the returned target version and runtime/static revisions, open the
  application in a browser and smoke-test the release's changed routes,
  player-visible copy and representative API calls. Inspect app/Caddy and
  metrics-history status; confirm the stack is isolated as
  `infinitydb-test`, not production. See
  [isolated deployment instructions](deployment.md#isolated-local-deployment-test).
  When acceptance is complete, stop only the test stack:

  ```sh
  sh ./scripts/stop-local-test.sh
  ```

- [ ] Confirm the intended Git changes, clean tracked tree, completed
  acceptance and exact candidate SHA. Corrections to runtime code, tests,
  databases or assets invalidate affected evidence: rerun the required
  local gates on the corrected candidate before approving the merge.

Hosted [Source checks](ci.md#risk-based-source-validation) retain
cross-platform build/determinism coverage and risk-based matrix reuse,
**in addition to** the local full-suite and Docker deployment required
here. The independently required installed-wheel and Docker smoke workflows
validate hosted packaging, not the local running-stack requirement. An
isolated Git-index preflight is useful for a specific packaging risk, but
is not a second default full-suite run.

## 5. Approve the candidate, merge, verify main, and tag

### Reuse CI for identical merge trees (v1.2.2)

Avoid repeating equivalent hosted validation solely because merging produces a
new commit SHA. The mandatory pre-merge acceptance and exact candidate CI
remain unchanged. The release-evidence collector implements this policy:

- Accept green candidate CI for the final release commit when both commits
  have the same Git tree SHA and the required workflow coverage and validation
  semantics are equivalent. Verify the approved candidate and resulting
  `main` commit belong to the intended merge; record both commit SHAs, their
  verified tree identity and the actual workflow run SHAs in release evidence.
- Require fresh applicable CI on the final commit when the trees differ or
  equivalence cannot be established. Never reuse incomplete, failed or
  otherwise ineligible candidate evidence.
- Retain final-commit, tag and artifact-identity checks wherever the result
  depends on the release SHA, ref, event or generated deployment artifact.
  Tree equivalence does not establish equality of commit-dependent image
  metadata or release version identity. The tag still points to the verified
  final `main` commit.

The three core `main`-push workflows independently verify the merged PR and
candidate evidence before omitting their expensive steps. A changed tree,
missing PR/evidence or inaccessible API falls back to fresh validation. Manual
workflow dispatch always permits fresh checks. The final release collector
requires the explicit approved candidate SHA to use this exception; it does
not treat a reuse acknowledgment as a newly executed smoke or Source run.

### Development freeze and release-only handoff

The **pre-merge sign-off above is mandatory**; it is not retroactively
satisfied by CI on `main`. The approved merge includes the final version,
dated changelog, README and all affected documentation. Historical v1.0
V1S-093–095 handoff details remain in Git history and acceptance records.
Do not create a routine second PR to finish release prose or TODO cleanup.

- [ ] Before merging, verify that **Source checks**, **Installed wheel smoke**
  and **Deployment smoke test** are successful for the **exact development
  candidate SHA** in the PR. Inspect all applicable Source matrix and
  deterministic-output jobs, or its demonstrably valid focused
  baseline-reuse path. Missing, skipped or pending mandatory jobs do not pass.
- [ ] Choose whether the four-platform **Cross-browser compatibility** check
  is required for this release's changed browser behavior. For v1.1.0 onward
  it remains opt-in, but significant navigation, accessibility or browser-API
  changes warrant it; if selected, require all four exact-SHA jobs to pass.
  The historical v1.0.x contract requires all four. Run optional
  `Full-asset checks` only when the external checksum-pinned bundle is
  relevant.
- [ ] Before merging, **rehearse the release-evidence collector on the exact
  development candidate SHA** once its selected hosted checks are complete,
  after finalizing the version metadata. This validates the current CI matrix
  contract without creating tag evidence yet:

  ```text
  python -m tools.ci.prepare_release_ci_evidence --repository OWNER/REPO --commit <candidate-sha> --tag v<version> --check-only
  ```

  The final post-merge collector run is still required for the exact `main` SHA.
- [ ] Check that the recorded local **full suite**, isolated **Docker
  deployment**, player-copy review, documentation, metadata and required
  accessibility acceptance are all complete. Obtain merge approval, then
  merge the verified candidate through the intended PR workflow.
- [ ] After merging, identify the resulting exact `main` SHA (which may
  differ from the branch tip after a merge/squash). Verify the three mandatory
  hosted workflows and any selected additional checks **before tagging**,
  either on this exact SHA or through the verified identical-tree exception.
  Investigate any actual failed post-merge checks; reuse is not a failure waiver.
  The hosted Deployment smoke workflow does not replace the pre-merge Docker test stack.
- [ ] If any check fails, correct the development branch, run the applicable
  local acceptance again (including the complete suite and running Docker
  test for changed runtime behavior), and obtain green hosted evidence for
  the replacement SHA. Do not merge or tag an unverified revision.
- [ ] Run the release-evidence collector, substituting the exact target
  SHA, version and a fresh UTC run ID. New release evidence belongs under
  ignored `local/validation/project-infrastructure/release-ci/<UTC-run-id>-<short-SHA>/`:

  ```text
  python -m tools.ci.prepare_release_ci_evidence --repository OWNER/REPO --commit <release-sha> --tag v<version> --json-output local/validation/project-infrastructure/release-ci/<UTC-run-id>-<short-SHA>/evidence.json --tag-message-output local/validation/project-infrastructure/release-ci/<UTC-run-id>-<short-SHA>/annotated-tag.txt
  ```

  For an identical merged tree, add `--candidate <approved-candidate-sha>` to
  that command. The collector verifies the actual same-repository PR merged into
  `main`, both commit trees, and complete candidate workflow coverage. If reuse
  cannot be established, obtain fresh final-SHA CI (dispatch manually if needed)
  and run the command without `--candidate`. Optional selected workflows must
  also have successful evidence on the chosen validation SHA.

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
- [ ] Verify production's public and metrics listeners, exact browser footer
  version (no `+dev`), `/api/version`, snapshot/static revisions and
  representative page routes with the shared deployment probe:

  ```sh
  .venv/bin/python -m tools.ci.verify_running_deployment --public-base https://YOUR-HOST --metrics-base http://127.0.0.1:9090 --expected-version <version>
  ```

  If the external proxy rejects the probe, use the
  [direct Caddy invocation with an explicit Host header](deployment.md#isolated-local-deployment-test)
  and separately verify public browser access.

  Use the available paired database/source verifier when the release changes
  data publications.
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
