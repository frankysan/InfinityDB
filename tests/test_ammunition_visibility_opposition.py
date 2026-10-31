"""Source/API parity and closed validation for Smoke/Eclipse opposition facts."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any
from wsgiref.util import setup_testing_defaults

import pymupdf
import pytest

from infinity_db.curated import load_curated_document
from infinity_db.rules_database import RulesDatabase
from infinity_db.web import create_app

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data/curated/rules/n5-core-v5.3.json"
RULES = ROOT / "data/generated/rules.db"
PDF = ROOT / "data/pdf/rules/n5-rules-v5-3-en.pdf"
PIN = "53921e91c2d3d62ad5f7125abcd4174b2cf937d45320233eed5b6d301b66af3f"


def expected(slug: str) -> dict[str, Any]:
    return {
        "ruleId": "rule:face-to-face-rolls",
        "attackRequirements": ["requires-roll", "requires-lof", "lof-crosses-zone"],
        "visorAttack": "normal-roll" if slug == "smoke" else "face-to-face-if-qualifying",
        "enemyDodge": "normal-roll",
        "templateRetention": "win-every-opposed-or-pass-unopposed",
        "critical": "no-additional-effect",
    }


def test_pinned_rules_require_rolled_crossing_lof_and_separate_visor_scope() -> None:
    assert hashlib.sha256(PDF.read_bytes()).hexdigest() == PIN
    with pymupdf.open(PDF) as pdf:
        smoke = " ".join(str(pdf[65].get_text("text")).casefold().split())
        eclipse = " ".join(str(pdf[63].get_text("text")).casefold().split())
    assert "attacks that require a roll and lof" in smoke
    assert "whose lof passes through the zero visibility zone" in smoke
    assert "win every single face to face roll" in smoke
    assert "fails an unopposed normal roll" in smoke
    assert "dodge aro will make a normal roll" in smoke
    assert "critical hits with smoke ammunition have no additional effect" in smoke
    assert "do not perform face to face rolls against smoke" in smoke
    assert "works in exactly the same way as smoke" in eclipse
    assert "attacks that require a roll and lof" in eclipse
    assert "also perform face to face rolls against weapons with eclipse" in eclipse


@pytest.fixture(scope="module")
def app() -> Any:
    return create_app(ROOT / "data/generated/infinity.db", rules_database_path=RULES)


@pytest.mark.parametrize("slug", ["smoke", "eclipse"])
def test_visibility_opposition_reaches_storage_api_and_owning_rule(app: Any, slug: str) -> None:
    record_id = f"ammunition:{slug}"
    authored = next(r for r in load_curated_document(SOURCE)["records"] if r["id"] == record_id)
    assert authored["facts"]["visibilityZone"]["opposition"] == expected(slug)
    assert "ammunitionResolution" not in authored["facts"]
    stored = RulesDatabase(RULES).composed_record(record_id)
    assert stored is not None
    assert stored["facts"]["visibilityZone"] == authored["facts"]["visibilityZone"]
    env: dict[str, Any] = {}
    setup_testing_defaults(env)
    env.update(PATH_INFO=f"/api/ammunition/{slug}", REQUEST_METHOD="GET")
    statuses: list[str] = []

    def respond(status: str, _headers: list, _exc: object = None) -> None:
        statuses.append(status)

    payload = json.loads(b"".join(app(env, respond)))
    assert statuses == ["200 OK"]
    record = next(r for r in payload["rules"] if r["id"] == record_id)
    assert record["facts"]["visibilityZone"]["opposition"] == expected(slug)
    targets = [r["record"] for r in record["display_relations"]
               if r["record"]["id"] == "rule:face-to-face-rolls"]
    assert targets and targets[0]["public_reference"] == {
        "catalog": "rules", "id": "face-to-face-rolls",
    }
    assert {c["page"] for c in record["citations"]
            if c["source_id"] == "n5-core-v5.3-pdf"} >= ({66} if slug == "smoke" else {64, 66})


@pytest.mark.parametrize("slug", ["smoke", "eclipse"])
@pytest.mark.parametrize("key,value", [
    ("ruleId", "rule:saving-rolls"),
    ("attackRequirements", ["requires-roll", "lof-crosses-zone"]),
    ("attackRequirements", ["requires-lof", "lof-crosses-zone"]),
    ("attackRequirements", ["requires-roll", "requires-lof"]),
    ("visorAttack", "always-face-to-face"),
    ("enemyDodge", "face-to-face"),
    ("templateRetention", "win-any-opposition"),
    ("critical", "additional-saving-roll"),
    ("automaticOutcome", "attack-misses"),
])
def test_visibility_opposition_rejects_unreviewed_semantics(
    tmp_path: Path, slug: str, key: str, value: Any,
) -> None:
    document = json.loads(SOURCE.read_text(encoding="utf-8"))
    record = next(r for r in document["records"] if r["id"] == f"ammunition:{slug}")
    record["facts"]["visibilityZone"]["opposition"][key] = value
    path = tmp_path / "mutated.json"
    path.write_text(json.dumps(document), encoding="utf-8")
    with pytest.raises(ValueError, match="visibility opposition facts"):
        load_curated_document(path)


@pytest.mark.parametrize("slug", ["smoke", "eclipse"])
def test_visibility_opposition_requires_its_rule_relation(tmp_path: Path, slug: str) -> None:
    document = json.loads(SOURCE.read_text(encoding="utf-8"))
    record = next(r for r in document["records"] if r["id"] == f"ammunition:{slug}")
    record["relations"] = [r for r in record["relations"]
                           if r["recordId"] != "rule:face-to-face-rolls"]
    path = tmp_path / "missing-relation.json"
    path.write_text(json.dumps(document), encoding="utf-8")
    with pytest.raises(ValueError, match="missing owning rule relation"):
        load_curated_document(path)


def test_legacy_visibility_zone_without_opposition_remains_readable(tmp_path: Path) -> None:
    document = json.loads(SOURCE.read_text(encoding="utf-8"))
    for record in document["records"]:
        zone = record.get("facts", {}).get("visibilityZone")
        if zone:
            del zone["opposition"]
    path = tmp_path / "legacy.json"
    path.write_text(json.dumps(document), encoding="utf-8")
    assert load_curated_document(path)
