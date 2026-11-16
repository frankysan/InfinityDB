"""Independent processed-symbol verifier acceptance and tamper tests."""

from __future__ import annotations

import csv
import hashlib
import json
import zipfile
from pathlib import Path

import pytest

from tools.symbols.verify_processed_symbol_handoff import (
    ProcessedSymbolHandoffError,
    verify_processed_symbol_handoff,
)

SVG = b'<svg xmlns="http://www.w3.org/2000/svg"><path d="M0 0"/></svg>'
FORMAT = "InfinityDB symbol processing stage receipt"


def _pin(path: Path):
    return {"name": path.name, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}


def _zip(path: Path, body: bytes):
    with zipfile.ZipFile(path, "w") as stream:
        stream.writestr("units/a.svg", body)


def _csv(path: Path, fields: list[str], rows: list[dict]):
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def _fixture(root: Path):
    original = root / "canonical.zip"
    final = root / "compressed.zip"
    _zip(original, SVG)
    _zip(final, SVG)
    digest = hashlib.sha256(SVG).hexdigest()
    conversion = root / "conversion.json"
    conversion.write_text(json.dumps({
        "format": FORMAT, "formatVersion": 1, "stage": "textConversion",
        "status": "passed", "outputArtifact": _pin(original),
        "outputAssets": [{"archivePath": "units/a.svg", "sha256": digest}],
        "canonicalByArchivePath": {"units/a.svg": "units/a.svg"},
    }))
    report = root / "compression.csv"
    _csv(report, ["file", "profile", "status", "error", "source_bytes", "output_bytes"], [{
        "file": "units/a.svg", "profile": "balanced",
        "status": "NO_SMALLER_PASSING_CANDIDATE", "error": "",
        "source_bytes": len(SVG), "output_bytes": len(SVG),
    }])
    candidates = root / "candidates.csv"
    _csv(candidates, ["file", "error"], [])
    run = root / "run.json"
    run.write_text(json.dumps({
        "profiles": ["balanced"], "renderer": "resvg",
        "renderer_version": "resvg 1.0", "svgo_version": "svgo 4.0",
        "target_sizes_css_px": [32, 64], "dprs": [1, 2],
        "balanced_precisions": [2, 3], "max_rms": 0.01,
        "max_changed_fraction": 0.01, "pixel_diff_threshold": 8, "jobs": 2,
    }))
    receipt = root / "compression.json"
    receipt.write_text(json.dumps({
        "format": FORMAT, "formatVersion": 1, "stage": "compression",
        "status": "passed", "inputArtifact": _pin(original),
        "textConversionReceipt": _pin(conversion),
        "outputArtifact": _pin(final),
        "outputAssets": [{
            "archivePath": "units/a.svg", "sha256": digest, "sourceSha256": digest,
        }],
        "profile": "balanced", "renderer": "resvg",
        "rendererVersion": "resvg 1.0", "svgoVersion": "svgo 4.0",
        "parameters": {
            "targetSizes": [32, 64], "dprs": [1, 2],
            "balancedPrecisions": [2, 3], "maxRms": 0.01,
            "maxChangedFraction": 0.01, "pixelDiffThreshold": 8, "jobs": 2,
        },
        "reports": {
            "compression": _pin(report), "candidates": _pin(candidates),
            "run": _pin(run),
        },
        "summary": {
            "assetCount": 1, "sourceBytes": len(SVG), "outputBytes": len(SVG),
        },
    }))
    return (original, conversion, final, receipt, report, candidates, run)


def test_valid_handoff(tmp_path: Path):
    assert verify_processed_symbol_handoff(*_fixture(tmp_path)) == {
        "canonicalAssets": 1, "sourceIdentities": 1,
    }


@pytest.mark.parametrize("target", ["archive", "receipt", "report", "run"])
def test_tampering_fails_closed(tmp_path: Path, target: str):
    files = _fixture(tmp_path)
    if target == "archive":
        _zip(files[2], SVG.replace(b"M0 0", b"M1 1"))
    elif target == "receipt":
        state = json.loads(files[3].read_text())
        state["status"] = "failed"
        files[3].write_text(json.dumps(state))
    elif target == "report":
        files[4].write_text("corrupt")
    else:
        files[6].write_text(json.dumps({"renderer": "inkscape"}))
        state = json.loads(files[3].read_text())
        state["reports"]["run"] = _pin(files[6])
        files[3].write_text(json.dumps(state))
    with pytest.raises((ProcessedSymbolHandoffError, ValueError)):
        verify_processed_symbol_handoff(*files)


def test_active_text_rejected_even_with_matching_hashes(tmp_path: Path):
    files = _fixture(tmp_path)
    body = b'<svg xmlns="http://www.w3.org/2000/svg"><text>bad</text></svg>'
    _zip(files[2], body)
    state = json.loads(files[3].read_text())
    state["outputArtifact"] = _pin(files[2])
    state["outputAssets"][0]["sha256"] = hashlib.sha256(body).hexdigest()
    state["summary"]["outputBytes"] = len(body)
    files[3].write_text(json.dumps(state))
    with pytest.raises(ProcessedSymbolHandoffError, match="active text"):
        verify_processed_symbol_handoff(*files)
