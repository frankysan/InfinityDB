---
name: infinity-army-data-pipeline
description: "Use when changing Army acquisition or snapshots, normalization, maintained data/configuration, database schemas or exports, provenance, deterministic builds, or generated-data audits."
---

# Infinity Army data pipeline

**Project domains:** Acquisition, Data processing

## When to use

- Change how Army or other supported upstream snapshots are acquired or identified.
- Add or revise normalization, curated data, maintained mappings, validation, schema/export logic,
  or a generated database contract.
- Diagnose source-to-database data loss, provenance, determinism, or rebuild problems.

For source meaning or rules conflicts, first establish the evidence with
[source reconciliation](../infinity-source-reconciliation/SKILL.md).

## Procedure

1. Read [architecture](../../../docs/architecture.md),
   [data model](../../../docs/data-model.md), [data lifecycle](../../../data/README.md), and
   [curated-data contracts](../../../data/curated/README.md). Identify the current stage and its
   owning project domain before changing code.
2. Pin the exact input set and determine whether acquisition is explicitly requested. Preserve
   raw upstream inputs; ordinary builds and tests must not acquire network data. Keep source
   identity, acquisition metadata, maintained policy, generated build state, and runtime artifacts
   distinct.
3. Trace the value from its source field or maintained record through merge/normalization,
   validation, export, and runtime consumption. Reuse existing resolvers, schemas, validators, and
   provenance fields. Put maintained aliases, mappings, exceptions, and review decisions in
   validated configuration or curated data rather than consumer-specific code.
4. Preserve ordering, source identities, unresolved values, and ambiguity. Never silently discard
   structure, turn missing values into zero, or infer a relationship solely from names, ID ranges,
   or presentation conventions.
5. If changing a schema, compatibility contract, or runtime artifact, identify all consumers,
   migration/rebuild guidance, and current documented values. Update the canonical owner and
   relevant user/operator guidance in the same change.
6. Add or extend tests at the changed boundary. Check exact source-to-output parity and failure
   cases, including stale/mismatched inputs where applicable. Persistent generated artifacts must
   remain deterministic across supported platforms for the same pinned inputs and toolchain.
7. Run the narrowest relevant stage of
   [the standard checks](../../../docs/testing.md), then broaden only when the changed contract
   requires it. Use `tools/run_checks.py --profile data` for the combined Army/rules data profile;
   do not claim an unavailable stage passed.
8. Summarize changed inputs/contracts, generated consequences, validation results, and any
   remaining unresolved data. Do not update pinned source artifacts or publish acquisition output
   unless explicitly required by the task.

## References

- [Architecture](../../../docs/architecture.md)
- [Data model](../../../docs/data-model.md)
- [Data lifecycle](../../../data/README.md)
- [Curated data contracts](../../../data/curated/README.md)
- [Development checks](../../../docs/testing.md)
