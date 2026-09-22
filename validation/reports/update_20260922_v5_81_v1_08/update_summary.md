# 2026-09-22 update acceptance report

## Gate

**READY_FOR_PRODUCTION_PROMOTION**

Source Freeze, reviewed correspondence, candidate-audit full pipeline, isolated strict production-profile pipeline, structured search, and frontend validation passed with prohibited unmapped=0. Current production artifacts remained unchanged; no promotion was run.

No production canonical, release, unified, SQLite, Site-data, Sites Version, or deployment was changed.

## Three snapshots and source-state gate

- PRODUCTION: kokkoritsu 5.61 / shidai 0.97
- SUPERSEDED: kokkoritsu 5.74 / shidai 1.08
- CANDIDATE: kokkoritsu 5.81 / shidai 1.08

| Dataset | Old | Candidate | Dataset state | Artifact state | Source freeze | Gate |
|---|---:|---:|---|---|---|---|
| kokkoritsu | 5.61 | 5.81 | FROZEN | frozen | - | PASS |
| shidai | 0.97 | 1.08 | - | - | FROZEN | PASS |

Kokkoritsu v5.81 declares `dataset_state: FROZEN`; shidai v1.08 declares `sources.freeze_status: FROZEN`. The superseded kokkoritsu v5.74 remains historical input only and is never used for candidate builds.

Candidate version identity was checked against each supplied schema and its `canonical_data` filenames; filename-only inference was not used.

## Incoming preflight

| Dataset | File | Rows | Columns | Encoding | BOM | SHA-256 |
|---|---|---:|---:|---|---|---|
| kokkoritsu | master | 4,011 | 75 | UTF-8 | False | `d77665c27c2a4deed8f85d73ba6c546fe24fad21ded6a28719d67e2f3b490d6b` |
| kokkoritsu | coverage | 187 | 10 | UTF-8 | False | `8bce9276537767eb4fa2285f4d398f33d3634369e4168720c7f752d964e9bc5e` |
| kokkoritsu | research_requirements | 281 | 13 | UTF-8 | False | `044dba433319b482ae309952be4e765c85a412c77be1431617c8ff1584f40ec3` |
| kokkoritsu | schema | - | - | UTF-8 | False | `26b0bd61ea21f92927c31823a9b0057167d161c5ff0da0dd17dcaef0479c6bd0` |
| shidai | master | 2,400 | 75 | UTF-8-SIG | True | `7062ae8afb09eabc9aa6118dc0fc44e6170037db8c1f069684b5cdbcd170ce0e` |
| shidai | coverage | 73 | 10 | UTF-8-SIG | True | `489f97680cc51374af59ab8e037e3ab399e1aff7cb00ed5fb95c043ff36b349d` |
| shidai | research_requirements | 214 | 13 | UTF-8-SIG | True | `9269bb49ca61ad7d6a0771445c5bb925821fff4e699fd4807d35cc3a33b35ac8` |
| shidai | schema | - | - | UTF-8 | False | `6abf1bd3ae76fdd22ecabe968804ef9aac98d15d95f36f14046fec178a09c4cd` |

All candidate CSV headers match their supplied schema column lists and the current column order. There are no row-width mismatches, duplicate Master IDs, or duplicate Coverage keys.

## Candidate Unified checkpoint

Unified validation: `passed`; source versions `{'kokkoritsu': '5.81', 'shidai': '1.08'}`.
Rows: master 6,411, coverage 260, ResearchRequirements 495.
Manifest SHA-256: `66431d3ee6dca98bdb462a6838366017a8d02d25ce138e810844987f43b65eba`.

## Candidate audit validation profile

Previous final gate: `HOLD_BUILD`. The cause was a production-only English-unmapped publication blocker, not source corruption.

`production` remains the default deployability gate and continues to reject English `unmapped`. `candidate_audit` requires explicit opt-in, preserves raw and mapping status, keeps search fail-closed, and marks every derived artifact inspection-only with `production_ready: false`.

Gate history is preserved in `update_summary.json`: the earlier `HOLD_BUILD` and subsequent `READY_FOR_HUMAN_REVIEW` are not replaced by the current decision.

PK/FK, malformed row/schema, source/raw mismatch, invalid tri-state, SQLite integrity, FTS, and Site-data referential failures remain hard errors in both profiles. Only approved reviewable mapping gaps have profile-specific severity.

## Source row diff

| Dataset | Old | New | Unchanged | Added | Removed | Changed | Material changed |
|---|---:|---:|---:|---:|---:|---:|---:|
| kokkoritsu | 3,668 | 4,011 | 939 | 447 | 104 | 2,625 | 126 |
| shidai | 2,253 | 2,400 | 1,881 | 147 | 0 | 372 | 12 |
| total | 5,921 | 6,411 | 2,820 | 594 | 104 | 2,997 | 138 |

