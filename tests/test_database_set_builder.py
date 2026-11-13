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
from datetime import UTC, date, datetime
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
    COMPLETE_RUNTIME_FILES,
    validate_database_set,
)
from infinity_db.snapshot_provenance import SnapshotProvenanceError, write_snapshot_manifest
from infinity_db.sqlite_determinism import normalize_sqlite_header, vacuum_deterministic_sqlite
from infinity_db.web import create_app_from_database_set
from tools.browser_wsgi_transport import wsgi_response

RELEASE = Path(__file__).resolve().parents[1] / "data/generated"


@pytest.fixture
def project(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> tuple[Path, argparse.Namespace]:
    root = tmp_path / "project"
    for name in (
        "pyproject.toml",
        "src/sample.py",
        "data/curated/rules/sample.json",
        "data/curated/rules/n5-its-season-18-2026.09.01.json",
        "data/manifests/symbol-publication.json",
        "src/infinity_db/web/static/restrictions-reference.json",
        "config/catalogs/equipment-presentation-encodings.json",
        "config/catalogs/skill-source-classifications.json",
        "config/catalogs/unit-filter-semantics.json",
        "data/curated/identities/army-overview.json",
        "data/curated/identities/legacy-armies.json",
        "tools/build_weapon_profile_publication.py",
        "tools/audit_enrichment_coverage.py",
        "tools/audit_weapon_definition_gaps.py",
    ):
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("{}", encoding="utf-8")
    shutil.copyfile(
        RELEASE.parent.parent / "data/curated/rules/n5-its-season-18-2026.09.01.json",
        root / "data/curated/rules/n5-its-season-18-2026.09.01.json",
    )
    shutil.copyfile(
        RELEASE.parent.parent / "config/catalogs/equipment-presentation-encodings.json",
        root / "config/catalogs/equipment-presentation-encodings.json",
    )
    shutil.copyfile(
        RELEASE.parent.parent / "config/catalogs/skill-source-classifications.json",
        root / "config/catalogs/skill-source-classifications.json",
    )
    shutil.copyfile(
        RELEASE.parent.parent / "config/catalogs/unit-filter-semantics.json",
        root / "config/catalogs/unit-filter-semantics.json",
    )
    for name in ("army-overview.json", "legacy-armies.json"):
        shutil.copyfile(
            RELEASE.parent.parent / "data/curated/identities" / name,
            root / "data/curated/identities" / name,
        )
    source = root / "army.zip"
    with zipfile.ZipFile(source, "w") as archive:
        archive.writestr("metadata.json", json.dumps({"factions": [{"id": 1, "name": "Test"}]}))
    symbols = json.loads(
        (RELEASE.parent / "manifests/symbol-publication.json").read_text(encoding="utf-8")
    )
    symbols["sourceSnapshot"]["armyArtifact"]["sha256"] = file_sha256(source)
    (root / "data/manifests/symbol-publication.json").write_text(
        json.dumps(symbols),
        encoding="utf-8",
    )
    for relative in symbols["publishedSha256ByPath"]:
        target = root / "src/infinity_db/web/static" / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(RELEASE.parent.parent / "src/infinity_db/web/static" / relative, target)
    args = build_parser().parse_args(["build", str(source), "--db-dir", str(root / "output")])
    # This synthetic builder fixture deliberately writes "build-only" instead
    # of a real normalized document. Keep its existing raw-pair overlay path;
    # real normalized-source acceptance is covered by the pinned ZIP rebuild.
    for name in (
        "publish_equipment_encodings", "publish_skill_classifications",
        "publish_unit_filter_semantics", "publish_army_reference_data",
        "publish_symbol_paths",
    ):
        publisher = getattr(builder, name)

        def legacy_source(
            army: Path, _raw: Path | None, *sources: Path,
            normalized: Path | None = None, _publisher=publisher,
        ) -> None:
            assert _raw is None and normalized == army.with_name("normalized.json")
            _publisher(army, army.with_name("army.raw.db"), *sources)

        monkeypatch.setattr(builder, name, legacy_source)
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
    army = args.output_dir / "army.db"
    shutil.copyfile(RELEASE / "army.db", army)
    # Recreate the maintained base exporter boundary before running real overlays.
    with closing(sqlite3.connect(army)) as db, db:
        for name in (
            "equipment_presentation_metadata",
            "equipment_presentation_encodings",
            "skill_source_classification_metadata",
            "skill_source_classifications",
            "unit_filter_metadata",
            "hidden_unit_characteristics",
            "source_classification_memberships",
            "source_classification_matches",
            "army_reference_metadata",
            "legacy_army_identities",
            "army_overview_text",
            "symbol_path_metadata",
            "published_symbol_assets",
            "published_symbol_paths",
        ):
            db.execute(f"DROP TABLE IF EXISTS {name}")
        db.execute("PRAGMA user_version=26")
        db.execute(
            "UPDATE __infinity_metadata SET value='35' WHERE key='database_compatibility_version'"
        )
    with closing(sqlite3.connect(army)) as connection:
        meta = {
            key: json.loads(value)
            for key, value in connection.execute("SELECT key,value FROM __infinity_metadata")
        }
    meta["_meta"]["snapshotArchiveSha256"] = record["manifest"]["source"]["archiveSha256"]
    meta["armyMetadata"]["sourceSha256"] = record["manifest"]["source"]["metadataSha256"]
    meta["armyMetadata"]["sourceFile"] = record["manifest"]["source"]["metadataName"]
    _update_metadata(
        army,
        {
            BUILD_PROVENANCE_KEY: record,
            "_meta": meta["_meta"],
            "armyMetadata": meta["armyMetadata"],
        },
    )
    shutil.copyfile(army, args.output_dir / "army.raw.db")
    (args.output_dir / "normalized.json").write_text("build-only", encoding="utf-8")
    return 0


def _fake_rules(stage: Path, root: Path, manifest: dict[str, Any]) -> None:
    """Use the current complete semantic fixture with this build generation."""
    from infinity_db.rules_database import RulesDatabase
    from infinity_db.variant_usage_storage import _fingerprint
    from infinity_db.weapon_profile_storage import _digest, _read_document

    army, rules = stage / "army.db", stage / "rules_n5.db"
    shutil.copyfile(RELEASE / "rules_n5.db", rules)
    with closing(sqlite3.connect(rules)) as connection:
        document = _read_document(connection)
    document["sourceSnapshot"]["armyDatabaseSha256"] = file_sha256(army)
    with closing(sqlite3.connect(army)) as connection:
        generation = json.loads(
            connection.execute(
                "SELECT value FROM __infinity_metadata WHERE key='export_pair_sha256'"
            ).fetchone()[0]
        )
    publication = RulesDatabase(RELEASE / "rules_n5.db").variant_usage_payload(RELEASE / "army.db")
    assert publication is not None
    publication["sourceSnapshot"].update(
        armyDatabaseSha256=file_sha256(army),
        armyArchiveSha256=manifest["source"]["archiveSha256"],
        exportPairSha256=generation,
    )
    with closing(sqlite3.connect(rules)) as connection, connection:
        connection.execute(
            "UPDATE deployed_object_metadata SET value=? WHERE key='armyDatabaseSha256'",
            (json.dumps(file_sha256(army)),),
        )
        for (table,) in connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name LIKE '%metadata'"
        ).fetchall():
            columns = {row[1] for row in connection.execute(f"PRAGMA table_info({table})")}
            if "army_database_sha256" in columns:
                connection.execute(
                    f"UPDATE {table} SET army_database_sha256=?", (file_sha256(army),)
                )
        connection.execute(
            "UPDATE variant_usage_metadata SET army_archive_sha256=?,content_sha256=?",
            (manifest["source"]["archiveSha256"], _fingerprint(publication)),
        )
    with closing(sqlite3.connect(rules)) as connection, connection:
        connection.execute(
            "UPDATE weapon_chart_profile_metadata SET content_sha256=?", (_digest(document),)
        )
    _update_metadata(
        rules,
        {
            BUILD_PROVENANCE_KEY: build_record(manifest, "rules-n5", army_generation=generation),
        },
        rules=True,
    )


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


