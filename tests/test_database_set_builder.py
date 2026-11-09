"""Build identity and publication failure isolation, using shipped runtime fixtures."""

from __future__ import annotations

import argparse
import copy
import json
import os
import shutil
import sqlite3
import zipfile
from contextlib import closing
from pathlib import Path
from typing import Any

import pytest

from infinity_army_data.cli import build_parser as army_parser
from infinity_db import database_set_builder as builder
from infinity_db.build_provenance import (
    BUILD_PROVENANCE_KEY,
    build_record,
    build_set_id,
    canonical_bytes,
    file_sha256,
    validate_set_provenance,
)
from infinity_db.cli import build_parser
from infinity_db.database_set import (
    EMBEDDED_WEAPON_RUNTIME_FILES,
    V10_RUNTIME_FILES,
    validate_database_set,
)
from infinity_db.sqlite_determinism import normalize_sqlite_header, vacuum_deterministic_sqlite
from infinity_db.variant_usage_storage import stage_variant_usage
from infinity_db.weapon_profile_storage import stage_weapon_profile_citations
from infinity_db.web import create_app
from tools.browser_wsgi_transport import wsgi_response

RELEASE = Path(__file__).resolve().parents[1] / "data/generated"


@pytest.fixture
def project(tmp_path: Path) -> tuple[Path, argparse.Namespace]:
    root = tmp_path / "project"
    for name in (
        "pyproject.toml", "src/sample.py", "data/curated/rules/sample.json",
        "data/manifests/symbol-publication.json",
        "src/infinity_db/web/static/restrictions-reference.json",
        "tools/build_weapon_profile_publication.py", "tools/audit_enrichment_coverage.py",
        "tools/audit_weapon_definition_gaps.py",
    ):
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("{}", encoding="utf-8")
    source = root / "army.zip"
    with zipfile.ZipFile(source, "w") as archive:
        archive.writestr("metadata.json", json.dumps({"factions": [{"id": 1, "name": "Test"}]}))
    args = build_parser().parse_args(["build", str(source), "--db-dir", str(root / "output")])
    return root, args


def _update_metadata(path: Path, values: dict[str, Any], *, rules: bool = False) -> None:
    table = "__rules_metadata" if rules else "__infinity_metadata"
    connection = sqlite3.connect(path)
    try:
        with connection:
            connection.executemany(
                f"INSERT OR REPLACE INTO {table} (key,value) VALUES (?,?)",
                [(key, canonical_bytes(value).decode()) for key, value in values.items()],
            )
        vacuum_deterministic_sqlite(connection)
    finally:
        connection.close()
    normalize_sqlite_header(path)


def _fake_army(args: argparse.Namespace, record: dict[str, Any]) -> int:
    """Stand in for normalization/export; exercise real runtime validation afterward."""
    army = args.output_dir / "infinity.db"
    shutil.copyfile(RELEASE / "infinity.db", army)
    with closing(sqlite3.connect(army)) as connection:
        meta = {key: json.loads(value) for key, value in connection.execute(
            "SELECT key,value FROM __infinity_metadata"
        )}
    meta["_meta"]["snapshotArchiveSha256"] = record["manifest"]["source"]["archiveSha256"]
    meta["armyMetadata"]["sourceSha256"] = record["manifest"]["source"]["metadataSha256"]
    meta["armyMetadata"]["sourceFile"] = record["manifest"]["source"]["metadataName"]
    _update_metadata(army, {
        BUILD_PROVENANCE_KEY: record, "_meta": meta["_meta"], "armyMetadata": meta["armyMetadata"],
    })
    (args.output_dir / "normalized.json").write_text("build-only", encoding="utf-8")
    return 0


def _fake_rules(stage: Path, root: Path, manifest: dict[str, Any]) -> None:
    army, rules = stage / "infinity.db", stage / "rules.db"
    shutil.copyfile(RELEASE / "rules.db", rules)
    with closing(sqlite3.connect(army)) as connection:
        generation = json.loads(connection.execute(
            "SELECT value FROM __infinity_metadata WHERE key='export_pair_sha256'",
        ).fetchone()[0])
    with closing(sqlite3.connect(rules)) as connection, connection:
        connection.execute(
            "UPDATE deployed_object_metadata SET value=? WHERE key='armyDatabaseSha256'",
            (json.dumps(file_sha256(army)),),
        )
        publication = json.loads((RELEASE / "variant-usage.json").read_text(encoding="utf-8"))
        publication["sourceSnapshot"].update(
            armyDatabaseSha256=file_sha256(army),
            armyArchiveSha256=manifest["source"]["archiveSha256"], exportPairSha256=generation,
        )
        stage_variant_usage(connection, publication)
        document = json.loads(
            (RELEASE / "weapon-profile-sources.json").read_text(encoding="utf-8")
        )
        document["sourceSnapshot"]["armyDatabaseSha256"] = file_sha256(army)
        stage_weapon_profile_citations(connection, document, army)
        connection.execute("PRAGMA user_version=12")
        connection.execute("UPDATE __rules_metadata SET value='12' WHERE key='formatVersion'")
        connection.execute(
            "UPDATE __rules_metadata SET value='14' WHERE key='databaseCompatibilityVersion'"
        )
    _update_metadata(rules, {
        BUILD_PROVENANCE_KEY: build_record(manifest, "rules-n5", army_generation=generation),
    }, rules=True)


