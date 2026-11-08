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
- [ ] Review `docs/TODO.md` using the
  [completion and retirement rules](README.md#backlog-completion-and-retirement):
  no checked entry may retain unfinished descendants or required validation.
  Confirm practical outcomes are documented, completed tasks/subtrees are removed,
  completed child context is brief and linked, and open work describes only what remains.
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
historical context. Keep new private/raw audit evidence under ignored `local/audits/`;
existing ignored `docs/audits/` and `reports/` paths remain supported for
compatibility. Do not create a permanent release-specific audit document by default:
promote lasting conclusions into the canonical document owner, record release outcomes in `CHANGELOG.md`, and let Git history preserve the
review narrative. Keep a tracked audit/closeout file only when it contains unique rationale that
will actively guide later work.

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

- Write in **past tense**, including the Player summary and implemented
  changes in pending release sections: “Added the ability to …”, “Expanded …”,
  “Clarified the use of …” or “Corrected …”. Describe what changed; avoid
  imperative browsing instructions or a general present-tense feature guide.
  Planned work belongs in the backlog, not the changelog.
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
  use past tense and an end-user-first perspective, keep its `Player summary`
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

- [ ] Rebuild and validate any release runtime database whose source/curated inputs changed,
  then ensure `data/generated/infinity.db` and `data/generated/rules.db` are the intended
  tracked release artifacts.
- [ ] For 1.0, after rebuilding the tracked `rules.db`, run the
  [opt-in FAQ release-artifact parity gate](testing.md#10-four-core-scenario-browser-acceptance)
  with `INFINITYDB_RELEASE_FAQ_PARITY=1`. Require all 29 current FAQ
  records, citations, source metadata and 48 topic associations to
  match a fresh curated export. A stale tracked binary blocks release,
  even when source and browser tests using fresh exports pass.
- [ ] After rebuilding either database, follow the schema-specific
  [matched-artifact workflow](deployment.md#normal-updates-from-081-onward).
  For v10, verify embedded deployed objects and use
  `tools.build_v10_runtime_candidate --check` for the source-matched
  candidate; tracked promotion is a separate explicit operation.
  Only legacy v8/v9 releases generate and `--check` the pinned
  `data/generated/deployed-objects.json` with
  `tools.build_deployed_object_publication`. Regenerate the tracked
  `data/generated/variant-usage.json` with `tools.build_variant_usage --publish`
  from the matched raw Army archive, then run `--check-publication` before
  staging the exact bytes. Deployment/CI without raw inputs must validate the
  tracked variant publication against the released Army/rules/deployed-object
  fingerprints; a stale or absent publication blocks current-release packaging.
  Also rebuild and `--check` the tracked
  `data/generated/weapon-profile-sources.json` using
  `tools.build_weapon_profile_publication`; its database, review and PDF
  fingerprints must match before staging.
  With `INFINITYDB_RELEASE_FAQ_PARITY=1`, run the tracked-pair FAQ
  primary, secondary and conflict Chromium tests. Fresh-export browser
  tests alone do not verify the release database pair.
- [ ] For 1.0, require source-field occupancy verification against the release-matched
  `data/generated/infinity.db` and its paired `infinity.raw.db`. Use
  `python tools/run_checks.py --all --source-occupancy-gate` for the local
  release-candidate validation. The opt-in gate fails closed when the raw
  source pair is missing or any statically unrepresented player field is
  populated; re-audit changed inputs instead of suppressing a failure.
  Ordinary development and CI `--all` runs remain unchanged.
- [ ] Run `python tools/verify_deployment_assets.py` and require the tracked Army database,
  rules database, processed SVG publication, and publication snapshot provenance to pass as one
  release set.
- [ ] Install the pinned Markdownlint dependency with
  `npm ci --ignore-scripts --no-audit --no-fund` (Node.js 22+), then run the complete local
  validation suite with `python tools/run_checks.py --all` (for 1.0, include
  `--source-occupancy-gate` as described above), including the `docs`
  and Git-index `preflight` stages. The preflight checks staged release
  content, including tracked `src/` files and configured wheel data, **not
  unstaged tracked edits**. Run it again after staging the final candidate
  when the index changes; the separate
  `Installed wheel smoke` workflow remains mandatory for runtime validation.
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

### Development freeze and release-only handoff

For 1.0.0, **the development branch and its active implementation TODO must be
final before the approved merge**. The merge is the final *planned* tracked
source/documentation change. Afterward, exact-main-SHA CI, the annotated tag,
deployment and production verification are operator release steps. Record their
results in GitHub Actions, the immutable tag annotation, release/deployment
records and ignored operational reports, **not by editing TODO and making a
routine second merge**.

The following former V1S entries are **transferred obligations, not completed
tasks**. They are accepted only as their corresponding checklist steps pass:

- **V1S-093 — integration and tag:** Approve and merge the frozen candidate;
  require exact-main-SHA Source, wheel, deployment smoke and all four
  cross-browser jobs, optional full-asset evidence where configured, and the
  annotated tag. Investigate any recurring Windows scenario lifecycle timeout
  if it affects hosted acceptance. Tag approval remains a separate release-owner
  decision.
- **V1S-094 — authorized deployment:** Deploy the verified tagged artifact only
  with explicit operator approval; confirm previous-image/database and recovery
  assets exist. No live rollback rehearsal is required.
- **V1S-095 — deployed acceptance:** Verify the exact source/runtime database
  pair, application version, static assets and representative browser paths on
  the actual hosted deployment.

If a post-merge gate reveals a defect requiring tracked changes, **stop release
acceptance**, prepare and validate a corrected development candidate, then
perform another approved merge and exact-SHA checks. That is an exceptional
repair, not a routine second merge merely to retire operational TODO entries.

- [ ] Before merge, when the optional checksum-pinned publication bundle is part of the release
  gate, manually dispatch `Full-asset checks` against the release-candidate branch and record the
  successful run SHA. This pre-merge validation does not require the candidate to be on `main`.
- [ ] After the local release checklist is green, create the release-preparation commit and land
  it on protected `main` through the normal pull-request workflow. The resulting `main` revision is
  the candidate release commit; if the repository uses a merge or squash commit, use that resulting
  commit rather than assuming the branch-head SHA is the release SHA.
- [ ] For 1.0, require all four **Cross-browser compatibility** jobs
  (Ubuntu Chromium/Firefox, macOS WebKit and Windows Edge) successful on the
  exact candidate SHA. A green aggregate run cannot replace individual job
  acceptance. The version-aware release-evidence collector verifies the four
  terminal job conclusions before preparing the tag; a missing workflow,
  skipped job or previous candidate's run blocks tagging. Retain JUnit and
  failure traces, and preserve independent human/real-device sign-off.
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
  python -m tools.prepare_release_ci_evidence --repository OWNER/REPO --commit <release-sha> --tag v<version> --json-output reports/release-ci-v<version>.json --tag-message-output reports/release-tag-v<version>.txt
  ```

  The command must verify successful `Source checks`, `Installed wheel smoke`, and
  `Deployment smoke test` runs for that exact SHA. For tags **v1.0 or later**,
  it also automatically requires the `Cross-browser compatibility` workflow and
  its four successful matrix jobs; no optional flag can bypass this release gate.
  Add `--include-full-assets` when this release's
  retained evidence should also require the optional checksum-pinned `Full-asset checks` workflow.
  If merge/squash created a different SHA from the pre-merge candidate, dispatch the optional
  workflow again for the final `main` SHA before collecting evidence.
  Set `GITHUB_TOKEN` when authenticated GitHub API access is required or desirable for rate limits.
- [ ] Create an **annotated** version tag at that exact commit using the generated evidence message:

  ```text
  git tag -a v<version> <release-sha> -F reports/release-tag-v<version>.txt
  ```

  The annotation is the durable hosted-CI evidence record; a lightweight tag does not satisfy this
  release contract.
- [ ] Push the tag, then verify that the remote annotated tag resolves to the intended commit and its
  annotation contains the expected hosted workflow records (four for v1.0
  and later, or five when optional Full-asset checks are included).

A published release tag is immutable project history. Correct a material release
error with a subsequent release rather than silently moving a published tag.

## 6. Deployment and post-release verification

For releases that are deployed to the hosted InfinityDB instance:

- [ ] Deploy the tagged self-contained release using the workflow in `docs/deployment.md`;
  production must not rebuild or substitute runtime databases after the tag is validated.
- [ ] Verify the deployed application reports the intended release version and source
  snapshot. For 1.0, use the opt-in
  `tools.report_reference_baseline --verify-server <server-origin>` check
  against the exact retained candidate Army/rules databases and applicable
  Weapon-profile publication to reject stale or substituted runtime artifacts.
  This check does not validate symbol/PDF/Wiki inputs or rules completeness.
- [ ] Smoke-test the release's principal changed user-facing paths in the deployed
  application. For 1.0, run `tools.verify_release_candidate_browser` against
  the served candidate, explicitly specifying `--expected-version` and the
  release-matched Army/rules database pair and applicable Weapon-profile
  publication. It checks the exact runtime revision, release version and local
  static asset fingerprint **before and after** representative Unit-detail
  Chromium checks, aborting on any mismatch.
  Retain its JSON report under ignored `local/audits/` only after success.
  The default hosted Unit check is seven Units at three widths (21 pages).
  The separate local 81-page matrix includes additional layouts, optional-unit
  Settings and distance variants; see [testing](testing.md#10-source-evidence-baseline).
  Neither replaces the 1.0 source-to-browser completeness verdict or acceptance
  of the release's other changed surfaces.
- [ ] Confirm required database/schema rebuilds and published assets are actually the
  release-matched versions.
- [ ] Confirm the retained prior release image/database and documented recovery
  path remain available before considering deployment acceptance complete.
  For the single-operator 1.0 deployment, this is an availability check,
  **not** a required live-host rollback/forward rehearsal. Retain the normal
  deployment smoke, exact-version and runtime-pair verification gates.

Record durable release outcomes in the changelog/reference documentation. Detailed
check logs and one-off acceptance evidence should remain in their normal reports, CI,
or Git history rather than turning `docs/TODO.md` into an archive of completed
release checklists.
