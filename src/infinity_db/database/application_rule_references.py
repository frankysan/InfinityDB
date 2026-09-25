"""Materialize structured Infinity Army rules-reference metadata for application use."""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ApplicationRuleReferenceModel:
    hacking_programs: tuple[dict[str, Any], ...]
    hacking_program_devices: tuple[dict[str, Any], ...]
    hacking_program_targets: tuple[dict[str, Any], ...]
    hacking_program_skill_types: tuple[dict[str, Any], ...]
    martial_arts_levels: tuple[dict[str, Any], ...]
    metachemistry_results: tuple[dict[str, Any], ...]
    booty_results: tuple[dict[str, Any], ...]


def _dict_rows(
    connection: sqlite3.Connection, table_name: str, order_by: str
) -> list[dict[str, Any]]:
    cursor = connection.execute(f'SELECT * FROM "{table_name}" ORDER BY {order_by}')
    columns = tuple(column[0] for column in cursor.description or ())
    return [dict(zip(columns, row, strict=True)) for row in cursor.fetchall()]


def _display_text(value: Any, *, field: str, required: bool = False) -> str | None:
    if value is None:
        if required:
            raise ValueError(f"{field} must be a nonempty string")
        return None
    if not isinstance(value, str):
        raise ValueError(f"{field} must be a string or null")
    text = " ".join(value.replace("\xa0", " ").split())
    if required and not text:
        raise ValueError(f"{field} must be a nonempty string")
    return text or None


def _json_list(value: Any, *, field: str, item_type: type) -> list[Any]:
    if value in (None, ""):
        return []
    decoded = value
    if isinstance(value, str):
        try:
            decoded = json.loads(value)
        except json.JSONDecodeError as exc:
            raise ValueError(f"{field} must contain a JSON array") from exc
    if not isinstance(decoded, list) or any(type(item) is not item_type for item in decoded):
        raise ValueError(f"{field} must be an array of {item_type.__name__} values")
    return decoded


def _optional_int(value: Any, *, field: str) -> int | None:
    if value is None:
        return None
    if type(value) is not int:
        raise ValueError(f"{field} must be an integer or null")
    return value


def _reference_rows(
    rows: Iterable[dict[str, Any]],
    *,
    id_field: str,
    kind: str,
) -> tuple[dict[str, Any], ...]:
    result: list[dict[str, Any]] = []
    for row in rows:
        identity = row.get(id_field)
        if type(identity) is not int:
            raise ValueError(f"{kind}.{id_field} must be an integer")
        result.append(
            {
                "id": identity,
                "roll": _display_text(row.get("name"), field=f"{kind}.name", required=True),
                "result": _display_text(row.get("value"), field=f"{kind}.value", required=True),
            }
        )
    return tuple(result)


