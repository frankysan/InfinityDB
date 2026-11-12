"""Hermetic integrity and input validation for the local artwork review."""

from __future__ import annotations

import base64
import hashlib
import json
import re

import pytest

from tools import build_symbol_artwork_review as review

SVG = b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10"><path d="M0 0h5v5z"/></svg>'
NEW = SVG.replace(b"h5", b"h6")


def sha(content):
    return hashlib.sha256(content).hexdigest()


def write_json(path, value):
    content = json.dumps(value).encode()
    path.write_bytes(content)
    return sha(content)


@pytest.fixture
def inputs(tmp_path, monkeypatch):
    local = tmp_path / "local"
    local.mkdir()
    monkeypatch.setattr(review, "LOCAL_ROOT", local)
    current, candidate = tmp_path / "current", tmp_path / "candidate"
    for root in (current, candidate):
        (root / "units").mkdir(parents=True)
    (current / "units/a.svg").write_bytes(SVG)
    (candidate / "units/a.svg").write_bytes(NEW)
    (current / "units/old.svg").write_bytes(SVG)
    before = {
        "format": "InfinityDB symbol publication mapping", "formatVersion": 2,
        "publishedSha256ByPath": {"units/a.svg": sha(SVG), "units/old.svg": sha(SVG)},
        "canonicalArchivePathToPublishedPath": {"units/source.svg": "units/a.svg"},
        "sourceArchivePathToPublishedPath": {
            "units/source.svg": "units/a.svg", "units/alias.svg": "units/old.svg"},
        "sourceSnapshot": {"armyArtifact": {"name": "ARMY.zip", "sha256": "a" * 64}},
    }
    after = json.loads(json.dumps(before))
    after["publishedSha256ByPath"] = {"units/a.svg": sha(NEW)}
    after["sourceArchivePathToPublishedPath"]["units/alias.svg"] = "units/a.svg"
    current_manifest, candidate_manifest = tmp_path / "old.json", tmp_path / "new.json"
    record = {
        "format": "InfinityDB external symbol candidate publication comparison", "formatVersion": 1,
        "baselineManifestSha256": write_json(current_manifest, before),
        "candidateManifestSha256": write_json(candidate_manifest, after),
        "assetComparison": {
            "before": 2, "after": 1, "changed": ["units/a.svg"],
            "missing": ["units/old.svg"], "added": [],
        },
    }
    comparison = tmp_path / "comparison.json"
    write_json(comparison, record)
    return {
        "comparison": comparison, "current": current, "candidate": candidate,
        "output": local / "review.html", "current_manifest": current_manifest,
        "candidate_manifest": candidate_manifest,
    }


def payload(path):
    match = re.search(r'<script id="payload" type="application/json">(.*?)</script>',
                      path.read_text(encoding="utf-8"), re.S)
    assert match is not None
    return json.loads(match[1])


def test_report_embeds_exact_bytes_sources_and_compatibility(inputs):
    assert review.build_report(**inputs) == 0
    report = payload(inputs["output"])
    assert len(report["items"]) == 1
    item = report["items"][0]
    for key, content in (("current", SVG), ("candidate", NEW)):
        assert base64.b64decode(item[key].split(",")[1]) == content
    assert item["candidateSources"]["sourceArchivePathToPublishedPath"] == [
        "units/alias.svg", "units/source.svg"]
    assert report["removed"][0]["status"] == "unresolved compatibility requirement"
    assert report["removed"][0]["candidateDestinations"] == ["units/a.svg"]
    assert report["pins"]["candidateManifestSha256"] == sha(
        inputs["candidate_manifest"].read_bytes())
    assert report["candidateEvidence"] is None
    assert not any(inputs["output"].parent.glob("*.svg"))


def test_deterministic_output_and_no_overwrite(inputs):
    review.build_report(**inputs)
    first = inputs["output"].read_bytes()
    with pytest.raises(FileExistsError):
        review.build_report(**inputs)
    assert inputs["output"].read_bytes() == first
    inputs["output"] = inputs["output"].with_name("second.html")
    review.build_report(**inputs)
    assert inputs["output"].read_bytes() == first


@pytest.mark.parametrize("path", [
    "/a.svg", "../a.svg", "units/../a.svg", "C:/a.svg", "units\\a.svg",
    "units//a.svg", "./a.svg", "a.png", "a.svg\n", "//host/a.svg",
])
def test_rejects_noncanonical_paths(path):
    with pytest.raises(ValueError, match="Unsafe asset path"):
        review._asset_path(path)


