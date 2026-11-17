# Agent improvement log

**Project domain:** Project infrastructure

Record actionable opportunities noticed during implementation, investigation,
validation, documentation review, or handoff. [TODO.md](TODO.md) tracks accepted
work. Recording a suggestion leaves the current task scope in place.

1. Check for an existing entry and update it if applicable. For a new entry,
   assign the next unused `AI-####` ID and keep the ID stable.
2. Record the affected files or instructions, the observation and available
   evidence, the proposed change, why it matters, and its disposition. Mark
   uncertainty explicitly and keep private evidence out of tracked files.
3. Use `proposed`, `deferred`, `accepted`, `implemented`, `declined`, or
   `superseded`. Update the disposition when it changes and link the relevant
   TODO item, commit, or decision. Retain earlier entries for reference.
4. Mention relevant new entries in the handoff. If the checkout is read-only,
   include the proposed entry in the handoff for a later authorized edit.

## Entries

Use one heading per entry with its ID and a short title. Include the date,
affected area, observation and evidence, proposed change, and disposition.

## AI-0001 — Normalize ITS scenario Skill facts

- **Date:** 2026-11-17
- **Area:** `data/curated/its/n5-its-season-18.json`, scenario/Skill read models.
- **Observation:** The 26 explicitly identified current ITS Short Skills retain
  source-reviewed requirements, actions, and caveats in mission-rule paragraphs.
  Standard Skill cards can render this prose and cited mission page ranges, but
  dedicated Requirements, Effects, Restrictions, and per-action source pins are
  not yet authored separately.
- **Proposed change:** During the next substantive ITS source-reconciliation
  pass, curate structured facts and action-level citations where the published
  pages support them. Reuse the existing Skill renderer without introducing
  a parallel mission-card format.
- **Why:** More scannable player reference cards and more precise provenance.
- **Disposition:** deferred (not necessary to expose the existing reviewed text
  as scenario-specific Skills).

## AI-0002 — Check Core scenario Skill publication parity

- **Date:** 2026-11-17
- **Area:** Core curated rules and `rules_n5.db` generation.
- **Observation:** Core N5 curated source contains `skill:hack-consoles` and
  `skill:pick-up-supply-boxes` with category `scenario-skill`, but the
  currently generated Rules database did not expose `hack-consoles` in the
  public Skill listing during focused validation.
- **Proposed change:** Compare the generated Rules database to the current
  curated source and determine whether source selection, publication status,
  or artifact freshness explains the missing entry before adjusting the build.
- **Why:** Core scenario Skills should receive the same catalogue treatment
  when published.
- **Disposition:** proposed; precise cause unverified.
