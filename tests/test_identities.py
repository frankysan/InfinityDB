from __future__ import annotations

from pathlib import Path

import pytest

from infinity_db.identities import (
    IDENTITY_CONFIG_METADATA_KEY,
    IDENTITY_CONFIG_SHA256_METADATA_KEY,
    IdentityConfigError,
    identity_metadata,
    load_identity_config,
    normalized_profile_identity,
    parse_identity_config,
    parse_identity_metadata,
)


@pytest.fixture
def identity_document() -> dict:
    return load_identity_config(Path("config/identity/source-identities.json")).document


def test_source_identity_manifest_contains_current_explicit_aliases() -> None:
    config = load_identity_config()

    assert config.canonical_unit_id(1690) == 300
    assert config.canonical_unit_id(11345) == 1345
    assert config.canonical_army_id(998) == 999
    assert config.resolve_canonical_faction_id(1) == 1
    assert config.canonical_catalog_id("skills", 20) == 19
    assert config.canonical_catalog_id("skills", 70) == 69
    assert config.canonical_catalog_id("skills", 278) == 201
    assert config.canonical_catalog_id("equipment", 248) == 235
    assert config.canonical_catalog_id("weapons", 228) == 226
    assert config.catalog_source_ids("skills", 20) == (19, 20, 21, 22, 23)
    assert config.word_aliases["reconaissance"] == "recon"
    assert "intervention" in config.profile_identity_ignored_words


def test_profile_identity_uses_manifest_backed_policy() -> None:
    config = load_identity_config()

    assert (
        normalized_profile_identity(
            "REFUERZOS: R\u00e9conaissance Intervention Troops",
            config,
        )
        == "recon"
    )
    assert normalized_profile_identity("Armoured Unit", config) == "armored"


def test_default_identity_manifest_is_independent_of_working_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)

    config = load_identity_config()

    assert config.canonical_unit_id(1690) == 300


def test_unlisted_source_ids_are_not_implicitly_aliased() -> None:
    config = load_identity_config()

    assert config.canonical_unit_id(42) == 42
    assert config.canonical_army_id(101) == 101
    assert config.resolve_canonical_faction_id(101) == 101
    assert config.canonical_catalog_id("skills", 42) is None
    assert config.catalog_source_ids("skills", 42) == ()


def test_identity_metadata_contains_document_and_hash() -> None:
    config = load_identity_config()

    metadata = identity_metadata(config)

    assert metadata[IDENTITY_CONFIG_METADATA_KEY] == config.document
    assert metadata[IDENTITY_CONFIG_SHA256_METADATA_KEY] == config.content_sha256
    assert parse_identity_metadata(
        metadata[IDENTITY_CONFIG_METADATA_KEY],
        metadata[IDENTITY_CONFIG_SHA256_METADATA_KEY],
    ).content_sha256 == config.content_sha256


def test_identity_metadata_rejects_hash_mismatch() -> None:
    config = load_identity_config()

    with pytest.raises(IdentityConfigError, match="hash does not match"):
        parse_identity_metadata(config.document, "0" * 64)


def test_identity_config_rejects_overlapping_alias_groups(identity_document: dict) -> None:
    identity_document["units"]["groups"].append(
        {"canonical_id": 1690, "source_ids": [1690, 99999]}
    )

    with pytest.raises(IdentityConfigError, match="belongs to more than one alias group"):
        parse_identity_config(identity_document)


def test_identity_config_requires_canonical_id_in_group(identity_document: dict) -> None:
    identity_document["armies"]["groups"][0]["canonical_id"] = 997

    with pytest.raises(IdentityConfigError, match="must also appear in source_ids"):
        parse_identity_config(identity_document)


def test_identity_config_rejects_duplicate_canonical_faction_overrides(
    identity_document: dict,
) -> None:
    identity_document["canonical_faction_overrides"].extend(
        [
            {"source_id": 1, "canonical_faction_id": 901},
            {"source_id": 1, "canonical_faction_id": 101},
        ]
    )

    with pytest.raises(IdentityConfigError, match="duplicate source ID 1"):
        parse_identity_config(identity_document)


def test_identity_config_rejects_unknown_fields(identity_document: dict) -> None:
    identity_document["mystery"] = True

    with pytest.raises(IdentityConfigError, match="unknown field"):
        parse_identity_config(identity_document)


def test_identity_config_hash_is_independent_of_object_key_order(identity_document: dict) -> None:
    reversed_document = dict(reversed(list(identity_document.items())))

    assert (
        parse_identity_config(identity_document).content_sha256
        == parse_identity_config(reversed_document).content_sha256
    )
