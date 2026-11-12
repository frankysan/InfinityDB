"""Focused canonical-path reconciliation tests."""

import json

import pytest

from tools.compare_symbol_canonical_paths import compare_paths


def test_path_mismatch_is_reported(tmp_path):
    legacy = tmp_path / "legacy"
    legacy.mkdir()
    (legacy / "old.svg").write_text("<svg/>")
    receipt = tmp_path / "receipt.json"
    receipt.write_text(json.dumps({
        "stage": "duplicateDetection", "status": "passed",
        "canonicalByArchivePath": {
            "new.svg": "new.svg", "duplicate.svg": "new.svg",
        },
    }))
    result = compare_paths(legacy, receipt)
    assert result == {
        "externalCanonicalCount": 1,
        "legacyCanonicalCount": 1,
        "externalOnly": ["new.svg"],
        "legacyOnly": ["old.svg"],
    }


def test_unpassed_receipt_rejected(tmp_path):
    receipt = tmp_path / "receipt.json"
    receipt.write_text(json.dumps({
        "stage": "duplicateDetection", "status": "failed",
    }))
    with pytest.raises(ValueError, match="passed"):
        compare_paths(tmp_path, receipt)
