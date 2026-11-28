"""Offline snapshot comparisons reuse the historical source and effective projections."""

import json
from copy import deepcopy
from datetime import UTC, date, datetime
from pathlib import Path
from zipfile import ZipFile

import pytest

from infinity_db.snapshot_provenance import SnapshotProvenanceError, write_snapshot_manifest
from tests.test_army_history_pilot import faction
from tools.data import compare_army_snapshots
from tools.data.compare_army_snapshots import compare_documents, compare_snapshots


def documents():
    army = faction()
    army["version"] = "7.26246.158"
    army["filters"] = {
        "skills": [{"id": 1, "name": "Engineer"}],
        "weapons": [{"id": 4, "name": "Rifle"}, {"id": 5, "name": "Pistol"}],
    }
    group = army["units"][0]["profileGroups"][0]
    group["profiles"][0]["skills"] = [{"id": 1}]
    group["options"][0]["skills"] = []
    second = deepcopy(group["options"][0])
    second["id"] = 2
    group["options"].append(second)
    return {
        "101-panoceania.json": army,
        "metadata.json": {"skills": [{"id": 1, "name": "Engineer"}]},
    }


def test_effective_skill_move_is_not_automatically_neutral():
    before = documents()
    after = deepcopy(before)
    group = after["101-panoceania.json"]["units"][0]["profileGroups"][0]
    group["profiles"][0]["skills"] = []
    group["options"][0]["skills"] = [{"id": 1}]
    report = compare_documents(before, after)
    effects = report["comparisons"][0]["effectiveReferences"]
    assert [(e["loadoutId"], e["category"]) for e in effects] == [
        (1, "effectiveOccurrenceEquivalent"), (2, "effectiveOccurrenceChange"),
    ]
    assert effects[1]["lost"][0]["filter"]["name"] == "Engineer"
    assert not effects[1]["gained"]
    group["options"][1]["skills"] = [{"id": 1}]
    report = compare_documents(before, after)
    assert report["effectiveReferenceCounts"] == {"effectiveOccurrenceEquivalent": 2}


def test_source_scope_and_metadata_changes():
    before = documents()
    after = deepcopy(before)
    after["102-army.json"] = faction()
    group = after["101-panoceania.json"]["units"][0]["profileGroups"][0]
    group["profiles"][0]["bs"] = 13
    group["options"][0]["weapons"].reverse()
    before["metadata.json"]["weapons"] = [{"id": 4, "damage": 12}]
    after["metadata.json"]["weapons"] = [{"id": 4, "damage": 13}]
    report = compare_documents(before, after)
    assert report["sharedMemberCount"] == 1
    assert report["changeCounts"]["observedMemberAppearance"] == 1
    assert report["metadataChanges"][0]["category"] == "weaponMechanicsCandidate"
    changes = report["comparisons"][0]["changes"]
    assert {c["path"][-1]: c["classification"] for c in changes} == {
        "bs": "gameplayCandidate", "weapons": "representation",
    }
    assert report["comparisons"][0]["sharedReferenceMetadataFindings"]


def test_unresolved_reference_is_review():
    before = documents()
    after = deepcopy(before)
    group = after["101-panoceania.json"]["units"][0]["profileGroups"][0]
    group["profiles"][0]["skills"] = [{"id": 99}]
    effects = compare_documents(before, after)["comparisons"][0]["effectiveReferences"]
    assert {e["reason"] for e in effects} == {"missingFactionDefinition"}


def snapshot(root: Path, name: str, data, language="en"):
    root.mkdir()
    archive = root / name
    with ZipFile(archive, "w") as output:
        for member, body in data.items():
            output.writestr(member, json.dumps(body))
    manifest = write_snapshot_manifest(
        archive, root, snapshot_type="army",
        source_data_changed_on=date(2026, 9, 3),
        acquired_at=datetime(2026, 9, 17, 12, 0, tzinfo=UTC),
        source_url="https://api.corvusbelli.com/army",
        document_count=len(data), project_root=root, language=language,
    )
    return archive, manifest


def test_manifest_pins_determinism_and_language(tmp_path):
    data = documents()
    a, am = snapshot(tmp_path / "a", "a.zip", data)
    b, bm = snapshot(tmp_path / "b", "b.zip", data)
    report = compare_snapshots(a, am, b, bm)
    assert report == compare_snapshots(a, am, b, bm)
    assert report["before"]["members"]["metadata.json"]["sha256"]
    assert report["before"]["manifestSha256"]
    assert report["before"]["members"]["101-panoceania.json"]["factionId"] == 101
    assert report["before"]["contentSha256"] == report["after"]["contentSha256"]
    assert not report["changeCounts"]
    c, cm = snapshot(tmp_path / "c", "c.zip", data, "es")
    with pytest.raises(ValueError, match="languages differ"):
        compare_snapshots(a, am, c, cm)
    with b.open("ab") as stream:
        stream.write(b"changed")
    with pytest.raises(SnapshotProvenanceError):
        compare_snapshots(a, am, b, bm)


def test_catalog_order_and_ambiguous_record_changes():
    before = documents()
    before["metadata.json"]["weapons"] = [
        {"id": 4, "damage": 12}, {"id": 4, "damage": 13},
    ]
    after = deepcopy(before)
    after["metadata.json"]["weapons"].reverse()
    report = compare_documents(before, after)
    assert report["metadataChanges"][0]["classification"] == "representation"
    after["metadata.json"]["weapons"][0]["damage"] = 14
    report = compare_documents(before, after)
    assert report["metadataChanges"][0]["classification"] == "gameplayCandidate"


def test_cli_output_is_deterministic_and_never_overwrites(tmp_path, monkeypatch, capsys):
    data = documents()
    a, am = snapshot(tmp_path / "a", "a.zip", data)
    b, bm = snapshot(tmp_path / "b", "b.zip", data)
    root = tmp_path / "reports"
    monkeypatch.setattr(compare_army_snapshots, "REPORT_DIRECTORY", root)
    args = [
        "compare_army_snapshots", str(a), str(b),
        "--before-manifest", str(am), "--after-manifest", str(bm),
    ]
    monkeypatch.setattr("sys.argv", args)
    assert compare_army_snapshots.main() == 0
    first = next(root.glob("*.json"))
    body = first.read_bytes()
    assert json.loads(capsys.readouterr().out)["sharedMemberCount"] == 1
    with pytest.raises(FileExistsError):
        compare_army_snapshots.main()
    assert first.read_bytes() == body
    second = root / "second.json"
    monkeypatch.setattr("sys.argv", args + ["--output", str(second)])
    assert compare_army_snapshots.main() == 0
    assert second.read_bytes() == body
    monkeypatch.setattr("sys.argv", args + ["--output", str(tmp_path / "outside.json")])
    with pytest.raises(SystemExit):
        compare_army_snapshots.main()
    assert not (tmp_path / "outside.json").exists()


def test_duplicate_army_list_identity_fails_closed(tmp_path):
    data = documents()
    data["101-other-name.json"] = data["101-panoceania.json"]
    a, am = snapshot(tmp_path / "a", "a.zip", data)
    with pytest.raises(ValueError, match="duplicate Army list identity"):
        compare_snapshots(a, am, a, am)
