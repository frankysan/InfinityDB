from __future__ import annotations

import json
import zipfile
from pathlib import Path

import pytest

from tools.audit_1_0_reference_inputs import (
    SourceEvidenceError,
    _oldid_pin,
    chart_name_evidence,
    verify_wiki_revisions,
)


def _archive(tmp_path: Path, *, title: str = "Protheion", revision: int = 3908,
             indexed_path: str = "_history/oldid/3908.html", write_payload: bool = True) -> Path:
    url = "https://infinitythewiki.com/index.php?title=Protheion&oldid=3908"
    archive = tmp_path / "wiki.zip"
    index = {
        "format": "InfinityDB wiki revision history",
        "pages": [{"revisions": [{"url": url, "path": indexed_path}]}],
    }
    with zipfile.ZipFile(archive, "w") as z:
        z.writestr("_history/index.json", json.dumps(index))
        if write_payload:
            z.writestr(indexed_path, (
                '<html><script>RLCONF={"wgPageName":"' + title
                + '","wgRevisionId":' + str(revision) + '}</script></html>'
            ))
    return archive


def test_verifies_historical_payload_even_when_current_page_is_newer(tmp_path: Path) -> None:
    path = _archive(tmp_path)
    with zipfile.ZipFile(path) as archive:
        records = verify_wiki_revisions(archive, [{
            "id": "protheion", "url":
            "https://infinitythewiki.com/index.php?title=Protheion&oldid=3908",
        }])
    assert records[0]["status"] == "exact-revision-payload"
    assert records[0]["archiveMember"] == "_history/oldid/3908.html"


@pytest.mark.parametrize(
    ("title", "revision", "expected"),
    [
        ("Different_Page", 3908, "payload-identity-mismatch"),
        ("Protheion", 4051, "payload-identity-mismatch"),
    ],
)
def test_rejects_wrong_page_or_revision(
    tmp_path: Path, title: str, revision: int, expected: str
) -> None:
    with zipfile.ZipFile(_archive(tmp_path, title=title, revision=revision)) as archive:
        result = verify_wiki_revisions(archive, [{
            "id": "protheion", "url":
            "https://infinitythewiki.com/index.php?title=Protheion&oldid=3908",
        }])
    assert result[0]["status"] == expected


def test_missing_historical_payload_is_not_a_verified_revision(tmp_path: Path) -> None:
    with zipfile.ZipFile(_archive(tmp_path, write_payload=False)) as archive:
        result = verify_wiki_revisions(archive, [{
            "id": "protheion", "url":
            "https://infinitythewiki.com/index.php?title=Protheion&oldid=3908",
        }])
    assert result[0]["status"] == "indexed-payload-missing"


def test_rejects_unsafe_history_paths(tmp_path: Path) -> None:
    with zipfile.ZipFile(_archive(tmp_path, indexed_path="../outside.html")) as archive:
        with pytest.raises(SourceEvidenceError, match="Unsafe"):
            verify_wiki_revisions(archive, [])


def test_revision_urls_require_one_exact_oldid() -> None:
    assert _oldid_pin(
        "https://infinitythewiki.com/index.php?title=360%C2%BA_Visor&oldid=3511"
    ) == ("360º_Visor", 3511)
    assert _oldid_pin("https://example.invalid/index.php?title=Protheion") is None
    assert _oldid_pin(
        "https://example.invalid/index.php?title=Protheion&oldid=5&oldid=6"
    ) is None


def test_weapon_chart_name_evidence_is_not_rule_definition_coverage() -> None:
    page = """<nav>Unrelated Rifle</nav><table><tr><td>AP+DA CC Weapon</td>
    <td>8</td></tr><tr><td>Combi Rifle</td></tr></table>"""
    result = chart_name_evidence(page, ["Combi Rifle", "Rifle", "Unrelated Rifle"])
    assert [item["evidence"] for item in result] == [
        "name-in-chart-text", "name-in-chart-text", "not-seen"
    ]
