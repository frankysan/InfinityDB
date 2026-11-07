"""Validate source-context Include chains without inferring direct rule ownership."""

from __future__ import annotations

import json
import sqlite3
from collections import Counter, defaultdict
from typing import Any


def _ordered(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _owners(
    application: sqlite3.Connection, table: str, fields: tuple[str, ...],
) -> dict[tuple[int, ...], dict[str, Any]]:
    result = {}
    for row in application.execute(f"SELECT * FROM {table}"):
        key = tuple(row[field] for field in fields)
        if any(value is None for value in key) or key in result:
            raise ValueError(f"Missing or ambiguous Include owner: {table}/{key!r}")
        result[key] = dict(row)
    return result


def build_include_provenance(
    application: sqlite3.Connection, raw: sqlite3.Connection,
) -> dict[str, Any]:
    """Retain every source edge and chain after exact materialized-row parity.

    Nodes are source owner paths, never reusable payload IDs. A shared Unit
    option's target Army qualifies its target only, not the parent's membership.
    Repeated target visits through distinct source positions remain separate;
    quantity does not multiply paths or direct Skill/Equipment counts.
    """
    contexts = {
        "profile": _owners(application, "profile_payload_occurrences",
                           ("army_id", "unit_id", "group_id", "profile_id")),
        "option": _owners(application, "loadout_payload_occurrences",
                          ("army_id", "unit_id", "group_id", "option_id")),
        "unit_option": _owners(application, "unit_options", ("unit_id", "option_id")),
    }
    payloads = _owners(application, "loadout_payloads", ("id",))
    edges: list[dict[str, Any]] = []
    graph: dict[tuple[Any, ...], list[int]] = defaultdict(list)
    targets: list[tuple[Any, ...]] = []
    for owner, source_table, published_table, fields in (
        ("profile", "profile_includes", "profile_occurrence_includes",
         ("army_id", "unit_id", "group_id", "profile_id")),
        ("option", "option_includes", "loadout_occurrence_includes",
         ("army_id", "unit_id", "group_id", "option_id")),
        ("unit_option", "unit_option_includes", "unit_option_include_targets",
         ("unit_id", "option_id")),
    ):
        expected: list[tuple[Any, ...]] = []
        seen = set()
        columns = (*fields, "position")
        if owner == "unit_option":
            columns += ("target_army_id",)
        columns += ("target_loadout_payload_id", "quantity", "raw")
        for row in sorted(
            (dict(item) for item in raw.execute(f"SELECT * FROM {source_table}")),
            key=_ordered,
        ):
            path = tuple(row[field] for field in fields)
            key = (*path, row["position"])
            if any(value is None for value in key) or key in seen:
                raise ValueError(f"Missing or duplicate Include source key: {owner}/{key!r}")
            seen.add(key)
            if path not in contexts[owner]:
                raise ValueError(f"Missing Include parent: {owner}/{path!r}")
            if row["target_group_id"] is None or row["target_option_id"] is None:
                raise ValueError(f"Missing Include target key: {owner}/{key!r}")
            if owner == "unit_option":
                candidates = [
                    target for target in contexts["option"]
                    if target[1:] == (row["unit_id"], row["target_group_id"],
                                      row["target_option_id"])
                ]
            else:
                target = (row["army_id"], row["unit_id"], row["target_group_id"],
                          row["target_option_id"])
                candidates = [target] if target in contexts["option"] else []
            if not candidates:
                raise ValueError(f"Missing Include target owner: {owner}/{key!r}")
            for target in sorted(candidates):
                payload_id = contexts["option"][target]["loadout_payload_id"]
                if (payload_id,) not in payloads:
                    raise ValueError(f"Missing Include target payload: {payload_id!r}")
                published = {field: row[field] for field in (*fields, "position")}
                if owner == "unit_option":
                    published["target_army_id"] = target[0]
                published.update(target_loadout_payload_id=payload_id,
                                 quantity=row["quantity"], raw=row["raw"])
                expected.append(tuple(published[column] for column in columns))
                edge_key = [owner, *key, *target]
                source_node = (owner, *path)
                target_node = ("option", *target)
                graph[source_node].append(len(edges))
                targets.append(target_node)
                edges.append({
                    "kind": published_table, "owner": published,
                    "edgeKey": edge_key, "sourceOwnerPathKey": list(path),
                    "targetOwnerPathKey": list(target),
                })
        actual = [
            tuple(row[column] for column in columns)
            for row in application.execute(f"SELECT * FROM {published_table}")
        ]
        # A set would hide duplicated published edges or source truncation.
        if Counter(actual) != Counter(expected):
            raise ValueError(f"Include source/published rows differ: {published_table}")

    # Iterative depth-first traversal validates even disconnected cycles and
    # avoids recursion limits for long, otherwise valid source chains.
    active: set[tuple[Any, ...]] = set()
    complete: set[tuple[Any, ...]] = set()
    for root in sorted(graph, key=_ordered):
        stack = [(root, False)]
        while stack:
            node, leaving = stack.pop()
            if leaving:
                active.remove(node)
                complete.add(node)
                continue
            if node in active:
                raise ValueError(f"Cyclic Include source path: {node!r}")
            if node in complete:
                continue
            active.add(node)
            stack.append((node, True))
            stack.extend((targets[index], False) for index in reversed(graph.get(node, [])))

    paths = []
    for root in sorted(graph, key=_ordered):
        pending: list[tuple[int, ...]] = [(index,) for index in reversed(graph[root])]
        while pending:
            chain = pending.pop()
            endpoint = targets[chain[-1]]
            paths.append({
                "sourceOwnerKind": root[0], "sourceOwnerPathKey": list(root[1:]),
                "edgeKeys": [edges[index]["edgeKey"] for index in chain],
                "targetOwnerPathKey": list(endpoint[1:]),
                "relationshipKind": "include-context-only",
            })
            pending.extend((*chain, index) for index in reversed(graph.get(endpoint, [])))
    edges.sort(key=_ordered)
    paths.sort(key=_ordered)
    return {"includes": edges, "includePaths": paths}
