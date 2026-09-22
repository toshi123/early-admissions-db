# GPA / Grade crosswalk v0.2 candidate audit

Status: `passed`

This is a focused candidate-audit re-evaluation only. No full SQLite or Site-data rebuild was run.

## Scope

- Candidate admissions: 6,411
- Reviewed exact raw values: 63
- Affected admissions: 596
- Matching policy: raw exact match only

## Before / after exact-crosswalk coverage

| Layer | Before unmapped | After unmapped |
|---|---:|---:|
| GPA | 596 | 0 |
| Grade | 596 | 0 |

## Candidate admissions after review

- Grade status: `{"not_required": 368, "required": 67, "review_required": 128, "unknown": 33}`
- Numeric status: `{"ambiguous": 128, "historical": 21, "no_safe_overall_floor": 6, "non_admission_numeric": 28, "non_binding": 340, "safe_overall_with_additional_conditions": 38, "safe_simple_overall": 23, "unknown": 12}`
- Overall floor tenths: `{"35": 15, "38": 19, "40": 24, "41": 2, "43": 1, "NULL": 535}`

## Review-required decisions retained

Distinct raw values: 13; affected admissions: 128

| Order | Admissions | Exact raw value |
|---:|---:|---|
| 8 | 5 | なし（数値基準の明示なし） |
| 10 | 1 | アスリート：全体の学習成績の状況3.2以上。トップアスリート：学習成績による出願要件は設定しない。 |
| 11 | 10 | プログラム別の学力・履修要件による。 |
| 12 | 7 | プログラム別要件による。 |
| 13 | 5 | プログラム所定の学力要件による。 |
| 14 | 2 | プログラム所定要件による。 |
| 15 | 28 | 一律の評定平均値基準なし。 |
| 45 | 12 | 共通の一律評定基準は設けず、専攻・プログラム別の出願資格・能力条件を満たすこと。 |
| 49 | 3 | 学科別推薦基準による。 |
| 52 | 9 | 学類別出願要件による |
| 53 | 22 | 学類別要件あり（A-lympiad選抜では学習成績概評A又は指定教科4.3以上等） |
| 54 | 6 | 学類別要件を募集要項で確認 |
| 56 | 18 | 指定校・学科別推薦基準による。 |

## RIKKYO-2027-SCI-03

- Grade: `required`
- Overall floor: `38` tenths
- Overall status: `safe_overall_with_additional_conditions`
- Strict GPA: `conditional_review` with no numeric floor
- English: `required` / `safe_exact` (English v0.2 review; GPA/Grade unchanged)
