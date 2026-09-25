from __future__ import annotations

import json
from pathlib import Path

import pytest

from infinity_db.equipment_config import (
    EQUIPMENT_PRESENTATION_CONFIG_FORMAT,
    EQUIPMENT_PRESENTATION_CONFIG_VERSION,
    EquipmentConfigError,
    parse_equipment_presentation_config,
)


def test_checked_in_equipment_presentation_config_maps_cube_symbols() -> None:
    document = json.loads(
        Path("config/catalogs/equipment-presentation-encodings.json").read_text(
            encoding="utf-8"
        )
    )

    encodings = parse_equipment_presentation_config(document)

    assert [(item.equipment_id, item.characteristic) for item in encodings] == [
        ("cube", "Cube"),
        ("cube-2", "Cube 2.0"),
    ]


def test_equipment_presentation_config_rejects_duplicate_characteristics() -> None:
    document = {
        "format": EQUIPMENT_PRESENTATION_CONFIG_FORMAT,
        "formatVersion": EQUIPMENT_PRESENTATION_CONFIG_VERSION,
        "encodings": [
            {
                "equipment_id": "cube",
                "characteristic": "Cube",
                "reason": "first",
            },
            {
                "equipment_id": "cube-2",
                "characteristic": "cube",
                "reason": "second",
            },
        ],
    }

    with pytest.raises(EquipmentConfigError, match="duplicate Equipment characteristic"):
        parse_equipment_presentation_config(document)
