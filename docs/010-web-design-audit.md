# 0.10 web design conformance audit

**Project domain:** Web frontend

**Document status:** Current 0.10 design-refactor baseline. This document records the
source-level findings that should guide implementation against
`docs/web-design-guidelines.md`. Update the status and remaining findings as the refactor
progresses; transient screenshots, generated inventories, and manual-browser notes belong
under ignored `docs/audits/` rather than in this durable record.

## Scope and method

This audit compares the current browser implementation with the target design contract. It
is intentionally wider than the initial table-width issue: tables exposed the inconsistency,
but the same audit needs to establish whether shared surfaces, controls, responsive rules,
developer-only information, accessibility, typography, and theme preparation follow the
same reusable-structure philosophy.

The pass inspected the shared page shell; landing/About/Search; Unit Explorer and Unit
detail; Skills, Equipment, Weapons, Traits, States, and Hacking Programs list/detail
surfaces; Fireteams; Skill Modifiers; their browser render modules; `styles.css`; and the
frontend regression assertions in `tests/test_web.py`.

This is a structural/source audit, not a claim that every viewport and data combination has
been visually accepted. The implementation work should include a deliberate browser matrix
at desktop, compact, and narrow widths with Developer mode both off and on.

## Implementation progress

The first table-foundation pass has now implemented the shared parts needed by the catalog/list
family without redesigning its appearance:

- `.table-viewport` is the shared overflow owner around tabular content;
- Unit Explorer and all six rules catalog lists use one `data-table--listing` family with
  semantic primary, descriptor, metric, and technical column roles;
- generic first/last-column width rules and catalog-specific percentage overrides have been
  removed from that family;
- technical ID columns remain compact and can stay available in Developer mode on narrow
  screens, with insufficient width handled by the table viewport instead of an unconditional
  mobile hide;
- interactive row hover is explicit rather than applying to every table body; and
- catalog group-row spans derive from the active header shape instead of a page-name special
  case.

Surface containment and intrinsic content geometry are now separate shared primitives: `.surface`
owns the visual box while `.content-frame` owns bounded/intrinsic width, and the old overloaded
`.explorer` primitive no longer clips descendants or doubles as a surface. Static catalog, search,
and Fireteam containers and generated Unit/catalog detail cards now compose those roles explicitly;
legacy edge clipping is retained only through an explicit `.surface--clipped` variant where the old
container actually clipped content.

The reusable secondary-table pass now builds on the same vocabulary instead of adding another
parallel sizing layer:

- Skill/catalog usage tables reuse the listing-table family and its primary, descriptor, technical,
  and interactive-row behavior rather than maintaining a visually similar one-off layout;
- compact Hacking Program and Weapon profile tables use one profile-table family in which
  descriptive content receives flexible space and short comparison metrics remain compact;
- structured rules-reference, Skill Modifier, and Fireteam tables use a shared reference-table
  family while retaining their domain-specific width/responsive rules;
- Weapon stat/range tables now sit inside the common table viewport and generated comparison
  columns carry explicit semantic roles and table scopes/captions;
- Fireteam member/reference sizing no longer depends on `first-child`/`nth-child` selectors, and
  the narrow two-column Fireteam member transformation is limited to normal mode so Developer mode
  can preserve the wide reference table and scroll it instead; and
- Developer mode no longer expands an entire Fireteam card merely because technical member columns
  are visible.

The remaining work is intentionally broader: consolidate titlebars and controls, finish generated
table accessibility/responsive normalization outside the families already touched, rationalize
affected presentation tokens, and complete the manual browser matrix.

## Overall assessment

The frontend already has a good shared foundation. The persistent page shell, semantic font
roles, type scale, core color tokens, common catalog list renderer, state panels, buttons,
badges, rules-reference renderer, and compact-table density modifier all move in the target
direction. The strongest reuse is currently in JavaScript/data presentation: equivalent
catalog pages generally share renderers instead of reimplementing domain logic.

The principal mismatch is **ownership of visual behavior in CSS**. Shared concepts exist,
but several of them are mixed with page geometry or overridden positionally. As a result,
the cascade rather than the semantic structure often decides width, wrapping, overflow, and
responsive behavior. The immediate catalog-column issue is one symptom of that broader
problem.

The first refactor should therefore preserve the current visual language while making its
structures explicit. Do not begin by redesigning colors, typography, or individual pages.
First make common behavior reusable enough that later visual changes have one owner.

## What is already aligned

### Shared page structure

The application has a consistent page shell, main-content frame, top bar, intro region,
navigation, footer, skip links, and soft-navigation lifecycle. Catalog and detail routes
mostly compose these shared structures instead of creating isolated page shells.

