from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_runtime_web_import_does_not_load_build_time_normalization(tmp_path: Path) -> None:
    """Production imports must not require source-checkout build configuration."""
    script = r'''
import sys

from infinity_db.database import Database
from infinity_db.web.app import create_app

assert Database is not None
assert create_app is not None
blocked = {
    "infinity_db.database.importer",
    "infinity_army_data.normalize",
    "infinity_army_data.weapon_categories",
    "infinity_army_data.weapon_config",
    "infinity_army_data.weapon_profiles",
}
loaded = blocked.intersection(sys.modules)
if loaded:
    raise SystemExit(f"Runtime import loaded build-only modules: {sorted(loaded)!r}")
'''
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT / "src")
    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=tmp_path,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
