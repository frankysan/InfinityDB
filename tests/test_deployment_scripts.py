from __future__ import annotations

import fnmatch
import io
import json
import tomllib
from pathlib import Path

import pytest

from infinity_db.web import release_notes

ROOT = Path(__file__).resolve().parents[1]


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def test_v10_preview_requires_linux_engine_before_staging(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    from types import SimpleNamespace

    from tools import preview_runtime_image

    stage = tmp_path / "candidate"
    stage.mkdir()
    monkeypatch.setattr(preview_runtime_image.shutil, "which", lambda _name: "docker")
    monkeypatch.setattr(
        preview_runtime_image.subprocess, "run",
        lambda *_args, **_kwargs: SimpleNamespace(returncode=1),
    )
    monkeypatch.setattr(
        preview_runtime_image, "prepare_bundle",
        lambda *_args: pytest.fail("Must not change image bundle without Docker"),
    )
    with pytest.raises(ValueError, match="Docker Desktop Linux engine is unavailable"):
        preview_runtime_image.preview_image(stage, "infinity-db:v10-preview-test")


def test_v10_preview_waits_for_health_then_checks_http_without_published_ports(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    from types import SimpleNamespace

    from tools import preview_runtime_image

    stage = tmp_path / "candidate"
    stage.mkdir()
    calls: list[tuple[str, ...]] = []
    bundles: list[tuple[Path, Path]] = []
    probes = 0

    def fake_run(
        args: list[str] | tuple[str, ...], **_kwargs: object,
    ) -> SimpleNamespace:
        nonlocal probes
        command = tuple(args)
        calls.append(command)
        if command[:3] == ("docker", "exec", "infinitydb-v10-preview-check"):
            if command[-1] == preview_runtime_image._HEALTH_PROBE:
                probes += 1
                return SimpleNamespace(returncode=1 if probes == 1 else 0)
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(preview_runtime_image.shutil, "which", lambda _name: "docker")
    monkeypatch.setattr(preview_runtime_image.subprocess, "run", fake_run)
    monkeypatch.setattr(preview_runtime_image.time, "sleep", lambda _seconds: None)
    monkeypatch.setattr(
        preview_runtime_image, "prepare_bundle",
        lambda source, output: bundles.append((source, output)),
    )
    preview_runtime_image.preview_image(stage, "infinity-db:v10-preview-test")

    run = next(call for call in calls if call[:3] == ("docker", "run", "-d"))
    assert "--network" not in run
    assert "-p" not in run and "--publish" not in run
    assert "--read-only" in run
    assert probes == 2
    assert sum(call[-1] == preview_runtime_image._HTTP_VERIFY for call in calls) == 1
    assert calls[-2][:2] == ("docker", "stop")
    assert calls[-1][:3] == ("docker", "image", "rm")
    assert bundles == [
        (stage, preview_runtime_image.DEFAULT_OUTPUT),
        (preview_runtime_image.DEFAULT_SOURCE, preview_runtime_image.DEFAULT_OUTPUT),
    ]


def test_compose_supports_explicit_bind_address_and_host_port() -> None:
    compose = _read("compose.yaml")
    assert "${BIND_ADDRESS:-0.0.0.0}:${HTTP_PORT:-80}:80" in compose
    assert (
        "${METRICS_BIND_ADDRESS:-127.0.0.1}:${METRICS_PORT:-9090}:9090"
        in compose
    )




def test_metrics_history_service_is_immutable_private_and_volume_backed() -> None:
    compose = _read("compose.yaml")
    dockerfile = _read("Dockerfile.metrics-history")

    assert "metrics-history:" in compose
    assert "dockerfile: Dockerfile.metrics-history" in compose
    assert "infinity-db-metrics-history:${METRICS_HISTORY_IMAGE_TAG:-latest}" in compose
    assert "read_only: true" in compose
    assert "- metrics_history:/var/lib/infinitydb-metrics" in compose
    assert "metrics_history:" in compose
    assert "ports:" not in compose.split("  metrics-history:", 1)[1].split("  caddy:", 1)[0]
    metrics_service = compose.split("  metrics-history:", 1)[1].split("  caddy:", 1)[0]
    assert "condition: service_healthy" in metrics_service

    assert "FROM python:3.11-slim" in dockerfile
    assert "tools/metrics_history.py /app/metrics_history.py" in dockerfile
    assert "USER metrics" in dockerfile
    assert "ENTRYPOINT" in dockerfile
    assert 'CMD ["run"]' in dockerfile


def test_installer_config_umask_does_not_leak_into_release_checkout() -> None:
    script = _read("scripts/install-or-update.sh")
    settings = script.split("Save these settings to", 1)[1].split(
        "prepare_tracked_release_file()", 1,
    )[0]
    assert "    (\n      umask 077\n" in settings
    assert 'chmod 600 "$config_file"' in settings
    assert '    )\n    echo "Saved deployment settings' in settings


def test_fingerprinted_svg_assets_are_byte_exact() -> None:
    attributes = _read(".gitattributes")
    assert "src/infinity_db/web/static/*.svg -text" in attributes
    assert "src/infinity_db/web/static/silhouettes/*.svg -text" in attributes


def test_deploy_brackets_app_replacement_with_noncritical_metrics_history_scrapes() -> None:
    script = _read("scripts/deploy.sh")

    app_build = script.index(
        'docker compose build --build-arg "INFINITY_DB_DISPLAY_VERSION=$display_version" app'
    )
    history_build = script.index("docker compose build metrics-history")
    history_verify = script.index("verify-metrics-history-image.sh")
    stop_history = script.index("\nstop_metrics_history\n", history_verify)
    closing = script.index('collect_metrics_history "closing"')
    app_up = script.index("docker compose up -d --no-build --wait app caddy")
    opening = script.index('collect_metrics_history "opening"')
    history_start = script.index("start_metrics_history", opening)

    assert app_build < history_build < history_verify
    assert history_verify < stop_history < closing < app_up < opening < history_start
    assert 'warn "metrics-history $phase sample failed' in script
    assert "application deployment remains active" in script
    assert "--no-deps metrics-history collect" in script
    assert "--legacy-generation-at-collection" in script
    assert "docker compose up -d --no-build metrics-history" in script


def test_metrics_history_image_verifier_uses_read_only_ephemeral_state() -> None:
    script = _read("scripts/verify-metrics-history-image.sh")

    assert "docker run --rm" in script
    assert "--read-only" in script
    assert "--tmpfs /tmp" in script
    assert "INFINITYDB_METRICS_HISTORY_DATABASE=/tmp/history.db" in script
    assert '"$image" status' in script


def test_deployment_image_pruning_covers_app_and_metrics_history() -> None:
    script = _read("scripts/prune-app-images.sh")

    assert "prune_repository infinity-db app application" in script
    assert "prune_repository infinity-db-metrics-history metrics-history metrics-history" in script
    assert 'reference=$repository:app-*' in script

def test_runtime_databases_are_tracked_release_artifact_paths() -> None:
    gitignore = _read(".gitignore")
    attributes = _read(".gitattributes")

    assert "!data/generated/infinity.db" in gitignore
    assert "!data/generated/rules.db" in gitignore
    assert "data/generated/infinity.db binary" in attributes
    assert "data/generated/rules.db binary" in attributes


def test_checkout_builds_never_enter_immutable_docker_release_context() -> None:
    dockerignore = _read(".dockerignore")
    dockerfile = _read("Dockerfile")
    prepare = _read("tools/prepare_runtime_bundle.py")
    deploy = _read("scripts/deploy.sh")

    assert "local/" in dockerignore
    assert "COPY --chown=appuser:appuser data/runtime/ /app/data/" in dockerfile
    assert 'DEFAULT_SOURCE = ROOT / "data/generated"' in prepare
    assert '"$python" -m tools.prepare_runtime_bundle' in deploy
    assert "checkout-runtime" not in deploy


def test_release_images_require_embedded_deployed_objects() -> None:
    dockerfile = _read("Dockerfile")
    dockerignore = _read(".dockerignore")
    gitignore = _read(".gitignore")
    deploy = _read("scripts/deploy.sh")
    workflow = _read(".github/workflows/deployment-smoke.yml")
    smoke = _read("scripts/verify-container-image.sh")

    assert "data/generated/*" in gitignore
    assert "!data/generated/deployed-objects.json" not in gitignore
    assert "!data/generated/deployed-objects.json" not in dockerignore
    assert "COPY --chown=appuser:appuser data/runtime/ /app/data/" in dockerfile
    assert "tools.prepare_runtime_bundle" in deploy
    assert deploy.index("tools.prepare_runtime_bundle") < deploy.index("docker compose build")
    assert "tools.build_deployed_object_publication" not in workflow
    assert "tools.build_deployed_object_publication" not in deploy
    assert "validate_database_set" in workflow
    assert workflow.index("tools.prepare_runtime_bundle") < workflow.index("docker build")
    assert "validate_database_set(data_dir)" in smoke
    assert "load_deployed_object_publication(" not in smoke
    assert 'rules.deployed_objects_payload(data_dir / "infinity.db")' in smoke
    assert '/api/deployed-objects' in smoke
    assert 'http://127.0.0.1:8000/deployed-objects' in smoke


def test_variant_usage_publication_is_byte_exact_and_packaged_for_tracked_release() -> None:
    gitignore = _read(".gitignore")
    attributes = _read(".gitattributes")
    dockerignore = _read(".dockerignore")
    dockerfile = _read("Dockerfile")
    deploy = _read("scripts/deploy.sh")
    smoke = _read("scripts/verify-container-image.sh")
    workflow = _read(".github/workflows/deployment-smoke.yml")
    source_workflow = _read(".github/workflows/source-checks.yml")

    assert "!data/generated/variant-usage.json" in gitignore
    assert "data/generated/variant-usage.json binary" in attributes
    assert "data/generated/*" in dockerignore
    assert "COPY --chown=appuser:appuser data/runtime/ /app/data/" in dockerfile
    assert (ROOT / "data/generated/variant-usage.json").is_file()
    assert "tools.build_variant_usage --publish" not in deploy
    assert "tools.build_deployed_object_publication" not in deploy
    assert 'expected_files = set(report["sha256"])' in smoke
    assert "load_runtime_variant_usage(" in smoke
    assert "/api/variant-usage?record_id=" in smoke
    assert "tools.verify_deployment_assets --skip-svg" in source_workflow
    assert "tools.verify_deployment_assets --skip-svg" in workflow
    assert workflow.index("Validate pinned exact-variant release publication") < workflow.index(
        "Build application image from verified tracked databases"
    )


def test_weapon_profile_citations_are_release_paired_and_packaged() -> None:
    gitignore = _read(".gitignore")
    attributes = _read(".gitattributes")
    dockerignore = _read(".dockerignore")
    dockerfile = _read("Dockerfile")
    smoke = _read("scripts/verify-container-image.sh")
    workflow = _read(".github/workflows/deployment-smoke.yml")
    determinism = _read("tools/build_determinism_manifest.py")

    assert "!data/generated/weapon-profile-sources.json" in gitignore
    assert "data/generated/weapon-profile-sources.json binary" in attributes
    assert "data/generated/*" in dockerignore
    assert "COPY --chown=appuser:appuser data/runtime/ /app/data/" in dockerfile
    assert (ROOT / "data/generated/weapon-profile-sources.json").is_file()
    assert 'expected_files = set(report["sha256"])' in smoke
    assert "load_runtime_weapon_profile_publication(" in smoke
    assert "/api/weapons/rifle" in smoke
    assert "RUN rm /app/data/weapon-profile-sources.json" not in workflow
    assert "Prepare immutable runtime bundle" in workflow
    assert "tools.build_weapon_profile_publication" in determinism
    assert "publication/weapon-profile-sources.json" in determinism


def test_release_installer_deploys_tracked_runtime_databases_without_rebuilding() -> None:
    script = _read("scripts/install-or-update.sh")
    assert "infinity-db build" not in script
    assert "build-rules" not in script
    assert "data/generated/infinity.db" in script
    assert "data/generated/rules.db" in script
    assert 'git cat-file -e "$release_tag:$path"' in script
    assert "Removing legacy untracked" in script
    assert "sh ./scripts/deploy.sh" in script


def test_release_installer_hands_off_to_target_release_installer_before_prompts() -> None:
    script = _read("scripts/install-or-update.sh")
    handoff = 'git show "$release_tag:scripts/install-or-update.sh"'
    prompt = "printf 'Continue with this release? [Y/n]: '"

    assert "INFINITY_DB_INSTALLER_BOOTSTRAP_TAG" in script
    assert handoff in script
    assert 'INFINITY_DB_INSTALLER_BOOTSTRAP_TAG="$release_tag" sh "$bootstrap_script"' in script
    assert script.index(handoff) < script.index(prompt)


def test_capacity_overrides_separate_resource_boundary_from_worker_count() -> None:
    resources = _read("compose.capacity-4cpu-4g.yaml")
    workers = _read("compose.capacity-4x4.yaml")

    assert "services:" in resources
    assert "  app:" in resources
    assert "cpus: 4.0" in resources
    assert "mem_limit: 4g" in resources
    assert "command:" not in resources
    assert "caddy:" not in resources
    assert "metrics-history:" not in resources

    assert "services:" in workers
    assert "  app:" in workers
    assert "command:" in workers
    assert "- --workers" in workers
    assert '- "4"' in workers
    assert "- --threads" in workers
    assert "cpus:" not in workers
    assert "mem_limit:" not in workers
    assert "caddy:" not in workers
    assert "metrics-history:" not in workers

    compose = _read("compose.yaml")
    dockerfile = _read("Dockerfile")
    app_service = compose.split("  app:", 1)[1].split("  metrics-history:", 1)[0]
    assert "cpus:" not in app_service
    assert "mem_limit:" not in app_service
    assert '"--workers", "2", "--threads", "4"' in dockerfile


def test_local_test_deployment_is_loopback_only_and_isolated() -> None:
    script = _read("scripts/deploy-local-test.sh")
    assert "COMPOSE_PROJECT_NAME=infinitydb-test" in script
    assert "BIND_ADDRESS=127.0.0.1" in script
    assert "METRICS_BIND_ADDRESS=127.0.0.1" in script
    assert 'METRICS_PORT="$metrics_port"' in script
    assert "DOMAIN=localhost" in script
    assert "PRUNE_APP_IMAGES=0" in script
    assert "sh ./scripts/deploy.sh" in script
    assert "isolated infinitydb-test volume" in script


def test_stop_local_test_preserves_by_default_and_purges_only_isolated_project() -> None:
    script = _read("scripts/stop-local-test.sh")

    assert "COMPOSE_PROJECT_NAME=infinitydb-test docker compose down" in script
    assert "COMPOSE_PROJECT_NAME=infinitydb-test docker compose down -v" in script
    assert "--purge" in script
    assert "preserving its volumes" in script
    assert "prune-app-images" not in script
    assert "Production deployment was not targeted." in script


def test_low_level_deploy_can_disable_image_pruning() -> None:
    script = _read("scripts/deploy.sh")
    assert ': "${PRUNE_APP_IMAGES:=1}"' in script
    assert '[ "$PRUNE_APP_IMAGES" = "1" ]' in script
    assert "Deployment image pruning skipped for this deployment." in script


def test_deploy_bakes_display_version_into_container_image() -> None:
    script = _read("scripts/deploy.sh")
    dockerfile = _read("Dockerfile")
    verifier = _read("scripts/verify-container-image.sh")

    assert "infinity_db.__display_version__" in script
    assert (
        'docker compose build --build-arg "INFINITY_DB_DISPLAY_VERSION=$display_version" app'
        in script
    )
    assert 'ARG INFINITY_DB_DISPLAY_VERSION=""' in dockerfile
    assert "INFINITY_DB_DISPLAY_VERSION=${INFINITY_DB_DISPLAY_VERSION}" in dockerfile
    assert 'os.environ.get("INFINITY_DB_DISPLAY_VERSION", "").strip()' in verifier
    assert "Browser footer does not show built display version" in verifier


def test_docker_build_copies_curated_wheel_data_inputs() -> None:
    dockerfile = _read("Dockerfile")

    assert "COPY data/curated/identities /app/data/curated/identities" in dockerfile
    assert "COPY data/curated/peripherals /app/data/curated/peripherals" in dockerfile
    assert "rm -rf /app/config /app/data/curated" in dockerfile


def test_container_build_packages_canonical_changelog() -> None:
    dockerfile = _read("Dockerfile")

    assert "COPY docs/CHANGELOG.md /app/docs/CHANGELOG.md" in dockerfile
    assert "rm -rf /app/config /app/data/curated /app/docs /app/data/manifests" in dockerfile

    with (ROOT / "pyproject.toml").open("rb") as handle:
        project = tomllib.load(handle)

    documentation = project["tool"]["setuptools"]["data-files"]["share/infinity-db/docs"]
    assert documentation == ["docs/CHANGELOG.md"]


@pytest.mark.parametrize(
    "heading", ["## Unreleased", "## [1.0.1] - Unreleased", "## [0.10.0] - 2026-10-07"],
)
@pytest.mark.parametrize("matching_content", [True, False])
def test_container_smoke_validates_canonical_release_notes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    heading: str,
    matching_content: bool,
) -> None:
    changelog = tmp_path / "CHANGELOG.md"
    changelog.write_text(
        f"# Changelog\n\n{heading}\n\n### Player summary\n\n"
        "- New player highlight.\n\n### Fixed\n\n- Corrected behavior.\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(release_notes, "maintained_documentation_path", lambda *_: changelog)
    monkeypatch.setenv("INFINITY_DB_DISPLAY_VERSION", "")
    page = release_notes.render_current_release_notes_html()
    if not matching_content:
        page = page.replace("New player highlight.", "Outdated player highlight.")
    page = f'<section aria-label="InfinityDB release notes">{page}</section>'
    restrictions = {
        "available": True, "evaluationSupported": False,
        "items": [
            *[
                {
                    "subject": "TAG", "action": "enter-prone",
                    "scope": "all", "operation": {
                        "kind": "state-entry", "qualifier": {},
                    },
                }
                for _ in range(11)
            ],
            {
                "subject": "Motorcycle", "action": "upward-jump",
                "scope": "while-mounted-upwards-only",
                "operation": {
                    "kind": "directional-skill-movement",
                    "qualifier": {"direction": "upward"},
                },
            },
            *[
                {
                    "subject": subject, "action": "lieutenant-selection",
                    "scope": "army-selection-only",
                    "operation": {
                        "kind": "army-role-selection",
                        "qualifier": {"role": "lieutenant"},
                    },
                }
                for subject in ("REM", "Irregular")
            ],
        ],
    }
    profile_citations = [{"source_id": "n5-core-v5.3-pdf", "page": 183}]
    rifle = {
        "profile_citations_available": True,
        "profiles": [{"profile_citations": profile_citations}],
    }
    payloads = {
        "/api/restrictions": restrictions,
        "/api/armies": {
            "items": [
                {"id": 101, "role": "main", "group_id": None},
                {"id": 102, "role": "sectorial", "group_id": 101},
            ]
        },
        "/api/skills/74": {"rules": ["Super-Jump"]},
        "/api/deployed-objects": {
            "items": [{} for _ in range(17)],
            "unresolved_deliveries": [{}],
        },
        "/api/weapons/rifle": rifle,
        "/api/version": {"version": "0.10.0", "snapshot_revision": "fixture"},
    }

    def urlopen(url: str, timeout: int) -> io.BytesIO:
        route = url.removeprefix("http://127.0.0.1:8000")
        body = (
            page if route == "/changes"
            else "Deployed objects" if route == "/deployed-objects"
            else json.dumps(payloads[route])
        )
        return io.BytesIO(body.encode("utf-8"))

    monkeypatch.setattr("urllib.request.urlopen", urlopen)
    script = _read("scripts/verify-container-image.sh")
    runtime_probe = script.split('docker exec "$container" python -c \'\n', 1)[1]
    runtime_probe = runtime_probe.split("\n'", 1)[0]
    code = compile(runtime_probe, "verify-container-image.sh", "exec")
    if matching_content:
        exec(code, {})
        rifle["profile_citations_available"] = False
        with pytest.raises(SystemExit, match="wrong Weapon Chart publication status"):
            exec(code, {})
        rifle["profile_citations_available"] = True
        for citation in (
            {"source_id": "n5-core-v5.3-pdf", "page": 184},
            {"source_id": "incorrect-source", "page": 183},
        ):
            profile_citations[:] = [citation]
            with pytest.raises(SystemExit, match="lost its reviewed Weapon Chart citation"):
                exec(code, {})
    else:
        with pytest.raises(SystemExit, match="canonical changelog"):
            exec(code, {})


def test_installed_wheel_smoke_runs_database_health_check() -> None:
    workflow = _read(".github/workflows/installed-wheel.yml")

    assert "python tools/installed_wheel_smoke.py" in workflow
    smoke = _read("tools/installed_wheel_smoke.py")
    assert '[main_cli, "database-health", "generated/infinity.db", "--require-raw"]' in smoke


def test_full_asset_checks_can_run_against_candidate_branch() -> None:
    workflow = _read(".github/workflows/full-asset-checks.yml")

    assert "workflow_dispatch:" in workflow
    assert "name: full-assets" in workflow
    assert "github.ref == 'refs/heads/main'" not in workflow


def test_wheel_packages_runtime_unit_filter_semantics() -> None:
    with (ROOT / "pyproject.toml").open("rb") as handle:
        project = tomllib.load(handle)

    catalog_data = project["tool"]["setuptools"]["data-files"][
        "share/infinity-db/config/catalogs"
    ]
    assert "config/catalogs/unit-filter-semantics.json" in catalog_data


def test_deployment_smoke_validates_current_image_without_rollback_rehearsal() -> None:
    """One immutable current image and startup check replace the v8 rollback rehearsal."""
    workflow = _read(".github/workflows/deployment-smoke.yml")
    expected_order = (
        "Validate pinned exact-variant release publication",
        "Prepare immutable runtime bundle",
        "Build application image from verified tracked databases",
        "Validate image and production startup",
    )
    positions = [workflow.index(fragment) for fragment in expected_order]
    assert positions == sorted(positions)
    assert (
        "sh scripts/verify-container-image.sh infinity-db:deployment-smoke --published-assets"
        in workflow
    )
    assert "rollback" not in workflow.lower()
    assert "--legacy-v8" not in workflow
    assert "data/generated/rules.db /app/data/rules.db" not in workflow
    assert "data/generated/deployed-objects.json /app/data/deployed-objects.json" not in workflow


def test_release_metadata_and_browser_matrix_are_not_default_pr_gates() -> None:
    source = _read(".github/workflows/source-checks.yml")
    browser = _read(".github/workflows/cross-browser-compatibility.yml")

    assert "python -m tools.release_metadata" not in source
    assert "tests/test_release_metadata.py" not in source
    assert "workflow_dispatch:" in browser
    assert "  pull_request:" not in browser
    assert "  push:" not in browser


def test_source_and_cross_browser_ci_validate_selected_database_set() -> None:
    source = _read(".github/workflows/source-checks.yml")
    browser = _read(".github/workflows/cross-browser-compatibility.yml")
    source_checkout = source.split("- name: Check out source", 1)[1].split(
        "- name: Set up Python", 1
    )[0]
    # Frozen reference-evidence tests use git show against pinned older commits.
    assert "fetch-depth: 0" in source_checkout
    command = "python -m infinity_db database-health --db-dir data/generated"
    for workflow in (source, browser):
        assert workflow.count(command) == 1
        assert "tools.build_deployed_object_publication" not in workflow
    assert source.index(command) < source.index("- name: Run source checks")
    assert browser.index(command) < browser.index("- name: Run selected critical journeys")
    assert "python tools/run_checks.py" in source


def test_source_ci_runs_one_full_suite_and_cross_platform_build_checks() -> None:
    workflow = _read(".github/workflows/source-checks.yml")
    job = workflow.split("  source-checks:", 1)[1].split("    steps:", 1)[0]
    matrix = job.split("      matrix:", 1)[1].split("    runs-on:", 1)[0]
    legs: dict[tuple[str, str], tuple[str, bool, int]] = {}
    for block in matrix.split("          - os: ")[1:]:
        os_name, *lines = block.splitlines()
        fields: dict[str, str] = {}
        for line in lines:
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            key, value = stripped.split(":", 1)
            assert key not in fields
            fields[key] = value.strip().strip('"')
        identity = (os_name.strip(), fields["label"])
        assert identity not in legs
        legs[identity] = (
            fields["check_args"], fields["primary"] == "true",
            int(fields["timeout_minutes"]),
        )

    primary_checks = (
        "--stage test --stage lint --stage docs "
        "--stage type --stage build --stage rules"
    )
    portable_checks = "--stage build --stage rules"
    assert legs == {
        ("ubuntu-latest", "3.11"): (primary_checks, True, 30),
        ("windows-latest", "3.11"): (portable_checks, False, 30),
        ("macos-latest", "3.11"): (portable_checks, False, 15),
        ("ubuntu-latest", "3.14"): (portable_checks, False, 15),
    }
    assert "matrix.check_args == '--all'" not in workflow
    assert "&& matrix.primary" in workflow
    assert "timeout-minutes: ${{ matrix.timeout_minutes }}" in job
    source_checks = workflow.split("- name: Run source checks", 1)[1].split(
        "- name: Report deterministic-output toolchain", 1
    )[0]
    assert "python tools/run_checks.py ${{ matrix.check_args }}" in source_checks
    assert "--test-workers" not in source_checks
    assert "matrix.test_workers" not in workflow
    assert "--assets required --build-source tests/fixtures/deployment-smoke" in source_checks


def test_wheel_packages_all_registered_static_assets() -> None:
    """Any asset in the live HTTP registry must survive wheel installation.

    The installed web module hashes these assets at import time; excluding a
    single asset prevents both wheel and production container startup.
    """
    from infinity_db.web.presentation import ASSETS

    with (ROOT / "pyproject.toml").open("rb") as handle:
        project = tomllib.load(handle)
    patterns = project["tool"]["setuptools"]["package-data"]["infinity_db.web"]
    uncovered = [
        name
        for name, _ in sorted(ASSETS.values())
        if not any(
            fnmatch.fnmatchcase("static/" + name, pattern)
            for pattern in patterns
        )
    ]
    assert uncovered == [], f"Web registry assets omitted from wheel: {uncovered}"


def test_wheel_package_data_includes_browser_icon_rasters() -> None:
    with (ROOT / "pyproject.toml").open("rb") as handle:
        project = tomllib.load(handle)

    patterns = project["tool"]["setuptools"]["package-data"]["infinity_db.web"]
    assert "static/*.png" in patterns


def test_wheel_package_data_includes_theme_palettes() -> None:
    with (ROOT / "pyproject.toml").open("rb") as handle:
        project = tomllib.load(handle)

    patterns = project["tool"]["setuptools"]["package-data"]["infinity_db.web"]
    assert "static/themes/*.css" in patterns


def test_wheel_package_data_covers_every_published_symbol() -> None:
    with (ROOT / "pyproject.toml").open("rb") as handle:
        project = tomllib.load(handle)
    publication = json.loads(
        (ROOT / "data/manifests/symbol-publication.json").read_text(encoding="utf-8")
    )

    patterns = project["tool"]["setuptools"]["package-data"]["infinity_db.web"]
    published = publication["publishedSha256ByPath"]
    uncovered = [
        relative
        for relative in sorted(published)
        if not any(
            fnmatch.fnmatchcase(f"static/{relative}", pattern) for pattern in patterns
        )
    ]

    assert uncovered == []


def test_container_verifier_uses_installed_tracked_publication_provenance() -> None:
    verifier = _read("scripts/verify-container-image.sh")

    assert "--packaged-assets|--published-assets" in verifier
    assert 'if [ "$packaged_assets" -eq 1 ]; then' in verifier
    assert 'if [ "$published_assets" -eq 1 ]; then' in verifier
    assert "validate_database_symbol_provenance" in verifier
    assert 'maintained_manifest_path("symbol-publication.json")' in verifier
    assert "army-symbol-build.json" not in verifier
    assert '-v "$(pwd)/data/manifests' not in verifier


def test_production_observability_disables_raw_access_logs_and_keeps_metrics_private() -> None:
    dockerfile = _read("Dockerfile")
    caddyfile = _read("Caddyfile")

    assert '"--access-logfile"' not in dockerfile
    assert '"--preload"' in dockerfile
    assert "/internal/health" in dockerfile
    assert "@internal path /internal/*" in caddyfile
    assert "respond @internal 404" in caddyfile
    assert "reverse_proxy app:8000" in caddyfile
    assert "http://:9090 {" in caddyfile
    assert "handle /metrics" in caddyfile
    assert "rewrite * /internal/metrics" in caddyfile
    assert "handle /health" in caddyfile
    assert "rewrite * /internal/health" in caddyfile


def test_metrics_lan_binding_is_persisted_and_rejects_wildcard_addresses() -> None:
    deploy = _read("scripts/deploy.sh")
    installer = _read("scripts/install-or-update.sh")
    local_test = _read("scripts/deploy-local-test.sh")

    assert ': "${METRICS_BIND_ADDRESS:=127.0.0.1}"' in deploy
    assert ': "${METRICS_PORT:=9090}"' in deploy
    assert r"0.0.0.0|::|\[::\]" in deploy
    assert "METRICS_BIND_ADDRESS=%s" in installer
    assert "METRICS_PORT=%s" in installer
    assert "METRICS_BIND_ADDRESS=127.0.0.1" in local_test
    assert 'METRICS_PORT="$metrics_port"' in local_test