def test_maintained_text_inputs_ignore_checkout_line_endings(project) -> None:
    root, args = project
    original = builder.collect_build_manifest(root, args.source, None)
    paths = (
        "config/catalogs/equipment-presentation-encodings.json",
        "data/curated/rules/sample.json",
        "data/manifests/symbol-publication.json",
        "src/infinity_db/web/static/restrictions-reference.json",
        "pyproject.toml",
    )
    for name in paths:
        path = root / name
        data = path.read_bytes().replace(b"\\r\\n", b"\\n")
        path.write_bytes(data.replace(b"\\n", b"\\r\\n"))
    assert builder.collect_build_manifest(root, args.source, None) == original

    config = root / paths[0]
    config.write_bytes(config.read_bytes() + b" ")
    assert builder.collect_build_manifest(root, args.source, None) != original


def test_builder_code_and_selected_metadata_are_inputs(project) -> None:
    root, args = project
    original = builder.collect_build_manifest(root, args.source, None)
    web = root / "src/infinity_db/web"
    web.mkdir(parents=True, exist_ok=True)
    (web / "api_handler.py").write_text("# serving-only change\n", encoding="utf-8")
    assert builder.collect_build_manifest(root, args.source, None) == original
    (root / "src/sample.py").write_text("# changed\n", encoding="utf-8")
    code_change = builder.collect_build_manifest(root, args.source, None)
    assert code_change["builderRevision"] != original["builderRevision"]
    (root / "src/sample.py").write_bytes(b"# changed\r\n")
    assert builder.collect_build_manifest(root, args.source, None) == code_change
    # Historical audits are now independent diagnostics, not build inputs.
    (root / "tools/audit_enrichment_coverage.py").write_text("changed", encoding="utf-8")
    (root / "tools/audit_weapon_definition_gaps.py").write_text("changed", encoding="utf-8")
    assert builder.collect_build_manifest(root, args.source, None) == code_change
    metadata = root / "other-metadata.json"
    metadata.write_text('{"factions":[{"id":2,"name":"Other"}]}', encoding="utf-8")
    selected = builder.collect_build_manifest(root, args.source, metadata)
    assert selected["source"]["metadataSha256"] != code_change["source"]["metadataSha256"]


