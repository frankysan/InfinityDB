# Rules explanation audit 1.0: source provenance

**Project domains:** Acquisition, Data processing

This is the documentation-only evidence manifest for the
[audit](rules-explanation-audit-1.0.md) and its
[N5.3 reconciliation](rules-explanation-audit-1.0-n5.3-reconciliation.md).
Original examination: `859823f8d2899405a40cf126883d2adf5763db7c`.
Follow-up examination: `c5400ab1b950990fdacc509be91c110fe85431fb`, 2026-10-09.
The two curated collections have unchanged hashes and still contain 367 records.

## Evidence classes and portability

- **Tracked:** C/H curated text, source declarations, review policy, validation
  catalogs, maintained documentation, and the existing generated runtime databases.
  These are project evidence; curated text is not itself an official ruling.
- **Local external requirement:** official PDFs, Army/Wiki ZIPs, and acquisition
  manifests under ignored `data/` directories. They were inspected where stated
  below, but a clean tracked checkout does not contain them.
- **URL-backed:** official publication notices and individual Wiki pages.
  Retrieval during this audit is distinguished from publication and revision time.
- **Unavailable:** an expected artifact/revision whose bytes were not verified.
  A matching declaration or manifest does not count as recovered bytes.
- **Newly inspected in follow-up:** additional content in already available
  artifacts, the Spanish Wiki capture discovered locally, and rendered PDF pages.
  This does not mean the agent downloaded or generated those source archives.

Local artifact paths below are **literal requirements, not relative Markdown
download links**. Portable repository links target tracked documentation or
curation only. New documentation is intended to be tracked; no official PDFs,
raw HTML, screenshots, ZIPs, or copied upstream data are added to Git.

**Reproduction rule:** obtain the exact artifact from the original operator's
archive, compare the expected SHA-256, then inspect the specified page/member.
For new acquisition, use the official resource portal or the project's documented
Army/Wiki acquisition workflow in [data ownership](../data/README.md).
Reacquiring a mutable publication today is not guaranteed to reproduce an old
capture. A mismatched hash must be reported; do not overwrite the expected hash
or quietly repoint a curated source. Source migration requires a fresh comparison.

## Artifact register

Publication/effective version, acquisition time, and PDF creation metadata are
different facts. Unknown dates remain unknown; filesystem timestamps are not
used as publication evidence. Original source IDs S1-S12 remain stable.

