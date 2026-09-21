# Grade requirement search design v0.1

## 1. Scope

This contract adds a reviewed search layer over the unified
`admissions.gpa_requirement` raw value. It does not modify canonical, release,
unified, or raw SQLite admission facts. It separates two questions that the
existing strict-safe GPA layer intentionally combined:

1. Does the admission use school grades as an application requirement?
2. Is there a safely reviewed lower bound for the overall five-point grade
   average?

The existing `admission_search_gpa` and `admission_search_gpa_safe` contracts
remain unchanged. In particular, an admission may be searchable by the new
overall-grade filter while remaining excluded from the old strict-safe filter.

## 2. Source and freeze

The source is the raw `admissions.gpa_requirement` value for all 5,921 unified
admissions. The v0.1 freeze contains one row for each of the 553 distinct
non-NULL raw values in:

`schema/grade_requirement/grade_requirement_crosswalk_v0_1.csv`

SQL NULL is handled explicitly as `unknown` and is not serialized as a fake
text token in the crosswalk. Therefore the full audit covers 554 classes: 553
non-NULL exact values plus SQL NULL.

Production classification is exact-value lookup only. Substring matching,
regular expressions, numeric-token extraction, AI inference, and first-number
selection are prohibited at runtime. A future non-NULL value absent from the
freeze becomes `unmapped`, has no numeric floor, and fails closed.

## 3. Parent table

`admission_search_grade_requirements` contains exactly one row per
`admissions` row and preserves the raw value byte-for-byte after the CSV-to-SQL
NULL conversion already defined by the SQLite contract.

| Column | Meaning |
|---|---|
| `admission_rowid` | PK and FK to `admissions.admission_rowid` |
| `raw_value` | unchanged `gpa_requirement` raw value |
| `grade_requirement_status` | reviewed application-requirement classification |
| `overall_gpa_min_tenths` | safe current overall-grade lower bound, or NULL |
| `overall_gpa_min_inclusive` | 1 only for an inclusive safe floor; otherwise NULL |
| `overall_gpa_status` | reason the numeric floor is or is not usable |
| `additional_grade_conditions` | 1/0 only when a safe overall floor exists; otherwise NULL |
| `parse_status` | `exact_crosswalk`, `missing`, or `unmapped` |
| `mapping_contract_version` | `0.1` |
| `review_note` | compact human audit note |

The safe view `admission_search_grade_requirements_safe` contains only exact
reviewed `required` rows with an inclusive overall-grade floor.

## 4. Requirement status

- `required`: a current application route explicitly requires an overall
  grade, subject grade, multi-subject average, school grade evaluation, or a
  qualitative school-achievement condition.
- `not_required`: the reviewed wording safely establishes that grades are not
  an application requirement. Selection-stage use alone is not a requirement.
- `review_required`: the wording does not safely distinguish an application
  requirement from selection material, or only says that a numeric threshold
  was not found without resolving qualitative requirements.
- `unknown`: the source says unknown/unavailable, a private standard could not
  be inspected, the current-year rule is not established, or the raw value is
  SQL NULL.
- `not_applicable`: the exact wording concerns only a non-grade condition or
  explicitly states that the field is not applicable.
- `unmapped`: a future non-NULL raw value is absent from the frozen crosswalk.

`数値条件なし` alone is never sufficient to infer `not_required`. Qualitative
requirements such as `成績優秀` are `required`; unresolved wording remains
`review_required`.

## 5. Overall numeric status

- `safe_simple_overall`: a single current overall-grade inclusive lower bound
  is safe and no additional grade condition is present.
- `safe_overall_with_additional_conditions`: a current overall-grade inclusive
  lower bound is safe, while subject-grade or branch-grade conditions also
  remain. The number is useful only as one filter; it does not establish full
  eligibility.
- `no_safe_overall_floor`: a grade requirement exists or has been resolved,
  but no single safe current overall lower bound exists.
- `historical`: the number is previous-year context and is not searchable as a
  current floor.
- `non_binding`: wording such as `望ましい` is not a mandatory numeric floor.
- `non_admission_numeric`: the number is used for scholarships, fee waivers,
  or another non-application purpose.
- `ambiguous`, `unknown`, `not_applicable`, `unmapped`: no numeric floor may be
  emitted.

Tenths are the numeric authority: 3.8 is stored as 38. All v0.1 safe floors are
inclusive. Float equality is not used by search.

Subject-only rules, qualitative conditions, historical references,
non-binding values, non-admission numbers, and branches that allow a path with
no common safe overall threshold have a NULL floor. OR/branch expressions are
never reduced to the minimum number.

## 6. Search semantics

The new checkbox filter is:

`grade_requirement_status = 'required'`

With no number, it includes every safely reviewed required grade condition,
including subject-only and qualitative requirements. With a student overall
grade value `X`, it additionally requires an exact-reviewed safe overall floor
whose inclusive integer-tenths threshold is at most `X`.

The result means: “the reviewed overall-grade lower-bound condition is
safely matched.” It must never be described as application eligibility.
Additional conditions remain for the user to review.

Site URL parameters are:

- `grade_requirement=required`
- `overall_gpa=3.8`

`overall_gpa` is valid only with `grade_requirement=required`. Existing `gpa`
and `gpa_mode` parameters retain their strict-safe meaning for backward
compatibility.

CLI parameters are:

- `--grade-requirement required`
- `--overall-gpa 3.8`

Existing `--gpa` and `--gpa-mode` are unchanged.

## 7. RIKKYO regression

`shidai:0.97:RIKKYO-2027-SCI-03` is frozen as:

- `grade_requirement_status = required`
- `overall_gpa_min_tenths = 38`
- `overall_gpa_min_inclusive = 1`
- `overall_gpa_status = safe_overall_with_additional_conditions`
- `additional_grade_conditions = 1`

It matches the checkbox-only search and the new 3.8 overall-grade search, does
not match the new 3.7 search, and remains excluded from the old strict-safe 3.8
search.

## 8. Validation and metadata

Every build must validate one-to-one parent coverage, raw equality, exact
crosswalk coverage, enum and NULL invariants, fail-closed unmapped handling,
safe-view cardinality, integer-tenths bounds, RIKKYO behavior, and preservation
of the old GPA regression counts.

SQLite and Site-data manifests record the mapping contract version, crosswalk
SHA-256, classification counts, overall-status counts, numeric-floor counts,
raw mismatch count, and representative review/unmapped record IDs.

## 9. Scope boundary

v0.1 does not evaluate subject grades, OR groups, branch eligibility,
qualitative grades, or complete application eligibility. Candidate exports keep
the raw `gpa_requirement`; no canonical fact is rewritten.
