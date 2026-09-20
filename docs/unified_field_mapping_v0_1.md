# Unified field mapping and normalization v0.1

## 1. Purpose

This document maps kokkoritsu v5.61 and shidai v0.97 canonical fields into the proposed unified v0.1 tables. It is a contract proposal, not an executed transformation.

Canonical source values are never edited by this mapping. Every output row is traceable through `source_dataset`, `source_version`, and its source key.

## 2. Mapping operations

| Operation | Rule |
|---|---|
| `CONST` | Add the fixed dataset/version value shown in the mapping. |
| `COPY_REQUIRED` | Copy the exact nonblank source string. Blank is an error. |
| `COPY` | Copy the exact nonblank source string; blank becomes logical `null`. |
| `RAW` | Same representation as `COPY`, with an explicit statement that the values are source-specific and do not form a shared enum. |
| `INT_REQUIRED` | Parse a nonblank base-10 integer. Invalid or blank is an error. |
| `INT_NULLABLE` | Parse a nonblank base-10 integer; blank becomes `null`. |
| `BOOL_NULLABLE` | Apply the approved boolean crosswalk; blank becomes `null`. |
| `TRISTATE` | Preserve exact `Yes`, `No`, or `Unknown`; blank becomes `null`; any other value is an error. |
| `ENUM` | Preserve the exact value if it is in the unified enum; otherwise error. |
| `COMMON_TEST_REQUIRED` | Preserve `Yes`, `No`, or `Unknown`; map `条件付き` to `Conditional`; blank becomes `null`. |
| `DETAIL_STATUS` | Apply the narrow detail-completeness crosswalk below. |
| `RESEARCH_LEVEL_STATUS` | Apply the narrow research-activity crosswalk below. |

`COPY`, `COPY_REQUIRED`, and `RAW` do not trim, rewrite punctuation, normalize Unicode, parse dates, or split explanatory text.

## 3. Shared normalization crosswalks

### 3.1 Boolean values

Used only for `stem_flag` and `fallback_previous_year`.

| Source value | Unified JSON value |
|---|---|
| `True` | `true` |
| `Yes` | `true` |
| `False` | `false` |
| `No` | `false` |
| blank | `null` |
| anything else | error |

Unified CSV serializes these as lowercase `true` and `false`.

### 3.2 Tri-state values

Used for the explicitly listed Master fields only.

| Source value | Unified value |
|---|---|
| `Yes` | `Yes` |
| `No` | `No` |
| `Unknown` | `Unknown` |
| blank | `null` |
| anything else | error |

### 3.3 Detail completeness

Both the common status and original source value are emitted.

| Dataset | Source rule | `detail_completeness_status` |
|---|---|---|
| shidai | exact `complete` | `complete` |
| shidai | exact `partial` | `partial` |
| shidai | exact `pending` | `pending` |
| shidai | exact `unknown` | `unknown` |
| kokkoritsu | value begins with exact prefix `detailed` | `complete` |
| kokkoritsu | value begins with exact prefix `partial` | `partial` |
| either | blank | `null` |
| either | any other nonblank value | `unmapped` plus validator warning |

`detail_completeness_raw` always receives the exact nonblank source value. No Japanese sentence is classified from semantic inference in v0.1.

The common value records a normalized source label; it is not an assertion that all unified validators pass.

### 3.4 Research activity level

Both the common status and original source value are emitted. Matches are exact and case-sensitive.

