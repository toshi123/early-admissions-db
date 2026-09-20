# Early Admissions Unified Data Contract v0.1 (proposal)

## 1. Status and scope

- Contract version: `0.1`
- Status: proposal; no unified dataset has been generated under this contract.
- Target admission year: 2027.
- Source datasets:
  - `kokkoritsu`, source version `5.61`
  - `shidai`, source version `0.97`
- Authoritative inputs are the canonical CSV files and their source schemas. This contract does not modify, repair, deduplicate, or overwrite canonical or release data.
- The unified layer consists of three logical tables: `Master`, `Coverage`, and `ResearchRequirements`.
- Field-level mappings are defined in `docs/unified_field_mapping_v0_1.md`.
- The machine-readable row and column contract is defined in `schema/unified/early_admissions_unified_schema_v0_1.json`.

This proposal defines a loss-aware integration boundary. It does not assert that identically named source fields have identical semantics unless this document or the field mapping explicitly says so.

## 2. Authoritative sources and immutability

The following files remain authoritative and immutable for this contract:

- `data/canonical/kokkoritsu/master.csv`
- `data/canonical/kokkoritsu/coverage.csv`
- `data/canonical/kokkoritsu/research_requirements.csv`
- `schema/kokkoritsu/kokkoritsu_early_admissions_schema_v5_61.json`
- `data/canonical/shidai/master.csv`
- `data/canonical/shidai/coverage.csv`
- `data/canonical/shidai/research_requirements.csv`
- `schema/shidai/shidai_early_admissions_schema_v0_97.json`

All normalization is performed only while producing a derived unified artifact. A source value that is ambiguous, unsupported by an approved crosswalk, or inconsistent with another field must remain traceable to its canonical source and must not be silently repaired.

## 3. Tables, grain, and identities

### 3.1 Master

- Grain: one row is one actual application unit / selection slot.
- Source primary key: `record_id` within one source dataset and source version.
- Unified primary key: (`source_dataset`, `source_version`, `record_id`).
- `record_id` is copied unchanged. A globally unique replacement identifier is not generated in v0.1.

### 3.2 Coverage

- Grain: one row records investigation/coverage state for one university within one source dataset and source version.
- Unified key: (`source_dataset`, `source_version`, `institution_type`, `university`).
- A Coverage row with `master_rows = 0` is valid. It may represent a graduate-only institution, no applicable 2027 early-admissions slot, a stopped recruitment program, or a source-access/review hold.
- `master_rows` must equal the number of Master rows having the same source dataset, source version, institution type, and university.

### 3.3 ResearchRequirements

- Grain: one source row that preserves a structured detail about a research competition, research activity, required level, evidence, or related condition.
- Foreign key: (`source_dataset`, `source_version`, `admission_id`) references Master (`source_dataset`, `source_version`, `record_id`).
- No natural or synthetic primary key is introduced in v0.1.
- Source row multiplicity is preserved. Exact duplicate source rows are not silently removed.
- A later SQLite/export layer may add a technical surrogate row identifier, but it must not be treated as an admission fact.

ResearchRequirements does **not** receive a new `required / alternative / relevant` classification in v0.1. The current information is not sufficiently consistent to support that classification without inference.

The intended relationship is:

- Master `research_requirement_required` describes whether a research-achievement requirement is present according to the source Master row.
- ResearchRequirements preserves structured details when such details are available, including activity, competition, required level, evidence, or related conditions.
- Parent flag and child-row existence are not required to correspond one-to-one.

Consequently:

- `research_requirement_required = Yes` with no child row is a validator **warning**, not an error.
- `research_requirement_required = No` with one or more child rows is validator **informational**, not an error.
- An orphan `admission_id` remains an error.

## 4. Source provenance

Every unified row must contain:

- `source_dataset`: `kokkoritsu` or `shidai`
- `source_version`: `5.61` or `0.97`, respectively

Allowed pairs are fixed for v0.1:

| source_dataset | source_version |
|---|---|
| `kokkoritsu` | `5.61` |
| `shidai` | `0.97` |

Any other pair is an error. These fields identify the source snapshot; they do not replace row-level source URLs, verification dates, or evidence fields.

## 5. Null and unknown semantics

The unified logical representation distinguishes three states:

1. A concrete value: the source provides a usable value.
2. An explicit unknown: the source row explicitly contains `Unknown`, `unknown`, or `不明` in a field whose approved enum supports that state.
3. `null`: the source CSV cell is blank, or the field is structurally not applicable.

Rules:

- `null` must not be converted to `Unknown`, `No`, `false`, zero, or an empty list.
- Explicit unknown must not be converted to `null` or a negative value.
- A source `No` must not be inferred merely because a detail field or child row is absent.
- JSON uses `null`. Unified CSV serialization uses an empty cell for `null`.
- Whitespace-only or unexpectedly padded values are reported; they are not silently trimmed in the base unified artifact.

## 6. Common Test fields are distinct

`common_test_required` and `selection_common_test` remain separate fields.

- `common_test_required`: whether taking, submitting, or otherwise satisfying the Common Test is stated as a requirement for the application unit.
- `selection_common_test`: whether the Common Test is represented as an explicit component in the structured selection-method flags.

No equality constraint, implication, warning, or automatic synchronization is defined between these fields. Their existing disagreements must be preserved.

The source value `条件付き` in `common_test_required` is mapped to the unified enum value `Conditional`. It is not mapped to `Yes` or `No`.

## 7. Date and period fields

The base unified dataset preserves the exact nonblank source strings for:

- `application_start`
- `application_end`
- `web_registration_period`
- `first_stage_result_date`
- `second_stage_start`
- `second_stage_end`
- `final_result_date`
- `verified_on`
- `checked_on`

