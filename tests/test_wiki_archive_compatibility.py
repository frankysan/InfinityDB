"""Read-only downstream checks for independently acquired Wiki snapshots.

Real ignored archives are optional in CI; synthetic source-reader contracts live in
test_audit_1_0_reference_inputs.py. No acquisition or runtime build is performed.
"""

from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path

import pytest

from infinity_db.snapshot_provenance import load_snapshot_manifest
from tools.research.audit_1_0_reference_inputs import (
    _history_index,
    verify_wiki_revisions,
)

ROOT = Path(__file__).resolve().parents[1]
ACQUISITIONS = (
    ("en", "WIKI-en 20261116-075926", "WIKI-en-history 20261116-090844", 711, 2801),
    ("es", "WIKI-es 20261116-092640", "WIKI-es-history 20261116-101038", 930, 2655),
)


def _paths(stem: str) -> tuple[Path, Path, Path]:
    return (
        ROOT / "local/data/wiki" / f"{stem}.zip",
        ROOT / "local/data/manifests/snapshots" / f"{stem}.json",
        ROOT / "local/data/manifests/snapshots/inventories" / f"{stem}.inventory.json",
    )


@pytest.mark.parametrize("language,current,history,expected_pages,expected_revisions", ACQUISITIONS)
def test_copied_wiki_snapshot_pair_integrity(
    language: str, current: str, history: str, expected_pages: int, expected_revisions: int,
) -> None:
    for stem, is_history in ((current, False), (history, True)):
        archive_path, manifest_path, inventory_path = _paths(stem)
        if not all(path.is_file() for path in (archive_path, manifest_path, inventory_path)):
            pytest.skip("Ignored Wiki acquisition artifacts are not installed in this checkout")

        provenance = load_snapshot_manifest(manifest_path, archive=archive_path)
        inventory = json.loads(inventory_path.read_text(encoding="utf-8"))
        assert provenance["source"]["language"] == inventory["language"] == language
        assert inventory["format"] == "InfinityDB wiki snapshot inventory"
        assert inventory["formatVersion"] in (1, 2)
        assert inventory["history"] is is_history
        assert inventory["snapshot"]["archiveName"] == archive_path.name
        assert inventory["snapshot"]["archiveSha256"] == provenance["snapshot"]["archive"]["sha256"]
        assert inventory["snapshot"]["contentSha256"] == provenance["snapshot"]["contentSha256"]

        records = inventory["members"]
        expected = {record["path"]: record for record in records}
        assert len(expected) == len(records) == provenance["snapshot"]["documentCount"]
        with zipfile.ZipFile(archive_path) as archive:
            names = archive.namelist()
            assert len(names) == len(set(names)) == len(records)
            assert set(names) == set(expected)
            for info in archive.infolist():
                record = expected[info.filename]
                assert record["size"] == info.file_size
                with archive.open(info) as stream:
                    digest = hashlib.file_digest(stream, "sha256").hexdigest()
                assert record["sha256"] == digest

        pages = [record for record in records if record["kind"] == "current-page"]
        assert len(pages) == expected_pages
        assert all(page["path"].endswith(".html") for page in pages)
        assert all(page["page"]["url"].startswith("https://infinitythewiki.com/") for page in pages)
        url_to_member = {page["page"]["url"]: page["path"] for page in pages}
        assert len(url_to_member) == expected_pages
        assert all(url_to_member[page["page"]["url"]] == page["path"] for page in pages)
        assert any(len(Path(page["path"]).parts) > (2 if language == "es" else 1) for page in pages)
        if language == "es":
            assert all(page["path"].startswith("es/") for page in pages)
        else:
            assert all(not page["path"].startswith("es/") for page in pages)
        assert any("__u_" in page["path"] for page in pages)

        if is_history:
            assert sum(record["kind"] == "revision" for record in records) == expected_revisions
            assert sum(record["kind"] == "generated-index" for record in records) == 1
            parent = provenance["inputArtifact"]
            assert parent["name"] == f"{current}.zip"
            assert parent["sha256"] == load_snapshot_manifest(
                _paths(current)[1],
            )["snapshot"]["archive"]["sha256"]