@pytest.mark.parametrize("field", ["current_manifest", "candidate_manifest"])
def test_rejects_manifest_drift(inputs, field):
    inputs[field].write_bytes(inputs[field].read_bytes() + b" ")
    with pytest.raises(ValueError, match="Manifest hash mismatch"):
        review.build_report(**inputs)
    assert not inputs["output"].exists()


@pytest.mark.parametrize("key,value", [
    ("changed", []), ("changed", ["units/a.svg", "units/a.svg"]), ("missing", []),
    ("added", ["units/fake.svg"]), ("before", 999),
])
def test_rejects_incomplete_or_stale_inventory(inputs, key, value):
    record = json.loads(inputs["comparison"].read_bytes())
    record["assetComparison"][key] = value
    write_json(inputs["comparison"], record)
    with pytest.raises(ValueError, match="Comparison"):
        review.build_report(**inputs)
    assert not inputs["output"].exists()


@pytest.mark.parametrize("key,value", [
    ("formatVersion", 99), ("format", "other"), ("assetComparison", []),
])
def test_rejects_unsupported_comparison(inputs, key, value):
    record = json.loads(inputs["comparison"].read_bytes())
    record[key] = value
    write_json(inputs["comparison"], record)
    with pytest.raises(ValueError):
        review.build_report(**inputs)
    assert not inputs["output"].exists()


@pytest.mark.parametrize("root,path", [
    ("current", "units/a.svg"), ("candidate", "units/a.svg"), ("current", "units/old.svg"),
])
def test_rejects_asset_drift_including_removed_url(inputs, root, path):
    (inputs[root] / path).write_bytes(b"changed")
    with pytest.raises(ValueError, match="Asset hash mismatch"):
        review.build_report(**inputs)
    assert not inputs["output"].exists()


@pytest.mark.parametrize("content", [
    b"<svg", b"<html/>", b'<!DOCTYPE svg><svg xmlns="http://www.w3.org/2000/svg"/>',
])
def test_rejects_invalid_svg_before_writing(inputs, content):
    (inputs["candidate"] / "units/a.svg").write_bytes(content)
    manifest = json.loads(inputs["candidate_manifest"].read_bytes())
    manifest["publishedSha256ByPath"]["units/a.svg"] = sha(content)
    record = json.loads(inputs["comparison"].read_bytes())
    record["candidateManifestSha256"] = write_json(inputs["candidate_manifest"], manifest)
    write_json(inputs["comparison"], record)
    with pytest.raises(ValueError, match="SVG"):
        review.build_report(**inputs)
    assert not inputs["output"].exists()


def test_evidence_is_bound_and_embedded(inputs):
    evidence = inputs["comparison"].with_name("evidence.json")
    value = {
        "format": "InfinityDB symbol publication candidate", "formatVersion": 1,
        "status": "prepared", "publicationManifestSha256": sha(
            inputs["candidate_manifest"].read_bytes()),
        "inputFiles": {"raw": {"name": "SYMBOLS.zip", "sha256": "b" * 64}},
    }
    write_json(evidence, value)
    review.build_report(**inputs, candidate_evidence=evidence)
    report = payload(inputs["output"])
    assert report["candidateEvidence"] == value
    assert report["pins"]["candidateEvidenceSha256"] == sha(evidence.read_bytes())
    inputs["output"] = inputs["output"].with_name("bad.html")
    value["publicationManifestSha256"] = "f" * 64
    write_json(evidence, value)
    with pytest.raises(ValueError, match="evidence"):
        review.build_report(**inputs, candidate_evidence=evidence)


def test_metadata_cannot_break_out_of_payload(inputs):
    manifest = json.loads(inputs["candidate_manifest"].read_bytes())
    manifest["sourceSnapshot"] = {"name": "</script><img src=x onerror=alert(1)>"}
    record = json.loads(inputs["comparison"].read_bytes())
    record["candidateManifestSha256"] = write_json(inputs["candidate_manifest"], manifest)
    write_json(inputs["comparison"], record)
    review.build_report(**inputs)
    page = inputs["output"].read_text(encoding="utf-8")
    assert "</script><img" not in page
    assert payload(inputs["output"])["candidateSnapshot"] == manifest["sourceSnapshot"]
    assert "connect-src 'none'" in page


def test_refuses_output_outside_local(inputs):
    inputs["output"] = inputs["current"] / "review.html"
    with pytest.raises(ValueError, match="under ignored local"):
        review.build_report(**inputs)
    assert not inputs["output"].exists()


