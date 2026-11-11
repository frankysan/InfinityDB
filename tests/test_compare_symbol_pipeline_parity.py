"""Focused offline coverage for the optional symbol-pipeline parity gate."""

from __future__ import annotations

import zipfile
from pathlib import Path
from types import SimpleNamespace

import pytest

from tools import compare_symbol_pipeline_parity as parity

SVG = b'<svg xmlns="http://www.w3.org/2000/svg"><path d="M0 0"/></svg>'


def _inputs(tmp_path: Path):
    archive = tmp_path / "compressed.zip"
    with zipfile.ZipFile(archive, "w") as stream:
        stream.writestr("units/a.svg", SVG)
    legacy = tmp_path / "legacy"
    (legacy / "units").mkdir(parents=True)
    (legacy / "units" / "a.svg").write_bytes(SVG)
    files = [tmp_path / f"{name}.json" for name in range(6)]
    for path in files:
        path.write_text("fixture")
    return files[:2] + [archive] + files[2:] + [legacy]


def _mock(monkeypatch, *, passed=True):
    monkeypatch.setattr(
        parity, "verify_processed_symbol_handoff",
        lambda *args: {"canonicalAssets": 1, "sourceIdentities": 1},
    )
    monkeypatch.setattr(parity, "get_tool_version", lambda executable: "resvg 1.0")

    class FakeValidator:
        def __init__(self, **kwargs):
            assert kwargs["target_sizes"] == [32, 64]
            assert kwargs["reference_svg"].read_bytes() == SVG

        def prepare_reference(self):
            return True, ""

        def validate(self, candidate, name):
            assert candidate.read_bytes() == SVG
            return passed, SimpleNamespace(
                worst_rms=0.0 if passed else 0.5,
                worst_changed_fraction=0.0 if passed else 0.5,
            ), ""

    monkeypatch.setattr(parity, "RasterValidator", FakeValidator)


def test_parity_pass_and_failure(tmp_path, monkeypatch):
    files = _inputs(tmp_path)
    _mock(monkeypatch)
    report = parity.compare_symbol_pipeline_parity(*files, renderer="resvg", executable="resvg")
    assert report["status"] == "passed"
    assert report["verifiedAssets"] == 1
    assert report["assets"][0]["legacySha256"] == report["assets"][0]["externalSha256"]
    _mock(monkeypatch, passed=False)
    report = parity.compare_symbol_pipeline_parity(*files, renderer="resvg", executable="resvg")
    assert report["status"] == "failed"
    assert report["failedAssets"] == 1


def test_path_mismatch_rejected(tmp_path, monkeypatch):
    files = _inputs(tmp_path)
    _mock(monkeypatch)
    (files[-1] / "units" / "a.svg").unlink()
    with pytest.raises(ValueError, match="path mismatch"):
        parity.compare_symbol_pipeline_parity(
            *files, renderer="resvg", executable="resvg",
        )


def test_unavailable_renderer_rejected(tmp_path, monkeypatch):
    files = _inputs(tmp_path)
    _mock(monkeypatch)
    monkeypatch.setattr(parity, "get_tool_version", lambda executable: "unknown")
    with pytest.raises(ValueError, match="version"):
        parity.compare_symbol_pipeline_parity(
            *files, renderer="resvg", executable="resvg",
        )