def test_complete_build_publishes_only_selected_files_and_is_repeatable(
    project,
    monkeypatch: pytest.MonkeyPatch,
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
    assert first["layout"] == "v17-three-file"
    assert first["seasons"]["its-18"]["revision"] == "2026.09.01"
    assert first["restrictionChartRows"] == 6
    assert first["traitWikiLinks"] == 33
    assert first["combinedSavingRollProfiles"] == 6
    assert first["ammunitionReferences"] == 16
    assert first["weaponProperties"] == 12
    assert first["equipmentPresentationEncodings"] == 2
    assert first["skillSourceClassifications"] == 6
    assert first["reviewedWeapons"] == 62
    assert validate_database_set(args.db_dir)["sha256"] == first["sha256"]
    assert set(_digests(args.db_dir)) == {*COMPLETE_RUNTIME_FILES, "keep.txt"}
    assert (args.db_dir / "keep.txt").read_text(encoding="utf-8") == "unrelated"
    app = create_app_from_database_set(args.db_dir)
    assert app.database.path == args.db_dir / "army.db"
    assert app.rules_database is not None
    assert app.rules_database.path == args.db_dir / "rules_n5.db"
    assert app.publication_registry is not None
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


def test_complete_startup_rejects_partial_formats_and_unrecorded_provenance(
    project,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root, args = project
    monkeypatch.setattr(builder, "_build_rules_and_publications", _fake_rules)
    builder.build_database_set(args, _fake_army, root=root)
    army, rules = args.db_dir / "army.db", args.db_dir / "rules_n5.db"
    original = {path: path.read_bytes() for path in (army, rules, args.db_dir / "its_18.db")}
    for case, message in (
        ("army", "require Army schema v31"),
        ("rules", "require Rules schema v17"),
        ("provenance", "require recorded matched build provenance"),
    ):
        if case == "provenance":
            for path, table in ((army, "__infinity_metadata"), (rules, "__rules_metadata")):
                with closing(sqlite3.connect(path)) as connection, connection:
                    connection.execute(f"DELETE FROM {table} WHERE key=?", (BUILD_PROVENANCE_KEY,))
        else:
            path, version = (army, 30) if case == "army" else (rules, 16)
            with closing(sqlite3.connect(path)) as connection, connection:
                connection.execute(f"PRAGMA user_version={version}")
        before = _digests(args.db_dir)
        with pytest.raises(ValueError, match=message):
            create_app_from_database_set(args.db_dir)
        assert _digests(args.db_dir) == before
        for path, content in original.items():
            path.write_bytes(content)


@pytest.mark.parametrize("failure", ["generation", "validation", "changed-input"])
def test_failure_before_publication_retains_all_destination_bytes(
    project,
    monkeypatch: pytest.MonkeyPatch,
    failure: str,
) -> None:
    root, args = project
    args.db_dir.mkdir()
    for name in COMPLETE_RUNTIME_FILES:
        shutil.copyfile(RELEASE / name, args.db_dir / name)
    before = _digests(args.db_dir)

    def fail(stage: Path, root: Path, manifest: dict[str, Any]) -> None:
        if failure == "generation":
            raise ValueError("deliberate source rejection")
        _fake_rules(stage, root, manifest)
        if failure == "validation":
            with closing(sqlite3.connect(stage / "rules_n5.db")) as connection, connection:
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
    project,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root, args = project
    args.db_dir.mkdir()
    for name in COMPLETE_RUNTIME_FILES:
        shutil.copyfile(RELEASE / name, args.db_dir / name)
    monkeypatch.setattr(builder, "_build_rules_and_publications", _fake_rules)
    replace = os.replace

    def interrupted(source: Path, destination: Path) -> None:
        if destination.name == "rules_n5.db":
            raise OSError("deliberate interrupted replacement")
        replace(source, destination)

    monkeypatch.setattr(builder.os, "replace", interrupted)
    with pytest.raises(OSError, match="interrupted"):
        builder.build_database_set(args, _fake_army, root=root)
    with pytest.raises(ValueError, match="generations do not match"):
        validate_database_set(args.db_dir)
    monkeypatch.setattr(builder.os, "replace", replace)
    builder.build_database_set(args, _fake_army, root=root)
    assert (
        validate_set_provenance(
            args.db_dir / "army.db",
            args.db_dir / "rules_n5.db",
        )["status"]
        == "matched"
    )


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
    "damage",
    ["id", "version", "mixed", "army-generation", "archive", "metadata"],
)
def test_recorded_provenance_rejects_tampered_or_mixed_inputs(
    project,
    monkeypatch: pytest.MonkeyPatch,
    damage: str,
) -> None:
    root, args = project
    monkeypatch.setattr(builder, "_build_rules_and_publications", _fake_rules)
    result = builder.build_database_set(args, _fake_army, root=root)
    manifest = builder.collect_build_manifest(root, args.source, None)
    army, rules = args.db_dir / "army.db", args.db_dir / "rules_n5.db"
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
            value = json.loads(
                connection.execute(
                    "SELECT value FROM __infinity_metadata WHERE key=?",
                    (key,),
                ).fetchone()[0]
            )
        value["snapshotArchiveSha256" if damage == "archive" else "sourceSha256"] = "0" * 64
        _update_metadata(army, {key: value})
    with pytest.raises(ValueError, match="provenance|generations|generation|manifest"):
        validate_set_provenance(army, rules)


def test_output_cannot_replace_the_selected_source_archive(project) -> None:
    root, args = project
    source = root / "army.db"
    shutil.copyfile(args.source, source)
    before = file_sha256(source)
    args.source, args.db_dir = source, root
    with pytest.raises(ValueError, match="replace an input"):
        builder.build_database_set(args, _fake_army, root=root)
    assert file_sha256(source) == before
    assert not (root / "data/work/build").exists()


def _pin_army_source_for_build(root: Path, args: argparse.Namespace) -> Path:
    """Give the existing synthetic builder fixture a valid source revision and v3 pin."""
    with zipfile.ZipFile(args.source, "a") as archive:
        archive.writestr(
            "101-first-army.json",
            json.dumps({"version": "7.26246.158", "units": []}),
        )
    symbols_path = root / "data/manifests/symbol-publication.json"
    symbols = json.loads(symbols_path.read_text(encoding="utf-8"))
    symbols["sourceSnapshot"]["armyArtifact"]["sha256"] = file_sha256(args.source)
    symbols_path.write_text(json.dumps(symbols), encoding="utf-8")
    return write_snapshot_manifest(
        args.source,
        root / "data/manifests/snapshots",
        snapshot_type="army",
        acquired_at=datetime(2026, 9, 17, 12, 0, tzinfo=UTC),
        source_url="https://api.corvusbelli.com/army",
        document_count=2,
        language="en",
        project_root=root,
        source_data_changed_on=date(2026, 9, 3),
    )


def test_pinned_army_build_selection_preserves_legacy_cli_contract() -> None:
    app = build_parser().parse_args(["build"])
    assert app.source is None and app.snapshot_manifest is None
    assert app.db_dir == Path("data/generated")
    pinned = build_parser().parse_args([
        "build", "local/data/raw/army/source.zip",
        "--snapshot-manifest", "local/data/manifests/snapshots/source.json",
        "--db-dir", "local/work/test-databases",
    ])
    assert pinned.source == Path("local/data/raw/army/source.zip")
    assert pinned.snapshot_manifest == Path(
        "local/data/manifests/snapshots/source.json"
    )
    assert pinned.db_dir == Path("local/work/test-databases")
    with pytest.raises(SystemExit):
        army_parser().parse_args(["build", "--snapshot-manifest", "a.json"])


def test_pinned_army_build_requires_unambiguous_explicit_inputs(project) -> None:
    root, args = project
    manifest = _pin_army_source_for_build(root, args)
    args.snapshot_manifest = manifest
    selected = args.source
    args.source = None
    with pytest.raises(ValueError, match="requires an explicit Army ZIP"):
        builder.build_database_set(args, _fake_army, root=root)
    args.source = selected
    args.metadata = root / "other-metadata.json"
    with pytest.raises(ValueError, match="cannot combine with --metadata"):
        builder.build_database_set(args, _fake_army, root=root)
    assert not args.db_dir.exists()
    assert not (root / "data/work/build").exists()


@pytest.mark.parametrize("layout", ("data/raw", "local/data/raw/army"))
def test_pinned_source_selection_uses_explicit_archive_not_implicit_newest(
    project, monkeypatch: pytest.MonkeyPatch, layout: str,
) -> None:
    root, args = project
    manifest = _pin_army_source_for_build(root, args)
    selected = root / layout / args.source.name
    selected.parent.mkdir(parents=True)
    shutil.copyfile(args.source, selected)
    args.source = selected
    args.snapshot_manifest = manifest
    monkeypatch.setattr(
        builder, "latest_snapshot",
        lambda: pytest.fail("Pinned build must never select the newest ZIP"),
    )
    expected = builder.collect_build_manifest(
        root, selected, None, snapshot_manifest=manifest,
    )
    assert expected["source"]["archiveSha256"] == file_sha256(selected)
    assert expected["source"]["metadataName"] == "metadata.json"
    assert not args.db_dir.exists()
    assert not (root / "data/work/build").exists()


def test_pinned_complete_build_produces_same_three_database_set_from_both_layouts(
    project, monkeypatch: pytest.MonkeyPatch,
) -> None:
    root, args = project
    manifest = _pin_army_source_for_build(root, args)
    local_source = root / "local/data/raw/army" / args.source.name
    local_source.parent.mkdir(parents=True)
    shutil.copyfile(args.source, local_source)
    local_manifest = root / "local/data/manifests/snapshots" / manifest.name
    local_manifest.parent.mkdir(parents=True)
    shutil.copyfile(manifest, local_manifest)

    monkeypatch.setattr(builder, "_build_rules_and_publications", _fake_rules)
    monkeypatch.setattr(
        builder, "latest_snapshot",
        lambda: pytest.fail("Explicit source must not use latest_snapshot"),
    )
    args.snapshot_manifest = manifest
    legacy_result = builder.build_database_set(args, _fake_army, root=root)
    legacy_digests = {
        filename: file_sha256(args.db_dir / filename)
        for filename in COMPLETE_RUNTIME_FILES
    }
    assert legacy_result["buildProvenance"]["status"] == "matched"

    args.source = local_source
    args.snapshot_manifest = local_manifest
    local_result = builder.build_database_set(args, _fake_army, root=root)
    assert local_result["buildProvenance"]["status"] == "matched"
    assert local_result["buildProvenance"]["buildSetId"] == (
        legacy_result["buildProvenance"]["buildSetId"]
    )
    assert {
        filename: file_sha256(args.db_dir / filename)
        for filename in COMPLETE_RUNTIME_FILES
    } == legacy_digests


def test_pinned_build_rejects_changed_archive_before_any_publication(
    project,
) -> None:
    root, args = project
    manifest = _pin_army_source_for_build(root, args)
    args.snapshot_manifest = manifest
    with zipfile.ZipFile(args.source, "a") as archive:
        archive.writestr("new-source.json", "{}")
    with pytest.raises(SnapshotProvenanceError, match="SHA-256 mismatch"):
        builder.build_database_set(args, _fake_army, root=root)
    assert not args.db_dir.exists()
    assert not (root / "data/work/build").exists()


def test_pinned_build_rejects_conflicting_sidecar_before_any_publication(
    project,
) -> None:
    root, args = project
    manifest = _pin_army_source_for_build(root, args)
    args.snapshot_manifest = manifest
    args.source.with_name("metadata.json").write_text(
        '{"factions":[{"id":9,"name":"Unrelated"}]}', encoding="utf-8",
    )
    with pytest.raises(ValueError, match="Ambiguous Army metadata"):
        builder.build_database_set(args, _fake_army, root=root)
    assert not args.db_dir.exists()
    assert not (root / "data/work/build").exists()


def test_pinned_build_rejects_manifest_modified_during_generation(
    project, monkeypatch: pytest.MonkeyPatch,
) -> None:
    root, args = project
    manifest = _pin_army_source_for_build(root, args)
    args.snapshot_manifest = manifest
    args.db_dir.mkdir()
    for name in COMPLETE_RUNTIME_FILES:
        shutil.copyfile(RELEASE / name, args.db_dir / name)
    before = _digests(args.db_dir)

    def rewrite_provenance(stage: Path, root: Path, record: dict[str, Any]) -> None:
        _fake_rules(stage, root, record)
        document = json.loads(manifest.read_text(encoding="utf-8"))
        document["source"]["url"] = "https://api.corvusbelli.com/army-modified"
        manifest.write_text(json.dumps(document), encoding="utf-8")

    monkeypatch.setattr(builder, "_build_rules_and_publications", rewrite_provenance)
    with pytest.raises(ValueError, match="Build inputs changed"):
        builder.build_database_set(args, _fake_army, root=root)
    assert _digests(args.db_dir) == before
    assert not list((root / "data/work/build").iterdir())


def test_runtime_and_narrow_build_outputs_are_explicitly_exclusive() -> None:
    with pytest.raises(SystemExit):
        build_parser().parse_args(["build", "--db-dir", "one", "--output-dir", "two"])
    with pytest.raises(SystemExit):
        army_parser().parse_args(["build", "--db-dir", "one"])
