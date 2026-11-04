"""V1S-031 independent whole-term source and publication acceptance.

This deliberately covers exactly five newer Visibility Zone Game terms. It is
not an ARO, target-visibility or MOD evaluator and does not approve other terms.
"""

from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from pathlib import Path
from typing import Any
from wsgiref.util import setup_testing_defaults

import pytest

from infinity_db.curated import load_curated_document
from infinity_db.rules_database import RulesDatabase
from infinity_db.web import create_app

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "config/validation/visibility-zone-whole-record-v1.json"
CORE = ROOT / "data/curated/rules/n5-core-v5.3.json"
RULES = ROOT / "data/generated/rules.db"
ARMY = ROOT / "data/generated/infinity.db"
EN = ROOT / "data/pdf/rules/n5-rules-v5-3-en.pdf"
ES = ROOT / "data/pdf/rules/esp-n5-update-5-3.pdf"
PINS = {
    "english": "53921e91c2d3d62ad5f7125abcd4174b2cf937d45320233eed5b6d301b66af3f",
    "spanish": "7f564c864c6f26d6b218a0477c8afeba99da5c56e1a5369bb259f423689bb28f",
}
# The complete operative Visibility Condition paragraphs on N5.3 EN p.144 and
# ES p.148, distinct from the adjacent Difficult Terrain/Saturation provisions.
# Each reviewed source condition is paired with its current authored wording.
CASES: dict[str, dict[str, Any]] = {
    "term:visibility-zone": {
        "name": "Visibility Zone",
        "clauses": (
            (
                "Any Skill, Special Skill or piece of Equipment that requires LoF, except Dodge",
                "Cualquier Habilidad, Habilidad Especial o Equipo que requiera LDT, "
                "excepto Esquivar",
            ),
            (
                "from, into, or through a Visibility Zone",
                "desde, hacia o a través una Zona de Visibilidad",
            ),
            (
                "This MOD for Visibility stacks with other MODs for Special Skills",
                "El MOD por Zona de Visibilidad es acumulativo con otros MOD dados "
                "por Habilidades Especiales",
            ),
            (
                "Partial Cover, Range... but never with other Zone of Visibility MODs",
                "Cobertura Parcial, Distancia... pero no con otros MOD de Zona de Visibilidad",
            ),
            (
                "Visibility Zone MODs never stack with other Visibility Zone MODs",
                "Los MOD de Zona de Visibilidad no son acumulables entre sí",
            ),
            (
                "always the most restrictive one",
                "será siempre el más restrictivo de todos",
            ),
        ),
        "summary": (
            "from, into, or through the area",
            "[[skill:dodge|Dodge]] is excluded",
            "Range, Partial Cover, Special Skills, and Equipment",
            "**never stack with other [[term:visibility-zone|Visibility Zone]] MODs**",
            "most restrictive [[term:visibility-zone|Visibility Zone]] MOD",
        ),
    },
    "term:low-visibility-zone": {
        "name": "Low Visibility Zone",
        "clauses": (
            ("Low Visibility Zones apply a MOD of -3",
             "Zona de Baja Visibilidad aplicará un MOD de -3"),
        ),
        "summary": (
            "imposes a -3 MOD", "from, into, or through it",
            "except [[skill:dodge]]", "MODs do not stack",
        ),
    },
    "term:poor-visibility-zone": {
        "name": "Poor Visibility Zone",
        "clauses": (
            ("Poor Visibility Zones apply a MOD of -6",
             "Zona de Mala Visibilidad aplicará un MOD de -6"),
        ),
        "summary": (
            "imposes a -6 MOD", "from, into, or through it",
            "except [[skill:dodge]]", "MODs do not stack",
        ),
    },
    "term:zero-visibility-zone": {
        "name": "Zero Visibility Zone",
        "clauses": (
            (
                "LoF cannot be drawn into, through, or out of a Zero Visibility Zone",
                "No se puede trazar LDT hacia el interior, a través o desde una "
                "Zona de Visibilidad Nula",
            ),
            (
                "Any Trooper who is the target of a BS Attack into, through, or out "
                "of a Zero Visibility Zone treats the Zero Visibility Zone as a Poor "
                "Visibility Zone when drawing LoF to the attacker",
                "Cualquier Tropa que sea objetivo de un Ataque CD en el interior, "
                "a través o desde una Zona de Visibilidad Nula, tratará esta zona "
                "como una Zona de Mala Visibilidad cuando trace LDT hacia el atacante",
            ),
        ),
        "summary": (
            "normally blocks Line of Fire from, into, or through it",
            "target of a [[skill:bs-attack]] crossing the Zone",
            "treats it as a [[term:poor-visibility-zone|Poor Visibility Zone]]",
            "when drawing Line of Fire to the attacker",
        ),
    },
    "term:white-noise-zone": {
        "name": "White Noise Zone",
        "clauses": (
            (
                "A White Noise Zone acts as a Zero Visibility Zone, but only for "
                "Troopers with the Marksmanship Special Skill or equipped with "
                "a Multispectral Visor of any Level",
                "La Zona de Ruido Blanco funciona como una Zona de Visibilidad Nula "
                "sólo para Tropas con Puntería o equipadas con Visor Multiespectral, "
                "de cualquier Nivel",
            ),
            (
                "their Multispectral Visor cannot reduce the MODs of the resulting "
                "Poor Visibility Zone",
                "no reducirá los MOD de la Zona de Mala Visibilidad resultante",
            ),
        ),
        "summary": (
            "acts like a [[term:zero-visibility-zone|Zero Visibility Zone]] only for Troopers",
            "[[skill:marksmanship]]", "[[equipment:multispectral-visor]]",
            "or another specified piece of Equipment",
            "Visor cannot reduce the resulting "
            "[[term:poor-visibility-zone|Poor Visibility Zone]] MOD",
        ),
    },
}


