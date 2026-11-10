#!/usr/bin/env python3
"""Exercise a built wheel in a fresh environment outside its source checkout."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import tomllib
from contextlib import contextmanager, nullcontext
from pathlib import Path
from typing import Any

SYMBOL_DIRECTORIES = ("armies", "characteristics", "orders", "peripherals", "units")


def clean_environment() -> dict[str, str]:
    env = os.environ.copy()
    for name in (
        "PYTHONPATH", "PYTHONHOME", "GIT_INDEX_FILE", "GIT_DIR", "GIT_WORK_TREE",
        "PIP_TARGET", "PIP_PREFIX", "PIP_USER", "VIRTUAL_ENV",
    ):
        env.pop(name, None)
    env["PYTHONNOUSERSITE"] = "1"
    return env


def remove_symbol_assets(static: Path, prefix: Path, *, require_assets: bool) -> None:
    for category in SYMBOL_DIRECTORIES:
        target = (static / category).resolve()
        if not target.is_relative_to(prefix.resolve()):
            raise ValueError("Refusing to remove assets outside the wheel environment")
        if require_assets and not target.is_dir():
            raise ValueError(f"Installed symbol directory missing: {category}")
        if target.exists():
            shutil.rmtree(target)


@contextmanager
def without_build_inputs(prefix: Path, static: Path):
    """Prove complete runtime startup cannot read installed build JSON."""
    with tempfile.TemporaryDirectory(prefix="runtime-inputs-", dir=prefix) as name:
        holding = Path(name).resolve()
        assert holding.is_relative_to(prefix.resolve())
        moved = []
        candidates = [prefix / "share/infinity-db/config", prefix / "share/infinity-db/data"]
        candidates.extend(static.rglob("*.json"))
        try:
            for index, source in enumerate(candidates):
                if source.exists():
                    if not source.resolve().is_relative_to(prefix.resolve()):
                        raise ValueError("Runtime resource move escaped installed environment")
                    target = holding / str(index)
                    shutil.move(str(source), str(target))
                    moved.append((source, target))
            yield
        finally:
            for source, target in reversed(moved):
                shutil.move(str(target), str(source))


def verify_runtime(work: Path, *, asset_free: bool, require_assets: bool) -> None:
    # This function runs under the wheel interpreter with -I, never the editable
    # source environment. Imports remain local so the orchestrator is stdlib-only.
    from importlib.resources import files
    from wsgiref.util import setup_testing_defaults

    import infinity_db
    from infinity_army_data.project_resources import maintained_config_path
    from infinity_db.database import Database
    from infinity_db.rules_database import RulesDatabase

    prefix = Path(sys.prefix).resolve()
    if (infinity_db.__file__ is None
            or not Path(infinity_db.__file__).resolve().is_relative_to(prefix)):
        raise ValueError("Smoke test imported application code outside the installed environment")
    share_root = prefix / "share/infinity-db/config"
    for parts in json.loads((work / "expected-config.json").read_text(encoding="utf-8")):
        path = maintained_config_path(*parts).resolve()
        if not path.is_file() or not path.is_relative_to(share_root):
            raise ValueError(f"Installed configuration unavailable: {'/'.join(parts)}")

    resource = files("infinity_db.web").joinpath("static")
    if not isinstance(resource, Path):
        raise ValueError("Installed wheel resources must be filesystem paths")
    static = resource.resolve()
    if asset_free:
        remove_symbol_assets(static, prefix, require_assets=require_assets)
    context = nullcontext() if asset_free else without_build_inputs(prefix, static)
    with context:
        from infinity_db.web import create_app, create_app_from_database_set

        # Both smoke modes exercise the same complete embedded runtime set.
        # The standalone generated/ fixture only covers the exporter CLI and
        # lacks the v12+ projections required by the application runtime.
        selected = work / "runtime"
        database = Database(selected / "army.db")
        database.validate()
        rules = RulesDatabase(selected / "rules_n5.db")
        rules.validate()
        if asset_free:
            # Embedded symbol provenance requires the published assets at
            # startup. An install with missing assets must fail closed.
            from infinity_db.symbol_catalog import SymbolCatalogError

            try:
                create_app(database.path, rules.path)
            except SymbolCatalogError as exc:
                if "Packaged symbol bytes differ or are missing" not in str(exc):
                    raise
            else:
                raise ValueError("Runtime accepted missing published symbol assets")
            print("Installed wheel missing-symbol rejection: PASS", flush=True)
            return
        app = create_app_from_database_set(selected)
        assert app.database.path == database.path
        assert app.rules_database is not None

        def request(path: str) -> int:
            environ: dict[str, Any] = {}
            setup_testing_defaults(environ)
            environ.update(PATH_INFO=path, QUERY_STRING="", REQUEST_METHOD="GET")
            statuses: list[int] = []

            def start_response(status: str, _headers: Any, _exc_info: Any = None) -> None:
                statuses.append(int(status.split()[0]))

            b"".join(app(environ, start_response))
            return statuses[0]

        for path in ("/", "/api/armies", "/units", "/skills", "/internal/health",
                     "/static/unit-symbols.js", "/changes"):
            assert request(path) == 200, path
    print("Installed wheel normal runtime: PASS", flush=True)


def smoke_wheel(wheel: Path, source: Path, work: Path, *, require_assets: bool) -> None:
    wheel, source, work = wheel.resolve(), source.resolve(), work.resolve()
    if work.is_relative_to(source) or source.is_relative_to(work):
        raise ValueError("Wheel smoke workspace must be separate from the source checkout")
    if work.exists() and any(work.iterdir()):
        raise ValueError("Wheel smoke workspace must be empty")
    work.mkdir(parents=True, exist_ok=True)
    env = clean_environment()

    def run(command: list[str], cwd: Path = work) -> None:
        print(f"Wheel smoke: {subprocess.list2cmdline(command)}", flush=True)
        subprocess.run(command, cwd=cwd, env=env, check=True)

    environment = work / "venv"
    run([sys.executable, "-m", "venv", str(environment)])
    scripts = environment / ("Scripts" if os.name == "nt" else "bin")
    python = str(scripts / ("python.exe" if os.name == "nt" else "python"))
    env["VIRTUAL_ENV"] = str(environment)
    env["PATH"] = str(scripts) + os.pathsep + env.get("PATH", "")
    run([python, "-I", "-m", "pip", "install", "--no-deps", "--no-index", str(wheel)])
    inputs = work / "inputs"
    inputs.mkdir()
    shutil.copytree(source / "tests/fixtures/deployment-smoke", inputs / "army")
    shutil.copytree(source / "data/curated/rules", inputs / "rules")
    project = tomllib.loads((source / "pyproject.toml").read_text(encoding="utf-8"))
    configured = project["tool"]["setuptools"]["data-files"]
    expected = [
        list(Path(path).parts[1:]) for paths in configured.values() for path in paths
        if Path(path).parts[0] == "config"
    ]
    (inputs / "expected-config.json").write_text(
        json.dumps(expected), encoding="utf-8", newline="\n",
    )
    suffix = ".exe" if os.name == "nt" else ""
    main_cli = str(scripts / f"infinity-db{suffix}")
    army_cli = str(scripts / f"infinity-army{suffix}")
    for command in (
        [main_cli, "--version"], [army_cli, "--version"],
        [army_cli, "build", "army", "--output-dir", "generated", "--compact"],
        [main_cli, "export", "generated/normalized.json", "generated/army.db"],
        [main_cli, "database-health", "generated/army.db", "--require-raw"],
        [army_cli, "build", "army", "--output-dir", "army-only", "--compact"],
        [main_cli, "build-rules", "--help"],
        [main_cli, "validate-curated", "rules"],
    ):
        run(command, inputs)
    # This controlled reference fixture tests the installed exporter and runtime.
    # Full source/Army-bound Rules builds belong to the checkout build workflow.
    run([python, "-I", "-c", "\n".join((
        "from pathlib import Path",
        "from infinity_db.curated import load_curated_directory",
        "from infinity_db.rules_database import export_rules_database",
        "export_rules_database(load_curated_directory(Path('rules')), "
        "Path('generated/rules_n5.db'))",
    ))], inputs)
    runtime = inputs / "runtime"
    runtime.mkdir()
    for name in ("army.db", "rules_n5.db", "its_18.db"):
        shutil.copyfile(source / "data/generated" / name, runtime / name)
    for mode in ("normal", "asset-free"):
        run([
            python, "-I", str(source / "tools/installed_wheel_smoke.py"),
            "--work-dir", str(inputs), "--verify-runtime", mode,
            "--assets", "required" if require_assets else "off",
        ], inputs)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wheel", type=Path)
    parser.add_argument("--work-dir", type=Path, required=True)
    parser.add_argument("--source-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--assets", choices=("off", "required"), default="required")
    parser.add_argument("--verify-runtime", choices=("normal", "asset-free"))
    args = parser.parse_args(argv)
    try:
        if args.verify_runtime:
            verify_runtime(
                args.work_dir, asset_free=args.verify_runtime == "asset-free",
                require_assets=args.assets == "required",
            )
        elif args.wheel is None:
            parser.error("--wheel is required for installed-wheel smoke")
        else:
            smoke_wheel(
                args.wheel, args.source_root, args.work_dir,
                require_assets=args.assets == "required",
            )
    except (OSError, ValueError, AssertionError, subprocess.CalledProcessError) as exc:
        print(f"Installed wheel smoke FAILED: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
