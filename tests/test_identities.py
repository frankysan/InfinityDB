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
    normalized_unit_identity,
    parse_identity_config,
    parse_identity_metadata,
)


@pytest.fixture
def identity_document() -> dict:
    return load_identity_config(Path("config/identity/source-identities.json")).document


def test_source_identity_manifest_contains_current_explicit_aliases() -> None:
    config = load_identity_config()

    assert config.document["schema_version"] == 2
    assert config.canonical_unit_id(1690) == 300
    assert config.canonical_unit_id(11345) == 1345
    assert config.canonical_army_id(998) == 999
    assert config.resolve_canonical_faction_id(1) == 1

    for catalog in ("skills", "equipment", "weapons"):
        for group in config.document["catalogs"][catalog]["groups"]:
            assert isinstance(group["canonical_id"], str)
            assert all(isinstance(ref, str) for ref in group["source_ids"])

    assert dict(
        config.resolve_catalog_aliases(
            "skills",
            {
                19: "Martial Arts L1",
                20: "Martial Arts L2",
                21: "Martial Arts L3",
                22: "Martial Arts L4",
                23: "Martial Arts L5",
                69: "Strategos L1",
                70: "Strategos L2",
                201: "BS Attack",
                278: "BS=12",
                279: "BS=11",
                240: "CC Attack",
                274: "CC=21",
            },
        )
    ) == {
        19: 19,
        20: 19,
        21: 19,
        22: 19,
        23: 19,
        69: 69,
        70: 69,
        201: 201,
        278: 201,
        279: 201,
        240: 240,
        274: 240,
    }
    assert dict(
        config.resolve_catalog_aliases(
            "equipment",
            {
                169: "TinBot: Firewall",
                188: "TinBot: Neourocinetics",
                193: "TinBot (Albedo)",
                235: "TinBot",
                244: "TinBot: Discover",
                247: "TinBot: ECM Guided",
                248: "Tinbot (Repeater)",
            },
        )
    ) == {169: 235, 188: 235, 193: 235, 235: 235, 244: 235, 247: 235, 248: 235}
    assert dict(
        config.resolve_catalog_aliases(
            "weapons",
            {
                209: "Armed Turret (Combi R.)",
                215: "Armed Turret (Marksman R.)",
                219: "Armed Turret (AP Rifle)",
                222: "Armed Turret (Rifle)",
                226: "Armed Turret",
                228: "Armed Turret (E/Mitter)",
            },
        )
    ) == {209: 226, 215: 226, 219: 226, 222: 226, 226: 226, 228: 226}

    assert config.word_aliases["reconaissance"] == "recon"
    assert config.reinforcement_prefixes == ("reinf", "refuerzos")
    assert "intervention" in config.profile_identity_ignored_words


def test_catalog_identity_groups_accept_numeric_or_slug_references(
    identity_document: dict,
) -> None:
    identity_document["catalogs"]["skills"]["groups"] = [
        {
            "canonical_id": "camouflage-l1",
            "source_ids": [19, "camouflage-l2"],
            "reason": "Readable mixed-reference test",
        }
    ]

    config = parse_identity_config(identity_document)

    assert dict(
        config.resolve_catalog_aliases(
            "skills",
            {19: "Camouflage L1", 20: "Camouflage L2"},
        )
    ) == {19: 19, 20: 19}


def test_catalog_identity_group_can_be_absent_from_source_snapshot(
    identity_document: dict,
) -> None:
    config = parse_identity_config(identity_document)

    assert dict(config.resolve_catalog_aliases("skills", {42: "Stealth"})) == {}


def test_catalog_identity_slug_references_fail_closed_when_unknown_or_ambiguous(
    identity_document: dict,
) -> None:
    identity_document["catalogs"]["skills"]["groups"] = [
        {
            "canonical_id": 19,
            "source_ids": [19, "camouflage-l2"],
        }
    ]
    config = parse_identity_config(identity_document)

    with pytest.raises(IdentityConfigError, match="unknown skills slug"):
        config.resolve_catalog_aliases("skills", {19: "Camouflage L1"})

    with pytest.raises(IdentityConfigError, match="ambiguous skills slug"):
        config.resolve_catalog_aliases(
            "skills",
            {19: "Camouflage L1", 20: "Camouflage L2", 21: "Camouflage-L2"},
        )


def test_reinforcement_prefixes_are_manifest_backed_identity_policy() -> None:
    config = load_identity_config()

    assert normalized_unit_identity("REINF: ARMBOTS BULLETEERS", config) == "armbot bulleteer"
    assert (
        normalized_unit_identity("REFUERZOS: ARMBOTS BULLETEERS", config)
        == "armbot bulleteer"
    )
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
    assert dict(config.resolve_catalog_aliases("skills", {42: "Stealth"})) == {}


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


def test_identity_config_rejects_invalid_reinforcement_prefixes(identity_document: dict) -> None:
    identity_document["name_normalization"]["reinforcement_prefixes"] = ["REINF"]

    with pytest.raises(IdentityConfigError, match="trimmed and case-folded"):
        parse_identity_config(identity_document)

    identity_document["name_normalization"]["reinforcement_prefixes"] = ["reinf", "reinf"]
    with pytest.raises(IdentityConfigError, match="contains duplicates"):
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