That is the right architectural direction: route-specific content sits inside stable browser
infrastructure, and navigation/preferences remain shared state rather than page-local UI.

### Catalog rendering

Skills, Equipment, Weapons, Traits, States, and Hacking Programs already use the same
catalog-list module and nearly identical catalog structure. Loading, error, empty, filter,
result-count, table, and link behavior are therefore substantially deduplicated already.

This is an important success to preserve. Catalog differences should continue to be data and
semantic-column differences, not separate page implementations.

### Typography and density

The stylesheet defines semantic font-family roles and a rem-based type scale. Current tests
also enforce that component `font-size` declarations use the shared type tokens. This is
stronger than much of the remaining visual system and gives the refactor a useful model:
components consume named roles rather than choosing arbitrary local sizes.

`data-table--compact` is similarly well-shaped: it changes table density through shared
variables without defining a separate width policy. That matches the guideline's separation
of density from geometry.

### Accessibility foundations

The browser has global `:focus-visible` treatment, skip links, screen-reader-only text,
reduced-motion handling, labeled filters, live result status, and good table semantics on the
static catalog lists. Catalog tables use captions, column scopes, and row-header scopes;
Fireteam tables also explicitly provide captions and scopes.

These are foundations to keep while the component structure is simplified.

## Structural mismatches

### Surface and layout responsibilities were mixed

The baseline implementation made `.surface` and `.explorer` both draw the same box while
`.explorer` also owned intrinsic width and descendant clipping. That ambiguity is now removed:
`.surface` owns visual containment and `.content-frame` owns bounded/intrinsic geometry. The
former generic `.explorer` primitive has been retired, and overflow is no longer hidden as a
side effect of choosing that layout role. Existing edge containment is expressed explicitly through
`.surface--clipped` instead.

Static catalog/search/Fireteam containers and generated Unit/catalog detail cards explicitly
compose `surface` and `content-frame` when they need both roles. Domain-specific classes such
as `.fireteam-explorer` remain free to define meaningful page geometry without also redrawing
the common surface.

**Remaining:** several specialized containers still restate surface-like
border/background/shadow behavior, including landing links, rules-reference sections, profile
notation help, and Fireteam cards or summaries. Not every one must become the same component,
but each should be classified as a real surface variant or a genuinely different structure
rather than maintaining accidental parallel implementations.

### Header vocabulary has not yet converged in implementation

The stylesheet contains overlapping concepts such as `.section-heading`,
`.data-surface-header`, `.detail-section-title`, `.rules-card-header`, and
`.fireteam-card-header`. Some differences are meaningful, but their responsibilities are not
yet explicit enough to tell which one should be reused for a new surface.

**Target:** reduce these to a small hierarchy such as page/section heading, surface titlebar,
and detail subsection heading, with domain-specific additions layered on those roles. The
Hacking Program and Skills placement work should use those roles instead of creating a new
header treatment for each catalog.

### Shared controls are less reusable than their appearance suggests

Buttons and ordinary fields have useful shared primitives, but Settings switches are
implemented several times. Developer mode, optional-unit settings, and remember-settings
use nearly identical switch geometry and state styling in separate selectors; the distance
unit switch is a closely related variant with another copy of the same mechanism.

**Target:** establish one switch/control primitive with semantic modifiers where a real size
or labeling difference exists. Keep preference meaning in the owning setting, not in the
mechanics of drawing the switch.

### Visual tokens are only partially authoritative

The root stylesheet already contains semantic page/surface/text/action/border/focus tokens,
font roles, type scale, spacing primitives, radii, and several domain colors. That is the
right foundation for future themes.

The implementation still bypasses it frequently. A static count of the audited stylesheet
finds roughly 190 literal color occurrences outside `:root`, with many repeated values. Some
are legitimate domain-specific accents, but many are ordinary text, border, hover, surface,
or control-state colors that duplicate existing semantic roles or indicate missing ones.

**Target:** promote recurring semantic roles into tokens as components are touched. Do not
mechanically replace every literal with a variable; first decide what the color means. Theme
work should consume that semantic layer rather than adding dark-mode overrides around
hard-coded light-theme component values.

## Table audit

At the audit baseline, tables were the clearest divergence from the design contract and were
therefore selected as the first implementation workstream. The findings below remain useful as
rationale; the implementation-progress section above records which shared-listing issues have
already been addressed.

### Global positional sizing drives unrelated tables

The base stylesheet assigns widths to `thead th:first-child` and `thead th:last-child`.
Unit Explorer overrides those positions at wider viewports, and Equipment/Weapons/Traits
add another percentage override for the first catalog column. Narrow-screen rules then
change the same first/last positions again.