The base fields are raw strings, not typed search dates. Time suffixes, explanatory text, ranges, and explicit `Unknown` values remain unchanged.

A later search/index layer may add normalized fields such as `<field>_date`, `<field>_start_date`, `<field>_end_date`, and `<field>_parse_status`. Those fields must be derived without overwriting the raw value. Ambiguous strings must produce `unparsed` or `partial`, not a guessed date.

## 8. Common status plus source raw value

### 8.1 Detail completeness

The source `detail_completeness` field is split into:

- `detail_completeness_status`: common enum
- `detail_completeness_raw`: exact nonblank source value

Common enum values:

- `complete`
- `partial`
- `pending`
- `unknown`
- `unmapped`
- `null`

`unmapped` means that a nonblank source value exists but no approved lossless crosswalk currently maps it. It is not equivalent to `unknown`, `partial`, or `pending`.

This status is a normalized form of the source's own completeness label. `complete` does not certify that every validator passes and may coexist with evidence or provenance warnings.

Approved v0.1 mappings are intentionally narrow:

- Shidai `complete`, `partial`, `pending`, and `unknown` map directly.
- Kokkoritsu values beginning with `detailed` map to `complete`.
- Kokkoritsu values beginning with `partial` map to `partial`.
- Other nonblank values map to `unmapped` until explicitly reviewed.
- Blank maps to `null`.

### 8.2 Research activity level

The source `research_activity_level` field is split into:

- `research_activity_level_status`: common enum
- `research_activity_level_raw`: exact nonblank source value

Common enum values:

- `required`
- `relevant`
- `none`
- `unknown`
- `unmapped`
- `null`

Only the explicit crosswalk in the field-mapping document may populate a non-`unmapped` common value. No classifier based on arbitrary substring matching or child-row presence is allowed.

The common research-activity status does not change the separate meaning of `research_requirement_required` and does not classify ResearchRequirements child rows.

Likewise, `research_activity_level_status` is a normalized source label, not a value inferred from child-row count or independently re-adjudicated facts.

## 9. Other source-specific fields

The following fields retain their exact source strings in v0.1 and must not be treated as common enums without a later contract revision:

- Master `slot_type`
- Master `source_status`
- Master `publication_status`
- Coverage `research_status`
- Coverage `current_year_status`
- Coverage `fallback_status`
- ResearchRequirements `alternative_allowed`
- ResearchRequirements `evidence_required`

The same column name does not imply a shared controlled vocabulary for these fields.

## 10. Normalization allowed in v0.1

Only the following transformations are permitted:

- Add fixed `source_dataset` and `source_version` values.
- Parse `admission_year`, `information_year`, and Coverage `master_rows` as integers when nonblank and valid.
- Normalize `stem_flag`:
  - `True` or `Yes` -> `true`
  - `False` or `No` -> `false`
  - blank -> `null`
- Normalize `fallback_previous_year` by the same boolean crosswalk.
- Normalize approved `Yes / No / Unknown` fields to those exact strings; blank remains `null`.
- Map `common_test_required = 条件付き` to `Conditional`.
- Apply the explicit detail-completeness and research-activity crosswalks.
- Convert a blank CSV cell to logical `null`.

All other values are copied exactly. Unrecognized values in a normalized field are errors unless that field explicitly supports `unmapped`.

## 11. Validation severity

### Errors

- Missing or unsupported (`source_dataset`, `source_version`) pair.
- Missing or duplicate Master unified primary key.
- Blank ResearchRequirements `admission_id`.
- Orphan ResearchRequirements foreign key.
- Duplicate Coverage unified key.
- Coverage `master_rows` differs from the actual Master count.
- Missing required columns or wrong column order.
- Invalid value for a closed unified enum after applying the approved mapping.
- Silent removal, replacement, or rewriting of a nonblank raw source value.

### Warnings

- `research_requirement_required = Yes` with no ResearchRequirements child row.
- Exact duplicate ResearchRequirements rows. Duplicates remain present unless canonical data is separately revised.
- Parent/child denormalized display fields differ, including university, faculty, department, or selection name.
- A nonblank detail-completeness or research-activity raw value maps to `unmapped`.
- A provenance URL required by the applicable source policy is blank.
- Unexpected leading/trailing whitespace.

### Informational

- `research_requirement_required = No` with one or more ResearchRequirements child rows.
- Coverage row with `master_rows = 0` and an explicit coverage/status explanation.
- Raw date or period string is not an unambiguous ISO date.
- `common_test_required` and `selection_common_test` differ.

## 12. Serialization and column order

- UTF-8 is required for derived unified CSV and JSON.
- Unified CSV uses LF line endings and no BOM.
- CSV `null` is an empty cell.
- JSON `null` is JSON null; booleans and integers use native JSON types.
- Field order for each CSV is fixed by `x-table-contracts.*.csv_columns` in the unified schema.
- Input BOM and line-ending differences are parser concerns and do not alter source facts.
- The JSON Schema root describes a logical dataset bundle. Implementations may validate records incrementally against `$defs.masterRecord`, `$defs.coverageRecord`, and `$defs.researchRequirementRecord`; they need not materialize all rows in memory.

## 13. Explicitly out of scope

This proposal does not:

- modify canonical or release files;
- remove duplicate ResearchRequirements rows;
- repair factual discrepancies;
- infer missing admission facts;
- classify ResearchRequirements rows as required, alternative, or relevant;
- create normalized search-date columns in the base unified tables;
- generate unified CSV, SQLite, JSON, Excel, or site artifacts;
- define a search ranking or user-interface display policy.

Those actions require later implementation and, where facts are affected, a separately authorized source-data review.
