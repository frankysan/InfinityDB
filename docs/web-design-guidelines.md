# Web design guidelines

**Project domain:** Web frontend

This document defines InfinityDB's target browser design contract. It is intentionally aspirational: it describes what the interface should converge toward, not every detail of the current implementation.

The visual layer should follow the same engineering philosophy as the rest of the project: define reusable structures, keep responsibilities explicit, simplify repeated behavior, and remove duplication rather than accumulating page-specific exceptions. When current UI behavior conflicts with this document, treat the mismatch as implementation debt to resolve deliberately rather than copying the inconsistency into new work.

`docs/architecture.md` remains authoritative for subsystem boundaries and frontend/backend responsibility. This document owns the reusable visual and interaction vocabulary and the intended behavior of shared browser structures. `src/infinity_db/web/static/styles.css` implements that contract; it is not the specification itself.

## Design principles

### Prefer reusable structures over page-local styling

Recurring UI behavior should be represented by shared primitives with explicit semantics. A new page should normally compose existing structures before adding new ones. When two pages solve the same presentation problem differently, first determine whether the difference is meaningful; otherwise consolidate them.

Page-specific CSS and markup remain appropriate for genuinely unique content, but they should not redefine common concepts such as surfaces, table geometry, badges, headers, controls, spacing, responsive behavior, or developer-only presentation.

### Give visual rules semantic meaning

Style according to what an element is and what role it serves, not merely where it happens to appear. Prefer concepts such as primary column, metric column, technical metadata, surface header, and status badge over positional rules such as first child, third column, or last row.

A semantic role should behave consistently when surrounding content changes. Adding, hiding, or reordering unrelated elements should not accidentally change its visual treatment.

### Simplify before adding exceptions

When a layout problem appears, first look for unnecessary width, spacing, wrappers, overrides, or duplicated rules. Prefer removing conflicting behavior or strengthening a shared primitive over adding another narrowly targeted selector.

An exception should exist because the information has different requirements, not because the current cascade makes the common structure inconvenient to reuse.

### Optimize for lookup, comparison, and scanning

InfinityDB is a dense reference application. The interface should make names, values, relationships, and differences easy to scan without feeling cramped. Decorative complexity must not compete with data hierarchy.

Use whitespace to separate meaningful groups, not to distribute empty space evenly. Dense information may be compact, but compactness must not force premature wrapping, unstable columns, or ambiguous grouping.

### Preserve predictable geometry

Equivalent structures should occupy equivalent visual roles across pages. Normal interaction such as enabling developer mode, changing filters, expanding optional information, or moving between similar catalog pages should not cause unrelated columns or controls to jump unpredictably when that can be avoided.

Stable geometry is especially important for side-by-side comparison and repeated navigation through catalogs.

### Use progressive disclosure for secondary information

Player-facing information should dominate the normal view. Provenance, internal identifiers, source diagnostics, and developer metadata should remain available without distorting the ordinary layout.

Developer mode should add technical depth rather than redefine the primary presentation.

### Make responsiveness a content-priority decision

Responsive design is not simply shrinking desktop geometry. At narrower widths, preserve the most important information and relationships first, then deliberately choose whether secondary content should wrap, scroll, collapse, or transform.

Breakpoints should correspond to layout failure or content need rather than arbitrary device categories.

### Treat accessibility as part of the component contract

Reusable structures must remain usable with keyboard navigation, visible focus, screen readers, user font scaling, reduced motion where relevant, and non-color-only meaning. A component is not complete if its intended interaction depends on a mouse, a specific viewport width, or a specific color perception.

### Keep theme and layout concerns separate

Themes define semantic color and appearance roles. Layout primitives define structure, spacing, sizing, and interaction behavior. Components should consume both without baking a particular theme into geometry or duplicating layout for individual theme variants.

### Maintain measurable contrast and non-color meaning

Normal and compact text roles must maintain at least 4.5:1 contrast against the surfaces they own in every shipped theme. Meaningful focus indicators and other graphical cues that communicate state or structure must maintain at least 3:1 against the adjacent audited surface. Disabled controls and purely decorative separators are not treated as normal readable content.