def derive_application_rule_references(
    connection: sqlite3.Connection,
) -> ApplicationRuleReferenceModel:
    """Return validated application projections of the four structured Army reference sets."""

    hacking_programs: list[dict[str, Any]] = []
    hacking_program_devices: list[dict[str, Any]] = []
    hacking_program_targets: list[dict[str, Any]] = []
    hacking_program_skill_types: list[dict[str, Any]] = []
    equipment_names = {
        int(row["id"]): _display_text(
            row.get("name"),
            field="metadata_equipment.name",
            required=True,
        )
        for row in _dict_rows(connection, "metadata_equipment", "id")
    }

    for row in _dict_rows(connection, "metadata_hacking_programs", "position"):
        position = row.get("position")
        if type(position) is not int:
            raise ValueError("metadata_hacking_programs.position must be an integer")
        hacking_programs.append(
            {
                "position": position,
                "name": _display_text(
                    row.get("name"),
                    field="metadata_hacking_programs.name",
                    required=True,
                ),
                "attack_mod": _display_text(
                    row.get("attack"), field="metadata_hacking_programs.attack"
                ),
                "opponent_mod": _display_text(
                    row.get("opponent"), field="metadata_hacking_programs.opponent"
                ),
                "ps": _display_text(
                    row.get("damage"), field="metadata_hacking_programs.damage"
                ),
                "burst": _display_text(
                    row.get("burst"), field="metadata_hacking_programs.burst"
                ),
                "special": _display_text(
                    row.get("special"), field="metadata_hacking_programs.special"
                ),
                "source_extra_id": _optional_int(
                    row.get("extra"), field="metadata_hacking_programs.extra"
                ),
            }
        )
        devices = _json_list(
            row.get("devices"),
            field="metadata_hacking_programs.devices",
            item_type=int,
        )
        targets = _json_list(
            row.get("target"),
            field="metadata_hacking_programs.target",
            item_type=str,
        )
        skill_types = _json_list(
            row.get("skillType"),
            field="metadata_hacking_programs.skillType",
            item_type=str,
        )
        hacking_program_devices.extend(
            {
                "program_position": position,
                "position": index,
                "source_equipment_id": source_equipment_id,
                "source_equipment_name": equipment_names.get(source_equipment_id),
            }
            for index, source_equipment_id in enumerate(devices, start=1)
        )
        hacking_program_targets.extend(
            {
                "program_position": position,
                "position": index,
                "target": _display_text(
                    target,
                    field="metadata_hacking_programs.target[]",
                    required=True,
                ),
            }
            for index, target in enumerate(targets, start=1)
        )
        hacking_program_skill_types.extend(
            {
                "program_position": position,
                "position": index,
                "skill_type": _display_text(
                    skill_type,
                    field="metadata_hacking_programs.skillType[]",
                    required=True,
                ),
            }
            for index, skill_type in enumerate(skill_types, start=1)
        )

    martial_arts_levels: list[dict[str, Any]] = []
    for row in _dict_rows(connection, "metadata_martial_arts", "position"):
        position = row.get("position")
        if type(position) is not int:
            raise ValueError("metadata_martial_arts.position must be an integer")
        martial_arts_levels.append(
            {
                "position": position,
                "level": _display_text(
                    row.get("name"), field="metadata_martial_arts.name", required=True
                ),
                "attack_mod": _display_text(
                    row.get("attack"), field="metadata_martial_arts.attack"
                ),
                "opponent_mod": _display_text(
                    row.get("opponent"), field="metadata_martial_arts.opponent"
                ),
                "ps_mod": _display_text(
                    row.get("damage"), field="metadata_martial_arts.damage"
                ),
                "burst_mod": _display_text(
                    row.get("burst"), field="metadata_martial_arts.burst"
                ),
            }
        )

    metachemistry_results = _reference_rows(
        _dict_rows(connection, "metadata_metachemistry", "id"),
        id_field="id",
        kind="metadata_metachemistry",
    )
    booty_results = _reference_rows(
        _dict_rows(connection, "metadata_booty", "id"),
        id_field="id",
        kind="metadata_booty",
    )

    return ApplicationRuleReferenceModel(
        hacking_programs=tuple(hacking_programs),
        hacking_program_devices=tuple(hacking_program_devices),
        hacking_program_targets=tuple(hacking_program_targets),
        hacking_program_skill_types=tuple(hacking_program_skill_types),
        martial_arts_levels=tuple(martial_arts_levels),
        metachemistry_results=metachemistry_results,
        booty_results=booty_results,
    )


def materialize_application_rule_references(
    connection: sqlite3.Connection,
) -> ApplicationRuleReferenceModel:
    """Materialize structured reference rows before source-only metadata tables are removed."""

    model = derive_application_rule_references(connection)
    connection.executemany(
        "INSERT INTO application_hacking_programs "
        "(position, name, attack_mod, opponent_mod, ps, burst, special, source_extra_id) "
        "VALUES (:position, :name, :attack_mod, :opponent_mod, :ps, :burst, :special, "
        ":source_extra_id)",
        model.hacking_programs,
    )
    connection.executemany(
        "INSERT INTO application_hacking_program_devices "
        "(program_position, position, source_equipment_id, source_equipment_name) "
        "VALUES (:program_position, :position, :source_equipment_id, :source_equipment_name)",
        model.hacking_program_devices,
    )
    connection.executemany(
        "INSERT INTO application_hacking_program_targets "
        "(program_position, position, target) VALUES (:program_position, :position, :target)",
        model.hacking_program_targets,
    )
    connection.executemany(
        "INSERT INTO application_hacking_program_skill_types "
        "(program_position, position, skill_type) "
        "VALUES (:program_position, :position, :skill_type)",
        model.hacking_program_skill_types,
    )
    connection.executemany(
        "INSERT INTO application_martial_arts_levels "
        "(position, level, attack_mod, opponent_mod, ps_mod, burst_mod) "
        "VALUES (:position, :level, :attack_mod, :opponent_mod, :ps_mod, :burst_mod)",
        model.martial_arts_levels,
    )
    connection.executemany(
        "INSERT INTO application_metachemistry_results (id, roll, result) "
        "VALUES (:id, :roll, :result)",
        model.metachemistry_results,
    )
    connection.executemany(
        "INSERT INTO application_booty_results (id, roll, result) "
        "VALUES (:id, :roll, :result)",
        model.booty_results,
    )
    return model
