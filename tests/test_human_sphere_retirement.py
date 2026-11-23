"""Synthetic regression checks for current-page Human Sphere archive retirement."""

from __future__ import annotations

import zipfile
from pathlib import Path

from tools.research.audit_human_sphere_retirement import compare


def _archive(path: Path, pages: dict[str, tuple[str, int, int]], assets: dict[str, bytes]) -> None:
    with zipfile.ZipFile(path, "w") as archive:
        for member, (title, article, revision) in pages.items():
            archive.writestr(member, '<html><script>RLCONF={'
                             f'"wgPageName":"{title}","wgArticleId":{article},'
                             f'"wgRevisionId":{revision}' + '}</script></html>')
        for member, data in assets.items():
            archive.writestr(member, data)


def test_preserved_revision_across_legacy_and_portable_paths(tmp_path: Path) -> None:
    old, new = tmp_path / "old.zip", tmp_path / "new.zip"
    _archive(old, {"A_Page": ("A_Page", 10, 22),
                   "File_Example.jpg": ("File:Example.jpg", 12, 34)},
             {"images/a.png": b"png"})
    _archive(new, {"A_Page.html": ("A_Page", 10, 22),
                   "File_Example.jpg.html": ("File:Example.jpg", 12, 34),
                   "More.html": ("More", 11, 33)}, {"images/a.png": b"png"})
    result = compare(old, new)
    assert result["strictCoverageComplete"]
    assert result["pageStatusCounts"] == {"revision-preserved": 2}
    assert result["missingNonPageMemberCount"] == 0


def test_changed_missing_renamed_and_assets_block_retirement(tmp_path: Path) -> None:
    old, new = tmp_path / "old.zip", tmp_path / "new.zip"
    _archive(old, {"A": ("A", 10, 22), "B": ("B", 11, 23),
                   "C": ("C", 12, 24)}, {"images/lost.png": b"image"})
    _archive(new, {"A.html": ("A", 10, 25), "Renamed.html": ("Renamed", 11, 23)}, {})
    result = compare(old, new)
    assert not result["strictCoverageComplete"]
    assert result["pageStatusCounts"] == {
        "missing-page": 1, "revision-changed": 1, "title-changed": 1,
    }
    assert result["missingNonPageMembers"] == ["images/lost.png"]
