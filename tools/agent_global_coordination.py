"""Cross-machine cooperative task claims backed by a fast-forward-only Git ref.

Independent Windows/Linux checkouts coordinate through origin, not MCP. The
coordination ref contains only non-secret identifiers and path scopes; it does
not contain source files and never alters the caller's HEAD or working tree.
No force-push, lease expiration, remote checkout, or implicit source sync.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from tools.agent_coordination import _PROTECTED, CoordinationError, _overlaps, _scope
from tools.agent_workspaces import WorkspaceError, guard

REF = "refs/heads/coordination/agent-claims"
STATE_FILE = "claims.json"
_SHA = re.compile(r"[0-9a-f]{40}\Z")
_ID = re.compile(r"[0-9a-f]{32}\Z")
_TOKEN = re.compile(r"[a-z0-9][a-z0-9-]{0,39}\Z")
_MAX_RETRIES = 5


class GlobalClaimError(ValueError):
    """Global claim operation refused or could not safely complete."""


def _git(
    directory: Path, *args: str, input_text: str | None = None,
) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        ["git", "-C", str(directory), *args],
        input=input_text.encode("utf-8") if input_text is not None else None,
        capture_output=True, check=False, timeout=45,
        env={**os.environ, "GIT_TERMINAL_PROMPT": "0"},
    )
    return subprocess.CompletedProcess(
        result.args, result.returncode,
        result.stdout.decode("utf-8", errors="replace"),
        result.stderr.decode("utf-8", errors="replace"),
    )


def _require(result: subprocess.CompletedProcess[str], label: str) -> str:
    if result.returncode != 0:
        raise GlobalClaimError(f"Git {label} failed; remote registry unchanged or unverified")
    return result.stdout.strip()


def _checkout(root: Path) -> Path:
    root = root.resolve(strict=True)
    resolved = _require(_git(root, "rev-parse", "--show-toplevel"), "checkout inspection")
    if Path(resolved).resolve() != root:
        raise GlobalClaimError("Run from the root of an explicit Git checkout")
    return root


def _token(value: object, label: str) -> str:
    if not isinstance(value, str) or not _TOKEN.fullmatch(value):
        raise GlobalClaimError(f"Invalid {label}")
    return value


def _validate(state: object) -> dict:
    if not isinstance(state, dict) or state.get("version") not in (1, 2):
        raise GlobalClaimError("Unsupported coordination registry version")
    if type(state.get("revision")) is not int or state["revision"] < 0:
        raise GlobalClaimError("Invalid coordination registry revision")
    claims = state.get("claims")
    if not isinstance(claims, dict) or not (
        state.get("integration") is None or isinstance(state["integration"], dict)
    ):
        raise GlobalClaimError("Invalid coordination registry structure")
    for ident, item in claims.items():
        if not isinstance(ident, str) or not _ID.fullmatch(ident) or not isinstance(item, dict):
            raise GlobalClaimError("Invalid global claim")
        if item.get("id") != ident:
            raise GlobalClaimError("Global claim ID mismatch")
        for name in ("machine", "agent", "task"):
            _token(item.get(name), name)
        if not isinstance(item.get("branch"), str) or not item["branch"]:
            raise GlobalClaimError("Invalid claim branch")
        if not isinstance(item.get("baseline"), str) or not _SHA.fullmatch(item["baseline"]):
            raise GlobalClaimError("Invalid claim baseline")
        paths = item.get("scope")
        if not isinstance(paths, list) or not paths:
            raise GlobalClaimError("Invalid claim scope")
        try:
            if paths != sorted(set(_scope(path).casefold() for path in paths)):
                raise GlobalClaimError("Claim scope is not normalized")
            if item["branch"] != f"agent/{item['machine']}/{item['agent']}/{item['task']}":
                raise GlobalClaimError("Global claim branch identity mismatch")
        except CoordinationError as exc:
            raise GlobalClaimError("Invalid claim scope") from exc
    integration = state["integration"]
    if integration is not None:
        if not isinstance(integration.get("id"), str) or not _ID.fullmatch(integration["id"]):
            raise GlobalClaimError("Invalid global integration ID")
        _token(integration.get("owner"), "owner")
        _token(integration.get("machine"), "machine")
        if not isinstance(integration.get("expected_head"), str) or not _SHA.fullmatch(
            integration["expected_head"]
        ):
            raise GlobalClaimError("Invalid global integration revision")
        operation = integration.get("operation")
        if operation is not None:
            if state["version"] != 2 or not isinstance(operation, dict):
                raise GlobalClaimError("Invalid integration operation")
            if (
                not isinstance(operation.get("id"), str)
                or not _ID.fullmatch(operation["id"])
                or operation.get("phase") not in ("running", "completed")
                or not isinstance(operation.get("proposal_head"), str)
                or not _SHA.fullmatch(operation["proposal_head"])
                or operation.get("task_claim") not in claims
            ):
                raise GlobalClaimError("Invalid integration operation identity")
    return state


def _read(remote: Path) -> tuple[str | None, dict | None]:
    # Use an isolated disposable bare repository, not a worktree's shared FETCH_HEAD.
    listing = _git(remote, "ls-remote", "--exit-code", "origin", REF)
    if listing.returncode == 2:
        return None, None
    output = _require(listing, "coordination lookup")
    fields = output.split()
    if len(fields) != 2 or not _SHA.fullmatch(fields[0]) or fields[1] != REF:
        raise GlobalClaimError("Invalid coordination ref response")
    _require(_git(remote, "fetch", "--no-tags", "origin", REF), "coordination fetch")
    sha = _require(
        _git(remote, "rev-parse", "--verify", "FETCH_HEAD^{commit}"),
        "commit inspection",
    )
    if sha != fields[0]:
        raise GlobalClaimError("Coordination ref changed between lookup and fetch")
    tree = _require(_git(remote, "ls-tree", sha), "tree inspection")
    entries = tree.splitlines()
    fields_tree = entries[0].split("\t", 1) if len(entries) == 1 else []
    if (
        len(fields_tree) != 2
        or not re.fullmatch(r"100644 blob [0-9a-f]{40}", fields_tree[0])
        or fields_tree[1] != STATE_FILE
    ):
        raise GlobalClaimError("Coordination commit must contain only claims.json")
    blob_sha = fields_tree[0].split()[2]
    contents = _require(_git(remote, "cat-file", "blob", blob_sha), "state read")
    try:
        state = _validate(json.loads(contents))
    except (ValueError, TypeError) as exc:
        raise GlobalClaimError("Remote registry is invalid; refusing all mutations") from exc
    return sha, state


def _write(remote: Path, parent: str | None, state: dict, message: str) -> bool:
    content = json.dumps(state, indent=2, sort_keys=True) + "\n"
    blob = _require(_git(remote, "hash-object", "-w", "--stdin", input_text=content), "blob write")
    tree = _require(
        _git(remote, "mktree", input_text=f"100644 blob {blob}\t{STATE_FILE}\n"),
        "tree write",
    )
    command = ["-c", "user.name=InfinityDB Coordination", "-c",
               "user.email=coordination@users.noreply.github.com",
               "commit-tree", tree]
    if parent:
        command.extend(("-p", parent))
    command.extend(("-m", message))
    commit = _require(_git(remote, *command), "commit creation")
    if not _SHA.fullmatch(commit):
        raise GlobalClaimError("Invalid generated coordination commit")
    # Deliberately omit '+' and all force flags. A competing writer must
    # cause a non-fast-forward rejection, after which the caller rereads.
    pushed = _git(remote, "push", "--porcelain", "origin", f"{commit}:{REF}")
    if pushed.returncode == 0:
        return True
    error = (pushed.stdout + pushed.stderr).lower()
    if any(reason in error for reason in (
        "non-fast-forward", "fetch first", "stale info", "cannot lock ref",
    )):
        return False
    raise GlobalClaimError("Coordination push rejected; inspect remote access or branch policy")


def _operation(
    root: Path, action, *, initialize: bool = False, finish_integration: bool = False,
) -> dict:
    root = _checkout(root)
    origin = _require(_git(root, "remote", "get-url", "origin"), "origin lookup")
    if not origin or "\n" in origin:
        raise GlobalClaimError("Invalid origin")
    with tempfile.TemporaryDirectory(prefix="infinitydb-global-claims-") as temp:
        remote = Path(temp) / "registry.git"
        _require(_git(Path(temp), "init", "-q", "--bare", str(remote)), "scratch creation")
        _require(_git(remote, "remote", "add", "origin", origin), "scratch remote")
        for _ in range(_MAX_RETRIES):
            parent, state = _read(remote)
            if state is None:
                if not initialize:
                    raise GlobalClaimError("Global registry is not initialized")
                state = {"version": 1, "revision": 0, "claims": {}, "integration": None}
            active = (state["integration"] or {}).get("operation", {})
            if active.get("phase") == "running" and not finish_integration:
                raise GlobalClaimError(
                    "Integration operation is unresolved; inspect state before recovery",
                )
            result = action(state)
            if result is None:
                return {"revision": state["revision"], "status": "unchanged"}
            state["revision"] += 1
            if _write(remote, parent, state, result["message"]):
                return {"revision": state["revision"], **result["payload"]}
        raise GlobalClaimError("Concurrent global claims prevented update; retry explicitly")


def bootstrap(root: Path) -> dict:
    root = _checkout(root)
    if root.name != "InfinityDB":
        raise GlobalClaimError("Global registry bootstrap requires the designated primary")
    if _require(_git(root, "symbolic-ref", "--short", "HEAD"), "branch") != "dev/v1.0.0":
        raise GlobalClaimError("Primary is not on dev/v1.0.0")
    def action(state: dict) -> dict | None:
        if state["revision"] or state["claims"] or state["integration"] is not None:
            return None
        return {"message": "chore: initialize agent coordination registry",
                "payload": {"status": "initialized"}}
    return _operation(root, action, initialize=True)


def status(root: Path) -> dict:
    root = _checkout(root)
    origin = _require(_git(root, "remote", "get-url", "origin"), "origin lookup")
    with tempfile.TemporaryDirectory(prefix="infinitydb-global-status-") as temp:
        remote = Path(temp) / "registry.git"
        _require(_git(Path(temp), "init", "-q", "--bare", str(remote)), "scratch creation")
        _require(_git(remote, "remote", "add", "origin", origin), "scratch remote")
        _, state = _read(remote)
    if state is None:
        return {"status": "uninitialized", "scope": "origin-only"}
    return {
        "status": "available", "scope": "origin-only",
        "version": state["version"],
        "revision": state["revision"],
        "claims": list(state["claims"].values()), "integration": state["integration"],
    }


def claim(root: Path, agent: str, task: str, paths: list[str]) -> dict:
    root = _checkout(root)
    current = guard(root, agent, task)
    if not paths:
        raise GlobalClaimError("Explicit path scopes required")
    # Conservative cross-platform comparison: Windows file paths are
    # case-insensitive even when Linux checks out the same Git objects.
    scope = sorted(set(_scope(path).casefold() for path in paths))
    if any(_overlaps(path, reserved) for path in scope for reserved in _PROTECTED):
        raise GlobalClaimError("Integration-owned path cannot be globally claimed")
    machine = current["branch"].split("/")[1]
    _token(machine, "machine")
    claim_id = uuid4().hex

    def action(state: dict) -> dict:
        if any(
            existing["task"] == task
            or existing["branch"] == current["branch"]
            or any(_overlaps(a, b) for a in scope for b in existing["scope"])
            for existing in state["claims"].values()
        ):
            raise GlobalClaimError("Global task, branch or file scope already claimed")
        entry = {
            "id": claim_id, "agent": agent, "task": task, "machine": machine,
            "branch": current["branch"], "baseline": current["baseline"],
            "scope": scope, "created_utc": datetime.now(UTC).isoformat(timespec="seconds"),
        }
        state["claims"][claim_id] = entry
        return {"message": "chore: claim agent work scope", "payload": entry}
    return _operation(root, action)


def check(root: Path, agent: str, task: str, claim_id: str) -> dict:
    """Verify a remote task claim is still held by this specific local agent."""
    root = _checkout(root)
    current = guard(root, agent, task)
    if not _ID.fullmatch(claim_id):
        raise GlobalClaimError("Invalid global claim ID")
    entries = status(root).get("claims", [])
    entry = next((item for item in entries if item["id"] == claim_id), None)
    if (
        entry is None or entry["agent"] != agent or entry["task"] != task
        or entry["branch"] != current["branch"]
        or entry["baseline"] != current["baseline"]
    ):
        raise GlobalClaimError("Global task claim has changed or is missing")
    return {"status": "valid", "claim": claim_id, "scope": entry["scope"]}


def release(root: Path, agent: str, task: str, claim_id: str) -> dict:
    root = _checkout(root)
    current = guard(root, agent, task)
    if not _ID.fullmatch(claim_id):
        raise GlobalClaimError("Invalid global claim ID")
    def action(state: dict) -> dict:
        if (state["integration"] or {}).get("operation", {}).get("task_claim") == claim_id:
            raise GlobalClaimError("Release integration before releasing its task claim")
        entry = state["claims"].get(claim_id)
        if not entry or any((
            entry["agent"] != agent, entry["task"] != task,
            entry["branch"] != current["branch"], entry["baseline"] != current["baseline"],
        )):
            raise GlobalClaimError("Global claim is missing or owned by another agent")
        del state["claims"][claim_id]
        return {"message": "chore: release agent work scope",
                "payload": {"released": claim_id}}
    return _operation(root, action)


def _source_head(root: Path, expected_head: str) -> None:
    """Read origin's source tip without updating any local ref or FETCH_HEAD."""
    if source_head(root) != expected_head:
        raise GlobalClaimError("Remote source HEAD differs from expected primary HEAD")


