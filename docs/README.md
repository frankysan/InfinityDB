# Documentation map

**Project domain:** Project infrastructure

InfinityDB documentation is organized by **authority**, not by development chronology. Current
behavior should have one maintained owner; secondary documents link to that owner instead of
repeating the same contract. Git history and `docs/CHANGELOG.md` preserve release history.

## Canonical current-state documents

Use these documents when deciding how the project works now:

- `architecture.md` — system boundaries, engineering principles, ownership between subsystems,
  runtime/browser/deployment architecture, and accepted design direction.
- `data-model.md` — current source/application identities, semantic provenance, persistence,
  query semantics, and generated-database contracts.
- `application-domains.md` — canonical player-facing domain ownership and publication capabilities.
- `web-design-guidelines.md` — target browser design and language contract, including reusable
  surfaces, tables, controls, responsive behavior, typography, accessibility, and theming. It states
  requirements and design direction rather than claiming every current surface already complies.
- `project-domains.md` — engineering ownership labels used by planning and release notes.
- `data/README.md` — external inputs, generated artifacts, snapshot provenance, and publication
  lifecycle.
- `data/curated/README.md` — authored/curated data schemas and review contracts.
- `testing.md` — local validation commands, test selectors, worker and asset
  policies, plus dated 1.0 acceptance results. Historical runs are evidence for
  their pinned inputs, not current-release approval.
- [multi-agent-workspaces.md](multi-agent-workspaces.md) — optional coordination, enabled only
  by explicit user request; its checkout roles, claims and serialized integration apply within
  that requested scope, rather than to ordinary development by default.
- `validation-queue.md` — canonical VD/VR scheduling and active deferred-validation
  register (design/execution thresholds, dependencies, drain and retirement); not an implementation backlog.
- `ci.md` — hosted CI workflows and repository-level validation policy.
- `deployment.md` — production install/update/rollback/operations contract.
- `server-migration.md` — moving released or development environments between hosts.
- [syncthing-assets.md](syncthing-assets.md) — private Windows-to-Linux ignored-source staging,
  verification, and explicit checkout activation.
- `releasing.md` — mandatory release gate and the 1.0 completeness definition.

When two documents appear to overlap, prefer the owner above. Correct the owner first, then reduce
secondary text to a link or short boundary statement. Keep **current behavior**,
**accepted but unimplemented design direction**, and **historical evidence** clearly
distinguished. Unimplemented tasks live only in `TODO.md`; historical acceptance
may remain in source audits without being treated as current status. Agent entry
points (`AGENTS.md` and `.agents/skills/`) should provide task-boundary and
domain-specific actions, not second copies of operational thresholds or rules.
`AGENTS.local.md` is private, machine/user-specific guidance and must not
override tracked project policy.

## Active strategic plans

- [restructuring-plan.md](restructuring-plan.md) — proposed phased simplification of
  developer workflow, SQLite runtime data, source-family databases, player-facing
  presentation, tooling and repository structure. It maps dependencies and
  acceptance criteria but does not override current behavior or duplicate the
  live implementation backlog in `TODO.md`.

## Maintained evidence and research

These files intentionally retain reviewed evidence that is useful beyond one release:

- `rules-semantics.md` — audited rules meaning that already has a concrete InfinityDB consumer.
- `rules-research.md` — verified source findings retained for possible future product/model work.
- [official-source-clarifications.md](official-source-clarifications.md) — canonical,
  stable-ID register of unresolved and locally reconciled rules, Army, Wiki, FAQ
  and scenario discrepancies requiring possible official rulings or source
  corrections. Owns question wording, evidence, and publisher-response status;
  `TODO.md` tracks only the remaining follow-up work.
- `n5-source-history.md` — N5 official update-post index, historical Army evidence, and
  cross-source reconciliation procedure; an index, not a verified completeness ledger.
- [v1.0-source-coverage-audit.md](v1.0-source-coverage-audit.md) — dated 2026-10-31
  baseline evidence with subsequent source, browser, artifact and local candidate
  acceptance records. It preserves the reviewed 1.0 input scope without implying
  exhaustive whole-source coverage. Historical snapshots in this file are not
  current task status; `releasing.md` owns release handoff and `TODO.md`
  owns post-1.0 development.
- [rules-explanation-audit-1.0.md](rules-explanation-audit-1.0.md) — dated
  source/interaction assessment with implementation follow-ups and remaining
  source conflicts. Its linked inventory, N5.3 reconciliation and source manifest
  retain unique finding IDs, exact source hashes/revisions and unresolved
  publication discrepancies; they remain **frozen baseline evidence**, not a
  current defects list or a requirement for exhaustive post-1.0 source review.
  Keep unique source/provenance evidence while it supports unresolved questions;
  use `TODO.md` for current work and `rules-semantics.md` for reviewed meaning.