Status, range, rules-category, and similar semantic colors must retain readable text or another explicit label/value so meaning never depends on hue alone. Faction colors are supplementary identity accents: Unit/Army names and symbols remain the identity source, so faction gradients may stay visually subtle instead of being forced into text-contrast roles. The executable palette audit lives in `tests/test_theme_contrast.py`; new theme tokens that carry readable or state-bearing content should be added to that contract.

## Design vocabulary

Use these terms when discussing, documenting, or implementing the browser UI.

### Page and surface vocabulary

- **Page shell** — the persistent shared navigation, header, footer, and page frame surrounding route-specific content.
- **Main content** — the route-specific content area inside the page shell.
- **Surface** — a visually grouped container for related content. A card is a kind of surface, but `surface` is the general design term. A surface owns visual containment, not page width or overflow policy.
- **Content frame** — a layout role for a bounded or intrinsic block of structured content. It may be combined with a surface, but owns geometry only: it does not draw the box or clip descendants.
- **Clipped surface** — an explicit surface variant used when edge-to-edge child backgrounds must stay inside the surface boundary. Clipping is opt-in and must not substitute for a table viewport or responsive overflow policy.
- **Section heading** — the heading row that introduces a major page section or catalog region. It may carry a compact index/count beside the heading, but it is not owned by a nested record surface.
- **Surface titlebar** — the heading area owned by a surface. Record-wide classification, actions, and compact metadata may live here when they describe the whole surface rather than one row.
- **Detail heading** — a heading inside the detail flow that introduces a subsection or group without creating a new surface titlebar.
- **Detail group** — a reusable grouping of related fields or subsections within a detail page.
- **Catalog surface** — the complete reusable structure for browsing one catalog: title/context, controls or filters, result state, and catalog table/list.
- **Control bar** — a grouped row or responsive cluster of filters, search, sorting, display options, or actions associated with a surface.
- **Settings group** — a labeled collection of related persistent/session preferences.
- **Setting row** — one preference row pairing its label/context with the control that changes it.
- **Switch** — the shared binary-control primitive used when a setting represents an immediate on/off choice. Visual size variants are acceptable only when the interaction context genuinely differs.
- **Badge** — a compact labeled semantic value, category, state, or role. A badge is treated as one visual token and should not break internally.
- **Metadata** — secondary descriptive information that supports the main content without becoming its primary identity.
- **Technical metadata** — internal identifiers, diagnostics, provenance, or implementation-facing information intended primarily for developer mode.

### Table vocabulary

- **Table viewport** — the container immediately around a table. It owns clipping or horizontal scrolling behavior.
- **Table** — the semantic tabular structure itself.
- **Table header / header row** — the table's heading region.
- **Column header** — one heading cell describing a column.
- **Data row** — a normal record or value row.
- **Group row** — a row that labels or separates a group of following rows rather than representing a normal record.
- **Primary column** — the identifying column for the row, such as Unit, Skill, Equipment, Weapon, State, or Hacking Program name.
- **Descriptor column** — textual or tokenized metadata that classifies or describes the primary record, such as Skill Type.
- **Metric column** — short values intended for quick comparison, such as Uses, AVA, Points, MOD, Burst, or similar concise values.
- **Technical column** — developer-facing identifiers or diagnostics.
- **Core columns** — the columns that define the normal player-facing table.
- **Developer columns** — technical columns shown only in developer mode.
- **Compact table** — a table using reduced visual density. Compactness is a spacing/type treatment, not a column-width policy.
- **Intrinsic table** — a table whose useful width is primarily determined by its content and does not expand merely to fill its container.
- **Full-width table** — a table intentionally designed to occupy the available surface width.
- **Scrollable table** — a table that preserves useful column geometry and delegates insufficient horizontal space to its table viewport.
- **Responsive/stacked table** — a table with an intentionally designed narrow-screen representation that changes its visual structure while preserving the underlying information hierarchy.

## Reusable structure rules