| Dataset | Source value | `research_activity_level_status` |
|---|---|---|
| shidai | `required` | `required` |
| shidai | `relevant` | `relevant` |
| shidai | `none` | `none` |
| shidai | `unknown` | `unknown` |
| kokkoritsu | `explicit_requirement` | `required` |
| kokkoritsu | `探究活動必須` | `required` |
| kokkoritsu | `必須（指定実績のいずれか）` | `required` |
| kokkoritsu | `関連する課外活動実績が出願要件` | `required` |
| kokkoritsu | `relevant` | `relevant` |
| kokkoritsu | `related` | `relevant` |
| kokkoritsu | `explicitly_evaluated` | `relevant` |
| kokkoritsu | `探究活動重視` | `relevant` |
| kokkoritsu | `研究活動重視` | `relevant` |
| kokkoritsu | `none` | `none` |
| kokkoritsu | `なし` | `none` |
| kokkoritsu | `not_specified` | `unknown` |
| either | blank | `null` |
| either | any other nonblank value | `unmapped` plus validator warning |

In particular, values such as `alternative_requirement`, `activity_based`, rankings such as `中`/`高`, and source-specific explanatory phrases remain `unmapped` until separately reviewed. Child-row existence must not be used to derive this status.

### 3.5 Expected mapping profile for the frozen inputs

This preflight is informational and does not create an output artifact.

| Field | Kokkoritsu v5.61 | Shidai v0.97 |
|---|---|---|
| `detail_completeness_status` | `complete` 2,544; `partial` 806; `unmapped` 318 | `complete` 2,137; `partial` 116 |
| `research_activity_level_status` | `required` 90; `relevant` 104; `none` 387; `unknown` 1,478; `unmapped` 281; `null` 1,328 | `required` 95; `relevant` 565; `none` 1,588; `unknown` 5 |

The `unmapped` counts are deliberate. They prevent unsupported source phrases from being forced into a shared category.

## 4. Master mapping

For rows from kokkoritsu, `source_dataset=kokkoritsu` and `source_version=5.61`. For rows from shidai, `source_dataset=shidai` and `source_version=0.97`.

