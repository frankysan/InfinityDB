"""Check the active V1S execution-slice register in docs/TODO.md."""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTER_HEADING = "pre-planned 1.0 execution slices"
HEADING = re.compile(r"^ {0,3}(?P<marks>#{1,6})\s+(?P<title>.+?)\s*#*\s*$")
FENCE = re.compile(r"^ {0,3}(?P<fence>`{3,}|~{3,})")
LIST_ITEM = re.compile(
    r"^(?P<indent>[ \t]*)(?:[-+*]|\d+[.)])\s+(?P<body>.*)$"
)
CHECKBOX = re.compile(r"^\[(?P<state>[ xX])\](?:\s+(?P<body>.*))?$")
V1S_ID = re.compile(r"V1S-\d{3}")
V1S_PREFIX = re.compile(r"^(?:\*\*)?(?P<token>V1S-[^\s*]*)(?:\*\*)?")
ANNOTATION = re.compile(r"(?:^|\s)(?P<kind>Blocked|Deferred):\s*(?P<detail>.*)$")


@dataclass(frozen=True)
class BacklogTask:
    task_id: str
    checked: bool
    line_start: int
    line_end: int
    parent_task_id: str | None
    parent_lines: tuple[int, ...]
    section_path: tuple[str, ...]
    text: str
    blocked: str | None
    deferred: str | None


@dataclass(frozen=True)
class Diagnostic:
    code: str
    severity: str
    source: str
    line: int
    message: str
    suggestion: str


@dataclass(frozen=True)
class BacklogAnalysis:
    tasks: tuple[BacklogTask, ...]
    diagnostics: tuple[Diagnostic, ...]


@dataclass
class _TaskBuilder:
    task_id: str
    checked: bool
    line_start: int
    line_end: int
    parent_task_id: str | None
    parent_lines: tuple[int, ...]
    section_path: tuple[str, ...]
    text_parts: list[str] = field(default_factory=list)

    def finish(self) -> BacklogTask:
        text = " ".join(part.strip() for part in self.text_parts if part.strip())
        blocked = None
        deferred = None
        for line in text.splitlines():
            match = ANNOTATION.search(line)
            if match:
                if match.group("kind") == "Blocked":
                    blocked = match.group("detail").strip()
                else:
                    deferred = match.group("detail").strip()
        return BacklogTask(
            task_id=self.task_id,
            checked=self.checked,
            line_start=self.line_start,
            line_end=self.line_end,
            parent_task_id=self.parent_task_id,
            parent_lines=self.parent_lines,
            section_path=self.section_path,
            text=text,
            blocked=blocked,
            deferred=deferred,
        )


@dataclass
class _ListNode:
    indent: int
    line: int
    checked: bool | None
    task_id: str | None
    builder: _TaskBuilder | None


def _heading_title(line: str) -> tuple[int, str] | None:
    match = HEADING.match(line)
    if match is None:
        return None
    return len(match.group("marks")), match.group("title").strip().casefold()


def _register_bounds(lines: list[str]) -> tuple[int, int, int, tuple[int, ...]] | None:
    headings: list[tuple[int, int]] = []
    fence_char: str | None = None
    fence_length = 0
    for index, line in enumerate(lines):
        fence_match = FENCE.match(line)
        if fence_match is not None:
            marker = fence_match.group("fence")
            if fence_char is None:
                fence_char = marker[0]
                fence_length = len(marker)
            elif marker[0] == fence_char and len(marker) >= fence_length:
                fence_char = None
            continue
        if fence_char is not None:
            continue
        heading = _heading_title(line)
        if heading is not None and heading[1] == REGISTER_HEADING:
            headings.append((index, heading[0]))

    if not headings:
        return None
    start, level = headings[0]
    end = len(lines)
    fence_char = None
    fence_length = 0
    for index in range(start + 1, len(lines)):
        fence_match = FENCE.match(lines[index])
        if fence_match is not None:
            marker = fence_match.group("fence")
            if fence_char is None:
                fence_char = marker[0]
                fence_length = len(marker)
            elif marker[0] == fence_char and len(marker) >= fence_length:
                fence_char = None
            continue
        if fence_char is not None:
            continue
        if fence_char is None:
            heading = _heading_title(lines[index])
            if heading is not None and heading[0] <= level:
                end = index
                break
    return start, end, level, tuple(index for index, _ in headings)


