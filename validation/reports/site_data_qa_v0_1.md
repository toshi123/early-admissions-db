# Site-data projection v0.1 QA

- Build ID: `bbffbaee7aadbdb0ae43`
- Input SQLite SHA-256: `6a59be8707e30fa07d0f40d1e297c57b3c55d071f834c579d99090bdee3e50a0`
- Site-data schema: `0.1`
- Validation: `passed`
- Search rows / detail records / child rows: 5921 / 5921 / 437
- Search shards / detail shards: 8 / 128
- Search bytes / gzip equivalent: 8876347 / 475582
- Detail bytes / gzip equivalent: 29104651 / 3675884
- SQLite-to-Site semantic equivalence: 25 queries, logical-key set and summary equality PASS

## GPA strict-safe regression

- GPA 3.0: 72
- GPA 3.5: 490
- GPA 3.8: 743
- GPA 4.0: 1124
- GPA 4.5: 1199

## Academic-field regression

- Mapping statuses: `{"multi": 1833, "review_required": 19, "single": 4069}`
- Group memberships: `{"agriculture_fisheries": 423, "arts_design": 232, "dentistry": 36, "education": 787, "engineering": 1750, "environment": 238, "home_lifestyle": 76, "humanities": 334, "information": 852, "interdisciplinary": 46, "life_sciences": 631, "medicine": 154, "natural_sciences": 702, "nursing_health_welfare": 778, "pharmacy": 173, "social_sciences": 608, "sports": 45, "tourism_hospitality": 16, "veterinary": 71}`

## Scope

SQLite was opened with `mode=ro&immutable=1` and `PRAGMA query_only=ON`. No Site UI, API, FTS search, conditional-GPA evaluator, date parser, or source-data mutation was performed.