| Unified field | Kokkoritsu source | Shidai source | Operation / notes |
|---|---|---|---|
| `source_dataset` | constant `kokkoritsu` | constant `shidai` | `CONST` |
| `source_version` | constant `5.61` | constant `0.97` | `CONST` |
| `record_id` | `record_id` | `record_id` | `COPY_REQUIRED`; source identifier remains unchanged |
| `admission_year` | `admission_year` | `admission_year` | `INT_REQUIRED`; must equal `2027` |
| `institution_type` | `institution_type` | `institution_type` | `ENUM`: `国立`, `公立`, `私立` |
| `university` | `university` | `university` | `COPY_REQUIRED` |
| `prefecture` | `prefecture` | `prefecture` | `COPY` |
| `academic_field` | `academic_field` | `academic_field` | `COPY` |
| `stem_flag` | `stem_flag` | `stem_flag` | `BOOL_NULLABLE` |
| `faculty_school` | `faculty_school` | `faculty_school` | `COPY` |
| `department` | `department` | `department` | `COPY` |
| `selection_category` | `selection_category` | `selection_category` | `RAW`; no unified enum in v0.1 |
| `selection_name` | `selection_name` | `selection_name` | `COPY` |
| `slot_type` | `slot_type` | `slot_type` | `RAW`; the two sources use different semantics |
| `capacity` | `capacity` | `capacity` | `RAW`; keep textual capacities and qualifiers |
| `school_recommendation_required` | same field | same field | `TRISTATE` |
| `school_nomination_limit` | same field | same field | `COPY` |
| `school_nomination_limit_total` | same field | same field | `COPY` |
| `school_nomination_limit_rule` | same field | same field | `COPY` |
| `exclusive_enrollment_status` | same field | same field | `ENUM`: `専願`, `併願可`, `条件付き`, `不明` |
| `exclusive_enrollment` | same field | same field | `COPY` |
| `exclusive_enrollment_evidence` | same field | same field | `COPY` |
| `exclusive_enrollment_evidence_page` | same field | same field | `COPY` |
| `exclusive_enrollment_evidence_url` | same field | same field | `COPY` |
| `eligibility_graduation` | same field | same field | `COPY` |
| `gpa_requirement` | same field | same field | `COPY` |
| `english_requirement` | same field | same field | `COPY` |
| `subject_prerequisites` | same field | same field | `COPY` |
| `common_test_required` | same field | same field | `COMMON_TEST_REQUIRED`; remains distinct from `selection_common_test` |
| `common_test_usage` | same field | same field | `COPY` |
| `research_activity_level_status` | `research_activity_level` | `research_activity_level` | `RESEARCH_LEVEL_STATUS` |
| `research_activity_level_raw` | `research_activity_level` | `research_activity_level` | `COPY`; exact source value |
| `research_requirement_required` | same field | same field | `TRISTATE`; does not constrain child-row existence |
| `research_activity_detail` | same field | same field | `COPY` |
| `research_requirement_summary` | same field | same field | `COPY` |
| `academic_record_required` | same field | same field | `TRISTATE` |
| `academic_record_type` | same field | same field | `COPY` |
| `academic_record_detail` | same field | same field | `COPY` |
| `documents_summary` | same field | same field | `COPY` |
| `selection_process` | same field | same field | `COPY` |
| `selection_document_review` | same field | same field | `TRISTATE` |
| `selection_interview` | same field | same field | `TRISTATE` |
| `selection_oral_exam` | same field | same field | `TRISTATE` |
| `selection_presentation` | same field | same field | `TRISTATE` |
| `selection_essay` | same field | same field | `TRISTATE` |
| `selection_written_exam` | same field | same field | `TRISTATE` |
| `selection_practical` | same field | same field | `TRISTATE` |
| `selection_group_discussion` | same field | same field | `TRISTATE` |
| `selection_aptitude_test` | same field | same field | `TRISTATE` |
| `selection_common_test` | same field | same field | `TRISTATE`; no equality rule with `common_test_required` |
| `interview_detail` | same field | same field | `COPY` |
| `oral_exam_subjects` | same field | same field | `COPY` |
| `oral_exam_detail` | same field | same field | `COPY` |
| `presentation_detail` | same field | same field | `COPY` |
| `essay_detail` | same field | same field | `COPY` |
| `written_exam_detail` | same field | same field | `COPY` |
| `selection_method_detail` | same field | same field | `COPY` |
| `application_start` | same field | same field | `RAW`; do not parse or rewrite in base unified data |
| `application_end` | same field | same field | `RAW`; do not parse or rewrite in base unified data |
| `web_registration_period` | same field | same field | `RAW`; do not split ranges in base unified data |
| `first_stage_result_date` | same field | same field | `RAW`; retain time/qualifier text |
| `second_stage_start` | same field | same field | `RAW` |
| `second_stage_end` | same field | same field | `RAW` |
| `final_result_date` | same field | same field | `RAW`; retain time/qualifier text |
| `source_status` | same field | same field | `RAW`; source-specific narrative |
| `detail_completeness_status` | `detail_completeness` | `detail_completeness` | `DETAIL_STATUS` |
| `detail_completeness_raw` | `detail_completeness` | `detail_completeness` | `COPY`; exact source value |
| `verification_grade` | same field | same field | `ENUM`: `A`, `B`, `C`, or `null` |
| `verified_on` | same field | same field | `RAW` and required; no base-layer date conversion |
| `source_url` | same field | same field | `COPY_REQUIRED` |
| `schedule_url` | same field | same field | `COPY` |
| `guideline_url` | same field | same field | `COPY` |
| `notes` | same field | same field | `RAW`; preserve leading/trailing whitespace and warn |
| `information_year` | same field | same field | `INT_NULLABLE` |
| `publication_status` | same field | same field | `RAW`; no unified enum in v0.1 |
| `fallback_previous_year` | same field | same field | `BOOL_NULLABLE` |
| `current_year_release_expected` | same field | same field | `RAW` |
| `previous_year_source_url` | same field | same field | `COPY` |
| `fallback_note` | same field | same field | `COPY` |

## 5. Coverage mapping

