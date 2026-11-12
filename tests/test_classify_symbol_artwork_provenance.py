"""Reproducible input attribution, alias handling and rejection of disconnected evidence."""

from __future__ import annotations

import io
import json
import zipfile
from collections import Counter
from pathlib import Path

import pytest

from tools import classify_symbol_artwork_provenance as provenance


def fixture_inputs(tmp_path, *, split_alias=False, canonical_change=False):
    files = {}

    def store(role, value):
        content = value if isinstance(value, bytes) else json.dumps(value).encode()
        path = tmp_path / (role + ".input")
        path.write_bytes(content)
        files[role] = {"path": str(path), "sha256": provenance.digest(content)}
        return files[role]["sha256"]

    def archive(members):
        stream = io.BytesIO()
        with zipfile.ZipFile(stream, "w") as output:
            for name, content in members.items():
                output.writestr(name, content)
        return stream.getvalue()

    def document(format_name, **fields):
        return {"format": format_name, "formatVersion": 1, **fields}

    source_names = [f"units/{name}.svg" for name in ("a", "b", "c", "alias")]
    upstream = dict(zip(source_names, [b"raw-a", b"raw-b", b"raw-c", b"raw-b"], strict=True))
    old_bytes = dict(
        zip(
            source_names,
            [
                b"old-override-a",
                b"raw-b",
                b"stable-override-c",
                b"raw-alias" if split_alias else b"raw-b",
            ],
            strict=True,
        )
    )
    new_bytes = dict(
        zip(
            source_names,
            [
                b"new-override-a",
                b"new-override-b",
                b"stable-override-c",
                b"new-override-b",
            ],
            strict=True,
        )
    )
    old_rows, new_rows = [], []
    overrides = tmp_path / "overrides"
    overrides.mkdir()
    lookups = []
    for name in source_names:
        url = "https://example.test/" + name
        old_override = name in {"units/a.svg", "units/c.svg"}
        old_rows.append(
            {
                "archivePath": name,
                "url": url,
                "sha256": provenance.digest(old_bytes[name]),
                "upstreamSha256": provenance.digest(
                    old_bytes[name] if name == "units/alias.svg" else upstream[name]
                ),
                "sourceMethod": "override" if old_override else "cache",
            }
        )
        relative = "units/b.svg" if name == "units/alias.svg" else name
        new_rows.append(
            {
                "archivePath": name,
                "url": url,
                "sha256": provenance.digest(new_bytes[name]),
                "upstreamSha256": provenance.digest(upstream[name]),
                "sourceMethod": "override",
                "overridePath": relative,
                "overrideSha256": provenance.digest(new_bytes[name]),
            }
        )
        file = overrides / relative
        file.parent.mkdir(exist_ok=True)
        file.write_bytes(new_bytes[name])
        lookups.append({"url": url, "overridePath": name})
    # The historical override's upstream hash is recorded, not substituted for its effective bytes.
    old_rows[0]["upstreamSha256"] = provenance.digest(upstream["units/a.svg"])
    old_rows[2]["upstreamSha256"] = provenance.digest(upstream["units/c.svg"])
    old_map = {name: name for name in source_names}
    old_map["units/alias.svg"] = "units/alias.svg" if split_alias else "units/b.svg"
    new_map = {name: name for name in source_names}
    new_map["units/alias.svg"] = "units/b.svg"
    if canonical_change:
        new_map["units/b.svg"] = new_map["units/alias.svg"] = "units/alias.svg"
    army = {"name": "ARMY.zip", "sha256": "a" * 64}
    old_outputs = {c: ("old-output:" + c).encode() for c in set(old_map.values())}
    new_outputs = {c: ("new-output:" + c).encode() for c in set(new_map.values())}

    def publication(mapping, outputs):
        canonical = {
            c: ("units/b.svg" if c == "units/alias.svg" and canonical_change else c)
            for c in outputs
        }
        return {
            "format": "InfinityDB symbol publication mapping",
            "formatVersion": 2,
            "sourceSnapshot": {"armyArtifact": army},
            "publishedSha256ByPath": {
                canonical[c]: provenance.digest(b) for c, b in outputs.items()
            },
            "canonicalArchivePathToPublishedPath": canonical,
            "sourceArchivePathToPublishedPath": {s: canonical[c] for s, c in mapping.items()},
        }

    before, after = publication(old_map, old_outputs), publication(new_map, new_outputs)
    store("current_manifest", before)
    store("candidate_manifest", after)
    store("historical_archive", archive(old_bytes))
    store("effective_archive", archive(new_bytes))
    store("raw_archive", archive(upstream))
    store("candidate_compressed", archive(new_outputs))
    store("override_lookups", document("InfinityDB symbol override lookup plan", lookups=lookups))
    store(
        "duplicate_receipt",
        document(
            "InfinityDB symbol processing stage receipt",
            stage="duplicateDetection",
            status="passed",
            inputArtifact={"sha256": files["effective_archive"]["sha256"]},
            canonicalByArchivePath=new_map,
        ),
    )
    store(
        "effective_report",
        document(
            "InfinityDB effective symbol processing report",
            inputArtifact=army,
            assets=new_rows,
            snapshot={"sha256": files["effective_archive"]["sha256"]},
            rawSnapshot={"sha256": files["raw_archive"]["sha256"]},
            overrideLookupPlanSha256=files["override_lookups"]["sha256"],
        ),
    )
    store(
        "historical_compression",
        (
            "file,output_sha256\n"
            + "".join(c + "," + provenance.digest(b) + "\n" for c, b in old_outputs.items())
        ).encode(),
    )
    store(
        "historical_build",
        {
            "format": "InfinityDB army symbol build",
            "formatVersion": 8,
            "assets": old_rows,
            "snapshot": {
                "armyArtifact": army,
                "symbolArtifact": {"sha256": files["historical_archive"]["sha256"]},
            },
            "processing": {
                "publication": {
                    "publicationManifest": {"sha256": files["current_manifest"]["sha256"]}
                },
                "duplicateDetection": {"canonicalByArchivePath": old_map},
                "compression": {"report": {"sha256": files["historical_compression"]["sha256"]}},
            },
        },
    )
    store(
        "baseline_audit",
        document(
            "InfinityDB symbol production-source baseline audit",
            inputs={
                "symbolSha256": files["historical_archive"]["sha256"],
                "armySha256": army["sha256"],
            },
            counts={
                "verifiedArchiveMembers": 4,
                "effectiveMethods": dict(Counter(row["sourceMethod"] for row in old_rows)),
            },
        ),
    )
    store(
        "matched_inputs",
        document(
            "InfinityDB matched symbol parity input evidence",
            status="passed",
            matchedSourceIdentities=4,
            externalInputArtifacts={"compressedSha256": files["candidate_compressed"]["sha256"]},
            inputs={k: files[k]["sha256"] for k in ("duplicate_receipt", "effective_report")},
        ),
    )
    store(
        "candidate_evidence",
        document(
            "InfinityDB symbol publication candidate",
            status="prepared",
            publicationManifestSha256=files["candidate_manifest"]["sha256"],
            inputFiles={**files, "compressed_archive": files["candidate_compressed"]},
        ),
    )
    store(
        "comparison",
        document(
            "InfinityDB external symbol candidate publication comparison",
            baselineManifestSha256=files["current_manifest"]["sha256"],
            candidateManifestSha256=files["candidate_manifest"]["sha256"],
            assetComparison={
                "changed": ["units/a.svg", "units/b.svg", "units/c.svg"],
                "added": [],
                "missing": ["units/alias.svg"] if split_alias else [],
                "before": len(old_outputs),
                "after": len(new_outputs),
            },
        ),
    )
    store("override_notes", b"units:\na: source=vyo; pixel-identical\na: second declaration\n")
    selection = document(
        "InfinityDB symbol provenance inputs", files=files, overrideRoot=str(overrides)
    )
    selected = tmp_path / "inputs.json"
    selected.write_text(json.dumps(selection), encoding="utf-8")
    return selected, selection


