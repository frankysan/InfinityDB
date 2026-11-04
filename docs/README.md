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
- `testing.md` — local validation entry points, phased validation policy, test slices,
  asset modes, reports, and benchmark tooling.
- `validation-queue.md` — the active VD/VR register for deferred test design and
  execution, with strict five-item drain-to-zero triggers and evidence; not an implementation backlog.
- `ci.md` — hosted CI workflows and repository-level validation policy.
- `deployment.md` — production install/update/rollback/operations contract.
- `server-migration.md` — moving released or development environments between hosts.
- [syncthing-assets.md](syncthing-assets.md) — private Windows-to-Linux ignored-source staging,
  verification, and explicit checkout activation.
- `releasing.md` — mandatory release gate and the 1.0 completeness definition.

When two documents appear to overlap, prefer the owner above. Correct the owner first, then reduce
secondary text to a link or short boundary statement.

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
  evidence for active v1.0 source omissions and reproducible audit/test defects.
  It preserves the current-input triage and explains why catalog/page-citation
  counts do not certify whole-source coverage. Retain while these findings guide
  unresolved work; `TODO.md` owns their open tasks, not this assessment.
- [rules-explanation-audit-1.0.md](rules-explanation-audit-1.0.md) — dated
  source/interaction assessment with implementation follow-ups and remaining
  source conflicts. Its linked inventory, N5.3 reconciliation and source manifest
  retain unique finding IDs, exact source hashes/revisions and unresolved
  publication discrepancies; they remain **frozen baseline evidence**, not a
  current defects list or proof of 1.0 completion. Keep these linked appendices
  until the final source reconciliation and citation migration is accepted;
  use `TODO.md` for current work and `rules-semantics.md` for reviewed meaning.
- `rules-interaction-checklist.md` — generated cross-release interaction-review ledger. Regenerate
  it with `tools/audit_rules_interactions.py`; do not edit it manually. Its release labels record the
  original review/defer decision and are evidence provenance, not the active roadmap; use `TODO.md`
  for current milestone planning.

Completed audit/closeout documents are **not** permanent reference documentation by default. Once
an audit closes, move lasting contracts into the canonical owner above, record user/operator-visible
outcomes in `CHANGELOG.md`, and let Git history preserve the detailed narrative. Keep a tracked audit
only when it contains unique rationale that still guides active work.

## Planning and history

- `TODO.md` — only work that is still unimplemented or intentionally deferred.
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