def _review() -> dict[str, Any]:
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def _check_review(review: dict[str, Any]) -> None:
    if (
        review.get("format") != "InfinityDB V1S-031 five Visibility Zone term acceptance"
        or review.get("formatVersion") != 1
        or review.get("reviewedOn") != "2026-11-04"
        or review.get("scope") != "five-current-n5.3-visibility-zone-terms-only"
        or review.get("historicalFrozenDenominator") != 367
        or review.get("currentCoreHackingDenominator") != 450
        or review.get("otherSourceSectionsApproved") != 0
        or review.get("sourcePages") != {"english": 144, "spanish": 148}
        or review.get("sourcePins") != PINS
        or review.get("browserWidths") != [1440, 390, 320]
        or review.get("browserTest") != (
            "tests/test_verify_scenario_faq_browser.py"
            "::test_visibility_zone_terms_normal_browser"
        )
    ):
        raise ValueError("V1S-031 source, scope, history or browser evidence drift")
    entries = review.get("entries")
    if not isinstance(entries, list) or len(entries) != len(CASES):
        raise ValueError("V1S-031 term coverage changed")
    ids = [row.get("id") for row in entries if isinstance(row, dict)]
    if len(ids) != len(CASES) or len(set(ids)) != len(ids) or set(ids) != set(CASES):
        raise ValueError("V1S-031 term identities changed")
    for row in entries:
        identity = row["id"]
        if row != {
            "id": identity,
            "name": CASES[identity]["name"],
            "href": f"/glossary#{identity.replace(':', '-')}",
            "sourceDisposition": "all-n5.3-p144-p148-visibility-condition-clauses-reviewed",
            "browserDisposition": "normal-glossary-and-search-three-widths-verified",
            "fullRecordAcceptance": "accepted-for-this-term-only",
        }:
            raise ValueError(f"V1S-031 term acceptance drift: {identity}")


def _get(app: Any, path: str) -> tuple[str, bytes]:
    environ: dict[str, Any] = {}
    setup_testing_defaults(environ)
    environ.update(PATH_INFO=path, REQUEST_METHOD="GET")
    status: list[str] = []
    response = app(environ, lambda s, _h, _i=None: status.append(s))
    try:
        body = b"".join(response)
    finally:
        close = getattr(response, "close", None)
        if close:
            close()
    return status[0], body


