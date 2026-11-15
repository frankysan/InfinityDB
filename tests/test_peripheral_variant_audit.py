"""Name-only Army capabilities are review signals, never inferred facts."""
from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from tools.data import audit_peripheral_variant_payloads as audit


def test_suffix_candidates_cover_skills_equipment_and_weapons(monkeypatch) -> None:
    source = SimpleNamespace(
        faction_id=601, filename="601-test.json",
        data={
            "filters": {
                "skills": [{"id": 1, "name": "Hacker"}],
                "equip": [{"id": 63, "name": "Repeater"}],
                "weapons": [{"id": 88, "name": "Adhesive Launcher Rifle"}],
            },
            "units": [{
                "id": 965, "name": "Example",
                "profileGroups": [{
                    "id": 1, "profiles": [],
                    "options": [
                        {"id": 1, "name": "Scout (Hacker)", "skills": []},
                        {"id": 2, "name": "Scout (Repeater)", "equip": []},
                        {"id": 3, "name": "Scout (Adhesive Launcher Rifle)",
                         "weapons": []},
                        {"id": 4, "name": "Scout (Repeater)", "equip": [{"id": 63}]},
                        {"id": 5, "name": "Scout (Hacker)", "skills": [{"id": 1}]},
                        {"id": 6, "name": "Scout (Unknown)"},
                    ],
                }],
            }],
        },
    )
    monkeypatch.setattr(audit, "load_sources", lambda _archive: ([source], None))
    report = audit.summarize(Path("ignored.zip"), unit_id=0, max_families=10)
    assert report["capabilitySuffixCandidatesCount"] == 3
    assert {
        (item["optionId"], item["catalog"], tuple(item["namedIdsAbsentFromLoadout"]))
        for item in report["capabilitySuffixCandidates"]
    } == {
        (1, "skills", ("1",)),
        (2, "equipment", ("63",)),
        (3, "weapons", ("88",)),
    }
    assert report["catalogSuffixCandidatesCount"] == 1
    assert report["catalogSuffixCandidates"][0]["namedEquipmentIdsAbsentFromLoadout"] == ["63"]