def _declaration_id(body: str) -> tuple[str | None, str | None]:
    content = body.lstrip()
    if content.startswith("`"):
        return None, None
    if not (content.startswith("V1S-") or content.startswith("**V1S-")):
        return None, None
    match = V1S_PREFIX.match(content)
    if match is None:
        return None, "V1S declaration has no identifier"
    token = match.group("token")
    if not V1S_ID.fullmatch(token):
        return token, f"malformed V1S identifier {token!r}; expected V1S-NNN"
    if content.startswith("**V1S-") and "**" not in content[2:]:
        return token, "bold V1S declaration is missing its closing '**'"
    return token, None


def analyze_backlog(markdown: str, *, source: str = "docs/TODO.md") -> BacklogAnalysis:
    """Parse and validate the designated V1S execution-slice section."""
    lines = markdown.splitlines()
    diagnostics: list[Diagnostic] = []
    bounds = _register_bounds(lines)
    if bounds is None:
        return BacklogAnalysis(
            tasks=(),
            diagnostics=(
                Diagnostic(
                    code="V1B004",
                    severity="error",
                    source=source,
                    line=1,
                    message=f"missing '{REGISTER_HEADING}' section",
                    suggestion="Restore the designated pre-planned 1.0 execution-slice heading.",
                ),
            ),
        )

    start, end, register_level, matching_headings = bounds
    for index in matching_headings[1:]:
        diagnostics.append(
            Diagnostic(
                code="V1B004",
                severity="error",
                source=source,
                line=index + 1,
                message="duplicate pre-planned 1.0 execution-slice section",
                suggestion="Keep one active execution-slice register in docs/TODO.md.",
            )
        )

    tasks: list[_TaskBuilder] = []
    list_stack: list[_ListNode] = []
    seen_ids: set[str] = set()
    register_match = HEADING.match(lines[start])
    assert register_match is not None
    section_stack: list[tuple[int, str]] = [
        (register_level, register_match.group("title").strip())
    ]
    last_node: _ListNode | None = None
    fence_char: str | None = None
    fence_length = 0

    for index in range(start + 1, end):
        line = lines[index]
        line_number = index + 1
        fence_match = FENCE.match(line)
        if fence_match is not None:
            marker = fence_match.group("fence")
            if fence_char is None:
                fence_char = marker[0]
                fence_length = len(marker)
            elif marker[0] == fence_char and len(marker) >= fence_length:
                fence_char = None
            continue
        if fence_char is not None:
            continue

        heading_match = HEADING.match(line)
        if heading_match is not None:
            heading_level = len(heading_match.group("marks"))
            while section_stack and section_stack[-1][0] >= heading_level:
                section_stack.pop()
            section_stack.append((heading_level, heading_match.group("title").strip()))
            list_stack.clear()
            last_node = None
            continue

        item_match = LIST_ITEM.match(line)
        if item_match is not None:
            indent = len(item_match.group("indent").expandtabs(4))
            while list_stack and list_stack[-1].indent >= indent:
                list_stack.pop()
            body = item_match.group("body")
            checkbox_match = CHECKBOX.match(body)
            checked: bool | None = None
            declaration: str | None = None
            declaration_error: str | None = None
            builder: _TaskBuilder | None = None
            if checkbox_match is not None:
                checked = checkbox_match.group("state").casefold() == "x"
                declaration, declaration_error = _declaration_id(
                    checkbox_match.group("body") or ""
                )
                if declaration_error is not None:
                    diagnostics.append(
                        Diagnostic(
                            code="V1B002",
                            severity="error",
                            source=source,
                            line=line_number,
                            message=declaration_error,
                            suggestion=(
                                "Use a complete V1S-NNN identifier at the start "
                                "of the checkbox title."
                            ),
                        )
                    )
                elif declaration is not None:
                    if declaration in seen_ids:
                        diagnostics.append(
                            Diagnostic(
                                code="V1B001",
                                severity="error",
                                source=source,
                                line=line_number,
                                message=f"duplicate active declaration for {declaration}",
                                suggestion="Keep one active declaration for each V1S identifier.",
                            )
                        )
                    seen_ids.add(declaration)
                    parent_task_id = next(
                        (
                            ancestor.task_id
                            for ancestor in reversed(list_stack)
                            if ancestor.task_id is not None
                        ),
                        None,
                    )
                    parent_lines = tuple(ancestor.line for ancestor in list_stack)
                    builder = _TaskBuilder(
                        task_id=declaration,
                        checked=checkbox_match.group("state").casefold() == "x",
                        line_start=line_number,
                        line_end=line_number,
                        parent_task_id=parent_task_id,
                        parent_lines=parent_lines,
                        section_path=tuple(title for _, title in section_stack),
                        text_parts=[checkbox_match.group("body") or ""],
                    )
                    tasks.append(builder)

                if not checked:
                    checked_ancestor = next(
                        (
                            ancestor
                            for ancestor in reversed(list_stack)
                            if ancestor.checked and ancestor.task_id is not None
                        ),
                        None,
                    )
                    if checked_ancestor is not None:
                        diagnostics.append(
                            Diagnostic(
                                code="V1B003",
                                severity="error",
                                source=source,
                                line=line_number,
                                message=(
                                    f"open checkbox is nested under checked "
                                    f"{checked_ancestor.task_id} at line {checked_ancestor.line}"
                                ),
                                suggestion=(
                                    "Reopen the checked V1S parent or complete "
                                    "every descendant."
                                ),
                            )
                        )

            node = _ListNode(
                indent=indent,
                line=line_number,
                checked=checked,
                task_id=declaration if declaration_error is None else None,
                builder=builder,
            )
            list_stack.append(node)
            last_node = node
            continue

        if last_node is None or not line.strip():
            continue
        continuation_indent = len(line) - len(line.lstrip(" \t"))
        if continuation_indent > last_node.indent:
            continuation = line.strip()
            if last_node.builder is not None and continuation:
                last_node.builder.text_parts.append(continuation)
                last_node.builder.line_end = line_number
        elif not line.lstrip().startswith((">", "|")):
            list_stack.clear()
            last_node = None

    return BacklogAnalysis(
        tasks=tuple(task.finish() for task in tasks),
        diagnostics=tuple(sorted(diagnostics, key=lambda item: (item.line, item.code))),
    )