def _digests(directory: Path) -> dict[str, str]:
    return {path.name: file_sha256(path) for path in directory.iterdir() if path.is_file()}


def test_input_identity_is_order_independent_and_contains_no_host_paths(project) -> None:
    root, args = project
    manifest = builder.collect_build_manifest(root, args.source, None)
    shuffled = copy.deepcopy(manifest)
    shuffled["inputs"] = dict(reversed(list(shuffled["inputs"].items())))
    assert build_set_id(shuffled) == build_set_id(manifest)
    assert str(root).encode() not in canonical_bytes(manifest)
    (root / "data/curated/rules/sample.json").write_text('{"changed":true}', encoding="utf-8")
    assert build_set_id(builder.collect_build_manifest(root, args.source, None)) != (
        build_set_id(manifest)
    )


def test_builder_code_and_selected_metadata_are_inputs(project) -> None:
    root, args = project
    original = builder.collect_build_manifest(root, args.source, None)
    (root / "src/sample.py").write_text("# changed\n", encoding="utf-8")
    code_change = builder.collect_build_manifest(root, args.source, None)
    assert code_change["builderRevision"] != original["builderRevision"]
    (root / "src/sample.py").write_bytes(b"# changed\r\n")
    assert builder.collect_build_manifest(root, args.source, None) == code_change
    metadata = root / "other-metadata.json"
    metadata.write_text('{"factions":[{"id":2,"name":"Other"}]}', encoding="utf-8")
    selected = builder.collect_build_manifest(root, args.source, metadata)
    assert selected["source"]["metadataSha256"] != code_change["source"]["metadataSha256"]


def test_complete_build_publishes_only_selected_files_and_is_repeatable(
    project, monkeypatch: pytest.MonkeyPatch,
) -> None:
    root, args = project
    monkeypatch.setenv("INFINITY_DB_DB_DIR", str(root / "must-not-write"))
    monkeypatch.setattr(builder, "_build_rules_and_publications", _fake_rules)
    args.db_dir.mkdir()
    (args.db_dir / "keep.txt").write_text("unrelated", encoding="utf-8")
    (args.db_dir / "variant-usage.json").write_bytes(b"obsolete publication")
    (args.db_dir / "weapon-profile-sources.json").write_bytes(b"obsolete publication")
    first = builder.build_database_set(args, _fake_army, root=root)
    assert first["buildProvenance"]["status"] == "matched"
    assert first["layout"] == "v12-two-file"
    assert first["reviewedWeapons"] == 62
    assert validate_database_set(args.db_dir)["sha256"] == first["sha256"]
    assert set(_digests(args.db_dir)) == {*EMBEDDED_WEAPON_RUNTIME_FILES, "keep.txt"}
    assert (args.db_dir / "keep.txt").read_text(encoding="utf-8") == "unrelated"
    app = create_app(args.db_dir / "infinity.db", rules_database_path=args.db_dir / "rules.db")
    assert app.weapon_profile_citations is not None
    assert len(app.weapon_profile_citations) == 69
    status, _, body = wsgi_response(app, "http://local.test/api/weapons/uragan-mrl")
    assert status == 200
    item = json.loads(body)
    assert item["profile_citations_available"] is True
    assert all(profile["profile_citations"] for profile in item["profiles"])
    assert not (root / "must-not-write").exists()
    assert not list((root / "data/work/build").iterdir())
    second = builder.build_database_set(args, _fake_army, root=root)
    assert second == first


@pytest.mark.parametrize("failure", ["generation", "validation", "changed-input"])
def test_failure_before_publication_retains_all_destination_bytes(
    project, monkeypatch: pytest.MonkeyPatch, failure: str,
) -> None:
    root, args = project
    args.db_dir.mkdir()
    for name in V10_RUNTIME_FILES:
        shutil.copyfile(RELEASE / name, args.db_dir / name)
    before = _digests(args.db_dir)

    def fail(stage: Path, root: Path, manifest: dict[str, Any]) -> None:
        if failure == "generation":
            raise ValueError("deliberate source rejection")
        _fake_rules(stage, root, manifest)
        if failure == "validation":
            with closing(sqlite3.connect(stage / "rules.db")) as connection, connection:
                connection.execute(
                    "UPDATE variant_usage_groups SET unique_units=unique_units+1 WHERE id=1"
                )
        else:
            (root / "data/curated/rules/sample.json").write_text("changed", encoding="utf-8")

    monkeypatch.setattr(builder, "_build_rules_and_publications", fail)
    with pytest.raises(ValueError):
        builder.build_database_set(args, _fake_army, root=root)
    assert _digests(args.db_dir) == before
    assert not list((root / "data/work/build").iterdir())


