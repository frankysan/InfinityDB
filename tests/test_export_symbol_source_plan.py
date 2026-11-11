"""Read-only symbol source-request plan contract."""

from __future__ import annotations

import json
import zipfile
from datetime import UTC, date, datetime
from pathlib import Path

import pytest

from infinity_db.snapshot_provenance import (
    SnapshotProvenanceError,
    write_snapshot_manifest,
)
from tools.export_symbol_source_plan import (
    FORMAT,
    VERSION,
    build_source_plan,
    write_source_plan,
)

BASE = "https://assets.corvusbelli.net/army/img/"
UNIT = BASE + "logo/units/unit.svg"
FACTION = BASE + "logo/factions/faction.svg"
STATIC = BASE + "icon/cube.svg"


def _inputs(tmp_path: Path, *, unexpected_svg: bool = False) -> tuple[Path, Path, Path]:
    archive = tmp_path / "JSON 20260917-120000.zip"
    unit = {
        "id": 9,
        "profileGroups": [{"profiles": [{"name": "Unit", "logo": UNIT}]}],
    }
    if unexpected_svg:
        unit["unexpectedSourceField"] = {"logo": BASE + "other/unknown.svg"}
    with zipfile.ZipFile(archive, "w") as output:
        output.writestr(
            "metadata.json",
            json.dumps({"factions": [{"id": 101, "logo": FACTION}]}),
        )
        output.writestr(
            "101-panoceania.json",
            json.dumps({"version": "7.26246.158", "units": [unit]}),
        )
    manifest = write_snapshot_manifest(
        archive,
        tmp_path / "manifests",
        snapshot_type="army",
        acquired_at=datetime(2026, 9, 17, 12, 0, tzinfo=UTC),
        source_url="https://api.corvusbelli.com/army",
        document_count=2,
        source_data_changed_on=date(2026, 9, 3),
        language="en",
        project_root=tmp_path,
    )
    static = tmp_path / "static-symbols.json"
    static.write_text(
        json.dumps({
            "schema_version": 2,
            "base_url": BASE + "icon/",
            "assets": [{
                "key": "cube", "category": "characteristics",
                "filename": "cube.svg", "label": "Cube",
            }],
        }),
        encoding="utf-8",
    )
    return archive, manifest, static


def test_symbol_source_plan_is_pinned_and_deterministic(tmp_path: Path) -> None:
    archive, manifest, static = _inputs(tmp_path)
    plan = build_source_plan(
        archive, manifest, static_symbols_path=static, legacy_armies_path=None,
        project_root=tmp_path,
    )
    assert plan["format"] == FORMAT
    assert plan["formatVersion"] == VERSION
    assert plan["inputArtifact"]["name"] == archive.name
    assert len(plan["inputArtifact"]["sha256"]) == 64
    assert plan["sourceDocumentCount"] == 2
    assert plan["requests"] == [
        {"url": STATIC, "archivePath": "static/characteristics/cube.svg"},
        {"url": FACTION, "archivePath": "factions/faction.svg"},
        {"url": UNIT, "archivePath": "units/unit.svg"},
    ]
    target = tmp_path / "source-requests.json"
    write_source_plan(target, plan)
    payload = target.read_bytes()
    assert payload.endswith(b"\n")
    assert b"\r" not in payload
    assert json.loads(payload) == plan
    assert write_source_plan(target, plan) == target
    assert target.read_bytes() == payload

    changed = dict(plan)
    changed["requests"] = []
    with pytest.raises(ValueError, match="differs"):
        write_source_plan(target, changed)
    assert target.read_bytes() == payload


def test_symbol_source_plan_does_not_delete_existing_staging(tmp_path: Path) -> None:
    archive, manifest, static = _inputs(tmp_path)
    plan = build_source_plan(
        archive, manifest, static_symbols_path=static, legacy_armies_path=None,
    )
    target = tmp_path / "requests.json"
    staging = target.with_suffix(".json.tmp")
    staging.write_bytes(b"another writer's staging")
    with pytest.raises(FileExistsError):
        write_source_plan(target, plan)
    assert staging.read_bytes() == b"another writer's staging"
    assert not target.exists()


def test_symbol_source_plan_rejects_unknown_svg_fields(tmp_path: Path) -> None:
    archive, manifest, static = _inputs(tmp_path, unexpected_svg=True)
    with pytest.raises(ValueError, match="Unknown SVG-bearing Army source fields"):
        build_source_plan(
            archive, manifest, static_symbols_path=static, legacy_armies_path=None,
        )


def test_symbol_source_plan_refuses_changed_army_archive(tmp_path: Path) -> None:
    archive, manifest, static = _inputs(tmp_path)
    with zipfile.ZipFile(archive, "a") as output:
        output.writestr("extra.txt", "tampered")
    with pytest.raises(SnapshotProvenanceError, match="SHA-256 mismatch"):
        build_source_plan(
            archive, manifest, static_symbols_path=static, legacy_armies_path=None,
        )
