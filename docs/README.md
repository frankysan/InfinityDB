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
- [its-season-database.md](its-season-database.md) — ITS Season 17/18 schema,
  season-source binding, builder and selected publication contract.
- [season-publication-ownership.md](season-publication-ownership.md) — current
  N5/FAQ/ITS authority boundary, cross-domain references and version selection.
- `application-domains.md` — canonical player-facing domain ownership and publication capabilities.
- `web-design-guidelines.md` — target browser design and language contract, including reusable
  surfaces, tables, controls, responsive behavior, typography, accessibility, and theming. It states
  requirements and design direction rather than claiming every current surface already complies.
- `project-domains.md` — engineering ownership labels used by planning and release notes.
- `../data/README.md` — external inputs, generated artifacts, snapshot provenance, and publication
  lifecycle.
- `../data/curated/README.md` — authored/curated data schemas and review contracts.
- [testing.md](testing.md) — local validation workflow, check runner, test
  selection, host and asset policies, and index/preflight checks.
- [testing-data.md](testing-data.md) — runtime database and source validation,
  publication audits, and the release-tracked FAQ parity procedure.
- [testing-browser.md](testing-browser.md) — focused browser verification,
  manual visual and accessibility checks, and served-candidate acceptance.
- [testing-performance.md](testing-performance.md) — runtime benchmarks,
  test concurrency and host-capacity measurements supporting current decisions.
  Historical results validate only their recorded revisions; superseded runs
  remain in [Git history](testing.md#historical-validation-evidence).
- [multi-agent-workspaces.md](multi-agent-workspaces.md) — legacy optional coordination
  contract, currently branch-pinned to `dev/v1.0.0` in its implementing tools.
  It must be adapted before use on the current branch; ordinary work does not
  require it.
- `validation-queue.md` — active register for genuinely deferred test design
  or execution (owner, prerequisites, resumption trigger and outcome); no
  mandatory per-edit entries or numeric thresholds.
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

## Diagram notation

Prefer fenced `mermaid` blocks for charts, graphs and diagrams in Markdown
documentation when Mermaid can clearly express the content. Use this for
architecture flows, dependency graphs and similar relationships instead of
ASCII art, keeping labels readable in both source and rendered form.

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
- `rules-interaction-checklist.md` — generated cross-release interaction-review ledger. Regenerate
  it with `tools/data/audit_rules_interactions.py`; do not edit it manually. Its release labels record the
  original review/defer decision and are evidence provenance, not the active roadmap; use `TODO.md`
  for current milestone planning.

Other retained, **bounded source/implementation evidence** has a distinct
purpose: the [FAQ v0.1 applicability inventory](faq-v0.1-scope-inventory.md)
pins reviewed question and scope decisions. It is not a second backlog,
release checklist or current schema owner; consult the [data model](data-model.md),
[data lifecycle](../data/README.md), and
[source clarification register](official-source-clarifications.md) for
maintained behavior.

The completed 1.0 source-coverage audit and four rules-explanation audit files
were retired to Git history at the `add2280` baseline. A compact 367-record
identity fixture remains under `config/validation/` for the actively used
baseline comparison. Use the maintained source-history, clarification and
semantic registers for current meaning.

Completed audit/closeout documents are **not** permanent reference documentation by default. Once
an audit closes, move lasting contracts into the canonical owner above, record user/operator-visible
outcomes in `CHANGELOG.md`, and let Git history preserve the detailed narrative. Keep a tracked audit
only when it contains unique rationale that still guides active work.

## One-use tool and audit lifecycle

**Project domain:** Project infrastructure

Use this policy for bounded tools, plans, reports, audits and generated
evidence. A name such as `stage_*`, `promote_*` or `audit_*`, or an old
version/date, is not proof that the item is disposable. Prefer a maintained
existing command when the operation will recur.

At creation, identify the domain, owner, purpose, expected artifacts,
source/revision scope and completion or retirement trigger. Categorize
temporary output in ignored `local/`; do not make builds, CI, runtime
or release procedures depend on private execution logs.

At task closeout, a deliberate cleanup or an accepted publication:

1. **Confirm independent purpose and consumers.** Check the owning task,
   current imports/entry points, tests, CI, packaging, source readers,
   operator procedures and links. Historical-only tests or obsolete
   staging dependencies do not justify retaining an obsolete implementation.
   Preserve tests of continuing source, parity, compatibility and
   deterministic-publication invariants when replacing their old producer.
2. **Preserve lasting meaning.** Transfer accepted semantics,
   source discrepancies, unresolved work, supported procedures and
   reproducibility requirements to their canonical
   [documentation owners](#canonical-current-state-documents). Keep
   stable source identities, revisions, hashes and reviewed provenance
   needed by open research or publication acceptance.
3. **Choose the smallest useful disposition:**
   - **Retain** actively supported operations, open research or unique
     source/acceptance evidence in their appropriate tracked owner.
   - **Extract and replace** reusable validators/parsers or current
     policy embedded in a one-use wrapper or historical narrative.
   - **Rename/relocate** still-useful material whose path obscures its
     purpose, preserving source identity and updating consumers together.
   - **Retire** superseded tracked tools, plans, reports and audits to
     Git history after transferring any open findings and removing
     obsolete entry points, tests and links. Do not create a second
     `archive/` or completed-task registry in the tracked tree.
   - **Preserve private evidence** in categorized `local/` only when
     unique research, recovery, source or legal/provenance needs justify
     retention. Ignored copies cannot replace shared Git-backed evidence.
4. **Validate the change proportionally.** Run checks for surviving
   behavior, the documentation/link stage, and Git diff/consumer review.
   State retired paths, preserved evidence and remaining dependencies in
   the commit or canonical closeout. Use the
   [validation queue](validation-queue.md) only for genuinely deferred tests.

Do not silently delete immutable upstream inputs, published artifacts,
source-referenced files, backups or unique ignored/private evidence.
Uncertain deletion requires separate review and authorization; age,
filename or a completed producer task is insufficient.

Tool and workspace cleanup completed on 2026-11-14. The detailed historical
execution record remains in Git history; current conventions belong to
[architecture](architecture.md#accepted-workspace-conventions-prospective-not-a-path-migration)
and the [data lifecycle](../data/README.md#accepted-ignored-artifact-policy-prospective).

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

**Freeze before merging a release candidate:** The active development TODO
must be reconciled before the final planned merge. Keep merge approval,
final-main hosted CI evidence, tagging, authorized deployment and post-deployment
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
   Add or consolidate meaningful player/operator outcomes in
   [the changelog](CHANGELOG.md) under the branch's
   [pending target release](releasing.md#between-releases); internal-only test, refactor or process work
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

When a change modifies a tracked backlog task, reconcile the affected subtree
at closeout rather than postponing it to release preparation. Unrelated edits
do not require full-backlog or historical-V1S review. Git history retains
retired details; do not create a second completed-task archive.

**Make retirement auditable:** when removing numbered `V1S-*` entries, include
*every retired ID* in the same Git commit's subject or body (for example,
`task-closeout: v1s-055, v1s-056`). The commit must also contain or link to
the actual acceptance evidence in its canonical documentation, or identify the
exact verified tests/revision. This convention makes removal distinguishable
from accidental omission without keeping checked items in the active backlog.
Do not retire an open implementation or ruling requirement just because its
bounded source review or related focused test passed; explicitly retain and
re-scope the remainder under its existing task or correct independent owner.

For a completed backlog item, reconcile its affected parent with the actual
diff, required acceptance and any concrete [deferred checks](validation-queue.md).
Retire finished work in that commit; leave incomplete work open with a specific
remaining dependency. Invoke the [V1S checkpoint](testing.md#v1s-backlog-checks)
only for reopened numbered V1S work. Do not turn routine unrelated development
into an administrative full-backlog or queue review.

Current `TODO.md` checkboxes are checked by the existing docs stage:
duplicate **leading, explicitly supplied** task IDs and open descendants
of checked parents are errors; IDs are optional. When the worktree changes
or a Git base is supplied, removed open tasks produce advisory `BKL003`
warnings. Unnumbered descriptions are matched conservatively so ordinary
rewrites are less likely to trigger false alarms. A warning asks the
maintainer to verify completion, supersession or transfer using the same
commit and canonical evidence; it is not a separate acceptance gate.

The Git-based `TODO.md` workflow remains the sole task register. Defer
GitHub Issues/Projects unless concrete cross-repository coordination,
dependency tracking or agent handoff problems justify the additional
overhead; do not create a parallel register or automatic status sync.

## Private local workspace

`local/` is Git-ignored and excluded from Docker build contexts. Use it for private audit evidence,
server-specific operational notes, command output, screenshots, diagnostics, and other untracked
material. For example, `local/audits/` and `local/operations/` can hold private findings without
placing them in public project documentation.

Historical evidence previously written to `docs/audits/` or root `reports/`
belongs under `local/archive/` or a categorized `local/` report directory.
No build, test, CI, runtime, or release step may depend on private evidence.

A normal audit therefore has three steps:

1. collect private evidence under `local/`;
2. correct and validate code, data, or documentation as needed; and
3. publish only generalized, reviewed product contracts or development tasks in tracked files.

Git ignore rules and Docker context exclusions are publication safeguards, not encryption or access
controls. Protect local file permissions and review staging, archives, and diffs before publication.
