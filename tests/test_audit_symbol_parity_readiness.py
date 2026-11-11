"""Readiness audit validates existing evidence without inventing upstream bytes."""

from __future__ import annotations

import hashlib
import json
import zipfile

import pytest

from tools.audit_symbol_parity_readiness import audit_parity_readiness


def test_missing_external_artifacts_and_unproven_override(tmp_path):
    body = b'<svg xmlns="http://www.w3.org/2000/svg"/>'
    archive = tmp_path / "symbols.zip"
    with zipfile.ZipFile(archive, "w") as stream:
        stream.writestr("a.svg", body)
    baseline = tmp_path / "baseline.json"
    baseline.write_text(json.dumps({
        "format": "InfinityDB symbol production-source baseline audit",
        "counts": {
            "requestedUrls": 1, "verifiedArchiveMembers": 1,
            "upstreamRecoverability": {"upstream_not_proven": 1},
        },
        "inputs": {
            "symbolSha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
        },
    }))
    plan = tmp_path / "plan.json"
    plan.write_text(json.dumps({
        "requests": [{"url": "https://example.org/a.svg", "archivePath": "a.svg"}],
    }))
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({
        "assets": [{"archivePath": "a.svg", "sha256": hashlib.sha256(body).hexdigest(),
                    "upstreamSha256": "0" * 64}],
    }))
    work = tmp_path / "work"
    (work / "compressed").mkdir(parents=True)
    (work / "compressed" / "a.svg").write_bytes(body)
    external = tmp_path / "external"
    result = audit_parity_readiness(
        baseline, plan, manifest, archive, work, external,
    )
    assert result["status"] == "blocked"
    assert result["upstreamUnprovenPaths"] == ["a.svg"]
    assert result["legacyCompressedAssets"] == 1
    assert len(result["blockers"]) == 2


def test_archive_tampering_is_rejected(tmp_path):
    archive = tmp_path / "symbols.zip"
    archive.write_bytes(b"tampered")
    baseline = tmp_path / "baseline.json"
    baseline.write_text(json.dumps({
        "format": "InfinityDB symbol production-source baseline audit",
        "counts": {"requestedUrls": 0},
        "inputs": {"symbolSha256": "0" * 64},
    }))
    plan = tmp_path / "plan.json"
    plan.write_text(json.dumps({"requests": []}))
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({"assets": []}))
    with pytest.raises(ValueError, match="differs from audited baseline"):
        audit_parity_readiness(
            baseline, plan, manifest, archive,
            tmp_path / "work", tmp_path / "external",
        )
