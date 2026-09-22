# Academic-field v0.2 taxonomy mapping contract v0.3

Status: active reviewed crosswalk contract
Reviewed on: 2026-09-22
Candidate sources: kokkoritsu 5.81 + shidai 1.08

## Version boundary

The 30 broad groups, 89 subcategories, UI ordering, and v0.1-to-v0.2
compatibility table remain the frozen taxonomy v0.2 artifacts. Mapping contract
v0.3 changes only exact raw/context crosswalk content. The previous v0.2 raw
and context crosswalks are retained byte-for-byte.

Human decisions are authoritative in:

- `validation/reports/update_20260922_v5_81_v1_08/academic_field_raw_human_review_decisions_v0_3.csv`
- `validation/reports/update_20260922_v5_81_v1_08/academic_field_context_human_review_decisions_v0_3.csv`

The deterministic outputs are under `schema/academic_field/v0_3/`.

## Exact mapping rules

Runtime classification is exact-only. It never trims or interprets text and
never infers from a faculty or department name. A context key is exactly:

`(source_dataset, university, faculty_school, department, academic_field)`

The 39 reviewed raw values are appended to the preserved v0.2 raw mappings.
Ambiguous raw values such as `地域` and `経済・工学` remain
`review_required` at raw level.

All 71 reviewed context tuples use `authoritative` merge semantics. Their
approved memberships are the complete final set for that exact tuple and
replace, rather than union with, raw membership. This prevents extra categories
from leaking into program-specific results. The rule does not generalize to
unreviewed contexts.

## v0.1 compatibility layer

Taxonomy v0.1 is unchanged. A reviewed v0.2 broad membership is projected to
v0.1 only when the reverse compatibility relation identifies exactly one v0.1
group. If any selected broad group is ambiguous under that relation, the whole
raw value fails closed as `review_required`; partial projection is prohibited.

## Validation

The update builder checks review order, exact keys, frequencies,
representative records, taxonomy parents, membership ordering, and review
metadata against the 6,411-row candidate. It then verifies zero prohibited
unmapped rows and exact authoritative application of all 71 reviewed contexts
(88 admission rows). Repeated builds from the same decision artifacts must be
byte-identical.