### Shared primitives own recurring behavior

When a behavior appears on multiple pages, prefer one shared primitive or modifier over multiple page selectors. Shared structures should own their normal spacing, typography, alignment, responsive behavior, focus treatment, and common states.

Modifiers should express meaningful variants such as compact density, highlighted surface, or technical metadata. Avoid modifiers whose only purpose is to patch one page's incidental geometry.

### Composition should remain shallow and understandable

Prefer composing a small number of explicit primitives over deep layers of wrappers and overrides. A maintainer should be able to identify which structure owns a visual rule without reconstructing a long selector chain.

The cascade should reinforce the component model rather than act as a hidden dependency graph.

### Page-specific rules should be narrow

A page-specific rule should normally describe content unique to that page. It should not redefine the baseline behavior of common surfaces, tables, controls, badges, or detail groups.

If several page-specific rules converge on the same behavior, replace them with a shared abstraction.

## Surface and information hierarchy

Surfaces should group information that belongs together and establish a clear reading order. Nesting is acceptable when it communicates real hierarchy, but repeated borders, backgrounds, or padding should not create unnecessary visual boxes.

Visual containment and layout geometry must remain separate responsibilities. A surface decides how a grouped region is drawn; a content frame or owning page/component decides whether that region is intrinsic, bounded, full-width, or otherwise constrained. Neither role should silently own unrelated overflow behavior. When visual edge containment genuinely requires clipping, use an explicit clipped-surface variant; data overflow still belongs to the structure that owns the data, such as a table viewport.

Section headings, surface titlebars, and detail headings have distinct ownership. A section heading introduces the surrounding page region; a surface titlebar belongs to one contained record/card; a detail heading introduces a subsection within the detail flow. Do not create page-specific heading classes merely because the same role appears in a different domain.

Surface titlebars should contain information that applies to the whole surface. For example, a record-wide type/classification belongs naturally with the record title when it does not vary by row. Row-specific values belong in the table or detail structure that owns those rows.

Equivalent catalog/detail pages should place equivalent concepts consistently. A user moving from Skills to Hacking Programs or Equipment should not have to relearn where identity, classification, related rules, usage, or technical metadata appear unless the data genuinely differs.

## Table design contract

Tables are a primary interaction surface in InfinityDB. Their behavior must be intentional and stable rather than an emergent result of browser auto-layout plus unrelated CSS overrides.

### Every table has an explicit width policy

Each table family should deliberately choose one of these behaviors:

- **Intrinsic** when the useful content is narrow and expanding it would create empty space.
- **Full-width/bounded** when distributing content across the available surface improves scanning or comparison.
- **Scrollable** when meaningful column widths should be preserved beyond the available viewport.
- **Responsive/stacked** only when a deliberately designed alternate representation is clearer than horizontal scrolling.

`width: 100%` should not be an accidental default for every table, and a table should not become wide merely because its parent surface is wide.

### Column behavior is semantic, not positional

Column sizing, wrapping, alignment, and visibility should follow column roles. Do not depend on `first-child`, `last-child`, or fragile `nth-child()` rules when the intended behavior means primary, metric, descriptor, or technical column.

Adding a developer column, optional column, or future field should not silently change how the existing semantic columns are styled.

### The primary column gets first claim on useful space

The primary column carries row identity and should remain easy to scan. It should receive flexible horizontal space before short supporting columns do.

Names should normally stay on one line when the viewport has enough room. They may wrap at ordinary word boundaries when space genuinely runs out, but should not be forced into early line breaks while neighbouring short columns retain large amounts of unused whitespace.

Avoid arbitrarily low global maximum widths for primary/title columns. If a table family needs a bound, define it from that family's actual comparison/readability requirements rather than inheriting an unrelated limit.

### Short columns stay short

Metrics, IDs, short flags, and similarly concise fields should size near their useful content. They should not receive large percentages of table width merely to fill the row.

Metric and identifier values normally use `nowrap`. Numeric comparison columns should use consistent alignment and tabular numerals where appropriate.

### Descriptor columns have an explicit wrapping policy

