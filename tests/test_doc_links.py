"""Offline documentation-link validation without fetching external sources."""

from __future__ import annotations

from pathlib import Path
from subprocess import CompletedProcess

import pytest

from tools.check_doc_links import _anchors, check_links, default_paths


def test_heading_anchors_preserve_punctuation_spacing_and_duplicates() -> None:
    source = (
        "### RS-AW-IMM-001 — Immunity changes covered effects\n"
        "## Repeated heading\n"
        "## Repeated heading\n"
        "## Thing with *emphasis* and [Link](elsewhere.md)\n"
    )
    assert _anchors(source) == {
        "rs-aw-imm-001--immunity-changes-covered-effects",
        "repeated-heading", "repeated-heading-1",
        "thing-with-emphasis-and-link",
    }


def test_local_links_support_paths_fragments_references_and_ignore_code(
    tmp_path: Path,
) -> None:
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "target.md").write_text(
        "# Existing\n\n## Repeated\n\n## Repeated\n",
        encoding="utf-8",
    )
    source = docs / "source.md"
    source.write_text(
        "# Entry\n\n"
        "[relative](target.md#existing)\n"
        "[local](#entry)\n"
        "[duplicate](target.md#repeated-1)\n"
        "[reference][good]\n"
        "[good]: target.md#existing\n"
        "[web](https://example.com/path#unknown)\n"
        "[app](/weapons/ap-mine#rule-weapon-mines)\n"
        + chr(96) + "[invalid](missing.md)" + chr(96) + "\n"
        + "~~~markdown\n[also invalid](missing.md)\n~~~\n",
        encoding="utf-8",
    )
    assert check_links([source], tmp_path) == []


def test_broken_paths_fragments_and_escape_are_reported(tmp_path: Path) -> None:
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "target.md").write_text("## Valid\n", encoding="utf-8")
    source = docs / "source.md"
    source.write_text(
        "[missing](none.md)\n"
        "[wrong](target.md#absent)\n"
        "[escaped](../../outside.md)\n",
        encoding="utf-8",
    )
    errors = check_links([source], tmp_path)
    assert len(errors) == 3
    assert "missing target: none.md" in errors[0]
    assert "missing heading #absent" in errors[1]
    assert "link leaves repository: ../../outside.md" in errors[2]


def test_default_paths_include_tracked_nested_markdown_but_not_ignored(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    (tmp_path / "docs").mkdir()
    (tmp_path / "extras").mkdir()
    (tmp_path / "local").mkdir()
    (tmp_path / "docs/README.md").write_text("# Docs\n", encoding="utf-8")
    (tmp_path / "extras/README.md").write_text("# Extra\n", encoding="utf-8")
    (tmp_path / "local/ignored.md").write_text(
        "[broken](missing.md)\n", encoding="utf-8",
    )
    monkeypatch.setattr(
        "tools.check_doc_links.subprocess.run",
        lambda *args, **kwargs: CompletedProcess(
            args=[], returncode=0,
            stdout=b"docs/README.md\0extras/README.md\0",
        ),
    )
    paths = default_paths(tmp_path)
    assert paths == [tmp_path / "docs/README.md", tmp_path / "extras/README.md"]
    assert check_links(paths, tmp_path) == []


def test_default_paths_work_without_git(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs/new.md").write_text("# New\n", encoding="utf-8")

    def unavailable(*args: object, **kwargs: object) -> None:
        raise FileNotFoundError("git unavailable")

    monkeypatch.setattr("tools.check_doc_links.subprocess.run", unavailable)
    assert default_paths(tmp_path) == [tmp_path / "docs/new.md"]


def test_current_documentation_local_links_are_valid() -> None:
    root = Path(__file__).resolve().parents[1]
    paths = default_paths(root)
    assert root / "docs" / "README.md" in paths
    assert root / "data" / "curated" / "README.md" in paths
    assert root / "data" / "curated" / "snapshot-notes" / "README.md" in paths
    assert root / "THIRD_PARTY_NOTICES.md" in paths
    assert not any("local" in path.parts for path in paths)
    assert check_links(paths, root) == []