Full added/removed rows and field-level changed rows are in the ignored `data/derived/update_audit/20260922_v5_81_v1_08/` directory.

## Fallback transitions

| Dataset | Removed | Newly introduced | Current-year upgrades | Added fallback rows | Information-year changes | Publication-status changes |
|---|---:|---:|---:|---:|---:|---:|
| kokkoritsu | 0 | 0 | 0 | 21 | 0 | 150 |
| shidai | 0 | 0 | 0 | 0 | 0 | 0 |

## Superseded v5.74 to frozen v5.81

Master 3,841 → 4,011; added 303, removed 133, changed 2,409, material changed 0.
Coverage added/removed/changed: 0/0/46. Research exact rows added/removed: 5/0.
Source state: `UNFROZEN` → `FROZEN`.

## Sidecar coherence

| Dataset | Coverage missing | Coverage mismatches | Research rows | Exact duplicates | Orphans | Display mismatches |
|---|---:|---:|---:|---:|---:|---:|
| kokkoritsu | 0 | 0 | 281 | 0 | 0 | 8 |
| shidai | 0 | 0 | 214 | 4 | 0 | 2 |

The supplied versioned sidecars are structurally coherent with their candidate Master tables. Display-field differences and exact child duplicates remain contract-defined warnings and are not rewritten or deduplicated.

## Full source validator

The production validator semantics were run against all six candidate CSVs without changing severity or accepted values.

| Dataset | Errors | Warnings | Informational |
|---|---:|---:|---:|
| kokkoritsu | 0 | 1149 | 1352 |
| shidai | 0 | 18 | 1940 |
| total | 0 | 1167 | 3292 |

Baseline to candidate severity delta:

| Severity | Baseline | Candidate | Delta |
|---|---:|---:|---:|
| error | 0 | 0 | +0 |
| warning | 686 | 1167 | +481 |
| informational | 3136 | 3292 | +156 |

Warning-code deltas:

| Code | Baseline | Candidate | Delta |
|---|---:|---:|---:|
| `DETAIL_COMPLETENESS_UNMAPPED` | 318 | 767 | +449 |
| `PROVENANCE_URL_MISSING` | 19 | 55 | +36 |
| `RESEARCH_ACTIVITY_LEVEL_UNMAPPED` | 281 | 281 | +0 |
| `RESEARCH_DENORMALIZED_FIELD_MISMATCH` | 8 | 10 | +2 |
| `RESEARCH_EXACT_DUPLICATE` | 4 | 4 | +0 |
| `RESEARCH_REQUIRED_WITHOUT_CHILD` | 51 | 45 | -6 |
| `WHITESPACE_PADDING` | 5 | 5 | +0 |

## Derived fail-closed review gate

| Layer | New-vs-old raw values | Unmapped values | Unmapped rows |
|---|---:|---:|---:|
| gpa | 63 | 0 | 0 |
| grade_requirement | 63 | 0 | 0 |
| english_requirement | 66 | 0 | 0 |
| prefecture | 0 | 0 | 0 |
| academic_field_v0_1 | 39 | 0 | 0 |
| academic_field_v0_2 | 39 | 0 | 0 |

Academic-field v0.2 candidate coverage: Broad 6,400/6,411; Subcategory 5,317/6,411; exact context consulted/effective 1,579/1,568.
New program-context tuples: 368; review required: 0.

Human-review packets and versioned decision CSVs are retained beside this report. The approved decisions are reflected only in new versioned crosswalks; historical crosswalks remain unchanged.

## Downstream acceptance stages

| Stage | Result |
|---|---|
| Full source validator | completed_zero_errors |
| Unified candidate rebuild | passed |
| SQLite candidate rebuild/validation | passed |
| Structured-search regression | passed |
| Site-data candidate rebuild/validation | passed |
| Frontend candidate tests/build | passed |
| Isolated strict production-profile build | passed |
| Sites Version/deployment | NOT RUN - explicitly prohibited |

## Candidate artifacts

