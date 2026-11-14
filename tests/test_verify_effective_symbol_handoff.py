"""Read-only consumer acceptance of the standalone intermediate override artifact."""

from __future__ import annotations

import hashlib
import json
import zipfile
from datetime import UTC, datetime
from pathlib import Path

import pytest

from infinity_db.snapshot_provenance import sha256_file, write_snapshot_manifest
from tools.snapshot_archive import create_timestamped_archive
from tools.symbols.verify_effective_symbol_handoff import (
    EffectiveHandoffError,
    verify_effective_symbol_handoff,
)

STAMP = datetime(2026, 11, 11, 12, 0, tzinfo=UTC)
BASE = "https://assets.corvusbelli.net/army/img/"
A = BASE + "logo/units/unit-a.svg"
B = BASE + "logo/units/unit-b.svg"
C = BASE + "icon/cube.svg"
UPSTREAM = b'<svg xmlns="http://www.w3.org/2000/svg"><rect width="1"/></svg>'
CUBE = b'<svg xmlns="http://www.w3.org/2000/svg"><circle r="1"/></svg>'
OVERRIDE = b'<svg xmlns="http://www.w3.org/2000/svg"><path d="M1 1"/></svg>'


def _canonical(value: dict) -> bytes:
    return (
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    ).encode("utf-8")


def _write_zip(
    root: Path, destination: Path, name: str, members: dict[str, bytes],
) -> Path:
    files = []
    for relative, content in members.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        files.append(path)
    return create_timestamped_archive(
        files, destination, prefix=name, root=root, now=STAMP,
    )


def _fixtures(tmp_path: Path) -> tuple[Path, ...]:
    army = tmp_path / "JSON 20260917-120000.zip"
    with zipfile.ZipFile(army, "w") as archive:
        archive.writestr("metadata.json", "{}")
        archive.writestr("101-test.json", '{"version":"7.26246.158","units":[]}')
    raw = _write_zip(
        tmp_path / "raw", tmp_path / "snapshots", "SYMBOLS", {
            "static/characteristics/cube.svg": CUBE,
            "units/unit-a.svg": UPSTREAM,
            "units/unit-b.svg": UPSTREAM,
        },
    )
    raw_manifest = write_snapshot_manifest(
        raw, tmp_path / "manifests", snapshot_type="symbols",
        acquired_at=STAMP, source_url=BASE, document_count=3,
        input_artifact=army, project_root=tmp_path,
    )
    source_plan = {
        "format": "InfinityDB raw symbol acquisition requests",
        "formatVersion": 1,
        "inputArtifact": {"name": army.name, "sha256": sha256_file(army)},
        "sourceDocumentCount": 2,
        "requests": [
            {"url": C, "archivePath": "static/characteristics/cube.svg"},
            {"url": A, "archivePath": "units/unit-a.svg"},
            {"url": B, "archivePath": "units/unit-b.svg"},
        ],
    }
    plan_path = tmp_path / "source-plan.json"
    plan_path.write_bytes(_canonical(source_plan))
    lookup = {
        "format": "InfinityDB symbol override lookup plan",
        "formatVersion": 1,
        "sourcePlanSha256": hashlib.sha256(_canonical(source_plan)).hexdigest(),
        "lookups": [
            {"url": C, "overridePath": "characteristics/cube.svg"},
            {"url": A, "overridePath": "units/unit-a.svg"},
            {"url": B, "overridePath": "units/unit-b.svg"},
        ],
    }
    lookup_path = tmp_path / "override-lookups.json"
    lookup_path.write_bytes(_canonical(lookup))
    raw_report = {
        "format": "InfinityDB raw symbol acquisition report",
        "formatVersion": 1,
        "inputArtifact": source_plan["inputArtifact"],
        "sourcePlanSha256": hashlib.sha256(_canonical(source_plan)).hexdigest(),
        "snapshot": {
            "archiveName": raw.name,
            "sha256": sha256_file(raw),
            "snapshotManifestName": raw_manifest.name,
            "snapshotManifestSha256": sha256_file(raw_manifest),
            "documentCount": 3,
            "acquiredAt": STAMP.isoformat(timespec="seconds"),
        },
        "assets": [
            {
                "url": url, "archivePath": rel,
                "sha256": hashlib.sha256(body).hexdigest(),
                "sourceMethod": "network",
            }
            for url, rel, body in (
                (C, "static/characteristics/cube.svg", CUBE),
                (A, "units/unit-a.svg", UPSTREAM),
                (B, "units/unit-b.svg", UPSTREAM),
            )
        ],
        "unavailableAssets": [],
    }
    raw_report_path = tmp_path / "raw-report.json"
    raw_report_path.write_bytes(_canonical(raw_report))
    overrides = tmp_path / "overrides"
    (overrides / "units").mkdir(parents=True)
    (overrides / "units/unit-a.svg").write_bytes(OVERRIDE)
    effective = _write_zip(
        tmp_path / "effective-root", tmp_path / "effective",
        "EFFECTIVE-SYMBOLS", {
            "static/characteristics/cube.svg": CUBE,
            "units/unit-a.svg": OVERRIDE,
            "units/unit-b.svg": OVERRIDE,
        },
    )
    effective_manifest = write_snapshot_manifest(
        effective, tmp_path / "effective-manifests",
        snapshot_type="symbols", acquired_at=STAMP,
        source_url=BASE, document_count=3,
        input_artifact=army, project_root=tmp_path,
    )
    effective_report = {
        "format": "InfinityDB effective symbol processing report",
        "formatVersion": 1,
        "processingStages": {
            "overrides": "completed",
            "fontAudit": "pending",
            "deduplication": "pending",
            "textConversion": "pending",
            "compression": "pending",
        },
        "inputArtifact": source_plan["inputArtifact"],
        "sourcePlanSha256": hashlib.sha256(_canonical(source_plan)).hexdigest(),
        "overrideLookupPlanSha256": hashlib.sha256(_canonical(lookup)).hexdigest(),
        "rawSourceReportSha256": sha256_file(raw_report_path),
        "rawSnapshot": {
            "archiveName": raw.name, "sha256": sha256_file(raw),
            "manifestName": raw_manifest.name,
            "manifestSha256": sha256_file(raw_manifest),
        },
        "snapshot": {
            "archiveName": effective.name,
            "sha256": sha256_file(effective),
            "manifestName": effective_manifest.name,
            "manifestSha256": sha256_file(effective_manifest),
            "documentCount": 3, "processedAt": STAMP.isoformat(timespec="seconds"),
        },
        "assets": [
            {
                "url": url, "archivePath": rel,
                "sourceMethod": "network" if url == C else "override",
                "upstreamSha256": hashlib.sha256(raw_body).hexdigest(),
                "sha256": hashlib.sha256(effective_body).hexdigest(),
                "overridePath": None if url == C else "units/unit-a.svg",
                "overrideSha256": None if url == C else hashlib.sha256(OVERRIDE).hexdigest(),
            }
            for url, rel, raw_body, effective_body in (
                (C, "static/characteristics/cube.svg", CUBE, CUBE),
                (A, "units/unit-a.svg", UPSTREAM, OVERRIDE),
                (B, "units/unit-b.svg", UPSTREAM, OVERRIDE),
            )
        ],
        "unavailableAssets": [],
        "rawUnavailableAssets": [],
        "unusedOverrides": [],
        "overrideSummary": {"direct": 1, "propagated": 1},
    }
    effective_report_path = tmp_path / "effective-report.json"
    effective_report_path.write_bytes(_canonical(effective_report))
    return (
        plan_path, lookup_path, army, raw, raw_manifest, raw_report_path,
        effective, effective_manifest, effective_report_path, overrides,
    )


