"""Pinned basic BS/CC conditions and ordinary Skill-page acceptance (VD-0020)."""
from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any
from zipfile import ZipFile

import pytest
from reference_acceptance_support import (
    PDF_LABEL,
    PIN,
    WIKI,
    WIKI_PIN,
    api,
    browse,
    pdf_pages,
    published,
    records,
    selected_pdf,
)
from test_verify_ammunition_publication_browser import browser as browser

from tools.research.source_paths import SourcePathError


def test_reference_source_prerequisite_requires_selected_layout_and_pin(
    tmp_path: Path,
) -> None:
    payload = b"%PDF hermetic source label, not a parsed official publication"
    pin = hashlib.sha256(payload).hexdigest()
    legacy = tmp_path / PDF_LABEL
    local = tmp_path / "local/data/pdf" / Path(PDF_LABEL).relative_to("data/pdf")
    for path in (legacy, local):
        path.parent.mkdir(parents=True)
        path.write_bytes(payload)
    assert selected_pdf(PDF_LABEL, pin, root=tmp_path) == local
    assert selected_pdf(PDF_LABEL, pin, layout="legacy", root=tmp_path) == legacy
    local.write_bytes(b"unreviewed revision")
    with pytest.raises(SourcePathError, match="hash mismatch"):
        selected_pdf(PDF_LABEL, pin, layout="local", root=tmp_path)
    local.unlink()
    assert selected_pdf(PDF_LABEL, pin, root=tmp_path) is None
    assert selected_pdf(PDF_LABEL, pin, layout="legacy", root=tmp_path) == legacy
    with pytest.raises(SourcePathError, match="Unknown research source layout"):
        selected_pdf(PDF_LABEL, pin, layout="automatic", root=tmp_path)


def test_reference_pdf_page_reader_uses_explicit_verified_path(tmp_path: Path) -> None:
    import pymupdf

    with pymupdf.open() as document:
        page = document.new_page()
        page.insert_text((72, 72), "Explicit Source Layout Proof")
        payload = document.tobytes()
    path = tmp_path / "local/data/pdf/rules/n5-rules-v5.3-en.pdf"
    path.parent.mkdir(parents=True)
    path.write_bytes(payload)
    pin = hashlib.sha256(payload).hexdigest()
    selected = selected_pdf(PDF_LABEL, pin, layout="local", root=tmp_path)
    assert selected is not None and selected == path
    assert "explicit source layout proof" in pdf_pages(
        (1,), pdf_path=selected, pin=pin,
    )[1]
    with pytest.raises(AssertionError):
        pdf_pages((1,), pdf_path=selected, pin="0" * 64)


def test_basic_attacks_match_pinned_pdf_and_archived_wiki(
    require_source_files, reference_pdf_layout: str,
) -> None:
    pdf = selected_pdf(PDF_LABEL, PIN, layout=reference_pdf_layout)
    if pdf is None:
        pytest.skip(f"Pinned PDF unavailable in {reference_pdf_layout} layout: {PDF_LABEL}")
    require_source_files(WIKI)
    pages = pdf_pages((36, 39, 40, 42, 51, 52), pdf_path=pdf)
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
