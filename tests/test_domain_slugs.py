from __future__ import annotations

import pytest

from infinity_db.domain_slugs import (
    assign_domain_slugs,
    normalize_domain_slug,
    require_domain_slug,
    resolve_domain_slug_candidates,
    validate_assigned_domain_slugs,
    validate_typed_domain_id,
)


def test_normalize_domain_slug_is_case_accent_and_punctuation_insensitive() -> None:
    assert normalize_domain_slug("Zúyŏng Invincibles") == "zuyong-invincibles"
    assert normalize_domain_slug("CC Attack (+3)") == "cc-attack-3"
    assert normalize_domain_slug("  MULTI  Rifle  ") == "multi-rifle"


def test_assigned_domain_slugs_must_use_canonical_syntax() -> None:
    assert require_domain_slug("doctor", context="skill slug") == "doctor"

    with pytest.raises(ValueError, match="lowercase ASCII slug"):
        require_domain_slug("Doctor", context="skill slug")


def test_provisional_candidate_resolution_records_unresolved_states() -> None:
    resolved = resolve_domain_slug_candidates(
        [(1, "Alpha"), (2, "Alpha"), (3, "!!!"), (4, "Beta")],
        domain="units",
    )

    assert resolved[1].candidate_slug == "alpha"
    assert resolved[1].slug is None
    assert resolved[1].status == "collision"
    assert resolved[2].status == "collision"
    assert resolved[3].candidate_slug is None
    assert resolved[3].status == "unavailable"
    assert resolved[4].slug == "beta"
    assert resolved[4].status == "resolved"


def test_candidate_collisions_fail_closed_instead_of_getting_numeric_suffixes() -> None:
    with pytest.raises(ValueError, match="slug collision 'cc-attack-3'"):
        assign_domain_slugs(
            [(1, "CC Attack (+3)"), (2, "CC Attack (-3)")],
            domain="traits",
        )


def test_assigned_slug_collisions_are_scoped_to_one_domain() -> None:
    validate_assigned_domain_slugs([(1, "doctor")], domain="skills")
    validate_assigned_domain_slugs([(7, "doctor")], domain="units")

    with pytest.raises(ValueError, match="assigned to both identities"):
        validate_assigned_domain_slugs([(1, "doctor"), (2, "doctor")], domain="skills")


def test_curated_typed_ids_use_kind_as_the_domain_prefix() -> None:
    assert (
        validate_typed_domain_id(
            "skill:doctor", expected_domain="skill", context="record id"
        )
        == "skill:doctor"
    )
    assert (
        validate_typed_domain_id(
            "skill-declaration-category:automatic:p86",
            expected_domain="skill-declaration-category",
            context="record id",
        )
        == "skill-declaration-category:automatic:p86"
    )

    with pytest.raises(ValueError, match="must start with 'skill'"):
        validate_typed_domain_id(
            "equipment:doctor", expected_domain="skill", context="record id"
        )
