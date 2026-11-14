"""V1S-035 primary source citations and scoped timing/defense (VD-0023)."""
from __future__ import annotations

from typing import Any

import pytest
from reference_acceptance_support import (
    PDF_LABEL,
    PIN,
    browse,
    pdf_pages,
    published,
    records,
    selected_pdf,
)
from test_verify_ammunition_publication_browser import browser as browser

PROGRAM_PAGES = {
    "assisted-fire": 59, "carbonite": 59, "controlled-jump": 59, "cybermask": 59,
    "enhanced-reaction": 60, "fairy-dust": 60, "oblivion": 60, "spotlight": 60,
    "total-control": 61, "trinity": 61, "white-noise": 61, "zero-pain": 61,
}


def test_hacking_sources_pin_citation_pages_and_distinct_procedures(
    reference_pdf_layout: str,
) -> None:
    pdf = selected_pdf(PDF_LABEL, PIN, layout=reference_pdf_layout)
    if pdf is None:
        pytest.skip(f"Pinned PDF unavailable in {reference_pdf_layout} layout: {PDF_LABEL}")
    pages = pdf_pages((55, 56, 59, 60, 61), pdf_path=pdf)
    assert "supportware programs" in pages[55]
    assert "only sustain one active supportware" in pages[55]
    assert "this is a range amplifier" in pages[56]
    assert "instead of in the resolution step" in pages[59]
    for phrase in ("at the end of the order", "totally inside", "infinite height",
                   "active or reactive turn", "two wip rolls", "either roll",
                   "does not have to make any saving rolls"):
        assert phrase in pages[61], phrase
    for slug, page in PROGRAM_PAGES.items():
        assert slug.replace("-", " ") in pages[page]


def test_hacking_primary_citations_and_clarifications_are_published() -> None:
    core, programs = records(), records("n5-hacking-programs-v5.3.json")
    pdf_id = "n5-core-v5.3-pdf"
    for identity, page, section, path in (
        ("equipment:repeater", 56, "Repeater", "/api/equipment/repeater"),
        ("rule:supportware", 55, "Supportware", "/api/rules/supportware"),
    ):
        record = core[identity]
        assert {c["page"] for c in record["citations"]
                if c["sourceId"] == pdf_id and c.get("section") == section} == {page}
        published(identity, path, record)
    for slug, page in PROGRAM_PAGES.items():
        identity = f"hacking-program:{slug}"
        record = programs[identity]
        assert {c["page"] for c in record["citations"]
                if c["sourceId"] == pdf_id and c.get("section") == record["name"]} == {page}
        published(identity, f"/api/hacking-programs/{slug}", record)
        if slug in ("assisted-fire", "controlled-jump", "enhanced-reaction"):
            assert {c["page"] for c in record["citations"]
                    if c["sourceId"] == pdf_id and c.get("section") == "Supportware"} == {55}
    white = " ".join(programs["hacking-program:white-noise"]["facts"]["clarifications"])
    assert "at the end of the Order" in white and "hacking-program:controlled-jump" in white
    zero = " ".join(programs["hacking-program:zero-pain"]["facts"]["clarifications"])
    for phrase in ("either the Active or Reactive", "two [[attribute:wip|WIP]] Rolls",
                   "either die", "no [[rule:saving-rolls|Saving Rolls]]", "special effects",
                   "otherwise ineligible"):
        assert phrase in zero


@pytest.mark.parametrize("width", (1440, 390, 320))
def test_hacking_source_pages_and_timing_are_visible(browser: Any, width: int) -> None:
    browse(browser, width, "hacking-programs", "white-noise", "hacking-program:white-noise",
           ("at the end of the Order", "infinite", "Controlled Jump", "p. 61"),
           ("/rules/hacking-area", "/hacking-programs/controlled-jump"))
    browse(browser, width, "hacking-programs", "zero-pain", "hacking-program:zero-pain",
           ("Active or Reactive Turn", "two WIP Rolls", "no Saving Rolls", "ineligible"),
           ("/rules/saving-rolls", "/rules/face-to-face-rolls"))
    browse(browser, width, "rules", "supportware", "rule:supportware",
           ("only one Supportware Program", "p. 55", "p. 60"),
           ("/hacking-programs/fairy-dust",))
    browse(browser, width, "equipment", "repeater", "equipment:repeater",
           ("same Army List", "p. 56"), ("/rules/hacking-area",))
