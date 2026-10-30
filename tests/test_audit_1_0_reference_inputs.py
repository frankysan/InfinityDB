from __future__ import annotations

import hashlib
import json
import zipfile
from functools import partial
from pathlib import Path

import pytest

from tools.audit_1_0_reference_inputs import (
    SourceEvidenceError,
    _oldid_pin,
    _wiki_history_language,
    _WikiErrataLabels,
    chart_name_evidence,
    verify_curated_wiki_snapshot,
    verify_curated_wiki_snapshots,
    verify_reinforcements_inputs,
    verify_wiki_revisions,
)


def _reinforcements_inventory(tmp_path: Path, present: tuple[str, ...]) -> Path:
    sources = []
    for language in ("en", "es"):
        relative = f"data/pdf/rules/reinforcement-rules-{language}.pdf"
        # Synthetic bytes test identity verification, not PDF interpretation.
        payload = f"%PDF synthetic historical fixture {language}".encode()
        if language in present:
            target = tmp_path / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(payload)
        sources.append({
            "id": f"reinforcements-n4-{language}", "language": language,
            "edition": "N4", "applicability": "historical-only",
            "localPath": relative, "sha256": hashlib.sha256(payload).hexdigest(),
            "sourceUrl": f"https://downloads.corvusbelli.com/infinity/rules/reinforcement-rules-{language}.pdf",
            "publishedDate": None,
        })
    path = tmp_path / "inventory.json"
    path.write_text(json.dumps({
        "formatVersion": 1, "scope": "historical-source-identity-not-n5-authority",
        "sources": sources,
    }), encoding="utf-8")
    return path


@pytest.mark.parametrize("present", ((), ("en",), ("en", "es")))
def test_historical_reinforcements_availability_does_not_establish_n5(
    tmp_path: Path, present: tuple[str, ...],
) -> None:
    evidence = verify_reinforcements_inputs(_reinforcements_inventory(tmp_path, present), tmp_path)
    assert evidence["declaredCount"] == 2
    assert evidence["verifiedCount"] == len(present)
    assert evidence["n5AuthorityVerified"] is False
    for source in evidence["items"]:
        assert source["edition"] == "N4" and source["publishedDate"] is None
        if source["language"] in present:
            assert source["status"] == "verified-pinned-historical-bytes"
            assert source["actualSha256"] == source["sha256"]
        else:
            assert source["status"] == "not-supplied"
            assert source["actualSha256"] is None


def test_historical_reinforcements_changed_bytes_fail_closed(tmp_path: Path) -> None:
    inventory = _reinforcements_inventory(tmp_path, ("en", "es"))
    (tmp_path / "data/pdf/rules/reinforcement-rules-en.pdf").write_bytes(b"new unknown revision")
    with pytest.raises(SourceEvidenceError, match="hash mismatch"):
        verify_reinforcements_inputs(inventory, tmp_path)


@pytest.mark.parametrize(
    "field,value,message",
    (("edition", "N5", "cannot establish N5"),
     ("applicability", "current", "cannot establish N5"),
     ("publishedDate", "2026-10-30", "cannot establish N5"),
     ("localPath", "data/pdf/rules/../../../outside.pdf", "Unsafe"),
     ("localPath", "C:/private/source.pdf", "Unsafe"),
     ("sha256", "not-a-sha256", "fingerprint"),
     ("sourceUrl", "https://example.invalid/annex.pdf", "official"),
     ("language", ["en"], "identity")),
)
def test_historical_source_inventory_rejects_unreviewed_claims(
    tmp_path: Path, field: str, value: object, message: str,
) -> None:
    inventory = _reinforcements_inventory(tmp_path, ())
    document = json.loads(inventory.read_text(encoding="utf-8"))
    document["sources"][0][field] = value
    inventory.write_text(json.dumps(document), encoding="utf-8")
    with pytest.raises(SourceEvidenceError, match=message):
        verify_reinforcements_inputs(inventory, tmp_path)


