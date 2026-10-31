"""Source-scoped disclosure of Silent's unresolved Attribute-Immunity timing.

Selected English/Spanish clauses and FAQ bytes are evidence, not a ruling
or an assertion that no later official clarification can exist.
"""
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
CURATED = ROOT / "data/curated/rules/n5-core-v5.3.json"
ARMY = ROOT / "data/generated/infinity.db"
RULES = ROOT / "data/generated/rules.db"
PINS = {
    "data/pdf/rules/n5-rules-v5-3-en.pdf":
        "53921e91c2d3d62ad5f7125abcd4174b2cf937d45320233eed5b6d301b66af3f",
    "data/pdf/rules/esp-n5-update-5-3.pdf":
        "7f564c864c6f26d6b218a0477c8afeba99da5c56e1a5369bb259f423689bb28f",
}


def test_pinned_clauses_separate_timings_and_preserve_bilingual_wording() -> None:
    texts: list[dict[int, str]] = []
    for (relative, pin), pages in zip(PINS.items(), ((14, 95, 175), (14, 99, 182)), strict=True):
        path = ROOT / relative
        assert hashlib.sha256(path.read_bytes()).hexdigest() == pin
        with pymupdf.open(path) as pdf:
            texts.append({n: " ".join(str(pdf[n - 1].get_text("text")).casefold().split())
                          for n in pages})
    en, es = texts
    assert en[14].index("determine which mods apply") < en[14].index("5.1 effects")
    assert "including saving rolls and dodge movement" in en[14]
    assert "the trooper must make a saving roll" in en[95]
    assert "reduce the attributes of the target" in en[95]
    silent = en[175].split("silent (x).", 1)[1].split("speculative attack", 1)[0]
    assert "inside the target’s zoc and outside their lof" in silent
    assert "face to face dodge roll" in silent
    assert "silent" not in en[95]
    assert "5. resolución" in es[14] and "5.1. efectos" in es[14]
    assert "incluyendo las tiradas de salvación" in es[14]
    assert "la tropa debe realizar una tirada de salvación" in es[99]
    spanish = es[182].split("silenciosa.", 1)[1].split("sin objetivo", 1)[0]
    assert "en zc pero fuera de ldt" in spanish
    assert "tirada de esquivar" in spanish
    assert "enfrentada" not in spanish


@pytest.mark.parametrize("name,pin", [
    ("n5-faqs-v0-0-en.pdf",
     "a04c5eb43e7acd7272c794a3e7d4bb5fe2595ec04463778eb73c741feef5d043"),
    ("n5-faqs-v0-1-en.pdf",
     "7bf26b7d039db7826ef5500b1a2159fe54855b4e632133cab416becee65b85aa"),
    ("esp-faqs-n5-v0-1.pdf",
     "7c40a9ba25b8f61c4e3f40e43b4b15884dfcf27b623baebfc14b003bbeafbf8a"),
])
def test_supplied_faq_identity_and_selected_term_inventory(name: str, pin: str) -> None:
    path = ROOT / "data/pdf/faq" / name
    assert hashlib.sha256(path.read_bytes()).hexdigest() == pin
    with pymupdf.open(path) as pdf:
        text = " ".join(str(page.get_text("text")) for page in pdf).casefold()
    assert all(word not in text for word in ("silent", "silenciosa", "immunity", "inmunidad"))


@pytest.fixture(scope="module")
def app() -> Any:
    return create_app(ARMY, rules_database_path=RULES)


@pytest.mark.parametrize("record_id,path", [
    ("trait:silent-x", "/api/traits/silent-x"),
    ("skill:immunity", "/api/skills/immunity"),
    ("weapon:silenced-pistol", "/api/weapons/silenced-pistol"),
])
def test_source_scope_is_visible_in_authored_stored_and_api_clarifications(
    app: Any, record_id: str, path: str,
) -> None:
    authored = next(r for r in load_curated_document(CURATED)["records"] if r["id"] == record_id)
    notes = [s for s in authored["facts"]["clarifications"] if "Unresolved timing question" in s]
    assert len(notes) == 1
    assert "[[trait:silent-x|" in notes[0]
    assert "[[skill:immunity|" in notes[0] or record_id == "skill:immunity"
    stored = RulesDatabase(RULES).composed_record(record_id)
    assert stored is not None
    assert stored["facts"]["clarifications"] == authored["facts"]["clarifications"]
    environ: dict[str, Any] = {}
    setup_testing_defaults(environ)
    environ.update(PATH_INFO=path, REQUEST_METHOD="GET")
    statuses: list[str] = []

    def respond(status: str, _headers: list, _exc: object = None) -> None:
        statuses.append(status)

    payload = json.loads(b"".join(app(environ, respond)))
    assert statuses == ["200 OK"]
    rule = next(r for r in payload["rules"] if r["id"] == record_id)
    assert rule["facts"]["clarifications"] == authored["facts"]["clarifications"]
    tokens = [t for clause in rule["fact_tokens"]["clarifications"] for t in clause]
    assert any(t.get("target") == "trait:silent-x" for t in tokens)
    if record_id == "trait:silent-x":
        assert any(t["type"] == "review-needed" and t["reason"] == "scope-unclear" for t in tokens)
        assert {c["page"] for c in rule["citations"]
                if c["source_id"] == "n5-core-v5.3-pdf"} >= {14, 95, 175}
        assert {c["page"] for c in rule["citations"]
                if c["source_id"] == "n5-core-v5.3-es-pdf"} >= {14, 99, 182}
        assert "Spanish N5.3 p. 182" in authored["facts"]["sourceNotes"][0]
    elif record_id == "skill:immunity":
        cases = rule["facts"]["immunityInteraction"]
        assert len(cases["reviewedCombinedCases"]) == 9
        assert len(cases["reviewedCriticalCases"]) == 5
        assert len(cases["reviewedWeaponCases"]) == 5
        assert len(cases["reviewedSavingRollCases"]) == 2
        assert sum(len(group) for key, group in cases.items() if key.startswith("reviewed")) == 23
