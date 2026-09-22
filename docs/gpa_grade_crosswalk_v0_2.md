# GPA / Grade exact crosswalk freeze v0.2

## 1. Scope

This freeze adds the 63 `gpa_requirement` raw values reviewed on 2026-09-22
for the kokkoritsu 5.81 and shidai 1.08 candidate sources. It versions only
the GPA and Grade exact crosswalks. English-requirement and academic-field
crosswalks are outside this change.

The previous v0.1 artifacts remain present and loadable so that the current
5,921-row production snapshot can be reproduced exactly.

Read-only structured search and Site-data projection explicitly support Grade
mapping versions `0.1` and `0.2` during this transition. New SQLite builds use
`0.2`. Site projection still requires every detail record to equal the input
SQLite manifest's single declared mapping version; mixed-version payloads are
rejected.

## 2. Authority and provenance

- Previous version: `0.1`
- New version: `0.2`
- Reviewed on: `2026-09-22`
- Review source: human review
- Candidate sources: kokkoritsu `5.81`, shidai `1.08`
- Matching policy: raw exact match only

The two 63-row review packets were compared by raw value, frequency,
university, faculty, department, and representative record ID before any
decision was projected. The result was 63/63 matches and zero mismatches.

The human decisions are preserved separately in
`validation/reports/update_20260922_v5_81_v1_08/gpa_grade_human_review_decisions_v0_2.csv`.
The original review packets are not overwritten.

## 3. Artifacts

| Role | Path | Rows | SHA-256 |
|---|---|---:|---|
| GPA v0.2 exact allowlist | `validation/reports/gpa_requirement_raw_value_audit_v0_2.csv` | 617 including SQL NULL class | `bc6a5416f4b4efe3ce86ed10947e52f556d2a370d6472a2397bd8dbb6c887ffe` |
| Grade v0.2 exact crosswalk | `schema/grade_requirement/grade_requirement_crosswalk_v0_2.csv` | 616 non-NULL raws | `6095c2eebfa37a2a97359fa91f270e6a092bb77b06d23dad805a959710aa57c3` |
| Freeze receipt | `schema/grade_requirement/gpa_grade_crosswalk_manifest_v0_2.json` | n/a | `da9c8d7219eea0f10cf86e602574a5a8127840c01d53d4f44ddf2c3b1e4faad7` |

The receipt records the previous artifacts and hashes, both review packets,
the human-decision artifact, both candidate Master inputs, decision counts,
and output hashes.

## 4. Exact mapping semantics

No substring, regex, fuzzy, or model inference is used. A future raw value
that does not exactly equal a reviewed row remains `unmapped` and receives no
numeric floor.

The Grade layer preserves the two reviewed questions separately:

- `grade_requirement_status` states whether an application-grade condition is
  present.
- `overall_gpa_status` and `overall_gpa_min_tenths` state whether a safe
  current overall-grade inclusive lower bound exists.

Thus a subject-only rule may be `required` while its overall floor remains
NULL. A branch that permits application without a common grade floor also
remains NULL. Non-binding wording and numbers used only in selection or another
non-admission purpose do not become application floors.

The existing SQL contract permits `additional_grade_conditions` only when a
safe overall floor exists. For reviewed rows without a safe floor, the
human-approved true/false decision remains in the human-decision artifact and
the operational derived value is SQL NULL. This is a projection rule, not a
loss or reinterpretation of the reviewed decision.

## 5. Relationship to strict-safe GPA v0.1

The strict-safe GPA parser contract remains `0.1`. Its meaning is unchanged:
only a current, simple, overall, single inclusive lower bound is definitive.

- `safe_simple_overall` is added to the strict-safe allowlist.
- `safe_overall_with_additional_conditions` is retained for Grade search but
  remains `conditional_review` with no strict GPA numeric floor.
- `no_safe_overall_floor`, ambiguous, unknown, historical, non-binding, and
  non-admission values receive no strict GPA floor.

This preserves the production strict-safe regression and avoids claiming that
an overall GPA alone establishes application eligibility.

## 6. Review-required values

Human review intentionally retained 13 exact raws as `review_required`, at
review orders 8, 10, 11, 12, 13, 14, 15, 45, 49, 52, 53, 54, and 56. Human
inspection of the raw alone was insufficient; program or official-guideline
context is still required.

## 7. Candidate-focused validation

The focused candidate audit scans 6,411 source admissions without producing a
new unified dataset, SQLite database, or Site-data tree. The 63 reviewed raws
affect 596 admissions.

- GPA exact-crosswalk unmapped: 596 before, 0 after
- Grade unmapped: 596 before, 0 after
- Review-required: 13 distinct raws / 128 admissions after review
- RIKKYO-2027-SCI-03: Grade `required`, overall floor 38 tenths,
  `safe_overall_with_additional_conditions`, strict GPA
  `conditional_review`, and English remains `unmapped`

The machine-readable and human-readable receipts are:

- `validation/reports/update_20260922_v5_81_v1_08/gpa_grade_crosswalk_v0_2_candidate_audit.json`
- `validation/reports/update_20260922_v5_81_v1_08/gpa_grade_crosswalk_v0_2_candidate_audit.md`

## 8. Rebuild

Run:

```bash
./scripts/build_gpa_grade_crosswalk_v0_2
```

The command validates packet correspondence and candidate frequencies, writes
the two versioned crosswalks and manifest deterministically, then runs only the
focused GPA/Grade candidate audit. It does not modify canonical, release,
unified, SQLite, Site-data, English, or academic-field artifacts.
