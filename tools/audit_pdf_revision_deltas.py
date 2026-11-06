"""Compare pinned PDF revisions without treating text extraction as a ruling.

The output is an audit candidate list, not semantic equivalence, and lives in local/.
Source PDFs are ignored external inputs. No source bytes are modified or published.
"""

from __future__ import annotations

import argparse
import bisect
import difflib
import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import cast

try:
    import pymupdf as fitz
except ImportError as exc:
    raise SystemExit("PyMuPDF is required: install the dev extra") from exc


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data" / "pdf"
PAIRS = {
    "its18-en": ("its/its-18-rules-v2026.09.01-en.pdf", "its/its-18-rules-v2026.09.11-en.pdf", 1),
    "n5-v1-v1.1-en": ("rules/n5-rules-v1-en.pdf", "rules/n5-rules-v1.1-en.pdf", 1),
    "n5-v1.1-v5.1.1-en": ("rules/n5-rules-v1.1-en.pdf", "rules/n5-rules-v5.1.1-en.pdf", 1),
    "n5-v5.1.1-v5.2-en": ("rules/n5-rules-v5.1.1-en.pdf", "rules/n5-rules-v5.2-en.pdf", 1),
    "n5-v5.2-v5.3-en": ("rules/n5-rules-v5.2-en.pdf", "rules/n5-rules-v5.3-en.pdf", 1),
    "n5-v1-v1.1-es": ("rules/n5-rules-v1-es.pdf", "rules/n5-rules-v1.1-es.pdf", 1),
    "n5-v1.1-v5.1.1-es": ("rules/n5-rules-v1.1-es.pdf", "rules/n5-rules-v5.1.1-es.pdf", 1),
    "n5-v5.1.1-v5.2-es": ("rules/n5-rules-v5.1.1-es.pdf", "rules/n5-rules-v5.2-es.pdf", 1),
    "n5-v5.2-v5.3-es": ("rules/n5-rules-v5.2-es.pdf", "rules/n5-rules-v5.3-es.pdf", 1),
    "faq-en": ("faq/n5-faq-v0.0-en.pdf", "faq/n5-faq-v0.1-en.pdf", 1),
    "faq-es": ("faq/n5-faq-v0.0-es.pdf", "faq/n5-faq-v0.1-es.pdf", 1),
}
WORD = re.compile(r"[^\W_]+(?:[.’'/-][^\W_]+)*|[+\-]+|[*]+", re.UNICODE)
FOOTER = re.compile(
    r"(?:Version|Versi[oó]n)\s+\d{4}\.\d{2}\.\d{2}.*?"
    r"(?:Page|P[aá]gina)\s+\d+\s+(?:of|de)\s+\d+",
    re.I,
)
SOURCE_HEADER = re.compile(r"^FAQs?\s+V\d+\.\d+\s+-\s+(?:English|Espa[nñ]ol)", re.I)
PAGE_NUMBER = re.compile(r"^\s*\d{1,3}\s*$")
PUNCTUATION = re.compile(r"[\s\u00a0]+")
PIN_PATH = ROOT / "local" / "pdf-revision-inventory.json"


@dataclass
class Extracted:
    path: str
    sha256: str
    pages: int
    starts: list[int]
    words: list[str]


def extract(relative: str, skip_pages: int) -> Extracted:
    path = SOURCE / relative
    payload = path.read_bytes()
    sha256 = hashlib.sha256(payload).hexdigest()
    starts: list[int] = []
    words: list[str] = []
    with fitz.open(stream=payload, filetype="pdf") as document:
        pages = len(document)
        for index in range(skip_pages, pages):
            page = document.load_page(index)
            starts.append(len(words))
            text = cast(str, page.get_text("text", sort=False))
            cleaned = []
            for line in text.splitlines():
                line = FOOTER.sub("", line)
                if PAGE_NUMBER.fullmatch(line) or SOURCE_HEADER.match(line.strip()):
                    continue
                if line.strip().startswith("https://infinityuniverse.com/"):
                    continue
                cleaned.append(line)
            normalized = PUNCTUATION.sub(" ", " ".join(cleaned))
            words.extend(m.group(0).casefold() for m in WORD.finditer(normalized))
    return Extracted(path=relative, sha256=sha256, pages=pages, starts=starts, words=words)


def page_for(extracted: Extracted, word_offset: int, skip_pages: int) -> int:
    if not extracted.starts:
        return 0
    return max(1, skip_pages + bisect.bisect_right(extracted.starts, word_offset))


def phrase(words: list[str], start: int, end: int, limit: int = 18) -> str:
    if start >= end:
        return ""
    return " ".join(words[start:min(end, start + limit)])


def changes(before: Extracted, after: Extracted, skip: int) -> list[dict]:
    # Nine-word shingles are anchors stable across page breaks and line wrapping.
    # Unlike a per-page diff, this keeps valid matches after a section shifts pages.
    def shingle_hashes(words: list[str]) -> list[int]:
        return [hash(tuple(words[i:i + 9])) for i in range(max(0, len(words) - 8))]

    before_hashes = shingle_hashes(before.words)
    after_hashes = shingle_hashes(after.words)
    matcher = difflib.SequenceMatcher(a=before_hashes, b=after_hashes, autojunk=True)
    raw = []
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            continue
        # Adjacent 9-gram windows overlap. A 1-token edit typically appears as
        # 9 differing windows; subtracting 8 from the side with changes avoids
        # inflating single number or word substitutions into whole paragraphs.
        old_start = min(i1 + 8, len(before.words))
        old_end = min(i2, len(before.words))
        new_start = min(j1 + 8, len(after.words))
        new_end = min(j2, len(after.words))
        # For short spans the padding must be ignored; keep original coordinates
        # so a 1-word change is never lost from the candidate list.
        if old_start >= old_end:
            old_start, old_end = i1, min(i2 + 8, len(before.words))
        if new_start >= new_end:
            new_start, new_end = j1, min(j2 + 8, len(after.words))
        a_len = old_end - old_start
        b_len = new_end - new_start
        raw.append({
            "before_page": page_for(before, old_start, skip),
            "after_page": page_for(after, new_start, skip),
            "before_words": a_len,
            "after_words": b_len,
            "before_excerpt": phrase(before.words, old_start, old_end),
            "after_excerpt": phrase(after.words, new_start, new_end),
            "before_offset": old_start,
            "after_offset": new_start,
            "anchor_match": "nine-word sequence",
        })
    return raw


