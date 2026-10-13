from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path

import pytest

from tools.audit_1_0_reference_inputs import (
    SourceEvidenceError,
    _oldid_pin,
    _wiki_history_language,
    chart_name_evidence,
    verify_curated_wiki_snapshot,
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


def _curated_snapshot_fixture(
    tmp_path: Path, *, history_revision: int = 4109
) -> tuple[Path, Path, dict[str, object], list[dict[str, str | None]]]:
    snapshot = tmp_path / "WIKI-en 20260926-200832.zip"
    history = tmp_path / "history.zip"
    member = "Transmutation"
    def content(revision: int) -> str:
        return (
            '<html><script>RLCONF={"wgPageName":"Transmutation",'
            f'"wgRevisionId":{revision}'
            '}</script><main><h2><span>Transmutation '
            '(Escape System-X)</span></h2></main></html>'
        )

    with zipfile.ZipFile(snapshot, "w") as archive:
        archive.writestr(member, content(4109))
    with zipfile.ZipFile(history, "w") as archive:
        archive.writestr(member, content(history_revision))
    declared = {
        "id": "wiki-en-20260926-200832",
        "localPath": "data/wiki/WIKI-en 20260926-200832.zip",
        "sha256": hashlib.sha256(snapshot.read_bytes()).hexdigest(),
        "documentCount": 1,
    }
    references: list[dict[str, str | None]] = [
        {
            "sourceId": "wiki-en-20260926-200832",
            "member": member,
            "heading": "Transmutation (Escape System-X)",
        },
        {
            "sourceId": "wiki-en-20260926-200832",
            "member": member,
            "heading": "Transmutation (Escape System-X)",
        },
    ]
    return snapshot, history, declared, references


def test_curated_snapshot_verifies_declared_hash_members_and_headings(
    tmp_path: Path,
) -> None:
    snapshot, history, source, refs = _curated_snapshot_fixture(tmp_path)
    with zipfile.ZipFile(history) as historical:
        evidence = verify_curated_wiki_snapshot(
            snapshot, historical, [source, source.copy()], refs
        )
    assert evidence["status"] == "verified-local-source-and-locators"
    assert evidence["sourceDeclarations"] == 2
    assert evidence["references"] == 2
    assert evidence["uniquePages"] == 1
    assert evidence["headingsVerified"] == 2
    assert evidence["matchingHistoryPageRevisions"] == 1


@pytest.mark.parametrize(
    ("defect", "message"),
    [
        ("hash", "SHA-256"),
        ("member", "member"),
        ("heading", "heading"),
        ("revision", "revision mismatch"),
        ("filename", "archive name"),
        ("count", "member count"),
    ],
)
def test_curated_snapshot_rejects_unverified_source_locators(
    tmp_path: Path, defect: str, message: str
) -> None:
    snapshot, history, source, refs = _curated_snapshot_fixture(
        tmp_path, history_revision=4108 if defect == "revision" else 4109
    )
    if defect == "hash":
        source["sha256"] = "0" * 64
    elif defect == "member":
        refs[0]["member"] = "Escape_System"
    elif defect == "heading":
        refs[0]["heading"] = "Unrelated rule"
    elif defect == "filename":
        source["localPath"] = "data/wiki/incorrect.zip"
    elif defect == "count":
        source["documentCount"] = 2
    with zipfile.ZipFile(history) as historical:
        with pytest.raises(SourceEvidenceError, match=message):
            verify_curated_wiki_snapshot(snapshot, historical, [source], refs)


def test_curated_snapshot_rejects_conflicting_collection_source_pins(
    tmp_path: Path,
) -> None:
    snapshot, history, source, refs = _curated_snapshot_fixture(tmp_path)
    different = source.copy()
    different["sha256"] = "0" * 64
    with zipfile.ZipFile(history) as historical:
        with pytest.raises(SourceEvidenceError, match="consistent"):
            verify_curated_wiki_snapshot(snapshot, historical, [source, different], refs)


@pytest.mark.parametrize(
    ("url", "language"),
    [
        ("https://infinitythewiki.com/index.php?title=Protheion&oldid=3908", "en"),
        ("https://infinitythewiki.com/wiki-es/index.php?title=Inmunidad&oldid=3677", "es"),
        ("https://infinitythewiki.com/es/index.php?title=Tabla_de_Armas&oldid=3987", "es"),
    ],
)
def test_revision_source_language_follows_wiki_url(url: str, language: str) -> None:
    assert _wiki_history_language(url) == language


def test_spanish_revision_is_verified_from_language_matched_history(tmp_path: Path) -> None:
    url = "https://infinitythewiki.com/wiki-es/index.php?title=Inmunidad&oldid=3677"
    path = tmp_path / "spanish-history.zip"
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr(
            "_history/index.json",
            json.dumps({
                "format": "InfinityDB wiki revision history",
                "pages": [{
                    "revisions": [{
                        "url": url,
                        "path": "_history/oldid/3677.html",
                    }],
                }],
            }),
        )
        archive.writestr(
            "_history/oldid/3677.html",
            '<html><script>RLCONF={"wgPageName":"Inmunidad",'
            '"wgRevisionId":3677}</script></html>',
        )
    with zipfile.ZipFile(path) as archive:
        result = verify_wiki_revisions(archive, [{"id": "spanish", "url": url}])
    assert result[0]["status"] == "exact-revision-payload"
