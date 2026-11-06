"""Shared/Direct/Impact Template source and normal-browser parity (VD-0021)."""
from __future__ import annotations

import hashlib
import re
from typing import Any
from zipfile import ZipFile

import pytest
from reference_acceptance_support import (
    PDF,
    ROOT,
    WIKI,
    WIKI_PIN,
    api,
    browse,
    pdf_pages,
    published,
    records,
)
from test_verify_ammunition_publication_browser import browser as browser


def test_template_conditions_match_pinned_pdf_wiki_and_faq(require_source_files) -> None:
    faq = ROOT / "data/pdf/faq/n5-faq-v0.1-en.pdf"
    require_source_files(PDF, WIKI, faq)
    pages = pdf_pages((43, 44, 45, 46, 47, 49))
    for page, phrases in {
        43: ("main target", "automatically considered a failure", "half their width"),
        44: ("that shot is cancelled", "other shots", "can still declare aros",
             "use is still consumed", "only the main", "+3 mod"),
        45: ("every trooper involved", "do not require a bs roll", "only some of them",
             "must be placed", "any active trooper"),
        46: ("a single normal ph", "will not be affected"),
        47: ("independently", "main target", "targetless", "single roll"),
        49: ("blast focus", "total cover", "within the area of effect"),
    }.items():
        for phrase in phrases:
            assert phrase in pages[page], (page, phrase)
    assert hashlib.sha256(WIKI.read_bytes()).hexdigest() == WIKI_PIN
    with ZipFile(WIKI) as archive:
        for member, revision in {"Template_Weapons_and_Equipment": 3880,
                                 "Direct_Template_Weapons": 3881,
                                 "Impact_Template_Weapons": 3782}.items():
            assert re.search(r'"wgRevisionId"\s*:\s*' + str(revision),
                             archive.read(member).decode("utf-8"))
    assert hashlib.sha256(faq.read_bytes()).hexdigest() == (
        "7bf26b7d039db7826ef5500b1a2159fe54855b4e632133cab416becee65b85aa"
    )
    import pymupdf
    with pymupdf.open(faq) as document:
        # File page 1 is the cover; printed FAQ page 1 is file page 2.
        first = " ".join(str(document[1].get_text("text")).casefold().split())
    assert "corners" in first and "secondary targets" in first


def test_template_procedures_and_source_identity_reach_api() -> None:
    current = records()
    for identity, path in {
        "rule:template-weapons-and-equipment": "/api/rules/template-weapons-and-equipment",
        "trait:direct-template": "/api/traits/direct-template",
        "trait:impact-template": "/api/traits/impact-template",
    }.items():
        published(identity, path, current[identity])
    search = api("/api/search?q=Template+Weapons+and+Equipment")
    assert any(item.get("href") == "/rules/template-weapons-and-equipment"
               for item in search["items"])
    for slug in ("direct-template", "impact-template"):
        assert current[f"trait:{slug}"]["facts"]["sourceIdentity"]["prefixes"] == [
            ("Direct" if slug == "direct-template" else "Impact") + " Template (",
        ]
    shared = current["rule:template-weapons-and-equipment"]["facts"]
    text = " ".join(shared["requirements"] + shared["effects"] + shared["restrictions"])
    for phrase in ("affects no game element", "neither a PS value nor an imposed condition",
                   "Other shots", "cancelled shot", "Disposable", "every Trooper",
                   "+3", "Saving Roll"):
        assert phrase in text
    direct = current["trait:direct-template"]["facts"]
    assert any("corners" in s and "firing Trooper" in s for s in direct["restrictions"])
    assert any("skill:intuitive-attack" in s and "attribute:wip" in s
               for s in direct["clarifications"])
    impact = current["trait:impact-template"]["facts"]
    assert any("single" in s and "separately" in s for s in impact["clarifications"])
    assert any("trait:targetless" in s and "skill:speculative-attack" in s
               for s in impact["clarifications"])


@pytest.mark.parametrize("width", (1440, 390, 320))
def test_template_catalogs_links_and_conditional_prose(browser: Any, width: int) -> None:
    browse(browser, width, "rules", "template-weapons-and-equipment",
           "rule:template-weapons-and-equipment",
           ("affects no game element", "neither a PS value nor an imposed condition",
            "Other shots", "every Trooper", "Critical", "Blast Focus"),
           ("/traits/direct-template", "/traits/impact-template"))
    browse(browser, width, "traits", "direct-template", "trait:direct-template",
           ("cannot fire around corners", "normally unopposed", "One unopposed",
            "Intuitive Attack", "Main Target"),
           ("/rules/template-weapons-and-equipment", "/skills/intuitive-attack"))
    browse(browser, width, "traits", "impact-template", "trait:impact-template",
           ("Compare that same Roll separately", "single", "Targetless", "Speculative Attack"),
           ("/rules/template-weapons-and-equipment", "/skills/speculative-attack"))
