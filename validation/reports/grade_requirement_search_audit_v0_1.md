# Grade requirement search audit v0.1

## Audited snapshot

- Unified admissions: **5,921**
- Distinct raw classes: **554** (553 non-NULL exact values plus SQL NULL)
- Unified `master.csv` SHA-256:
  `1df386ed99532a3dff381507978a1454d7c20113574285b2526f6ae122050279`
- Prior GPA raw-value audit SHA-256:
  `d111046ce752c2c5ecc4585e1551811e125b23290d4daeb14e496f4fcee24563`
- Exact-reviewed crosswalk SHA-256:
  `9b09a7d8c91fb8837fb974c441e9975ed26a02fcb656684a7db304804859882c`

The prior audit supplied frequencies, features, and numeric-safety evidence;
every distinct non-NULL raw value was reclassified for the separate question
of whether school grades are an application requirement. Production uses only
exact crosswalk lookup. SQL NULL is handled explicitly by code, and a future
non-NULL value becomes `unmapped` without a numeric floor.

## Grade-requirement status

| Status | Distinct raw classes | Admissions |
|---|---:|---:|
| `required` | 403 | 2,286 |
| `not_required` | 32 | 339 |
| `review_required` | 72 | 1,291 |
| `unknown` | 36 | 1,985 |
| `not_applicable` | 11 | 20 |
| `unmapped` | 0 | 0 |
| **Total** | **554** | **5,921** |

The `unknown` distinct count includes SQL NULL as one class. The crosswalk CSV
itself therefore has 553 data rows.

## Overall numeric usability

| Status | Distinct raw classes | Admissions |
|---|---:|---:|
| `safe_simple_overall` | 96 | 1,206 |
| `safe_overall_with_additional_conditions` | 65 | 123 |
| `no_safe_overall_floor` | 266 | 1,269 |
| `historical` | 2 | 2 |
| `non_binding` | 5 | 26 |
| `non_admission_numeric` | 3 | 7 |
| `ambiguous` | 71 | 1,284 |
| `unknown` | 35 | 1,984 |
| `not_applicable` | 11 | 20 |
| `unmapped` | 0 | 0 |
| **Total** | **554** | **5,921** |

Safe inclusive overall floors exist for 161 distinct expressions and 1,329
admissions. All other rows have a NULL numeric floor. Subject-only rules,
qualitative achievement wording, branches with a grade-free route, historical
figures, non-binding recommendations, and non-admission numbers are not
reduced to a first or minimum number.

## Reviewed boundary examples

- `RIKKYO-2027-SCI-03`: `required`, overall floor 38 tenths, inclusive,
  `safe_overall_with_additional_conditions`, additional conditions true.
- `数学・理科とも3.8以上`: `required`, no overall floor.
- `学習成績概評A段階`: `required`, no overall floor.
- `全体の学習成績の状況3.5以上、または大学指定英語資格・検定スコア条件を満たすこと。`:
  `required`, but no common safe overall floor.
- `評定基準なし。調査書等は選考資料として30点で評価。`:
  `not_required`, no overall floor.
- `数値による評定要件なし。`: `review_required`, because absence of a
  numeric threshold does not establish absence of qualitative requirements.
- `2026年度参考：全体の学習成績の状況4.3以上`: `unknown` plus
  `historical`; it is not a current numeric floor.

No raw source value was rewritten, trimmed, or inferred at runtime.