def review_args(inputs):
    return [
        "--comparison", str(inputs["comparison"]),
        "--current", str(inputs["current"]),
        "--candidate", str(inputs["candidate"]),
        "--current-manifest", str(inputs["current_manifest"]),
        "--manifest", str(inputs["candidate_manifest"]),
        "--output", str(inputs["output"]),
    ]


def comparison_args(inputs, output):
    return [
        "--write-comparison",
        "--comparison", str(output),
        "--current-manifest", str(inputs["current_manifest"]),
        "--manifest", str(inputs["candidate_manifest"]),
        "--expected-current-sha256", sha(inputs["current_manifest"].read_bytes()),
        "--expected-candidate-sha256", sha(inputs["candidate_manifest"].read_bytes()),
    ]


@pytest.mark.parametrize("flag", [
    "--comparison", "--current", "--candidate", "--current-manifest", "--manifest", "--output",
])
def test_cli_requires_explicit_review_inputs(inputs, flag, capsys):
    args = review_args(inputs)
    index = args.index(flag)
    del args[index:index + 2]
    with pytest.raises(SystemExit) as error:
        review.main(args)
    assert error.value.code == 2
    assert flag in capsys.readouterr().err
    assert not inputs["output"].exists()


def test_cli_fails_cleanly_without_creating_report(inputs, capsys):
    args = review_args(inputs)
    args[args.index("--comparison") + 1] = str(inputs["comparison"].with_name("absent.json"))
    with pytest.raises(SystemExit) as error:
        review.main(args)
    assert error.value.code == 1
    assert "Review generation failed" in capsys.readouterr().err
    assert not inputs["output"].exists()


def test_cli_writes_pinned_comparison_then_builds_review(inputs):
    comparison = inputs["output"].with_name("new-comparison.json")
    args = comparison_args(inputs, comparison)
    assert review.main(args) == 0
    assert json.loads(comparison.read_bytes()) == json.loads(inputs["comparison"].read_bytes())
    first = comparison.read_bytes()
    with pytest.raises(SystemExit) as error:
        review.main(args)
    assert error.value.code == 1
    assert comparison.read_bytes() == first

    second = comparison.with_name("second-comparison.json")
    assert review.main(comparison_args(inputs, second)) == 0
    assert second.read_bytes() == first
    inputs["comparison"] = comparison
    assert review.main(review_args(inputs)) == 0
    report = payload(inputs["output"])
    assert report["pins"]["comparisonSha256"] == sha(first)
    assert report["removed"][0]["status"] == "unresolved compatibility requirement"


def test_generated_comparison_includes_added_and_unchanged_assets(inputs):
    before = json.loads(inputs["current_manifest"].read_bytes())
    after = json.loads(inputs["candidate_manifest"].read_bytes())
    for root in ("current", "candidate"):
        (inputs[root] / "units/same.svg").write_bytes(SVG)
    (inputs["candidate"] / "units/new.svg").write_bytes(NEW)
    before["publishedSha256ByPath"]["units/same.svg"] = sha(SVG)
    after["publishedSha256ByPath"]["units/same.svg"] = sha(SVG)
    after["publishedSha256ByPath"]["units/new.svg"] = sha(NEW)
    write_json(inputs["current_manifest"], before)
    write_json(inputs["candidate_manifest"], after)

    comparison = inputs["output"].with_name("new-comparison.json")
    assert review.main(comparison_args(inputs, comparison)) == 0
    assert json.loads(comparison.read_bytes())["assetComparison"] == {
        "before": 3, "after": 3, "changed": ["units/a.svg"],
        "missing": ["units/old.svg"], "added": ["units/new.svg"],
    }
    inputs["comparison"] = comparison
    assert review.main(review_args(inputs)) == 0
    assert payload(inputs["output"])["added"] == ["units/new.svg"]


@pytest.mark.parametrize("flag", ["--expected-current-sha256", "--expected-candidate-sha256"])
def test_cli_rejects_missing_or_mismatched_comparison_pins(inputs, flag, capsys):
    comparison = inputs["output"].with_name("new-comparison.json")
    args = comparison_args(inputs, comparison)
    index = args.index(flag)
    missing = args[:index] + args[index + 2:]
    with pytest.raises(SystemExit) as error:
        review.main(missing)
    assert error.value.code == 2
    assert flag in capsys.readouterr().err
    args[index + 1] = "0" * 64
    with pytest.raises(SystemExit) as error:
        review.main(args)
    assert error.value.code == 1
    assert "Manifest hash mismatch" in capsys.readouterr().err
    args[index + 1] = "not-a-sha256"
    with pytest.raises(SystemExit) as error:
        review.main(args)
    assert error.value.code == 1
    assert "Invalid expected" in capsys.readouterr().err
    assert not comparison.exists()


