from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools.compare_determinism_manifests import compare


def _write(path: Path, artifacts: dict[str, str]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "format": "InfinityDB cross-platform determinism manifest",
                "formatVersion": 1,
                "artifacts": artifacts,
            },
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return path


def test_compare_accepts_identical_manifests(tmp_path: Path) -> None:
    first = _write(tmp_path / "linux.json", {"build/infinity.db": "a" * 64})
    second = _write(tmp_path / "windows.json", {"build/infinity.db": "a" * 64})
    assert compare([first, second]) == []


def test_compare_reports_missing_or_changed_artifacts(tmp_path: Path) -> None:
    first = _write(
        tmp_path / "linux.json",
        {"build/infinity.db": "a" * 64, "archives/work.zip": "b" * 64},
    )
    second = _write(tmp_path / "windows.json", {"build/infinity.db": "c" * 64})
    errors = compare([first, second])
    assert any("build/infinity.db" in error for error in errors)
    assert any("archives/work.zip" in error for error in errors)


def test_compare_requires_multiple_manifests(tmp_path: Path) -> None:
    only = _write(tmp_path / "only.json", {"build/infinity.db": "a" * 64})
    with pytest.raises(ValueError, match="At least two"):
        compare([only])