def test_five_visibility_zone_full_term_accepted_facts_and_source_identity() -> None:
    _check_review(_review())
    original = {
        item["id"]: item for item in load_curated_document(CORE)["records"]
        if item["id"] in CASES
    }
    assert len(original) == 5
    published = RulesDatabase(RULES)
    app = create_app(ARMY, rules_database_path=RULES)
    code, body = _get(app, "/api/glossary")
    assert code == "200 OK"
    items = {item["id"]: item for item in json.loads(body)["items"]}
    code, body = _get(app, "/glossary")
    assert code == "200 OK" and b"<html" in body.lower()

    for identity, spec in CASES.items():
        curated = original[identity]
        stored = published.composed_record(identity)
        assert stored is not None, identity
        assert curated["kind"] == stored["kind"] == "term"
        assert curated["name"] == stored["name"] == spec["name"]
        assert curated["composition"]["role"] == "definition"
        assert curated["scope"] == {"game": "N5", "seasons": ["current"]}
        assert curated["facts"]["scope"] == stored["facts"]["scope"] == (
            "visibility-condition"
        )
        assert curated["review"]["status"] == "reviewed"
        assert curated["citations"] == [{
            "sourceId": "n5-core-v5.3-pdf",
            "page": 144,
            "section": "Visibility Condition",
        }]
        assert any(
            citation["source_id"] == "n5-core-v5.3-pdf"
            and citation["page"] == 144
            for citation in stored["citations"]
        )
        assert curated["summary"] == stored["summary"]
        for fragment in spec["summary"]:
            assert fragment in curated["summary"], (identity, fragment)
        entry = items[identity]
        assert entry["domain"] == "Game term"
        assert entry["name"] == spec["name"]
        assert entry["href"] == f"/glossary#{identity.replace(':', '-')}"
        assert entry["description"]
        # Additional route and responsive browser checks are covered by the
        # exact Chromium test named in the acceptance manifest.


def test_five_visibility_zone_every_operative_source_clause_is_pinned_bilingually() -> None:
    _check_review(_review())
    if not EN.is_file() or not ES.is_file():
        pytest.skip("Pinned English and Spanish N5.3 sources unavailable")
    pymupdf = pytest.importorskip("pymupdf")
    texts = []
    for language, path, page in (("english", EN, 144), ("spanish", ES, 148)):
        assert hashlib.sha256(path.read_bytes()).hexdigest() == PINS[language]
        with pymupdf.open(path) as pdf:
            texts.append(" ".join(pdf[page - 1].get_text().split()).casefold())
    for identity, spec in CASES.items():
        for en_clause, es_clause in spec["clauses"]:
            for excerpt, source_text in zip((en_clause, es_clause), texts, strict=True):
                assert " ".join(excerpt.split()).casefold() in source_text, (
                    identity, excerpt,
                )
    # The adjacent Difficult Terrain and Saturation sections concern separate
    # gameplay properties, not extra Visibility Zone term conditions.


def test_five_visibility_zone_acceptance_fails_closed_on_scope_and_identity() -> None:
    original = _review()
    changes = (
        lambda x: x["entries"].pop(),
        lambda x: x["entries"][0].update(id="term:poor-visibility-zone"),
        lambda x: x["entries"][0].update(href="/rules/visibility-zone"),
        lambda x: x["entries"][0].update(fullRecordAcceptance="all-rules-complete"),
        lambda x: x["sourcePins"].update(english="0" * 64),
        lambda x: x.update(historicalFrozenDenominator=372),
        lambda x: x.update(otherSourceSectionsApproved=743),
        lambda x: x.update(browserWidths=[1440]),
    )
    for mutate in changes:
        changed = deepcopy(original)
        mutate(changed)
        with pytest.raises(ValueError):
            _check_review(changed)