@pytest.mark.parametrize("present", ((), ("en",), ("en", "es")))
@pytest.mark.parametrize("core_hash_uppercase", (False, True))
def test_historical_reinforcements_report_uses_actual_availability(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, present: tuple[str, ...],
    core_hash_uppercase: bool,
) -> None:
    import sqlite3

    from tools import audit_1_0_reference_inputs as audit

    inventory = _reinforcements_inventory(tmp_path, present)
    monkeypatch.setattr(audit, "verify_reinforcements_inputs", partial(
        audit.verify_reinforcements_inputs, source_root=tmp_path,
    ))
    monkeypatch.setattr(audit, "audit_coverage", lambda *args: {"domains": {
        "weapons": {"items": []}, "skills": {"items": [{"name": "Commlink"}]},
    }})
    army = tmp_path / "army.db"
    army.touch()
    core = tmp_path / "core.pdf"
    core.write_bytes(b"synthetic N5 core")
    faq = tmp_path / "faq.pdf"
    faq.write_bytes(b"synthetic FAQ")
    rules = tmp_path / "rules.db"
    with sqlite3.connect(rules) as db:
        db.execute("CREATE TABLE sources(id, url, kind, title, version, sha256)")
        core_hash = hashlib.sha256(core.read_bytes()).hexdigest()
        db.execute("INSERT INTO sources VALUES (?, ?, ?, ?, ?, ?)", (
            "core", "https://example.invalid/core", "pdf", "N5 Core Rules", "5.3",
            core_hash.upper() if core_hash_uppercase else core_hash,
        ))
    history = _archive(tmp_path)
    with zipfile.ZipFile(history, "a") as archive:
        archive.writestr("Weapon_Chart", "<table></table>")
        archive.writestr("Commlink", "<h1>Commlink</h1>")
    report = audit.build_report(army, rules, history, core, faq, reinforcements_inventory=inventory)
    assert report["formatVersion"] == 3
    assert report["enrichmentGapEvidence"]["reinforcementsAnnexPdfSupplied"] is bool(present)
    assert report["enrichmentGapEvidence"]["reinforcementsN5AuthorityVerified"] is False
    markdown = audit.report_markdown(report)
    assert f"**{len(present)}/2**" in markdown
    assert "has not been supplied" not in markdown
    assert "not verified N5 procedural authority" in markdown
    assert "pin status: declared-hash-match" in markdown
    assert "no declared SHA" not in markdown


@pytest.mark.parametrize("defect", ("version", "extra-authority", "duplicate-language"))
def test_historical_inventory_contract_cannot_silently_expand(
    tmp_path: Path, defect: str,
) -> None:
    inventory = _reinforcements_inventory(tmp_path, ())
    document = json.loads(inventory.read_text(encoding="utf-8"))
    if defect == "version":
        document["formatVersion"] = True
    elif defect == "extra-authority":
        document["n5AuthorityVerified"] = True
    else:
        document["sources"][1]["language"] = "en"
    inventory.write_text(json.dumps(document), encoding="utf-8")
    with pytest.raises(SourceEvidenceError):
        verify_reinforcements_inputs(inventory, tmp_path)


def test_available_pinned_historical_reinforcements_bytes_match_review() -> None:
    root = Path(__file__).resolve().parents[1]
    inventory = root / "config/validation/reinforcements-source-inputs.json"
    document = json.loads(inventory.read_text(encoding="utf-8"))
    if not all((root / source["localPath"]).is_file() for source in document["sources"]):
        pytest.skip("Ignored historical PDFs unavailable; byte identity not verified")
    evidence = verify_reinforcements_inputs(inventory, root)
    assert evidence["verifiedCount"] == 2
    assert evidence["n5AuthorityVerified"] is False


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


