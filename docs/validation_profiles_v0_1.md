# Validation profiles v0.1

The derived SQLite and Site-data builders support two explicit validation
profiles. Omitting the option always selects `production`.

- `production` is the deployability gate. All existing strict validation is
  retained, including the rule that English-requirement `unmapped` rows block
  publication.
- `candidate_audit` is an inspection-only update-acceptance profile. It permits
  reviewable, fail-closed mapping gaps to pass through the technical pipeline
  only when raw values and explicit mapping statuses are preserved. It never
  marks an artifact production-ready.

PK/FK failures, malformed rows or schemas, raw-value mismatches, invalid
tri-state values, source/version mismatches, SQLite integrity failures, and
Site-data referential failures remain hard errors in both profiles.

The CLI flags are:

```text
python -m early_admissions.build_sqlite --validation-profile production
python -m early_admissions.build_sqlite --validation-profile candidate-audit
python -m early_admissions.build_site_data --validation-profile production
python -m early_admissions.build_site_data --validation-profile candidate-audit
```

Candidate-audit Site-data requires an input SQLite manifest and database
metadata that both explicitly record `candidate_audit`. A missing profile is
interpreted only as the safe legacy default, `production`; it can never opt an
artifact into candidate-audit behavior.

Candidate manifests record the validation profile, review-required counts, and
`production_ready: false`. Search filters continue to match only approved safe
classifications. An unmapped raw value remains visible in detail data but is not
coerced into `required`, `not_required`, a numeric GPA floor, or an academic
field membership.
