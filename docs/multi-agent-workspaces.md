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

**Implemented in the initial phase:** this maintained contract,
`tools.agent_workspaces create/guard`, and focused tests of worktree safety.
These are usable without MCP. **Not yet implemented:** a durable cross-host
task-claim service, independently enforceable integration lease, protected
command gateway for arbitrary shell clients, automatic conflict checks,
worktree lifecycle/cleanup automation, and MCP named-checkout routing for
every runner/Git operation. Git hooks and advisory leases alone cannot
prevent a fully privileged direct shell agent from bypassing policy.
Use independent workspaces and one deliberately designated integration owner
until those controls are implemented and tested.
