# Multi-agent workspace and integration protocol

**Project domain:** Project infrastructure

This is the canonical InfinityDB contract for simultaneous work by ChatGPT/MCP,
VS Code Copilot, terminal agents and human developers. It is independent of the
interface used to edit files. This protocol supplements Git and the
[phased validation workflow](testing.md#phased-development-and-validation);
it does not change the [VD/VR queue's](validation-queue.md#queue-rules)
thresholds or the release gate.

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
python -m tools.agent_coordination integrate-proposal --agent chatgpt --task workspace-bootstrap --claim-id <task-claim-id> --owner integrator --integration-id <integration-claim-id> --expected-head <primary-sha> --proposal-head <proposal-sha>
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
Recovery and a globally enforceable cross-host authority remain unimplemented.

**Important limitation:** The local coordinator cannot detect a concurrent
claim on the independent Linux clone or stop an unrestricted external Git
client. Cross-host assignments still require the integration owner to arbitrate
manually; this is **not** complete Phase 2 integration-leadership enforcement.
Do not run two machine-local integration owners just because each machine
reports its own reservation available. The Windows integration owner alone
owns `dev/v1.0.0` until a global coordination service is implemented.

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
**Not yet implemented:** a durable cross-host
task-claim service, independently enforceable integration lease, protected
command gateway for arbitrary shell clients, automatic conflict checks,
worktree lifecycle/cleanup automation, and MCP named-checkout routing for
every runner/Git operation. Git hooks and advisory leases alone cannot
prevent a fully privileged direct shell agent from bypassing policy.
Use independent workspaces and one deliberately designated integration owner
until those controls are implemented and tested.
