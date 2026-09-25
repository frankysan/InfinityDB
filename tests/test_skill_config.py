from __future__ import annotations

import json
from pathlib import Path

import pytest

from infinity_db.skill_config import (
    SkillConfigError,
    load_skill_source_config,
    parse_skill_source_config,
)


def _document() -> dict:
    return json.loads(
        Path("config/catalogs/skill-source-classifications.json").read_text(encoding="utf-8")
    )


def test_checked_in_skill_source_classifications_cover_known_non_skills() -> None:
    classifications = load_skill_source_config()

    assert {
        (item.skill_ref, item.classification)
        for item in classifications
    } == {
        ("bangbomb", "equipment"),
        ("bts-3", "attribute-override"),
        ("gizmokit", "equipment"),
        ("infinity-team-ops", "source-marker"),
        ("medikit", "equipment"),
        ("regular", "training"),
    }


def test_skill_source_classification_config_accepts_numeric_references() -> None:
    document = _document()
    document["classifications"][0]["skill_id"] = 123

    parsed = parse_skill_source_config(document)

    assert parsed[0].skill_ref == 123


def test_skill_source_classification_config_rejects_unknown_classification() -> None:
    document = _document()
    document["classifications"][0]["classification"] = "not-a-domain"

    with pytest.raises(SkillConfigError, match="classification must be one of"):
        parse_skill_source_config(document)
