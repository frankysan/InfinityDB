"""Read-only acceptance of standalone SVG duplicate report identities."""

from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest
from test_verify_effective_symbol_handoff import _fixtures

from infinity_db.snapshot_provenance import sha256_file
from tools.symbols.verify_symbol_duplicate_handoff import (
    DuplicateHandoffError,
    verify_duplicate_symbol_handoff,
)


def _canonical(value: dict) -> bytes:
    return (
        json.dumps(value, sort_keys=True, indent=2, ensure_ascii=False) + "\n"
    ).encode("utf-8")


def _write_csv(path: Path, fields: list[str], rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def _evidence(tmp_path: Path) -> tuple[Path, ...]:
    source = _fixtures(tmp_path)
    archive, provenance, effective_report = source[6:9]
    report_doc = json.loads(effective_report.read_text(encoding="utf-8"))
    actual = {row["archivePath"]: row["sha256"] for row in report_doc["assets"]}
    sizes = {}
    import zipfile

    with zipfile.ZipFile(archive) as current:
        sizes = {name: len(current.read(name)) for name in actual}

    font_report = tmp_path / "font-audit.json"
    font_content = {
        "format": "InfinityDB SVG font audit",
        "formatVersion": 1,
        "symbolArtifact": {"name": archive.name, "sha256": sha256_file(archive)},
        "summary": {
            "svgCount": 3,
            "fontMissingAssetCount": 0,
        },
        "assets": [
            {"archivePath": name, "category": "no_active_text"}
            for name in sorted(actual)
        ],
    }
    font_report.write_bytes(_canonical(font_content))
    font_receipt = tmp_path / "font-audit-state.json"
    font_receipt.write_bytes(_canonical({
        "format": "InfinityDB symbol processing stage receipt",
        "formatVersion": 1,
        "stage": "fontAudit",
        "status": "passed",
        "inputArtifact": font_content["symbolArtifact"],
        "summary": font_content["summary"],
        "report": {
            "name": font_report.name,
            "sha256": sha256_file(font_report),
        },
    }))

    group_path = tmp_path / "duplicate-groups.csv"
    group_header = [
        "group", "type", "role", "representative", "classification",
        "file", "size_bytes", "byte_sha256", "visual_sha256",
    ]
    rep = "units/unit-a.svg"
    dup = "units/unit-b.svg"
    _write_csv(group_path, group_header, [
        {
            "group": "D0001", "type": "exact", "role": role,
            "representative": rep, "classification": "no_active_text",
            "file": name, "size_bytes": str(sizes[name]),
            "byte_sha256": actual[name], "visual_sha256": "simulated-visual",
        }
        for name, role in [(rep, "representative"), (dup, "duplicate")]
    ])
    errors_path = tmp_path / "duplicate-render-errors.csv"
    _write_csv(errors_path, ["file", "byte_sha256", "renderer", "error"], [])
    canonical = {
        "static/characteristics/cube.svg": "static/characteristics/cube.svg",
        rep: rep,
        dup: rep,
    }
    summary = {
        "sourceAssetCount": 3,
        "canonicalAssetCount": 2,
        "uniqueByteSetCount": 2,
        "rendersAvoidedExactCount": 1,
        "exactGroupCount": 1,
        "visualGroupCount": 0,
        "redundantAssetCount": 1,
        "renderErrorCount": 0,
        "sourceAssetBytes": sum(sizes.values()),
        "canonicalAssetBytes": sizes["static/characteristics/cube.svg"] + sizes[rep],
        "reclaimedAssetBytes": sizes[dup],
    }
    summary_csv = tmp_path / "duplicate-summary.csv"
    _write_csv(summary_csv, [
        "renderer", "renderer_version", "jobs", "render_size",
        "source_svg_files", "canonical_svg_files", "unique_byte_sets",
        "renders_avoided_exact", "exact_groups", "visual_groups",
        "redundant_files", "render_errors", "source_size_bytes",
        "canonical_size_bytes", "reclaimed_size_bytes",
        "reduction_percent", "elapsed_seconds",
    ], [{
        "renderer": "resvg", "renderer_version": "test-1.0",
        "jobs": "2", "render_size": "512",
        "source_svg_files": "3", "canonical_svg_files": "2",
        "unique_byte_sets": "2", "renders_avoided_exact": "1",
        "exact_groups": "1", "visual_groups": "0",
        "redundant_files": "1", "render_errors": "0",
        "source_size_bytes": str(summary["sourceAssetBytes"]),
        "canonical_size_bytes": str(summary["canonicalAssetBytes"]),
        "reclaimed_size_bytes": str(summary["reclaimedAssetBytes"]),
        "reduction_percent": "33.333333", "elapsed_seconds": "0.004",
    }])
    receipt = tmp_path / "duplicate-receipt.json"
    receipt.write_bytes(_canonical({
        "format": "InfinityDB symbol processing stage receipt",
        "formatVersion": 1,
        "stage": "duplicateDetection",
        "status": "passed",
        "inputArtifact": font_content["symbolArtifact"],
        "fontAuditReport": {
            "name": font_report.name, "sha256": sha256_file(font_report),
        },
        "fontAuditReceipt": {
            "name": font_receipt.name, "sha256": sha256_file(font_receipt),
        },
        "renderer": "resvg",
        "rendererVersion": "test-1.0",
        "renderSize": 512,
        "jobs": 2,
        "reports": {
            name: {"name": path.name, "sha256": sha256_file(path)}
            for name, path in (
                ("groups", group_path),
                ("errors", errors_path),
                ("summary", summary_csv),
            )
        },
        "summary": summary,
        "canonicalByArchivePath": canonical,
    }))
    return (
        archive, provenance, effective_report, font_report, font_receipt,
        group_path, errors_path, summary_csv, receipt,
    )


def _mutate(path: Path, change) -> None:
    data = json.loads(path.read_text(encoding="utf-8"))
    change(data)
    path.write_bytes(_canonical(data))


def test_valid_standalone_duplicate_receipt_is_accepted(tmp_path: Path) -> None:
    assert verify_duplicate_symbol_handoff(*_evidence(tmp_path)) == {
        "assets": 3, "canonical": 2, "redundant": 1, "renderErrors": 0,
    }


def test_modified_csv_is_rejected_before_use(tmp_path: Path) -> None:
    args = _evidence(tmp_path)
    with args[5].open("ab") as writer:
        writer.write(b"\n")
    with pytest.raises(DuplicateHandoffError, match="groups CSV name/SHA-256"):
        verify_duplicate_symbol_handoff(*args)


def test_wrong_canonical_target_is_rejected(tmp_path: Path) -> None:
    args = _evidence(tmp_path)
    _mutate(
        args[8],
        lambda report: report["canonicalByArchivePath"].__setitem__(
            "units/unit-b.svg", "static/characteristics/cube.svg",
        ),
    )
    with pytest.raises(DuplicateHandoffError, match="disagrees"):
        verify_duplicate_symbol_handoff(*args)


def test_wrong_byte_metric_rejected(tmp_path: Path) -> None:
    args = _evidence(tmp_path)
    _mutate(
        args[8],
        lambda report: report["summary"].__setitem__("canonicalAssetBytes", 1),
    )
    with pytest.raises(DuplicateHandoffError, match="summary/count/status"):
        verify_duplicate_symbol_handoff(*args)


def test_failed_font_audit_cannot_be_used(tmp_path: Path) -> None:
    args = _evidence(tmp_path)
    _mutate(args[4], lambda report: report.__setitem__("status", "failed"))
    with pytest.raises(DuplicateHandoffError, match="Font-audit evidence"):
        verify_duplicate_symbol_handoff(*args)


def test_canonical_map_and_csv_must_cover_same_duplicates(tmp_path: Path) -> None:
    args = _evidence(tmp_path)
    _mutate(
        args[8],
        lambda report: report["canonicalByArchivePath"].__setitem__(
            "units/unit-b.svg", "units/unit-b.svg",
        ),
    )
    with pytest.raises(DuplicateHandoffError, match="disagrees"):
        verify_duplicate_symbol_handoff(*args)


def test_stale_effective_archive_identity_rejected(tmp_path: Path) -> None:
    args = _evidence(tmp_path)
    _mutate(
        args[2],
        lambda report: report["snapshot"].__setitem__("sha256", "0" * 64),
    )
    with pytest.raises(DuplicateHandoffError, match="source evidence mismatch"):
        verify_duplicate_symbol_handoff(*args)