These rules mean "first column" and "last column" are being used as proxies for primary and
technical/metric roles. That assumption is already false across the application: Skills adds
a descriptor column, States and Hacking Programs have only identity plus ID, usage tables
have Unit/Armies/ID, weapon tables are stat matrices, and Fireteam tables have entirely
different semantics.

**Target:** remove global positional geometry. Mark semantic column roles and let each table
family choose a deliberate width policy. The catalog primary/title column should be the main
flexible column; descriptor, metric, and technical columns should remain compact.

### Developer columns currently change core geometry

Developer-only table cells are normally removed with `display: none`. With `table-layout:
auto`, enabling them causes the browser to recalculate the remaining columns. This is the
main structural reason catalog columns can jump when Developer mode changes.

There are additional divergent cases:

- at `max-width: 600px`, `.id-column` is hidden unconditionally, so IDs cannot become visible
  there even when Developer mode is enabled;
- Fireteam cards expand from a bounded width to `width: 100%` in Developer mode;
- Fireteam member tables increase their minimum width in Developer mode, but their narrow
  layout still allocates fixed percentages only to the first two columns while additional
  developer columns can be present.

**Target:** Developer mode is additive. Core columns keep their semantic geometry; technical
columns append compact information. If the result no longer fits, the table viewport should
scroll or technical metadata should move to a deliberate secondary presentation.

### The table viewport exists in markup but not as a shared CSS contract

Many pages correctly wrap tables in `.table-container`, but there is no general
`.table-container` rule defining width or overflow ownership. Individual table families,
notably Fireteams, implement horizontal scrolling themselves. At the same time `.explorer`
uses `overflow: hidden`.

This leaves overflow behavior dependent on the surrounding page rather than the table
structure itself.

**Target:** promote the existing container into the documented **table viewport** primitive.
It should own horizontal overflow and allow tables to preserve useful geometry. Specialized
table families may choose responsive transformation, but clipping should never be an
accidental consequence of the enclosing surface.

### Current table families need explicit policies

The audit identifies these recurring families:

- **Catalog lists** — Skills, Equipment, Weapons, Traits, States, Hacking Programs. Shared
  family; primary column flexible, descriptors/metrics/technical columns compact.
- **Unit Explorer** — similar browsing table but with Army availability presentation and an
  optional extended-results structure. It should share column-role primitives without being
  forced into the exact catalog-list geometry.
- **Usage tables** — Unit / Armies / ID tables on Skill and other catalog details. These are
  already visually compact and should converge on one shared semantic implementation.
- **Unit profile/loadout tables** — dense profile data with deliberate narrow-screen
  transformations. These are specialized responsive tables, not generic catalog tables.
- **Weapon profile/range tables** — compact stat and range matrices. Their comparison
  semantics justify specialized alignment/width rules.
- **Hacking Program profile tables** — compact profile matrices that should reuse the same
  stat-table semantics where applicable.
- **Fireteam member/reference tables** — information-dense reference tables where horizontal
  scrolling is preferable to compressing meaningful columns beyond usefulness.
- **Skill Modifiers** — a data-review table whose three descriptive columns should have an
  explicit policy rather than inheriting generic first/last widths.

The implementation does not need one universal table class. It needs a small set of shared
roles plus explicit family modifiers.

### Group-row behavior is coupled to current column counts

The shared catalog renderer hard-codes group-row `colSpan` from the current page (`4` for
Skills, `3` for Weapons). That works today but treats the active column set as an incidental
page fact.

**Target:** derive or declare the active semantic columns once, then use that definition for
headers, rows, group-row span, and developer-column behavior.

### Global row hover implies interaction where none may exist

`tbody tr:hover` applies a hover background to every table row. Many rows contain links, but
stat matrices, rule/reference tables, and other non-row-action tables receive the same visual
affordance.

**Target:** make row hover an explicit interactive-row/table-family behavior rather than a
global table default.

## Responsive design audit

The current implementation contains several good content-priority decisions. Unit profile
and loadout data deliberately transform at narrow widths, and weapon profile/stat structures
have page-specific narrow representations rather than simply shrinking every cell. Fireteam
reference/member tables already recognize that dense tables need special handling.

The problem is consistency and ownership:

- responsive behavior is distributed across fourteen media-query blocks in one stylesheet,
  including repeated `max-width: 600px` and `max-width: 400px` blocks;
- several narrow layouts depend on positional column selectors and fixed percentages;
- `overflow-wrap: anywhere` is used on ordinary profile/table content as an emergency fit
  mechanism;
- some tables switch from scrollable desktop behavior to squeezed fixed-layout mobile
  behavior even when the semantic comparison structure would benefit from preserved widths.

**Target:** keep the existing useful specialized transformations, but move breakpoint
behavior into the component/family that owns it. Resolve width pressure in the order defined
by the guideline: remove wasted space, preserve compact columns, allow sensible prose wraps,
scroll when comparison geometry matters, and only then use an intentionally designed stacked
representation.