def test_dated_errata_label_needs_bold_rule_and_date_in_one_block() -> None:
    english = _WikiErrataLabels()
    english.feed(
        '<div class="errata_border"><span class="errata_title">'
        '<b>Update</b><i>Mazebreaker, May 2026</i></span>'
        '<div class="errata_highlightblock"><b>Dodge (ARM+3)</b>'
        ' only applies under its conditions.</div></div>'
    )
    assert "dodge (arm+3): may 2026" in english.labels
    assert "dodge (arm+3): june 2026" not in english.labels

    spanish = _WikiErrataLabels()
    spanish.feed(
        '<div class="errata_border"><span class="errata_title">'
        '<b>Actualizaci?n</b><i>Mazebreaker, mayo 2026</i></span>'
        '<div class="errata_highlightblock"><b>Esquivar (BLI+3)</b>'
        ' y su MOD.</div></div>'
    )
    assert "esquivar (bli+3): mayo 2026" in spanish.labels

    # A date and rule label from different errata blocks must not combine.
    separate = _WikiErrataLabels()
    separate.feed(
        '<div class="errata_border"><span class="errata_title">'
        'May 2026</span><div class="errata_highlightblock">'
        '<b>Different Skill</b></div></div>'
        '<div class="errata_border"><span class="errata_title">'
        'June 2026</span><div class="errata_highlightblock">'
        '<b>Dodge (ARM+3)</b></div></div>'
    )
    assert "dodge (arm+3): may 2026" not in separate.labels


def test_bilingual_snapshots_require_exact_pins_and_matched_histories(
    tmp_path: Path,
) -> None:
    english, history_en, source_en, refs_en = _curated_snapshot_fixture(tmp_path)
    source_en["language"] = "en"
    spanish = tmp_path / "WIKI-es 20261009-211304.zip"
    history_es = tmp_path / "history-es.zip"
    payload = (
        '<html><script>RLCONF={"wgRevisionId":4012}</script>'
        '<h2>Esquivar (BLI+3)</h2></html>'
    )
    with zipfile.ZipFile(spanish, "w") as archive:
        archive.writestr("es/Esquivar", payload)
    with zipfile.ZipFile(history_es, "w") as archive:
        archive.writestr("es/Esquivar", payload)
    source_es = {
        "id": "wiki-es-20261009-211304",
        "language": "es",
        "localPath": "data/wiki/WIKI-es 20261009-211304.zip",
        "sha256": hashlib.sha256(spanish.read_bytes()).hexdigest(),
        "documentCount": 1,
    }
    refs = refs_en + [
        {"sourceId": source_es["id"], "member": "es/Esquivar", "heading": "Esquivar (BLI+3)"}
    ]
    sources = [source_en, source_en.copy(), source_es]
    with zipfile.ZipFile(history_en) as en, zipfile.ZipFile(history_es) as es:
        paths = {"en": english, "es": spanish}
        result = verify_curated_wiki_snapshots(
            sources, refs, paths, {"en": en, "es": es}
        )
        assert result["en"]["sourceDeclarations"] == 2
        assert result["en"]["references"] == 2
        assert result["es"]["sourceDeclarations"] == 1
        assert result["es"]["references"] == 1
        with pytest.raises(SourceEvidenceError, match="pinned languages"):
            verify_curated_wiki_snapshots(
                sources, refs, {"en": english}, {"en": en}
            )
        with pytest.raises(SourceEvidenceError, match="matching-language history"):
            verify_curated_wiki_snapshots(sources, refs, paths, {"en": en})
        with pytest.raises(SourceEvidenceError, match="matching page"):
            verify_curated_wiki_snapshots(
                sources, refs, paths, {"en": en, "es": en}
            )
        mismatched = tmp_path / "wrong-revision-history.zip"
        with zipfile.ZipFile(mismatched, "w") as archive:
            archive.writestr(
                "es/Esquivar", payload.replace('"wgRevisionId":4012', '"wgRevisionId":4011')
            )
        with zipfile.ZipFile(mismatched) as wrong:
            with pytest.raises(SourceEvidenceError, match="revision mismatch"):
                verify_curated_wiki_snapshots(
                    sources, refs, paths, {"en": en, "es": wrong}
                )
        incorrect_source = source_es.copy()
        incorrect_source["language"] = "en"
        with pytest.raises(SourceEvidenceError, match="spans languages"):
            verify_curated_wiki_snapshots(
                sources + [incorrect_source], refs, paths, {"en": en, "es": es}
            )