def test_interrupted_replacement_is_rejected_and_rerun_recovers(
    project, monkeypatch: pytest.MonkeyPatch,
) -> None:
    root, args = project
    args.db_dir.mkdir()
    for name in V10_RUNTIME_FILES:
        shutil.copyfile(RELEASE / name, args.db_dir / name)
    monkeypatch.setattr(builder, "_build_rules_and_publications", _fake_rules)
    replace = os.replace

    def interrupted(source: Path, destination: Path) -> None:
        if destination.name == "rules.db":
            raise OSError("deliberate interrupted replacement")
        replace(source, destination)

    monkeypatch.setattr(builder.os, "replace", interrupted)
    with pytest.raises(OSError, match="interrupted"):
        builder.build_database_set(args, _fake_army, root=root)
    with pytest.raises(ValueError, match="provenance"):
        validate_database_set(args.db_dir)
    monkeypatch.setattr(builder.os, "replace", replace)
    builder.build_database_set(args, _fake_army, root=root)
    assert validate_set_provenance(
        args.db_dir / "infinity.db", args.db_dir / "rules.db",
    )["status"] == "matched"


def test_complete_build_requires_zip_and_lossless_verification(project) -> None:
    root, args = project
    args.no_verify = True
    with pytest.raises(ValueError, match="no-verify"):
        builder.build_database_set(args, _fake_army, root=root)
    args.no_verify = False
    args.source = root
    with pytest.raises(ValueError, match="immutable local Army ZIP"):
        builder.build_database_set(args, _fake_army, root=root)
    assert not args.db_dir.exists()


@pytest.mark.parametrize(
    "damage", ["id", "version", "mixed", "army-generation", "archive", "metadata"],
)
def test_recorded_provenance_rejects_tampered_or_mixed_inputs(
    project, monkeypatch: pytest.MonkeyPatch, damage: str,
) -> None:
    root, args = project
    monkeypatch.setattr(builder, "_build_rules_and_publications", _fake_rules)
    result = builder.build_database_set(args, _fake_army, root=root)
    manifest = builder.collect_build_manifest(root, args.source, None)
    army, rules = args.db_dir / "infinity.db", args.db_dir / "rules.db"
    generation = result["buildProvenance"]["armyExportPairSha256"]
    if damage in {"id", "version", "mixed", "army-generation"}:
        record = build_record(manifest, "rules-n5", army_generation=generation)
        if damage == "id":
            record["buildSetId"] = "0" * 64
        elif damage == "version":
            record["formatVersion"] = 999
        elif damage == "mixed":
            changed = copy.deepcopy(manifest)
            changed["inputs"]["data/curated/rules/sample.json"] = "0" * 64
            record = build_record(changed, "rules-n5", army_generation=generation)
        else:
            record["requiredArmyExportPairSha256"] = "0" * 64
        _update_metadata(rules, {BUILD_PROVENANCE_KEY: record}, rules=True)
    else:
        key = "_meta" if damage == "archive" else "armyMetadata"
        with closing(sqlite3.connect(army)) as connection:
            value = json.loads(connection.execute(
                "SELECT value FROM __infinity_metadata WHERE key=?", (key,),
            ).fetchone()[0])
        value["snapshotArchiveSha256" if damage == "archive" else "sourceSha256"] = "0" * 64
        _update_metadata(army, {key: value})
    with pytest.raises(ValueError, match="provenance|generations|generation|manifest"):
        validate_set_provenance(army, rules)


def test_output_cannot_replace_the_selected_source_archive(project) -> None:
    root, args = project
    source = root / "infinity.db"
    shutil.copyfile(args.source, source)
    before = file_sha256(source)
    args.source, args.db_dir = source, root
    with pytest.raises(ValueError, match="replace an input"):
        builder.build_database_set(args, _fake_army, root=root)
    assert file_sha256(source) == before
    assert not (root / "data/work/build").exists()


def test_runtime_and_narrow_build_outputs_are_explicitly_exclusive() -> None:
    with pytest.raises(SystemExit):
        build_parser().parse_args(["build", "--db-dir", "one", "--output-dir", "two"])
    with pytest.raises(SystemExit):
        army_parser().parse_args(["build", "--db-dir", "one"])
