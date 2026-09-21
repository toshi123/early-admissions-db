# Site-data projection v0.1 QA

- Build ID: `407ddfbc5a6da6389cd9`
- Input SQLite SHA-256: `629e93518f67c52b57127516af5cb721a225766c2ec8daee80138b708ae8ea47`
- Site-data schema: `0.1`
- Validation: `passed`
- Search rows / detail records / child rows: 5921 / 5921 / 437
- Search shards / detail shards: 16 / 256
- Search bytes / gzip equivalent: 12254865 / 693228
- Detail bytes / gzip equivalent: 33520791 / 4455174
- SQLite-to-Site semantic equivalence: 25 queries, logical-key set and summary equality PASS

## GPA strict-safe regression

- GPA 3.0: 72
- GPA 3.5: 490
- GPA 3.8: 743
- GPA 4.0: 1124
- GPA 4.5: 1199

## Grade-requirement regression

- Reviewed requirement-only rows: 2286
- Reviewed overall GPA 3.8 rows: 833
- Requirement statuses: `{"not_applicable": 20, "not_required": 339, "required": 2286, "review_required": 1291, "unknown": 1985}`
- Overall numeric usability: `{"ambiguous": 1284, "historical": 2, "no_safe_overall_floor": 1269, "non_admission_numeric": 7, "non_binding": 26, "not_applicable": 20, "safe_overall_with_additional_conditions": 123, "safe_simple_overall": 1206, "unknown": 1984}`

## Academic-field regression

- Mapping statuses: `{"multi": 1833, "review_required": 19, "single": 4069}`
- Group memberships: `{"agriculture_fisheries": 423, "arts_design": 232, "dentistry": 36, "education": 787, "engineering": 1750, "environment": 238, "home_lifestyle": 76, "humanities": 334, "information": 852, "interdisciplinary": 46, "life_sciences": 631, "medicine": 154, "natural_sciences": 702, "nursing_health_welfare": 778, "pharmacy": 173, "social_sciences": 608, "sports": 45, "tourism_hospitality": 16, "veterinary": 71}`

## Scope

SQLite was opened with `mode=ro&immutable=1` and `PRAGMA query_only=ON`. No Site UI, API, FTS search, conditional-GPA evaluator, date parser, or source-data mutation was performed.