@pytest.mark.parametrize("output", ["outside.json", "local/not-json.html"])
def test_comparison_refuses_invalid_output(inputs, output):
    destination = inputs["current"].parent / output
    with pytest.raises(ValueError, match="JSON file under ignored local"):
        review.write_comparison(
            inputs["current_manifest"], inputs["candidate_manifest"], destination,
            expected_current_sha256=sha(inputs["current_manifest"].read_bytes()),
            expected_candidate_sha256=sha(inputs["candidate_manifest"].read_bytes()),
        )
    assert not destination.exists()


def test_cli_rejects_review_only_inputs_in_comparison_mode(inputs, capsys):
    comparison = inputs["output"].with_name("new-comparison.json")
    args = comparison_args(inputs, comparison) + ["--current", str(inputs["current"])]
    with pytest.raises(SystemExit) as error:
        review.main(args)
    assert error.value.code == 2
    assert "--current" in capsys.readouterr().err
    assert not comparison.exists()


def test_cli_rejects_comparison_only_pins_in_review_mode(inputs, capsys):
    args = review_args(inputs) + ["--expected-current-sha256", "0" * 64]
    with pytest.raises(SystemExit) as error:
        review.main(args)
    assert error.value.code == 2
    assert "--expected-current-sha256" in capsys.readouterr().err
    assert not inputs["output"].exists()


def add_provenance(inputs):
    """Minimal renderer fixture; it does not establish source attribution."""
    pins = {
        "comparisonSha256": sha(inputs["comparison"].read_bytes()),
        "currentManifestSha256": sha(inputs["current_manifest"].read_bytes()),
        "candidateManifestSha256": sha(inputs["candidate_manifest"].read_bytes()),
        "candidateEvidenceSha256": None,
    }
    report = {
        "format": "InfinityDB symbol artwork provenance", "formatVersion": 1,
        "publicationPins": pins, "comparedAssets": 1,
        "summary": {**dict.fromkeys(review.CAUSES, 0), "override-newly-applied": 1},
        "assets": [{
            "path": "units/a.svg", "currentSha256": sha(SVG), "candidateSha256": sha(NEW),
            "cause": "override-newly-applied", "reason": "Verified renderer fixture input change.",
            "sources": [],
        }],
        "inputs": {}, "limits": ["Synthetic renderer fixture; no publication approval."],
    }
    path = inputs["comparison"].with_name("provenance.json")
    write_json(path, report)
    inputs["provenance"] = path
    return report


def test_provenance_is_embedded_and_changes_review_identity(inputs):
    review.build_report(**inputs)
    plain = payload(inputs["output"])
    inputs["output"] = inputs["output"].with_name("classified.html")
    report = add_provenance(inputs)
    review.build_report(**inputs)
    classified = payload(inputs["output"])
    assert classified["provenance"] == report
    assert classified["items"][0]["provenance"] == report["assets"][0]
    assert classified["reviewId"] != plain["reviewId"]
    assert classified["pins"]["provenanceSha256"] == sha(inputs["provenance"].read_bytes())


@pytest.mark.parametrize(
    "change",
    [
        "format", "version", "pins", "partial", "duplicates", "hash",
        "candidate-hash", "cause", "summary", "count",
    ],
)
def test_rejects_stale_or_inconsistent_provenance_before_writing(inputs, change):
    report = add_provenance(inputs)
    if change == "format":
        report["format"] = "unexpected"
    elif change == "version":
        report["formatVersion"] = 2
    elif change == "pins":
        report["publicationPins"]["candidateManifestSha256"] = "0" * 64
    elif change == "partial":
        report["assets"] = []
    elif change == "duplicates":
        report["assets"].append(report["assets"][0])
    elif change == "hash":
        report["assets"][0]["currentSha256"] = "0" * 64
    elif change == "candidate-hash":
        report["assets"][0]["candidateSha256"] = "0" * 64
    elif change == "cause":
        report["assets"][0]["cause"] = "guess"
    elif change == "summary":
        report["summary"]["processing-only"] = 999
    else:
        report["comparedAssets"] = 0
    write_json(inputs["provenance"], report)
    with pytest.raises(ValueError):
        review.build_report(**inputs)
    assert not inputs["output"].exists()