- `rules-interaction-checklist.md` — generated cross-release interaction-review ledger. Regenerate
  it with `tools/audit_rules_interactions.py`; do not edit it manually. Its release labels record the
  original review/defer decision and are evidence provenance, not the active roadmap; use `TODO.md`
  for current milestone planning.

Completed audit/closeout documents are **not** permanent reference documentation by default. Once
an audit closes, move lasting contracts into the canonical owner above, record user/operator-visible
outcomes in `CHANGELOG.md`, and let Git history preserve the detailed narrative. Keep a tracked audit
only when it contains unique rationale that still guides active work.

## One-use tool and audit lifecycle

**Project domain:** Project infrastructure

A one-use tool is a script written for a bounded migration, investigation, recovery or publication
step rather than an ongoing supported command. An audit may likewise be a dated investigation or
frozen acceptance record rather than maintained guidance. Names such as `stage_*`, `promote_*`
and `audit_*` are **candidates for review**, not proof that a file is disposable. Do not classify
reusable source validators, release gates or helpers as one-use solely from their names or age.

**Plan retirement when creating one-use work.** State the purpose, owning TODO/source-review ID,
expected artifacts/evidence, and the event after which the tool or report can be retired. Put
one-off output, backup files and execution logs under ignored `local/`; avoid making permanent
build, CI, runtime or release commands depend on them. Prefer extending an existing maintained
tool over accumulating a new wrapper when the operation is expected to recur.

**Review at bounded task closeout**, after successful publication/acceptance of the intended
artifact, or during a deliberate repository-hygiene pass. Use this order:

1. **Establish completion and provenance.** Identify the last purpose and exact input/output
   revisions or source hashes where material; verify the corresponding acceptance, rollback or
   release obligation is closed. An older successful stage does not retire a tool still needed
   for an open migration, reproducible source comparison or release-matched publication.
2. **Check consumers, not just direct imports.** Search the tracked tree for imports, module
   invocations and command strings, tests/fixtures, CI workflows, scripts, package entry points,
   generated-file recipes, agent skills, TODO items, source audits and documentation links.
   Check indirect/shared helpers and externally documented operator procedures. If a dependency
   or intended future invocation remains, retain or replace it before retiring the file.
3. **Preserve lasting knowledge.** Transfer accepted semantics, source discrepancies, unresolved
   decisions, reproducibility requirements and current procedures to their canonical owners.
   Keep stable finding IDs and source-version/hash evidence that an open reconciliation relies on.
   A large frozen baseline can remain tracked while it is needed for acceptance, but it must be
   labeled historical rather than maintained current state.
4. **Choose the smallest safe disposition:**
   - **Retain** if the command/audit is active, a reusable validator, an imported helper, the
     canonical generator, or necessary to satisfy an open release/validation/source gate.
   - **Extract and replace** if a one-use entry point contains reusable logic: move that logic to
     a maintained module, update its consumers/tests and then retire only the obsolete wrapper.
   - **Move evidence to `local/provenance/`** if unique raw findings, private inputs, recovery
     material or replay instructions justify a local copy. Record source revision, purpose and
     limits of the evidence. Since `local/` is ignored, such copies are **not shared Git
     provenance** and cannot be required by a clean checkout.
   - **Delete from the tracked tree** if the work is complete, references are cleared and
     its content is already recoverable from Git history or canonical records. Do not copy
     every obsolete script into `local/` by default; that would create a second archive.
5. **Close out atomically.** Remove or replace stale command examples, links and imports in
   the same change. State the retired paths, disposition, acceptance/replacement evidence and
   any local-only archive location in the commit message or canonical closeout. Run relevant
   dependency tests and the `docs` stage (including link checks), inspect the full diff and
   confirm the intended release/CI path does not depend on ignored material. Respect the
   [VD/VR queue](validation-queue.md) for deferred test work; never equate retirement with
   acceptance of an unrelated pending gate.

A one-use audit **report** follows the same procedure: first reconcile its actionable findings
with `TODO.md`, `official-source-clarifications.md` or other appropriate owners; then delete the
superseded narrative or preserve only genuinely unique evidence. Audit findings are not closed
merely because a newer report exists. Do not rewrite or discard immutable upstream snapshots,
license/provenance obligations, or reviewed historical evidence required by the
[data lifecycle](../data/README.md). Prefer explicit retention with a reason over uncertain loss.

## Planning and history

