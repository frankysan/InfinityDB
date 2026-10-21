"""Release-time generation and fail-closed loading of deployed-object references."""

from __future__ import annotations

import copy
import json
import shutil
from pathlib import Path

import pytest

from infinity_db.deployed_object_publication import load_deployed_object_publication
from tools.build_deployed_object_publication import build_publication, publication_bytes


@pytest.fixture(scope="module")
def source_paths() -> tuple[Path, Path, Path, Path, Path]:
    root = Path(__file__).resolve().parents[1]
    files = (
        root / "data/generated/infinity.db",
        root / "data/generated/rules.db",
        root / "data/curated/rules/n5-core-v5.3.json",
        root / "config/validation/deployed-object-delivery-reviews.json",
        root / "config/validation/deployed-object-candidate-reviews.json",
    )
    if not all(path.is_file() for path in files):
        pytest.skip("Pinned release source inputs unavailable")
    return files


def test_pinned_publication_is_deterministic_and_source_complete(
    source_paths: tuple[Path, Path, Path, Path, Path], tmp_path: Path,
) -> None:
    publication = build_publication(*source_paths)
    assert publication_bytes(publication) == publication_bytes(build_publication(*source_paths))
    assert len(publication["objects"]) == 17
    assert len(publication["unresolvedDeliveries"]) == 1
    path = tmp_path / "deployed-objects.json"
    path.write_bytes(publication_bytes(publication))
    assert load_deployed_object_publication(path, source_paths[0], source_paths[1]) == (
        publication
    )


def test_publication_missing_is_legacy_compatible_but_corrupt_fails_closed(
    source_paths: tuple[Path, Path, Path, Path, Path], tmp_path: Path,
) -> None:
    output = tmp_path / "deployed-objects.json"
    assert load_deployed_object_publication(output, source_paths[0], source_paths[1]) is None
    output.write_text("{", encoding="utf-8", newline="\n")
    with pytest.raises(ValueError, match="JSON"):
        load_deployed_object_publication(output, source_paths[0], source_paths[1])

    output.write_bytes(publication_bytes(build_publication(*source_paths)))
    with pytest.raises(ValueError, match="requires a rules database"):
        load_deployed_object_publication(output, source_paths[0], None)
    wrong = tmp_path / "wrong.db"
    shutil.copyfile(source_paths[1], wrong)
    wrong.write_bytes(b"wrong")
    with pytest.raises(ValueError, match="does not match"):
        load_deployed_object_publication(output, source_paths[0], wrong)


def test_publication_rejects_identity_value_and_delivery_tampering(
    source_paths: tuple[Path, Path, Path, Path, Path], tmp_path: Path,
) -> None:
    original = build_publication(*source_paths)
    output = tmp_path / "deployed-objects.json"

    def rejected(document: dict, message: str) -> None:
        output.write_text(json.dumps(document), encoding="utf-8", newline="\n")
        with pytest.raises(ValueError, match=message):
            load_deployed_object_publication(output, source_paths[0], source_paths[1])

    changed = copy.deepcopy(original)
    changed["objects"].append(copy.deepcopy(changed["objects"][0]))
    rejected(changed, "duplicate deployed-object identity")

    changed = copy.deepcopy(original)
    changed["objects"][0]["attributes"]["S"] = {
        "status": "unreported", "value": "0", "provenance": [],
    }
    rejected(changed, "cannot invent a value")

    changed = copy.deepcopy(original)
    disputed = next(
        row for row in changed["objects"] if row["attributes"]["S"]["status"] == "disputed"
    )
    disputed["attributes"]["S"]["provenance"] = []
    rejected(changed, "missing source provenance")

    changed = copy.deepcopy(original)
    changed["objects"][0]["deliverySources"] = [{"recordId": "weapon:pitcher"}]
    rejected(changed, "reviewed delivery edge")