def source_head(root: Path) -> str:
    """Inspect the source ref without fetching or changing source Git state."""
    output = _require(
        _git(root, "ls-remote", "--exit-code", "origin", "refs/heads/dev/v1.0.0"),
        "source HEAD lookup",
    )
    fields = output.split()
    if (len(fields) != 2 or not _SHA.fullmatch(fields[0])
            or fields[1] != "refs/heads/dev/v1.0.0"):
        raise GlobalClaimError("Invalid remote source HEAD response")
    return fields[0]


def _recover_integration(root: Path, inspection: dict) -> dict:
    """CAS settlement used only after the local inspection/idle-job guard."""
    def action(state: dict) -> dict:
        lease = state["integration"]
        if (
            state["revision"] != inspection["global_revision"]
            or not lease or lease["id"] != inspection["global_integration"]
            or lease["owner"] != inspection["owner"]
            or lease["expected_head"] != inspection["expected_head"]
            or lease.get("operation") != inspection["global_operation"]
            or inspection["global_claim"] not in state["claims"]
        ):
            raise GlobalClaimError("Recovery registry changed; inspect again")
        _source_head(root, inspection["remote_source_head"])
        operation = dict(lease.get("operation") or {
            "id": uuid4().hex, "proposal_head": inspection["proposal_head"],
            "task_claim": inspection["global_claim"],
        })
        operation.update(
            phase="completed", outcome=inspection["outcome"],
            recovered_utc=datetime.now(UTC).isoformat(timespec="seconds"),
        )
        state["version"] = 2
        lease["operation"] = operation
        return {"message": "chore: settle inspected integration operation",
                "payload": {"operation": operation}}

    return _operation(root, action, finish_integration=True)