- `TODO.md` — only work that is still unimplemented or intentionally deferred.
- [workflow-improvement-review-2026-11-04.md](workflow-improvement-review-2026-11-04.md) — dated review of task, validation, CI and tooling workflow improvements; recommendations, not an active task ledger.
- `CHANGELOG.md` — concise release outcomes and upgrade consequences.
- `AI_CONTEXT.md` — compact agent-oriented index of non-obvious current invariants and pointers to
  canonical documentation. It is not a second architecture or data-model specification.

### Backlog completion and retirement

**Project domain:** Project infrastructure

`TODO.md` is an active backlog. A checked task means that its stated outcome and
**every descendant task** are complete, required acceptance checks have passed,
and the documentation handoff is done. A checked parent must never contain open
or deferred work. Implementation alone does not complete a task whose required
validation remains in the [validation queue](validation-queue.md). A bounded task
can close while a separate, explicitly owned final release gate remains open;
do not relabel unfinished descendants as separate gates merely to close a parent.

**Freeze before merging a release candidate:** The active development TODO
must be reconciled before the final planned merge. Keep merge approval,
exact-main-SHA hosted CI, tagging, authorized deployment and post-deployment
verification in the canonical [release checklist](releasing.md), not as open
development tasks whose later retirement requires a second merge. When an
existing V1S entry concerns only those external release operations, transfer
it explicitly to the runbook with its former ID, exact remaining obligation,
approval dependency and evidence requirement; cite the IDs and this handoff
in the transfer commit. **Transfer is not completion** and never waives a
release gate. CI or deployment failures requiring tracked fixes reopen
development and require a corrected release candidate instead of pretending
the earlier merge is final.

When correcting or extending an existing task, reopen it and every checked
ancestor **before** editing its scope or adding subtasks. If genuinely new scope
arises after completion, create a separate open task referring to the delivered
capability; do not append work beneath a checked entry. Checkmarks are never
progress indicators for partially delivered tasks.

Complete the handoff at the same time as the work:

1. Record the practical outcome in the canonical behavior/design documentation.
   Add or consolidate meaningful player/operator outcomes under `Unreleased` in
   [the changelog](CHANGELOG.md); internal-only test, refactor or process work
   needs no release-note entry, with that decision stated in the handoff.
2. Remove a completed standalone task or completed parent and its whole subtree.
   A completed subtask whose immediate parent is still open may instead become
   a brief, plain context note under that parent, only when the remaining work
   needs it. Keep one or two outcome sentences and a canonical documentation
   link; remove the checked item and its implementation history.
3. Rewrite the open parent's scope around what remains. Preserve dependencies,
   unresolved source questions and required acceptance gates. Keep validation
   obligations in the validation queue, source evidence in its maintained owner,
   and run logs, hashes and intermediate counts out of TODO.

Apply this to subtasks at every depth during each change's closeout, not only at
release preparation. Git history retains retired details; do not create another
completed-task archive or append new status reports to completed entries.

**Make retirement auditable:** when removing numbered `V1S-*` entries, include
*every retired ID* in the same Git commit's subject or body (for example,
`task-closeout: v1s-055, v1s-056`). The commit must also contain or link to
the actual acceptance evidence in its canonical documentation, or identify the
exact verified tests/revision. This convention makes removal distinguishable
from accidental omission without keeping checked items in the active backlog.
Do not retire an open implementation or ruling requirement just because its
bounded source review or related focused test passed; explicitly retain and
re-scope the remainder under its existing task or correct independent owner.

Before beginning the next task, reconcile the just-worked task and any touched
parent against `TODO.md`, the [VD/VR queue](validation-queue.md), current
documentation and the inspected diff. Retire fully finished work **in that
closeout commit**; leave partial/blocked work unchecked with a concrete
remaining action or dependency. For autonomous work selection, follow the
[V1S checkpoint](TODO.md#v1s-work-selection-and-handoff); numeric gaps alone
are not evidence of skipped or completed work.

## Private local workspace

`local/` is Git-ignored and excluded from Docker build contexts. Use it for private audit evidence,
server-specific operational notes, command output, screenshots, diagnostics, and other untracked
material. For example, `local/audits/` and `local/operations/` can hold private findings without
placing them in public project documentation.

Existing ignored locations such as `docs/audits/` and `reports/` remain supported for compatibility.
New private operational evidence should be kept under `local/`. No build, test, CI, runtime, or
release step may depend on its contents.

A normal audit therefore has three steps:

1. collect private evidence under `local/`;
2. correct and validate code, data, or documentation as needed; and
3. publish only generalized, reviewed product contracts or development tasks in tracked files.

Git ignore rules and Docker context exclusions are publication safeguards, not encryption or access
controls. Protect local file permissions and review staging, archives, and diffs before publication.
