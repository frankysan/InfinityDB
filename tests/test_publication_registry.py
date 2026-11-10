"""P3.4 domain-aware registry and cross-publication fail-closed boundaries."""

from __future__ import annotations

from pathlib import Path

import pytest

from infinity_db.its_season_database import build_its_database
from infinity_db.publication_registry import PublicationReference, PublicationRegistry
from infinity_db.rules_database import RulesDatabase

ROOT = Path(__file__).resolve().parents[1]
RULES_PATH = ROOT / "data/generated/rules_n5.db"
ITS_SOURCE = ROOT / "data/curated/rules/n5-its-season-18-2026.09.01.json"
REVISION = "2026.09.01"


@pytest.fixture
def registry(tmp_path: Path) -> PublicationRegistry:
    path = tmp_path / "its_18.db"
    build_its_database(ITS_SOURCE, path)
    return PublicationRegistry(RulesDatabase(RULES_PATH), {"its-18": path})


def test_registry_resolves_same_scenario_id_by_owner_and_revision(
    registry: PublicationRegistry,
) -> None:
    assert registry.core_revision == "5.3"
    core = registry.resolve(PublicationReference("rules-n5", "scenario:battleground"))
    season = registry.resolve(PublicationReference(
        "its-18", "scenario:battleground", REVISION,
    ))
    assert core is not None and season is not None
    assert core["id"] == season["record"]["id"]
    assert season["publication"]["collectionId"] == "its-18"
    assert season["publication"]["sourceCollectionId"] == "its-season-18-2026.09.01"
    manifest = registry.season_manifest()["its-18"]
    assert manifest["revision"] == REVISION
    assert manifest["requiredCoreRulesRevision"] == "5.3"
    assert len(manifest["sha256"]) == 64


def test_explicit_owner_revision_and_context_fail_closed(
    registry: PublicationRegistry,
) -> None:
    assert registry.resolve(PublicationReference(
        "its-18", "scenario:battleground", "2025.09.01",
    )) is None
    assert registry.resolve(PublicationReference(
        "its-17", "scenario:battleground", REVISION,
    )) is None
    assert registry.resolve(PublicationReference(
        "its-18", "scenario:missing", REVISION,
    )) is None
    assert registry.resolve(PublicationReference("rules-n5", "scenario:missing")) is None
    assert registry.season_policies(
        season_id="its-18", revision=REVISION, context="free-play",
    ) == []
    assert registry.season_policies(
        season_id="its-17", revision=REVISION, context="official-tournament",
    ) == []
    assert registry.season_policies(
        season_id="its-18", revision="2025.09.01", context="official-tournament",
    ) == []


def test_policy_targets_resolve_from_core_only_in_explicit_context(
    registry: PublicationRegistry,
) -> None:
    specs = registry.season_policies(
        season_id="its-18", revision=REVISION, context="official-tournament",
    )
    assert len(specs) == 1
    assert specs[0]["policy"]["id"] == "its18-spec-ops-tournament"
    assert specs[0]["policy"]["target"] == {
        "domain": "rules-n5", "recordId": "skill:infinity-spec-ops",
    }
    assert specs[0]["target"]["id"] == "skill:infinity-spec-ops"
    extra = registry.season_policies(
        season_id="its-18", revision=REVISION, context="reinforcements-extra",
    )
    assert len(extra) == 1
    assert extra[0]["target"]["id"] == "rule:reinforcements-extra"
    assert registry.season_policies(
        season_id="its-18", revision=REVISION, context="official-tournament",
        target_id="rule:reinforcements-extra",
    ) == []


def test_registry_rejects_wrong_season_registration_and_core_revision(tmp_path: Path) -> None:
    its = tmp_path / "its_18.db"
    build_its_database(ITS_SOURCE, its)
    rules = RulesDatabase(RULES_PATH)
    with pytest.raises(ValueError, match="registration does not match"):
        PublicationRegistry(rules, {"its-17": its})

    class WrongCoreRevision(RulesDatabase):
        def current_core_scenario_revision(self) -> str:
            return "5.4"

    with pytest.raises(ValueError, match="different N5 core revision"):
        PublicationRegistry(WrongCoreRevision(RULES_PATH), {"its-18": its})


def test_registry_rejects_unknown_cross_domain_policy_target(tmp_path: Path) -> None:
    its = tmp_path / "its_18.db"
    build_its_database(ITS_SOURCE, its)

    class MissingReference(RulesDatabase):
        def composed_record(self, record_id: str, **kwargs):
            if record_id == "skill:infinity-spec-ops":
                return None
            return super().composed_record(record_id, **kwargs)

    with pytest.raises(ValueError, match="unknown N5 target"):
        PublicationRegistry(MissingReference(RULES_PATH), {"its-18": its})


@pytest.mark.parametrize(
    ("reference", "message"),
    [
        (("rules-n5", "scenario:battleground", REVISION), "do not take season"),
        (("its-18", "scenario:battleground", None), "require an exact season"),
        (("its-18", "skill:infinity-spec-ops", REVISION), "must identify a Scenario"),
        (("unknown", "scenario:battleground", None), "Unregistered publication"),
        (("rules-n5", "untyped", None), "typed record"),
    ],
)
def test_publication_reference_requires_explicit_typed_ownership(
    reference: tuple[str, str, str | None], message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        PublicationReference(*reference)