def begin_integration(
    root: Path, agent: str, task: str, claim_id: str, *, owner: str,
    integration_id: str, expected_head: str, proposal_head: str,
    expected_revision: int, scope: list[str], paths: list[str],
) -> dict:
    """Pin ownership durably before local Git mutation; never release on failure.

    Version 2 makes older clients refuse mutations instead of ignoring the
    in-flight operation. All cooperative registry writes freeze until completion.
    """
    current = guard(root, agent, task)
    if (
        type(expected_revision) is not int or expected_revision < 0
        or not _SHA.fullmatch(expected_head) or not _SHA.fullmatch(proposal_head)
        or current["head"] != proposal_head
    ):
        raise GlobalClaimError("Invalid integration revision or proposal HEAD")
    operation = {"id": uuid4().hex, "phase": "running",
                 "proposal_head": proposal_head, "task_claim": claim_id}

    def action(state: dict) -> dict:
        if state["revision"] != expected_revision:
            raise GlobalClaimError("Global registry revision differs; inspect before retrying")
        lease = state["integration"]
        entry = state["claims"].get(claim_id)
        if (
            not lease or lease["id"] != integration_id or lease["owner"] != owner
            or lease["expected_head"] != expected_head or lease.get("operation")
        ):
            raise GlobalClaimError("Global integration reservation changed or missing")
        if (
            not entry or entry["agent"] != agent or entry["task"] != task
            or entry["branch"] != current["branch"]
            or entry["baseline"] != current["baseline"]
            or entry["scope"] != sorted(set(path.casefold() for path in scope))
            or any(not any(_overlaps(path.casefold(), allowed) for allowed in entry["scope"])
                   for path in paths)
        ):
            raise GlobalClaimError("Global task ownership or file scope differs")
        _source_head(root, expected_head)
        state["version"] = 2
        lease["operation"] = operation
        return {"message": "chore: pin integration operation",
                "payload": {"operation": operation}}

    return _operation(root, action)


