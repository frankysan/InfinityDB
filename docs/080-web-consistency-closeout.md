# 0.8.0 web consistency closeout audit

**Project domains:** Web backend, Web frontend

## Scope

This is a focused browser-consistency pass before the 0.8.0 release. It checks the
shared page shell and the player-facing routes changed or added during 0.8.x. It is
**not** the broader production-baselined end-to-end consistency audit planned for
0.10.0; that later audit still owns storage/API/render parity, production provenance,
degraded runtime contexts, and the full semantic matrix.

The inspected work archive is `InfinityDB-work-4efc063dfac5.zip`. The archive does not
contain `.git`, so the `4efc063dfac5` label is treated as the supplied base identity
rather than independently verified as a Git commit from inside the archive.

Routes reviewed:

- landing page and shared navigation/settings shell;
- Unit Explorer and Unit detail;
- Skills, Equipment, Weapons, Traits, States, and Hacking Programs list/detail pages;
- Fireteams;
- Skill Modifiers data-review page;
- About InfinityDB.

The pass checked shared-shell composition, navigation state, route classification,
page title/description metadata, settings disclosure, soft-navigation lifecycle,
Content Security Policy coverage, and the currency of public project-scope copy.

## Findings and corrections

### Shared shell and public wording

- **Fixed:** the About page still described 0.7 as current and listed Fireteams,
  Peripherals/Controllers, dependencies, and Reinforcement parentage as future work.
  It now describes the connected 0.8 surface and the accepted 0.9/0.10/1.0 roadmap.
- **Fixed:** the sidebar footer still labeled the whole application as `Unit catalog`.
  It now uses the broader `Player reference` label already used by the landing/About
  shell.
- **Fixed:** the persistent-settings disclosure named only distance, optional-unit,
  and Developer mode. It now also names the Fireteam Wildcard preference and correctly
  refers to browser cookies in the plural.
- **Fixed:** the maintained browser-preferences architecture text now includes the
  Fireteam Wildcard preference.

### Route and page classification

- **Fixed:** Skills, Equipment, Weapons, and Traits pages identified themselves as
  `Rules reference` in page content while the shared top bar classified them as
  `Reference data`. All player-facing rules catalog list/detail pages now use the
  same `Rules reference` shell classification. The Skill Modifiers page retains
  `Reference data` because it is explicitly a data-review surface rather than a
  normal player catalog.
- **Fixed:** Unit and Skill detail documents were the only browser pages without a
  meta description. Every current browser page now supplies one.
- **Confirmed:** the landing-page primary links and sidebar navigation contain the
  same eight player data/reference destinations in the same order; About remains a
  separate project-information destination rather than a ninth database card.

### Soft navigation

- **Fixed:** soft navigation previously compared navigation links by exact pathname,
  so moving from `/skills` to `/skills/<slug>` (and equivalent Unit/catalog detail
  routes) cleared the active sidebar state. Detail routes now inherit the matching
  parent navigation item.
- **Fixed:** soft navigation updated the document title but left the previous route's
  meta description in place. The description now follows the newly loaded document.
- **Fixed:** transient page modules could leave window-level event listeners active
  after their `<main>` was replaced. Repeated in-app navigation could therefore
  accumulate stale handlers. Catalog list/detail, Skill detail, Skill Modifiers,
  Unit detail, Fireteams, and Hacking Program detail now bind fetch lifetime and
  global listeners to the page lifecycle and abort/dispose them on
  `infinity:beforenavigation`.
- **Confirmed:** the Unit Explorer already had explicit request cancellation and
  popstate-listener cleanup, so it did not need the new transient-page controller.
  Shared navigation/preferences scripts remain intentionally persistent because their
  DOM is not replaced during soft navigation.

### Regression coverage

- **Fixed:** shared-shell and CSP route matrices lagged behind recently added pages.
  They now include Traits, States, Hacking Programs, and Fireteams where applicable.
- **Added:** tests pin navigation/landing destination parity, consistent `Rules reference`
  classification, meta-description presence, parent-route active navigation, description
  synchronization, and page lifecycle cleanup for transient modules.

## Remaining intentional differences

- `/skill-extras` remains an unlisted **Data review** page. Its purpose is to inspect
  distance-like Skill extras, so it is deliberately not promoted into the main player
  navigation or landing-page database cards in this pass.
- Fireteams retain their `Fireteam charts` top-bar tag and `Connected game structure`
  page framing because that surface is Army-scoped relationship/configuration data,
  not a rules catalog.
- The 0.10.0 end-to-end consistency audit remains open. This closeout pass does not
  claim production provenance verification, full API/render semantic parity, browser
  automation, degraded-production-context coverage, or the broader frontend
  responsibility/theme refactor assigned there.