def test_classifies_verified_bytes_without_guessing_file_history(tmp_path):
    selected, _ = fixture_inputs(tmp_path)
    report = provenance.classify(selected)
    assert report["summary"] == {
        **dict.fromkeys(provenance.CAUSES, 0),
        "override-content-changed": 1,
        "override-newly-applied": 1,
        "processing-only": 1,
    }
    assert report == provenance.classify(selected)
    a, b, c = report["assets"]
    assert (
        a["sources"][0]["historical"]["overrideSha256"]
        != (a["sources"][0]["candidate"]["overrideSha256"])
    )
    assert "filename/file history not recorded" in a["sources"][0]["historical"]["overrideEvidence"]
    assert "edit date unknown" in b["reason"]
    assert c["sources"][0]["historical"]["sourceMethod"] == "override"
    assert c["cause"] == "processing-only"  # Override involvement alone proves no change.
    # The notes claim pixel identity, but that claim does not establish the classification.
    assert len(a["sources"][0]["candidate"]["declaredOverrideNotes"]) == 2


def test_all_aliases_are_traced_including_propagated_override(tmp_path):
    selected, _ = fixture_inputs(tmp_path)
    b = provenance.classify(selected)["assets"][1]
    assert {s["archivePath"] for s in b["sources"]} == {"units/b.svg", "units/alias.svg"}
    alias = next(s for s in b["sources"] if s["archivePath"] == "units/alias.svg")
    assert alias["candidate"]["overrideApplication"] == "propagated"
    assert alias["candidate"]["overrideDonorSources"] == ["units/b.svg"]


def test_alias_remapping_does_not_replace_canonical_cause_or_close_compatibility(tmp_path):
    selected, _ = fixture_inputs(tmp_path, split_alias=True)
    report = provenance.classify(selected)
    b = report["assets"][1]
    assert b["sourceMappingChanged"]
    assert b["cause"] == "override-newly-applied"
    alias = next(s for s in b["sources"] if s["archivePath"] == "units/alias.svg")
    assert alias["cause"] == "unresolved"  # Both override application and raw identity changed.
    assert alias["historicalPublishedPath"] == "units/alias.svg"
    assert report["unresolvedCompatibility"] == ["units/alias.svg"]