def finish_integration(
    root: Path, owner: str, integration_id: str, operation_id: str,
    expected_revision: int,
) -> dict:
    """Record a verified local success; reservations remain explicitly held."""
    def action(state: dict) -> dict:
        lease = state["integration"]
        operation = (lease or {}).get("operation", {})
        if (
            state["revision"] != expected_revision
            or not lease or lease["owner"] != owner or lease["id"] != integration_id
            or operation.get("id") != operation_id or operation.get("phase") != "running"
        ):
            raise GlobalClaimError("In-flight integration changed; inspect before recovery")
        if (
            root.name != "InfinityDB"
            or _require(_git(root, "symbolic-ref", "--short", "HEAD"), "branch") != "dev/v1.0.0"
            or _require(_git(root, "rev-parse", "HEAD"), "HEAD") != operation["proposal_head"]
            or _require(_git(root, "status", "--porcelain"), "status")
        ):
            raise GlobalClaimError("Integrated primary state differs; inspect before recovery")
        _source_head(root, lease["expected_head"])
        operation["phase"] = "completed"
        return {"message": "chore: confirm local integration",
                "payload": {"operation": operation}}

    return _operation(root, action, finish_integration=True)


def acquire_integration(root: Path, owner: str, expected_head: str) -> dict:
    root = _checkout(root)
    owner = _token(owner, "owner")
    if root.name != "InfinityDB" or not _SHA.fullmatch(expected_head):
        raise GlobalClaimError("Integration requires primary checkout and exact HEAD")
    if _require(_git(root, "symbolic-ref", "--short", "HEAD"), "branch") != "dev/v1.0.0":
        raise GlobalClaimError("Integration requires dev/v1.0.0")
    if _require(_git(root, "rev-parse", "HEAD"), "HEAD") != expected_head:
        raise GlobalClaimError("Primary HEAD mismatch")
    if _require(_git(root, "status", "--porcelain"), "status"):
        raise GlobalClaimError("Primary checkout is dirty")
    ident = uuid4().hex
    def action(state: dict) -> dict:
        if state["integration"] is not None:
            raise GlobalClaimError("Global integration already reserved")
        entry = {"id": ident, "owner": owner, "machine": "windows",
                 "expected_head": expected_head,
                 "created_utc": datetime.now(UTC).isoformat(timespec="seconds")}
        state["integration"] = entry
        return {"message": "chore: reserve integration ownership", "payload": entry}
    return _operation(root, action)