- Unified rows: master 6,411, coverage 260, research 495
- SQLite: `16b93c33fe7acfb964c55291b36ca26977dfd3da21dd967bb190ec385601573d` (37,318,656 bytes), profile `trigram`
- Validation profile: `candidate_audit`; production ready: `false`
- Review-required counts: `{"academic_field_context_review": 0, "academic_field_unmapped_admissions": 0, "academic_field_v2_unmapped_admissions": 0, "english_unmapped_admissions": 0, "gpa_new_unmapped_admissions": 0, "gpa_unparsed_admissions": 227, "grade_unmapped_admissions": 0}`
- SQLite validation: `passed`; FTS5=True, trigram=True
- Site-data build ID: `f31383fed50309ee033e`
- Site-data manifest SHA-256: `0d289be663c1df7ca25aa4e30843fbfaa8301d47d121584e418eb0ad52dbf2f9`
- Site-data deterministic rebuild: `passed` (274 files)

## Representative search deltas

| Query | Production | Candidate | Delta | Universities old/new | Added | Removed |
|---|---:|---:|---:|---|---:|---:|
| 東京都 membership | 1010 | 1261 | +251 | 50/53 | 260 | 9 |
| 神奈川県 membership | 684 | 689 | +5 | 23/23 | 11 | 6 |
| 東京＋神奈川 membership | 1694 | 1950 | +256 | 68/69 | 271 | 15 |
| 法学・政治・公共政策 | 81 | 114 | +33 | 40/45 | 35 | 2 |
| 経済 | 150 | 173 | +23 | 52/58 | 26 | 3 |
| 経営・商 | 169 | 191 | +22 | 44/48 | 26 | 4 |
| 心理 | 25 | 31 | +6 | 13/18 | 7 | 1 |
| 外国語・言語 | 128 | 197 | +69 | 27/32 | 71 | 2 |
| 理学 | 702 | 762 | +60 | 99/100 | 69 | 9 |
| 理学＋数学 | 107 | 113 | +6 | 42/44 | 7 | 1 |
| 工学 | 1642 | 1696 | +54 | 123/124 | 81 | 27 |
| 情報 | 865 | 892 | +27 | 126/129 | 35 | 8 |
| 評定条件あり | 2286 | 2373 | +87 | 194/196 | 99 | 12 |
| overall GPA 3.8 | 833 | 871 | +38 | 109/113 | 38 | 0 |
| English required | 311 | 467 | +156 | 45/59 | 171 | 15 |
| research achievement | 231 | 273 | +42 | 47/51 | 42 | 0 |
| exclusive enrollment | 4269 | 4474 | +205 | 216/220 | 231 | 26 |
| common test | 1342 | 1432 | +90 | 109/112 | 90 | 0 |
| combined representative | 78 | 78 | +0 | 11/11 | 0 | 0 |

## Fail-closed search denominator

- Total admissions: 6,411
- English safe binary-search rows / unmapped excluded: 1,732 / 0
- Grade mapped rows / unmapped: 6,411 / 0
- GPA safe numeric / unparsed: 1,258 / 227
- Academic-field v0.2 Broad/Subcategory coverage: 6,400 / 5,317
- Academic-field v0.2 no-Broad membership / unmapped / context review: 11 / 0 / 0

Review-sensitive queries record candidate matches, excluded-unmapped counts, and representative stable record IDs in `update_summary.json`.

## Frontend and performance

- Frontend tests: PASS (151)
- Responsive focused tests: PASS (11)
- Repository tests: PASS (141)
- Production build: PASS
- Admissions size delta: 5,921 → 6,411 (+8.28%)
- SQLite size delta: 34,058,240 → 37,318,656 bytes (+9.57%)
- Site-data total: 52,206,123 → 56,782,525 bytes (+8.77%)
- Search projection: 14,210,412 → 15,398,431 bytes (+8.36%)
- Search projection gzip: 797,884 → 876,809 bytes (+9.89%)
- Detail projection: 37,822,700 → 41,207,307 bytes (+8.95%)
- Detail projection gzip-equivalent: 4,867,844 → 5,385,169 bytes (+10.63%)
- Candidate build time: SQLite 6.998s; Site-data 29.817s; deterministic rebuild 29.901s
- Frozen 25-query median latency: 37.637 → 38.834 ms

## Isolated strict production profile

- SQLite: `3f7cda8c9788f601c86991b7d0ccb19fc516638ef9c19d91447fd71d2ab0bbe7` (37,318,656 bytes)
- SQLite validation/profile: `passed` / `production`
- Site-data build ID: `f23d7efe23536453f276`
- Site-data manifest SHA-256: `27a7ab931f71ccbd701b92c3210f226ec3b4fac39d7433c94696cea95b6c497a`
- Frozen structured-search queries: 25/25 PASS
- Frontend tests, responsive tests, oracle export, and production build: PASS

## Production immutability

Receipt status: `passed`; checked 20 files/directories; changed 0.

## Human decision

The gate authorizes a separate future promotion decision only. It does not mean that production canonical data, artifacts, Git state, Sites Version, or deployment was changed.
