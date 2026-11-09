from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

import tools.verify_deployment_assets as deployment_assets
from infinity_db.cli import main as infinity_db_main
from infinity_db.deployment_provenance import (
    DeploymentProvenanceError,
    publication_snapshot_sha256,
    validate_database_symbol_provenance,
)
from tools.verify_deployment_assets import DeploymentAssetError, verify_deployment_assets

SVG = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1 1"></svg>'


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_publication(
    project_root: Path, *, army_sha256: str = "a" * 64
) -> tuple[Path, Path]:
    static = project_root / "src" / "infinity_db" / "web" / "static"
    static.mkdir(parents=True)
    expected = (
        "armies/panoceania/101-test.svg",
        "units/panoceania/1-test-unit.svg",
        "orders/regular.svg",
        "characteristics/cube.svg",
    )
    digest = hashlib.sha256(SVG.encode()).hexdigest()
    for relative in expected:
        path = static / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(SVG, encoding="utf-8")

    publication_manifest = project_root / "data" / "manifests" / "symbol-publication.json"
    publication_manifest.parent.mkdir(parents=True, exist_ok=True)
    publication_manifest.write_text(
        json.dumps(
            {
                "format": "InfinityDB symbol publication mapping",
                "formatVersion": 2,
                "sourceSnapshot": {
                    "armyArtifact": {
                        "name": "army.zip",
                        "sha256": army_sha256,
                    }
                },
                "summary": {
                    "publishedAssetCount": len(expected),
                    "publishedBytes": len(SVG.encode()) * len(expected),
                },
                "factionIdToPublishedPath": {"101": expected[0]},
                "unitSlugToPublishedPath": {"test-unit": expected[1]},
                "unitProfileLogoToPublishedPath": {},
                "staticKeyToPublishedPath": {
                    "regular": expected[2],
                    "cube": expected[3],
                },
                "publishedSha256ByPath": {relative: digest for relative in expected},
                "browserUsageSummary": {
                    "browserReferencedAssetCount": len(expected),
                    "unreferencedPublishedAssetCount": 0,
                },
            },
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    return publication_manifest, static


def _build_fixture_database(tmp_path: Path, name: str) -> tuple[Path, str]:
    source = Path(__file__).resolve().parent / "fixtures" / "deployment-smoke"
    archive = tmp_path / f"{name}.zip"
    import zipfile

    with zipfile.ZipFile(archive, "w") as output:
        for path in source.iterdir():
            output.write(path, path.name)
        output.comment = name.encode("ascii")
    output_dir = tmp_path / name
    assert (
        infinity_db_main(["build", str(archive), "--output-dir", str(output_dir), "--compact"])
        == 0
    )
    return output_dir / "infinity.db", _sha256(archive)


def test_deployment_assets_require_complete_tracked_publication(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    publication_manifest, static = _write_publication(tmp_path)
    monkeypatch.setattr(deployment_assets, "validate_database_symbol_provenance", lambda *_: None)

    class FakeRulesDatabase:
        def __init__(self, path: Path) -> None:
            self.path = path

        def validate(self) -> None:
            pass

    monkeypatch.setattr(deployment_assets, "RulesDatabase", FakeRulesDatabase)
    # This test isolates symbol coverage; variant publication has separate
    # required-path and missing/stale-source regressions below.
    monkeypatch.setattr(deployment_assets, "verify_variant_release_publication", lambda *_: None)
    weapon_checks = []
    monkeypatch.setattr(
        deployment_assets, "verify_weapon_profile_release_publication",
        lambda *paths: weapon_checks.append(paths),
    )
    validation = verify_deployment_assets(
        static,
        database_path=tmp_path / "infinity.db",
        rules_database_path=tmp_path / "rules.db",
        publication_manifest_path=publication_manifest,
    )

    assert validation.complete
    assert validation.present_count == validation.expected_count
    assert weapon_checks == [(tmp_path / "infinity.db", tmp_path / "rules.db")]


def test_deployment_assets_reject_missing_published_svg(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    publication_manifest, static = _write_publication(tmp_path)
    (static / "units" / "panoceania" / "1-test-unit.svg").unlink()
    monkeypatch.setattr(deployment_assets, "validate_database_symbol_provenance", lambda *_: None)

    with pytest.raises(DeploymentAssetError, match="does not satisfy"):
        verify_deployment_assets(
            static,
            database_path=tmp_path / "infinity.db",
            rules_database_path=tmp_path / "rules.db",
            publication_manifest_path=publication_manifest,
        )


def test_deployment_assets_validate_rules_database(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    publication_manifest, static = _write_publication(tmp_path)
    monkeypatch.setattr(deployment_assets, "validate_database_symbol_provenance", lambda *_: None)

    with pytest.raises(ValueError, match="Rules database does not exist"):
        verify_deployment_assets(
            static,
            database_path=tmp_path / "infinity.db",
            rules_database_path=tmp_path / "missing-rules.db",
            publication_manifest_path=publication_manifest,
        )


@pytest.mark.parametrize(
    ("state", "expected_error"),
    [
        ("missing", "missing or empty"),
        ("empty", "missing or empty"),
        ("stale", "does not match release artifacts"),
    ],
)
def test_deployment_requires_release_paired_variant_publication(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, state: str, expected_error: str,
) -> None:
    def load(army: Path, rules: Path) -> tuple[dict | None, str | None]:
        assert army == tmp_path / "infinity.db"
        assert rules == tmp_path / "rules.db"
        if state == "missing":
            return None, None
        if state == "empty":
            return {"variants": []}, None
        raise ValueError("Variant usage publication does not match release artifacts")

    monkeypatch.setattr(deployment_assets, "load_runtime_variant_usage", load)
    with pytest.raises((DeploymentAssetError, ValueError), match=expected_error):
        deployment_assets.verify_variant_release_publication(
            tmp_path / "infinity.db", tmp_path / "rules.db",
        )


def test_deployment_accepts_release_paired_variant_publication(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        deployment_assets, "load_runtime_variant_usage",
        lambda *_: ({"variants": [{"variantKey": "reviewed"}]}, "reviewed"),
    )
    deployment_assets.verify_variant_release_publication(
        tmp_path / "infinity.db", tmp_path / "rules.db",
    )


def test_deployment_checks_weapon_profile_publication_against_reviewed_inputs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = []

    def check(army: Path, rules: Path, reviews: Path, publication: Path) -> None:
        calls.append((army, rules, reviews, publication))
        raise ValueError("reviewed publication is missing")

    monkeypatch.setattr(deployment_assets, "check_publication", check)
    with pytest.raises(ValueError, match="reviewed publication is missing"):
        deployment_assets.verify_weapon_profile_release_publication(
            tmp_path / "infinity.db", tmp_path / "rules.db",
        )
    assert calls == [(
        tmp_path / "infinity.db",
        tmp_path / "rules.db",
        deployment_assets.DEFAULT_REVIEWS,
        tmp_path / "weapon-profile-sources.json",
    )]


def test_deployment_rejects_database_for_different_publication_snapshot(tmp_path: Path) -> None:
    smoke_database, _ = _build_fixture_database(tmp_path, "smoke")
    _, production_sha256 = _build_fixture_database(tmp_path, "production")
    publication_manifest, _ = _write_publication(tmp_path, army_sha256=production_sha256)

    with pytest.raises(DeploymentProvenanceError, match="does not match tracked symbol"):
        validate_database_symbol_provenance(smoke_database, publication_manifest)


def test_deployment_accepts_matching_database_and_publication_provenance(tmp_path: Path) -> None:
    database, archive_sha256 = _build_fixture_database(tmp_path, "production")
    publication_manifest, _ = _write_publication(tmp_path, army_sha256=archive_sha256)

    assert validate_database_symbol_provenance(database, publication_manifest) == archive_sha256
    assert publication_snapshot_sha256(publication_manifest) == archive_sha256


def test_deployment_rejects_publication_without_snapshot_provenance(tmp_path: Path) -> None:
    publication_manifest, _ = _write_publication(tmp_path)
    document = json.loads(publication_manifest.read_text(encoding="utf-8"))
    document.pop("sourceSnapshot")
    publication_manifest.write_text(json.dumps(document), encoding="utf-8")

    with pytest.raises(DeploymentProvenanceError, match="sourceSnapshot.armyArtifact.sha256"):
        publication_snapshot_sha256(publication_manifest)


@pytest.mark.parametrize("mismatched", [False, True])
def test_svg_skip_still_checks_real_database_publication_binding(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mismatched: bool,
) -> None:
    database, digest = _build_fixture_database(tmp_path, "runtime")
    manifest, _ = _write_publication(tmp_path, army_sha256="0" * 64 if mismatched else digest)
    validated = []

    class Rules:
        def __init__(self, path: Path) -> None:
            self.path = path

        def validate(self) -> None:
            validated.append(self.path)

    monkeypatch.setattr(deployment_assets, "RulesDatabase", Rules)
    # This fixture checks the symbol/database source binding, not the separately
    # tested variant-publication gate; it has no variant-usage source pair.
    monkeypatch.setattr(
        deployment_assets, "verify_variant_release_publication", lambda *_: None,
    )
    monkeypatch.setattr(
        deployment_assets, "verify_weapon_profile_release_publication", lambda *_: None,
    )
    monkeypatch.setattr(deployment_assets, "validate_asset_set", lambda *_args, **_kwargs: (
        pytest.fail("SVG availability must not be checked in skip mode")
    ))
    rules = tmp_path / "rules.db"
    assert deployment_assets.main([
        "--skip-svg", "--database", str(database), "--rules-database", str(rules),
        "--publication-manifest", str(manifest),
    ]) == (1 if mismatched else 0)
    assert validated == ([] if mismatched else [rules])