def check_integration(root: Path, owner: str, claim_id: str, expected_head: str) -> dict:
    """Read a global reservation without refreshing or changing source refs."""
    root = _checkout(root)
    owner = _token(owner, "owner")
    if not _ID.fullmatch(claim_id) or not _SHA.fullmatch(expected_head):
        raise GlobalClaimError("Invalid global integration identity")
    entry = status(root).get("integration")
    if (
        entry is None or entry["owner"] != owner or entry["id"] != claim_id
        or entry["expected_head"] != expected_head
    ):
        raise GlobalClaimError("Global integration reservation changed or missing")
    return {"status": "valid", "integration": claim_id, "expected_head": expected_head}


def release_integration(root: Path, owner: str, claim_id: str) -> dict:
    root = _checkout(root)
    owner = _token(owner, "owner")
    if root.name != "InfinityDB" or not _ID.fullmatch(claim_id):
        raise GlobalClaimError("Integration release requires primary and reservation ID")
    def action(state: dict) -> dict:
        entry = state["integration"]
        if not entry or entry["owner"] != owner or entry["id"] != claim_id:
            raise GlobalClaimError("Global integration reservation mismatch")
        state["integration"] = None
        return {"message": "chore: release integration reservation",
                "payload": {"released": claim_id}}
    return _operation(root, action)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="operation", required=True)
    sub.add_parser("status")
    sub.add_parser("bootstrap")
    c = sub.add_parser("claim")
    c.add_argument("--agent", required=True)
    c.add_argument("--task", required=True)
    c.add_argument("--path", action="append", required=True, dest="paths")
    for operation in ("check", "release"):
        entry = sub.add_parser(operation)
        entry.add_argument("--agent", required=True)
        entry.add_argument("--task", required=True)
        entry.add_argument("--claim-id", required=True)
    integration = sub.add_parser("acquire-integration")
    integration.add_argument("--owner", required=True)
    integration.add_argument("--expected-head", required=True)
    for operation in ("check-integration", "release-integration"):
        entry = sub.add_parser(operation)
        entry.add_argument("--owner", required=True)
        entry.add_argument("--claim-id", required=True)
        if operation == "check-integration":
            entry.add_argument("--expected-head", required=True)
    args = parser.parse_args(argv)
    try:
        root = Path.cwd()
        if args.operation == "status":
            result = status(root)
        elif args.operation == "bootstrap":
            result = bootstrap(root)
        elif args.operation == "claim":
            result = claim(root, args.agent, args.task, args.paths)
        elif args.operation == "check":
            result = check(root, args.agent, args.task, args.claim_id)
        elif args.operation == "release":
            result = release(root, args.agent, args.task, args.claim_id)
        elif args.operation == "acquire-integration":
            result = acquire_integration(root, args.owner, args.expected_head)
        elif args.operation == "check-integration":
            result = check_integration(root, args.owner, args.claim_id, args.expected_head)
        else:
            result = release_integration(root, args.owner, args.claim_id)
    except (GlobalClaimError, CoordinationError, WorkspaceError,
            OSError, subprocess.TimeoutExpired) as exc:
        parser.exit(2, f"global coordination refused: {exc}\n")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