Descriptor text may wrap when it contains natural prose or several independent tokens. Individual badges/tokens should not break internally. When a descriptor represents a record-wide classification rather than row-specific data, prefer moving it to the surface header/titlebar instead of reserving a sparse table column.

Collections of compact symbols or badges are not ordinary content-sized descriptors. When a column presents a potentially large availability or membership set, give that collection a reusable bounded column role with enough horizontal space to wrap into rows; do not let intrinsic sizing collapse it to one token per line. Equivalent collections should use the same geometry everywhere they appear.

### Developer mode is additive

Enabling developer mode should expose technical information without needlessly changing the geometry of the core table.

Developer columns should normally appear after core columns and remain compact. When adding them makes the table too wide, prefer expanding/scrolling the table viewport rather than compressing ordinary columns into a different layout. Player-facing column order, labels, and semantic meaning must remain unchanged.

### Density and geometry are independent

Compact tables may reduce padding or type size, but compact density must not implicitly change the table's width policy, column roles, or responsive strategy.

Do not use a density modifier as a substitute for defining proper column behavior.

### The table viewport owns overflow

Cells should not individually solve insufficient horizontal space through arbitrary clipping or emergency wrapping. The table viewport decides whether the table may overflow horizontally, and the table's responsive policy decides whether a structural transformation is warranted.

Long unbreakable source strings may use defensive overflow handling, but `overflow-wrap: anywhere` should not be a general solution for ordinary names or labels.

### Group rows span the active table

Group rows should visually and semantically span the active set of columns. Their behavior must remain correct when optional or developer columns are shown or hidden.

A group row labels a group; it should not inherit metric or technical column alignment merely because of its position in the table.

### Alignment follows data type

As a default:

- names and descriptive text align left;
- comparable numeric values align consistently, usually right or centered depending on the table's scan pattern;
- internal identifiers align consistently and use the technical/monospace treatment;
- badges and short categorical values use the alignment that best preserves row scanning without creating excessive whitespace.

Alignment should be consistent within a table family and across equivalent catalog tables.

### Empty values must preserve structure

Empty, unavailable, and not-applicable values should use one consistent representation appropriate to the domain. Their presence must not cause columns to collapse, shift, or adopt a different visual role from populated rows.

Do not insert decorative placeholders solely to force geometry that the table structure should own directly.

## Catalog table conventions

Catalog list pages should converge on one shared family of structures rather than carrying independent table layouts for Skills, Equipment, Weapons, Traits, States, Hacking Programs, and future catalogs.

For a normal catalog table:

- the primary identity column comes first;
- descriptors/classification follow only when they vary meaningfully by row;
- concise metrics follow descriptors;
- technical/developer columns come last;
- the title column remains the main flexible column;
- short columns remain content-sized;
- developer mode should not make the core columns jump or reorder;
- equivalent controls, result counts, empty states, and table headers should use shared structures.

Differences between catalog domains should come from the data they present, not from unrelated CSS geometry.

## Responsive behavior

When horizontal space decreases, resolve pressure in a deliberate order:

1. Remove unnecessary margins, gaps, or empty expansion.
2. Let flexible columns consume the space released by intrinsically sized short columns.
3. Allow descriptive prose to wrap at sensible boundaries.
4. Preserve semantic tokens and concise metrics without internal wrapping.
5. Use horizontal table scrolling when preserving the comparison structure is more useful than squeezing it.
6. Transform to a stacked/responsive representation only when that representation has been explicitly designed for the table family.

Do not start by shrinking every column equally. A narrow viewport should not make the least important whitespace more stable than the primary data.

Responsive transformations must preserve reading order, labels, relationships, keyboard access, and screen-reader meaning. If a table ceases to behave like a visual table on narrow screens, its accessible semantics must still communicate each value's label and record association.

## Controls and interaction

Controls that perform equivalent actions should use equivalent visual structures, labels, spacing, and states across pages. Search, filtering, sorting, settings, expand/collapse behavior, and mode switches should not each invent new control geometry.