def _edit(path: Path, change) -> None:
    value = json.loads(path.read_text(encoding="utf-8"))
    change(value)
    path.write_bytes(_canonical(value))


def test_verified_effective_handoff_accepts_override_and_propagation(tmp_path: Path) -> None:
    paths = _fixtures(tmp_path)
    assert verify_effective_symbol_handoff(
        *paths[:9], override_root=paths[9],
    ) == {"requested": 3, "effective": 3, "overridden": 2, "unavailable": 0}


def test_tampered_effective_bytes_are_rejected(tmp_path: Path) -> None:
    paths = _fixtures(tmp_path)
    with zipfile.ZipFile(paths[6], "a") as archive:
        archive.writestr("extra.svg", UPSTREAM)
    with pytest.raises(EffectiveHandoffError, match="ZIP/manifest/report hash"):
        verify_effective_symbol_handoff(*paths[:9])


def test_wrong_effective_member_hash_is_rejected(tmp_path: Path) -> None:
    paths = _fixtures(tmp_path)
    _edit(paths[8], lambda doc: doc["assets"][2].__setitem__("sha256", "0" * 64))
    with pytest.raises(EffectiveHandoffError, match="member digest mismatch"):
        verify_effective_symbol_handoff(*paths[:9])


def test_wrong_raw_provenance_binding_is_rejected(tmp_path: Path) -> None:
    paths = _fixtures(tmp_path)
    _edit(paths[8], lambda doc: doc["rawSnapshot"].__setitem__("sha256", "0" * 64))
    with pytest.raises(EffectiveHandoffError, match="Raw snapshot binding"):
        verify_effective_symbol_handoff(*paths[:9])


def test_illegal_cross_category_override_propagation_is_rejected(tmp_path: Path) -> None:
    paths = _fixtures(tmp_path)
    _edit(paths[8], lambda doc: doc["assets"][2].__setitem__(
        "overridePath", "characteristics/cube.svg",
    ))
    with pytest.raises(EffectiveHandoffError, match="Illegal override propagation"):
        verify_effective_symbol_handoff(*paths[:9])


def test_wrong_local_override_file_is_rejected(tmp_path: Path) -> None:
    paths = _fixtures(tmp_path)
    (paths[9] / "units/unit-a.svg").write_bytes(CUBE)
    with pytest.raises(EffectiveHandoffError, match="Local override input hash mismatch"):
        verify_effective_symbol_handoff(*paths[:9], override_root=paths[9])


def test_pending_stages_cannot_be_reported_as_complete(tmp_path: Path) -> None:
    paths = _fixtures(tmp_path)
    _edit(paths[8], lambda doc: doc["processingStages"].__setitem__(
        "compression", "completed",
    ))
    with pytest.raises(EffectiveHandoffError, match="only override resolution"):
        verify_effective_symbol_handoff(*paths[:9])


def test_incomplete_effective_coverage_is_rejected(tmp_path: Path) -> None:
    paths = _fixtures(tmp_path)
    _edit(paths[8], lambda doc: doc["assets"].pop())
    with pytest.raises(EffectiveHandoffError, match="ZIP members differ"):
        verify_effective_symbol_handoff(*paths[:9])


def test_wrong_lookup_source_sha_is_rejected(tmp_path: Path) -> None:
    paths = _fixtures(tmp_path)
    _edit(paths[1], lambda doc: doc.__setitem__("sourcePlanSha256", "0" * 64))
    with pytest.raises(EffectiveHandoffError, match="source-plan hash mismatch"):
        verify_effective_symbol_handoff(*paths[:9])
