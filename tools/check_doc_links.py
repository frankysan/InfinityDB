"""Check local Markdown destinations and headings without network access."""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
import unicodedata
from collections import Counter
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
INLINE_LINK = re.compile(r"(?<!!)\[[^\]\n]*\]\((?:<([^>\n]+)>|([^\n]*?))\)")
REFERENCE_LINK = re.compile(r"^\s{0,3}\[[^\]]+\]:\s*(?:<([^>]+)>|(\S+))")
HEADING = re.compile(r"^#{1,6}\s+(.+?)\s*#*\s*$")
HTML_ANCHOR = re.compile(r'<a\s+[^>]*id=["\x27]([^"\x27]+)["\x27]', re.IGNORECASE)
FENCE = re.compile(r"^\s*(?:\x60{3,}|~{3,})")
INLINE_CODE = re.compile(r"(\x60+).*?\1")


def _slug(text: str) -> str:
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"!?\[([^\]]+)\]\([^)]*\)", r"\1", text)
    text = text.replace(chr(96), "").strip().lower()
    text = "".join(
        char for char in text
        if char in "-_ " or unicodedata.category(char)[0] not in {"P", "S"}
    )
    # GitHub-style anchors replace each space after stripping punctuation;
    # the spaces around an em dash therefore become two hyphens.
    return re.sub(r"\s", "-", text)


def _anchors(source: str) -> set[str]:
    counts: Counter[str] = Counter()
    anchors: set[str] = set()
    in_fence = False
    for line in source.splitlines():
        if FENCE.match(line):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        match = HEADING.match(line)
        if match:
            slug = _slug(match.group(1))
            ordinal = counts[slug]
            counts[slug] += 1
            anchors.add(slug if not ordinal else f"{slug}-{ordinal}")
        anchors.update(HTML_ANCHOR.findall(line))
    return anchors


def _destinations(source: str) -> list[tuple[int, str]]:
    result: list[tuple[int, str]] = []
    in_fence = False
    for line_no, line in enumerate(source.splitlines(), 1):
        if FENCE.match(line):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        line = INLINE_CODE.sub("", line)
        for match in INLINE_LINK.finditer(line):
            result.append((line_no, match.group(1) or match.group(2)))
        reference = REFERENCE_LINK.match(line)
        if reference:
            result.append((line_no, reference.group(1) or reference.group(2)))
    return result


def check_links(paths: list[Path], root: Path) -> list[str]:
    """Return deterministic diagnostics; never follow paths outside root."""
    errors: list[str] = []
    cache: dict[Path, set[str]] = {}
    for path in sorted(set(paths)):
        if not path.is_file():
            errors.append(f"{path}: missing Markdown file")
            continue
        for line, raw_target in _destinations(path.read_text(encoding="utf-8")):
            target = raw_target.strip()
            if not target or target.startswith(("/", "//")):
                continue  # Application route or out-of-scope destination.
            split = urlsplit(target)
            if split.scheme or split.netloc or split.query:
                continue
            local = unquote(split.path)
            if not local and not split.fragment:
                continue
            destination = (path.parent / local).resolve() if local else path.resolve()
            if not destination.is_relative_to(root.resolve()):
                errors.append(f"{path.relative_to(root)}:{line}: link leaves repository: {target}")
                continue
            if not destination.exists():
                errors.append(f"{path.relative_to(root)}:{line}: missing target: {target}")
                continue
            if split.fragment and destination.suffix.lower() == ".md":
                if destination not in cache:
                    cache[destination] = _anchors(destination.read_text(encoding="utf-8"))
                fragment = unquote(split.fragment)
                if fragment not in cache[destination]:
                    errors.append(
                        f"{path.relative_to(root)}:{line}: missing heading #{fragment}: {target}"
                    )
    return errors


def default_paths(root: Path) -> list[Path]:
    """Cover tracked Markdown, including nested documentation outside docs/."""
    candidates: set[Path] = set()
    try:
        result = subprocess.run(
            ["git", "-C", str(root), "ls-files", "--cached", "-z", "--", "*.md"],
            capture_output=True,
            check=True,
        )
    except (OSError, subprocess.CalledProcessError):
        # Also usable from a source archive without Git metadata.
        pass
    else:
        candidates.update(
            root / os.fsdecode(name)
            for name in result.stdout.split(b"\0")
            if name
        )

    # Include new working documents before they are first staged, and keep
    # source-archive validation useful when Git metadata is not available.
    candidates.update((root / "docs").glob("*.md"))
    candidates.update(
        root / relative
        for relative in (
            "README.md",
            "AGENTS.md",
            "THIRD_PARTY_NOTICES.md",
            "data/README.md",
            "data/curated/README.md",
            "data/curated/snapshot-notes/README.md",
        )
    )
    return sorted(path for path in candidates if path.is_file())


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", type=Path, nargs="*")
    args = parser.parse_args(argv)
    paths = [ROOT / value for value in args.paths] if args.paths else default_paths(ROOT)
    errors = check_links(paths, ROOT)
    for issue in errors:
        print(issue)
    if errors:
        print(f"Markdown links: {len(errors)} errors", file=sys.stderr)
        return 1
    print(f"Markdown links: PASS ({len(paths)} files; local paths and headings)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
