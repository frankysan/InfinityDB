from __future__ import annotations

import fnmatch
import json
import tomllib
from pathlib import Path

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


def test_runtime_databases_are_tracked_release_artifact_paths() -> None:
    gitignore = _read(".gitignore")
    attributes = _read(".gitattributes")

    assert "!data/generated/infinity.db" in gitignore
    assert "!data/generated/rules.db" in gitignore
    assert "data/generated/infinity.db binary" in attributes
    assert "data/generated/rules.db binary" in attributes


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


def test_local_test_deployment_is_loopback_only_and_isolated() -> None:
    script = _read("scripts/deploy-local-test.sh")
    assert "COMPOSE_PROJECT_NAME=infinitydb-test" in script
    assert "BIND_ADDRESS=127.0.0.1" in script
    assert "METRICS_BIND_ADDRESS=127.0.0.1" in script
    assert 'METRICS_PORT="$metrics_port"' in script
    assert "DOMAIN=localhost" in script
    assert "PRUNE_APP_IMAGES=0" in script
    assert "sh ./scripts/deploy.sh" in script


def test_stop_local_test_targets_only_isolated_compose_project() -> None:
    script = _read("scripts/stop-local-test.sh")
    assert "COMPOSE_PROJECT_NAME=infinitydb-test docker compose down" in script
    assert "docker compose down -v" not in script
    assert "prune-app-images" not in script
    assert "Production deployment was not targeted." in script


def test_low_level_deploy_can_disable_image_pruning() -> None:
    script = _read("scripts/deploy.sh")
    assert ': "${PRUNE_APP_IMAGES:=1}"' in script
    assert '[ "$PRUNE_APP_IMAGES" = "1" ]' in script
    assert "Application image pruning skipped for this deployment." in script


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


def test_wheel_packages_runtime_unit_filter_semantics() -> None:
    with (ROOT / "pyproject.toml").open("rb") as handle:
        project = tomllib.load(handle)

    catalog_data = project["tool"]["setuptools"]["data-files"][
        "share/infinity-db/config/catalogs"
    ]
    assert "config/catalogs/unit-filter-semantics.json" in catalog_data


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