def _git(repository: Path, *arguments: str) -> str:
    """Run a bounded, read-only Git inspection; never invoke a shell."""
    try:
        result = subprocess.run(
            ["git", "-C", str(repository), *arguments],
            capture_output=True, text=True, check=False, timeout=30,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise ValueError(f"unable to inspect Git history: {exc}") from exc
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip()[:300]
        raise ValueError(f"git {arguments[0]} failed: {detail or result.returncode}")
    if len(result.stdout) > 8 * 1024 * 1024:
        raise ValueError("Git inspection output exceeds the 8 MiB limit")
    return result.stdout


def _resolve_commit(repository: Path, revision: str) -> str:
    if not revision.strip():
        raise ValueError("a nonempty Git revision is required")
    return _git(
        repository, "rev-parse", "--verify", "--end-of-options",
        f"{revision}^{{commit}}",
    ).strip()


def _retirement_error(code: str, message: str, suggestion: str) -> Diagnostic:
    return Diagnostic(
        code=code, severity="error", source="docs/TODO.md", line=1,
        message=message, suggestion=suggestion,
    )


def audit_retirements(
    base: str, target: str = "HEAD", *, repository: Path = ROOT,
    enforce: bool = False,
) -> tuple[Diagnostic, ...]:
    """Check removed V1S declarations against their introducing Git commits.

    Default mode is advisory for historical history. Use enforce only against a
    deliberately chosen new-closeout baseline, not arbitrary legacy commits.
    A cited ID and evidence *pointer* never establish semantic acceptance.
    """
    try:
        base_sha = _resolve_commit(repository, base)
        target_sha = _resolve_commit(repository, target)
        try:
            ancestor = subprocess.run(
                ["git", "-C", str(repository), "merge-base", "--is-ancestor",
                 base_sha, target_sha],
                capture_output=True, text=True, check=False, timeout=30,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise ValueError(f"unable to inspect Git ancestry: {exc}") from exc
        if ancestor.returncode == 1:
            return (_retirement_error(
                "V1B008", f"{base} is not an ancestor of {target}",
                "Use a base in the target's history; never infer closeout from a diverged range.",
            ),)
        if ancestor.returncode != 0:
            raise ValueError(
                f"git merge-base failed: {ancestor.stderr.strip()[:300]}"
            )
        first_parent_lineage = _git(
            repository, "rev-list", "--first-parent", target_sha,
        ).splitlines()
        if base_sha not in first_parent_lineage:
            return (_retirement_error(
                "V1B008", f"{base} is not on the first-parent path of {target}",
                "Choose a first-parent baseline; do not attribute merged work "
                "to the wrong commit.",
            ),)
        commits = _git(
            repository, "rev-list", "--reverse", "--first-parent",
            f"{base_sha}..{target_sha}",
        ).splitlines()
        if len(commits) > 500:
            raise ValueError("retirement audit range exceeds 500 commits")
        previous = base_sha
        before = analyze_backlog(
            _git(repository, "show", f"{previous}:docs/TODO.md"),
            source=f"{previous[:12]}:docs/TODO.md",
        )
        if any(d.severity == "error" for d in before.diagnostics):
            raise ValueError("base backlog contains invalid V1S declarations")
        diagnostics: list[Diagnostic] = []
        for commit in commits:
            after = analyze_backlog(
                _git(repository, "show", f"{commit}:docs/TODO.md"),
                source=f"{commit[:12]}:docs/TODO.md",
            )
            if any(d.severity == "error" for d in after.diagnostics):
                raise ValueError(f"invalid V1S declarations in commit {commit[:12]}")
            survivors = {task.task_id for task in after.tasks}
            removed = [
                task for task in before.tasks if task.task_id not in survivors
            ]
            if removed:
                message = _git(repository, "log", "-1", "--format=%B", commit)
                cited = {
                    item.upper()
                    for item in re.findall(r"V1S-\d{3}", message, re.IGNORECASE)
                }
                docs_changed = _git(
                    repository, "diff", "--name-only", previous, commit,
                    "--", "docs/",
                ).splitlines()
                canonical_evidence = any(
                    name not in {"docs/TODO.md", "docs/validation-queue.md"}
                    for name in docs_changed
                )
                message_evidence = bool(re.search(
                    r"(?:docs/[\w./-]+\.md|tests?/test_[\w.]+|"
                    r"acceptance:|evidence:|verified:)",
                    message, re.IGNORECASE,
                ))
                for task in removed:
                    source = f"{previous[:12]}:docs/TODO.md"
                    if task.task_id not in cited:
                        diagnostics.append(Diagnostic(
                            code="V1B005",
                            severity="error" if enforce else "warning",
                            source=source, line=task.line_start,
                            message=(
                                f"{task.task_id} retired in {commit[:12]} "
                                "without an ID reference in that commit message"
                            ),
                            suggestion=(
                                "Include every retired V1S ID in the closeout "
                                "commit subject or body."
                            ),
                        ))
                    if not (canonical_evidence or message_evidence):
                        diagnostics.append(Diagnostic(
                            code="V1B006", severity="warning",
                            source=source, line=task.line_start,
                            message=(
                                f"{task.task_id} retired in {commit[:12]} "
                                "without an apparent acceptance-evidence pointer"
                            ),
                            suggestion=(
                                "Link canonical acceptance documentation or "
                                "identify exact verified tests/revision in the commit."
                            ),
                        ))
            previous, before = commit, after
        return tuple(diagnostics)
    except ValueError as exc:
        return (_retirement_error(
            "V1B007", str(exc),
            "Verify that both revisions exist and docs/TODO.md is valid at each revision.",
        ),)


def audit_pending_retirements(
    *, state: str, repository: Path = ROOT,
) -> tuple[Diagnostic, ...]:
    """Report uncommitted V1S removals without pretending a commit exists."""
    if state not in {"index", "worktree"}:
        raise ValueError("Pending closeout state must be 'index' or 'worktree'")
    try:
        committed = analyze_backlog(
            _git(repository, "show", "HEAD:docs/TODO.md"),
            source="HEAD:docs/TODO.md",
        )
        if state == "index":
            proposed_text = _git(repository, "show", ":docs/TODO.md")
            changed = _git(
                repository, "diff", "--cached", "--name-only", "HEAD", "--", "docs/",
            ).splitlines()
        else:
            destination = repository / "docs" / "TODO.md"
            if destination.stat().st_size > 8 * 1024 * 1024:
                raise ValueError("worktree TODO exceeds the 8 MiB limit")
            proposed_text = destination.read_text(encoding="utf-8")
            changed = _git(
                repository, "diff", "--name-only", "HEAD", "--", "docs/",
            ).splitlines()
        proposed = analyze_backlog(
            proposed_text, source=f"{state}:docs/TODO.md",
        )
        if any(d.severity == "error" for d in (*committed.diagnostics, *proposed.diagnostics)):
            raise ValueError("current or proposed backlog contains invalid V1S declarations")
        survivors = {task.task_id for task in proposed.tasks}
        evidence = any(
            name not in {"docs/TODO.md", "docs/validation-queue.md"}
            for name in changed
        )
        diagnostics: list[Diagnostic] = []
        for task in committed.tasks:
            if task.task_id in survivors:
                continue
            diagnostics.append(Diagnostic(
                code="V1B009", severity="warning",
                source="HEAD:docs/TODO.md", line=task.line_start,
                message=(
                    f"{task.task_id} removed from {state}; no closeout commit exists yet"
                ),
                suggestion=(
                    "Review the retirement evidence and cite this V1S ID in the "
                    "eventual closeout commit, then audit that committed range."
                ),
            ))
            if not evidence:
                diagnostics.append(Diagnostic(
                    code="V1B006", severity="warning",
                    source="HEAD:docs/TODO.md", line=task.line_start,
                    message=(
                        f"{task.task_id} pending retirement has no changed "
                        "canonical documentation evidence pointer"
                    ),
                    suggestion=(
                        "Record acceptance in the owning canonical documentation "
                        "and link the verified selector/revision or no-change review."
                    ),
                ))
        return tuple(diagnostics)
    except (OSError, UnicodeError, ValueError) as exc:
        return (_retirement_error(
            "V1B007", str(exc),
            "Verify the Git index/worktree and the committed docs/TODO.md.",
        ),)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--todo",
        type=Path,
        default=ROOT / "docs" / "TODO.md",
        help="backlog Markdown file to inspect (default: docs/TODO.md)",
    )
    parser.add_argument(
        "--base",
        help="Git base revision for per-commit V1S retirement audit",
    )
    parser.add_argument(
        "--target", default="HEAD",
        help="Git target revision for retirement audit (default: HEAD)",
    )
    parser.add_argument(
        "--target-state", choices=("commit", "index", "worktree"), default="commit",
        help="Audit committed history, staged index, or current worktree",
    )
    parser.add_argument(
        "--enforce-closeout", action="store_true",
        help="Fail on unaccounted retirements after an explicitly chosen base",
    )
    args = parser.parse_args(argv)
    if args.enforce_closeout and not args.base:
        parser.error("--enforce-closeout requires --base")
    if args.target_state != "commit" and (not args.base or args.target != "HEAD"):
        parser.error("index/worktree closeout requires --base and --target HEAD")
    try:
        markdown = args.todo.read_text(encoding="utf-8")
    except OSError as exc:
        print(f"{args.todo}: unable to read backlog: {exc}", file=sys.stderr)
        return 2

    analysis = analyze_backlog(markdown, source=str(args.todo))
    diagnostics = list(analysis.diagnostics)
    if args.base:
        diagnostics.extend(audit_retirements(
            args.base, args.target, enforce=args.enforce_closeout,
        ))
        if args.target_state != "commit":
            diagnostics.extend(audit_pending_retirements(state=args.target_state))
    for diagnostic in diagnostics:
        print(
            f"{diagnostic.source}:{diagnostic.line}: {diagnostic.severity} "
            f"{diagnostic.code}: {diagnostic.message}\n"
            f"  Suggested correction: {diagnostic.suggestion}"
        )
    errors = sum(item.severity == "error" for item in diagnostics)
    warnings = sum(item.severity == "warning" for item in diagnostics)
    if errors:
        print(f"V1S backlog: FAIL ({errors} error(s), {warnings} warning(s))", file=sys.stderr)
        return 1
    print(
        f"V1S backlog: PASS ({len(analysis.tasks)} declarations; "
        f"{warnings} warning(s))"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
