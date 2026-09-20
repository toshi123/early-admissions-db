# English qualification derived search contract v0.1

## Scope

This layer classifies the unchanged unified `english_requirement` raw value for
search. It does not infer whether an applicant is eligible and does not rewrite
canonical, release, unified, or SQLite `admissions` values.

The v0.1 snapshot contains 5,921 admissions, 3,959 SQL NULL values, and 177
distinct non-NULL raw values. The complete frequency audit is
`validation/reports/english_requirement_raw_value_audit_v0_1.csv`.

## Fail-closed classification

- `required`: an externally awarded English qualification, test, score, or its
  submission is an unconditional requirement for the admission row.
- `not_required`: the reviewed wording explicitly makes that external
  qualification unnecessary or optional/additive only.
- `review_required`: alternatives, branches, scope ambiguity, or interaction
  with other qualifications prevents a safe binary result.
- `unknown`: the source could not establish the condition, or the raw value is
  SQL NULL.
- `not_applicable`: reserved for an explicit reviewed non-applicability value.
- `unmapped`: a new non-NULL raw value absent from the frozen exact crosswalk.

Only exact-crosswalk `required` and `not_required` rows have
`search_disposition=safe_exact`. All other statuses are excluded when either
radio option is selected. New raw values become `unmapped`; no substring,
regular-expression, numeric, or first-match inference is permitted.

## UI semantics

The Japanese radio labels are `指定なし`, `必要`, and `必要なし`. `必要` maps
only to `required`; `必要なし` maps only to `not_required`. `review_required`,
`unknown`, `not_applicable`, `unmapped`, and SQL NULL are included only for
`指定なし`. The raw value remains available on the admission detail page.

## Snapshot audit

| status | rows |
|---|---:|
| required | 311 |
| not_required | 1,257 |
| review_required | 251 |
| unknown (non-NULL) | 143 |
| SQL NULL -> unknown/missing | 3,959 |
| not_applicable | 0 |
| unmapped | 0 |

The crosswalk is versioned and exact. Any source refresh must regenerate the
audit, explicitly review new distinct raw values, and update the contract input
before those values can enter a safe binary search result.
