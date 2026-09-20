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


def test_low_level_deploy_can_disable_image_pruning() -> None:
    script = _read("scripts/deploy.sh")
    assert ': "${PRUNE_APP_IMAGES:=1}"' in script
    assert '[ "$PRUNE_APP_IMAGES" = "1" ]' in script
    assert "Application image pruning skipped for this deployment." in script
