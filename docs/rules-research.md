# Rules research

This document holds verified rules findings that may become useful to InfinityDB
but do not yet have a confirmed processing, validation, query, presentation, or
data-model consumer.

It is deliberately not a speculation backlog. Every entry needs an authoritative
source and a concise statement of what is known. Once an application becomes
clear, promote the finding to `rules-semantics.md` and create normal TODO/code
work only if implementation is actually required.

## Entry contract

Record:

- a stable local finding ID;
- rules scope and canonical term(s);
- concise verified fact;
- wiki URL and reviewed version;
- PDF/FAQ/ITS citation when available;
- why the fact may matter later;
- what is still missing before it becomes implementation-relevant.

Keep unresolved interpretations explicitly unresolved. Do not use this file to
turn an inference into a source-native rule.

## Basic Rules / Unit Profile

### RR-BR-UP-001 — Troop Type carries specific rule restrictions

**Scope:** core N5.

The current Unit Profile wiki associates concrete restrictions with several
Troop Types: TAG and VH cannot go Prone or declare Cautious Movement, while REM
may not declare Cautious Movement or be chosen as Lieutenant.

This may eventually support contextual help, rule-aware filtering, or validation
of derived rule relationships. InfinityDB does not currently need these
restrictions to interpret the imported `type` field, so they remain research-only
until the Restrictions Chart and the affected rules are audited as a complete
set.

Source:

- Wiki: <https://infinitythewiki.com/Unit_Profile#Trooper_Characteristics>, live
  N5.3 page
- PDF cross-check: pending the Quick Reference / Restrictions Chart audit

### RR-BR-UP-002 — Game-term thesaurus can span domains without creating entities

**Scope:** project research derived from source-native terminology.

The Unit Profile page already exposes cross-domain terms such as Unit, Unit
Profile, Trooper, Attribute, Characteristic, Training, Troop Type, Trooper
Classification, ISC, Peripheral, and Controller. These terms can form the first
seed of a game-term thesaurus even when no dedicated database domain is warranted
for a term.

Before implementing a thesaurus, the Game States and Glossary audit should
establish the broader canonical vocabulary, aliases, relationships, and source
coverage so the project does not build a second competing glossary structure.

Sources:

- Wiki: <https://infinitythewiki.com/Unit_Profile>
- PDF: Infinity N5 V5.3, printed pages 8-9
