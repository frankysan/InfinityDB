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
    assert "COPY tools/metrics_history.py /app/metrics_history.py" in dockerfile
    assert "USER metrics" in dockerfile
    assert "ENTRYPOINT" in dockerfile
    assert 'CMD ["run"]' in dockerfile


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


def test_deployed_object_publication_is_generated_and_verified_for_each_release_image() -> None:
    dockerfile = _read("Dockerfile")
    dockerignore = _read(".dockerignore")
    gitignore = _read(".gitignore")
    deploy = _read("scripts/deploy.sh")
    workflow = _read(".github/workflows/deployment-smoke.yml")
    smoke = _read("scripts/verify-container-image.sh")

    assert "data/generated/*" in gitignore
    assert "!data/generated/deployed-objects.json" not in gitignore
    assert "!data/generated/deployed-objects.json" in dockerignore
    assert (
        "COPY --chown=appuser:appuser data/generated/deployed-objects.json "
        "/app/data/deployed-objects.json"
    ) in dockerfile
    build = '"$python" -m tools.build_deployed_object_publication'
    assert deploy.index(build + "\n") < deploy.index(build + " --check")
    assert deploy.index(build + " --check") < deploy.index("docker compose build")
    ci_build = "PYTHONPATH=src python -m tools.build_deployed_object_publication"
    assert workflow.index(ci_build + "\n") < workflow.index(ci_build + " --check")
    assert workflow.index(ci_build + " --check") < workflow.index("docker build")
    assert '{"infinity.db", "rules.db", "deployed-objects.json"}' in smoke
    assert "load_deployed_object_publication(" in smoke
    assert '/api/deployed-objects' in smoke
    assert 'http://127.0.0.1:8000/deployed-objects' in smoke


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


@pytest.mark.parametrize("heading", ["## Unreleased", "## [0.10.0] - 2026-10-07"])
@pytest.mark.parametrize("matching_content", [True, False])
@pytest.mark.parametrize("restrictions_version", [8, 9])
def test_container_smoke_validates_canonical_notes_in_both_release_states(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    heading: str,
    matching_content: bool,
    restrictions_version: int,
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
    if restrictions_version == 9:
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
    else:
        restrictions = {
            "available": False, "evaluationSupported": False, "items": [],
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
    if matching_content:
        exec(compile(runtime_probe, "verify-container-image.sh", "exec"), {})
    else:
        with pytest.raises(SystemExit, match="canonical changelog"):
            exec(compile(runtime_probe, "verify-container-image.sh", "exec"), {})


def test_installed_wheel_smoke_runs_database_health_check() -> None:
    workflow = _read(".github/workflows/installed-wheel.yml")

    assert (
        '"$RUNNER_TEMP/wheel-venv/bin/infinity-db" database-health '
        "generated/infinity.db --require-raw"
    ) in workflow


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


def test_deployment_smoke_builds_and_exercises_v8_rollback_image() -> None:
    """Rehearse v8 with the same installed application, never overwrite v9."""
    workflow = _read(".github/workflows/deployment-smoke.yml")
    expected_order = (
        "sh scripts/verify-container-image.sh infinity-db:deployment-smoke --published-assets",
        "python -m infinity_db build-rules --output local/restrictions-v8-ci/rules.db",
        (
            "python -m tools.build_deployed_object_publication "
            "--rules-db local/restrictions-v8-ci/rules.db "
            "--output local/restrictions-v8-ci/deployed-objects.json"
        ),
        "--output local/restrictions-v8-ci/deployed-objects.json --check",
        'if old.execute("PRAGMA user_version").fetchone()[0] != 8:',
        "FROM ${BASE_IMAGE}",
        "COPY --chown=appuser:appuser rules.db /app/data/rules.db",
        "COPY --chown=appuser:appuser deployed-objects.json /app/data/deployed-objects.json",
        (
            "docker build --build-arg BASE_IMAGE=infinity-db:deployment-smoke "
            "--tag infinity-db:rollback-v8 local/restrictions-v8-ci"
        ),
        "sh scripts/verify-container-image.sh infinity-db:rollback-v8 --published-assets",
        "Verify v9 image remains valid after rollback rehearsal",
    )
    positions = [workflow.index(fragment) for fragment in expected_order]
    assert positions == sorted(positions)
    assert 'if expected != current_publication:' in workflow
    assert "Rollback modified the canonical legacy relationship graph" in workflow
    assert 'assert r.restrictions_payload()["available"] is False' in workflow
    assert "data/generated/rules.db /app/data/rules.db" not in workflow
    assert "data/generated/deployed-objects.json /app/data/deployed-objects.json" not in workflow


def test_source_ci_builds_ignored_release_publication_before_tests() -> None:
    workflow = _read(".github/workflows/source-checks.yml")
    generate = workflow.index("python -m tools.build_deployed_object_publication")
    verify = workflow.index("python -m tools.build_deployed_object_publication --check")
    source_checks = workflow.index("- name: Run source checks")
    assert generate < verify < source_checks
    assert "python tools/run_checks.py" in workflow


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
