# Academic-field v0.2 Site integration QA

- Build ID: `865009a49ad663caf924`
- Validation profile: `production`
- Production ready: `true`
- Input SQLite SHA-256: `f56a8e671296822b0c844b42de15fcde90fe8aa37e4083dc0096d59304378128`
- Site-data schema: `0.3`
- Validation: `passed`
- Search rows / detail records / child rows: 6699 / 6699 / 495
- Search shards / detail shards: 16 / 256
- Search bytes / gzip equivalent: 16098499 / 917912
- Detail bytes / gzip equivalent: 44254204 / 5716957
- SQLite-to-Site semantic equivalence: 25 queries, logical-key set and summary equality PASS

## GPA strict-safe regression

- GPA 3.0: 72
- GPA 3.5: 499
- GPA 3.8: 763
- GPA 4.0: 1175
- GPA 4.5: 1258

## Grade-requirement regression

- Reviewed requirement-only rows: 2373
- Reviewed overall GPA 3.8 rows: 871
- Requirement statuses: `{"not_applicable": 17, "not_required": 711, "required": 2373, "review_required": 1508, "unknown": 2043, "unmapped": 47}`
- Overall numeric usability: `{"ambiguous": 1501, "historical": 23, "no_safe_overall_floor": 1267, "non_admission_numeric": 35, "non_binding": 366, "not_applicable": 17, "safe_overall_with_additional_conditions": 157, "safe_simple_overall": 1265, "unknown": 2021, "unmapped": 47}`

## Academic-field regression

- Mapping statuses: `{"multi": 1930, "review_required": 45, "single": 4721, "unmapped": 3}`
- Group memberships: `{"agriculture_fisheries": 432, "arts_design": 287, "dentistry": 44, "education": 908, "engineering": 1856, "environment": 246, "home_lifestyle": 75, "humanities": 468, "information": 904, "interdisciplinary": 71, "life_sciences": 654, "medicine": 173, "natural_sciences": 798, "nursing_health_welfare": 831, "pharmacy": 189, "social_sciences": 725, "sports": 49, "tourism_hospitality": 18, "veterinary": 73}`

## Academic-field v0.2

- Broad/Subcategory taxonomy rows: 30 / 89
- Broad/Subcategory membership rows: 9251 / 7538
- Broad/Subcategory coverage: 6680 / 5556
- Branch result: 1916 admissions / 129 universities
- Frozen branch logical-key equality: `passed`
- Broad/Subcategory equivalence cases: 8 / 8
- Combined-filter equivalence cases: 5

## Scope

SQLite was opened with `mode=ro&immutable=1` and `PRAGMA query_only=ON`. No Site UI, API, FTS search, conditional-GPA evaluator, date parser, or source-data mutation was performed.