@pytest.mark.parametrize("language,current,history,expected_pages,expected_revisions", ACQUISITIONS)
def test_real_wiki_history_reader_and_extracted_mirror(
    language: str, current: str, history: str, expected_pages: int, expected_revisions: int,
) -> None:
    archive_path, _, _ = _paths(history)
    mirror = ROOT / "local/data/wiki-extracted" / history
    if not archive_path.is_file() or not mirror.is_dir():
        pytest.skip("Ignored Wiki history ZIP or extracted mirror is unavailable")
    with zipfile.ZipFile(archive_path) as archive:
        index = json.loads(archive.read("_history/index.json"))
        assert index["language"] == language
        pages = index["pages"]
        assert len(pages) == expected_pages
        pins = _history_index(archive)
        revision_paths = {path for path in pins.values()}
        assert len(revision_paths) == expected_revisions
        assert revision_paths == {
            name for name in archive.namelist() if name.startswith("_history/oldid/")
        }
        samples = [
            record
            for page in pages
            for record in page["revisions"][:1]
        ][:4]
        assert samples
        for i, record in enumerate(samples):
            evidence = verify_wiki_revisions(
                archive, [{"id": f"sample-{i}", "url": record["url"]}]
            )
            assert evidence[0]["status"] == "exact-revision-payload"

        # Check extracted files by identity without making the mirror a dependency
        # of the provenance reader, runtime, or normal build.
        for name in [pages[0]["currentPath"], samples[0]["path"], "_history/index.json"]:
            assert (mirror / name).read_bytes() == archive.read(name)

        if language == "en":
            service = [p for p in pages if p["currentPath"] == "api.php.html"]
            assert len(service) == 1
            assert service[0]["revisions"] == []
            assert service[0]["currentPath"] in archive.namelist()
            assert service[0]["currentPath"] not in revision_paths


@pytest.mark.parametrize(
    ("language", "source_id", "legacy_member"),
    (
        ("en", "wiki-en-20260926-200832", "Labels"),
        ("es", "wiki-es-20261009-211304", "es/Esquivar"),
    ),
)
def test_existing_curated_wiki_pins_are_not_redirected(
    language: str, source_id: str, legacy_member: str,
) -> None:
    curated = json.loads(
        (ROOT / "data/curated/rules/n5-core-v5.3.json").read_text(encoding="utf-8")
    )
    sources = [source for source in curated["sources"] if source["id"] == source_id]
    assert len(sources) == 1
    source = sources[0]
    assert source["language"] == language
    legacy = ROOT / "local/data/wiki" / Path(source["localPath"]).name
    if not legacy.is_file():
        pytest.skip("Pinned legacy Wiki ZIP is unavailable")
    assert hashlib.sha256(legacy.read_bytes()).hexdigest() == source["sha256"]
    with zipfile.ZipFile(legacy) as archive:
        assert legacy_member in archive.namelist()
    current = next(item[1] for item in ACQUISITIONS if item[0] == language)
    new_zip = _paths(current)[0]
    if not new_zip.is_file():
        pytest.skip("New Wiki ZIP is unavailable")
    assert hashlib.sha256(new_zip.read_bytes()).hexdigest() != source["sha256"]
    with zipfile.ZipFile(new_zip) as archive:
        assert legacy_member not in archive.namelist()


def test_portable_html_citation_requires_exact_member_and_snapshot(tmp_path: Path) -> None:
    from tools.research.audit_1_0_reference_inputs import (
        SourceEvidenceError,
        verify_curated_wiki_snapshot,
    )

    snapshot = tmp_path / "WIKI-en 20261116-075926.zip"
    history = tmp_path / "WIKI-en-history 20261116-090844.zip"
    payload = (
        '<html><script>RLCONF={"wgRevisionId":123}</script>'
        '<h2>Portable section</h2></html>'
    )
    member = "Rules/Unicode__u_123456789abc.html"
    with zipfile.ZipFile(snapshot, "w") as archive:
        archive.writestr(member, payload)
    with zipfile.ZipFile(history, "w") as archive:
        archive.writestr(member, payload)
    source = {
        "id": "wiki-en-20261116-075926",
        "localPath": "data/wiki/" + snapshot.name,
        "sha256": hashlib.sha256(snapshot.read_bytes()).hexdigest(),
        "documentCount": 1,
    }
    reference = {
        "sourceId": source["id"], "member": member, "heading": "Portable section",
    }
    with zipfile.ZipFile(history) as archive:
        assert verify_curated_wiki_snapshot(
            snapshot, archive, [source], [reference],
        )["references"] == 1
        with pytest.raises(SourceEvidenceError, match="Unresolvable Wiki citation member"):
            verify_curated_wiki_snapshot(
                snapshot, archive, [source], [{**reference, "member": "Rules/Unicode"}],
            )
        with pytest.raises(SourceEvidenceError, match="Unresolvable Wiki citation member"):
            verify_curated_wiki_snapshot(
                snapshot, archive, [{**source, "id": "old-source"}], [reference],
            )
