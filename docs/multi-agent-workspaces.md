# Multi-agent workspace and integration protocol

**Project domain:** Project infrastructure

This is the canonical contract for InfinityDB's **optional, explicitly enabled**
coordination system for ChatGPT/MCP, VS Code Copilot, terminal agents and human
developers. It is independent of the interface used to edit files. When enabled,
this protocol supplements Git and the
[development validation workflow](testing.md#phased-development-and-validation);
it does not change [deferred-check ownership](validation-queue.md#queue-rules)
or the release gate.

## Activation and default workflow

**Default: this coordination system is not enabled.** Agents use the ordinary
authorized checkout, validation, commit and safe fast-forward publication
workflow. Automated task claims, registry access, workspace identity guards,
client upgrades and a designated integration leader are not prerequisites for
ordinary work. Concurrent work still requires agreed edit boundaries and
serialized Git operations; preserve other agents' files, branches and running
validation jobs.

Enable this protocol only when the user explicitly requests its use for a
defined scope. The remaining checkout-role and registry requirements in this
document apply only to that scope. Neither the presence of multiple agents,
existing claims/worktrees, an earlier task's activation nor discussion or
development of these tools enables it for new work. Generic requests to
continue InfinityDB development do not authorize adoption or further development
of this optional infrastructure.

For work resuming after the mandatory rollout, preserve each existing proposal
and checkout assignment. An existing registry entry does not require an agent
to repair or upgrade the coordination client before ordinary work can resume;
the user's opt-out instruction takes precedence over older checkout instructions.
Review the actual Git state and hand off or integrate the proposal using the
ordinary authorized workflow, respecting other active work. Do not require a
merge solely to refresh the coordination CLI. Leave old claims and registry
history intact unless their owners explicitly release them or the user requests
an inspected cleanup. Opting out does not authorize discarding another agent's
work, deleting reservations or silently synchronizing another checkout.

The CLI commands remain available and keep their fail-closed checks when
explicitly invoked. They do not install Git hooks or automatically gate normal
Git commands. Do not weaken their guards to implement the default workflow;
ordinary work does not invoke them.

## Checkout roles

- **Primary checkout (one per machine):** the named, stable checkout used for
  synchronization, inspection and controlled integration. On Windows this is
  the existing `InfinityDB/`; on the interactive Linux VM it is
  `/home/infinitydb/InfinityDB/`. These are different repositories and are
  not automatically mirrored. **Only the designated Windows integration
  owner may advance and publish `dev/v1.0.0`.** A Linux primary is not a
  second integration authority.
- **Development checkout (one per concurrent writer):** a unique checkout and
  Git branch for an assigned agent/task. An agent edits, stages and commits
  *only in its own checkout*, and never stages, commits, checks out branches
  or pushes from a primary checkout. A contributor may work on multiple tasks
  sequentially in one development checkout, but simultaneous writers get
  different checkouts.
- **Validation checkout:** the existing MCP worker checkout at
  `/srv/mcp-worker/workspaces/InfinityDB/` is reserved for pinned runs.
  This is **not** the interactive Linux primary. Its HEAD and relevant
  inputs must remain unchanged while a job runs.

The single integration owner may be another specifically delegated agent. That
is a **role**, not a requirement to use MCP. Two agents must never both
assume they hold the role. A primary checkout is not a shared scratchpad.

## Creating a development checkout

For trusted agents on one machine, use distinct **Git worktrees**. They
have independent working files and indexes but share Git objects and refs.
Agents with unrestricted Git commands still can affect shared metadata;
use **independent clones** for less-trusted agents or when that shared
metadata is unacceptable. Neither layout is an OS security boundary.

From a **clean** primary checkout on `dev/v1.0.0`:

Windows PowerShell:

```powershell
.\.venv\Scripts\python.exe -m tools.agent_workspaces create --agent copilot-01 --task v1s-082 --machine windows
cd ..\InfinityDB-agent-windows-copilot-01-v1s-082
py -3 -m tools.agent_workspaces guard --agent copilot-01 --task v1s-082
```

Linux:

```sh
./.venv/bin/python -m tools.agent_workspaces create --agent codex-01 --task v1s-083 --machine devbox
cd ../InfinityDB-agent-devbox-codex-01-v1s-083
python3 -m tools.agent_workspaces guard --agent codex-01 --task v1s-083
```

The helper creates a sibling `InfinityDB-agent-<machine>-<agent>-<task>/`
worktree and unique `agent/<machine>/<agent>/<task>` branch from an
**explicitly recorded HEAD SHA**. It refuses a dirty, detached or unexpected
primary branch, duplicate branch/destination and an agent checkout as source.
It never fetches, resets, switches the primary branch, stages, commits or
pushes. The agent worktree contains an ignored
`local/agent-workspace.json` marker; `guard` checks the agent, task and
current branch before local changes.

The marker is a **mistake-prevention check**, not an access-control mechanism,
cross-host lease or proof of exclusive task ownership. Agents using other
editors or terminal commands must still obey this protocol. A full clone
created by another mechanism must have an explicitly assigned owner and scope;
do not claim that `guard` validates such a checkout.

Every worktree needs its own `.venv`, `node_modules`, generated databases,
reports, caches and test output, as applicable. Do not hardlink mutable files
between workspaces: hardlinks share underlying content and can bypass
checkout isolation. Activate optional Syncthing/source inputs explicitly and
record their identity for test evidence. Read-only immutable inputs may be
shared only when the underlying execution cannot modify them.

## Local coordination CLI (Phase 2, single-machine scope)

The portable `tools.agent_coordination` module provides durable **local**
claims shared by all worktrees using the *same Git common directory*.
It uses an OS-exclusive file lock for every read-modify-write transaction,
writes state atomically, never expires or steals ownership automatically,
and refuses invalid state. This is a cooperative safety layer for direct-file,
IDE and MCP agents alike, **not** a credential or OS permission boundary.
Other clones, other machines and unrelated Git object stores do not share it.

An assigned development agent runs from its worktree (with its own Python
environment available):

```powershell
python -m tools.agent_coordination claim --agent chatgpt --task workspace-bootstrap --path tools/ --path tests/
python -m tools.agent_coordination status
```

The first command returns an opaque, non-secret claim ID. Before a handoff,
check the active claim and full changed-file scope, then explicitly release
it after the integrator has received the proposal:

```powershell
python -m tools.agent_coordination check --agent chatgpt --task workspace-bootstrap --claim-id <claim-id>
python -m tools.agent_coordination release --agent chatgpt --task workspace-bootstrap --claim-id <claim-id>
```

Development claims refuse duplicate task ownership, one agent worktree
claiming twice, overlapping exact-file/directory scopes, and protected
integration-owned TODO/VD/VR and publication paths. A claim does not grant
permission to write files outside its declared scope. Register it **before**
editing; revise changed file scope by releasing and taking a new claim only
after inspecting the checkout. Scope checking examines committed/uncommitted
tracked differences from the recorded baseline plus non-ignored new files.
State is kept outside worktree files at
`<git-common-dir>/infinitydb-agent-coordination/state.json`, **never
Git-tracked or automatically synchronized**.

On the designated primary, the integration owner may acquire an exclusive
*local* integration reservation pinned to an exact SHA:

```powershell
python -m tools.agent_coordination acquire-integration --owner integrator --expected-head <40-character-sha>
python -m tools.agent_coordination check-integration --owner integrator --claim-id <claim-id> --expected-head <40-character-sha>
python -m tools.agent_coordination release-integration --owner integrator --claim-id <claim-id>
```

Once an agent's proposal is **committed and its scope verified**, the designated
integration owner can operate from that agent's worktree without changing
its branch. The `--primary` option resolves the locally registered primary
checkout through Git's common directory:

```powershell
python -m tools.agent_coordination acquire-integration --primary --owner integrator --expected-head <primary-sha>
python -m tools.agent_coordination integrate-proposal --agent chatgpt --task workspace-bootstrap --claim-id <task-claim-id> --owner integrator --integration-id <integration-claim-id> --expected-head <primary-sha> --proposal-head <proposal-sha> --global-claim-id <global-task-id> --global-integration-id <global-integration-id> --global-revision <reviewed-registry-revision>
python -m tools.agent_coordination release-integration --primary --owner integrator --claim-id <integration-claim-id>
```

`integrate-proposal` requires the primary checkout and agent checkout to be
clean, verifies their Git identities and claims, and refuses any changed file
outside the task's scope. It accepts only a local **fast-forward** from the
specified primary HEAD to the exact proposal SHA; hooks are disabled. It
does not push or run tests. If another proposal was integrated first, this
agent must **merge the current primary branch into its own isolated branch**
and resolve conflicts deliberately. The original baseline must remain an
ancestor of the current primary HEAD, and the new proposal commit must include
that primary HEAD. Force updates, rebases, implicit synchronization and
automatic conflict resolution are not part of this operation.

Check active jobs and exclusive integration ownership immediately before the
Git operation. Revalidate the integrated revision and publish it separately
using the existing safe fast-forward push protocol; release the integration
reservation only after the operation and required follow-through are complete.
This is a cooperative, *local* reservation, not an automatic lock over
arbitrary `git` processes. If a process crashes, state remains reserved.
**Stop** and investigate instead of deleting/reassigning the claim.
Bounded inspected integration recovery is described below. Global ownership is enforced for
cooperating integration clients as described below; unrestricted Git writers
remain outside that protection.

**Important limitation:** The local coordinator cannot detect a concurrent
claim on the independent Linux clone or stop an unrestricted external Git
client. Cross-host assignments require the global registry below; local claims
alone do not establish cross-host integration ownership.
Do not run two machine-local integration owners just because each machine
reports its own reservation available. The Windows integration owner alone
owns `dev/v1.0.0`; the global registry does not designate a second owner.

## Cross-machine claims through a dedicated Git ref

`tools.agent_global_coordination` adds a tool-independent global registry
using the configured `origin` remote and the dedicated
`refs/heads/coordination/agent-claims` Git ref. It records only normalized
task IDs, machine/agent names, baselines and repository-relative path scopes;
**never store credentials, absolute paths, private notes, or secrets**.
Metadata on a public Git repository is itself public. Agents do not need MCP.

An authorized Windows integration owner initializes this ref **once**, after
the code is integrated and reviewed:

```powershell
python -m tools.agent_global_coordination bootstrap
python -m tools.agent_global_coordination status
```

On **each machine's assigned agent worktree**, claim local and global scope
before edits. Both commands require explicit invocation; neither fetches,
merges or modifies the source checkout:

```powershell
python -m tools.agent_coordination claim --agent copilot --task v1s-082 --path src/
python -m tools.agent_global_coordination claim --agent copilot --task v1s-082 --path src/
python -m tools.agent_global_coordination check --agent copilot --task v1s-082 --claim-id <global-claim-id>
```

Record both claim IDs separately. Check the **local claim** as well; it verifies
changed-file scope, while the global check verifies cross-machine ownership.
If either claim fails, **do not edit**. Release any successfully created other
claim deliberately after inspecting the checkout. Global claims reject
duplicate tasks, overlapping directory/file scopes and integration-owned
paths across independent Windows/Linux clones. Path comparisons are
conservatively case-insensitive. The registry never expires ownership
automatically, and is unavailable if `origin` cannot be reached.

Before integration, the designated primary owner additionally reserves
global integration ownership (alongside the local integration reservation):

```powershell
python -m tools.agent_global_coordination acquire-integration --owner integrator --expected-head <primary-sha>
python -m tools.agent_global_coordination check-integration --owner integrator --claim-id <global-integration-id> --expected-head <primary-sha>
```

Read `status` after acquiring both reservations and pass that exact global
revision, global task ID and global integration ID to `integrate-proposal`.
There is no local-only integration fallback. The command checks both task
identities, equal normalized file scopes, changed paths, local primary HEAD,
exact proposal SHA and origin's `dev/v1.0.0` tip. Stale registry revisions,
missing claims and unavailable registry/source refs refuse integration.

Before the fast-forward, a non-forced metadata update records a unique running
operation pinned to the task claim and proposal. This is stronger than a
read-only preflight: while it is running, cooperating clients refuse **all
registry mutations**, including task or leadership release. Competing begins
cannot both commit against the reviewed registry revision. Read-only status
remains available. Both checkouts are rechecked after network preflight and
after integration; local success is then recorded as completed. Neither source
publication nor reservation release is automatic.

The first operation upgrades both registries to **version 2**. The designated
integration owner schedules this transition and publishes the updated primary.
Older version-1 clients deliberately reject version 2 instead of silently
ignoring the running-operation guard; their coordination writes pause while
existing claims stay held. Each owner must inspect its checkout and explicitly
merge the published primary revision into its own branch before its next
coordination write. No other source checkout is upgraded or synchronized
automatically. Until updated, an older checkout cannot use its bundled
coordination CLI against either registry.

On success, publish using the separately reviewed fast-forward protocol, then
explicitly release both integration reservations before releasing task claims.
Use `release-integration --owner ... --claim-id ...` and
`release --agent ... --task ... --claim-id ...` for the remote registry. An
interruption, failed merge, unexpected checkout mutation or ambiguous remote
result leaves reservations held. A running operation blocks release and new
registry writes until inspected recovery; no timeout expires it. Never edit the
registry manually just to unblock another task.

The local filesystem mutex covers the entire integration operation. The global
running record covers cooperative cross-clone ownership transitions. Neither
is a lock on arbitrary Git commands or on a server-side source ref: a privileged
writer can still move the source branch after a check. Remote HEAD is checked
before pinning and after local integration; a detected race retains unresolved
ownership rather than rolling back or reporting acceptance. This is cooperative
serialization, **not** an authenticated or enforceable cross-host transaction.

Each remote update creates an ordinary descendant commit in the metadata ref
and pushes **without force**. Concurrent pushes that fail fast-forward are
reconciled by fetching and validating the latest metadata revision, then
retrying within a bounded limit. Those operations use a disposable Git
repository; they do not switch branches, pull source files or touch the
working tree's Git index. The code is tested against an independent shared
bare remote. **Do not manually rebase, rewrite, or delete this coordination
ref**, and do not treat a missing or unreachable ref as permission to ignore
existing ownership. If a process fails after its remote update, inspect
`status` from the independent machine before retrying or recovering.

This remains **cooperative coordination**, not an OS permission boundary,
branch protection, or prevention of arbitrary privileged Git commands.
The Windows integration primary is authoritative by project policy; the
remote ref does not cryptographically establish a user's identity. Read-only
MCP status views may be added later, but direct-file agents must be able to
use the CLI without the MCP gateway.

## Assignment and edit boundaries

Before work begins, an integration coordinator assigns a distinct agent,
task ID, workspace, base revision and expected path scope. Check
[TODO](TODO.md#v1s-work-selection-and-handoff) and
[validation queue](validation-queue.md#queue-rules) before assigning a numbered
slice. Avoid two agents implementing the same acceptance target without an
explicit split or agreed dependency. Overlapping expected paths are a
coordination warning; **distinct worktrees prevent accidental shared edits,
not semantic merge conflicts**.

Development agents may independently inspect and edit source files, run
permitted checks and create coherent commits on their own branch. They must
not change the primary checkout, the validation checkout, shared Git branches,
other agents' worktrees or running jobs. Do not run destructive shared-repo
operations (`git gc`, `git worktree prune`, branch deletion, forced updates,
resets or rebases) without a separately reviewed maintenance operation.

The canonical `docs/TODO.md`, `docs/validation-queue.md`, source discrepancy
registers and release publications remain **single-owner integration files**.
An implementation agent submits its proposed task/VD/VR amendments and
evidence with the change handoff; the integration owner applies and reconciles
the canonical registers in one integration operation. Do not let multiple
agents independently allocate VD/VR IDs or retire the same V1S ID.

## Submission and serialized integration

An agent hands off: task and scope, agent branch and base SHA, changed-file
list and commit SHA(s), checks actually run and their exact result,
unverified VD/VR obligations, and any conflict or source ambiguity.
A worktree commit is a **proposal**, not an accepted `dev/v1.0.0` revision.

The single integration owner serially:

1. Verifies the primary checkout branch, HEAD, worktree status and exclusive
   integration ownership. Stop if that ownership is uncertain or unrelated
   dirty changes appear; never assume an unlocked checkout is idle.
2. Compares the proposal's baseline and complete diff with current
   `dev/v1.0.0`; checks overlapping files, generated outputs, dependencies
   and applicable license/provenance conditions. Explicitly re-review any
   changes since the proposal was prepared.
3. Integrates **only** approved task-related changes using ordinary Git,
   resolving conflicts deliberately; never sweep the entire shared working
   tree into a commit. Reconcile TODO, VD/VR, documentation and required
   acceptance evidence in the same batch, preserving unchanged user work.
4. Runs immediate safety/static checks and any due VD/VR stages according to
   existing policy, then commits and safely fast-forward pushes the branch.
   Record the exact integrated SHA. A development branch's checks do not
   automatically validate the integrated revision.
5. Explicitly updates the separate Linux validation checkout when the queue
   requires it; pin jobs to the intended SHA and leave the tested checkout
   untouched while they run. Follow CI and release acceptance independently.

No agent may merge, cherry-pick, fast-forward or push the shared branch merely
because its own proposal passed tests. There is **no automatic cross-machine
Git synchronization**. A cross-machine handoff requires explicitly authorized
branch transfer or a reviewed patch, not silent copying of a checkout.

## Inspected integration recovery

`tools.agent_coordination` provides a bounded recovery path for an interrupted
integration with its original identities and reservations still present. It
does not recover abandoned task claims or transfer ownership between agents.
The designated integration owner first inspects affected jobs through their
actual execution interfaces, including MCP jobs and direct terminal processes,
and confirms no writer or pinned validation job is using either checkout.
An elapsed timeout is not evidence that a job stopped. Inspect both checkouts,
their branches, HEADs, index, working files, remote source tip and both registries.

From the original owned proposal checkout, request a read-only receipt:

```powershell
python -m tools.agent_coordination inspect-integration --agent chatgpt --task workspace-bootstrap --claim-id <local-task-id> --owner integrator --integration-id <local-integration-id> --expected-head <before-sha> --proposal-head <proposal-sha> --global-claim-id <global-task-id> --global-integration-id <global-integration-id>
```

Review the returned local/global revisions, source HEADs, scope, changed paths,
proposed outcome and `inspection` digest. The command refuses dirty or changed
checkouts, mismatched identities/scopes, missing ownership, unavailable remote
state and unrelated source revisions. It permits only an unchanged pre-integration
primary, or the exact proposed commit already integrated. A published source tip
equal to that exact proposal can reconcile an uncertain earlier source push;
an unrelated newer tip requires separate investigation.

After inspecting jobs and confirming they are idle, settle metadata explicitly:

```powershell
python -m tools.agent_coordination recover-integration --agent chatgpt --task workspace-bootstrap --claim-id <local-task-id> --owner integrator --integration-id <local-integration-id> --expected-head <before-sha> --proposal-head <proposal-sha> --global-claim-id <global-task-id> --global-integration-id <global-integration-id> --inspection <reviewed-digest> --jobs-inspected
```

`--jobs-inspected` is the caller's explicit idle-job attestation; this portable
CLI cannot discover every process or remote job, and does not represent that
attestation as automated process verification. Recovery repeats the inspection
under the local mutex and requires the same receipt, then uses a pinned remote
metadata update. Changed local/global revisions, source state or receipt refuse
the write. A second caller cannot consume the same receipt successfully.

Recovery changes **only coordination metadata**. It reports `integrated` or
`not-integrated`, marks the operation `completed` with that explicit `outcome`,
and retains all task claims and both integration reservations. Here `completed`
means the operation has been settled; read its outcome before claiming that Git
integration happened. No fast-forward, push, reset, rebase, file restoration,
claim release or ownership transfer is performed. After a verified integration,
perform any still-required publication separately, then release reservations
explicitly. For a non-integrated result, release the settled reservations before
acquiring fresh ones for a reviewed retry; retain task claims while work continues.

If the recovery's own remote response or local state write is interrupted,
inspect again. A fresh receipt can reconcile matching completed remote metadata
with an unresolved local operation. An unknown branch movement, lost task claim,
missing reservation, dirty checkout or unavailable remote remains a blocker.
Do not delete or rewrite state merely to unblock a second agent.

For a disconnected owner or task transfer, first preserve the proposal and
inspect jobs, both Git states, remote ancestry and claims. Record the intended
successor, scope and exact handoff revision. The current owner may explicitly
release its claims only after that inspection and handoff; the successor uses a
new owned checkout and fresh claims. If the original owner cannot participate,
stop for an explicitly delegated maintainer recovery. The tooling does not
implement claim stealing, automatic expiry or absent-owner reassignment.

## Failure, recovery and current enforcement limits

If the integration owner is interrupted, another agent must inspect primary
HEAD, index, working tree, branch, remote ancestry and running jobs **before**
taking over. Never expire a claim and assume the repository is safe to overwrite.
If two proposed patches conflict, keep both original workspaces intact and
resolve the conflict under the integration owner. An in-flight test result
belongs only to its pinned revision and actual inputs.

**Implemented:** this maintained contract, `tools.agent_workspaces`
create/guard, the local-Git-store `tools.agent_coordination` claim/integration
CLI and focused isolation/concurrency tests. These are usable without MCP.
**Implemented:** global cross-host claim and integration reservations via a
dedicated fast-forward-only Git ref, and mandatory dual-registry integration
preflight with a durable version-2 running-operation guard, and inspected
integration-metadata recovery with preserved reservations. Bootstrap remains
an explicit one-time operation for each new origin.
MCP named checkout recognition is implemented for local pytest and non-test
checks; it is not the authority for direct-file agents. **Not yet implemented:**
OS-level restrictions on arbitrary Git processes, abandoned-task recovery and
ownership transfer tooling, comprehensive MCP Git operation routing, worktree cleanup automation,
and a consolidated status monitor. Existing Git hooks and advisory claims
cannot prevent a fully privileged direct-shell agent from bypassing policy.
Use independent workspaces and one designated integration owner throughout.
