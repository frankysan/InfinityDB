"""SQLite deployed-object projection: normalized persistence and source pairing."""
from __future__ import annotations

import json
import shutil
import sqlite3
from pathlib import Path
from wsgiref.util import setup_testing_defaults

import pytest

from infinity_db.deployed_object_storage import (
    read_deployed_objects,
    stage_deployed_objects,
)
from tools.build_deployed_object_publication import build_publication


@pytest.fixture(scope="module")
def pinned_inputs() -> tuple[Path, ...]:
    root = Path(__file__).resolve().parents[1]
    paths = (
        root / "data/generated/infinity.db",
        root / "data/generated/rules.db",
        root / "data/curated/rules/n5-core-v5.3.json",
        root / "config/validation/deployed-object-delivery-reviews.json",
        root / "config/validation/deployed-object-candidate-reviews.json",
    )
    if not all(path.is_file() for path in paths):
        pytest.skip("Pinned source and release files are unavailable")
    return paths


def test_normalized_snapshot_round_trips_exact_reviewed_projection(
    pinned_inputs: tuple[Path, ...],
) -> None:
    publication = build_publication(*pinned_inputs)
    with sqlite3.connect(":memory:") as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        stage_deployed_objects(connection, publication)
        rebuilt = read_deployed_objects(connection, pinned_inputs[0])
        expected = {
            **publication,
            "sourceSnapshot": {
                key: value for key, value in publication["sourceSnapshot"].items()
                if key != "rulesDatabaseSha256"
            },
        }
        assert rebuilt == expected
        assert len(rebuilt["objects"]) == 17
        assert len(rebuilt["unresolvedDeliveries"]) == 1
        assert connection.execute("PRAGMA foreign_key_check").fetchall() == []



def test_v10_runtime_serves_embedded_deployed_objects_without_json(
    pinned_inputs: tuple[Path, ...], tmp_path: Path,
) -> None:
    from infinity_db.cli import build_parser, cmd_build_rules
    from infinity_db.web import create_app

    army = tmp_path / "infinity.db"
    rules = tmp_path / "rules.db"
    shutil.copyfile(pinned_inputs[0], army)
    args = build_parser().parse_args([
        "build-rules", "--army-db", str(army), "--output", str(rules),
    ])
    assert cmd_build_rules(args) == 0
    assert not (tmp_path / "deployed-objects.json").exists()
    application = create_app(army, rules)
    assert application.deployed_objects is not None
    assert len(application.deployed_objects["objects"]) == 17

    staged_rules = tmp_path / "staging" / "rules.db"
    staged_rules.parent.mkdir()
    shutil.copyfile(rules, staged_rules)
    preview = create_app(army, staged_rules)
    assert preview.deployed_objects is not None
    assert len(preview.deployed_objects["objects"]) == 17

    environ: dict[str, str] = {}
    setup_testing_defaults(environ)
    environ.update(REQUEST_METHOD="GET", PATH_INFO="/api/deployed-objects")
    statuses: list[str] = []

    def start_response(status: str, _headers: object, _exc_info: object = None) -> None:
        statuses.append(status)

    payload = json.loads(b"".join(application(environ, start_response)))
    assert statuses[0].startswith("200")
    assert len(payload["items"]) == 17
    assert payload["scope"] == "reviewed-projection-not-complete-unit-usage"
    assert len(payload["unresolved_deliveries"]) == 1


def test_v10_variant_usage_publication_needs_no_deployed_json(
    pinned_inputs: tuple[Path, ...], tmp_path: Path,
) -> None:
    from infinity_db.cli import build_parser, cmd_build_rules
    from infinity_db.variant_usage import build_variant_usage_projection
    from infinity_db.variant_usage_reference import (
        load_variant_usage_publication,
        publication_from_candidate,
    )

    root = Path(__file__).resolve().parents[1]
    raw = root / "data/generated/infinity.raw.db"
    if not raw.is_file():
        pytest.skip("Matched raw Army archive is unavailable")
    army = tmp_path / "infinity.db"
    rules = tmp_path / "rules.db"
    shutil.copyfile(pinned_inputs[0], army)
    args = build_parser().parse_args([
        "build-rules", "--army-db", str(army), "--output", str(rules),
    ])
    assert cmd_build_rules(args) == 0
    missing_json = tmp_path / "deployed-objects.json"
    candidate = build_variant_usage_projection(army, raw, rules)
    assert "deployedObjectPublicationSha256" not in candidate["sourceSnapshot"]
    publication = publication_from_candidate(candidate)
    assert publication["formatVersion"] == 2
    output = tmp_path / "variant-usage.json"
    output.write_text(json.dumps(publication), encoding="utf-8")
    assert load_variant_usage_publication(output, army, rules, missing_json) == publication



