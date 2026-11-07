# Agent instructions

This file contains repository-wide instructions for coding agents working on
InfinityDB.

After reading this file, also read root-level `AGENTS.local.md` when it exists.
That optional companion is intentionally Git-ignored and is reserved for
user-specific workflow, communication, tooling, and machine-local preferences.
It must not define project architecture, data semantics, repository-wide
constraints, or durable decisions that other contributors need. Tracked
repository instructions and documentation take precedence if the local file
conflicts with them. Promote a local preference into tracked project
documentation only when the user explicitly wants it to become project policy.

Before making substantial changes, consult `docs/README.md` to identify the
canonical owner, then inspect the affected source, tests and **relevant sections**
of that owner's documentation. Use targeted searches/line ranges rather than
rereading entire large documents or historical acceptance logs at every task
boundary. Consult `docs/architecture.md` and `docs/data-model.md` for the
invariants affected by a code/data change, `docs/testing.md` for applicable
validation procedures, and `docs/project-domains.md` plus `docs/releasing.md`
for planning/release decisions. `docs/AI_CONTEXT.md` is an optional navigation
index, not an additional required full-document read. Broaden the reading scope
when dependencies or changed contracts warrant it; never skip a relevant rule.

For browser visual, layout, responsive, interaction, or player-facing copy changes, also read
`docs/web-design-guidelines.md`; it defines the target UI vocabulary, language, and reusable
design contract.

