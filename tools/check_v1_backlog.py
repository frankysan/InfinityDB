"""Check the active V1S execution-slice register in docs/TODO.md."""

from __future__ import annotations

import argparse
import re
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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--todo",
        type=Path,
        default=ROOT / "docs" / "TODO.md",
        help="backlog Markdown file to inspect (default: docs/TODO.md)",
    )
    args = parser.parse_args(argv)
    try:
        markdown = args.todo.read_text(encoding="utf-8")
    except OSError as exc:
        print(f"{args.todo}: unable to read backlog: {exc}", file=sys.stderr)
        return 2

    analysis = analyze_backlog(markdown, source=str(args.todo))
    for diagnostic in analysis.diagnostics:
        print(
            f"{diagnostic.source}:{diagnostic.line}: {diagnostic.severity} "
            f"{diagnostic.code}: {diagnostic.message}\n"
            f"  Suggested correction: {diagnostic.suggestion}"
        )
    errors = sum(item.severity == "error" for item in analysis.diagnostics)
    warnings = sum(item.severity == "warning" for item in analysis.diagnostics)
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
