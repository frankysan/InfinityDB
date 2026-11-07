"""Pinned basic BS/CC conditions and ordinary Skill-page acceptance (VD-0020)."""
from __future__ import annotations

import hashlib
import re
from typing import Any
from zipfile import ZipFile

import pytest
from reference_acceptance_support import (
    PDF,
    WIKI,
    WIKI_PIN,
    api,
    browse,
    pdf_pages,
    published,
    records,
)
from test_verify_ammunition_publication_browser import browser as browser


def test_basic_attacks_match_pinned_pdf_and_archived_wiki(require_source_files) -> None:
    require_source_files(PDF, WIKI)
    pages = pdf_pages((36, 39, 40, 42, 51, 52))
    for page, phrases in {
        36: ("those dice will be lost", "same point"),
        39: ("one for the entire burst", "all shots"),
        40: ("-6 mod", "every failed bs attack roll", "chooses"),
        42: ("maximum range", "automatically fails", "disposable"),
        51: ("coup de grâce", "without the possibility", "dogged", "no wound incapacitation"),
        52: ("2 or more", "only one", "dodge, idle or reset", "25 mm", "40 mm"),
    }.items():
        for phrase in phrases:
            assert phrase in pages[page], (page, phrase)
    assert hashlib.sha256(WIKI.read_bytes()).hexdigest() == WIKI_PIN
    with ZipFile(WIKI) as archive:
        for member, revision in {"Combat_Module": 4030, "BS_Attack": 4004,
                                 "Ballistic_Skills": 4094, "CC_Attack": 3953,
                                 "Close_Combat": 4023}.items():
            html = archive.read(member).decode("utf-8")
            assert re.search(r'"wgRevisionId"\s*:\s*' + str(revision), html)


def test_attack_conditions_and_citations_reach_runtime_and_api() -> None:
    current = records()
    for slug in ("bs-attack", "cc-attack"):
        published(f"skill:{slug}", f"/api/skills/{slug}", current[f"skill:{slug}"])
    bs = current["skill:bs-attack"]["facts"]
    assert any("one Ammunition type for the entire Burst" in s and "dice" in s
               for s in bs["effects"])
    text = " ".join(bs["clarifications"])
    for phrase in ("-6 MOD for each allied", "Every failed", "chooses which ally", "expends a use"):
        assert phrase in text
    cc = " ".join(current["skill:cc-attack"]["facts"]["clarifications"])
    for phrase in ("state:unconscious", "state:dead", "skill:dogged",
                   "skill:no-wound-incapacitation", "at least two", "activated by the Order",
                   "neither", "not declared", "skill:dodge", "skill:idle", "skill:reset",
                   "skill:doctor", "skill:engineer"):
        assert phrase in cc
    # The conditional explanation does not become a permanent weapon bonus.
    weapon = api("/api/weapons/cc-weapon")
    profiles = weapon.get("profiles", []) + [
        p for v in weapon.get("weapon_variants", []) for p in v.get("profiles", [])
    ]
    assert profiles
    assert all("immunity_result" not in p and "immunityInteraction" not in p for p in profiles)


@pytest.mark.parametrize("width", (1440, 390, 320))
def test_attack_skill_catalog_conditions_and_keyboard_links(browser: Any, width: int) -> None:
    browse(browser, width, "skills", "bs-attack", "skill:bs-attack",
           ("Shooting into close combat", "Every failed", "one firing position", "Disposable"),
           ("/rules/face-to-face-rolls", "/states/engaged"))
    browse(browser, width, "skills", "cc-attack", "skill:cc-attack",
           ("Coup de Grâce", "Active Turn", "Reactive Turn", "25 mm", "not declared"),
           ("/states/dead", "/skills/doctor", "/skills/engineer"))