The engineering principles in `docs/architecture.md` are authoritative for
technical design decisions. Preserve the v1.0 reference baseline defined by the
[release citation gate](docs/releasing.md#version-10-data-completeness-gate):
at least **one applicable current source** per in-scope rule and a usable
browser reference; exhaustive source inventories and discrepancy hunts are
not required.

## Tooling and validation

Use the project's virtual environment (normally
`.venv\\Scripts\\python.exe` on Windows or `.venv/bin/python` on
Linux/macOS), not system Python. The [testing guide](docs/testing.md)
owns `tools/run_checks.py` stages, profiles, asset policy, setup,
test dispatch, reports and preflight requirements. Use its current
commands rather than maintaining a second command reference here.
Use the [read-only development status](docs/testing.md#read-only-development-status)
for a compact task-boundary snapshot when useful; it does not replace the
V1S selection gate, VD/VR rules or exact-SHA CI acceptance.

### Backlog work selection and closeout

For autonomous work, apply the [V1S selection checkpoint](docs/TODO.md#v1s-work-selection-and-handoff).
**Invoke the explicit selection gate** from the [testing guide](docs/testing.md#v1s-backlog-checks)
before starting a numbered slice; inspect all earlier open IDs, documented
blocked/deferred reasons and any exact TODO-recorded user-priority override.
Do not use a free-form override argument to bypass earlier work.
Before retiring a V1S entry, run the Git-aware closeout check for the proposed
staged index and cite the removed ID in the eventual commit. The historical
audit requires a deliberate, documented baseline; it does not approve
semantic completion. At every task boundary apply the
[backlog retirement contract](docs/README.md#backlog-completion-and-retirement):
reconcile the worked task and parent against actual evidence and VD/VR
obligations; retire complete work in the same change, leave actionable
incomplete work open, and record removed V1S IDs in its commit.

### Phased validation and task-boundary checkpoint

The [active VD/VR queue](docs/validation-queue.md#queue-rules) is the sole
authority for design/execution thresholds, drain order, due dates, linked
dependencies, and retirement evidence. **Check it before ordinary
implementation, at every task boundary, and at closeout**. Design due VD
tests without running them; batch compatible VR executions while reconciling
each due VR separately.
Register concrete missing regression designs and each distinct changed
behavior's deferred execution before reporting an implementation complete.
Report counts, oldest due/blocked entry, and intended execution host.
Do not call unrun tests passed or claim a task accepted while its required
validation is pending.

The [testing guide](docs/testing.md#focused-first-vr-execution)
requires risk-based **focused-first** test execution, including impacted
cross-layer invariants, and owns immediate safety exceptions and reports.
A VD/VR threshold alone does not require a full suite.
Its [Linux dispatch protocol](docs/testing.md#parallel-windows-development-and-linux-validation)
owns explicit safe Git preparation, pinned asynchronous test execution,
input/artifact verification and the narrowly scoped Windows-development
exception while a full Linux suite is **actually running**. Hosted
[CI](docs/ci.md#agent-ci-monitoring-and-repair) and
[release acceptance](docs/releasing.md) remain independent. Never use a
partial Linux run or job dispatch as permission to bypass a due drain.

## Optional multi-agent coordination

Use the ordinary authorized Git workflow by default. The
[multi-agent coordination protocol](docs/multi-agent-workspaces.md#activation-and-default-workflow)
is **opt-in for an explicitly requested scope**: use it only when the user
explicitly asks to run that work with the coordination system. Multiple agents,
existing worktrees or registry claims, and work on the coordination tools do
not activate it. Do not require registry access, claim acquisition, an ownership
guard, client upgrades or an integration-leader designation for ordinary work.

Preserve existing assignments and unrelated changes. Concurrent writers must
agree on separate working trees or non-overlapping work and serialize Git
operations against a shared checkout. Never modify another agent's checkout or
move a validation checkout while its pinned jobs are running. When the user
explicitly enables coordinated mode, its checkout roles, claims, guards and
designated integration owner apply within that scope.

## Repository access and change delivery

- Check whether the agent has authorized direct access to the current local
  checkout before relying on uploaded archives or remote repository content.
  A connected filesystem/terminal is a normal working tree, regardless of which
  agent uses it. Do not assume local access is unavailable based on an earlier
  session or workflow.
- When direct access is available, inspect the actual branch, HEAD, working-tree
  status, relevant files, and existing local instructions first. Treat that
  checkout as the source of truth; use remote Git services only for information
  that cannot be established locally or for explicitly requested remote work.
- Edit and validate directly in the authorized working tree, preserving any
  existing checkout assignment and concurrent work. Preserve unrelated
  tracked and untracked changes. Do not require a repository ZIP or produce an
  apply-yourself patch as the primary delivery when the files are already edited.
  Generate a Git-native patch only when requested or needed for transfer/review.
- When direct access is unavailable, request an appropriate repository snapshot
  or use an authorized remote-read workflow; validate any proposed patch against
  its actual base before claiming applicability. Do not infer current local
  state from a stale archive or a remote branch alone.
- After local edits, inspect the actual diff and status and run relevant
  focused checks. For InfinityDB's authorized autonomous workflow, stage
  only reviewed task-related files and commit a coherent validated batch with
  a lowercase conventional message, then safely fast-forward push the authorized
  branch after reviewing its remote tip and ancestry. **Only in explicitly
  enabled coordinated mode**, development checkout owners hand off committed
  proposals and the designated integration owner publishes the shared branch.
  Report each SHA and exact validation
  outcomes, and proceed to the next clearly identifiable open task only when
  the validation queue and workspace assignment permit it. Do not commit failed
  or uncertain changes as accepted, fold unrelated user edits into the
  commit, force-push, reset, rebase, deploy, or publish a release without
  separate authorization. A pushed revision is not automatically a
  validated Linux or CI revision.
- Keep machine-specific configuration, operational diagnostics, and private
  evidence out of tracked files. The Git-ignored `local/` workspace is the
  preferred location for private notes; ignore rules alone are not access
  controls. Review the public diff and generated artifacts for accidental
  disclosures before delivery.

## Repository rules

- Support Windows, Linux, and macOS. Do not introduce machine-specific absolute
  paths or assume a particular shell.
- Preserve raw upstream inputs; transformations belong in separate working or
  generated outputs.
- Do not silently discard ambiguous, unresolved, or source-specific information.
- Keep source-format, database, HTTP, browser, and deployment concerns in their
  established layers. Classify durable work using the canonical project domains in
  `docs/project-domains.md`.
- For an application domain with a stable canonical slug, treat numeric IDs and
  domain-local slugs as interchangeable lookup forms. Application-facing calls should
  accept either; generated links, browser state, API references, and human-authored
  configuration should prefer the slug. Keep numeric compatibility/fallback, and reuse
  the domain's central resolver instead of creating consumer-specific slug logic.
- Normal builds and tests must not unexpectedly require network access.
- Do not redistribute third-party data or assets unless their licensing permits
  it; see `THIRD_PARTY_NOTICES.md`.
- Prefer validated configuration for project-specific aliases, mappings,
  filters, overrides, exceptions, and other maintained domain knowledge rather
  than burying that knowledge in implementation code. Generated manifests are
  for provenance/build state, not maintained policy.
- Do not add a JavaScript build step unless a clear requirement justifies it.

## Repository write safety

When modifying the repository through a remote Git/GitHub API rather than a
normal local working tree:

- Read the target branch tip immediately before starting any write sequence and
  use that exact commit as the expected base.
- Prepare and review the complete intended change set before creating Git blobs,
  trees, or commits. Do not use repository object creation as scratch staging.
- Prefer a direct file-update operation for a single-file change. For a
  multi-file atomic change, create blobs/tree/commit only after every replacement
  is ready, then move the branch ref once with a non-forced fast-forward update.
- Never report a change as committed merely because blobs, trees, or a commit
  object were created. A change is on the branch only after the branch ref has
  been updated successfully.
- Immediately after a write sequence, re-read the branch tip and inspect the
  resulting commit/diff or changed-file set. Confirm that only the intended
  files changed before reporting success.
- If a tool call fails, stalls, or the user interrupts a write sequence, stop
  making writes and re-read the branch tip before continuing. Explicitly state
  whether the branch changed; unattached Git objects do not count as repository
  changes.
- Do not force-update a branch unless the user explicitly requests history
  rewriting or a previously agreed recovery requires it.

## Post-push hosted CI follow-through

Follow the [CI monitoring and repair protocol](docs/ci.md#agent-ci-monitoring-and-repair)
after authorized pushes: record the exact SHA and available runs, inspect
statuses at task boundaries rather than waiting for each run, and
autonomously repair actionable repository failures with a focused,
validated and safely pushed fix. Do not treat local success, incomplete
CI or an older commit's result as hosted acceptance. External,
source-authority or unsafe-Git blockers require explicit escalation;
actual merge/release gates still require terminal results.

## Documentation and project tracking

Follow the [documentation map and ownership rules](docs/README.md).
Update the canonical current-state owner for changed behavior, with
planned or unimplemented contracts clearly labelled. The
[backlog](docs/TODO.md) owns unfinished work and its V1S selection rules;
[retirement](docs/README.md#backlog-completion-and-retirement) requires
the corresponding acceptance evidence and same-change closeout.
Use the [release-note writing rules](docs/releasing.md#3-prepare-release-notes-and-metadata)
for substantive user/operator outcomes; do not add entries for
internal-only tests, refactors or process updates.

Review the actual diff for documentation impact, update public
`README.md` for user-visible capabilities or setup, and use canonical
[project-domain labels](docs/project-domains.md) for new/revised
documentation. An actual release requires the complete
[release and project-wide documentation audit](docs/releasing.md).
Apply the [one-use tool and audit retirement policy](docs/README.md#one-use-tool-and-audit-lifecycle)
at bounded task closeout: check imports, tests, workflow/CLI consumers and
release obligations before retiring transient scripts or dated audit reports.
Do not duplicate active task lists, reference semantics or operational
instructions in agent guidance.

## Source-reference safeguards

For rules/Army/FAQ/Wiki source reconciliation, use the
[source-reconciliation skill](.agents/skills/infinity-source-reconciliation/SKILL.md),
the [N5 source-history policy](docs/n5-source-history.md), and the
[curated explanation contract](data/curated/README.md#explaining-rules-interactions).
Preserve exact source version, provenance, scope and uncertainty. Research
PDFs/Wiki archives are not implicitly Army pipeline inputs; consult
[data lifecycle ownership](data/README.md). Do not bulk-reproduce
copyrighted text or artwork or silently promote an inferred interpretation
into a verified rule.