`research_status`, `current_year_status`, and `fallback_status` are preserved as source-specific raw values. In particular, shidai `research_status` is not mapped to the kokkoritsu coverage enum.

| Unified field | Kokkoritsu source | Shidai source | Operation / notes |
|---|---|---|---|
| `source_dataset` | constant `kokkoritsu` | constant `shidai` | `CONST` |
| `source_version` | constant `5.61` | constant `0.97` | `CONST` |
| `institution_type` | `institution_type` | `institution_type` | `ENUM` |
| `university` | `university` | `university` | `COPY_REQUIRED` |
| `undergraduate_scope` | same field | same field | `RAW` |
| `research_status` | same field | same field | `RAW`; source-specific semantics |
| `master_rows` | same field | same field | `INT_REQUIRED`; must equal joined Master count |
| `current_year_status` | same field | same field | `RAW` |
| `fallback_status` | same field | same field | `RAW` |
| `checked_on` | same field | same field | `RAW` and required; no base-layer date conversion |
| `official_source_url` | same field | same field | `COPY`; in-scope blank values produce a warning |
| `notes` | same field | same field | `RAW` |

## 6. ResearchRequirements mapping

No new classification field is added. In particular, neither `requirement_code`, `alternative_allowed`, `evidence_required`, nor parent flags are used to create a `required / alternative / relevant` class.

| Unified field | Kokkoritsu source | Shidai source | Operation / notes |
|---|---|---|---|
| `source_dataset` | constant `kokkoritsu` | constant `shidai` | `CONST` |
| `source_version` | constant `5.61` | constant `0.97` | `CONST` |
| `admission_id` | `admission_id` | `admission_id` | `COPY_REQUIRED`; composite FK with source provenance |
| `university` | same field | same field | `COPY_REQUIRED`; denormalized display value |
| `faculty_school` | same field | same field | `COPY`; denormalized display value |
| `department` | same field | same field | `COPY`; denormalized display value |
| `selection_name` | same field | same field | `COPY`; denormalized mismatch is warning only |
| `requirement_code` | same field | same field | `RAW`; not treated as a cross-source enum |
| `program_or_competition` | same field | same field | `RAW` |
| `required_level` | same field | same field | `RAW` |
| `requirement_detail` | same field | same field | `RAW` |
| `alternative_allowed` | same field | same field | `RAW`; do not coerce annotated values to boolean |
| `evidence_required` | same field | same field | `RAW`; do not coerce annotated values to boolean |
| `source_url` | same field | same field | `COPY_REQUIRED` |
| `verified_on` | same field | same field | `RAW` and required; no base-layer date conversion |

## 7. Derived search-date proposal

Searchable dates belong to a later derived search/index schema, not to the base unified tables. A future derived layer should use a structure equivalent to:

| Derived field | Meaning |
|---|---|
| `<source_field>_date` | One unambiguous normalized ISO date, otherwise `null` |
| `<source_field>_start_date` | Start of an unambiguous range, otherwise `null` |
| `<source_field>_end_date` | End of an unambiguous range, otherwise `null` |
| `<source_field>_parse_status` | `parsed`, `partial`, `unparsed`, or `not_applicable` |

The original field remains present and unchanged. A date prefix followed by time or explanatory text may be marked `partial`; the parser must not discard the suffix or present the derived value as the complete source fact.

## 8. Validation treatment for ResearchRequirements presence

| Condition | Severity | Required action |
|---|---|---|
| Parent `research_requirement_required=Yes`, zero children | warning | Preserve row; report count and identifiers |
| Parent `research_requirement_required=No`, one or more children | informational | Preserve parent and children; do not reinterpret the flag |
| Parent `Unknown` or `null`, any child count | informational only if useful | No inferred flag value |
| Child FK does not resolve | error | Do not publish the affected unified artifact as valid |
| Exact duplicate child rows | warning | Preserve multiplicity; do not silently deduplicate |
