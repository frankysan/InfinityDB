# Rules explanation audit 1.0: source provenance

**Project domains:** Acquisition, Data processing

This is the documentation-only evidence manifest for the
[audit](rules-explanation-audit-1.0.md) and its
[N5.3 reconciliation](rules-explanation-audit-1.0-n5.3-reconciliation.md).
Original examination: `859823f8d2899405a40cf126883d2adf5763db7c`.
Follow-up examination: `c5400ab1b950990fdacc509be91c110fe85431fb`, 2026-10-09.
**Supplementary verification (2026-10-09):** operator-supplied Spanish N5.3 PDF
and Spanish Wiki revision-history ZIP were inspected without changing curated data.
At those examined commits, the two curated collections retained their original hashes
and contained 367 records. These are frozen audit inputs, not current-candidate counts.

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
| S7 | Wiki Inmunidad, Spanish, revision 3677 | S21 revision timestamp 2025-07-15T14:34:59Z | Original URL read 2026-10-09; exact time not logged. Follow-up bytes independently inspected within S14 | [official page](https://infinitythewiki.com/es/Inmunidad); exact member `es/Inmunidad` in S14 | Example 4 and IMPORTANT clauses corroborate Flash Pulse result; do not settle S8's profile conflict. REA-010/027 |
| S8 | Wiki Tabla de Armas, Spanish, revision 3987 | S21 revision timestamp 2026-08-27T14:20:08Z | Original URL read 2026-10-09; follow-up S14 member inspection | [official page](https://infinitythewiki.com/es/Tabla_de_Armas); member `es/Tabla_de_Armas` | Flash Pulse still has two PB rolls and lacks State: Stunned. Breaker Marksman equivalent is under FUSILES DE PRECISIÓN. REA-027/044 |
| S9 | Wiki Ingeniero, Spanish, revision 3823 | S21 revision timestamp 2025-11-26T15:07:04Z | Original URL read 2026-10-09; follow-up S14 bytes | [official page](https://infinitythewiki.com/es/Ingeniero); member `es/Ingeniero` | Contact/STR repair/other-State branches and absence of an explicit universal Allied clause inspected. REA-001/009/038 |
| S10 | Wiki Ataque Intuitivo, Spanish, revision 3882 | S21 revision timestamp 2025-11-28T15:32:42Z; original web response had N5.2 banner | Original URL read 2026-10-09; exact time not logged | [official page](https://infinitythewiki.com/es/Ataque_Intuitivo); original URL-backed evidence | WIP resolution example supports REA-003. Not newly certified as a Spanish PDF clause |
| S11 | ITS Season 18 + N5.3 Rules Update, English, official publication notice | 2026-09-01, displayed publication date | Original and follow-up URL reads 2026-10-09; exact times not logged | [official notice](https://infinityuniverse.com/en/news/infinity-rules-update-5-3); rules and Army list items identified by ordinal in the reconciliation | All 26 English rules bullets and 20 Army bullets inventoried. Notice cannot override a rule/PDF/profile. English Breaker weapon label needs reconciliation, REA-044 |
| S12 | English Wiki Engineer 3980 and Intuitive Attack 3877 | S4 index: 3980 at 2025-10-31T11:38:24Z; 3877 at 2025-10-29T10:12:44Z | Original/follow-up URL reads; S4 separately captured exact oldid content | [Engineer](https://infinitythewiki.com/Engineer), [Intuitive Attack](https://infinitythewiki.com/Intuitive_Attack); S4 `_history/oldid/3980.html`, `_history/oldid/3877.html` | Direct clause evidence for REA-001/003/038; current banner does not change revision authorship dates |
| S13 | ITS Temporada 18 + Actualización N5.3, Spanish, official notice | 2026-09-01, displayed date | Follow-up URL read 2026-10-09; exact time not logged | [official Spanish notice](https://infinityuniverse.com/es/news/infinity-rules-update-5-3) | 30 rules bullets: the 26 shared subjects plus four language-specific subjects absent from English. Not proof that the Spanish PDF was checked |
| S14 | Infinity Wiki Spanish local capture; 786 members | Individual page revisions; no single publication/effective date | Existing manifest: 2026-10-09T21:13:04+02:00 | `data/wiki/WIKI-es 20261009-211304.zip`; origin `https://infinitythewiki.com/es/` | Discovered locally and independently hash/member checked during follow-up; not acquired by this task. Selected payloads below. Supports REA-027/034/037/038/041/042/044 and language reconciliation |
| S15 | N5 FAQs, English, cover v0.0; 4 file pages / 3 printed content pages | Creation metadata 2025-10-15; exact publication date unverified | Original download time unknown | `data/pdf/faq/n5-faqs-v0-0-en.pdf`; preserved official FAQ publication | Entire content compared with S2: 28 earlier Q&A blocks; S2 has 37, including nine additions. Historical FAQ scope remains separate |
| S16 | ITS Season 18: Overheat, English, version 2026.09.01; 132 pages | Cover explicitly says last updated September 1, 2026 | Original acquisition time unknown | `data/pdf/its/Its-rules-season-18-en.pdf`; cover gives current digital owner [ITS rules](https://experience.corvusbelli.com/en/infinity/its-rules) | Selected pp. 26, 28-29 inspected: ordinary Spec-Ops prohibited, TEAM-OPS is a distinct optional Extra and does not permit the Spec-Ops Skill. Supports REA-040's scope clarification; not a complete ITS audit |
| S17 | Infinity N5 Core Rules, Spanish, v5.3; 204 file/printed pages | PDF creation metadata 2026-08-10; **publication date not established by metadata**. S13 announcement 2026-09-01 | Operator supplied 2026-10-09; original download timestamp and authoritative direct URL unknown | Uploaded `esp-n5-update-5-3.pdf`; original portal [official resources](https://experience.corvusbelli.com/en/infinity/resources); retain the failed candidate URL only as earlier research history | **Verified SHA-256 and relevant rendered cells/clauses:** pp. 74, 75, 99, 140, 142, 191, 196, 203. The official Spanish PDF resolves the Flash Pulse *PDF-versus-PDF* question (REA-027); it repeats the Level 3 example error (REA-034), Armed Turret S2/S1 conflict (REA-037), and contradicts itself on Special Dice (REA-041). Its Dodge (BLI+3) wording agrees with English S1 (REA-042). No full-book bilingual audit claimed |
| S18 | Curated source `wiki-en-20260918-130233`, English capture, declared 812 members | Not a rules publication date | Declared 2026-09-18T13:02:33+02:00 | Expected `data/wiki/WIKI-en 20260918-130233.zip`; origin Wiki acquisition. Exact original operator archive required | **Still unavailable.** Expected hash agrees between tracked C/H declarations and ignored acquisition manifest; no ZIP bytes recovered. 72 records / 74 citations depend on it, REA-029 |
| S19 | Wiki Doctor, English, revision 3979; Médico, Spanish, revision 3822 | English: S4 index 2025-10-31T11:38:00Z; Spanish: S21 index 2025-11-26T15:03:51Z | Follow-up exact English bytes in S4 and Spanish bytes in S14 inspected; live URLs also read | [Doctor](https://infinitythewiki.com/Doctor), [Médico](https://infinitythewiki.com/es/M%C3%A9dico); `_history/oldid/3979.html` and `es/Medico` | Requirement/allegiance comparison, REA-002/038. Both distinguish older collapsed wording; no universal Allied target restriction located |
| S21 | Infinity Wiki Spanish revision-history archive; 2503 revisions, 3290 ZIP members | Each oldid has its own revision timestamp; no single effective rules date | Operator supplied 2026-10-09; archive filename includes `20261009-215316`, independently supplied download metadata not verified | `WIKI-es-history 20261009-215316.zip`; revision acquisition via `https://infinitythewiki.com/wiki-es/api.php`, `_history/index.json` plus `_history/oldid/*.html` | **Exact revision timestamps and payload hashes inspected**, with selected revisions below; historical content not automatically identical to S14 rendered current page bytes; corroborates REA-027/034/037/041/042. Not a replacement for missing S18 English archive |

## Supplementary Spanish PDF and revision-history checks

S17 is an actual **official Spanish N5.3 PDF**, not a hypothesized source. Its
creation timestamp (`2026-08-10T10:26:43+02:00`) precedes the official N5.3
notice (2026-09-01); the creation timestamp is not asserted to be the release
date. SHA-256 was measured directly from the uploaded PDF. S21 revision
identities and timestamps are from the captured MediaWiki API index, not from
filesystem timestamps or a page's current N5.3 banner. The old failed PDF
candidate endpoint is not evidence about the authenticity or contents of S17.

These additional sources clarify the **scope** of the five disputed findings:

- REA-027: S17 p. 196 prints Pulso Flash / Aturdidora / PB / **one** Saving
  Roll, including Estado: Aturdido and No Letal; S1 p. 186 matches. S8/S14/S21
  revision 3987 (2026-08-27) differs with two and without the State Trait.
  The supported **gameplay reference** is one PB/BTS roll; the discrepancy
  persists as a Spanish Wiki publication error/conflict, not a Spanish PDF one.
- REA-034: S17 p. 142 repeats the Level 3 Fireteam example including its
  Level 4 +1 CD bonus. Both official PDFs contain the conflicting example.
- REA-037: S17 p. 74 detailed Armed Turret S2 versus p. 74 deployable summary
  S1 and p. 203 summary S1. This is a **within-PDF contradiction in both
  languages**, not a version-independent resolution in favor of S2.
- REA-041: S17 p. 75 says +1DE does not count toward maximum Burst 6, but
  p. 140 Fireteam reminder includes extra dice in a total-six limit; the
  contradiction occurs inside the Spanish PDF, not just S14 Wiki pages.
- REA-042: S17 p. 75 says Esquivar (BLI+3) **always** adds +3 BLI on the
  Saving Roll when Dodge is declared, matching S1 p. 75. S14/S21 revision
  4012 (2026-09-08) retains a different condition. A source conflict remains,
  but is now **Wiki versus both current N5.3 PDFs**.

## Checksums and selected members

All values below are preserved from the original report where already present.
Previously available artifacts were hashed during the original follow-up;
S17 and S21 were independently hashed in this supplementary verification.
S18 remains an **expected** hash only, without verified ZIP bytes.

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
S17 7f564c864c6f26d6b218a0477c8afeba99da5c56e1a5369bb259f423689bb28f
S18 aa407f1959fbaafce98058acf507640cc94bfc2690d4a7519a547caf1492f23a EXPECTED ONLY
S21 ce588e4f7cb70b84ca115a63f66c3c227a0d7f91d89969caa9a1d46e94d9489b
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
| S14 | `es/Medico` | 3822 / timestamp from S21 index below | `333e201ea384c6de1466069cc9df2b2b8dbf63821865dbce4ed7063f3492cdf3` |
| S14 | `es/Ingeniero` | 3823 / timestamp from S21 index below | `fcb061fb360efd1fde552a56583a5e1ceb35313f950bd8f6d91f4574a810a8d2` |
| S14 | `es/Inmunidad` | 3677 / timestamp from S21 index below | `d2e4e2b07e1deb84983feb8a3481da99765591ec2e4da2d97f3d29557defdac8` |
| S14 | `es/Tabla_de_Armas` | 3987 / timestamp from S21 index below | `9410d3e948fb323dc04020a8ba329ada02ae0372c475324dfa9690692e88c5a5` |
| S14 | `es/Torreta_Artillada` | 3754 / timestamp from S21 index below | `d9319dc63273b92dd5e34474ba90eba1d385a100e35bfc7a09c193c12d5c5446` |
| S14 | `es/Bonos_de_Fireteam` | 3918 / timestamp from S21 index below | `db1b60ea63eb9740e22d0aee24eabc26a3462ebd8503bcf57fff90927d24ca76` |
| S14 | `es/Ejemplos_de_Fireteam` | 3443 / timestamp from S21 index below | `e3128e0df00a71bbe3db73c9aaf4046ea4ea19969ce10611bae70bc0c88321e7` |
| S14 | `es/Modificadores_(MOD)_Detallados` | 4012 / timestamp from S21 index below | `f5c6f7c60941d67a51ae77f05366285a6b464394a347c585e6060d168159b4c8` |
| S14 | `es/Sigilo` | 4004 / timestamp from S21 index below | `50dbfab5291c9ce556f68818160d1c39df4c19cc031dd958b8ee886d57823f34` |
| S14 | `es/Super-Salto` | 3964 / timestamp from S21 index below | `36ef1dac97b35e1e9ade92be99f397f321830857210aab165553c31cfbb76723` |
| S14 | `es/Visor_Multiespectral` | 4013 / timestamp from S21 index below | `ee8c52f2cae31c0a42cd7dd325f38c37dbe494464ee01d861ccfec5b33e3ea00` |

## S21 Spanish revision-history index (exact oldid provenance)

| Oldid / subject | Timestamp (UTC) | Exact archive member / SHA-256 |
| --- | --- | --- |
| 3677 / Inmunidad | 2025-07-15T14:34:59Z | `_history/oldid/3677.html` / `2ac16b93221c59756de397334a3e1d82f07930c3c493d828223bff1da2c87305` |
| 3987 / Tablas de Armas | 2026-08-27T14:20:08Z | `_history/oldid/3987.html` / `7f0d1899d469077baf51a93216ca34ed6d6ccd32ebfe7d54bd141e6b94a6b0a1` |
| 3822 / Médico | 2025-11-26T15:03:51Z | `_history/oldid/3822.html` / `a690c8f8c2334706696521767b0da0b6540903e96fa8efca6fb2804cda3e91d1` |
| 3823 / Ingeniero | 2025-11-26T15:07:04Z | `_history/oldid/3823.html` / `063b05c98db95867f8a1f6535a5c9aa376fc6fea048477fd81afe517fd702029` |
| 3882 / Ataque Intuitivo | 2025-11-28T15:32:42Z | `_history/oldid/3882.html` / `2632c9ee022706a05917fae75c6b10cfa89daa71c0fc44ad79693eaea529722a` |
| 3918 / Bonos de Fireteam | 2025-11-28T16:26:17Z | `_history/oldid/3918.html` / `7e11bdd6a340a9b36a746977e8d8888fedd3bf6bc99053dc5d5742c2953b0400` |
| 4012 / Módulo de Habilidades y Equipo (MOD) | 2026-09-08T10:04:10Z | `_history/oldid/4012.html` / `2356720d93a1eeafa1c21874fcae2b684ec0f28522a97125f6cccce1957aba63` |
| 3443 / Ejemplos de Fireteam | 2025-07-08T12:38:50Z | `_history/oldid/3443.html` / `2ed3f2ef1c2746d21721003331b480b923dfe621f5d35c958923f9ba6cac9caa` |
| 3754 / Torreta Artillada | 2025-11-19T14:44:41Z | `_history/oldid/3754.html` / `2baeac78a1a749b10891b2017eef656caade4566381c4fccdc93bf79998423c4` |

S14's current-page member bytes and S21's pinned historical oldid bytes have
**different hashes**; cite the exact archive and member when attributing text.
The revision date of Spanish Weapon Chart 3987 is later than the PDF creation
metadata, but this does **not** establish that the Wiki supersedes the officially
published N5.3 PDF, or prove which editorial mistake caused the difference.

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

- **REA-027:** S17 Spanish PDF p. 196 and S1 English PDF p. 186 agree:
  one BTS/PB save with the State: Stunned and Non-Lethal Traits. Spanish Wiki
  revision 3987 (S14/S21) instead shows two and lacks the State Trait.
  Gameplay interpretation supported; the Wiki publication discrepancy remains.
- **REA-028:** printed Kobra CC DA/one-save/missing Anti-materiel visually
  confirmed on S1 p. 182, and S17 p. 191 repeats DA/one save. DA rules and
  S6/S4 support two saves; Anti-materiel remains unresolved.
- **REA-029:** S18 acquisition manifest is present as local evidence, but
  its expected exact English Wiki ZIP bytes are still missing.
- **REA-030:** S2/S15 publication comparison completed; ITS Ancillary scope
  remains unadjudicated for core scenarios. S16 verifies separate TEAM-OPS.
- **REA-034:** both PDFs have the Level 3 example with the Level 4 BS/CD
  bonus; tables disagree. No overriding FAQ/erratum independently verified.
- **REA-037:** both PDFs show Armed Turret S2 in detailed profile and S1 in
  deployable summary; a source decision remains necessary.
- **REA-041:** S17 **itself** contradicts its general SD/Burst explanation
  (p. 75) in a Fireteam reminder (p. 140). Keep both printed clauses.
- **REA-042:** both official v5.3 PDFs grant the Dodge ARM/BLI +3 when
  declared; the captured Spanish Wiki 4012 uses a different condition. The
  missing-PDF rationale is superseded, but an upstream Wiki discrepancy remains.

Eleven locally supplied/available primary source artifacts are accounted for:
S1-S6, S14-S17, and S21. S1/S2/S4/S5/S6/S14/S17/S21 are now directly
available from the supplied material; S3/S15/S16 were cited as inspected in
the prior audit and were **not supplied anew in this review**. The provenance
register preserves original classifications and does not claim a new whole-PDF
or whole-Wiki-corpus audit. S18 remains unavailable.

No historical GitHub Army backup commit was independently acquired in follow-up.
The prior [source-history procedure](n5-source-history.md#historical-army-evidence)
still applies. Browser visual acceptance of the application remains separate from
visual inspection of the source PDF.