| ID | Official title / language / version | Publication or effective date | Acquisition separately | Expected local artifact / original URL or procedure | Inspection and supported findings |
| --- | --- | --- | --- | --- | --- |
| S1 | Infinity N5 Core Rules, English, v5.3; 196 file pages | C declares 2026-08-10; PDF creation metadata agrees. Official release notice S11 is 2026-09-01. Do not conflate them | Original download time not recorded | `data/pdf/rules/n5-rules-v5-3-en.pdf`; obtain the version-labeled English rules from [official resources](https://experience.corvusbelli.com/en/infinity/resources); exact direct download URL was not preserved | Original and follow-up clause inspection; follow-up visual pages 70, 74, 138, 180, 182, 185, 186, 195. Supports most mechanical findings, especially REA-001/002/034/037/038/039/040/043/044 |
| S2 | N5 FAQs, English, cover v0.1; 5 file pages, 4 printed content pages | Publication date unverified; creation metadata 2026-08-25 is not asserted as release date. S11 announces a new FAQ on 2026-09-01 | Original download time not recorded | `data/pdf/faq/n5-faqs-v0-1-en.pdf`; official resource portal, FAQ category, English v0.1 | All content read; comparison with S15. Supports REA-007/008/014/015/016/017/020/023/030/036; no universal Doctor/Engineer allegiance answer found |
| S3 | Infinity N5 Core Rules, English, v5.2; 194 file pages | PDF creation metadata 2025-10-15; version-associated official update date separately indexed in N5 source history | Original download time not recorded | `data/pdf/rules/n5-rules-v5-2-en.pdf`; preserved older official English publication | Original Kobra comparison expanded to selected clauses in the reconciliation. Historical evidence, not current authority |
| S4 | Infinity Wiki, English revision-history acquisition | No single publication date/version for the archive; each revision has its own timestamp | Manifest: 2026-09-28T16:57:27+02:00 | `data/wiki/WIKI-en-history 20260928-165727.zip`; acquisition origin `https://infinitythewiki.com/`; 3592 members; `_history/index.json` identifies each revision URL/member | Original exact revisions plus Doctor 3979, Engineer 3980 and Fireteams Chart 4116 checked in follow-up. Supports REA-010/027/028/035/038 and FTO coverage |
| S5 | Infinity Wiki, English capture | Capture is not an effective rules publication | Manifest: 2026-09-26T20:08:32+02:00 | `data/wiki/WIKI-en 20260926-200832.zip`; Wiki acquisition, 812 members | Hash/availability independently checked; not a replacement for S18 and not a substantive full-member review |
| S6 | Official Infinity Army API, English snapshot; 59 documents including metadata | Manifest reports source `dataChangedOn=2026-09-03`; not inferred to be every profile's publication date | 2026-09-29T11:43:35+02:00 | `data/raw/JSON 20260929-114335.zip`; acquisition origin `https://api.corvusbelli.com/army`; `metadata.json` plus 58 faction members | Exact selected weapon profiles and Army update context checked. Member versions: 36 files `7.26246.158`, 22 files `7.26246.159`. Supports REA-025/027/028/044; current presence is not proof of a historical addition |
| S7 | Wiki Inmunidad, Spanish, revision 3677 | Revision timestamp not verified in this audit | Original URL read 2026-10-09; exact time not logged. Follow-up bytes independently inspected within S14 | [official page](https://infinitythewiki.com/es/Inmunidad); exact member `es/Inmunidad` in S14 | Example 4 and IMPORTANT clauses corroborate Flash Pulse result; do not settle S8's profile conflict. REA-010/027 |
| S8 | Wiki Tabla de Armas, Spanish, revision 3987 | Revision timestamp not verified | Original URL read 2026-10-09; follow-up S14 member inspection | [official page](https://infinitythewiki.com/es/Tabla_de_Armas); member `es/Tabla_de_Armas` | Flash Pulse still has two PB rolls and lacks State: Stunned. Breaker Marksman equivalent is under FUSILES DE PRECISIÓN. REA-027/044 |
| S9 | Wiki Ingeniero, Spanish, revision 3823 | Revision timestamp not verified | Original URL read 2026-10-09; follow-up S14 bytes | [official page](https://infinitythewiki.com/es/Ingeniero); member `es/Ingeniero` | Contact/STR repair/other-State branches and absence of an explicit universal Allied clause inspected. REA-001/009/038 |
| S10 | Wiki Ataque Intuitivo, Spanish, revision 3882 | Revision timestamp unverified; original web response had N5.2 banner | Original URL read 2026-10-09; exact time not logged | [official page](https://infinitythewiki.com/es/Ataque_Intuitivo); original URL-backed evidence | WIP resolution example supports REA-003. Not newly certified as a Spanish PDF clause |
| S11 | ITS Season 18 + N5.3 Rules Update, English, official publication notice | 2026-09-01, displayed publication date | Original and follow-up URL reads 2026-10-09; exact times not logged | [official notice](https://infinityuniverse.com/en/news/infinity-rules-update-5-3); rules and Army list items identified by ordinal in the reconciliation | All 26 English rules bullets and 20 Army bullets inventoried. Notice cannot override a rule/PDF/profile. English Breaker weapon label needs reconciliation, REA-044 |
| S12 | English Wiki Engineer 3980 and Intuitive Attack 3877 | S4 index: 3980 at 2025-10-31T11:38:24Z; 3877 at 2025-10-29T10:12:44Z | Original/follow-up URL reads; S4 separately captured exact oldid content | [Engineer](https://infinitythewiki.com/Engineer), [Intuitive Attack](https://infinitythewiki.com/Intuitive_Attack); S4 `_history/oldid/3980.html`, `_history/oldid/3877.html` | Direct clause evidence for REA-001/003/038; current banner does not change revision authorship dates |
| S13 | ITS Temporada 18 + Actualización N5.3, Spanish, official notice | 2026-09-01, displayed date | Follow-up URL read 2026-10-09; exact time not logged | [official Spanish notice](https://infinityuniverse.com/es/news/infinity-rules-update-5-3) | 30 rules bullets: the 26 shared subjects plus four language-specific subjects absent from English. Not proof that the Spanish PDF was checked |
| S14 | Infinity Wiki Spanish local capture; 786 members | Individual page revisions; no single publication/effective date | Existing manifest: 2026-10-09T21:13:04+02:00 | `data/wiki/WIKI-es 20261009-211304.zip`; origin `https://infinitythewiki.com/es/` | Discovered locally and independently hash/member checked during follow-up; not acquired by this task. Selected payloads below. Supports REA-027/034/037/038/041/042/044 and language reconciliation |
| S15 | N5 FAQs, English, cover v0.0; 4 file pages / 3 printed content pages | Creation metadata 2025-10-15; exact publication date unverified | Original download time unknown | `data/pdf/faq/n5-faqs-v0-0-en.pdf`; preserved official FAQ publication | Entire content compared with S2: 28 earlier Q&A blocks; S2 has 37, including nine additions. Historical FAQ scope remains separate |
| S16 | ITS Season 18: Overheat, English, version 2026.09.01; 132 pages | Cover explicitly says last updated September 1, 2026 | Original acquisition time unknown | `data/pdf/its/Its-rules-season-18-en.pdf`; cover gives current digital owner [ITS rules](https://experience.corvusbelli.com/en/infinity/its-rules) | Selected pp. 26, 28-29 inspected: ordinary Spec-Ops prohibited, TEAM-OPS is a distinct optional Extra and does not permit the Spec-Ops Skill. Supports REA-040's scope clarification; not a complete ITS audit |
| S17 | Official Spanish N5.3 PDF requirement | Not verified | Not acquired | Filename/local path not authoritatively established; obtain Spanish v5.3 from official resource portal. Candidate `https://downloads.corvusbelli.com/infinity/rules/infinity-rules-n5-es-v5.3.pdf` returned HTTP 404 in follow-up | **Unavailable.** No expected hash invented. Blocks bilingual PDF closure for REA-027/034/037/041/042. A 404 proves the candidate endpoint failed, not that the publication does not exist |
| S18 | Curated source `wiki-en-20260918-130233`, English capture, declared 812 members | Not a rules publication date | Declared 2026-09-18T13:02:33+02:00 | Expected `data/wiki/WIKI-en 20260918-130233.zip`; origin Wiki acquisition. Exact original operator archive required | **Still unavailable.** Expected hash agrees between tracked C/H declarations and ignored acquisition manifest; no ZIP bytes recovered. 72 records / 74 citations depend on it, REA-029 |
| S19 | Wiki Doctor, English, revision 3979; Médico, Spanish, revision 3822 | English: S4 index 2025-10-31T11:38:00Z. Spanish revision timestamp unknown | Follow-up exact English bytes in S4 and Spanish bytes in S14 inspected; live URLs also read | [Doctor](https://infinitythewiki.com/Doctor), [Médico](https://infinitythewiki.com/es/M%C3%A9dico); `_history/oldid/3979.html` and `es/Medico` | Requirement/allegiance comparison, REA-002/038. Both distinguish older collapsed wording; no universal Allied target restriction located |

## Checksums and selected members

All values below are preserved from the original report where already present.
Available artifact bytes were independently rehashed during follow-up. S18 is
an **expected** hash only. S17 has no verified bytes/hash.

```text
S1  53921e91c2d3d62ad5f7125abcd4174b2cf937d45320233eed5b6d301b66af3f
S2  7bf26b7d039db7826ef5500b1a2159fe54855b4e632133cab416becee65b85aa
S3  643ab0b6d7c3e9e5ffbf668543723161f252367e7788af09ec008be19c17851b
S4  d49db0515420af297a7349201e8bb7750ecb422048d32bb494273ee1cea78a5d
S5  c0fe18c165473e3f273efd58aa7ecb0ea0d94ee274189de9361aad175b3de987
S6  f103a7afd02e68d845cc9ce38b1948f46914676bbc6a5e6b790d0a04148b6c75
S14 8e4d40f0ad60d9a42c276f90a07253d8bcdbb61ed7839506cf9f91b7c8270be4
S15 a04c5eb43e7acd7272c794a3e7d4bb5fe2595ec04463778eb73c741feef5d043
S16 9e16874924112e62d51acf78d622f5c0cf6196064cc36f003b515de9dc448baf
S18 aa407f1959fbaafce98058acf507640cc94bfc2690d4a7519a547caf1492f23a EXPECTED ONLY
S6 metadata.json bb46ff9c6039dde600108f6592be616cb7620d67240cd81c2e3587cad4fc8995
C bb17f2013a1b8bc32961689789e4afff6fcc30f1476248d5d53d4b96587ab9a5
H 8b5a90cd036e048603d20d647139232e9fe7e27e1e43223cc68741387cd3143b
S20 9e5514a7f481421ac5dd87d54998f1e3b0174ab6462ad864eeafe91065225d72 DERIVED DATABASE
```

The local acquisition manifests are ignored evidence requirements, not portable
repository links. Their exact archive/content hash fields are different. For S14
the manifest's content hash is
`24a0b3b374159e486fb6248cfb2032dab1c42c8e33f2e5961482c3830003ba05`;
the ZIP hash above is the verified artifact identity.

| Archive | Exact member | Revision / timestamp where verified | Payload SHA-256 |
| --- | --- | --- | --- |
| S4 | `_history/oldid/3643.html` | Immunity 3643 / 2025-04-28T09:04:03Z | `7014821db88a6725addd6e1c354952e5a2ac017a15a6d2ddb695a5de6333dfa8` |
| S4 | `_history/oldid/4083.html` | Weapon Chart 4083 / 2026-08-27T14:26:38Z | `b08f1eb349d4ed35055755fde6222f7461dbbf1a33a402cd8dc45c2cfbae7ba3` |
| S4 | `_history/oldid/3000.html` | Combined Ammunition 3000 / 2025-03-28T15:15:11Z | `1ad611ee7d66293387922c7755aa97dbab167cd44c8f1a76ee87518dc5bd7abd` |
| S4 | `_history/oldid/3156.html` | Vulnerability 3156 / 2025-04-08T10:35:35Z | `a92fddb42c092cb1cc67f64c613eafff01b64f7b3a0ed10e78c252bf23d3a2f7` |
| S4 | `_history/oldid/3979.html` | Doctor 3979 / 2025-10-31T11:38:00Z | `49efc2c27fef1f98604afc3f05ad59db676d15c8b08f926de0ef6dc80b1795c2` |
| S4 | `_history/oldid/3980.html` | Engineer 3980 / 2025-10-31T11:38:24Z | `1b865c651eacfb12e96d413d1d3048ca9e4b1696507b6d1cf9712401ddbf348e` |
| S4 | `_history/oldid/3877.html` | Intuitive Attack 3877 / 2025-10-29T10:12:44Z | `5682556645d5426dc6070229d78c7d50ef4ea62cb14f9b47458effc991d4bf07` |
| S4 | `_history/oldid/4116.html` | Fireteams Chart 4116 / 2026-09-04T13:53:17Z | `cec8215998f63085439c27487d35b8ef27d2d0b11560859e27b8aaab3cbb541a` |
| S14 | `es/Medico` | 3822 / timestamp unavailable | `333e201ea384c6de1466069cc9df2b2b8dbf63821865dbce4ed7063f3492cdf3` |
| S14 | `es/Ingeniero` | 3823 / timestamp unavailable | `fcb061fb360efd1fde552a56583a5e1ceb35313f950bd8f6d91f4574a810a8d2` |
| S14 | `es/Inmunidad` | 3677 / timestamp unavailable | `d2e4e2b07e1deb84983feb8a3481da99765591ec2e4da2d97f3d29557defdac8` |
| S14 | `es/Tabla_de_Armas` | 3987 / timestamp unavailable | `9410d3e948fb323dc04020a8ba329ada02ae0372c475324dfa9690692e88c5a5` |
| S14 | `es/Torreta_Artillada` | 3754 / timestamp unavailable | `d9319dc63273b92dd5e34474ba90eba1d385a100e35bfc7a09c193c12d5c5446` |
| S14 | `es/Bonos_de_Fireteam` | 3918 / timestamp unavailable | `db1b60ea63eb9740e22d0aee24eabc26a3462ebd8503bcf57fff90927d24ca76` |
| S14 | `es/Ejemplos_de_Fireteam` | 3443 / timestamp unavailable | `e3128e0df00a71bbe3db73c9aaf4046ea4ea19969ce10611bae70bc0c88321e7` |
| S14 | `es/Modificadores_(MOD)_Detallados` | 4012 / timestamp unavailable | `f5c6f7c60941d67a51ae77f05366285a6b464394a347c585e6060d168159b4c8` |
| S14 | `es/Sigilo` | 4004 / timestamp unavailable | `50dbfab5291c9ce556f68818160d1c39df4c19cc031dd958b8ee886d57823f34` |
| S14 | `es/Super-Salto` | 3964 / timestamp unavailable | `36ef1dac97b35e1e9ade92be99f397f321830857210aab165553c31cfbb76723` |
| S14 | `es/Visor_Multiespectral` | 4013 / timestamp unavailable | `ee8c52f2cae31c0a42cd7dd325f38c37dbe494464ee01d861ccfec5b33e3ea00` |

S4 `_history/index.json` also identifies Doctor 3979, Engineer 3980 and
Fireteams Chart 4116 (2026-09-04T13:53:17Z). Exact locator and timestamp checks
do not migrate URL-backed curated citations into an archive source. Historical
payload banners can reflect the surrounding newer website; use revision metadata.

## Army and runtime comparison scope

S6's `101-panoceania.json` has version `7.26246.158`; `1001-o-12.json` has
`7.26246.159`. Other representative members for the reconciliation are
`103-military-orders.json`, `201-yu-jing.json`, `301-ariadna.json`,
`401-haqqislam.json`, `501-nomads.json`, `601-combined-army.json`,
`602-morat.json`, `603-shasvastii.json`, `605-next-wave.json`, `701-aleph.json`,
`801-tohaa.json`, `901-non-aligned-armies.json`, and `902-druze.json`.
The appendix records event-specific Unit/source IDs. The archive has no verified
pre-September-1 Army comparison: all available September snapshots postdate the notice.

The reconciliation additionally inspects `1101-jsa.json` (`7.26246.159`) and,
for source Unit 1874, `1003-torchlight-brigade.json` (`7.26246.159`),
`107-kestrel-colonial-force.json`, `204-invincible-army.json` and
`304-usariadna.json` (all `7.26246.158`). Najjarun 314's shared profile explicitly
includes Equipment 238, resolved as Deactivator in `metadata.json`; its separate
option weapon 222 is not that Equipment. Racerbot 1905's legacy dual Bangbomb
encoding is interpreted using the tracked source-classification policy, not by
assuming raw collection placement is the public semantic classification.

**Supporting derived artifact S20:** tracked `data/generated/infinity.db` was
opened read-only. Its embedded metadata binds to S6's archive hash, 2026-09-29
download date and 2026-09-03 source-change date. It is not an independent official
rules source. REA-044 compares `metadata_weapons` source 225 with the public
application identity graph and getter; both numeric and slug lookups return
`None` despite the preserved metadata row. No database was rebuilt or altered.
The final protected-input check pins S20's unchanged bytes separately from source hashes.

## Revisited discrepancies and limitations

- **REA-027:** English one-save Flash Pulse row visually confirmed. S14 reproduces
  Spanish revision 3987's two saves/missing Trait and revision 3677's failed-save
  Stunned example. S17 missing; profile conflict remains unresolved.
- **REA-028:** printed Kobra CC DA/one-save/missing Anti-materiel visually confirmed
  on S1 p. 182. Two saves remain supported by DA and S6/S4; Anti-materiel unresolved.
- **REA-029:** S18 manifest recovered as local evidence, but the expected ZIP is
  still missing. Do not treat the manifest, S4, S5, or S14 as recovered S18 bytes.
- **REA-030:** S2/S15 publication comparison completed; ITS Ancillary scope remains
  unadjudicated for core scenarios. S16 verifies current Spec-Ops/TEAM-OPS separation.
- **REA-034:** S1 p. 138's extra Level 4 bonus visually confirmed. S14's Spanish
  example repeats it; repetition is not a resolving ruling.
- **REA-037:** S1 detailed S2 versus summary S1 verified visually on pp. 70/74/195.
  S14's detailed Spanish Wiki profile is S2. S17 missing; no priority rule invented.
- **REA-041/042:** additional Spanish Wiki inconsistencies found, with exact capture
  hashes; absence of S17 prevents assuming the capture equals the latest Spanish PDF.

Eight available local primary artifacts received selected-content comparisons;
S5 received an availability/hash check only. All nine available local primary
artifact hashes were checked. These counts exclude tracked derived S20 and
URL-only notices/pages. They do not assert whole-archive clause coverage.

No historical GitHub Army backup commit was independently acquired in follow-up.
The prior [source-history procedure](n5-source-history.md#historical-army-evidence)
still applies. Browser visual acceptance of the application remains separate from
visual inspection of the source PDF.
