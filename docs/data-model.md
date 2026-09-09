# Data model notes

## Pipeline

```text
raw Army JSON
    -> lossless merged master.json
    -> normalized relational-style JSON
    -> database adapter (next stage)
```

## Identities

- `unit.id` is treated as the global unit identity.
- Unit `profileGroups` and unit-level `filters` are army-list-specific variants.
- Profile group, profile and loadout option IDs are local to their army/unit hierarchy and use composite keys in normalized data.
- Skills, weapons, equipment, ammunition, characteristics, troop types, categories and extras use stable global lookup IDs.
- Peripheral IDs are army-local.
- Referenced but undefined factions/units/categories are retained as explicit placeholder records rather than discarded.

## Principle

The merged master layer is lossless and source-oriented. The normalized layer is query-oriented. Database-specific choices should live in exporters/adapters rather than in source parsing.
