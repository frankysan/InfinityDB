from pathlib import Path

import pytest

from tools.data.verify_complete_database_build import ROOT, verify


def test_complete_build_verifier_uses_repository_root() -> None:
    assert ROOT == Path(__file__).resolve().parents[1]


def test_complete_build_verifier_rejects_missing_source(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="Selected source ZIP"):
        verify(tmp_path / "missing.zip", "0" * 64)