def unmatched_phrases(source: Extracted, other: Extracted, skip: int) -> list[dict]:
    """Find content-level 9-word windows missing anywhere in the other corpus.

    This disregards pagination and block order, unlike the alignment diagnostic.
    A one-word edit loses up to nine windows; relocation alone does not.
    """
    width = 9
    other_windows = {
        tuple(other.words[i:i + width])
        for i in range(len(other.words) - width + 1)
    }
    missing = [
        tuple(source.words[i:i + width]) not in other_windows
        for i in range(len(source.words) - width + 1)
    ]
    ranges = []
    first = None
    for i, absent in enumerate(missing):
        if absent and first is None:
            first = i
        if not absent and first is not None:
            ranges.append((first, i))
            first = None
    if first is not None:
        ranges.append((first, len(missing)))
    return [
        {
            "page": page_for(source, start, skip),
            "unmatched_windows": end - start,
            "source_tokens": end - start + width - 1,
            "excerpt": phrase(source.words, start, min(end + width - 1, len(source.words)), 28),
            "source_offset": start,
        }
        for start, end in sorted(ranges, key=lambda pair: pair[1] - pair[0], reverse=True)
    ][:100]


def summarize(name: str, old: Extracted, new: Extracted, skip: int) -> dict:
    candidate_changes = changes(old, new, skip)
    by_magnitude = sorted(
        candidate_changes,
        key=lambda x: max(x["before_words"], x["after_words"]),
        reverse=True,
    )
    return {
        "pair": name,
        "old": {
            "path": old.path, "sha256": old.sha256,
            "pdf_pages": old.pages, "audited_words": len(old.words),
        },
        "new": {
            "path": new.path, "sha256": new.sha256,
            "pdf_pages": new.pages, "audited_words": len(new.words),
        },
        "excluded_front_pages": skip,
        "omitted_phrases": unmatched_phrases(old, new, skip),
        "added_phrases": unmatched_phrases(new, old, skip),
        "candidate_spans": len(candidate_changes),
        "largest_candidates": by_magnitude[:60],
        "small_candidates": [
            c for c in candidate_changes
            if max(c["before_words"], c["after_words"]) < 80
            and (re.search(r"\d", c["before_excerpt"] + c["after_excerpt"])
                 or max(c["before_words"], c["after_words"]) >= 5)
        ][:100],
        "warning": (
            "Automated text/order differences only; verify columns, charts, rules, "
            "and applicability visually before any semantic decision."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--pairs", nargs="+", choices=sorted(PAIRS),
        default=["its18-en", "faq-en", "faq-es"],
    )
    parser.add_argument("--output", default="local/audits/pdf-deltas-2026-11-06.json")
    args = parser.parse_args()
    output = ROOT / args.output
    if (
        output.resolve() == ROOT
        or ROOT not in output.resolve().parents
        or "local" not in output.relative_to(ROOT).parts
    ):
        parser.error("Output must be inside repository local/")
    pins = json.loads(PIN_PATH.read_text(encoding="utf-8"))
    expected = {
        artifact["path"].removeprefix("data/pdf/"): artifact["sha256"]
        for artifact in pins["artifacts"]
    }
    documents = {}
    results = []
    for name in args.pairs:
        before_name, after_name, skip = PAIRS[name]
        for relative in [before_name, after_name]:
            cache_key = (relative, skip)
            if cache_key not in documents:
                extracted = extract(relative, skip)
                if extracted.sha256 != expected.get(relative):
                    raise SystemExit(f"Unpinned or changed PDF: {relative} {extracted.sha256}")
                documents[cache_key] = extracted
        result = summarize(
            name, documents[(before_name, skip)], documents[(after_name, skip)], skip,
        )
        results.append(result)
        print(f'{name}: {result["old"]["pdf_pages"]}->{result["new"]["pdf_pages"]} pages; '
              f'{result["old"]["audited_words"]}->{result["new"]["audited_words"]} tokens; '
              f'{result["candidate_spans"]} candidate diff spans')
        for direction in ["added_phrases", "omitted_phrases"]:
            for candidate in result[direction][:4]:
                print(
                    f'  {direction} p {candidate["page"]} '
                    f'({candidate["unmatched_windows"]} 9-grams): '
                    f'{candidate["excerpt"][:115]!a}'
                )
        for candidate in result["largest_candidates"][:2]:
            print(f'  pp {candidate["before_page"]}->{candidate["after_page"]} '
                  f'({candidate["before_words"]}/{candidate["after_words"]} tokens): '
                  f'{candidate["before_excerpt"][:68]!a} => {candidate["after_excerpt"][:68]!a}')
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps({
        "method": (
            "version-locked PDF text extraction and nine-word sequence alignment; "
            "candidates are not rulings"
        ),
        "pairs": results,
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Report: {output.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
