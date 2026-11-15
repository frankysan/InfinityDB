---
name: handoff
description: "Create a copy-ready continuation prompt for the current InfinityDB task, targeting a fresh ChatGPT.com chat (chat), VS Code Codex session (codex), or VS Code GitHub Copilot session (copilot). Use for handoffs, session changes, and continuation requests. Read-only: do not perform the next task."
argument-hint: "chat | codex | copilot [optional focus]"
user-invocable: true
---

# Handoff — continue InfinityDB work in another session

Produce **one self-contained, ready-to-paste prompt** that lets the receiving agent resume the **actual current task**, not a generic project overview. This skill only creates the prompt. Do **not** edit files, stage, commit, push, sync checkouts, deploy, launch another session, or perform the next implementation step while preparing a handoff.

## Invocation

- `handoff chat` — fresh conversation on ChatGPT.com.
- `handoff codex` — fresh Codex session inside VS Code with the intended workspace open.
- `handoff copilot` — fresh GitHub Copilot Chat/Agent session inside VS Code with the intended workspace open.
- When supported, use `$handoff codex` in Codex or `/handoff copilot` in Copilot. Natural-language requests such as "hand off to chat" work too; the **argument determines the destination**, not the agent currently generating the prompt.
- An optional focus may select a subtask, failure, workstream, or repository; preserve all still-relevant constraints.

If no destination is stated or unambiguously inferable, ask only: **"Which handoff target: chat, codex, or copilot?"** If the user explicitly requests multiple destinations, generate a separately labeled prompt for each.

## Collect the smallest sufficient context (read-only)

1. **Immediate objective:** identify the user's current task, accepted design decisions, scope, exclusions, key unresolved questions, and **next concrete action** from this conversation. Do not replace ongoing work with an unrelated item from the backlog.
2. **Current state:** identify what has actually been implemented, tested, committed, pushed, or deployed, versus what is only proposed. Record relevant failures, blockers, dependent jobs and last known validation outcomes; do not imply pending checks passed.
3. **Repository state:** when authorized tools are available, briefly verify the relevant repo/worktree, branch, full HEAD, tracked/untracked changes, and (where material) whether commits are pushed. Distinguish Windows, Linux interactive and dedicated worker checkouts. Do not run a broad audit or long validation just for a handoff.
4. **Authoritative pointers:** include the necessary repo-relative paths, relevant `docs/TODO.md` work item, test selectors or commands, source/review records and applicable documentation. In InfinityDB, `AGENTS.md`, any `AGENTS.local.md`, `docs/README.md` and the canonical domain owners define the workflow; `docs/releasing.md` owns actual release gates.
5. **Access boundary:** the receiving agent may not have this conversation, connected tools, saved context, local ignored assets, unstaged changes in another checkout, or an unpushed commit. Record last-known facts accurately and instruct the new session to verify them.

If current verification is unavailable, label the snapshot **"last reported — verify on arrival"**. Never invent hashes, paths, test results, source authority, approvals, or tool access. Exclude credentials, private evidence contents, personal machine paths, large logs, and temporary ChatGPT sandbox references.

## Tailor the prompt to its destination

### `chat` — new ChatGPT.com conversation

- Supply all essential background in the prompt itself. The new chat must not need previous messages to understand the task.
- Name the repository, task, exact last-verified Git state when known, relevant decisions, implementation progress and next action.
- Tell the receiving agent to check connected workspace/repository tools **if available**, then inspect the actual checkout, read `AGENTS.md` and applicable local/project guidance before editing. If direct access is unavailable, disclose that and use available files or request the needed access rather than guessing.
- Do not assume a new chat inherits the same connectors, files, instructions, or authorizations.

### `codex` — new Codex session in VS Code

- Start by directing Codex to work in the **open repository/worktree**, inspect Git branch/HEAD/status, and read `AGENTS.md`, `AGENTS.local.md` if present, and relevant canonical docs/skills.
- Give concrete repo-relative file anchors, next implementation steps, acceptance criteria and focused validation. Keep it executable rather than a generic roadmap.
- Preserve unrelated staged/unstaged/untracked work; distinguish local checkout from `linux-dev` and interactive SSH checkouts. Never assume remote sync, installed tooling or a passed CI result.
- Follow the repository's current Git authorization and release rules; a handoff grants no new permission to reset, rebase, force-push, deploy or publish.

### `copilot` — new GitHub Copilot session in VS Code

- Start by directing Copilot Agent to inspect the **open VS Code workspace** and its Git state, read `AGENTS.md`, `.github/copilot-instructions.md`, `AGENTS.local.md` when present, and the relevant canonical docs/skills.
- Identify the **first bounded action** and specific files/behavior to change, followed by focused tests and stop conditions.
- Prefer PowerShell when giving Windows commands; do not assume Copilot has this chat's connected tools, remote workers, or permissions.
- Preserve unrelated changes and obey existing commit/push permissions; do not silently synchronize machines, deploy, or modify other repositories.

## Output contract

Return the **prompt itself**, preferably as a single fenced `text` block for direct copying. Do not create a handoff file unless the user specifically requests one. Use the user's requested language, otherwise English for InfinityDB development.

Use concise sections where useful:

1. **Continue: [specific task]** — immediate objective and desired outcome.
2. **Verified starting state** — repository, branch, exact SHA, status, environments and freshness qualifiers.
3. **Completed work and accepted decisions** — only facts needed to resume.
4. **Unfinished work and blockers** — distinguish planned, implemented and verified.
5. **Next actions and validation** — ordered coherent work, expected deliverables and meaningful tests.
6. **Working boundaries** — relevant source/Git/release constraints and instructions to consult.

Omit empty headings and duplicated boilerplate. If the task has already finished, say so and distinguish the next agreed follow-up from unfinished work. Begin the prompt with an imperative to **continue the named task**, and end with a concrete **"Start by..."** instruction so the next agent proceeds instead of generating another plan.

Outside the prompt, at most one short sentence may identify the target or a genuine limitation. Never claim that another session was launched or received the handoff.
