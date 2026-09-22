# 2026-09-22 update acceptance report

## Gate

**HOLD_SOURCE_COHERENCE**

The complete versioned four-file bundles were supplied and the CSV relationships validate, but kokkoritsu v5.74 explicitly declares dataset_state=UNFROZEN and canonical_csv_json=active_unfrozen. That source-owned state is a mandatory stop gate.

No canonical, release, unified, SQLite, Site-data, frontend source, Sites Version, or deployment was changed.

## Versions and source-state gate

| Dataset | Old | Candidate | Dataset state | Artifact state | Source freeze | Gate |
|---|---:|---:|---|---|---|---|
| kokkoritsu | 5.61 | 5.74 | UNFROZEN | active_unfrozen | - | HOLD |
| shidai | 0.97 | 1.08 | - | - | FROZEN | PASS |

Kokkoritsu v5.74 explicitly declares `dataset_state: UNFROZEN` and `artifact_status.canonical_csv_json: active_unfrozen`. Its `unfreeze` block records post-freeze batch processing. This authoritative state blocks downstream release-candidate generation until the source is explicitly re-frozen.

Candidate version identity was checked against each supplied schema and its `canonical_data` filenames; filename-only inference was not used.

## Incoming preflight

| Dataset | File | Rows | Columns | Encoding | BOM | SHA-256 |
|---|---|---:|---:|---|---|---|
| kokkoritsu | master | 3,841 | 75 | UTF-8 | False | `d4e0df40df4ac45e773b0b16e4fa08151f8182d9122dbcf1dc65086b79de4bc5` |
| kokkoritsu | coverage | 187 | 10 | UTF-8 | False | `c241c39033781214aacb9ca11f7a354f88f8408a4054964263aeeb73e3c713cc` |
| kokkoritsu | research_requirements | 276 | 13 | UTF-8 | False | `3d4374fa7f7373fb7ea1b2c012f1aefd79f5c5441b7b58a2dd2e8c6413e426e7` |
| kokkoritsu | schema | - | - | UTF-8 | False | `a75f6367c6d371f573eb9fcfc0f23d8ebb2474f33a1f3755695edfa9b522a05c` |
| shidai | master | 2,400 | 75 | UTF-8-SIG | True | `7062ae8afb09eabc9aa6118dc0fc44e6170037db8c1f069684b5cdbcd170ce0e` |
| shidai | coverage | 73 | 10 | UTF-8-SIG | True | `489f97680cc51374af59ab8e037e3ab399e1aff7cb00ed5fb95c043ff36b349d` |
| shidai | research_requirements | 214 | 13 | UTF-8-SIG | True | `9269bb49ca61ad7d6a0771445c5bb925821fff4e699fd4807d35cc3a33b35ac8` |
| shidai | schema | - | - | UTF-8 | False | `6abf1bd3ae76fdd22ecabe968804ef9aac98d15d95f36f14046fec178a09c4cd` |

All candidate CSV headers match their supplied schema column lists and the current column order. There are no row-width mismatches, duplicate Master IDs, or duplicate Coverage keys.

## Source row diff

| Dataset | Old | New | Unchanged | Added | Removed | Changed | Material changed |
|---|---:|---:|---:|---:|---:|---:|---:|
| kokkoritsu | 3,668 | 3,841 | 3,248 | 174 | 1 | 419 | 133 |
| shidai | 2,253 | 2,400 | 1,881 | 147 | 0 | 372 | 12 |
| total | 5,921 | 6,241 | 5,129 | 321 | 1 | 791 | 145 |

Full added/removed rows and field-level changed rows are in the ignored `data/derived/update_audit/20260922_v5_74_v1_08/` directory.

## Fallback transitions

| Dataset | Removed | Newly introduced on shared records | Added fallback rows | Information-year changes | Publication-status changes |
|---|---:|---:|---:|---:|---:|
| kokkoritsu | 0 | 0 | 21 | 0 | 157 |
| shidai | 0 | 0 | 0 | 0 | 0 |

## Sidecar coherence

| Dataset | Coverage missing | Coverage mismatches | Research rows | Exact duplicates | Orphans | Display mismatches |
|---|---:|---:|---:|---:|---:|---:|
| kokkoritsu | 0 | 0 | 276 | 0 | 0 | 8 |
| shidai | 0 | 0 | 214 | 4 | 0 | 2 |

The supplied versioned sidecars are structurally coherent with their candidate Master tables. Display-field differences and exact child duplicates remain contract-defined warnings and are not rewritten or deduplicated.

## Full source validator

The production validator semantics were run against all six candidate CSVs without changing severity or accepted values.

| Dataset | Errors | Warnings | Informational |
|---|---:|---:|---:|
| kokkoritsu | 0 | 991 | 1358 |
| shidai | 0 | 18 | 1940 |
| total | 0 | 1009 | 3298 |

Baseline to candidate severity delta:

| Severity | Baseline | Candidate | Delta |
|---|---:|---:|---:|
| error | 0 | 0 | +0 |
| warning | 686 | 1009 | +323 |
| informational | 3136 | 3298 | +162 |

Warning-code deltas:

| Code | Baseline | Candidate | Delta |
|---|---:|---:|---:|
| `DETAIL_COMPLETENESS_UNMAPPED` | 318 | 612 | +294 |
| `PROVENANCE_URL_MISSING` | 19 | 52 | +33 |
| `RESEARCH_ACTIVITY_LEVEL_UNMAPPED` | 281 | 281 | +0 |
| `RESEARCH_DENORMALIZED_FIELD_MISMATCH` | 8 | 10 | +2 |
| `RESEARCH_EXACT_DUPLICATE` | 4 | 4 | +0 |
| `RESEARCH_REQUIRED_WITHOUT_CHILD` | 51 | 45 | -6 |
| `WHITESPACE_PADDING` | 5 | 5 | +0 |

## Derived fail-closed review gate

| Layer | New-vs-old raw values | Unmapped values | Unmapped rows |
|---|---:|---:|---:|
| gpa | 51 | 51 | 325 |
| grade_requirement | 51 | 51 | 325 |
| english_requirement | 43 | 43 | 145 |
| prefecture | 0 | 0 | 0 |
| academic_field_v0_1 | 28 | 28 | 64 |
| academic_field_v0_2 | 28 | 28 | 64 |

Academic-field v0.2 candidate coverage: Broad 6,165/6,241; Subcategory 5,203/6,241; exact context consulted/effective 1,495/1,484.

Human-review CSVs are stored beside this report. They are recommendations only and do not modify any production crosswalk.

## Downstream acceptance stages

| Stage | Result |
|---|---|
| Full source validator | PASS with contract-defined findings; zero errors |
| Unified candidate rebuild | NOT RUN - kokkoritsu v5.74 is explicitly UNFROZEN |
| SQLite candidate rebuild/validation | NOT RUN - gated by unified candidate |
| Structured-search regression | NOT RUN - no coherent SQLite candidate |
| Site-data candidate rebuild/validation | NOT RUN - no coherent SQLite candidate |
| Frontend candidate tests/build | NOT RUN - no coherent Site-data candidate |
| Sites Version/deployment | NOT RUN - explicitly prohibited |

## Required source-owner action before continuation

Provide an authoritative re-frozen kokkoritsu bundle/schema, or an explicit source-owner correction that changes the v5.74 source state from UNFROZEN. Do not relabel these files locally. After that state change, rerun this audit; the existing crosswalk review packet remains fail-closed and will gate production readiness separately.