Settings should compose shared setting rows and switch controls rather than styling each preference independently. Preference-specific classes or IDs should own behavior/state only; they should not redraw the same switch. A labeled choice such as `cm / in` may specialize the shared switch through a semantic size/context modifier, but the switch mechanism remains one primitive.

Control groups should remain visually associated with the surface they affect. A control should not appear to apply globally when it only changes one catalog or detail group. Related persistent/session preferences may be grouped under a settings-group label; standalone settings should keep the same row alignment and control treatment.

Interactive state changes should preserve surrounding geometry where practical. Loading, empty, error, and disabled states should not cause avoidable layout shifts or remove context needed to understand what changed.

## Developer-mode presentation

Developer mode exists to expose additional implementation and provenance information while retaining the player-facing view as the reference geometry.

Technical information should therefore:

- use shared technical typography/metadata treatment;
- remain visually subordinate to player-facing identity and rules data;
- appear in predictable locations;
- avoid changing ordinary labels or reinterpreting existing fields;
- avoid forcing core data to wrap merely because an identifier was added;
- use shared developer-only structures rather than page-specific diagnostics markup.

Where technical detail cannot fit without harming the normal layout, prefer a dedicated metadata area, expandable section, or scrollable table viewport rather than compressing the core presentation.

## Typography and tokens

Typography, spacing, radii, border treatment, focus styling, color roles, shadows, and component density should come from shared design tokens or primitives. Literal visual values should be introduced only when they represent a deliberate new shared role or an unavoidable unique asset constraint.

Theme-facing tokens describe **meaning**, not a particular hue or page. Prefer roles such as default/subtle/data surfaces, primary/secondary/technical text, normal/strong/subtle borders, actions, focus, controls, status, and data emphasis. Components consume those roles; they should not copy a light-theme color merely because it currently looks correct. A component-local custom property may adapt a shared role for geometry or state, but its visual value should come from the semantic theme layer.

When the same literal presentation color recurs, treat that as a signal to identify the shared role rather than repeat the value. Unique literals may remain for genuinely local presentation while their meaning is still unique; if the role recurs, promote it. Domain-identity colors such as faction or rules-category accents remain explicit semantic data tokens rather than being folded into generic interface colors.

Each theme should therefore replace semantic token values, not duplicate component/layout rules. Light and Dark are the initial first-class themes, not an architectural limit: additional themes should plug into the same semantic token contract. Theme work may need theme-specific contrast-safe values for domain accents, but should preserve the component contract and non-color meaning.

Text hierarchy should communicate function: identity/title, section heading, normal content, compact/tabular content, metadata, and technical identifiers are different semantic roles. Pages should not invent new type sizes or weights merely to make one local element appear important.

## Exceptions and evolution

These guidelines define defaults, not a prohibition on specialized design. A deliberate exception is valid when the information has requirements that the shared structure cannot express cleanly.

When introducing an exception:

1. confirm that the need is semantic rather than incidental;
2. keep the exception as local as possible;
3. avoid weakening the shared primitive for unrelated pages;
4. document the reason when it is not obvious from the data structure; and
5. if the exception recurs, promote the common behavior into the shared vocabulary instead.

The design system should become simpler as it matures: fewer independent rules, clearer ownership, stronger reusable structures, and smaller page-specific deltas.

## Review checklist

Use this checklist when adding or materially changing a browser surface:

- Is this behavior already represented by a shared primitive or semantic role?
- If not, is the new structure reusable, or is it genuinely page-specific?
- Does the markup/CSS describe semantic roles rather than element positions?
- Are spacing and width used for information hierarchy rather than empty distribution?
- For tables, is the width policy explicit and are column roles defined?
- Do primary names avoid unnecessary line breaks while short columns remain compact?
- Does developer mode add information without destabilizing the core layout?
- Does the narrow-screen behavior preserve the important data and relationships?
- Are focus, keyboard, touch, screen-reader, scaling, and non-color meaning preserved?
- Would another page solving the same problem be expected to use the same structure?
- Can any new rule replace duplicated behavior instead of adding another exception?