## Developer-mode audit

The root `data-developer-mode` attribute and shared `.developer-only` convention are good
system-level primitives. Developer information is also generally visually subordinate.

The remaining debt is presentation rather than state management. Technical cells and text do
not yet have one layout contract, and some page-specific rules let Developer mode change the
width of the surrounding component rather than simply reveal more information.

**Target:** define shared technical-column/technical-metadata treatment and test Developer
mode as a layout state on every reusable family. The normal player-facing geometry remains
the reference; Developer mode may make a viewport scroll, but should not silently redefine
ordinary column widths or hide a technical field only because the viewport is narrow.

## Accessibility and semantic-markup audit

Static catalog and Fireteam tables provide a good semantic baseline. Dynamic table creation
is less consistent:

- the generic Unit table helper creates column-header `<th>` elements without explicit
  `scope="col"` and does not provide a caption contract;
- Hacking Program profile headers are generated without `scope` or a table caption;
- weapon stat/range tables are generated without captions and without explicit column scope;
- Skill structured/reference tables correctly set column scope, showing that this can be
  handled by a shared builder rather than per-call markup.

A visible section heading can provide context for sighted users, but equivalent generated
tables should expose equivalent semantics to assistive technology.

**Target:** shared table constructors/family helpers should own caption strategy, header
scope, row-header scope where applicable, and responsive labels. Accessibility semantics
should be harder to omit than to include.

## CSS and regression-test architecture

`styles.css` is currently 4,723 lines. A large single stylesheet is not itself a defect, but
its current shape reflects accretion: shared primitives, page geometry, responsive overrides,
and newer feature-specific blocks are interleaved. This makes it difficult to see which rule
owns a reusable concept and encourages adding a later override rather than simplifying the
earlier rule.

Frontend tests compound that issue in a few places by asserting exact implementation details
such as `th:first-child`, fixed percentages, Fireteam minimum widths, and specific selector
forms. Those tests protected real regressions when introduced, but some now pin the very
implementation that the design contract says should be replaced.

**Target:** during refactors, retain behavioral regression coverage but move assertions toward
semantic invariants: the presence of shared role classes, correct Developer-mode visibility,
accessible table structure, intended width/overflow family, and deliberate responsive mode.
Do not keep positional CSS solely because a test names its current selector.

The stylesheet may remain one file initially. Reorganize ownership before deciding whether a
physical split is useful; splitting duplicated rules into several files would not improve the
design system.

## Recommended implementation order

1. **Clarify primitives without redesigning the appearance.** Separate visual surface
   containment from layout geometry; establish a real table-viewport primitive; define
   semantic table/column roles; and add an explicit interactive-row role.
2. **Converge the catalog/list family.** Apply the shared roles to Unit Explorer and all
   catalog lists, remove first/last-child width rules, make primary columns use available
   space intelligently, and make Developer mode geometry stable. This directly addresses the
   original title-wrapping/column-jump problems.
3. **Converge reusable secondary table families.** Unify catalog usage tables, then normalize
   Hacking Program/weapon stat tables and Fireteam table viewport behavior without erasing
   their genuine semantic differences.
4. **Consolidate surfaces, titlebars, and controls.** Remove `explorer`/`surface` ownership
   overlap, promote recurring header roles, and replace duplicated settings switches with a
   shared primitive.
5. **Normalize responsive and accessibility contracts.** Remove emergency wrapping where a
   better width/overflow policy exists; ensure generated tables get consistent captions,
   scopes, labels, focus behavior, and narrow-screen semantics.
6. **Improve token/theme readiness as components are consolidated.** Replace recurring
   hard-coded presentation colors with semantic roles and leave first-class Light/Dark theme
   implementation for its existing dedicated workstream.
7. **Finish with a browser acceptance matrix.** Exercise representative pages at desktop,
   compact, and narrow widths, normal and Developer modes, with long names, dense badges,
   empty states, and the widest table families. Record intentional exceptions rather than
   reintroducing local fixes.

## Refactor constraints

The design-system pass should not become a browser-framework rewrite. The current lightweight
HTML/CSS/JavaScript architecture is compatible with the target design contract.

Implementation should also preserve domain-specific differences. A weapon range matrix is not
a catalog list, and a Unit loadout table is not a Fireteam chart. Reuse the common structural
roles—surface, viewport, column semantics, density, technical metadata, responsive strategy—
without forcing semantically different data into identical geometry.

The success criterion is not fewer CSS lines by itself. It is fewer independent decisions:
one shared place to change a recurring behavior, predictable geometry across equivalent
surfaces, and page-specific rules only where the information genuinely requires them.