def test_changed_canonical_selection_remains_unresolved(tmp_path):
    selected, _ = fixture_inputs(tmp_path, canonical_change=True)
    b = provenance.classify(selected)["assets"][1]
    assert b["cause"] == "unresolved"
    assert b["historicalCanonicals"] != b["candidateCanonicals"]


@pytest.mark.parametrize(
    "role",
    [
        "historical_archive",
        "candidate_manifest",
        "effective_report",
        "override_notes",
        "duplicate_receipt",
        "comparison",
        "matched_inputs",
    ],
)
def test_rejects_selected_input_drift(tmp_path, role):
    selected, selection = fixture_inputs(tmp_path)
    Path(selection["files"][role]["path"]).write_bytes(b"changed")
    with pytest.raises(ValueError, match="selected " + role):
        provenance.classify(selected)


@pytest.mark.parametrize(
    "role,key,value",
    [
        ("historical_build", "formatVersion", 99),
        ("effective_report", "inputArtifact", {"sha256": "f" * 64}),
        ("candidate_evidence", "status", "unverified"),
        ("matched_inputs", "matchedSourceIdentities", 99),
    ],
)
def test_rejects_repinned_but_disconnected_evidence(tmp_path, role, key, value):
    selected, selection = fixture_inputs(tmp_path)
    path = Path(selection["files"][role]["path"])
    document = json.loads(path.read_bytes())
    document[key] = value
    content = json.dumps(document).encode()
    path.write_bytes(content)
    selection["files"][role]["sha256"] = provenance.digest(content)
    selected.write_text(json.dumps(selection))
    with pytest.raises(ValueError):
        provenance.classify(selected)


def test_rejects_current_override_drift(tmp_path):
    selected, selection = fixture_inputs(tmp_path)
    (Path(selection["overrideRoot"]) / "units/a.svg").write_bytes(b"unrecorded edit")
    with pytest.raises(ValueError, match="current override bytes"):
        provenance.classify(selected)


@pytest.mark.parametrize(
    "old,new,expected",
    [
        (None, {}, "unresolved"),
        (
            {"sha256": "a", "sourceMethod": "cache"},
            {"sha256": "b", "sourceMethod": "network"},
            "upstream-source-changed",
        ),
        (
            {"sha256": "a", "sourceMethod": "override", "upstreamSha256": "x"},
            {"sha256": "b", "sourceMethod": "network", "upstreamSha256": "x"},
            "override-removed",
        ),
        (
            {"sha256": "a", "sourceMethod": "cache", "upstreamSha256": "x"},
            {"sha256": "b", "sourceMethod": "override", "upstreamSha256": "y"},
            "unresolved",
        ),
    ],
)
def test_source_cause_limits(old, new, expected):
    assert provenance.source_cause(old, new)[0] == expected


def test_notes_keep_duplicate_declarations_and_line_numbers():
    notes = provenance.parse_override_notes(b"units:\na: first\na: second\n")
    assert notes["units/a.svg"] == [{"line": 2, "text": "first"}, {"line": 3, "text": "second"}]


def test_zip_rejects_unsafe_members():
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w") as archive:
        archive.writestr("../outside.svg", "unsafe")
    with pytest.raises(ValueError, match="Unsafe SVG member"):
        provenance._zip(stream.getvalue())


def test_historical_member_hash_is_verified_independently_of_manifest_selector(tmp_path):
    selected, selection = fixture_inputs(tmp_path)
    path = Path(selection["files"]["historical_build"]["path"])
    document = json.loads(path.read_bytes())
    document["assets"][0]["sha256"] = "0" * 64
    content = json.dumps(document).encode()
    path.write_bytes(content)
    selection["files"]["historical_build"]["sha256"] = provenance.digest(content)
    selected.write_text(json.dumps(selection))
    with pytest.raises(ValueError, match="effective bytes units/a.svg"):
        provenance.classify(selected)


def test_cli_exclusive_local_output_and_no_partial_report(tmp_path, monkeypatch, capsys):
    selected, _ = fixture_inputs(tmp_path)
    monkeypatch.setattr(provenance, "ROOT", tmp_path)
    output = tmp_path / "local/result.json"
    args = ["--inputs", str(selected), "--output", str(output)]
    assert provenance.main(args) == 0
    first = output.read_bytes()
    with pytest.raises(SystemExit) as error:
        provenance.main(args)
    assert error.value.code == 1
    assert output.read_bytes() == first
    with pytest.raises(SystemExit):
        provenance.main(["--inputs", str(selected), "--output", str(tmp_path / "unsafe.json")])
    assert not (tmp_path / "unsafe.json").exists()
    assert "under ignored local" in capsys.readouterr().err
