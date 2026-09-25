from __future__ import annotations

import json
from pathlib import Path

from infinity_army_data.deterministic_io import json_text, write_json_lf, write_text_lf


def test_write_text_lf_normalizes_all_line_endings(tmp_path: Path) -> None:
    path = tmp_path / "output.txt"
    write_text_lf(path, "one\r\ntwo\rthree\n")
    assert path.read_bytes() == b"one\ntwo\nthree\n"


def test_write_json_lf_is_stable_and_sorted_when_requested(tmp_path: Path) -> None:
    path = tmp_path / "output.json"
    document = {"z": 1, "a": ["x", "y"]}
    write_json_lf(path, document, sort_keys=True)
    expected = json.dumps(document, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    assert path.read_bytes() == expected.encode("utf-8")
    assert json_text(document, compact=True, sort_keys=True) == '{"a":["x","y"],"z":1}'


def test_normalized_validation_is_stable_across_hash_seeds(tmp_path: Path) -> None:
    import os
    import subprocess
    import sys

    root = Path(__file__).resolve().parents[1]
    fixture = root / "tests" / "fixtures" / "deployment-smoke"
    outputs: list[bytes] = []
    for seed in ("1", "2"):
        target = tmp_path / seed
        env = os.environ.copy()
        env["PYTHONHASHSEED"] = seed
        env["PYTHONPATH"] = str(root / "src") + os.pathsep + env.get("PYTHONPATH", "")
        subprocess.run(
            [
                sys.executable,
                "-m",
                "infinity_db",
                "build",
                str(fixture),
                "--output-dir",
                str(target),
                "--compact",
            ],
            cwd=root,
            env=env,
            check=True,
            capture_output=True,
        )
        outputs.append((target / "normalized-validation.json").read_bytes())

    assert outputs[0] == outputs[1]


def test_persistent_path_write_text_calls_declare_newline_policy() -> None:
    import ast

    root = Path(__file__).resolve().parents[1]
    missing: list[str] = []
    for source_root in (root / "src", root / "tools"):
        for path in source_root.rglob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if not isinstance(node, ast.Call):
                    continue
                if not isinstance(node.func, ast.Attribute) or node.func.attr != "write_text":
                    continue
                keywords = {keyword.arg for keyword in node.keywords if keyword.arg is not None}
                if "newline" not in keywords:
                    relative = path.relative_to(root).as_posix()
                    missing.append(f"{relative}:{node.lineno}")

    assert missing == []