def test_v10_validator_rejects_missing_embedded_table(tmp_path: Path) -> None:
    from infinity_db.cli import build_parser, cmd_build_rules
    from infinity_db.rules_database import RulesDatabase

    output = tmp_path / "candidate.db"
    args = build_parser().parse_args(["build-rules", "--output", str(output)])
    assert cmd_build_rules(args) == 0
    with sqlite3.connect(output) as connection:
        connection.execute("DROP TABLE deployed_object_unresolved")
    with pytest.raises(ValueError, match="Incomplete normalized deployed-object schema"):
        RulesDatabase(output).validate()


def test_v10_standalone_build_is_deterministic(tmp_path: Path) -> None:
    from infinity_db.cli import build_parser, cmd_build_rules

    outputs = [tmp_path / name for name in ("first.db", "second.db")]
    for output in outputs:
        args = build_parser().parse_args(["build-rules", "--output", str(output)])
        assert cmd_build_rules(args) == 0
    assert outputs[0].read_bytes() == outputs[1].read_bytes()



def test_complete_v10_candidate_bundle_has_no_deployed_object_json(
    pinned_inputs: tuple[Path, ...], tmp_path: Path,
) -> None:
    from tools.build_v10_runtime_candidate import (
        REQUIRED,
        build_candidate,
        verify_candidate,
    )
    from tools.prepare_runtime_bundle import prepare_bundle

    root = Path(__file__).resolve().parents[1]
    if not (root / "data/generated/infinity.raw.db").is_file():
        pytest.skip("Matched raw Army archive is unavailable")
    candidate = tmp_path / "candidate"
    result = build_candidate(candidate)
    assert result["schemaVersion"] == 10
    assert result["variantPublicationVersion"] == 2
    assert result["deployedObjects"] == 17
    assert {path.name for path in candidate.iterdir()} == REQUIRED
    bundle = tmp_path / "bundle"
    assert prepare_bundle(candidate, bundle) == REQUIRED
    assert {path.name for path in bundle.iterdir()} == REQUIRED
    assert verify_candidate(candidate)["sha256"] == result["sha256"]

    import tempfile

    from infinity_db.checkout_runtime import select_checkout_database
    from tools.build_v10_runtime_candidate import publish_checkout_runtime

    (root / "local").mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(
        prefix="checkout-test-", dir=root / "local",
    ) as directory:
        checkout = Path(directory) / "checkout-runtime"
        published = publish_checkout_runtime(candidate / "rules.db", checkout)
        assert published["sha256"] == result["sha256"]
        assert {path.name for path in checkout.iterdir()} == REQUIRED
        assert select_checkout_database(
            tracked_army=pinned_inputs[0], standalone_rules=candidate / "rules.db",
            checkout=checkout,
        ) == checkout / "infinity.db"

    (candidate / "weapon-profile-sources.json").write_bytes(b"stale")
    with pytest.raises(ValueError, match="differs from reviewed inputs"):
        verify_candidate(candidate)


@pytest.mark.parametrize("schema", (8, 9))
def test_legacy_image_bundle_is_rejected_before_modifying_output(
    pinned_inputs: tuple[Path, ...], tmp_path: Path,
    schema: int,
) -> None:
    from tools.prepare_runtime_bundle import prepare_bundle

    source = tmp_path / "source"
    source.mkdir()
    shutil.copyfile(pinned_inputs[0], source / "infinity.db")
    shutil.copyfile(pinned_inputs[1], source / "rules.db")
    with sqlite3.connect(source / "rules.db") as connection:
        connection.execute(f"PRAGMA user_version={schema}")
    (source / "deployed-objects.json").write_text("{", encoding="utf-8")
    output = tmp_path / "bundle"
    output.mkdir()
    sentinel = output / "keep.txt"
    sentinel.write_bytes(b"retained")
    with pytest.raises(ValueError, match="Unsupported Rules schema"):
        prepare_bundle(source, output)
    assert {path.name for path in output.iterdir()} == {"keep.txt"}
    assert sentinel.read_bytes() == b"retained"


def test_normalized_snapshot_rejects_mismatched_army_sha(
    pinned_inputs: tuple[Path, ...],
) -> None:
    publication = build_publication(*pinned_inputs)
    with sqlite3.connect(":memory:") as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        stage_deployed_objects(connection, publication)
        connection.execute(
            "UPDATE deployed_object_metadata SET value = ? WHERE key = ?",
            ('"not-the-army-sha"', "armyDatabaseSha256"),
        )
        with pytest.raises(ValueError, match="do not match"):
            read_deployed_objects(connection, pinned_inputs[0])
