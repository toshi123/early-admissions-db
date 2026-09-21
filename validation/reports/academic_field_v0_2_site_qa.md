# Academic-field v0.2 Site integration QA

- Build ID: `cc11abf42ba59717eec3`
- Input SQLite SHA-256: `a83055bfab2d9e32b7078f3ee12ea0673392abdc06c32c14b8900e30ec67c624`
- Site-data schema: `0.2`
- Validation: `passed`
- Search rows / detail records / child rows: 5921 / 5921 / 437
- Search shards / detail shards: 16 / 256
- Search bytes / gzip equivalent: 14210412 / 797884
- Detail bytes / gzip equivalent: 37822700 / 4867844
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

## Academic-field v0.2

- Broad/Subcategory taxonomy rows: 30 / 89
- Broad/Subcategory membership rows: 8275 / 6880
- Broad/Subcategory coverage: 5910 / 5027
- Branch result: 1796 admissions / 128 universities
- Frozen branch logical-key equality: `passed`
- Broad/Subcategory equivalence cases: 8 / 8
- Combined-filter equivalence cases: 5

## Scope

SQLite was opened with `mode=ro&immutable=1` and `PRAGMA query_only=ON`. No Site UI, API, FTS search, conditional-GPA evaluator, date parser, or source-data mutation was performed.
