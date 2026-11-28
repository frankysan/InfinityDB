---
name: infinity-mcp-workspace
description: "Use connected mcp-lab workspace tools for InfinityDB development, validation, interactive browser investigation and source/artifact research."
---

# InfinityDB MCP workspace

**Project domain:** Project infrastructure

MCP is optional direct development access, not a separate source of truth or
a requirement for terminal-capable agents. The mcp-lab README,
BROWSER_AUTOMATION.md and SECURITY_RUNBOOK.md own tool contracts and limits.
Discover the actual client schemas; do not assume planned tools are available.

## Development and validation

- Discover repositories with `list_workspace`; inspect branch, HEAD, status
  and applicable instructions. Use scoped file reads, search and Git diffs.
- Use `apply_workspace_patch` with the inspected HEAD and optional file
  hashes for coherent changes. Review the actual diff; receipts are not
  acceptance evidence by themselves.
- Run non-test canonical checks through `run_checks` or
  `run_checks_workspace`. Use `start_test_job` or `start_script_job`
  for test-bearing workloads and poll terminal results. Recover existing
  jobs after disconnect rather than submitting duplicates.
- Use `start_database_build_job` for the integrated build and tracked
  project tools for specialized research and benchmarks. Review generated
  artifacts and provenance before staging.
- Use `list_workers`, explicit synchronization and expected-commit pinning
  for Linux validation. Keep worker and interactive checkouts distinct.
  Bounded worker file transfers target ignored local paths; use existing
  asset staging for large inputs.
- Follow [Git authorization](../../../AGENTS.md) for explicit staging,
  commits and fast-forward pushes; inspect terminal job results. Managed
  worktrees can isolate tasks without enabling mandatory coordination.
  Follow the [testing guide](../../../docs/testing.md) for validation.

## Interactive browser investigation

When the configured origin policy permits, use actual browser observations
for exploratory testing and visual iteration, not instead of tracked tests.

1. Open an isolated session at an approved HTTPS destination with a
   representative viewport. Query exact roles, labels or CSS selectors.
   Computed styles, geometry and hit observations help diagnose spacing,
   clipping, overlapping labels and layout differences.
2. Exercise clicks, checks (including supported ARIA controls), native
   selects, field input and dragging. Read field values and assert resulting
   state with waits. Batch known sequences; recover partial results and
   inspect state after failure before retrying mutations.
3. Resize to representative desktop/mobile widths. Exercise filters, history
   disclosures, reference navigation, faction themes and scenario maps.
   Capture viewport, region or bounded full-page PNGs. Retrieve saved inline
   previews and compare hash-verified captures at equal dimensions under
   controlled content, theme and viewport. Pixel differences locate changes;
   they do not determine correctness or accessibility.
4. Emulate print CSS and use guarded PDF capture for permitted pages.
   Read passive diagnostics when exposed for warning/error categories,
   failed requests and HTTP errors. Raw messages and URLs are omitted;
   absence of events does not prove health.
5. Record meaningful evidence (revision, page, state, viewport, results,
   capture IDs/hashes as appropriate), close sessions and translate stable
   regressions into focused tests.

The external browser currently accepts configured public HTTPS origins,
not arbitrary local development URLs. Do not bypass a denied origin or
print restriction. Use the local browser harness or authorized direct
terminal access for unreachable builds. See
[browser acceptance](../infinity-browser-acceptance/SKILL.md).

## Source and artifact research

- Browse ZIP members and read relevant text without extracting everything.
  Read selected PDF pages for text and permitted binary chunks for original
  images, PDFs or databases. Avoid transferring entire large files.
- Verify file identity with `verify_workspace_files` and SHA-256 when
  required for provenance. Hash equality is not semantic correctness.
  Use existing tracked analysis scripts for structured data comparisons.
- Render Markdown previews where useful and inspect the actual result.
  Preserve original sources, private evidence and artifact locations.
  Distinguish observed live behavior from authoritative source facts and
  curated interpretations. Do not publish captures or third-party assets
  implicitly.
- Follow [source reconciliation](../infinity-source-reconciliation/SKILL.md)
  and [Army data pipeline](../infinity-army-data-pipeline/SKILL.md).

## Capability gaps and feedback

The 2026-11-27 review identified managed local previews, general image/SVG/PDF
visual previews, read-only SQLite/JSON inspection, richer owned-app diagnostics,
additional native interactions and persistent experiments as opportunities,
not assumed available tools. Use existing project runners or direct access
as needed. Record concrete server limitations and improvements in mcp-lab's
roadmap, not InfinityDB's release backlog. Keep domain interpretation and
acceptance expectations in the consuming repository.

Distinguish source implementation, running gateway deployment, refreshed
client discovery and actual deployed execution. After a server update, verify
required tools in the current conversation; refresh/reconnect or hand off if
needed. Never infer acceptance from schema discovery alone.