@pytest.mark.parametrize("width", (1440, 390, 320))
@pytest.mark.parametrize("classified", (False, True))
def test_browser_filters_overlay_and_exact_input_decision_roundtrip(
    inputs, tmp_path, chromium_test_slot, width, classified,
):
    sync = pytest.importorskip("playwright.sync_api")
    if classified:
        add_provenance(inputs)
    review.build_report(**inputs)
    with sync.sync_playwright() as driver:
        try:
            browser = driver.chromium.launch(channel="chrome")
        except sync.Error as error:
            if "Executable doesn't exist" in str(error) or "not found" in str(error):
                pytest.skip(f"Chrome unavailable: {error}")
            raise
        page = browser.new_page(viewport={"width": width, "height": 900})
        errors, failed = [], []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.on("requestfailed", lambda request: failed.append(request.url))
        page.goto(inputs["output"].as_uri())
        page.wait_for_function("()=>Array.from(document.images).every(x=>x.complete&&x.naturalWidth>0)")
        assert page.locator("article:visible").count() == 1
        page.locator("#search").fill("ALIAS")
        assert page.locator("article:visible").count() == 1
        page.locator("#search").fill("absent")
        assert page.locator("#empty").is_visible()
        page.locator("#search").fill("")
        page.locator("#category").select_option("units")
        page.locator("#cause").select_option(
            "override-newly-applied" if classified else "unclassified")
        assert page.locator("article:visible").count() == 1
        if classified:
            assert "Newly applied override: 1" in page.locator("#provenance-summary").inner_text()
        page.locator("#mode").select_option("overlay")
        assert page.locator(".overlay").is_visible()
        page.locator("#opacity").fill("25")
        assert page.locator(".candidate-layer").evaluate(
            "x=>getComputedStyle(x).opacity") == "0.25"
        page.locator("article select").nth(0).select_option("investigate")
        page.locator("article select").nth(1).select_option("source-change")
        page.locator("textarea").fill("Reviewer hypothesis; verify pinned raw bytes.")
        with page.expect_download() as download:
            page.locator("#export").click()
        export = tmp_path / "decisions.json"
        download.value.save_as(export)
        saved = json.loads(export.read_bytes())
        assert saved["unresolvedCompatibility"][0]["path"] == "units/old.svg"
        assert saved["decisions"]["units/a.svg"]["classification"] == "source-change"
        page.reload()
        assert page.locator("article select").nth(0).input_value() == "unreviewed"
        page.locator("#import").set_input_files(export)
        page.wait_for_function(
            "()=>document.querySelector('#status').textContent.startsWith('Imported')")
        assert page.locator("article select").nth(0).input_value() == "investigate"
        assert page.locator("textarea").input_value() == saved["decisions"]["units/a.svg"]["notes"]
        page.locator("#filter").select_option("accept")
        assert page.locator("#empty").is_visible()
        page.locator("#filter").select_option("investigate")
        assert page.locator("article:visible").count() == 1

        def import_value(value):
            page.locator("#status").evaluate("x=>x.textContent=''")
            page.locator("#import").set_input_files({
                "name": "review.json", "mimeType": "application/json",
                "buffer": json.dumps(value).encode(),
            })
            page.wait_for_function(
                "()=>document.querySelector('#status').textContent.startsWith('Import')")

        wrong = json.loads(json.dumps(saved))
        wrong["reviewId"] = "wrong"
        import_value(wrong)
        assert "Import failed" in page.locator("#status").inner_text()
        assert page.locator("article select").nth(0).input_value() == "investigate"
        bad = json.loads(json.dumps(saved))
        bad["decisions"]["units/a.svg"]["decision"] = "accept"
        bad["decisions"]["unknown.svg"] = saved["decisions"]["units/a.svg"]
        import_value(bad)
        assert "Import failed" in page.locator("#status").inner_text()
        # Reject the whole import, including the valid entry preceding the invalid one.
        assert page.locator("article select").nth(0).input_value() == "investigate"
        saved["decisions"] = {}
        import_value(saved)
        assert page.locator("article select").nth(0).input_value() == "unreviewed"
        page.locator("#filter").select_option("")
        assert page.evaluate("document.documentElement.scrollWidth<=innerWidth")
        assert errors == failed == []
        browser.close()
