"""P2.3 embedded Weapon Chart citations: exact source, mode and Army pairing."""

from __future__ import annotations

import json
import shutil
import sqlite3
from copy import deepcopy
from pathlib import Path

import pytest

from infinity_db.weapon_profile_publication import load_weapon_profile_publication
from infinity_db.weapon_profile_storage import (
    read_weapon_profile_citations,
    stage_weapon_profile_citations,
    validate_weapon_profile_snapshot,
)

ROOT = Path(__file__).resolve().parents[1]
RELEASE = ROOT / "data/generated"
ARMY = RELEASE / "infinity.db"
SIDECAR = RELEASE / "weapon-profile-sources.json"


@pytest.fixture
def embedded(tmp_path: Path) -> tuple[Path, dict]:
    path = tmp_path / "rules.db"
    shutil.copyfile(RELEASE / "rules.db", path)
    document = json.loads(SIDECAR.read_text(encoding="utf-8"))
    with sqlite3.connect(path) as connection:
        connection.execute("PRAGMA foreign_keys=ON")
        with connection:
            stage_weapon_profile_citations(connection, document, ARMY)
        assert connection.execute("PRAGMA foreign_key_check").fetchall() == []
    return path, document


def test_embedded_citations_match_the_current_api_publication(embedded) -> None:
    path, document = embedded
    with sqlite3.connect(path) as connection:
        validate_weapon_profile_snapshot(connection)
        actual = read_weapon_profile_citations(connection, ARMY)
    expected = load_weapon_profile_publication(SIDECAR, ARMY, RELEASE / "rules.db")
    assert actual == expected
    assert len({key[0] for key in actual}) == len(document["weapons"]) == 62
    assert len(actual) == sum(len(weapon["profiles"]) for weapon in document["weapons"]) == 69
    assert any(mode is None for _, _, mode in actual)
    assert any(mode is not None for _, _, mode in actual)


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        ("source", "differs from current Rules"),
        ("army", "Army/review provenance"),
        ("review", "Army/review provenance"),
        ("profile", "profile identity changed"),
        ("mode", "modes do not match"),
        ("duplicate", "duplicate reviewed Weapon mode"),
        ("page", "Invalid or duplicate reviewed Weapon mode"),
    ],
)
def test_rejects_mixed_or_ambiguous_curation(
    tmp_path: Path, mutation: str, message: str,
) -> None:
    document = json.loads(SIDECAR.read_text(encoding="utf-8"))
    reviewed = next(row for row in document["weapons"] if row["slug"] == "uragan-mrl")
    if mutation == "source":
        document["source"]["sha256"] = "0" * 64
    elif mutation == "army":
        document["sourceSnapshot"]["armyDatabaseSha256"] = "0" * 64
    elif mutation == "review":
        document["sourceSnapshot"]["reviewsSha256"] = "not-a-hash"
    elif mutation == "profile":
        reviewed["profileSha256"] = "0" * 64
    elif mutation == "mode":
        reviewed["profiles"][0]["mode"] = "Unreviewed"
    elif mutation == "duplicate":
        reviewed["profiles"].append(deepcopy(reviewed["profiles"][0]))
    elif mutation == "page":
        reviewed["profiles"][0]["page"] = 999
    path = tmp_path / "rules.db"
    shutil.copyfile(RELEASE / "rules.db", path)
    with sqlite3.connect(path) as connection:
        with pytest.raises(ValueError, match=message):
            stage_weapon_profile_citations(connection, document, ARMY)


def test_modified_embedded_citation_fails_content_fingerprint(embedded) -> None:
    path, _ = embedded
    with sqlite3.connect(path) as connection:
        connection.execute("UPDATE weapon_chart_profile_citations SET page=page+1 WHERE rowid=("
                           "SELECT min(rowid) FROM weapon_chart_profile_citations)")
        with pytest.raises(ValueError, match="fingerprint differs"):
            validate_weapon_profile_snapshot(connection)


def test_embedding_does_not_require_sidecar_for_read(embedded) -> None:
    path, _ = embedded
    with sqlite3.connect(path) as connection:
        assert read_weapon_profile_citations(connection, ARMY)
    assert not (path.parent / "weapon-profile-sources.json").exists()
