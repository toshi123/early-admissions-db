# Academic-field v0.2 Site integration QA

- Build ID: `f31383fed50309ee033e`
- Validation profile: `candidate_audit`
- Production ready: `false`
- Input SQLite SHA-256: `16b93c33fe7acfb964c55291b36ca26977dfd3da21dd967bb190ec385601573d`
- Site-data schema: `0.2`
- Validation: `passed`
- Search rows / detail records / child rows: 6411 / 6411 / 495
- Search shards / detail shards: 16 / 256
- Search bytes / gzip equivalent: 15398431 / 876809
- Detail bytes / gzip equivalent: 41207307 / 5385169
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
- Requirement statuses: `{"not_applicable": 17, "not_required": 707, "required": 2373, "review_required": 1404, "unknown": 1910}`
- Overall numeric usability: `{"ambiguous": 1397, "historical": 23, "no_safe_overall_floor": 1263, "non_admission_numeric": 35, "non_binding": 366, "not_applicable": 17, "safe_overall_with_additional_conditions": 157, "safe_simple_overall": 1265, "unknown": 1888}`

## Academic-field regression

- Mapping statuses: `{"multi": 1877, "review_required": 40, "single": 4494}`
- Group memberships: `{"agriculture_fisheries": 420, "arts_design": 249, "dentistry": 43, "education": 804, "engineering": 1805, "environment": 239, "home_lifestyle": 74, "humanities": 462, "information": 879, "interdisciplinary": 71, "life_sciences": 640, "medicine": 170, "natural_sciences": 762, "nursing_health_welfare": 817, "pharmacy": 181, "social_sciences": 714, "sports": 49, "tourism_hospitality": 18, "veterinary": 71}`

## Academic-field v0.2

- Broad/Subcategory taxonomy rows: 30 / 89
- Broad/Subcategory membership rows: 8903 / 7261
- Broad/Subcategory coverage: 6400 / 5317
- Branch result: 1862 admissions / 129 universities
- Frozen branch logical-key equality: `passed`
- Broad/Subcategory equivalence cases: 8 / 8
- Combined-filter equivalence cases: 5

## Scope

SQLite was opened with `mode=ro&immutable=1` and `PRAGMA query_only=ON`. No Site UI, API, FTS search, conditional-GPA evaluator, date parser, or source-data mutation was performed.
