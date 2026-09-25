from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def test_compose_supports_explicit_bind_address_and_host_port() -> None:
    compose = _read("compose.yaml")
    assert "${BIND_ADDRESS:-0.0.0.0}:${HTTP_PORT:-80}:80" in compose


def test_transferred_artifact_deployment_never_rebuilds_runtime_data() -> None:
    script = _read("scripts/deploy-transferred.sh")
    assert "infinity-db build" not in script
    assert "build-rules" not in script
    assert "sh ./scripts/deploy.sh" in script
    assert "app-v$version" in script
    assert ".infinity-db-deploy.env" in script


def test_local_test_deployment_is_loopback_only_and_isolated() -> None:
    script = _read("scripts/deploy-local-test.sh")
    assert "COMPOSE_PROJECT_NAME=infinitydb-test" in script
    assert "BIND_ADDRESS=127.0.0.1" in script
    assert "DOMAIN=localhost" in script
    assert "PRUNE_APP_IMAGES=0" in script
    assert "sh ./scripts/deploy-transferred.sh" in script


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


def test_container_verifier_separates_packaging_from_production_provenance() -> None:
    verifier = _read("scripts/verify-container-image.sh")

    assert "--packaged-assets|--published-assets" in verifier
    assert 'if [ "$packaged_assets" -eq 1 ]; then' in verifier
    assert 'if [ "$published_assets" -eq 1 ]; then' in verifier
    assert "validate_database_symbol_provenance" in verifier
