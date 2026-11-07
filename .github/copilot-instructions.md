# GitHub Copilot instructions — InfinityDB

This is the VS Code Copilot entry point, not a second project policy. At the start
of repository work, read and follow the root [`AGENTS.md`](../AGENTS.md),
then the Git-ignored `AGENTS.local.md` when present. Use
[`docs/README.md`](../docs/README.md) to find the canonical owner of any
technical, testing, validation, CI, or release rule. If guidance conflicts,
tracked project policy and its canonical documents take precedence.

## Terminal and remote-work boundaries

- Prefer the authorized, currently open working tree. Inspect its branch,
  HEAD, status, and relevant files before editing. Do not assume another
  machine or checkout has identical contents.
- In a Windows VS Code terminal, use PowerShell for local commands. For
  permitted Linux commands, use an SSH alias explicitly configured in the
  user's **local** instructions; do not invent hosts, usernames, addresses,
  key paths, or authorization. Keep machine-specific details out of tracked
  instructions.
- Use non-interactive SSH for agent commands. Verify remote identity, working
  directory, branch, HEAD, and cleanliness before acting on a remote repo.
  Do not disable host-key verification, echo credentials, or copy secrets
  into chat, logs, or tracked files.
- An interactive Linux checkout reached through SSH is **not** necessarily
  the dedicated MCP `linux-dev` test-worker checkout. Never substitute
  its HEAD or test results for a pinned worker job without verification.
- Windows and Linux Git checkouts are independent. Do not fetch, pull,
  switch branches, reset, rebase, push, copy working-tree files, or move
  generated assets between them merely because SSH is available. Follow
  the explicit, safe handoff and revision-pinning rules in
  [`docs/testing.md`](../docs/testing.md) when validation is due.
- Follow [`docs/validation-queue.md`](../docs/validation-queue.md) at task
  boundaries. Prefer the documented asynchronous MCP Linux worker for due
  long-running tests when available; do not launch competing ad hoc full
  suites over interactive SSH or treat dispatch as acceptance. Work on
  Windows during a Linux suite only within the documented concurrency
  exception.
- Keep terminal command approvals enabled. Request approval for privileged,
  destructive, security-sensitive, or otherwise separately authorized
  operations. Instructions never grant tool permissions by themselves.
- In the handoff, distinguish local and remote commands, exact revisions,
  checks actually run, queued or blocked validation, and files changed.
